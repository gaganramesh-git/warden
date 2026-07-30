"""
WARDEN — actuator.py  (the ONLY prod-mutating service)
======================================================
apply(guardrail, verdict, token_A, token_B):
  1. verify BOTH signatures and ALL bindings via the gate Verifier
     (verify-only key access — it holds no private keys and cannot self-authorize)
  2. on success  -> apply the guardrail to the policy store, store a rollback
     token, return GuardrailApplied
  3. on ANY failure -> mutate NOTHING, return ActuationRefused with the reason

The stripped-token hard-fail (Build brief §5) is the demo climax and a first-
class test: strip token_A, apply() refuses, state is byte-identical.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .contracts import Guardrail, Verdict
from .gate import ActuationRefused, Token, Verifier
from .store import PolicyStore


class ActuationResult:
    def __init__(self, status: str, guardrail_id: Optional[str] = None,
                 rollback_token: Optional[str] = None, reason: Optional[str] = None):
        self.status = status                 # "applied" | "refused"
        self.guardrail_id = guardrail_id
        self.rollback_token = rollback_token
        self.reason = reason

    @property
    def applied(self) -> bool:
        return self.status == "applied"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "appliedGuardrailId": self.guardrail_id,
            "rollbackToken": self.rollback_token,
            "refusalReason": self.reason,
        }


class Actuator:
    def __init__(self, verifier: Verifier, policy: PolicyStore):
        # verifier holds PUBLIC keys only. There is no code path here that can
        # produce a signature.
        self._verifier = verifier
        self._policy = policy

    def apply(self, guardrail: Guardrail, verdict: Verdict,
              token_a: Optional[Token], token_b: Optional[Token]) -> ActuationResult:
        # Snapshot state so we can *prove* nothing changed on refusal.
        before = self._policy.snapshot()
        try:
            self._verifier.verify(
                plan_hash=guardrail.plan_hash(),
                verdict_hash=verdict.hash(),
                token_a=token_a,
                token_b=token_b,
            )
        except ActuationRefused as refusal:
            after = self._policy.snapshot()
            assert after == before, "INVARIANT VIOLATED: state changed on refusal"
            return ActuationResult("refused", reason=refusal.reason)

        # Both attestations verified and bound. Now — and only now — mutate.
        rollback_token = self._policy.apply(guardrail)
        return ActuationResult(
            "applied",
            guardrail_id=guardrail.guardrailId,
            rollback_token=rollback_token,
        )
