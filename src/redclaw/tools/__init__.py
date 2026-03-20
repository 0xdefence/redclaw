"""Tool wrappers and registry."""
from redclaw.tools.base import BaseTool
from redclaw.tools.registry import ToolRegistry, create_default_registry
from redclaw.tools.nmap import NmapTool
from redclaw.tools.nikto import NiktoTool
from redclaw.tools.dns import DigTool, WhoisTool
from redclaw.tools.nuclei import NucleiTool
from redclaw.tools.gobuster import GobusterTool

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "create_default_registry",
    "NmapTool",
    "NiktoTool",
    "DigTool",
    "WhoisTool",
    "NucleiTool",
    "GobusterTool",
]
