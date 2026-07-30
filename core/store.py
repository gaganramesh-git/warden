"""
WARDEN — store.py
=================
Thin case store + active-policy store. Local mode keeps everything in memory
(and can dump/load JSON); AWS mode swaps in DynamoDB single-table + S3 behind
the same method surface. Deliberately tiny — the backend is small on purpose.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .contracts import Guardrail


class CaseStore:
    """The single-table case store, modeled as nested dicts keyed by caseId."""

    def __init__(self):
        self._cases: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []

    def put(self, case_id: str, sk: str, item: Dict[str, Any]) -> None:
        self._cases.setdefault(case_id, {})[sk] = item

    def get(self, case_id: str, sk: str) -> Optional[Dict[str, Any]]:
        return self._cases.get(case_id, {}).get(sk)

    def case(self, case_id: str) -> Dict[str, Any]:
        return self._cases.get(case_id, {})

    def set_status(self, case_id: str, status: str) -> None:
        meta = self._cases.setdefault(case_id, {}).setdefault("META", {})
        meta["status"] = status

    def record_event(self, event: Dict[str, Any]) -> None:
        self._events.append(event)

    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def dump(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump({"cases": self._cases, "events": self._events}, f, indent=2, default=str)


class PolicyStore:
    """The 'production' agent config the Actuator mutates. In local mode this is
    an in-memory list (optionally mirrored to a policy file) that the demo agent
    reads. In AWS mode it is an AgentCore Policy / Cedar rule set."""

    def __init__(self, policy_file: Optional[str] = None):
        self._active: Dict[str, Guardrail] = {}
        self._rollback: Dict[str, Guardrail] = {}
        self.policy_file = policy_file

    def active_guardrails(self, agent_id: str) -> List[Guardrail]:
        return [g for g in self._active.values() if g.agentId == agent_id]

    def apply(self, guardrail: Guardrail) -> str:
        """Apply a guardrail; return a rollback token."""
        self._active[guardrail.guardrailId] = guardrail
        rollback_token = "rb_" + guardrail.guardrailId
        self._rollback[rollback_token] = guardrail
        self._flush()
        return rollback_token

    def rollback(self, rollback_token: str) -> bool:
        g = self._rollback.get(rollback_token)
        if not g:
            return False
        self._active.pop(g.guardrailId, None)
        self._flush()
        return True

    def is_active(self, guardrail_id: str) -> bool:
        return guardrail_id in self._active

    def snapshot(self) -> Dict[str, Any]:
        return {gid: g.to_dict() for gid, g in self._active.items()}

    def _flush(self) -> None:
        if not self.policy_file:
            return
        with open(self.policy_file, "w") as f:
            json.dump(self.snapshot(), f, indent=2)
