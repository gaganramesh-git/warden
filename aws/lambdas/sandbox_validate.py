"""S4 · Sandbox validate (Lambda). Replays with the guardrail ON: misbehavior
gone AND legit task still completes? On pass, signs token_A with KMS KEY_A.

This is the ONLY Lambda whose role has kms:Sign on KEY_A.
"""
from __future__ import annotations

from core.contracts import Guardrail, Status, Verdict
from core.sandbox import Sandbox
from aws.kms_gate import KmsSigner
from . import common


def handler(event, _context=None):
    store, s3 = common.cases(), common.transcripts()
    case_id = event["caseId"]
    trace = s3.get_transcript(event["sessionId"])

    verdict = Verdict(**_verdict_fields(store.get(case_id, "VERDICT")))
    guardrail = Guardrail(**_guardrail_fields(store.get(case_id, "GUARDRAIL")))

    store.set_status(case_id, Status.VALIDATING)
    sandbox = Sandbox(KmsSigner("KEY_A", common.KEY_A_ARN))
    run = sandbox.validate(trace, guardrail, verdict, sign=True)
    token_a = getattr(run, "tokenA", None)
    canonical = getattr(run, "canonical", None)

    store.put(case_id, "SANDBOX#" + run.sandboxRunId, {
        "mode": run.mode, "misbehaviorCleared": run.misbehaviorCleared,
        "taskStillCompletes": run.taskStillCompletes, "hasTokenA": token_a is not None,
    })
    # Persist token_A (a public signature, not a secret) so the REST /deploy demo
    # path can retrieve it. The saga passes it inline; this is the console's copy.
    if token_a is not None:
        store.put(case_id, "SANDBOX_TOKEN", {"tokenA": token_a.to_dict(),
                                             "canonical": canonical})
    s3.put_replay(case_id, run.sandboxRunId, {
        "mode": "validate", "emittedToolCalls": run.emittedToolCalls,
        "misbehaviorCleared": run.misbehaviorCleared,
    })

    if token_a is None:
        store.set_status(case_id, "ESCALATED")
        return {"type": "RehearsalFailed", "caseId": case_id, "signed": False}

    return {
        "type": "RehearsalCompleted", "caseId": case_id, "signed": True,
        "sandboxRunId": run.sandboxRunId,
        "misbehaviorCleared": run.misbehaviorCleared,
        "taskStillCompletes": run.taskStillCompletes,
        "tokenA": token_a.to_dict(), "canonical": canonical,
        "planHash": guardrail.plan_hash(), "verdictHash": verdict.hash(),
    }


def _verdict_fields(item):
    from core.contracts import Counterfactual
    d = {k: item[k] for k in ("rootCause", "rootCauseText", "confidence",
                               "rankedCauses", "recommendedGuardrailId")}
    cf = item["counterfactual"]
    d["counterfactual"] = Counterfactual(**cf)
    return d


def _guardrail_fields(item):
    r = item["rule"] if "rule" in item else item
    return {k: r[k] for k in ("guardrailId", "agentId", "when", "block", "description")}
