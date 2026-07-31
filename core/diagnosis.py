"""
WARDEN — diagnosis.py
=====================
N=4 hypothesis generators, each seeing a DISJOINT slice of the trace so none
can anchor on another's read:

  A · tool I/O only          (sees tool calls + outputs)
  B · instruction chain only (sees user + assistant instruction content)
  C · retrieved content only (sees untrusted external steps)
  D · reasoning steps only   (sees assistant reasoning)

Then ONE critic pass scores and prunes to the top candidate. Then Diagnosis
asks the Sandbox to FALSIFY the top candidate: remove it, replay, does the
misbehavior clear? The counterfactual is the arbiter — never another LLM. If
the top candidate fails to falsify, walk down the ranked list (bounded).

In AWS mode each generator/critic is a temperature-0 Bedrock (Claude) call over
its evidence slice. Local mode uses deterministic heuristic analyzers with the
identical contract, so the stage demo is reproducible. The *judgment* of truth
is empirical (the replay), not the analyzer — so this stays honest.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .contracts import (
    Counterfactual, Guardrail, Hypothesis, SessionTrace, Verdict, new_id,
)
from .detector import _INJECTION_MARKERS
from .sandbox import Sandbox

_REFUND_MENTION = re.compile(r"refund|wire|transfer|\$", re.IGNORECASE)


def _slice_steps(trace: SessionTrace, roles, need_untrusted=None, need_reasoning=False):
    out = []
    for s in trace.steps:
        if s.role not in roles:
            continue
        if need_untrusted is True and s.trusted is not False:
            continue
        if need_reasoning and not s.reasoning:
            continue
        out.append(s)
    return out


# --------------------------------------------------------------------------- #
# The four partitioned generators. Each returns at most one hypothesis over its
# OWN slice only. Confidences are deliberately shaped so no single generator is
# authoritative; the critic reconciles them and the replay decides.
# --------------------------------------------------------------------------- #
def _gen_A_tool_io(trace: SessionTrace) -> Optional[Hypothesis]:
    # Sees only tool calls/outputs. Can see THAT a refund fired, blames the call
    # itself — a proximate effect, not the root. Low-ish confidence.
    for s in trace.steps:
        if s.tool_call and s.tool_call.get("name") == "issue_refund":
            return Hypothesis("A", "tool_io", s.i, 0.45,
                              "issue_refund executed with args {}".format(s.tool_call.get("args")))
        if s.role == "tool" and s.tool == "issue_refund":
            return Hypothesis("A", "tool_io", s.i, 0.40,
                              "refund tool returned success")
    return None


def _gen_B_instructions(trace: SessionTrace) -> Optional[Hypothesis]:
    # Sees user + assistant instruction content. The legit user message rarely
    # asks for a refund; if it does not, B has weak signal and blames the user
    # turn at low confidence (a plausible-but-wrong candidate -> keeps RCA < 100%).
    steps = _slice_steps(trace, roles={"user", "assistant"})
    for s in steps:
        text = "\n".join(t for t in (s.content, s.reasoning) if t)
        if _INJECTION_MARKERS.search(text):
            return Hypothesis("B", "instructions", s.i, 0.70,
                              "instruction-like override phrasing in {} turn".format(s.role))
    for s in steps:
        if s.role == "user" and _REFUND_MENTION.search(s.content or ""):
            return Hypothesis("B", "instructions", s.i, 0.30,
                              "user turn mentions a refund")
    return None


def _gen_C_retrieved(trace: SessionTrace) -> Optional[Hypothesis]:
    # Sees ONLY untrusted external content. This is where an injection lives, so
    # when it finds an override marker in untrusted content it is confident — but
    # it cannot see whether that content actually drove the tool call (that is
    # what the counterfactual verifies).
    steps = _slice_steps(trace, roles={"retrieved", "user"}, need_untrusted=True)
    best = None
    for s in steps:
        text = "\n".join(t for t in (s.content, s.reasoning) if t)
        if _INJECTION_MARKERS.search(text):
            conf = 0.88 + (0.05 if _REFUND_MENTION.search(text) else 0.0)
            cand = Hypothesis("C", "retrieved", s.i, min(conf, 0.95),
                              "untrusted content ({}) carries an injected instruction"
                              .format(s.source or "external"))
            if best is None or cand.confidence > best.confidence:
                best = cand
    return best


def _gen_D_reasoning(trace: SessionTrace) -> Optional[Hypothesis]:
    # Sees only assistant reasoning. Blames the reasoning step that decided to
    # refund — proximate, not root.
    for s in trace.steps:
        if s.reasoning and _REFUND_MENTION.search(s.reasoning):
            return Hypothesis("D", "reasoning", s.i, 0.50,
                              "reasoning step concludes to issue a refund")
    return None


GENERATORS = [_gen_A_tool_io, _gen_B_instructions, _gen_C_retrieved, _gen_D_reasoning]


# --------------------------------------------------------------------------- #
# Critic — reconciles the four disjoint reads into one ranked list.
# Prior: a ROOT cause is an untrusted INPUT that precedes the sensitive call,
# not the call/reasoning it produced. So untrusted-origin candidates are up-
# weighted and tool/reasoning effects down-weighted.
# --------------------------------------------------------------------------- #
def _critic(trace: SessionTrace, hyps: List[Hypothesis]) -> List[Hypothesis]:
    step_by_i = {s.i: s for s in trace.steps}

    def score(h: Hypothesis) -> float:
        s = step_by_i.get(h.suspectFactor)
        adj = h.confidence
        if s is not None and s.trusted is False:
            adj += 0.15                     # untrusted inputs are prime suspects
        if h.evidenceSlice in ("tool_io", "reasoning"):
            adj -= 0.10                     # these are effects, not causes
        return adj

    ranked = sorted(hyps, key=score, reverse=True)
    return ranked


# --------------------------------------------------------------------------- #
# Public entry point.
# --------------------------------------------------------------------------- #
class Diagnosis:
    def __init__(self, sandbox: Sandbox):
        self.sandbox = sandbox

    def diagnose(self, trace: SessionTrace, agent_id: str) -> Tuple[Verdict, List[Hypothesis], object]:
        # 1. run the four partitioned generators
        hyps: List[Hypothesis] = []
        for g in GENERATORS:
            h = g(trace)
            if h:
                hyps.append(h)

        # 2. critic ranks
        ranked = _critic(trace, hyps)
        ranked_factors = [h.suspectFactor for h in ranked]

        # 3. counterfactual is the arbiter: falsify down the ranked list until
        #    one candidate genuinely clears the misbehavior (bounded).
        confirmed_run = None
        confirmed_factor = None
        confirmed_conf = 0.0
        tried = set()
        for h in ranked[:4]:
            tried.add(h.suspectFactor)
            run = self.sandbox.falsify(trace, h.suspectFactor)
            if run.misbehaviorCleared:
                confirmed_run = run
                confirmed_factor = h.suspectFactor
                confirmed_conf = h.confidence
                break

        # Bounded safety net: if the ranked hypotheses did not falsify (e.g. the
        # top guess was a decoy), sweep the remaining untrusted inputs — still
        # empirical, still the replay deciding. This keeps a wrong first guess
        # from ever shipping the wrong (or no) guardrail.
        if confirmed_run is None:
            for s in trace.steps:
                if s.trusted is False and s.i not in tried:
                    run = self.sandbox.falsify(trace, s.i)
                    if run.misbehaviorCleared:
                        confirmed_run = run
                        confirmed_factor = s.i
                        confirmed_conf = 0.75  # recovered by sweep, not first-guess
                        break

        if confirmed_run is None:
            # Nothing cleared — emit the top guess unconfirmed (escalate).
            top = ranked[0] if ranked else Hypothesis("C", "retrieved", -1, 0.0, "none")
            run = self.sandbox.falsify(trace, top.suspectFactor)
            confirmed_run = run
            confirmed_factor = top.suspectFactor
            confirmed_conf = top.confidence

        # 4. build the recommended guardrail + verdict — shaped by the failure
        #    mode: injection -> block the tool on untrusted sessions; loop ->
        #    rate-limit the tool to one call per session.
        sig = trace.signature
        sensitive = sig.sensitiveCall if sig else "issue_refund"
        if sig and sig.kind == "loop":
            guardrail = Guardrail(
                guardrailId=new_id("g"), agentId=agent_id,
                when={"sessionTouchesUntrusted": True},
                block={"tool": sensitive, "maxCalls": 1},
                description="Rate-limit {} to one call per session (breaks the loop).".format(sensitive),
            )
        else:
            guardrail = Guardrail(
                guardrailId=new_id("g"), agentId=agent_id,
                when={"sessionTouchesUntrusted": True},
                block={"tool": sensitive},
                description="Block {} on any session that ingested untrusted content.".format(sensitive),
            )

        cf = Counterfactual(
            factor=confirmed_factor,
            sandboxRunId=confirmed_run.sandboxRunId,
            confirmed=confirmed_run.misbehaviorCleared,
        )
        root_step = {s.i: s for s in trace.steps}.get(confirmed_factor)
        root_text = "injected instruction in {}".format(
            (root_step.source if root_step and root_step.source else "input #{}".format(confirmed_factor))
        )
        verdict = Verdict(
            rootCause=confirmed_factor,
            rootCauseText=root_text,
            confidence=round(min(confirmed_conf + (0.15 if cf.confirmed else 0), 0.99), 2),
            counterfactual=cf,
            rankedCauses=ranked_factors,
            recommendedGuardrailId=guardrail.guardrailId,
        )
        return verdict, ranked, guardrail
