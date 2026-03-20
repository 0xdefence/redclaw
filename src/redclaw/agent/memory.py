"""Working memory for scan sessions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MemoryEntry:
    """A single memory entry."""
    timestamp: datetime
    type: str  # thought, action, observation, finding
    content: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=data["type"],
            content=data["content"],
            metadata=data.get("metadata", {}),
        )


class WorkingMemory:
    """Session-level working memory for ReAct loops."""

    def __init__(self, max_entries: int = 50, max_tokens: int = 4000) -> None:
        self.max_entries = max_entries
        self.max_tokens = max_tokens
        self.entries: list[MemoryEntry] = []
        self.goal: str = ""
        self.current_phase: str = "init"
        self.key_findings: list[str] = []
        self.tools_executed: list[str] = []
        self.hypotheses: list[str] = []

    def set_goal(self, goal: str) -> None:
        """Set the current goal/objective."""
        self.goal = goal
        self.add("goal", f"Goal set: {goal}")

    def add(self, entry_type: str, content: str, metadata: dict | None = None) -> None:
        """Add an entry to memory."""
        entry = MemoryEntry(
            timestamp=datetime.now(timezone.utc),
            type=entry_type,
            content=content,
            metadata=metadata or {},
        )
        self.entries.append(entry)

        # Trim if over limit
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def add_thought(self, thought: str) -> None:
        """Add a thought/reasoning entry."""
        self.add("thought", thought)

    def add_action(self, tool_id: str, args: dict) -> None:
        """Add an action entry."""
        self.tools_executed.append(tool_id)
        self.add("action", f"Execute {tool_id}", {"tool_id": tool_id, "args": args})

    def add_observation(self, tool_id: str, result: str, findings_count: int = 0) -> None:
        """Add an observation from tool output."""
        self.add("observation", f"{tool_id} result: {result[:200]}...", {
            "tool_id": tool_id,
            "findings_count": findings_count,
        })

    def add_finding(self, finding: str, severity: str = "info") -> None:
        """Add a key finding."""
        self.key_findings.append(finding)
        self.add("finding", finding, {"severity": severity})

    def add_hypothesis(self, hypothesis: str) -> None:
        """Add a working hypothesis."""
        self.hypotheses.append(hypothesis)
        self.add("hypothesis", hypothesis)

    def set_phase(self, phase: str) -> None:
        """Update the current phase."""
        self.current_phase = phase
        self.add("phase", f"Phase: {phase}")

    def to_context(self) -> str:
        """Generate a compressed context string for the LLM."""
        context = {
            "goal": self.goal,
            "current_phase": self.current_phase,
            "tools_executed": self.tools_executed,
            "key_findings": self.key_findings[-10:],  # Last 10
            "hypotheses": self.hypotheses[-5:],  # Last 5
            "recent_actions": [
                e.to_dict() for e in self.entries[-10:]
                if e.type in ("action", "observation", "finding")
            ],
        }
        return json.dumps(context, indent=2)

    def get_recent(self, n: int = 10, entry_type: str | None = None) -> list[MemoryEntry]:
        """Get recent entries, optionally filtered by type."""
        entries = self.entries
        if entry_type:
            entries = [e for e in entries if e.type == entry_type]
        return entries[-n:]

    def clear(self) -> None:
        """Clear all memory."""
        self.entries = []
        self.goal = ""
        self.current_phase = "init"
        self.key_findings = []
        self.tools_executed = []
        self.hypotheses = []

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "goal": self.goal,
            "current_phase": self.current_phase,
            "key_findings": self.key_findings,
            "tools_executed": self.tools_executed,
            "hypotheses": self.hypotheses,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkingMemory":
        """Deserialize from dict."""
        memory = cls()
        memory.goal = data.get("goal", "")
        memory.current_phase = data.get("current_phase", "init")
        memory.key_findings = data.get("key_findings", [])
        memory.tools_executed = data.get("tools_executed", [])
        memory.hypotheses = data.get("hypotheses", [])
        memory.entries = [MemoryEntry.from_dict(e) for e in data.get("entries", [])]
        return memory
