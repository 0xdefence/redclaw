"""Tool registry — register and discover tools."""
from __future__ import annotations

from redclaw.tools.base import BaseTool
from redclaw.models import ToolMeta


class ToolRegistry:
    """Central registry of all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.meta.id] = tool

    def get(self, tool_id: str) -> BaseTool | None:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def get_or_raise(self, tool_id: str) -> BaseTool:
        """Get a tool by ID or raise KeyError."""
        tool = self._tools.get(tool_id)
        if tool is None:
            available = ", ".join(sorted(self._tools.keys()))
            raise KeyError(f"Tool '{tool_id}' not found. Available: {available}")
        return tool

    def list_tools(self) -> list[ToolMeta]:
        """List metadata for all registered tools."""
        return [t.meta for t in self._tools.values()]

    def list_ids(self) -> list[str]:
        """List all registered tool IDs."""
        return sorted(self._tools.keys())

    def filter_by_category(self, category: str) -> list[BaseTool]:
        """Get tools matching a category."""
        return [t for t in self._tools.values() if t.meta.category.value == category]

    @property
    def count(self) -> int:
        return len(self._tools)


def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools."""
    from redclaw.tools.nmap import NmapTool
    from redclaw.tools.nikto import NiktoTool
    from redclaw.tools.dns import DigTool, WhoisTool
    from redclaw.tools.nuclei import NucleiTool
    from redclaw.tools.gobuster import GobusterTool

    registry = ToolRegistry()
    registry.register(NmapTool())
    registry.register(NiktoTool())
    registry.register(DigTool())
    registry.register(WhoisTool())
    registry.register(NucleiTool())
    registry.register(GobusterTool())
    return registry
