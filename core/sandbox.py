"""
WARDEN — sandbox.py  (the merged component: one engine, two modes)
==================================================================
One deterministic replay engine (agent_harness.replay) exposed two ways:

  falsify(trace, factor)     -> remove the suspect input, replay, did the
                                misbehavior signature stop firing? Used by
                                Diagnosis. The counterfactual is the ARBITER —
                                not an LLM's opinion.

  validate(trace, guardrail) -> replay with the guardrail active, is the
                                misbehavior gone AND the legit task still
                                completing? On pass, ask the gate to sign
                                token_A over the case facts.

"The same simulator that proves the cause proves the cure." Both return a
sandbox_run_id binding the run to the case.
"""
from __future__ import annotations

from typing import Optional

from . import agent_harness
from .contracts import (
    Guardrail, SandboxRun, SessionTrace, Verdict, new_id,
)
from .gate import Signer, Token, build_canonical


class Sandbox:
    """Holds KEY_A (via `signer`) and is the ONLY component that may mint a
    rehearsal-pass token — and only after a genuinely passing validate replay."""

    def __init__(self, signer: Signer):
        # signer is a KEY_A Signer. Nothing else in the system holds it.
        self._signer = signer

    # ----------------------------------------------------------------- falsify
    def falsify(self, trace: SessionTrace, factor: int) -> SandboxRun:
        """Replay with `factor` (a step index) removed. Clears => causal."""
        sensitive = trace.signature.sensitiveCall if trace.signature else "issue_refund"

        control = agent_harness.replay(trace)
        mutated = agent_harness.replay(trace, drop_step=factor)

        fired_before = control.signature_fires(sensitive)
        fired_after = mutated.signature_fires(sensitive)

        # "cleared" only means something if the misbehavior was there to begin
        # with. Removing an innocent step leaves it firing -> not cleared.
        cleared = bool(fired_before and not fired_after)
        return SandboxRun(
            sandboxRunId=new_id("sr"),
            mode="falsify",
            misbehaviorCleared=cleared,
            emittedToolCalls=mutated.emitted(),
        )

    # ---------------------------------------------------------------- validate
    def validate(self, trace: SessionTrace, guardrail: Guardrail,
                 verdict: Verdict, sign: bool = True) -> SandboxRun:
        """Replay with the guardrail ON. Must clear the misbehavior AND keep the
        legit task working. On pass (and sign=True), signs token_A."""
        sensitive = trace.signature.sensitiveCall if trace.signature else "issue_refund"

        mutated = agent_harness.replay(trace, guardrail=guardrail)
        cleared = not mutated.signature_fires(sensitive)
        task_ok = mutated.task_completes(trace.task_intent)

        run = SandboxRun(
            sandboxRunId=new_id("sr"),
            mode="validate",
            misbehaviorCleared=cleared,
            taskStillCompletes=task_ok,
            emittedToolCalls=mutated.emitted(),
        )

        token_a: Optional[Token] = None
        if sign and cleared and task_ok:
            canonical = build_canonical(
                session_id=trace.sessionId,
                plan_hash=guardrail.plan_hash(),
                sandbox_run_id=run.sandboxRunId,
                verdict_hash=verdict.hash(),
                nonce=new_id("nonce"),
            )
            token_a = self._signer.sign_rehearsal(canonical)
        # Attach the canonical + token to the run object for the orchestrator.
        run.tokenA = token_a  # type: ignore[attr-defined]
        run.canonical = canonical if token_a else None  # type: ignore[attr-defined]
        return run

    # ------------------------------------------------------- determinism check
    @staticmethod
    def is_deterministic(trace: SessionTrace, factor: int, runs: int = 5) -> bool:
        """Acceptance helper (Build brief §6): run falsify N times, same result."""
        sensitive = trace.signature.sensitiveCall if trace.signature else "issue_refund"
        results = set()
        for _ in range(runs):
            control = agent_harness.replay(trace)
            mutated = agent_harness.replay(trace, drop_step=factor)
            results.add((control.signature_fires(sensitive),
                         mutated.signature_fires(sensitive),
                         tuple(mutated.emitted())))
        return len(results) == 1
