"""S2 · Detector (Lambda). Scans a trace for the injection signature; on a hit,
opens a Case (DynamoDB) and emits MisbehaviorDetected. No hit -> no case."""
from __future__ import annotations

from core.contracts import Status, new_id
from core.detector import detect
from . import common


def handler(event, _context=None):
    store, s3 = common.cases(), common.transcripts()
    trace = s3.get_transcript(event["sessionId"])
    det = detect(trace)
    if not det.detected:
        return {"type": "NoMisbehavior", "sessionId": trace.sessionId, "detected": False}

    case_id = new_id("case")
    store.put(case_id, "META", {
        "agentId": trace.agentId, "sessionId": trace.sessionId,
        "type": det.type, "signature": det.signature.to_dict(),
        "severity": det.severity, "status": Status.DETECTED,
    })
    return {
        "type": "MisbehaviorDetected",
        "caseId": case_id, "sessionId": trace.sessionId,
        "detected": True, "severity": det.severity,
        "signature": det.signature.to_dict(), "spanRefs": det.span_refs,
    }
