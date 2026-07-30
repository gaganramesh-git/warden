# WARDEN — antivirus for autonomous AI agents

> Catch the hijack. **Prove** the cause. **Sign** the fix. Refuse everything unproven.

WARDEN watches an AI agent, catches it when a malicious input hijacks it,
**proves the cause** by replaying the session without that input (the
misbehavior vanishes), proposes a guardrail, **proves the guardrail works** by
replaying with it on, and then **refuses to deploy any fix that hasn't been both
rehearsed and human-approved** — enforced by two cryptographic signatures, not
by trust.

Two properties are the entire point:

- **PROVABLE cause** — a counterfactual *replay*, never an LLM's opinion. Remove
  the suspect input, replay the exact session, watch the attack disappear.
- **UNFORGEABLE safety** — the actuator has **verify-only** key access and
  physically cannot act without a rehearsal signature **and** a human signature
  over the same plan and the same rehearsal run.

The single most important moment: **strip the rehearsal signature and watch the
actuator hard-fail.**

---

## Quick start

```bash
# 1. Python deps (local mode is fully self-contained — no AWS account)
pip3 install -r requirements.txt

# 2. Prove it works — the acceptance suite (determinism, refusal, plan-swap, replay)
python3 -m pytest -q                 #  -> 18 passed

# 3. The three numbers — offline eval over 50 injected attacks
python3 -m eval.harness              #  -> 94% RCA · 100% guardrail · 0 unauthorized

# 4. The 4-minute demo, in the terminal
python3 -m demo.run_demo             #  -> disaster → catch → proof → seals → REFUSAL

# 5. The forensic console (React + Vite). Needs Node 18+.
cd ui && npm install && npm run data && npm run dev
```

Or just: `./run.sh all` (runs tests + eval + demo, then serves the console).

> **No Node?** Install it locally without sudo:
> `curl -L https://nodejs.org/dist/v24.18.1/node-v24.18.1-darwin-arm64.tar.gz | tar -xz -C ~/.local && mv ~/.local/node-v24.18.1-darwin-arm64 ~/.local/node && export PATH="$HOME/.local/node/bin:$PATH"`

---

## What's in the box

```
warden/
  core/               framework-free business logic — the real system
    contracts.py        frozen event + token + trace dataclasses
    gate.py             ★ the dual-key crypto gate (real Ed25519, never mocked)
    agent_harness.py    the demo agent + deterministic replay engine
    sandbox.py          falsify() + validate() — one engine proves cause AND cure
    detector.py         injection detection (the hero signature)
    diagnosis.py        4 partitioned generators + critic + counterfactual arbiter
    actuator.py         the only prod-mutating service — verify both tokens or refuse
    orchestrator.py     the saga (local wiring of the 5 services)
    store.py            case store + active-policy store
  demo/
    fixtures/           the hero attack session + a clean session
    run_demo.py         the 4-minute demo, narrated in the terminal
    build_ui_data.py    runs the live pipeline -> JSON the console renders
  eval/
    generate_fixtures.py  50 labeled injected-attack sessions
    harness.py            runs the whole pipeline offline -> the 3 numbers
  ui/                   React 18 + Vite + TS + Tailwind + Framer Motion console
  tests/               the acceptance suite the pitch's honesty depends on
```

---

## The moat: the dual-key gate (`core/gate.py`)

Two independent Ed25519 key pairs, three roles, verify-only actuator:

```
KEY_A  ->  only the Sandbox may sign  (REHEARSAL_PASS)
KEY_B  ->  only the Approval path may sign  (HUMAN_APPROVAL)
Verify ->  the Actuator holds PUBLIC keys only — it cannot mint either signature
```

Both tokens sign the *same* canonical payload. Before it mutates anything, the
actuator asserts **all** of:

1. `token_A` verifies under `KEY_A_pub`, `token_B` under `KEY_B_pub`
2. `plan_hash_A == plan_hash_B == sha256(guardrail)` — no approve-X-apply-Y
3. `verdict_hash_A == verdict_hash_B` — the approval is about *this* verdict
4. `sandbox_run_id_A == sandbox_run_id_B` — both attest the *same* rehearsal
5. `now < exp` and the nonce is unused — no replay of a stale approval

Any failure → `ActuationRefused`, and **state is byte-identical** (asserted).
`tests/test_gate.py` strips `token_A`, swaps the plan, and replays a nonce — each
refuses. That stripped-token test *is* the demo climax.

## Why the diagnosis isn't hallucinating

The four generators each see a **disjoint slice** of the trace (tool-I/O ·
instruction chain · retrieved content · reasoning), a critic ranks them, and
then the **counterfactual replay is the judge** — a cause is accepted only if
removing it makes the misbehavior disappear on replay. The arbiter is empirical.

## Why the replay is meaningful

The replay engine is a **pure function** of `(trace, mutation)` — temperature-0
by construction, tool outputs served from the recording, so the only variable
between a control replay and a mutated one is the mutation under test. Run
`falsify` a thousand times, get the same result (`tests/test_replay.py`).

---

## Honesty notes (what's real vs. simulated)

Nothing here is overclaimed:

- **Real:** the cryptography (genuine Ed25519, two key pairs, verify-only
  actuator), the deterministic replay engine, the counterfactual proof, the
  refusal, the nonce/plan/verdict bindings, and every number in the eval.
- **Simulated for stage reliability:** the monitored agent is a deterministic
  policy interpreter rather than a live temperature-0 model, so the demo can
  never flake offline. The four diagnosis generators are deterministic analyzers
  over their evidence slices rather than four Bedrock calls. Both are labeled as
  such in the source. Crucially, the *judge of truth is the replay*, not the
  analyzer — so swapping in live models changes cost and latency, not the safety
  property.

## AWS mode (the proof it's real — built, `cdk synth`-verified)

The same `core/` logic runs behind thin adapters in [aws/](aws/) and a one-stack
CDK app in [infra/](infra/): Step Functions (the saga), DynamoDB (single-table
case store), S3 (transcripts + replay artifacts), two **KMS** asymmetric keys,
Lambda per service, and an API Gateway BFF. The dual-key gate's binding checks
are the *exact same* `core.gate.verify_bindings` in both modes — only the
signature primitive (Ed25519 local / KMS `ECDSA_SHA_256`) and the key custody
change.

The role separation is enforced in **IAM**, and you can prove it from the
synthesized CloudFormation with no AWS account:

```bash
cd infra && pip3 install -r requirements.txt && cdk synth
```

| Role | KMS grant (in the synthesized template) |
|---|---|
| SandboxValidate | `kms:Sign` on KEY_A only |
| Approval | `kms:Sign` on KEY_B only |
| **Actuator** | `kms:Verify` + `GetPublicKey` only — **no Sign, on any key** |
| Diagnosis | none |

So "the actuator cannot self-authorize" is a real, deployed constraint. Full
deploy steps are in [infra/README.md](infra/README.md). Local mode is what runs
on stage; AWS mode is what makes "built on AWS" honestly true.

---

## The one-liner

> Everyone's shipping AI agents; almost no one can prove why one broke or
> guarantee a fix is safe. WARDEN does both — **provable cause, unforgeable
> fix.** Antivirus for autonomous agents.
