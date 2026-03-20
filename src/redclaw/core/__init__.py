"""Core module."""
from redclaw.core.executor import DockerExecutor
from redclaw.core.policy import SecurityPolicy
from redclaw.core.profiles import get_profile, list_profiles, ScanProfile

# Import ScanPlanner lazily to avoid circular imports
def __getattr__(name: str) -> object:
    if name == "ScanPlanner":
        from redclaw.core.planner import ScanPlanner
        return ScanPlanner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "DockerExecutor",
    "ScanPlanner",
    "SecurityPolicy",
    "get_profile",
    "list_profiles",
    "ScanProfile",
]
