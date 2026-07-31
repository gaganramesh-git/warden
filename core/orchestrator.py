"""
WARDEN — orchestrator.py
========================
The saga, wired for local mode. In AWS mode this is a Step Functions state
machine; here it is a plain object driving the same core services through the
same event contracts:

  DETECTED -> DIAGNOSING -> DIAGNOSED -> VALIDATING(sign A)
           -> AWAITING_APPROVAL(sign B) -> EXECUTING(verify A+B)
           -> RESOLVED | REFUSED | REJECTED

One WardenEngine owns key custody so role separation holds: the Sandbox is the
only holder of KEY_A, the Approval path the only holder of KEY_B, and the
Actuator gets a verify-only view. A single shared nonce ledger gives real
replay protection across deploy attempts.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .actuator import Actuator, ActuationResult
from .contracts import (
    Event, Guardrail, Hypothesis, SessionTrace, Status, Verdict, new_id,
)
from .detector import DetectionResult, detect
from .diagnosis import Diagnosis
from .gate import Keyring, NonceLedger, Token
from .sandbox import Sandbox
from .store import CaseStore, PolicyStore

EventSink = Callable[[Event], None]

# Sentinel: distinguishes "caller didn't pass a token, use the stored one" from
# "caller explicitly stripped this token" (the demo climax passes None on purpose).
_UNSET = object()


class WardenEngine:
    def __init__(self, policy_file: Optional[str] = None,
                 on_event: Optional[EventSink] = None):
        self.keyring = Keyring()
        self.ledger = NonceLedger()                      # shared replay-protection
        self.sandbox = Sandbox(self.keyring.sandbox_signer)
        self.diagnosis = Diagnosis(self.sandbox)
        self.policy = PolicyStore(policy_file=policy_file)
        self.verifier = self.keyring.actuator_verifier(self.ledger)
        self.actuator = Actuator(self.verifier, self.policy)
        self.cases = CaseStore()
        self._sink = on_event or (lambda e: None)

    # ------------------------------------------------------------------ events
    def _emit(self, etype: str, case_id: Optional[str] = None, **payload) -> None:
        ev = Event(type=etype, caseId=case_id, payload=payload)
        self.cases.record_event(ev.to_dict())
        self._sink(ev)

    # -------------------------------------------------- production (no WARDEN)
    def run_unprotected(self, trace: SessionTrace) -> Dict[str, Any]:
        """What the agent does with no WARDEN watching: the recorded control
        replay. This is the cold-open disaster."""
        from . import agent_harness
        control = agent_harness.replay(trace)
        executed = [
            {"name": c.name, "args": c.args, "introducedBy": c.introducedBy}
            for c in control.tool_calls if not c.blocked
        ]
        return {"sessionId": trace.sessionId, "executed": executed}

    # ------------------------------------------------------------------ detect
    def open_case(self, trace: SessionTrace, agent_id: str) -> Optional[str]:
        det: DetectionResult = detect(trace)
        if not det.detected:
            return None
        case_id = new_id("case")
        self.cases.put(case_id, "META", {
            "agentId": agent_id, "sessionId": trace.sessionId,
            "type": det.type, "signature": det.signature.to_dict(),
            "severity": det.severity, "status": Status.DETECTED,
        })
        self.cases.put(case_id, "TRACE", trace.to_dict())
        self._emit("MisbehaviorDetected", case_id, sessionId=trace.sessionId,
                   type=det.type, severity=det.severity,
                   signature=det.signature.to_dict(), spanRefs=det.span_refs)
        return case_id

    # ---------------------------------------------------------------- diagnose
    def diagnose(self, case_id: str) -> Verdict:
        meta = self.cases.get(case_id, "META")
        trace = SessionTrace.from_dict(self.cases.get(case_id, "TRACE"))
        self.cases.set_status(case_id, Status.DIAGNOSING)
        self._emit("DiagnosisStarted", case_id, sessionId=trace.sessionId)

        verdict, ranked, guardrail = self.diagnosis.diagnose(trace, meta["agentId"])

        for h in ranked:
            self.cases.put(case_id, "HYP#" + h.gen, h.to_dict())
            self._emit("HypothesisProduced", case_id, gen=h.gen,
                       evidenceSlice=h.evidenceSlice, suspectFactor=h.suspectFactor,
                       confidence=h.confidence, evidence=h.evidence)

        self.cases.put(case_id, "VERDICT", verdict.to_dict())
        self.cases.put(case_id, "GUARDRAIL", guardrail.to_dict())
        self.cases.set_status(case_id, Status.DIAGNOSED)
        self._emit("VerdictProduced", case_id, rootCause=verdict.rootCause,
                   rootCauseText=verdict.rootCauseText, confidence=verdict.confidence,
                   counterfactual=verdict.counterfactual.to_dict())
        self._emit("GuardrailProposed", case_id, guardrailId=guardrail.guardrailId,
                   rule=guardrail.to_dict(), cedar=guardrail.to_cedar(),
                   description=guardrail.description)
        self._verdict_cache = getattr(self, "_verdict_cache", {})
        self._verdict_cache[case_id] = verdict
        self._guardrail_cache = getattr(self, "_guardrail_cache", {})
        self._guardrail_cache[case_id] = guardrail
        return verdict

    # ---------------------------------------------------------------- validate
    def validate_and_sign(self, case_id: str) -> Token:
        trace = SessionTrace.from_dict(self.cases.get(case_id, "TRACE"))
        verdict = self._verdict_cache[case_id]
        guardrail = self._guardrail_cache[case_id]
        self.cases.set_status(case_id, Status.VALIDATING)

        run = self.sandbox.validate(trace, guardrail, verdict, sign=True)
        token_a: Optional[Token] = getattr(run, "tokenA", None)
        self.cases.put(case_id, "SANDBOX#" + run.sandboxRunId, {
            "mode": run.mode, "misbehaviorCleared": run.misbehaviorCleared,
            "taskStillCompletes": run.taskStillCompletes,
            "hasTokenA": token_a is not None,
        })
        self._emit("RehearsalCompleted", case_id, sandboxRunId=run.sandboxRunId,
                   misbehaviorCleared=run.misbehaviorCleared,
                   taskStillCompletes=run.taskStillCompletes,
                   signed=token_a is not None)
        if token_a is None:
            raise RuntimeError("validation failed; rehearsal not signed")
        self._token_a = getattr(self, "_token_a", {})
        self._token_a[case_id] = token_a
        self._canonical = getattr(self, "_canonical", {})
        self._canonical[case_id] = getattr(run, "canonical")
        self._sandbox_run = getattr(self, "_sandbox_run", {})
        self._sandbox_run[case_id] = run
        return token_a

    # ----------------------------------------------------------------- approve
    def request_approval(self, case_id: str) -> Dict[str, Any]:
        self.cases.set_status(case_id, Status.AWAITING_APPROVAL)
        verdict = self._verdict_cache[case_id]
        guardrail = self._guardrail_cache[case_id]
        run = self._sandbox_run[case_id]
        ctx = {
            "rootCause": verdict.rootCauseText,
            "counterfactualConfirmed": verdict.counterfactual.confirmed,
            "rehearsal": {"misbehaviorCleared": run.misbehaviorCleared,
                          "taskStillCompletes": run.taskStillCompletes},
            "guardrail": guardrail.to_dict(),
            "cedar": guardrail.to_cedar(),
            "blastRadius": "1 tool on {} sessions touching untrusted content".format(guardrail.agentId),
        }
        self._emit("ApprovalRequested", case_id, context=ctx)
        return ctx

    def approve(self, case_id: str, approver: str) -> Token:
        """The human-approval path — the ONLY holder of KEY_B."""
        canonical = self._canonical[case_id]
        token_b = self.keyring.approval_signer.sign_approval(canonical, approver)
        self.cases.put(case_id, "APPROVAL", {"approver": approver, "decision": "approved"})
        self._token_b = getattr(self, "_token_b", {})
        self._token_b[case_id] = token_b
        self._emit("ApprovalGranted", case_id, approver=approver)
        return token_b

    def reject(self, case_id: str, approver: str) -> None:
        self.cases.put(case_id, "APPROVAL", {"approver": approver, "decision": "rejected"})
        self.cases.set_status(case_id, Status.REJECTED)
        self._emit("ApprovalRejected", case_id, approver=approver)

    # ------------------------------------------------------------------ deploy
    def deploy(self, case_id: str, token_a=_UNSET, token_b=_UNSET,
               guardrail: Optional[Guardrail] = None,
               verdict: Optional[Verdict] = None) -> ActuationResult:
        """Actuator verifies both tokens then applies. Pass token_a=None
        explicitly to simulate the stripped-rehearsal demo climax; omit an
        argument (leave it _UNSET) to use the case's stored token."""
        self.cases.set_status(case_id, Status.EXECUTING)
        guardrail = guardrail or self._guardrail_cache[case_id]
        verdict = verdict or self._verdict_cache[case_id]
        ta = self._token_a.get(case_id) if token_a is _UNSET else token_a
        tb = getattr(self, "_token_b", {}).get(case_id) if token_b is _UNSET else token_b

        result = self.actuator.apply(guardrail, verdict, ta, tb)
        self.cases.put(case_id, "ACTUATION", result.to_dict())
        if result.applied:
            self.cases.set_status(case_id, Status.RESOLVED)
            self._emit("GuardrailApplied", case_id, guardrailId=result.guardrail_id,
                       rollbackToken=result.rollback_token)
        else:
            self.cases.set_status(case_id, Status.REFUSED)
            self._emit("ActuationRefused", case_id, reason=result.reason)
        return result

    def deploy_unsafe(self, case_id: str) -> ActuationResult:
        """THE CLIMAX: attempt to deploy while stripping the rehearsal token."""
        return self.deploy(case_id, token_a=None)  # explicitly stripped

    # ----------------------------------------------- re-run attack vs guardrail
    def rerun_against_policy(self, trace: SessionTrace) -> Dict[str, Any]:
        """Replay the attack against the now-active production policy."""
        from . import agent_harness
        active = self.policy.active_guardrails(trace.agentId)
        guardrail = active[0] if active else None
        result = agent_harness.replay(trace, guardrail=guardrail)
        return {
            "executed": result.emitted(),
            "attackBlocked": not result.misbehavior_fires(trace.signature),
            "guardrailActive": guardrail.guardrailId if guardrail else None,
        }
