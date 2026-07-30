"""
WARDEN — aws/kms_gate.py
========================
The AWS-mode gate: two KMS asymmetric keys (ECC_NIST_P256, SIGN_VERIFY) with the
signature primitive backed by KMS instead of local Ed25519. The *binding* logic
is NOT reimplemented here — it is `core.gate.verify_bindings`, the exact same
security-critical code the local mode runs. Only `sign` / `sig_verify` change.

Role separation is enforced by IAM (see infra/warden_stack.py), not by this
code:
    Sandbox task role   -> kms:Sign on KEY_A only
    Approval task role  -> kms:Sign on KEY_B only
    Actuator task role  -> kms:Verify (+ GetPublicKey) only, on both — NO Sign

So a compromised Actuator still cannot mint either attestation: it has no
kms:Sign grant on anything.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, Optional

from core.gate import (
    ActuationRefused, HUMAN_APPROVAL, REHEARSAL_PASS, Token, verify_bindings,
)

SIGNING_ALG = "ECDSA_SHA_256"   # KMS ECC_NIST_P256 SIGN_VERIFY
KEY_SPEC = "ECC_NIST_P256"


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


class KmsSigner:
    """Holds a grant to kms:Sign ONE key. The Sandbox gets one for KEY_A; the
    Approval path gets one for KEY_B. Neither can sign the other's key."""

    def __init__(self, key_id: str, key_arn: str, kms_client=None):
        self.key_id = key_id            # logical "KEY_A" | "KEY_B"
        self._arn = key_arn             # the KMS key ARN/id
        if kms_client is None:
            import boto3
            kms_client = boto3.client("kms")
        self._kms = kms_client

    def _sign_token(self, kind: str, payload: Dict[str, Any],
                    approver: Optional[str] = None) -> Token:
        tok = Token(kind=kind, payload=payload, signature="", keyId=self.key_id,
                    alg=SIGNING_ALG, approver=approver)
        resp = self._kms.sign(
            KeyId=self._arn,
            Message=tok.signed_message(),       # identical bytes to local mode
            MessageType="RAW",
            SigningAlgorithm=SIGNING_ALG,
        )
        tok.signature = _b64(resp["Signature"])
        return tok

    def sign_rehearsal(self, canonical: Dict[str, Any]) -> Token:
        return self._sign_token(REHEARSAL_PASS, canonical)

    def sign_approval(self, canonical: Dict[str, Any], approver: str) -> Token:
        return self._sign_token(HUMAN_APPROVAL, canonical, approver=approver)


class KmsVerifier:
    """The Actuator's view. It calls kms:Verify (it has no Sign grant), then runs
    the *shared* binding checks. Structurally identical guarantees to local mode."""

    def __init__(self, key_a_arn: str, key_b_arn: str, ledger,
                 kms_client=None):
        self._arn = {"KEY_A": key_a_arn, "KEY_B": key_b_arn}
        self.ledger = ledger            # DynamoNonceLedger (seen/record)
        if kms_client is None:
            import boto3
            kms_client = boto3.client("kms")
        self._kms = kms_client

    def _sig_verify(self, token: Token) -> bool:
        arn = self._arn.get(token.keyId)
        if not arn:
            return False
        try:
            resp = self._kms.verify(
                KeyId=arn,
                Message=token.signed_message(),
                MessageType="RAW",
                Signature=_unb64(token.signature),
                SigningAlgorithm=SIGNING_ALG,
            )
            return bool(resp.get("SignatureValid"))
        except self._kms.exceptions.KMSInvalidSignatureException:
            return False

    def verify(self, plan_hash: str, verdict_hash: str,
               token_a: Optional[Token], token_b: Optional[Token],
               now: Optional[float] = None) -> Dict[str, Any]:
        # Same shared logic as local mode — only _sig_verify differs.
        return verify_bindings(plan_hash, verdict_hash, token_a, token_b,
                               self._sig_verify, self.ledger, now)


# Re-export so callers can `except ActuationRefused` from one place.
__all__ = ["KmsSigner", "KmsVerifier", "ActuationRefused", "KEY_SPEC", "SIGNING_ALG"]
