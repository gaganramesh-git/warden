"""Determinism + counterfactual acceptance tests (Build brief §6, §9)."""
from core import agent_harness
from core.gate import Keyring
from core.sandbox import Sandbox


def _sandbox():
    return Sandbox(Keyring().sandbox_signer)


def test_replay_deterministic(hero):
    """Control replays reproduce the signature, byte-stable across runs."""
    results = set()
    for _ in range(25):
        r = agent_harness.replay(hero)
        results.add((r.signature_fires("issue_refund"), tuple(r.emitted())))
    assert len(results) == 1, "control replay must be deterministic"
    # and the control genuinely reproduces the misbehavior signature
    assert agent_harness.replay(hero).signature_fires("issue_refund") is True


def test_falsify_is_stable(hero):
    assert Sandbox.is_deterministic(hero, hero.signature.introducedBy, runs=10)


def test_counterfactual_proves_cause(hero):
    """Removing the injected message clears the misbehavior; removing an
    innocent message does not. This is the empirical arbiter."""
    sb = _sandbox()
    injected = hero.signature.introducedBy       # step 3 (poisoned doc)
    guilty = sb.falsify(hero, injected)
    assert guilty.misbehaviorCleared is True, "removing the poison must clear it"

    for innocent in (0,):                         # step 0 is the legit user turn
        r = sb.falsify(hero, innocent)
        assert r.misbehaviorCleared is False, "removing an innocent step must NOT clear it"


def test_clean_session_has_no_misbehavior(clean):
    r = agent_harness.replay(clean)
    assert r.signature_fires("issue_refund") is False
    assert "lookup_account" in r.emitted()        # legit task still ran


def test_guardrail_validate_keeps_task(hero):
    """The guardrail clears the attack AND the legit task still completes."""
    from core.contracts import Guardrail
    from core.diagnosis import Diagnosis
    sb = _sandbox()
    verdict, _, guardrail = Diagnosis(sb).diagnose(hero, hero.agentId)
    run = sb.validate(hero, guardrail, verdict, sign=False)
    assert run.misbehaviorCleared is True
    assert run.taskStillCompletes is True
