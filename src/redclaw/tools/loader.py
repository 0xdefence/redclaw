"""Custom tool loader — load tool definitions from YAML files."""
from __future__ import annotations

from pathlib import Path

from redclaw.tools.registry import ToolRegistry


def load_custom_tools(directory: Path, registry: ToolRegistry) -> int:
    """Load custom tool definitions from YAML files in a directory.

    Returns number of tools loaded.
    """
    # Post-MVP: implement YAML-based custom tool loading
    # For now, return 0 (no custom tools loaded)
    if not directory.exists():
        return 0

    count = 0
    for yaml_file in directory.glob("*.yaml"):
        # Future: parse YAML, create dynamic BaseTool subclass, register
        _ = yaml_file
        pass

    return count
