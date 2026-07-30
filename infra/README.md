# WARDEN — AWS mode (CDK)

The same `core/` logic, deployed. This stack is the "proof it's real" half of the
dual run mode: identical business logic, thin AWS adapters (`../aws/`), and the
IAM role separation that turns the dual-key gate from a promise into an enforced
property.

```
Step Functions (saga)  ─┬─▶ Detector  (Lambda)          DynamoDB  (warden, single table)
                        ├─▶ Diagnosis (Lambda)  ◀─▶ Sandbox.falsify
                        ├─▶ Validate  (Lambda)  ── sign token_A ── KMS KEY_A
                        ├─▶ RequestApproval (task-token wait) ── human ── KMS KEY_B (token_B)
                        └─▶ Actuator  (Lambda)  ── verify A+B (KMS Verify-only) ── apply
   Ingest (Lambda) ─▶ S3 (transcripts + replay)      API Gateway REST ─▶ BFF Lambda
```

## The security property, enforced in IAM (not in code)

| Role | KMS grant |
|---|---|
| `SandboxValidate` | `kms:Sign` on **KEY_A** only |
| `Approval` | `kms:Sign` on **KEY_B** only |
| `Actuator` | `kms:Verify` + `kms:GetPublicKey` only — **no `kms:Sign`, on any key** |
| `Diagnosis` | **no KMS grant** (it only falsifies; it never signs) |

A compromised Actuator still cannot mint either attestation. Verify this in the
**synthesized template** without an AWS account:

```bash
pip3 install -r requirements.txt        # aws-cdk-lib, constructs
cdk synth                                # -> cdk.out/WardenStack.template.json
```

## Deploy

```bash
# 1. build the cryptography Lambda layer (matches the linux runtime)
./build_layer.sh

# 2. bootstrap once per account/region, then deploy (defaults to ap-south-1)
cdk bootstrap
cdk deploy
```

Outputs: the table name, blob bucket, both KMS key ARNs, the saga ARN, and the
REST API URL. Kick off a case by starting the state machine with
`{ "sessionId": "<id>" }` after uploading a transcript to
`s3://<bucket>/sessions/<id>/transcript.json` (or invoke the `Ingest` Lambda with
an inline `trace`).

## Notes

- **Signature algorithm:** AWS KMS asymmetric keys use `ECC_NIST_P256` /
  `ECDSA_SHA_256` (KMS does not offer Ed25519). Local mode uses Ed25519. Only the
  primitive differs — the *binding* checks are the exact same
  `core.gate.verify_bindings` in both modes.
- **Diagnosis generators:** in this stack the generators run as the deterministic
  analyzers in `core/`. Swapping them for Bedrock AgentCore calls (one per
  evidence slice) changes cost/latency, not the safety property — the counter-
  factual replay remains the arbiter.
- **Region:** `ap-south-1` (Mumbai) by default; override with
  `CDK_DEFAULT_REGION`.
- **Teardown:** `cdk destroy` (all resources use `RemovalPolicy.DESTROY` for a
  clean hackathon lifecycle).
