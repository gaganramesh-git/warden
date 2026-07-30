#!/usr/bin/env python3
"""
WARDEN — demo/run_demo.py
=========================
Drives the four-minute demo from the real core (no mocks, real Ed25519 gate)
and narrates each beat to the terminal:

  1. the disaster (agent, no WARDEN, issues a fraudulent refund)
  2. the catch (injection detected, refund frozen)
  3. the proof (counterfactual replay — remove the poison, attack vanishes)
  4. the fix + validation (guardrail rehearsed, token A signed)
  5. the gate + approval (human signs token B, actuator verifies both, deploys)
  6. the re-run (attack now blocked at the door)
  7. THE CLIMAX (strip token A -> actuator hard-refuses, mutates nothing)
  8. the number (offline eval: 94% RCA / 100% effective / 0 unauthorized)

    python3 demo/run_demo.py            # full narrated run
    python3 demo/run_demo.py --ui       # also (re)build ui/demo_data.js
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.contracts import SessionTrace  # noqa: E402
from core.orchestrator import WardenEngine  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")

# ---- tiny ANSI helpers ---------------------------------------------------- #
class C:
    R = "\033[0m"; B = "\033[1m"; DIM = "\033[2m"
    RED = "\033[38;5;203m"; GRN = "\033[38;5;79m"
    AMB = "\033[38;5;179m"; IND = "\033[38;5;141m"
    SLATE = "\033[38;5;66m"; PAPER = "\033[38;5;223m"


def hr(char="─", n=64):
    print(C.SLATE + char * n + C.R)


def beat(title, t):
    print()
    hr("━")
    print("{}{}  ·  {}{}".format(C.B, title, C.DIM + t, C.R))
    hr("━")


def pause(s=0.0):
    if s and sys.stdout.isatty():
        time.sleep(s)


def short(sig: str, n=16) -> str:
    return sig[:n] + "…"


def main():
    build_ui = "--ui" in sys.argv
    slow = "--slow" in sys.argv
    d = (lambda s: pause(s if slow else 0))

    hero = SessionTrace.from_dict(json.load(open(os.path.join(FIX, "hero_attack.json"))))
    eng = WardenEngine(policy_file=None)

    print()
    print(C.B + C.IND + "  WARDEN" + C.R + C.DIM + "  ·  antivirus for autonomous AI agents" + C.R)
    print(C.DIM + "  provable cause · unforgeable fix · local mode (real Ed25519 gate)" + C.R)

    # -- BEAT 1 — THE DISASTER ---------------------------------------------- #
    beat("1 · THE DISASTER — a support agent with no WARDEN", "0:00")
    print("  agent: {}support-agent{}  tools: lookup_account, issue_refund".format(C.B, C.R))
    print("  a customer message hides an instruction inside a knowledge-base doc…")
    d(1.0)
    disaster = eng.run_unprotected(hero)
    for c in disaster["executed"]:
        color = C.RED if c["name"] == "issue_refund" else C.SLATE
        print("    {}→ {}({}){}".format(color, c["name"], _args(c["args"]), C.R))
    print("  {}✗ EXECUTED. $9,400 wired to acct_attacker_99. No human saw it.{}".format(C.RED + C.B, C.R))

    # -- BEAT 2 — THE CATCH ------------------------------------------------- #
    beat("2 · THE CATCH — same attack, WARDEN on", "0:40")
    cid = eng.open_case(hero, "support-agent")
    meta = eng.cases.get(cid, "META")
    print("  {}⚑ INJECTION DETECTED{} — the refund call is frozen, not executed.".format(C.RED + C.B, C.R))
    print("    case {}  type={}  severity={}".format(cid, meta["type"], meta["severity"]))
    print("    signature: sensitive call {}{}{} introduced by input #{}".format(
        C.B, meta["signature"]["sensitiveCall"], C.R, meta["signature"]["introducedBy"]))

    # -- BEAT 3 — THE PROOF ------------------------------------------------- #
    beat("3 · THE PROOF — counterfactual replay (not an opinion)", "1:05")
    verdict = eng.diagnose(cid)
    print("  four evidence partitions, each on a disjoint slice:")
    for sk, item in sorted(eng.cases.case(cid).items()):
        if sk.startswith("HYP#"):
            print("    {}[{}]{} {:<12} blames #{:<2} conf {:.2f}  {}{}{}".format(
                C.SLATE, item["gen"], C.R, item["evidenceSlice"],
                item["suspectFactor"], item["confidence"], C.DIM, item["evidence"][:44], C.R))
    d(0.8)
    cf = verdict.counterfactual
    print()
    print("  strike input #{} → replay the exact session → {}the attack VANISHES{}".format(
        cf.factor, C.GRN + C.B, C.R))
    print("  {}✓ CAUSE CONFIRMED{}: {}  (confidence {:.2f})".format(
        C.GRN + C.B, C.R, verdict.rootCauseText, verdict.confidence))

    # -- BEAT 4 — THE FIX + VALIDATION -------------------------------------- #
    beat("4 · THE FIX — proven the same way", "1:25")
    g = eng._guardrail_cache[cid]
    print("  proposed guardrail: {}".format(g.description))
    print(C.DIM + "    " + g.to_cedar().replace("\n", "\n    ") + C.R)
    token_a = eng.validate_and_sign(cid)
    run = eng._sandbox_run[cid]
    print("  rehearsal replay → misbehavior cleared={}  legit task still completes={}".format(
        run.misbehaviorCleared, run.taskStillCompletes))
    print("  {}◆ REHEARSAL SEAL{} signed with KEY_A  sig {}{}{}".format(
        C.IND + C.B, C.R, C.IND, short(token_a.signature), C.R))

    # -- BEAT 5 — THE GATE + APPROVAL --------------------------------------- #
    beat("5 · THE GATE — nothing ships on trust", "2:00")
    eng.request_approval(cid)
    print("  operator reviews cause + counterfactual + rehearsal + blast radius…")
    token_b = eng.approve(cid, "sec-lead@org")
    print("  {}◆ HUMAN SEAL{} signed with KEY_B by {}  sig {}{}{}".format(
        C.IND + C.B, C.R, token_b.approver, C.IND, short(token_b.signature), C.R))
    result = eng.deploy(cid)
    print("  actuator verifies BOTH signatures + all bindings → {}✓ GUARDRAIL DEPLOYED{}".format(
        C.GRN + C.B, C.R))
    print("    rollback token: {}".format(result.rollback_token))

    # -- BEAT 6 — THE RE-RUN ------------------------------------------------ #
    beat("6 · THE RE-RUN — attack now blocked at the door", "2:30")
    rerun = eng.rerun_against_policy(hero)
    print("  replay the same attack against the live policy:")
    print("    executed: {}   attack blocked: {}{}{}".format(
        rerun["executed"], C.GRN + C.B, rerun["attackBlocked"], C.R))

    # -- BEAT 7 — THE CLIMAX ------------------------------------------------ #
    beat("7 · THE CLIMAX — strip the rehearsal signature", "2:35")
    cid2 = eng.open_case(hero, "support-agent")
    eng.diagnose(cid2); eng.validate_and_sign(cid2)
    eng.request_approval(cid2); eng.approve(cid2, "sec-lead@org")
    before = eng.policy.snapshot()
    print("  watch me deploy a fix that skips the rehearsal…")
    d(1.0)
    refusal = eng.deploy_unsafe(cid2)
    after = eng.policy.snapshot()
    print()
    print("  " + C.RED + C.B + "╔" + "═" * 58 + "╗" + C.R)
    print("  " + C.RED + C.B + "║  ⛒ ACTUATION REFUSED — {:<33}║".format(refusal.reason) + C.R)
    print("  " + C.RED + C.B + "╚" + "═" * 58 + "╝" + C.R)
    print("  state unchanged: {}{}{}".format(C.B, before == after, C.R))
    print("  {}the actuator can CHECK signatures — it cannot FORGE them.{}".format(C.DIM, C.R))

    # -- BEAT 8 — THE NUMBER ------------------------------------------------ #
    beat("8 · THE NUMBER — offline eval, 50 injected attacks", "3:15")
    from eval.harness import run_eval
    rep = run_eval()
    print("    {}{:.0%}{} correct root cause (first diagnosis)".format(C.B + C.GRN, rep["rcaAccuracy"], C.R))
    print("    {}{:.0%}{} of deployed guardrails cleared their attack".format(C.B + C.GRN, rep["guardrailEffectiveness"], C.R))
    print("    {}{}{}  unauthorized actions across every run".format(C.B + C.GRN, rep["unauthorizedActions"], C.R))
    print()
    print("  " + C.DIM + "Everyone's shipping agents. Almost no one can prove why one broke" + C.R)
    print("  " + C.DIM + "or guarantee a fix is safe. WARDEN does both." + C.R)
    hr("━")

    if build_ui:
        from demo.build_ui_data import build
        path = build()
        print("\n  UI data written → {}".format(path))
        print("  open ui/index.html in a browser for the visual console.")


def _args(args):
    return ", ".join("{}={}".format(k, v) for k, v in args.items())


if __name__ == "__main__":
    main()
