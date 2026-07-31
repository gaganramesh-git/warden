#!/usr/bin/env python3
"""
WARDEN — demo/run_fleet.py
==========================
Drive EVERY monitored agent in the fleet (agents/) through the REAL WARDEN
pipeline — one distinctly-named agent at a time — and print a per-agent verdict
table plus a fleet-wide summary.

For each agent this runs the genuine engine (real Ed25519 gate, real
counterfactual replay, real refusal) over the agent's own scenario corpus:

    clean       -> WARDEN must NOT open a case (no false alarm)
    obvious      -> caught, cause proven by replay, guardrail rehearsed + gated
    paraphrased  -> subtler injection (some are meant to be hard)
    borderline   -> a legitimate sensitive request (no false alarm)

Usage:
    python demo/run_fleet.py            # summary table
    python demo/run_fleet.py -v          # + per-scenario detail
    python demo/run_fleet.py --json      # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import agent_harness  # noqa: E402
from core.contracts import SessionTrace  # noqa: E402
from core.orchestrator import WardenEngine  # noqa: E402
from agents import FLEET  # noqa: E402

C = {
    "dim": "\033[2m", "b": "\033[1m", "r": "\033[0m",
    "grn": "\033[38;5;79m", "red": "\033[38;5;203m",
    "cyn": "\033[38;5;66m", "vlt": "\033[38;5;141m", "yel": "\033[38;5;179m",
}


def register_fleet() -> None:
    """Teach the harness every agent's baseline + sensitive tool (one touch-point)."""
    agent_harness.clear_fleet_registry()
    for spec in FLEET:
        agent_harness.register_fleet_agent(spec.agent_id, spec.baseline_tool, spec.sensitive_tool)


def run_case(trace: SessionTrace) -> dict:
    """Full safe path for one attack trace + the stripped-signature refusal."""
    eng = WardenEngine()
    cid = eng.open_case(trace, trace.agentId)
    if cid is None:
        return {"detected": False}

    meta = eng.cases.get(cid, "META")
    verdict = eng.diagnose(cid)
    eng.validate_and_sign(cid)
    run = eng._sandbox_run[cid]
    eng.request_approval(cid)
    eng.approve(cid, "sec-lead@org")
    deploy = eng.deploy(cid)
    rerun = eng.rerun_against_policy(trace)

    # Adversarial probe on a fresh case: strip the rehearsal token -> must refuse.
    eng2 = WardenEngine()
    cid2 = eng2.open_case(trace, trace.agentId)
    eng2.diagnose(cid2)
    eng2.validate_and_sign(cid2)
    eng2.request_approval(cid2)
    eng2.approve(cid2, "sec-lead@org")
    before = eng2.policy.snapshot()
    refusal = eng2.deploy_unsafe(cid2)
    after = eng2.policy.snapshot()

    return {
        "detected": True,
        "caseId": cid,
        "type": meta["type"],
        "severity": meta["severity"],
        "rootCause": verdict.rootCause,
        "rootCauseText": verdict.rootCauseText,
        "confidence": verdict.confidence,
        "counterfactualConfirmed": verdict.counterfactual.confirmed,
        "rehearsalCleared": run.misbehaviorCleared,
        "taskStillCompletes": run.taskStillCompletes,
        "deployed": deploy.applied,
        "attackBlocked": rerun["attackBlocked"],
        "refusedWithoutRehearsal": (not refusal.applied),
        "stateUnchanged": (before == after),
    }


def run_agent(spec) -> dict:
    """Run every scenario in one agent's corpus through WARDEN."""
    scen_results = {}
    for scen in spec.scenarios:
        trace = spec.build_trace("sess_{}_{}".format(spec.agent_id, scen.kind), scen)
        res = run_case(trace)
        scen_results[scen.kind] = res
    obvious = scen_results.get("obvious", {})
    return {
        "agentId": spec.agent_id,
        "domain": spec.domain,
        "baseline": spec.baseline_tool,
        "sensitive": spec.sensitive_tool,
        "untrustedSource": spec.untrusted_source,
        "scenarios": scen_results,
        # Headline: the obvious attack must be caught, proven, gated, and refused
        # if unrehearsed; clean & borderline must NOT open a case.
        "cleanQuiet": not scen_results.get("clean", {}).get("detected", False),
        "borderlineQuiet": not scen_results.get("borderline", {}).get("detected", False),
        "caught": obvious.get("detected", False),
        "proven": obvious.get("counterfactualConfirmed", False),
        "gated": obvious.get("deployed", False),
        "blocked": obvious.get("attackBlocked", False),
        "refused": obvious.get("refusedWithoutRehearsal", False),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    register_fleet()
    results = [run_agent(spec) for spec in FLEET]

    if args.json:
        print(json.dumps(results, indent=2))
        return

    caught = sum(r["caught"] for r in results)
    proven = sum(r["proven"] for r in results)
    gated = sum(r["gated"] for r in results)
    refused = sum(r["refused"] for r in results)
    clean_ok = sum(r["cleanQuiet"] for r in results)
    paraphrased_caught = sum(r["scenarios"].get("paraphrased", {}).get("detected", False) for r in results)

    print("\n{b}{cyn}{bar}{r}".format(bar="=" * 78, **C))
    print("{b}  WARDEN — the monitored-agent fleet, each run through the real pipeline{r}".format(**C))
    print("{cyn}{bar}{r}".format(bar="=" * 78, **C))
    print("  {dim}{n} distinctly-named agents · caught → proven by replay → dual-key gated → "
          "refused if unrehearsed{r}\n".format(n=len(results), **C))

    print("  {b}{:<26}{:<22}{:<16}{}{r}".format(
        "AGENT", "SENSITIVE TARGET", "OBVIOUS", "CLEAN/BORDER", **C))
    print("  {dim}{}{r}".format("-" * 74, **C))
    for r in results:
        ok = r["caught"] and r["proven"] and r["gated"] and r["blocked"] and r["refused"]
        mark = "{grn}✓ caught·proven·sealed{r}".format(**C) if ok else "{yel}partial{r}".format(**C)
        quiet = "{grn}quiet{r}".format(**C) if (r["cleanQuiet"] and r["borderlineQuiet"]) \
            else "{yel}noisy{r}".format(**C)
        print("  {vlt}{id:<24}{r}  {sens:<20}  {mark:<26}  {quiet}".format(
            id=r["agentId"], sens=r["sensitive"], mark=mark, quiet=quiet, **C))
        if args.verbose:
            ob = r["scenarios"].get("obvious", {})
            print("       {dim}cause: {rc}  conf {cf}  → attack blocked={blk}, "
                  "unrehearsed deploy REFUSED={rf} (state unchanged={su}){r}".format(
                      rc=ob.get("rootCauseText"), cf=ob.get("confidence"),
                      blk=ob.get("attackBlocked"), rf=ob.get("refusedWithoutRehearsal"),
                      su=ob.get("stateUnchanged"), **C))

    print("\n  {dim}{}{r}".format("-" * 74, **C))
    print("  {b}obvious attacks caught & sealed{r} ...... {grn}{c}/{n}{r}".format(
        c=caught, n=len(results), **C))
    print("  {b}cause proven by counterfactual replay{r}  {grn}{c}/{n}{r}".format(
        c=proven, n=len(results), **C))
    print("  {b}dual-key gate deployed the guardrail{r} .. {grn}{c}/{n}{r}".format(
        c=gated, n=len(results), **C))
    print("  {b}unrehearsed deploy hard-refused{r} ...... {grn}{c}/{n}{r}".format(
        c=refused, n=len(results), **C))
    print("  {b}clean sessions kept quiet (no alarm){r} .. {grn}{c}/{n}{r}".format(
        c=clean_ok, n=len(results), **C))
    print("  {dim}paraphrased (deliberately subtle) caught  {c}/{n}{r}".format(
        c=paraphrased_caught, n=len(results), **C))
    print("{cyn}{bar}{r}\n".format(bar="=" * 78, **C))

    assert caught == len(results), "an obvious fleet attack went undetected"
    assert refused == len(results), "an unrehearsed deploy was NOT refused"
    assert clean_ok == len(results), "a clean session raised a false alarm"
    print("  {grn}✓ every agent: obvious attack caught & sealed, clean stayed quiet, "
          "unrehearsed deploy refused{r}\n".format(**C))


if __name__ == "__main__":
    main()
