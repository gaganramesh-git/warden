"""S5 · Actuator (Lambda) — the only prod-mutating service. Its role has
kms:Verify ONLY (no Sign, on any key). It verifies BOTH tokens + all bindings
via the shared verify_bindings (through KmsVerifier), then applies the guardrail
to the policy store, or hard-fails with ActuationRefused and mutates nothing.

Pass tokenA=None (the /deployUnsafe demo path) and it refuses — the climax."""
from __future__ import annotations

from core.contracts import Guardrail, Status, Verdict
from core.gate import ActuationRefused, Token
from aws.kms_gate import KmsVerifier
from .sandbox_validate import _guardrail_fields, _verdict_fields
from . import common


def handler(event, _context=None):
    store = common.cases()
    case_id = event["caseId"]
    guardrail = Guardrail(**_guardrail_fields(store.get(case_id, "GUARDRAIL")))
    verdict = Verdict(**_verdict_fields(store.get(case_id, "VERDICT")))

    token_a = _tok(event.get("tokenA"))
    token_b = _tok(event.get("tokenB"))

    store.set_status(case_id, Status.EXECUTING)
    verifier = KmsVerifier(common.KEY_A_ARN, common.KEY_B_ARN, common.nonce_ledger())
    try:
        verifier.verify(guardrail.plan_hash(), verdict.hash(), token_a, token_b)
    except ActuationRefused as refusal:
        store.put(case_id, "ACTUATION", {"status": "refused", "refusalReason": refusal.reason})
        store.set_status(case_id, Status.REFUSED)
        return {"type": "ActuationRefused", "caseId": case_id, "status": "refused",
                "reason": refusal.reason}

    rollback = common.policy().apply(guardrail)
    store.put(case_id, "ACTUATION", {"status": "applied",
                                     "appliedGuardrailId": guardrail.guardrailId,
                                     "rollbackToken": rollback})
    store.set_status(case_id, Status.RESOLVED)
    return {"type": "GuardrailApplied", "caseId": case_id, "status": "applied",
            "guardrailId": guardrail.guardrailId, "rollbackToken": rollback}


def _tok(d):
    return Token(**d) if d else None
