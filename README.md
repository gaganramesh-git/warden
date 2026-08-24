
# WARDEN — antivirus for autonomous AI agents
THE DEMO VIDEO LINK :https://drive.google.com/file/d/1d9UeMfZi44MOStweKJGmddvwCx6gIWUQ/view?usp=sharing

> Catch the hijack. **Prove** the cause. **Sign** the fix. Refuse everything unproven.

WARDEN watches an AI agent, catches it when it misbehaves, **proves the cause**
by replaying the session without the offending input (the misbehavior vanishes),
proposes a guardrail, **proves the guardrail works** by replaying with it on, and
then **refuses to deploy any fix that hasn't been both rehearsed and human-
approved** — enforced by two cryptographic signatures, not by trust.

Two properties are the whole point:

- **PROVABLE cause** — a counterfactual *replay*, never an LLM's opinion. Remove
  the suspect input, replay the exact session, watch the attack disappear.
- **UNFORGEABLE safety** — the actuator has **verify-only** key access and
  physically cannot act without a rehearsal signature **and** a human signature
  over the same plan and the same rehearsal.

The single most memorable moment: **strip the rehearsal signature and watch the
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

# 4. The 4-minute demo, narrated in the terminal
python3 -m demo.run_demo             #  -> disaster → catch → proof → seals → REFUSAL
```

### The forensic console (React)

Node lives in a local folder in this environment, so put it on PATH first:

```bash
export PATH="$HOME/.local/node/bin:$PATH"     # skip if node is already on PATH
cd ui
npm install                                   # first time only
npm run dev                                   # dev server → http://localhost:5173
#   …or serve the production build:
npm run build && npm run preview              #            → http://localhost:4173
```

One-command from the repo root (regenerate demo data + build + serve):

```bash
./run.sh ui
```

Other `run.sh` targets: `test` · `eval` · `demo` · `synth` (AWS) · `all`.

---

## What's built

| Area | Status |
|---|---|
| **Two attack types** — prompt **injection** + runaway **loop** | ✅ end-to-end |
| **Deterministic replay** sandbox (`falsify` + `validate`) | ✅ |
| **Dual-key crypto gate** (real Ed25519; KMS in AWS mode) | ✅ |
| **Verify-only actuator** + the live refusal | ✅ |
| **Scenario-driven console** (React) — Fleet, chain-of-custody, Gate cockpit, Reports | ✅ |
| **Offline eval** over 50 injected attacks | ✅ 94 / 100 / 0 |
| **AWS deployment** (CDK: KMS · DynamoDB · S3 · Step Functions · Lambda) | ✅ `cdk synth`-verified & deployed |
| **Monitored-agent fleet** (19 agent specs) | ✅ specs in `agents/` |

---

## Repository layout

```
warden/
  core/              framework-free engine — the real system
    contracts.py       frozen event + token + trace dataclasses (incl. attack kind/threshold)
    gate.py            ★ dual-key gate — real Ed25519, shared verify_bindings (never mocked)
    agent_harness.py   the demo agent + deterministic replay engine
    sandbox.py         falsify() + validate() — one engine proves cause AND cure
    detector.py        injection + loop detection (routes by signature)
    diagnosis.py       4 partitioned generators + critic + counterfactual arbiter
    actuator.py        the only prod-mutating service — verify both tokens or refuse
    orchestrator.py    the local saga (detect → diagnose → validate → approve → apply)
    store.py           case store + active-policy store
  agents/            monitored-agent FLEET — 19 data-only agent specs (see agents/README.md)
  aws/               thin AWS adapters (KMS gate, DynamoDB, S3, Lambda handlers)
  infra/             one CDK stack — KMS×2, DynamoDB, S3, Step Functions saga, 8 Lambdas
  ui/                React 18 + Vite + TS + Tailwind + Framer Motion console
  demo/
    fixtures/          recorded attack sessions (hero_attack, loop_attack, clean_session)
    run_demo.py        the 4-minute demo, narrated in the terminal
    build_ui_data.py   runs the live pipeline per scenario → the JSON the console renders
    run_aws_case.sh    drive one full case through the DEPLOYED AWS saga
  eval/              the 50-attack harness + fixture generator
  tests/             the acceptance suite the pitch's honesty depends on
```

---

## The moat: the dual-key gate (`core/gate.py`)

Two independent key pairs, three roles, verify-only actuator:

```
KEY_A  ->  only the Sandbox may sign  (REHEARSAL_PASS)
KEY_B  ->  only the Approval path may sign  (HUMAN_APPROVAL)
Verify ->  the Actuator holds PUBLIC keys only — it cannot mint either signature
```

Both tokens sign the *same* canonical payload. Before it mutates anything, the
actuator asserts **all** of: both signatures valid under their own keys ·
`plan_hash_A == plan_hash_B == sha256(guardrail)` · same `verdict_hash` · same
`sandbox_run_id` · fresh, single-use `nonce`. Any failure → `ActuationRefused`,
and **state is byte-identical** (asserted). Local mode uses Ed25519; AWS mode
uses KMS `ECDSA_SHA_256` — the *binding* logic is the exact same
`core.gate.verify_bindings` in both.

## Two attack types, one pipeline

- **Injection** — untrusted content is treated as an instruction that fires a
  sensitive tool call. Guardrail: block that tool on any session touching
  untrusted content.
- **Loop** — the same sensitive call fires repeatedly with no progress. Guardrail:
  a **rate-limit** (max calls per session).

Both share detector → diagnosis → counterfactual → gate → actuator. The console
renders each as its own selectable scenario (see the Fleet screen).

## The monitored-agent fleet (`agents/`)

19 data-only agent specs (support, billing, ops-copilot, data-analyst, email,
procurement, sales-quote, devops-pr, it-helpdesk, legal-contract, soc-triage,
trading-research, logistics, healthcare-intake, hr-onboarding, social-comms, …).
Each exports an `AgentSpec` with a system prompt, tool metadata, and a scenario
corpus (`clean · obvious · paraphrased · borderline`) that builds a
`SessionTrace`. The ground-truth `signature` is deliberately omitted so WARDEN
must **discover** it — the corpus doesn't grade itself. See `agents/README.md`.

## AWS mode (deployed proof)

The same `core/` logic runs behind thin adapters + a one-stack CDK app. The role
separation is enforced in **IAM** and provable from the synthesized template with
no AWS account:

```bash
cd infra && pip3 install -r requirements.txt && cdk synth
```

| Role | KMS grant |
|---|---|
| SandboxValidate | `kms:Sign` on KEY_A only |
| Approval | `kms:Sign` on KEY_B only |
| **Actuator** | `kms:Verify` + `GetPublicKey` only — **no Sign, on any key** |
| Diagnosis | none |

Full deploy + "run a live case" steps are in [`infra/README.md`](infra/README.md).

---

## The numbers

Offline harness over **50 injected attacks** (`python3 -m eval.harness`):

> **94% correct root cause · 100% of deployed guardrails cleared the fault · 0 unauthorized actions**

The harness doubles as the regression suite.

## Honesty notes

Nothing is overclaimed. **Real:** the cryptography (genuine Ed25519 / KMS, verify-
only actuator), the deterministic replay, the counterfactual, the refusal, every
binding, and every eval number. **Simulated for stage reliability:** the monitored
agent is a deterministic policy interpreter (not a live model) and the four
diagnosis generators are deterministic analyzers over their evidence slices — both
labeled as such in the source. The judge of truth is always the *replay*, never an
analyzer, so swapping in live models changes cost and latency, not the safety
property.

---

## The one-liner

> Everyone's shipping AI agents; almost no one can prove why one broke or
> guarantee a fix is safe. WARDEN does both — **provable cause, unforgeable fix.**
> Antivirus for autonomous agents.
