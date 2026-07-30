"""
WARDEN — aws/dynamo_store.py
============================
DynamoDB single-table adapter. Presents the SAME method surface as
core.store.CaseStore / PolicyStore, plus a DynamoDB-backed nonce ledger, so the
services in core/ don't change between local and AWS mode — only which store is
injected.

Table `warden` (Backend Schema §2):
    PK = CASE#<id>       SK = META | HYP#<gen> | VERDICT | SANDBOX#<run> |
                              APPROVAL | ACTUATION | TRACE
    PK = GUARDRAIL#<gid> SK = META
    PK = NONCE#<n>       SK = USED     (TTL-expired)
    GSI1: GSI1PK = STATUS#<status>, GSI1SK = <updatedAt>   (status board)
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.contracts import Guardrail


def _num(v: Any) -> Any:
    """DynamoDB returns every number as Decimal. Coerce back to int/float so the
    canonical-JSON hashing the signatures depend on stays byte-identical to the
    values that were signed."""
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, list):
        return [_num(x) for x in v]
    if isinstance(v, dict):
        return {k: _num(x) for k, x in v.items()}
    return v


class DynamoCaseStore:
    def __init__(self, table_name: str, ddb=None):
        if ddb is None:
            import boto3
            ddb = boto3.resource("dynamodb")
        self._t = ddb.Table(table_name)

    def put(self, case_id: str, sk: str, item: Dict[str, Any]) -> None:
        rec = {"PK": "CASE#" + case_id, "SK": sk, **item, "updatedAt": _now()}
        if sk == "META" and "status" in item:
            rec["GSI1PK"] = "STATUS#" + item["status"]
            rec["GSI1SK"] = rec["updatedAt"]
        self._t.put_item(Item=rec)

    def get(self, case_id: str, sk: str) -> Optional[Dict[str, Any]]:
        resp = self._t.get_item(Key={"PK": "CASE#" + case_id, "SK": sk})
        item = resp.get("Item")
        return _num(item) if item is not None else None

    def set_status(self, case_id: str, status: str) -> None:
        self._t.update_item(
            Key={"PK": "CASE#" + case_id, "SK": "META"},
            UpdateExpression="SET #s = :s, GSI1PK = :g, GSI1SK = :u, updatedAt = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": status, ":g": "STATUS#" + status, ":u": _now()},
        )

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        resp = self._t.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :g",
            ExpressionAttributeValues={":g": "STATUS#" + status},
            ScanIndexForward=False,
        )
        return [_num(i) for i in resp.get("Items", [])]

    def record_event(self, event: Dict[str, Any]) -> None:
        # Events flow over EventBridge in AWS mode; persisting is optional.
        pass


class DynamoNonceLedger:
    """Replay-protection ledger. `record` uses a conditional put so a concurrent
    replay of the same approval loses the race (stronger than the local set)."""

    def __init__(self, table_name: str, ddb=None, ttl_seconds: int = 3600):
        if ddb is None:
            import boto3
            ddb = boto3.resource("dynamodb")
        self._t = ddb.Table(table_name)
        self._ttl = ttl_seconds
        from botocore.exceptions import ClientError
        self._ClientError = ClientError

    def seen(self, nonce: str) -> bool:
        resp = self._t.get_item(Key={"PK": "NONCE#" + nonce, "SK": "USED"})
        return "Item" in resp

    def record(self, nonce: str) -> None:
        try:
            self._t.put_item(
                Item={"PK": "NONCE#" + nonce, "SK": "USED",
                      "usedAt": _now(), "ttl": int(time.time()) + self._ttl},
                ConditionExpression="attribute_not_exists(PK)",
            )
        except self._ClientError as e:
            # already recorded — treat as seen (idempotent)
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise


class DynamoPolicyStore:
    """The active-guardrail store the Actuator mutates (GUARDRAIL# items). The
    monitored agent reads these as its live policy (AgentCore Policy in prod)."""

    def __init__(self, table_name: str, ddb=None):
        if ddb is None:
            import boto3
            ddb = boto3.resource("dynamodb")
        self._t = ddb.Table(table_name)

    def apply(self, guardrail: Guardrail) -> str:
        self._t.put_item(Item={
            "PK": "GUARDRAIL#" + guardrail.guardrailId, "SK": "META",
            "agentId": guardrail.agentId, "rule": guardrail.to_dict(),
            "cedar": guardrail.to_cedar(), "status": "active", "createdAt": _now(),
        })
        return "rb_" + guardrail.guardrailId

    def rollback(self, rollback_token: str) -> bool:
        gid = rollback_token[3:]
        self._t.update_item(
            Key={"PK": "GUARDRAIL#" + gid, "SK": "META"},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "rolled_back"},
        )
        return True

    def snapshot(self) -> Dict[str, Any]:
        resp = self._t.query(
            KeyConditionExpression="PK = :p",
            ExpressionAttributeValues={":p": "GUARDRAIL#"},
        ) if False else {"Items": []}
        return {i["PK"]: i.get("rule") for i in resp.get("Items", [])}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
