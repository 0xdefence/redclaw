"""ReAct (Reasoning and Acting) loop implementation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Any

from redclaw.agent.agent import LLMAgent, get_agent
from redclaw.agent.memory import WorkingMemory
from redclaw.agent.prompts import get_prompt
from redclaw.models import ToolResult
from redclaw.tools import ToolRegistry, create_default_registry


class StepType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINISH = "finish"
    ERROR = "error"


@dataclass
class ReActStep:
    """A single step in the ReAct loop."""
    step_num: int
    type: StepType
    thought: str
    action: str | None = None
    action_input: dict = field(default_factory=dict)
    observation: str | None = None
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "step_num": self.step_num,
            "type": self.type.value,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class ReActResult:
    """Result of a ReAct loop execution."""
    goal: str
    target: str
    steps: list[ReActStep]
    final_answer: dict | None = None
    success: bool = True
    error: str | None = None
    total_duration_ms: int = 0
    tools_used: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "target": self.target,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "success": self.success,
            "error": self.error,
            "total_duration_ms": self.total_duration_ms,
            "tools_used": self.tools_used,
            "findings": self.findings,
        }


class ReActLoop:
    """ReAct loop for multi-step tool execution with reasoning."""

    def __init__(
        self,
        agent: LLMAgent | None = None,
        registry: ToolRegistry | None = None,
        max_steps: int = 10,
        max_depth: int = 2,
    ) -> None:
        self.agent = agent or get_agent()
        self.registry = registry or create_default_registry()
        self.max_steps = max_steps
        self.max_depth = max_depth
        self.current_depth = 0

    def run(
        self,
        goal: str,
        target: str,
        executor: Any | None = None,
        memory: WorkingMemory | None = None,
        on_step: Callable[[ReActStep], None] | None = None,
    ) -> ReActResult:
        """Execute a ReAct loop for the given goal.

        Args:
            goal: What to accomplish
            target: Target to scan
            executor: DockerExecutor for running tools (optional for planning)
            memory: Working memory (optional, creates new if not provided)
            on_step: Callback for each step

        Returns:
            ReActResult with steps, findings, and final answer
        """
        from redclaw.core.executor import DockerExecutor

        if not self.agent.is_available:
            return ReActResult(
                goal=goal,
                target=target,
                steps=[],
                success=False,
                error="LLM not available. Set OPENROUTER_API_KEY to enable AI features.",
            )

        # Check depth limit
        if self.current_depth >= self.max_depth:
            return ReActResult(
                goal=goal,
                target=target,
                steps=[],
                success=False,
                error=f"Maximum depth ({self.max_depth}) exceeded",
            )

        self.current_depth += 1
        memory = memory or WorkingMemory()
        memory.set_goal(goal)

        executor = executor or DockerExecutor()
        steps: list[ReActStep] = []
        tools_used: list[str] = []
        all_findings: list[dict] = []
        start_time = datetime.now(timezone.utc)

        try:
            for step_num in range(1, self.max_steps + 1):
                memory.set_phase(f"step_{step_num}")

                # Generate next action
                step = self._generate_step(goal, target, memory, step_num)
                steps.append(step)

                if on_step:
                    on_step(step)

                if step.type == StepType.ERROR:
                    return ReActResult(
                        goal=goal,
                        target=target,
                        steps=steps,
                        success=False,
                        error=step.error,
                        tools_used=tools_used,
                        findings=all_findings,
                    )

                if step.type == StepType.FINISH:
                    elapsed = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    return ReActResult(
                        goal=goal,
                        target=target,
                        steps=steps,
                        final_answer=step.action_input,
                        success=True,
                        total_duration_ms=elapsed,
                        tools_used=tools_used,
                        findings=all_findings,
                    )

                # Execute action
                if step.action and step.action != "finish":
                    tool = self.registry.get(step.action)
                    if tool is None:
                        step.observation = f"Unknown tool: {step.action}"
                        memory.add_observation(step.action, step.observation)
                        continue

                    tools_used.append(step.action)
                    memory.add_action(step.action, step.action_input)

                    try:
                        # Extract target from action_input or use default
                        tool_target = step.action_input.get("target", target)
                        tool_kwargs = {k: v for k, v in step.action_input.items() if k != "target"}

                        result = tool.execute(executor, tool_target, **tool_kwargs)
                        step.observation = self._format_observation(result)
                        memory.add_observation(step.action, step.observation, len(result.findings))

                        # Collect findings
                        all_findings.extend(result.findings)
                        for f in result.findings:
                            memory.add_finding(
                                f.get("title", "Unknown"),
                                f.get("severity", "info"),
                            )

                    except Exception as exc:
                        step.observation = f"Tool error: {exc}"
                        memory.add_observation(step.action, step.observation)

            # Max steps reached
            elapsed = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return ReActResult(
                goal=goal,
                target=target,
                steps=steps,
                success=False,
                error=f"Maximum steps ({self.max_steps}) reached without completing",
                total_duration_ms=elapsed,
                tools_used=tools_used,
                findings=all_findings,
            )

        finally:
            self.current_depth -= 1

    def _generate_step(
        self,
        goal: str,
        target: str,
        memory: WorkingMemory,
        step_num: int,
    ) -> ReActStep:
        """Generate the next step using the LLM."""
        # Build tools description
        tools_str = "\n".join(
            f"- {t.id}: {t.description} (risk: {t.risk_level.value})"
            for t in self.registry.list_tools()
        )

        system = get_prompt(
            "react_agent",
            tools=tools_str,
            memory=memory.to_context(),
            max_steps=self.max_steps,
        )

        prompt = f"Target: {target}\nGoal: {goal}\nStep {step_num}: What should I do next?"

        start = datetime.now(timezone.utc)
        try:
            response = self.agent.generate_json(prompt, system)
            elapsed = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

            thought = response.get("thought", "")
            action = response.get("action", "")
            action_input = response.get("action_input", {})

            memory.add_thought(thought)

            if action == "finish":
                return ReActStep(
                    step_num=step_num,
                    type=StepType.FINISH,
                    thought=thought,
                    action="finish",
                    action_input=action_input,
                    duration_ms=elapsed,
                )
            else:
                return ReActStep(
                    step_num=step_num,
                    type=StepType.ACTION,
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    duration_ms=elapsed,
                )

        except Exception as exc:
            elapsed = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            return ReActStep(
                step_num=step_num,
                type=StepType.ERROR,
                thought="",
                error=str(exc),
                duration_ms=elapsed,
            )

    def _format_observation(self, result: ToolResult) -> str:
        """Format a tool result as an observation string."""
        if result.status != "success":
            return f"Error: {result.error or 'Unknown error'}"

        lines = [f"Tool completed in {result.duration_ms}ms"]

        if result.findings:
            lines.append(f"Found {len(result.findings)} findings:")
            for f in result.findings[:5]:  # Limit to 5
                sev = f.get("severity", "info")
                title = f.get("title", "Unknown")
                lines.append(f"  - [{sev}] {title}")
            if len(result.findings) > 5:
                lines.append(f"  ... and {len(result.findings) - 5} more")

        if result.parsed:
            lines.append(f"Parsed data keys: {list(result.parsed.keys())}")

        return "\n".join(lines)
