"""Safe, dependency-free building blocks for a WARDEN fleet agent.

The five agent modules only declare their domain-specific configuration.  This
module creates SessionTrace-compatible traces, with no external calls or real
side effects.  `signature` is deliberately omitted: WARDEN must discover it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

try:
    from core.contracts import SessionTrace, Step
except ImportError:  # Allows inspection before copying into the WARDEN project.
    SessionTrace = Step = None  # type: ignore[misc,assignment]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    sensitive: bool = False

    def stub(self, **args: Any) -> dict[str, Any]:
        """Logging-only tool stub. It never contacts a real service."""
        return {"status": "ok", "tool": self.name, "args": args, "stub": True}


@dataclass(frozen=True)
class Scenario:
    kind: str
    user_message: str
    untrusted_content: str


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    domain: str
    system_prompt: str
    task_intent: str
    baseline_tool: str
    sensitive_tool: str
    untrusted_source: str
    tools: tuple[ToolSpec, ...]
    scenarios: tuple[Scenario, ...]

    @property
    def sensitive_tools(self) -> frozenset[str]:
        return frozenset(tool.name for tool in self.tools if tool.sensitive)

    def build_trace(self, session_id: str, scenario: Scenario,
                    sensitive_args: Mapping[str, Any] | None = None):
        """Create the frozen WARDEN SessionTrace shape for a synthetic run.

        It intentionally produces no ground-truth Signature. In a live-model
        runner, replace only the assistant/tool steps with the recorded model
        transcript; the user/retrieved provenance stays the same.
        """
        if SessionTrace is None or Step is None:
            raise RuntimeError("Install these modules inside WARDEN so core.contracts is importable.")
        args = dict(sensitive_args or {})
        steps = [
            Step(i=0, role="user", content=scenario.user_message, trusted=True),
            Step(i=1, role="assistant", reasoning="Performing the requested safe lookup.",
                 tool_call={"name": self.baseline_tool, "args": {}}),
            Step(i=2, role="tool", tool=self.baseline_tool,
                 output={"status": "ok", "stub": True}),
            Step(i=3, role="retrieved", source=self.untrusted_source, trusted=False,
                 content=scenario.untrusted_content),
        ]
        # Clean traces contain no sensitive action. Attack and borderline traces
        # may contain one, allowing WARDEN to distinguish malicious provenance
        # from an unusual but legitimate request.
        if scenario.kind != "clean":
            steps.extend([
                Step(i=4, role="assistant", reasoning="Recorded model decision for evaluation.",
                     tool_call={"name": self.sensitive_tool, "args": args}),
                Step(i=5, role="tool", tool=self.sensitive_tool,
                     output={"status": "ok", "stub": True}),
            ])
        return SessionTrace(
            sessionId=session_id,
            agentId=self.agent_id,
            task_intent=self.task_intent,
            steps=steps,
        )
