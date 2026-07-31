#!/usr/bin/env python3
"""
WARDEN — demo/build_ui_data.py
==============================
Runs the REAL pipeline (real Ed25519 signatures, real counterfactual, real
refusal) for each demo SCENARIO and serializes everything the console needs.
The UI thus displays genuine artifacts — real signature hashes, the real
verdict, the real refusal reason — not hand-written mockups.

Output shape:
    { "scenarios": [ ScenarioData, ... ], "eval": {...}, "redteam": [...] }

    python3 demo/build_ui_data.py
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import agent_harness  # noqa: E402
from core.contracts import SessionTrace  # noqa: E402
from core.orchestrator import WardenEngine  # noqa: E402
from eval.harness import run_eval  # noqa: E402
from agents import FLEET  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
UI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")


def _tok(t):
    if t is None:
        return None
    return {
        "kind": t.kind, "keyId": t.keyId, "alg": t.alg,
        "approver": t.approver,
        "sig": t.signature,
        "sigShort": t.signature[:22] + "…",
        "nonce": t.payload.get("nonce"),
        "planHash": t.payload.get("plan_hash", "")[:16] + "…",
        "sandboxRunId": t.payload.get("sandbox_run_id"),
        "exp": t.payload.get("exp"),
    }


# --------------------------------------------------------------------------- #
# Per-scenario step narrative. Text lives in DATA; the StepGuide wires the
# action (next / gotoRefusal / restart) by beat. Each scenario supplies its own.
# --------------------------------------------------------------------------- #
def injection_steps(agent: str, sensitive: str, sink: str, amount: str) -> Dict[str, Any]:
    return {
        "disaster": {"title": "The agent was hijacked",
                     "status": "A poisoned document made the agent wire {} to {} — executed, no human in the loop.".format(amount, sink),
                     "actionLabel": "Turn WARDEN on & replay"},
        "catch": {"title": "Injection caught",
                  "status": "WARDEN intercepted the {} the instant the agent acted on untrusted content. It's frozen, not executed.".format(sensitive.replace("_", " ")),
                  "actionLabel": "Investigate — gather the evidence"},
        "evidence": {"title": "Four generators disagree",
                     "status": "Each generator blames a different step. We don't trust any of them — the replay will decide.",
                     "actionLabel": "Prove the cause by replay"},
        "proof": {"title": "Cause confirmed",
                  "status": "Remove the poisoned input, replay the exact session, and the attack vanishes. That's a proof, not a guess.",
                  "actionLabel": "Propose the fix"},
        "fix": {"title": "Guardrail written",
                "status": "WARDEN proposes a guardrail. Rehearse it in the sandbox to earn the KEY_A signature.",
                "actionLabel": "Rehearse fix → sign KEY_A"},
        "rehearsal": {"title": "Rehearsal passed · KEY_A signed",
                      "status": "Attack cleared and the legit task still works, so the sandbox signed the rehearsal seal. Now a human must approve.",
                      "actionLabel": "Approve fix → sign KEY_B"},
        "approval": {"title": "Human approved · KEY_B signed",
                     "status": "Both signatures are now present and bound to the same plan and the same rehearsal.",
                     "actionLabel": "Deploy the guardrail"},
        "deployed": {"title": "Guardrail deployed ✓",
                     "status": "Done. The actuator verified BOTH signatures and applied the fix — the attack is now blocked and your approved guardrail is live. That's the full safe path.",
                     "actionLabel": "↺ Run through again",
                     "secondaryLabel": "Optional: try a tampered deploy with NO rehearsal →"},
        "refusal": {"title": "Refused — exactly as intended",
                    "status": "This was a SEPARATE, tampered deploy with the rehearsal signature stripped out. The actuator hard-refused and changed nothing — the guardrail you approved earlier is still live and untouched. It can check proof; it can't forge it.",
                    "actionLabel": "↺ Start over",
                    "secondaryLabel": "‹ Back to the deployed fix"},
    }


def loop_steps() -> Dict[str, Any]:
    s = injection_steps("shopping-agent", "issue_refund", "", "")
    s["disaster"] = {"title": "The agent got stuck in a loop",
                     "status": "A poisoned retry instruction made the agent re-issue the same refund over and over — draining the account, no human in the loop.",
                     "actionLabel": "Turn WARDEN on & replay"}
    s["catch"] = {"title": "Loop caught",
                  "status": "WARDEN saw the same sensitive call fire again and again with zero errors — the loop signature. The runaway calls are frozen.",
                  "actionLabel": "Investigate — gather the evidence"}
    s["fix"] = {"title": "Guardrail written",
                "status": "WARDEN proposes a rate-limit guardrail (cap the call per session). Rehearse it to earn the KEY_A signature.",
                "actionLabel": "Rehearse fix → sign KEY_A"}
    return s


# --------------------------------------------------------------------------- #
# Run the full pipeline for one recorded session and serialize the case.
# --------------------------------------------------------------------------- #
def build_scenario(scenario_id: str, label: str, attack_type: str,
                   fixture: str, agent: Dict[str, Any], steps: Dict[str, Any]) -> Dict[str, Any]:
    trace = SessionTrace.from_dict(json.load(open(os.path.join(FIX, fixture))))
    return _run_pipeline(scenario_id, label, attack_type, trace, agent, steps)


def _run_pipeline(scenario_id: str, label: str, attack_type: str,
                  trace: SessionTrace, agent: Dict[str, Any],
                  steps: Dict[str, Any]) -> Dict[str, Any]:
    eng = WardenEngine()

    disaster = eng.run_unprotected(trace)
    cid = eng.open_case(trace, agent["name"])
    meta = eng.cases.get(cid, "META")
    verdict = eng.diagnose(cid)
    hyps = [h for h in (eng.cases.get(cid, "HYP#" + g) for g in ("A", "B", "C", "D")) if h]
    guardrail = eng._guardrail_cache[cid]
    token_a = eng.validate_and_sign(cid)
    run = eng._sandbox_run[cid]
    ctx = eng.request_approval(cid)
    token_b = eng.approve(cid, "sec-lead@org")
    deploy = eng.deploy(cid)
    rerun = eng.rerun_against_policy(trace)

    # climax on a fresh case so the good deploy stays applied
    cid2 = eng.open_case(trace, agent["name"])
    eng.diagnose(cid2); eng.validate_and_sign(cid2)
    eng.request_approval(cid2); eng.approve(cid2, "sec-lead@org")
    before = eng.policy.snapshot()
    refusal = eng.deploy_unsafe(cid2)
    after = eng.policy.snapshot()

    return {
        "id": scenario_id, "label": label, "attackType": attack_type,
        "agent": agent,
        "session": {
            "id": trace.sessionId,
            "steps": [s.to_dict() for s in trace.steps],
            "signature": trace.signature.to_dict() if trace.signature else meta["signature"],
        },
        "disaster": disaster,
        "steps": steps,
        "case": {
            "id": cid, "type": meta["type"], "severity": meta["severity"],
            "signature": meta["signature"], "hypotheses": hyps,
            "verdict": {
                "rootCause": verdict.rootCause, "rootCauseText": verdict.rootCauseText,
                "confidence": verdict.confidence, "rankedCauses": verdict.rankedCauses,
                "counterfactual": verdict.counterfactual.to_dict(),
            },
            "guardrail": {
                "id": guardrail.guardrailId, "description": guardrail.description,
                "json": guardrail.to_dict(), "cedar": guardrail.to_cedar(),
                "planHash": guardrail.plan_hash(),
            },
            "rehearsal": {
                "sandboxRunId": run.sandboxRunId,
                "misbehaviorCleared": run.misbehaviorCleared,
                "taskStillCompletes": run.taskStillCompletes,
                "tokenA": _tok(token_a),
            },
            "approval": {
                "approver": token_b.approver, "blastRadius": ctx["blastRadius"],
                "tokenB": _tok(token_b),
            },
            "deploy": deploy.to_dict(),
            "rerun": rerun,
            "refusal": {
                "status": refusal.status, "reason": refusal.reason,
                "stateUnchanged": before == after,
            },
        },
    }


def fleet_steps(agent_name: str, sensitive: str, source: str) -> Dict[str, Any]:
    """Per-agent step narrative for a monitored FLEET agent's injection case."""
    s = injection_steps(agent_name, sensitive, "", "")
    act = sensitive.replace("_", " ")
    s["disaster"] = {
        "title": "The agent was hijacked",
        "status": "Poisoned {} content coerced the agent into calling {} — "
                  "executed, no human in the loop.".format(source, act),
        "actionLabel": "Turn WARDEN on & replay"}
    s["catch"] = {
        "title": "Injection caught",
        "status": "WARDEN intercepted {} the instant the agent acted on untrusted "
                  "content. It's frozen, not executed.".format(act),
        "actionLabel": "Investigate — gather the evidence"}
    return s


def build_fleet_scenarios() -> List[Dict[str, Any]]:
    """One end-to-end console case per monitored agent (agents/), each distinctly
    named, each a REAL run through the live pipeline. Registered only here so the
    refund-specific hero path above is untouched."""
    out: List[Dict[str, Any]] = []
    fleet = [spec for spec in FLEET if spec.agent_id != "support-agent"]
    for spec in fleet:
        agent_harness.register_fleet_agent(spec.agent_id, spec.baseline_tool, spec.sensitive_tool)
    for spec in fleet:
        obvious = next(s for s in spec.scenarios if s.kind == "obvious")
        trace = spec.build_trace("sess_{}".format(spec.agent_id), obvious)
        agent = {
            "name": spec.agent_id,
            "purpose": "{} agent — safely runs {}; {} is the guarded high-impact action.".format(
                spec.domain[:1].upper() + spec.domain[1:], spec.baseline_tool, spec.sensitive_tool),
            "tools": [t.name for t in spec.tools],
        }
        out.append(_run_pipeline(
            "{}-injection".format(spec.agent_id),
            "{} · prompt injection".format(spec.agent_id), "injection",
            trace, agent, fleet_steps(spec.agent_id, spec.sensitive_tool, spec.untrusted_source),
        ))
    return out


def build_scenarios() -> List[Dict[str, Any]]:
    # Hero cases first (rich recorded fixtures; refund-specific replay path).
    scenarios = [
        build_scenario(
            "support-injection", "Support agent · prompt injection", "injection",
            "hero_attack.json",
            {"name": "support-agent",
             "purpose": "Customer support — looks up accounts and issues refunds.",
             "tools": ["lookup_account", "issue_refund"]},
            injection_steps("support-agent", "issue_refund", "an attacker account", "a $9,400 refund"),
        ),
    ]
    # Loop scenario (1A) — only if its fixture exists yet.
    if os.path.exists(os.path.join(FIX, "loop_attack.json")):
        scenarios.append(build_scenario(
            "support-loop", "Support agent · runaway loop", "loop",
            "loop_attack.json",
            {"name": "support-agent",
             "purpose": "Customer support — looks up accounts and issues refunds.",
             "tools": ["lookup_account", "issue_refund"]},
            loop_steps(),
        ))
    # The rest of the monitored fleet — every agent in agents/, distinctly named.
    scenarios.extend(build_fleet_scenarios())
    return scenarios


def build() -> str:
    ev = run_eval()
    data = {
        "scenarios": build_scenarios(),
        "eval": {
            "rcaAccuracy": ev["rcaAccuracy"],
            "confirmedAccuracy": ev["confirmedAccuracy"],
            "guardrailEffectiveness": ev["guardrailEffectiveness"],
            "unauthorizedActions": ev["unauthorizedActions"],
            "sessions": ev["sessions"],
            "guardrailsShipped": ev["guardrailsShipped"],
            "perAttack": ev["perAttack"],
        },
    }

    os.makedirs(UI, exist_ok=True)
    with open(os.path.join(UI, "demo_data.js"), "w") as f:
        f.write("// Generated by demo/build_ui_data.py — REAL artifacts from the live pipeline.\n")
        f.write("window.WARDEN_DATA = ")
        json.dump(data, f, indent=2)
        f.write(";\n")

    json_dir = os.path.join(UI, "src", "data")
    os.makedirs(json_dir, exist_ok=True)
    with open(os.path.join(json_dir, "warden_data.json"), "w") as f:
        json.dump(data, f, indent=2)
    return os.path.join(UI, "src", "data", "warden_data.json")


if __name__ == "__main__":
    print("wrote", build())
