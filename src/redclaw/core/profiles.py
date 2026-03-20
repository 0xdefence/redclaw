"""Predefined scan profiles."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScanProfile:
    """A predefined combination of tools and settings."""
    name: str
    description: str
    tools: list[str]
    tool_kwargs: dict[str, dict] = field(default_factory=dict)


PROFILES: dict[str, ScanProfile] = {
    "quick": ScanProfile(
        name="quick",
        description="Fast port scan + DNS lookup",
        tools=["dig", "nmap"],
        tool_kwargs={"nmap": {"profile": "quick"}},
    ),
    "recon": ScanProfile(
        name="recon",
        description="Passive reconnaissance — DNS + WHOIS",
        tools=["dig", "whois"],
        tool_kwargs={"dig": {"record_type": "ANY"}},
    ),
    "full": ScanProfile(
        name="full",
        description="Full scan — DNS, WHOIS, port scan, web vuln scan",
        tools=["dig", "whois", "nmap", "nikto"],
        tool_kwargs={
            "nmap": {"profile": "full"},
        },
    ),
    "web": ScanProfile(
        name="web",
        description="Web vulnerability scan — port scan + nikto",
        tools=["nmap", "nikto"],
        tool_kwargs={"nmap": {"profile": "quick"}},
    ),
    "stealth": ScanProfile(
        name="stealth",
        description="Low-noise stealth scan",
        tools=["dig", "nmap"],
        tool_kwargs={"nmap": {"profile": "stealth"}},
    ),
}


def get_profile(name: str) -> ScanProfile:
    """Get a scan profile by name."""
    if name not in PROFILES:
        available = ", ".join(sorted(PROFILES.keys()))
        raise ValueError(f"Unknown profile '{name}'. Available: {available}")
    return PROFILES[name]


def list_profiles() -> list[ScanProfile]:
    """List all available profiles."""
    return list(PROFILES.values())
