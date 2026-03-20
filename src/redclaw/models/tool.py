"""Tool-related data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ToolCategory(str, Enum):
    RECON = "recon"
    SCANNING = "scanning"
    ENUMERATION = "enumeration"
    EXPLOITATION = "exploitation"
    ANALYSIS = "analysis"


class RiskLevel(str, Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    INTRUSIVE = "intrusive"


@dataclass(frozen=True)
class ToolMeta:
    """Metadata about a registered tool."""
    id: str
    name: str
    description: str
    category: ToolCategory
    risk_level: RiskLevel
    binary: str
    default_timeout: int = 300


@dataclass
class ToolResult:
    """Result from a single tool execution."""
    tool_id: str
    target: str
    command: str
    raw_output: str
    parsed: dict = field(default_factory=dict)
    findings: list[dict] = field(default_factory=list)
    status: str = "success"          # success | timeout | error
    exit_code: int = 0
    duration_ms: int = 0
    error: str | None = None


@dataclass
class ToolPlanStep:
    """One step in an execution plan."""
    tool_id: str
    args: dict = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.ACTIVE
    rationale: str = ""
    depends_on: list[str] = field(default_factory=list)


@dataclass
class ToolPlan:
    """Ordered execution plan for a scan objective."""
    objective: str
    steps: list[ToolPlanStep] = field(default_factory=list)
    estimated_duration_s: int = 0
    requires_confirmation: bool = False
