"""JSON output mode — structured output to stdout, progress to stderr."""
from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redclaw.models import Scan, Finding


class JSONOutput:
    """JSON output handler for structured scan results.

    Format (from spec):
    {
      "scan_id": "a8f2c1",
      "target": "example.com",
      "profile": "full",
      "status": "completed",
      "duration_ms": 77700,
      "tools_used": ["dig", "whois", "nmap", "nuclei", "ffuf"],
      "finding_counts": {
        "critical": 0,
        "high": 1,
        "medium": 1,
        "low": 3,
        "info": 12
      },
      "findings": [...]
    }

    Rules:
    - Single JSON object to stdout, nothing else
    - All progress/logging goes to stderr
    - Pretty-printed by default
    - --compact flag for single-line output
    """

    def __init__(self, compact: bool = False):
        """Initialize JSON output handler.

        Args:
            compact: If True, output single-line JSON (no pretty-printing)
        """
        self.compact = compact

    def progress(self, message: str) -> None:
        """Print progress message to stderr (doesn't affect JSON output).

        Args:
            message: Progress message
        """
        print(message, file=sys.stderr)

    def output_scan(self, scan: Scan) -> None:
        """Output complete scan as JSON to stdout.

        Args:
            scan: Scan object with results
        """
        data = self._scan_to_dict(scan)

        if self.compact:
            # Single line, no indentation
            json.dump(data, sys.stdout, separators=(",", ":"))
        else:
            # Pretty-printed with 2-space indentation
            json.dump(data, sys.stdout, indent=2)

        # Always end with newline
        print()

    def _scan_to_dict(self, scan: Scan) -> dict[str, Any]:
        """Convert Scan object to JSON-serializable dictionary.

        Args:
            scan: Scan object

        Returns:
            Dictionary matching the spec schema
        """
        return {
            "scan_id": scan.id,
            "target": scan.target,
            "profile": scan.profile,
            "status": scan.status.value,
            "duration_ms": scan.duration_ms,
            "started_at": scan.started_at.isoformat(),
            "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
            "tools_used": scan.tools_used,
            "finding_counts": scan.finding_counts,
            "findings": [self._finding_to_dict(f) for f in scan.findings],
            "error": scan.error,
        }

    def _finding_to_dict(self, finding: Finding) -> dict[str, Any]:
        """Convert Finding object to JSON-serializable dictionary.

        Args:
            finding: Finding object

        Returns:
            Dictionary with finding data
        """
        return {
            "severity": finding.severity.value,
            "title": finding.title,
            "description": finding.description,
            "tool_id": finding.tool_id,
            "target": finding.target,
            "evidence": finding.evidence,
            "remediation": finding.remediation,
            "references": finding.references,
            "metadata": finding.metadata,
        }


def format_scan_json(scan: Scan, compact: bool = False) -> str:
    """Format scan as JSON string (for testing/internal use).

    Args:
        scan: Scan object
        compact: If True, output single-line JSON

    Returns:
        JSON string
    """
    output = JSONOutput(compact=compact)
    data = output._scan_to_dict(scan)

    if compact:
        return json.dumps(data, separators=(",", ":"))
    else:
        return json.dumps(data, indent=2)
