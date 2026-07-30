"""Shared wiring for the WARDEN Lambda handlers. Reads config from env vars set
by the CDK stack; constructs the AWS-backed stores/gate. All boto3 lives here
and in the aws/ adapters — never in core/."""
from __future__ import annotations

import os

from aws.dynamo_store import DynamoCaseStore, DynamoNonceLedger, DynamoPolicyStore
from aws.s3_transcripts import S3Transcripts

TABLE = os.environ.get("WARDEN_TABLE", "warden")
BUCKET = os.environ.get("WARDEN_BUCKET", "warden-blobs")
KEY_A_ARN = os.environ.get("KEY_A_ARN", "")
KEY_B_ARN = os.environ.get("KEY_B_ARN", "")


def cases() -> DynamoCaseStore:
    return DynamoCaseStore(TABLE)


def transcripts() -> S3Transcripts:
    return S3Transcripts(BUCKET)


def nonce_ledger() -> DynamoNonceLedger:
    return DynamoNonceLedger(TABLE)


def policy() -> DynamoPolicyStore:
    return DynamoPolicyStore(TABLE)
