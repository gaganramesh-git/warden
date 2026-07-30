"""
WARDEN — gate.py  (THE MOAT — this is real cryptography, never mocked)
======================================================================
Two independent Ed25519 key pairs, two signers, one verifier.

    KEY_A  -> only the Sandbox may sign with it  (REHEARSAL_PASS)
    KEY_B  -> only the Approval path may sign it  (HUMAN_APPROVAL)
    Verify -> the Actuator holds PUBLIC keys ONLY. It can check signatures;
              it physically cannot mint them. This is the "verify-only"
              property enforced by construction, not by policy.

Both tokens sign the *same* canonical payload. The Actuator's verify() asserts
every binding in Backend-Schema §5 — swap the plan, reuse a nonce, strip a
token, or forge a signature and it HARD-FAILS.

Local mode uses PyCA `cryptography` (genuine asymmetric crypto). AWS mode swaps
the same three roles onto two KMS asymmetric keys with separate IAM grants; the
verification logic below is identical.
"""
from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Optional, Set

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .contracts import canonical_bytes

TOKEN_TTL_SECONDS = 300  # approvals expire; no replay of a stale approval

REHEARSAL_PASS = "REHEARSAL_PASS"
HUMAN_APPROVAL = "HUMAN_APPROVAL"


class ActuationRefused(Exception):
    """Raised by the verifier when ANY binding fails. Carries a plain reason
    the operator (and the demo banner) can read verbatim."""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------- #
# Keys
# --------------------------------------------------------------------------- #
def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


@dataclass
class Token:
    kind: str                      # REHEARSAL_PASS | HUMAN_APPROVAL
    payload: Dict[str, Any]        # the canonical payload (bytes actually signed)
    signature: str                 # base64(sig)
    keyId: str                     # KEY_A | KEY_B
    alg: str = "Ed25519"
    approver: Optional[str] = None # HUMAN_APPROVAL only

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def signed_message(self) -> bytes:
        """The exact bytes that were signed: canonical payload prefixed with the
        token kind (and approver), so a REHEARSAL token can never be replayed as
        an APPROVAL token even over an identical payload."""
        prefix = self.kind
        if self.approver:
            prefix = "{}:{}".format(self.kind, self.approver)
        return prefix.encode("utf-8") + b"|" + canonical_bytes(self.payload)


class Signer:
    """A holder of ONE private key. The Sandbox gets a Signer for KEY_A; the
    Approval path gets a Signer for KEY_B. Neither can sign the other's key."""

    def __init__(self, key_id: str, private_key: Optional[Ed25519PrivateKey] = None):
        self.key_id = key_id
        self._sk = private_key or Ed25519PrivateKey.generate()

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self._sk.public_key()

    def _sign_token(self, kind: str, payload: Dict[str, Any],
                    approver: Optional[str] = None) -> Token:
        tok = Token(kind=kind, payload=payload, signature="", keyId=self.key_id,
                    approver=approver)
        sig = self._sk.sign(tok.signed_message())
        tok.signature = _b64(sig)
        return tok

    def sign_rehearsal(self, canonical: Dict[str, Any]) -> Token:
        """Only ever called by the Sandbox after a passing `validate` replay."""
        return self._sign_token(REHEARSAL_PASS, canonical)

    def sign_approval(self, canonical: Dict[str, Any], approver: str) -> Token:
        """Only ever called by the human-approval path."""
        return self._sign_token(HUMAN_APPROVAL, canonical, approver=approver)


# --------------------------------------------------------------------------- #
# Canonical payload builder
# --------------------------------------------------------------------------- #
def build_canonical(session_id: str, plan_hash: str, sandbox_run_id: str,
                    verdict_hash: str, nonce: str,
                    exp: Optional[float] = None) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "plan_hash": plan_hash,
        "sandbox_run_id": sandbox_run_id,
        "verdict_hash": verdict_hash,
        "nonce": nonce,
        "exp": int(exp if exp is not None else time.time() + TOKEN_TTL_SECONDS),
    }


# --------------------------------------------------------------------------- #
# Verifier — the Actuator's view. PUBLIC keys only. Cannot sign anything.
# --------------------------------------------------------------------------- #
class NonceLedger:
    """Spent-token ledger for replay protection. Backed by an in-memory set in
    local mode; a DynamoDB `NONCE#<n>` item in AWS mode."""
    def __init__(self, used: Optional[Set[str]] = None):
        self._used: Set[str] = used if used is not None else set()

    def seen(self, nonce: str) -> bool:
        return nonce in self._used

    def record(self, nonce: str) -> None:
        self._used.add(nonce)


class Verifier:
    """Holds ONLY the two public keys. This is the whole point of "verify-only":
    there is no private-key material anywhere in this object, so a compromised
    Actuator still cannot forge either attestation."""

    def __init__(self, key_a_pub: Ed25519PublicKey, key_b_pub: Ed25519PublicKey,
                 ledger: Optional[NonceLedger] = None):
        self.key_a_pub = key_a_pub
        self.key_b_pub = key_b_pub
        self.ledger = ledger or NonceLedger()

    def _verify_sig(self, pub: Ed25519PublicKey, token: Token) -> bool:
        try:
            pub.verify(_unb64(token.signature), token.signed_message())
            return True
        except InvalidSignature:
            return False

    def verify(self, plan_hash: str, verdict_hash: str,
               token_a: Optional[Token], token_b: Optional[Token],
               now: Optional[float] = None) -> Dict[str, Any]:
        """Assert EVERY binding via the shared `verify_bindings`. The only thing
        that differs between local and AWS mode is the signature primitive; the
        binding logic is identical (and lives in one place). Ed25519 here."""
        def sig_verify(token: Token) -> bool:
            pub = self.key_a_pub if token.keyId == "KEY_A" else self.key_b_pub
            return self._verify_sig(pub, token)

        return verify_bindings(plan_hash, verdict_hash, token_a, token_b,
                               sig_verify, self.ledger, now)


# --------------------------------------------------------------------------- #
# The shared binding check — THE security-critical logic, in exactly one place.
# Both the local Ed25519 Verifier and the AWS KMS verifier call this; they only
# differ in the `sig_verify` primitive they inject. (Backend Schema §5.)
# --------------------------------------------------------------------------- #
def verify_bindings(plan_hash: str, verdict_hash: str,
                    token_a: Optional[Token], token_b: Optional[Token],
                    sig_verify: "Callable[[Token], bool]",
                    ledger: "NonceLedgerLike",
                    now: Optional[float] = None) -> Dict[str, Any]:
    """Assert EVERY binding. Any failure raises ActuationRefused and the caller
    (Actuator) must mutate nothing. On success, records the nonce so the same
    approval can never be replayed, and returns the verified facts.

    `sig_verify(token) -> bool` performs the raw signature check under the key
    the token names (Ed25519 locally / KMS.Verify in AWS). `ledger` needs only
    `.seen(nonce)` and `.record(nonce)` (an in-memory set locally, a DynamoDB
    item in AWS)."""
    now = now if now is not None else time.time()

    # 0. Both tokens must be present. (Strip token_A -> this is the demo climax.)
    if token_a is None:
        raise ActuationRefused("missing rehearsal signature")
    if token_b is None:
        raise ActuationRefused("missing human approval signature")

    # 1. Each signature is valid under its OWN key, and the kinds are right.
    if token_a.kind != REHEARSAL_PASS or token_a.keyId != "KEY_A":
        raise ActuationRefused("token A is not a rehearsal-pass from KEY_A")
    if token_b.kind != HUMAN_APPROVAL or token_b.keyId != "KEY_B":
        raise ActuationRefused("token B is not a human-approval from KEY_B")
    if not sig_verify(token_a):
        raise ActuationRefused("rehearsal signature failed verification")
    if not sig_verify(token_b):
        raise ActuationRefused("human approval signature failed verification")

    pa, pb = token_a.payload, token_b.payload

    # 2. plan_hash binding — you cannot approve plan X and apply plan Y.
    if not (pa["plan_hash"] == pb["plan_hash"] == plan_hash):
        raise ActuationRefused("plan hash mismatch (fix was altered after approval)")

    # 3. verdict binding — the approval is about THIS verdict.
    if not (pa["verdict_hash"] == pb["verdict_hash"] == verdict_hash):
        raise ActuationRefused("verdict hash mismatch")

    # 4. same rehearsal — both attest the SAME sandbox run.
    if pa["sandbox_run_id"] != pb["sandbox_run_id"]:
        raise ActuationRefused("rehearsal/approval attest different sandbox runs")

    # 5. same session.
    if pa["session_id"] != pb["session_id"]:
        raise ActuationRefused("tokens bind to different sessions")

    # 6. freshness + replay protection — one nonce, one use.
    nonce = pa["nonce"]
    if pa["nonce"] != pb["nonce"]:
        raise ActuationRefused("nonce mismatch between tokens")
    if now >= pa["exp"] or now >= pb["exp"]:
        raise ActuationRefused("approval expired")
    if ledger.seen(nonce):
        raise ActuationRefused("approval already used (replay blocked)")

    # All bindings hold. Burn the nonce; this approval can never be reused.
    ledger.record(nonce)
    return {
        "session_id": pa["session_id"],
        "sandbox_run_id": pa["sandbox_run_id"],
        "plan_hash": plan_hash,
        "nonce": nonce,
    }


# A structural type: anything with seen()/record(str). NonceLedger satisfies it,
# and so does the AWS DynamoDB nonce ledger.
NonceLedgerLike = Any


# --------------------------------------------------------------------------- #
# Keyring — wires the three roles together for local mode.
# --------------------------------------------------------------------------- #
class Keyring:
    """Local-mode key custody. Models AWS IAM role separation by construction:
    each role is handed only the key material it is allowed to hold."""

    def __init__(self):
        self.sandbox_signer = Signer("KEY_A")        # holds KEY_A private only
        self.approval_signer = Signer("KEY_B")       # holds KEY_B private only

    def actuator_verifier(self, ledger: Optional[NonceLedger] = None) -> Verifier:
        # Actuator receives PUBLIC keys only — no way to sign anything.
        return Verifier(
            key_a_pub=self.sandbox_signer.public_key,
            key_b_pub=self.approval_signer.public_key,
            ledger=ledger,
        )


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()
