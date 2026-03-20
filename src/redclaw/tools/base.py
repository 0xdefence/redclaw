"""Base tool abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from redclaw.models import ToolMeta, ToolResult, ToolCategory, RiskLevel, Finding

if TYPE_CHECKING:
    from redclaw.core.executor import DockerExecutor


class BaseTool(ABC):
    """Abstract base for all security tools."""

    meta: ToolMeta  # Subclasses must set this as a class variable

    def execute(self, executor: "DockerExecutor", target: str, **kwargs: object) -> ToolResult:
        """Run the tool and return parsed results.

        Args:
            executor: DockerExecutor instance
            target: Target host/IP/domain
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with raw_output, parsed dict, and findings list
        """
        args = self.build_args(target, **kwargs)
        result = executor.run_tool(
            binary=self.meta.binary,
            args=args,
            timeout=kwargs.get("timeout", self.meta.default_timeout),  # type: ignore[arg-type]
        )

        if result.status == "success" and result.raw_output.strip():
            result.parsed = self.parse_output(result.raw_output)
            result.findings = [f.__dict__ for f in self.extract_findings(result.parsed, target)]

        return result

    @abstractmethod
    def build_args(self, target: str, **kwargs: object) -> list[str]:
        """Build CLI arguments for the tool binary."""
        ...

    @abstractmethod
    def parse_output(self, raw: str) -> dict:
        """Parse raw stdout into a structured dict."""
        ...

    @abstractmethod
    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        """Extract security findings from parsed output."""
        ...
