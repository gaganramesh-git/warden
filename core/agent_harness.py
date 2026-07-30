"""
WARDEN — agent_harness.py  (BUILD FIRST — determinism is make-or-break)
======================================================================
The monitored demo agent and the deterministic replay loop.

The agent is a customer-support agent that can `lookup_account` and
`issue_refund`. In production this is a temperature-0 Bedrock (Claude) tool-
calling loop whose tool outputs are *recorded*, so a replay re-runs the exact
loop with the recorded outputs served back and only the mutation under test
varying. For a stage demo that can never flake, WARDEN's local mode uses a
*deterministic policy interpreter* over the recorded trace instead of a live
model — same contract, zero nondeterminism, no network. (Labeled clearly:
this is a simulated agent; the replay *engine* and everything downstream of it
is the real system.)

The load-bearing invariant (Build brief §6) is the misbehavior *signature*, not
the transcript: a control replay reproduces the signature; a mutated replay
(remove the poisoned step, or turn a guardrail on) flips it. Both `falsify` and
`validate` in sandbox.py are built on `replay()` below.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .contracts import Guardrail, SessionTrace, Step

SENSITIVE_TOOLS = {"issue_refund"}

# Directive patterns the agent will act on. The vulnerability being demonstrated
# is that the base agent treats ANY content — trusted or not — as instructions.
_REFUND_RE = re.compile(
    r"(?:issue|process|send|give|authorize|grant)\s+(?:a\s+)?(?:full\s+)?refund"
    r"|refund\s+(?:of\s+)?\$?\s*[\d,]+"
    r"|wire\s+\$?\s*[\d,]+",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(r"\$?\s*([\d,]{2,})")
_ACCT_RE = re.compile(r"(acct[_a-z0-9]+|account\s+[a-z0-9_]+)", re.IGNORECASE)
_LOOKUP_RE = re.compile(r"(look ?up|check|status of|where is|find).{0,40}"
                        r"(order|account|refund|balance)", re.IGNORECASE)


@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]
    introducedBy: int          # which step's content caused this call
    blocked: bool = False      # set True if an active guardrail vetoed it


@dataclass
class ReplayResult:
    session_id: str
    tool_calls: List[ToolCall]
    touched_untrusted: bool

    def emitted(self) -> List[str]:
        """Tool calls that actually executed (were not blocked)."""
        return [c.name for c in self.tool_calls if not c.blocked]

    def signature_fires(self, sensitive_call: str) -> bool:
        """Does the misbehavior signature still appear? (i.e. did the sensitive
        call actually execute in this replay?)"""
        return sensitive_call in self.emitted()

    def task_completes(self, task_intent: Optional[str]) -> bool:
        """Did the legitimate task still succeed after the mutation?"""
        if not task_intent:
            return True
        return task_intent in self.emitted()


# --------------------------------------------------------------------------- #
# Directive extraction — a pure, deterministic function of an INPUT step's
# content. Only external inputs (user + retrieved content) are treated as
# sources of directives. The agent's own reasoning/tool_calls are OUTPUTS and
# are re-derived on every replay — never replayed from the recording — so a
# counterfactual is meaningful: remove the poisoned input and the agent no
# longer produces the malicious call, because that call was its consequence.
# --------------------------------------------------------------------------- #
_DOLLAR_RE = re.compile(r"\$\s*([\d,]{2,})")


def _extract_calls_from_step(step: Step, recorded_refund_args: Dict[str, Any]) -> List[ToolCall]:
    calls: List[ToolCall] = []
    text = step.content or ""
    if not text:
        return calls

    if _LOOKUP_RE.search(text):
        calls.append(ToolCall("lookup_account", {"by": "session"}, introducedBy=step.i))

    if _REFUND_RE.search(text):
        # Prefer the concrete target the attacker actually specified (recovered
        # from the recorded tool call), then a $-prefixed amount, then any number.
        amount = recorded_refund_args.get("amount")
        to = recorded_refund_args.get("to")
        if amount is None:
            m = _DOLLAR_RE.search(text) or _AMOUNT_RE.search(text)
            if m:
                amount = int(m.group(1).replace(",", ""))
        if to is None:
            m = _ACCT_RE.search(text)
            if m:
                to = m.group(1)
        calls.append(ToolCall(
            "issue_refund",
            {"amount": amount, "to": to},
            introducedBy=step.i,
        ))
    return calls


def _guardrail_blocks(guardrail: Optional[Guardrail], call: ToolCall,
                      touched_untrusted: bool) -> bool:
    if guardrail is None:
        return False
    if guardrail.block.get("tool") != call.name:
        return False
    when = guardrail.when
    if when.get("sessionTouchesUntrusted") and not touched_untrusted:
        return False
    return True


# --------------------------------------------------------------------------- #
# The replay engine.
# --------------------------------------------------------------------------- #
def replay(trace: SessionTrace,
           drop_step: Optional[int] = None,
           guardrail: Optional[Guardrail] = None) -> ReplayResult:
    """Deterministically re-run the agent over the recorded trace.

    Exactly one thing varies between a control replay and a mutated one:
      * drop_step  -> remove that step before re-deriving behavior  (falsify)
      * guardrail  -> evaluate the guardrail against each tool call  (validate)

    Determinism: this is a pure function of (trace, drop_step, guardrail). No
    clocks, no RNG, no network. Run it a thousand times, get the same result.
    """
    # Recover the concrete refund target the attacker specified, from any
    # recorded refund tool_call. This is the ONE thing we read from the recorded
    # agent output — the args, never the decision to call it.
    recorded_refund_args: Dict[str, Any] = {}
    for s in trace.steps:
        if s.tool_call and s.tool_call.get("name") == "issue_refund":
            recorded_refund_args = dict(s.tool_call.get("args", {}))
            break

    # Only external inputs drive the agent. Assistant/tool steps are outputs.
    inputs = [s for s in trace.steps
              if s.role in ("user", "retrieved")
              and not (drop_step is not None and s.i == drop_step)]

    touched_untrusted = any((s.trusted is False) for s in inputs)

    calls: List[ToolCall] = []
    for step in inputs:
        for call in _extract_calls_from_step(step, recorded_refund_args):
            if _guardrail_blocks(guardrail, call, touched_untrusted):
                call.blocked = True
            calls.append(call)

    # De-duplicate identical (name) executions while preserving first-seen order,
    # so "task completes" and "signature fires" reason over distinct actions.
    seen = set()
    deduped: List[ToolCall] = []
    for c in calls:
        key = (c.name, c.blocked)
        if key in seen and c.name in {"lookup_account", "issue_refund"}:
            continue
        seen.add(key)
        deduped.append(c)

    return ReplayResult(trace.sessionId, deduped, touched_untrusted)


def record_control(trace: SessionTrace) -> ReplayResult:
    """The 'production' run with no mutation: what the agent actually did."""
    return replay(trace, drop_step=None, guardrail=None)
