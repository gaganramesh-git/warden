"""
WARDEN — aws/s3_transcripts.py
==============================
S3 blob store for session transcripts and replay artifacts (Backend Schema §3).
The replay source of truth in AWS mode; the local `fixtures/` dir plays this
role in local mode.

    s3://<bucket>/sessions/<sessionId>/transcript.json
    s3://<bucket>/cases/<caseId>/replay/<sandboxRunId>.json
"""
from __future__ import annotations

import json
from typing import Any, Dict

from core.contracts import SessionTrace


class S3Transcripts:
    def __init__(self, bucket: str, s3=None):
        self.bucket = bucket
        if s3 is None:
            import boto3
            s3 = boto3.client("s3")
        self._s3 = s3

    def put_transcript(self, trace: SessionTrace) -> str:
        key = "sessions/{}/transcript.json".format(trace.sessionId)
        self._s3.put_object(Bucket=self.bucket, Key=key,
                            Body=json.dumps(trace.to_dict()).encode("utf-8"),
                            ContentType="application/json")
        return key

    def get_transcript(self, session_id: str) -> SessionTrace:
        key = "sessions/{}/transcript.json".format(session_id)
        obj = self._s3.get_object(Bucket=self.bucket, Key=key)
        return SessionTrace.from_dict(json.loads(obj["Body"].read()))

    def put_replay(self, case_id: str, sandbox_run_id: str, artifact: Dict[str, Any]) -> str:
        key = "cases/{}/replay/{}.json".format(case_id, sandbox_run_id)
        self._s3.put_object(Bucket=self.bucket, Key=key,
                            Body=json.dumps(artifact).encode("utf-8"),
                            ContentType="application/json")
        return key
