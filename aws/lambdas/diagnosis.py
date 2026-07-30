"""S3 · Diagnosis (AgentCore/Bedrock in prod; deterministic here). Runs the four
partitioned generators + critic, then FALSIFIES via the Sandbox — the
counterfactual is the arbiter. Writes VERDICT + GUARDRAIL, emits VerdictProduced.

This Lambda's role has NO kms:Sign: falsify never signs. Only the validate step
mints token_A.
"""
from __future__ import annotations

from core.contracts import SessionTrace, Status
from core.diagnosis import Diagnosis
from core.sandbox import Sandbox
from aws.kms_gate import KmsSigner
from . import common


def handler(event, _context=None):
    store, s3 = common.cases(), common.transcripts()
    case_id = event["caseId"]
    trace = s3.get_transcript(event["sessionId"])
    meta = store.get(case_id, "META")

    # Sandbox needs a signer object, but diagnosis only falsifies (never signs),
    # so no kms:Sign grant is exercised here.
    sandbox = Sandbox(KmsSigner("KEY_A", common.KEY_A_ARN))
    verdict, ranked, guardrail = Diagnosis(sandbox).diagnose(trace, meta["agentId"])

    for h in ranked:
        store.put(case_id, "HYP#" + h.gen, h.to_dict())
    store.put(case_id, "VERDICT", verdict.to_dict())
    store.put(case_id, "GUARDRAIL", guardrail.to_dict())
    store.set_status(case_id, Status.DIAGNOSED)

    return {
        "type": "VerdictProduced",
        "caseId": case_id, "sessionId": trace.sessionId,
        "rootCause": verdict.rootCause, "confidence": verdict.confidence,
        "confirmed": verdict.counterfactual.confirmed,
        "guardrailId": guardrail.guardrailId,
    }
