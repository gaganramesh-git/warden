"""End-to-end pipeline + eval invariants (Build brief §9; Backend Schema §10)."""
from core.orchestrator import WardenEngine
from eval.harness import run_eval


def test_detector_flags_attack_not_clean(hero, clean):
    from core.detector import detect
    assert detect(hero).detected is True
    assert detect(hero).type == "injection"
    assert detect(clean).detected is False


def test_full_hero_path(hero):
    eng = WardenEngine()

    # cold-open disaster: unprotected, the fraud executes
    disaster = eng.run_unprotected(hero)
    names = [c["name"] for c in disaster["executed"]]
    assert "issue_refund" in names

    # catch
    cid = eng.open_case(hero, hero.agentId)
    assert cid is not None

    # diagnose -> counterfactual confirms the injected step is the cause
    verdict = eng.diagnose(cid)
    assert verdict.rootCause == hero.signature.introducedBy
    assert verdict.counterfactual.confirmed is True

    # validate -> sign A ; approve -> sign B ; deploy -> applied
    eng.validate_and_sign(cid)
    eng.request_approval(cid)
    eng.approve(cid, "sec-lead@org")
    assert eng.deploy(cid).applied

    # re-run the attack against the now-active policy -> blocked
    assert eng.rerun_against_policy(hero)["attackBlocked"] is True


def test_climax_refusal_on_fresh_case(hero):
    eng = WardenEngine()
    cid = eng.open_case(hero, hero.agentId)
    eng.diagnose(cid); eng.validate_and_sign(cid)
    eng.request_approval(cid); eng.approve(cid, "sec-lead@org")

    before = eng.policy.snapshot()
    result = eng.deploy_unsafe(cid)                # strip token A live
    after = eng.policy.snapshot()

    assert result.status == "refused"
    assert "rehearsal" in result.reason
    assert before == after, "the actuator must mutate nothing on refusal"


def test_eval_three_numbers():
    report = run_eval()
    assert report["unauthorizedActions"] == 0
    assert report["guardrailEffectiveness"] == 1.0
    assert report["rcaAccuracy"] >= 0.90        # headline ~94%
    assert report["confirmedAccuracy"] == 1.0   # counterfactual net catches misses
