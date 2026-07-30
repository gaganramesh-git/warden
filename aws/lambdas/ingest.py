"""S1 · Ingest (Lambda). Assembles/receives a session trace and writes the
transcript to S3, emitting SessionTraceReady. Fixture-loader escape hatch: if
`trace` is passed inline, persist it; otherwise read an existing S3 transcript.
"""
from __future__ import annotations

from core.contracts import SessionTrace
from . import common


def handler(event, _context=None):
    if "trace" in event:
        trace = SessionTrace.from_dict(event["trace"])
        common.transcripts().put_transcript(trace)
    else:
        trace = common.transcripts().get_transcript(event["sessionId"])
    sig = trace.signature.to_dict() if trace.signature else None
    return {
        "type": "SessionTraceReady",
        "sessionId": trace.sessionId,
        "agentId": trace.agentId,
        "s3Key": "sessions/{}/transcript.json".format(trace.sessionId),
        "signaturePresent": sig is not None,
    }
