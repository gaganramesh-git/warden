"""Approval path (API-invoked). The ONLY holder of kms:Sign on KEY_B. Signs
token_B over the SAME canonical the rehearsal signed, then resumes the saga with
SendTaskSuccess. A rogue service cannot forge this: it has no KEY_B grant."""
from __future__ import annotations

import json

from aws.kms_gate import KmsSigner
from . import common


def handler(event, _context=None):
    raw = event.get("body")
    body = json.loads(raw) if isinstance(raw, str) else (raw or {})
    # caseId is passed as a sibling of body by the API BFF; approver is in body.
    case_id = event.get("caseId") or body.get("caseId")
    approver = body.get("approver", "operator@org")

    store = common.cases()
    pending = store.get(case_id, "APPROVAL_PENDING")
    canonical = pending["canonical"]

    token_b = KmsSigner("KEY_B", common.KEY_B_ARN).sign_approval(canonical, approver)
    store.put(case_id, "APPROVAL", {"approver": approver, "decision": "approved",
                                    "tokenB": token_b.to_dict()})

    import boto3
    boto3.client("stepfunctions").send_task_success(
        taskToken=pending["taskToken"],
        output=json.dumps({"tokenB": token_b.to_dict(), "approver": approver}),
    )
    return {"type": "ApprovalGranted", "caseId": case_id, "approver": approver}
