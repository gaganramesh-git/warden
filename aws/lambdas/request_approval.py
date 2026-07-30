"""Orchestrator step · RequestApproval (Step Functions .waitForTaskToken).
Persists the task token + the canonical payload with the case and emits
ApprovalRequested. The saga pauses here until the operator resolves it via the
approval Lambda (SendTaskSuccess). Native human-in-the-loop, no polling."""
from __future__ import annotations

from core.contracts import Status
from . import common


def handler(event, _context=None):
    store = common.cases()
    case_id = event["caseId"]
    store.put(case_id, "APPROVAL_PENDING", {
        "taskToken": event["taskToken"],
        "canonical": event["canonical"],
        "sandboxRunId": event["sandboxRunId"],
    })
    store.set_status(case_id, Status.AWAITING_APPROVAL)
    # In prod this also publishes to EventBridge/Slack with the full context.
    return {"type": "ApprovalRequested", "caseId": case_id}
