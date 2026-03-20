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
        description="Comprehensive scan — recon, ports, web vulns, directories",
        tools=["dig", "whois", "nmap", "nikto", "nuclei", "gobuster"],
        tool_kwargs={
            "nmap": {"profile": "full"},
            "gobuster": {"mode": "dir"},
        },
    ),
    "web": ScanProfile(
        name="web",
        description="Web application scan — nikto + nuclei + directory enumeration",
        tools=["nmap", "nikto", "nuclei", "gobuster"],
        tool_kwargs={
            "nmap": {"profile": "quick"},
            "gobuster": {"mode": "dir"},
        },
    ),
    "stealth": ScanProfile(
        name="stealth",
        description="Low-noise stealth scan — passive recon + slow port scan",
        tools=["dig", "whois", "nmap"],
        tool_kwargs={"nmap": {"profile": "stealth"}},
    ),
    "vuln": ScanProfile(
        name="vuln",
        description="Vulnerability scan — nuclei with CVE detection",
        tools=["nmap", "nuclei"],
        tool_kwargs={
            "nmap": {"profile": "quick"},
            "nuclei": {"tags": "cve"},
        },
    ),
    "enum": ScanProfile(
        name="enum",
        description="Enumeration — directory and subdomain brute-forcing",
        tools=["dig", "nmap", "gobuster"],
        tool_kwargs={
            "nmap": {"profile": "quick"},
            "gobuster": {"mode": "dir"},
        },
    ),
    "custom": ScanProfile(
        name="custom",
        description="Custom tool selection (use with --tools)",
        tools=[],
        tool_kwargs={},
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
