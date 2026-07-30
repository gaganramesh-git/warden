"""The cryptographic gate — the moat. These tests ARE the demo climax made
runnable (Build brief §5, §9; Backend Schema §10)."""
import time

import pytest

from core.actuator import Actuator
from core.contracts import Guardrail, Verdict, Counterfactual
from core.gate import (
    ActuationRefused, Keyring, NonceLedger, build_canonical,
)
from core.store import PolicyStore


def _fixture():
    kr = Keyring()
    ledger = NonceLedger()
    verifier = kr.actuator_verifier(ledger)
    policy = PolicyStore()
    actuator = Actuator(verifier, policy)

    guardrail = Guardrail("g_1", "support-agent",
                          {"sessionTouchesUntrusted": True},
                          {"tool": "issue_refund"},
                          "Block refunds on untrusted sessions.")
    verdict = Verdict(3, "injected doc", 0.94,
                      Counterfactual(3, "sr_1", True), [3, 1], "g_1")
    canonical = build_canonical(
        session_id="s_1029", plan_hash=guardrail.plan_hash(),
        sandbox_run_id="sr_1", verdict_hash=verdict.hash(), nonce="nonce_1",
    )
    token_a = kr.sandbox_signer.sign_rehearsal(canonical)
    token_b = kr.approval_signer.sign_approval(canonical, "sec-lead@org")
    return kr, actuator, policy, guardrail, verdict, token_a, token_b, canonical


def test_gate_applies_with_both_tokens():
    _, actuator, policy, g, v, ta, tb, _ = _fixture()
    r = actuator.apply(g, v, ta, tb)
    assert r.applied and policy.is_active("g_1")


def test_gate_refuses_without_rehearsal_token():
    """THE CLIMAX: strip token_A -> refuse, and mutate NOTHING."""
    _, actuator, policy, g, v, ta, tb, _ = _fixture()
    before = policy.snapshot()
    r = actuator.apply(g, v, None, tb)
    after = policy.snapshot()
    assert r.status == "refused"
    assert "rehearsal" in r.reason
    assert before == after == {}, "state must be byte-identical after refusal"


def test_gate_refuses_without_human_token():
    _, actuator, policy, g, v, ta, tb, _ = _fixture()
    r = actuator.apply(g, v, ta, None)
    assert r.status == "refused" and not policy.is_active("g_1")


def test_gate_rejects_plan_swap():
    """token bound to plan_hash; approve plan X, apply plan Y -> refused."""
    _, actuator, policy, g, v, ta, tb, _ = _fixture()
    evil = Guardrail("g_evil", "support-agent",
                     {"sessionTouchesUntrusted": False},   # a weaker rule
                     {"tool": "nothing"}, "a bait-and-switch fix")
    r = actuator.apply(evil, v, ta, tb)
    assert r.status == "refused" and "plan hash" in r.reason
    assert not policy.is_active("g_evil")


def test_gate_rejects_verdict_swap():
    _, actuator, policy, g, v, ta, tb, _ = _fixture()
    other = Verdict(9, "different", 0.5, Counterfactual(9, "sr_9", True), [9], "g_1")
    r = actuator.apply(g, other, ta, tb)
    assert r.status == "refused" and "verdict" in r.reason


def test_gate_rejects_replay_nonce():
    """A nonce is single-use: the same approval cannot be applied twice."""
    _, actuator, policy, g, v, ta, tb, _ = _fixture()
    assert actuator.apply(g, v, ta, tb).applied
    r2 = actuator.apply(g, v, ta, tb)          # replay the exact same tokens
    assert r2.status == "refused" and "replay" in r2.reason


def test_gate_rejects_expired():
    kr = Keyring()
    verifier = kr.actuator_verifier()
    g = Guardrail("g_1", "support-agent", {"sessionTouchesUntrusted": True},
                  {"tool": "issue_refund"}, "x")
    v = Verdict(3, "x", 0.9, Counterfactual(3, "sr_1", True), [3], "g_1")
    canonical = build_canonical("s", g.plan_hash(), "sr_1", v.hash(), "n_exp",
                                exp=time.time() - 1)   # already expired
    ta = kr.sandbox_signer.sign_rehearsal(canonical)
    tb = kr.approval_signer.sign_approval(canonical, "sec-lead@org")
    with pytest.raises(ActuationRefused):
        verifier.verify(g.plan_hash(), v.hash(), ta, tb)


def test_gate_rejects_forged_signature():
    """A token signed by the WRONG key never verifies."""
    kr = Keyring()
    verifier = kr.actuator_verifier()
    g = Guardrail("g_1", "support-agent", {"sessionTouchesUntrusted": True},
                  {"tool": "issue_refund"}, "x")
    v = Verdict(3, "x", 0.9, Counterfactual(3, "sr_1", True), [3], "g_1")
    canonical = build_canonical("s", g.plan_hash(), "sr_1", v.hash(), "n1")
    # Attacker signs the "rehearsal" with KEY_B (they don't hold KEY_A).
    forged_a = kr.approval_signer.sign_rehearsal(canonical)   # keyId still says KEY_B
    tb = kr.approval_signer.sign_approval(canonical, "sec-lead@org")
    with pytest.raises(ActuationRefused):
        verifier.verify(g.plan_hash(), v.hash(), forged_a, tb)


def test_actuator_holds_no_private_keys():
    """Structural proof of 'verify-only': the Actuator's verifier exposes no
    signing capability at all."""
    kr = Keyring()
    verifier = kr.actuator_verifier()
    assert not hasattr(verifier, "sign")
    assert not hasattr(verifier, "_sk")
    # only public keys are present
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    assert isinstance(verifier.key_a_pub, Ed25519PublicKey)
    assert isinstance(verifier.key_b_pub, Ed25519PublicKey)
