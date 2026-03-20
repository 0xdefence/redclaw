"""Stealth mode output — minimal, parseable, no colors or formatting."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redclaw.models import Scan, Finding

# Stage categories for tool grouping
TOOL_STAGES = {
    # Recon tools
    "dig": "RECON",
    "dns": "RECON",
    "whois": "RECON",
    "dnsenum": "RECON",

    # Port scanning
    "nmap": "SCAN",
    "masscan": "SCAN",

    # Vulnerability scanning
    "nuclei": "VULN",
    "nikto": "VULN",

    # Enumeration/fuzzing
    "ffuf": "ENUM",
    "gobuster": "ENUM",
    "dirb": "ENUM",
    "dirbuster": "ENUM",
}


class StealthOutput:
    """Stealth mode output handler — minimal, parseable, no rich formatting.

    Format (from spec):
        redclaw v0.1.0
        [RECON] 5 dns records, 1 whois result
        [SCAN]  3 open ports (80,443,8080)
        [VULN]  2 findings (1 high, 1 medium)
        [ENUM]  8 endpoints discovered
        [DONE]  17 findings total

    Rules:
        - One line per stage, not per tool
        - Stage tags: [RECON], [SCAN], [VULN], [ENUM], [DONE]
        - No color codes
        - No box-drawing characters
        - Suitable for piping to log files
    """

    def __init__(self, version: str = "0.1.0"):
        """Initialize stealth output.

        Args:
            version: RedClaw version string
        """
        self.version = version
        self.stage_results: dict[str, list[str]] = {
            "RECON": [],
            "SCAN": [],
            "VULN": [],
            "ENUM": [],
        }

    def banner(self) -> None:
        """Print minimal banner."""
        print(f"redclaw v{self.version}")

    def tool_result(self, tool_id: str, count: int, detail: str | None = None) -> None:
        """Record a tool result (accumulated by stage).

        Args:
            tool_id: Tool identifier
            count: Number of results
            detail: Optional detail string (e.g., "80,443,8080")
        """
        stage = TOOL_STAGES.get(tool_id, "ENUM")

        # Format based on tool type
        if tool_id == "dig":
            text = f"{count} dns {'record' if count == 1 else 'records'}"
        elif tool_id == "whois":
            text = "whois result" if count > 0 else "no whois data"
        elif tool_id == "nmap":
            text = f"{count} open {'port' if count == 1 else 'ports'}"
            if detail:
                text += f" ({detail})"
        elif tool_id in ("nuclei", "nikto"):
            text = f"{count} {'finding' if count == 1 else 'findings'}"
            if detail:  # detail = "1 high, 1 medium"
                text += f" ({detail})"
        elif tool_id in ("ffuf", "gobuster"):
            text = f"{count} endpoints discovered"
        else:
            text = f"{count} results from {tool_id}"

        self.stage_results[stage].append(text)

    def flush_stage(self, stage: str) -> None:
        """Print accumulated results for a stage.

        Args:
            stage: Stage name (RECON, SCAN, VULN, ENUM)
        """
        if stage not in self.stage_results:
            return

        results = self.stage_results[stage]
        if not results:
            return

        # Combine results for this stage
        combined = ", ".join(results)
        print(f"[{stage}] {combined}")

        # Clear after printing
        self.stage_results[stage] = []

    def flush_all(self) -> None:
        """Print all accumulated results."""
        for stage in ["RECON", "SCAN", "VULN", "ENUM"]:
            self.flush_stage(stage)

    def scan_complete(
        self,
        total_findings: int,
        severity_breakdown: dict[str, int] | None = None,
    ) -> None:
        """Print scan completion summary.

        Args:
            total_findings: Total number of findings
            severity_breakdown: Optional severity counts
        """
        # Flush any remaining staged results
        self.flush_all()

        # Final summary
        if severity_breakdown:
            # Build severity string: "1 critical, 2 high, 3 medium"
            parts = []
            for sev in ["critical", "high", "medium", "low", "info"]:
                count = severity_breakdown.get(sev, 0)
                if count > 0:
                    parts.append(f"{count} {sev}")
            sev_str = ", ".join(parts) if parts else "0"
            print(f"[DONE]  {total_findings} findings total ({sev_str})")
        else:
            print(f"[DONE]  {total_findings} findings total")

    def error(self, message: str) -> None:
        """Print error message.

        Args:
            message: Error message
        """
        print(f"[ERROR] {message}", file=sys.stderr)


def format_scan_stealth(scan: Scan, version: str = "0.1.0") -> None:
    """Format a complete scan in stealth mode.

    Args:
        scan: Scan object
        version: RedClaw version
    """
    output = StealthOutput(version)
    output.banner()

    # Group results by stage
    stage_counts: dict[str, dict[str, int]] = {
        "RECON": {},
        "SCAN": {},
        "VULN": {},
        "ENUM": {},
    }

    # Process findings
    for finding in scan.findings:
        stage = TOOL_STAGES.get(finding.tool_id, "ENUM")
        tool_id = finding.tool_id

        if tool_id not in stage_counts[stage]:
            stage_counts[stage][tool_id] = 0
        stage_counts[stage][tool_id] += 1

    # Print stage results
    for stage in ["RECON", "SCAN", "VULN", "ENUM"]:
        if not stage_counts[stage]:
            continue

        # Combine tool counts for this stage
        for tool_id, count in stage_counts[stage].items():
            # For vulnerability stage, add severity breakdown
            if stage == "VULN":
                sev_counts = {}
                for f in scan.findings:
                    if f.tool_id == tool_id:
                        sev = f.severity.value
                        sev_counts[sev] = sev_counts.get(sev, 0) + 1

                # Build severity detail string
                parts = []
                for sev in ["critical", "high", "medium", "low"]:
                    if sev in sev_counts:
                        parts.append(f"{sev_counts[sev]} {sev}")
                detail = ", ".join(parts) if parts else None

                output.tool_result(tool_id, count, detail)
            else:
                output.tool_result(tool_id, count)

    # Flush and complete
    output.flush_all()
    output.scan_complete(len(scan.findings), scan.finding_counts)
