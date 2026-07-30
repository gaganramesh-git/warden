"""UI / BFF (API Gateway REST → Lambda). Thin router over the case store and the
saga. It has NO crypto permissions of its own: it INVOKES the approval and
actuator Lambdas (which own the KEY_B sign / verify grants), keeping role
separation intact. Refusal returns 200 with {status:"refused"} — a refusal is an
expected outcome, not a server error (Backend Schema §6)."""
from __future__ import annotations

import json
import os

from . import common


def _resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body)}


def _invoke(fn_env: str, payload: dict) -> dict:
    import boto3
    fn = os.environ.get(fn_env)
    out = boto3.client("lambda").invoke(FunctionName=fn, Payload=json.dumps(payload).encode())
    return json.loads(out["Payload"].read())


def handler(event, _context=None):
    method = event.get("httpMethod", "GET")
    path = event.get("path") or event.get("resource", "")
    # API Gateway proxy integration delivers the whole path in {proxy}, so derive
    # the case id from the path segments (robust with or without a stage prefix).
    segs = [s for s in path.split("/") if s]
    case_id = None
    if "cases" in segs:
        i = segs.index("cases")
        if i + 1 < len(segs):
            case_id = segs[i + 1]
    store = common.cases()

    # POST /cases/{id}/approve  -> approval Lambda signs token_B, resumes saga
    if method == "POST" and path.endswith("/approve"):
        return _resp(200, _invoke("APPROVAL_FN", {"body": event.get("body"), "caseId": case_id}))

    # POST /cases/{id}/deploy  -> actuator Lambda verifies A+B
    if method == "POST" and path.endswith("/deploy"):
        ta = (store.get(case_id, "SANDBOX_TOKEN") or {}).get("tokenA")
        tb = (store.get(case_id, "APPROVAL") or {}).get("tokenB")
        return _resp(200, _invoke("ACTUATOR_FN", {"caseId": case_id, "tokenA": ta, "tokenB": tb}))

    # POST /cases/{id}/deployUnsafe  -> DEMO: strip token_A, forced refusal
    if method == "POST" and path.endswith("/deployUnsafe"):
        tb = (store.get(case_id, "APPROVAL") or {}).get("tokenB")
        return _resp(200, _invoke("ACTUATOR_FN", {"caseId": case_id, "tokenA": None, "tokenB": tb}))

    # GET /cases/{id}  -> full case aggregate
    if method == "GET" and case_id:
        aggregate = {}
        for sk in ("META", "VERDICT", "GUARDRAIL", "APPROVAL", "ACTUATION"):
            item = store.get(case_id, sk)
            if item:
                aggregate[sk] = item
        return _resp(200, {"caseId": case_id, **aggregate})

    # GET /cases?status=AWAITING_APPROVAL
    if method == "GET":
        status = (event.get("queryStringParameters") or {}).get("status", "AWAITING_APPROVAL")
        return _resp(200, {"status": status, "cases": store.list_by_status(status)})

    return _resp(404, {"error": "not found"})
