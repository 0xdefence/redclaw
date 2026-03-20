"""Workflow generation from natural language objectives."""
from __future__ import annotations

from dataclasses import dataclass, field

from redclaw.intelligence.graph import ToolGraph, IntentCategory
from redclaw.models import ToolPlan, ToolPlanStep, RiskLevel


@dataclass
class WorkflowStep:
    """A step in a generated workflow."""
    tool_id: str
    rationale: str
    risk_level: str
    args: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    """A complete workflow for an objective."""
    objective: str
    steps: list[WorkflowStep]
    estimated_duration_s: int
    requires_confirmation: bool
    reasoning: str


class WorkflowGenerator:
    """Generates execution workflows from natural language objectives."""

    # Tool default timeouts for estimation
    TOOL_DURATIONS = {
        "dig": 10,
        "whois": 15,
        "nmap": 120,
        "nikto": 180,
        "nuclei": 300,
        "gobuster": 120,
    }

    def __init__(self, graph: ToolGraph | None = None) -> None:
        self.graph = graph or ToolGraph()

    def generate(self, objective: str, max_steps: int = 6) -> Workflow:
        """Generate a workflow for an objective.

        Args:
            objective: Natural language description of the goal
            max_steps: Maximum number of steps in the workflow

        Returns:
            Workflow object with ordered steps
        """
        # Analyze the objective
        intent_scores = self.graph.analyze_query(objective)

        # Get recommended tools
        recommendations = self.graph.recommend_tools(objective, limit=max_steps + 2)

        # Select tools based on intent
        selected_tools: list[str] = []
        for tool_id, score, _ in recommendations:
            if score > 0.15 and len(selected_tools) < max_steps:
                selected_tools.append(tool_id)

        # If no tools selected, use defaults based on intent
        if not selected_tools:
            selected_tools = self._get_default_tools(intent_scores)

        # Order tools by dependencies
        ordered_tools = self.graph.topological_sort(selected_tools)

        # Build workflow steps
        steps: list[WorkflowStep] = []
        requires_confirmation = False
        total_duration = 0

        for tool_id in ordered_tools:
            node = self.graph.get_node(tool_id)
            if not node:
                continue

            # Get dependencies within this workflow
            deps = [t for t in self.graph.get_dependencies(tool_id) if t in ordered_tools]

            # Determine args based on objective keywords
            args = self._infer_args(tool_id, objective)

            step = WorkflowStep(
                tool_id=tool_id,
                rationale=f"{node.name}: {node.description}",
                risk_level=node.risk_level,
                args=args,
                depends_on=deps,
            )
            steps.append(step)

            # Track confirmation requirement
            if node.risk_level == "intrusive":
                requires_confirmation = True

            # Estimate duration
            total_duration += self.TOOL_DURATIONS.get(tool_id, 60)

        # Generate reasoning
        reasoning = self._generate_reasoning(objective, steps, intent_scores)

        return Workflow(
            objective=objective,
            steps=steps,
            estimated_duration_s=total_duration,
            requires_confirmation=requires_confirmation,
            reasoning=reasoning,
        )

    def _get_default_tools(self, intent_scores: dict[IntentCategory, float]) -> list[str]:
        """Get default tools based on intent scores."""
        # Find dominant intent
        dominant = max(intent_scores.items(), key=lambda x: x[1])

        defaults = {
            IntentCategory.RECON: ["dig", "whois"],
            IntentCategory.SCANNING: ["nmap", "nikto"],
            IntentCategory.ENUMERATION: ["gobuster", "nmap"],
            IntentCategory.EXPLOITATION: ["nmap", "nuclei"],
            IntentCategory.ANALYSIS: ["nmap"],
        }

        return defaults.get(dominant[0], ["nmap"])

    def _infer_args(self, tool_id: str, objective: str) -> dict:
        """Infer tool arguments from objective keywords."""
        objective_lower = objective.lower()
        args: dict = {}

        if tool_id == "nmap":
            if "full" in objective_lower or "comprehensive" in objective_lower:
                args["profile"] = "full"
            elif "stealth" in objective_lower or "quiet" in objective_lower:
                args["profile"] = "stealth"
            elif "udp" in objective_lower:
                args["profile"] = "udp"
            else:
                args["profile"] = "quick"

        elif tool_id == "gobuster":
            if "directory" in objective_lower or "dir" in objective_lower:
                args["mode"] = "dir"
            elif "dns" in objective_lower or "subdomain" in objective_lower:
                args["mode"] = "dns"
            elif "vhost" in objective_lower:
                args["mode"] = "vhost"
            else:
                args["mode"] = "dir"

        elif tool_id == "nuclei":
            if "cve" in objective_lower:
                args["tags"] = "cve"
            elif "critical" in objective_lower:
                args["severity"] = "critical"

        return args

    def _generate_reasoning(
        self,
        objective: str,
        steps: list[WorkflowStep],
        intent_scores: dict[IntentCategory, float],
    ) -> str:
        """Generate human-readable reasoning for the workflow."""
        # Find top intents
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        top_intents = [cat.value for cat, score in sorted_intents[:2] if score > 0.1]

        if not top_intents:
            top_intents = ["general security assessment"]

        tool_names = [s.tool_id for s in steps]
        passive_count = sum(1 for s in steps if s.risk_level == "passive")
        active_count = sum(1 for s in steps if s.risk_level == "active")
        intrusive_count = sum(1 for s in steps if s.risk_level == "intrusive")

        reasoning = f"For objective '{objective}', detected intents: {', '.join(top_intents)}. "
        reasoning += f"Selected {len(steps)} tools: {', '.join(tool_names)}. "
        reasoning += f"Risk breakdown: {passive_count} passive, {active_count} active, {intrusive_count} intrusive. "

        if intrusive_count > 0:
            reasoning += "User confirmation required before intrusive scans."

        return reasoning

    def to_tool_plan(self, workflow: Workflow, target: str) -> ToolPlan:
        """Convert a Workflow to a ToolPlan model."""
        steps = []
        for ws in workflow.steps:
            risk = RiskLevel.PASSIVE
            if ws.risk_level == "active":
                risk = RiskLevel.ACTIVE
            elif ws.risk_level == "intrusive":
                risk = RiskLevel.INTRUSIVE

            steps.append(ToolPlanStep(
                tool_id=ws.tool_id,
                args=ws.args,
                risk_level=risk,
                rationale=ws.rationale,
                depends_on=ws.depends_on,
            ))

        return ToolPlan(
            objective=workflow.objective,
            steps=steps,
            estimated_duration_s=workflow.estimated_duration_s,
            requires_confirmation=workflow.requires_confirmation,
        )
