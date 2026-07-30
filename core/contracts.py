"""
WARDEN — contracts.py
=====================
The frozen data shapes and domain events every service integrates against.
(Build brief §7: "Freeze contracts.py in the first hour.")

Nothing here imports another WARDEN module. These are pure, framework-free
dataclasses so the same objects flow through local mode (in-process) and AWS
mode (EventBridge/DynamoDB) unchanged.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Canonical JSON — the single source of truth for every hash and signature.
# Sorted keys, no whitespace, UTF-8. If this ever changes, every signature and
# hash in the system changes with it, so it is defined exactly once, here.
# --------------------------------------------------------------------------- #
def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(obj: Any) -> bytes:
    return canonical_json(obj).encode("utf-8")


def new_id(prefix: str) -> str:
    return "{}_{}".format(prefix, uuid.uuid4().hex[:8])


def now_ts() -> float:
    return time.time()


# --------------------------------------------------------------------------- #
# Case status enum (Backend Schema §2)
# --------------------------------------------------------------------------- #
class Status:
    DETECTED = "DETECTED"
    DIAGNOSING = "DIAGNOSING"
    DIAGNOSED = "DIAGNOSED"
    VALIDATING = "VALIDATING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    ROLLED_BACK = "ROLLED_BACK"
    REJECTED = "REJECTED"
    REFUSED = "REFUSED"


# --------------------------------------------------------------------------- #
# Session trace — the recorded agent run; the source of truth for replay.
# (Backend Schema §3)
# --------------------------------------------------------------------------- #
@dataclass
class Step:
    i: int
    role: str                                   # user | retrieved | assistant | tool
    content: Optional[str] = None
    source: Optional[str] = None                # e.g. "kb_doc_42" for retrieved
    trusted: bool = True                        # False => untrusted external content
    reasoning: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None  # {"name","args"}
    tool: Optional[str] = None                  # for role == "tool"
    output: Optional[Dict[str, Any]] = None     # recorded tool output (for replay)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Signature:
    """The misbehavior signature: which sensitive call fired + which input
    introduced it. Small and structured on purpose (Detector DoD)."""
    sensitiveCall: str
    introducedBy: int                           # step index of the introducing input

    def to_dict(self) -> Dict[str, Any]:
        return {"sensitiveCall": self.sensitiveCall, "introducedBy": self.introducedBy}


@dataclass
class SessionTrace:
    sessionId: str
    agentId: str
    steps: List[Step]
    signature: Optional[Signature] = None       # ground-truth label (fixtures only)
    task_intent: Optional[str] = None           # the legitimate task, e.g. "lookup_account"

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SessionTrace":
        steps = [Step(**s) for s in d["steps"]]
        sig = d.get("signature")
        return SessionTrace(
            sessionId=d["sessionId"],
            agentId=d["agentId"],
            steps=steps,
            signature=Signature(**sig) if sig else None,
            task_intent=d.get("task_intent"),
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "sessionId": self.sessionId,
            "agentId": self.agentId,
            "steps": [s.to_dict() for s in self.steps],
        }
        if self.signature:
            out["signature"] = self.signature.to_dict()
        if self.task_intent:
            out["task_intent"] = self.task_intent
        return out

    def clone(self) -> "SessionTrace":
        return SessionTrace.from_dict(self.to_dict())


# --------------------------------------------------------------------------- #
# Guardrail — the deployable fix (Backend Schema §8)
# --------------------------------------------------------------------------- #
@dataclass
class Guardrail:
    guardrailId: str
    agentId: str
    when: Dict[str, Any]                         # e.g. {"sessionTouchesUntrusted": True}
    block: Dict[str, Any]                        # e.g. {"tool": "issue_refund"}
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "guardrailId": self.guardrailId,
            "agentId": self.agentId,
            "when": self.when,
            "block": self.block,
            "description": self.description,
        }

    def to_cedar(self) -> str:
        """AWS-mode representation (via AgentCore Policy). Shown in the console."""
        tool = self.block.get("tool", "*")
        cond = "context.session.touched_untrusted == true"
        return (
            'forbid(principal, action == Action::"{}", resource)\n'
            "when {{ {} }};".format(tool, cond)
        )

    # plan_hash is computed over the canonical guardrail so a signature binds to
    # the *exact* fix that gets deployed.
    def plan_hash(self) -> str:
        import hashlib
        return hashlib.sha256(canonical_bytes(self.to_dict())).hexdigest()


# --------------------------------------------------------------------------- #
# Diagnosis artifacts
# --------------------------------------------------------------------------- #
@dataclass
class Hypothesis:
    gen: str                                    # A | B | C | D
    evidenceSlice: str                          # tool_io | instructions | retrieved | reasoning
    suspectFactor: int                          # step index it blames
    confidence: float
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Counterfactual:
    factor: int                                 # step index removed
    sandboxRunId: str
    confirmed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Verdict:
    rootCause: int                              # step index confirmed as cause
    rootCauseText: str
    confidence: float
    counterfactual: Counterfactual
    rankedCauses: List[int]
    recommendedGuardrailId: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["counterfactual"] = self.counterfactual.to_dict()
        return d

    # verdict_hash binds a signature to this specific verdict.
    def hash(self) -> str:
        import hashlib
        payload = {
            "rootCause": self.rootCause,
            "confidence": round(self.confidence, 6),
            "counterfactual": self.counterfactual.to_dict(),
        }
        return hashlib.sha256(canonical_bytes(payload)).hexdigest()


# --------------------------------------------------------------------------- #
# Sandbox result
# --------------------------------------------------------------------------- #
@dataclass
class SandboxRun:
    sandboxRunId: str
    mode: str                                   # falsify | validate
    misbehaviorCleared: bool
    taskStillCompletes: Optional[bool] = None
    emittedToolCalls: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# --------------------------------------------------------------------------- #
# Domain events (Backend Schema §4). One envelope, typed payloads.
# --------------------------------------------------------------------------- #
@dataclass
class Event:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    caseId: Optional[str] = None
    agentId: Optional[str] = None
    sessionId: Optional[str] = None
    eventId: str = field(default_factory=lambda: new_id("evt"))
    occurredAt: float = field(default_factory=now_ts)
    schemaVersion: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
