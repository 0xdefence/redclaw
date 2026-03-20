"""Scan-related data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Finding:
    """A single security finding from a scan."""
    title: str
    severity: Severity
    description: str
    tool_id: str
    target: str
    evidence: str = ""
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class Scan:
    """A scan session (may include multiple tool executions)."""
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    target: str = ""
    profile: str = "quick"
    status: ScanStatus = ScanStatus.PENDING
    tools_used: list[str] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    duration_ms: int = 0
    error: str | None = None

    @property
    def finding_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return counts
