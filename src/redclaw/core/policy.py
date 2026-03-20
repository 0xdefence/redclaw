"""Security policy — target validation and argument sanitisation."""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from redclaw.models import get_config


@dataclass
class PolicyResult:
    """Result of a policy check."""
    allowed: bool
    reason: str = ""
    warnings: list[str] | None = None


# Private/reserved CIDR blocks
_PRIVATE_CIDRS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Shell metacharacters that indicate injection
_INJECTION_PATTERN = re.compile(r"[;&|`$\n\r]")

# Disallowed argument prefixes (dangerous flags)
_DANGEROUS_FLAGS = {
    "nmap": ["--script=", "-iR", "--exclude-ports"],
    "nikto": ["-update"],
    "gobuster": ["-x .env"],
}

# Max argument string length
_MAX_ARG_LENGTH = 2000


class SecurityPolicy:
    """Validates targets and arguments before tool execution."""

    def __init__(self) -> None:
        self.config = get_config()

    def validate_target(self, target: str) -> PolicyResult:
        """Validate a scan target (hostname, IP, URL).

        Blocks:
        - Empty targets
        - Private/reserved IPs (unless config allows)
        - Localhost
        - Targets with shell metacharacters
        """
        if not target or not target.strip():
            return PolicyResult(allowed=False, reason="Target cannot be empty")

        target = target.strip()

        # Check for injection in target string
        if _INJECTION_PATTERN.search(target):
            return PolicyResult(
                allowed=False,
                reason=f"Target contains disallowed characters: {target!r}"
            )

        # Extract hostname from URL if needed
        hostname = target
        if "://" in target:
            try:
                parsed = urlparse(target)
                hostname = parsed.hostname or target
                if parsed.scheme not in ("http", "https"):
                    return PolicyResult(
                        allowed=False,
                        reason=f"Only http/https schemes allowed, got: {parsed.scheme}"
                    )
            except ValueError:
                return PolicyResult(allowed=False, reason="Invalid URL format")

        # Check for IP-based restrictions
        try:
            addr = ipaddress.ip_address(hostname)
            if not self.config.allow_private_networks:
                for cidr in _PRIVATE_CIDRS:
                    if addr in cidr:
                        return PolicyResult(
                            allowed=False,
                            reason=f"Target {hostname} is in private/reserved range {cidr}. "
                                   "Set REDCLAW_ALLOW_PRIVATE_NETWORKS=true to override."
                        )
        except ValueError:
            # Not an IP — it's a hostname, check for localhost aliases
            if hostname.lower() in ("localhost", "localhost.localdomain"):
                if not self.config.allow_private_networks:
                    return PolicyResult(
                        allowed=False,
                        reason="Scanning localhost is blocked. "
                               "Set REDCLAW_ALLOW_PRIVATE_NETWORKS=true to override."
                    )

        # Length check
        if len(target) > 253:  # Max DNS name length
            return PolicyResult(allowed=False, reason="Target too long (max 253 characters)")

        return PolicyResult(allowed=True)

    def validate_args(self, tool_id: str, args: list[str]) -> PolicyResult:
        """Validate tool arguments for injection and dangerous flags.

        Blocks:
        - Shell metacharacters in arguments
        - Known dangerous flags per tool
        - Excessively long argument strings
        """
        full_args = " ".join(args)

        # Length check
        if len(full_args) > _MAX_ARG_LENGTH:
            return PolicyResult(
                allowed=False,
                reason=f"Arguments too long ({len(full_args)} chars, max {_MAX_ARG_LENGTH})"
            )

        # Check each argument for injection
        for arg in args:
            if _INJECTION_PATTERN.search(arg):
                return PolicyResult(
                    allowed=False,
                    reason=f"Argument contains disallowed characters: {arg!r}"
                )

        # Check for dangerous flags
        dangerous = _DANGEROUS_FLAGS.get(tool_id, [])
        warnings: list[str] = []
        for flag in dangerous:
            if any(a.startswith(flag) for a in args):
                warnings.append(f"Potentially dangerous flag: {flag}")

        if warnings:
            return PolicyResult(allowed=True, warnings=warnings)

        return PolicyResult(allowed=True)

    def check_all(self, target: str, tool_id: str, args: list[str]) -> PolicyResult:
        """Run all validation checks. Returns first failure or success."""
        target_result = self.validate_target(target)
        if not target_result.allowed:
            return target_result

        args_result = self.validate_args(tool_id, args)
        if not args_result.allowed:
            return args_result

        # Merge warnings
        all_warnings = (target_result.warnings or []) + (args_result.warnings or [])
        return PolicyResult(allowed=True, warnings=all_warnings if all_warnings else None)
