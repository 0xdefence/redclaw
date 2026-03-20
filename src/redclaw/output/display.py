"""Display components for RedClaw CLI output following the UX specification."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from redclaw.models import Scan, Finding, Severity

# Severity colors (from spec)
SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
    "info": "dim",
}

# Status icons (from spec)
STATUS_ICONS = {
    "running": "⚡",
    "success": "✓",
    "failed": "✗",
    "blocked": "⊘",
    "timeout": "⏱",
}


class DisplayComponents:
    """Display components for the RedClaw CLI following the UX specification."""

    def __init__(self, console: Console | None = None):
        """Initialize display components.

        Args:
            console: Rich console instance (creates one if not provided)
        """
        self.console = console or Console()

    def scan_header(
        self,
        target: str,
        profile: str,
        tools: list[str] | None = None,
        scan_id: str | None = None,
    ) -> None:
        """Print scan header box.

        Format (from spec):
        ┌──────────────────────────────────────────────┐
        │  Target: example.com    Profile: full       │
        │  Tools:  nmap, nuclei, ffuf                  │
        │  ID:     a8f2c1                              │
        └──────────────────────────────────────────────┘

        Args:
            target: Target domain/IP
            profile: Scan profile name
            tools: List of tool IDs (if specified)
            scan_id: Scan ID (optional)
        """
        lines = []
        lines.append(f"[bold white]Target:[/bold white] {target}    [bold white]Profile:[/bold white] {profile}")

        if tools:
            tool_str = ", ".join(tools)
            lines.append(f"[bold white]Tools:[/bold white]  {tool_str}")
        else:
            lines.append(f"[dim]Using profile: {profile}[/dim]")

        if scan_id:
            lines.append(f"[dim]ID:      {scan_id}[/dim]")

        self.console.print(
            Panel(
                "\n".join(lines),
                border_style="cyan",
                padding=(0, 1),
            )
        )
        self.console.print()

    def tool_progress_start(self, tool_id: str, description: str) -> None:
        """Print tool start progress line.

        Format: ⚡ toolname  running description...

        Args:
            tool_id: Tool identifier
            description: What the tool is doing
        """
        # Pad tool name to 8 chars
        tool_name = f"{tool_id:<8}"
        self.console.print(
            f"  [yellow]{STATUS_ICONS['running']}[/yellow] [bold white]{tool_name}[/bold white] [dim]{description}[/dim]"
        )

    def tool_progress_done(
        self,
        tool_id: str,
        status: str,
        count: int | None = None,
        duration_ms: int | None = None,
        has_findings: bool = False,
    ) -> None:
        """Print tool completion progress line.

        Format: ✓ toolname  5 records — 230ms

        Args:
            tool_id: Tool identifier
            status: success, failed, timeout, or blocked
            count: Number of results/findings
            duration_ms: Execution duration in milliseconds
            has_findings: True if there are security findings (colors count red)
        """
        # Pad tool name to 8 chars
        tool_name = f"{tool_id:<8}"

        # Get status icon and color
        icon = STATUS_ICONS.get(status, "?")
        if status == "success":
            icon_markup = f"[green]{icon}[/green]"
        elif status == "failed":
            icon_markup = f"[red]{icon}[/red]"
        elif status == "timeout":
            icon_markup = f"[red]{icon}[/red]"
        elif status == "blocked":
            icon_markup = f"[yellow]{icon}[/yellow]"
        else:
            icon_markup = icon

        # Build result text
        parts = []
        if count is not None:
            # Color count red if there are findings, green otherwise
            if has_findings:
                parts.append(f"[red]{count}[/red]")
            else:
                parts.append(f"[green]{count}[/green]")

            # Pluralize based on context
            if tool_id == "nmap":
                parts[0] += " " + ("port" if count == 1 else "ports")
            elif tool_id in ("dig", "dns"):
                parts[0] += " " + ("record" if count == 1 else "records")
            elif tool_id in ("nuclei", "nikto"):
                parts[0] += " " + ("finding" if count == 1 else "findings")
            else:
                parts[0] += " " + ("result" if count == 1 else "results")

        if duration_ms is not None:
            parts.append(f"[dim]{self._format_duration(duration_ms)}[/dim]")

        result_text = " — ".join(parts) if parts else ""

        self.console.print(
            f"  {icon_markup} [bold white]{tool_name}[/bold white] {result_text}"
        )

    def scan_summary(self, scan: Scan) -> None:
        """Print scan summary box.

        Format (from spec):
        ┌──────────────────────────────────────────────┐
        │  ✓ Scan complete — 77.7s  ID: a8f2c1        │
        │  1 HIGH  1 MEDIUM  3 LOW  12 INFO           │
        └──────────────────────────────────────────────┘

        Args:
            scan: Scan object with results
        """
        from redclaw.models import ScanStatus

        # Status line
        if scan.status == ScanStatus.COMPLETED:
            status_text = f"[green]✓[/green] Scan complete"
        elif scan.status == ScanStatus.FAILED:
            status_text = f"[red]✗[/red] Scan failed"
        else:
            status_text = f"Scan {scan.status.value}"

        duration_text = self._format_duration(scan.duration_ms) if scan.duration_ms else "—"
        status_line = f"{status_text} — [bold white]{duration_text}[/bold white]  [dim]ID: {scan.id}[/dim]"

        # Findings summary
        counts = scan.finding_counts
        severity_parts = []
        for sev in ["critical", "high", "medium", "low", "info"]:
            if counts.get(sev, 0) > 0:
                color = SEVERITY_COLORS[sev]
                count = counts[sev]
                severity_parts.append(f"[{color}]{count} {sev.upper()}[/{color}]")

        findings_line = "  ".join(severity_parts) if severity_parts else "[dim]No findings[/dim]"

        # Build panel
        content = status_line
        if not scan.error:
            content += f"\n{findings_line}"
        else:
            content += f"\n[red]Error: {scan.error}[/red]"

        self.console.print()
        self.console.print(
            Panel(
                content,
                border_style="cyan" if scan.status == ScanStatus.COMPLETED else "red",
                padding=(0, 1),
            )
        )

    def findings_list(
        self,
        findings: list[Finding],
        verbose: bool = False,
    ) -> None:
        """Print findings list with progressive disclosure.

        Format (from spec):
          HIGH     RCE via path traversal (CVE-2024-1234)
                   nuclei • /api/v1/upload

          LOW      Backup file found: /backup.sql.bak
                   ffuf • Status 200, 12KB

          INFO     + 12 informational findings (use -v to show)

        Args:
            findings: List of Finding objects
            verbose: If True, show all INFO findings (default: collapse if > 10 total)
        """
        if not findings:
            return

        # Sort findings: critical → high → medium → low → info
        # Secondary sort: by tool_id, then title
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sorted_findings = sorted(
            findings,
            key=lambda f: (
                severity_order.get(f.severity.value, 99),
                f.tool_id,
                f.title,
            ),
        )

        # Count INFO findings
        info_count = sum(1 for f in findings if f.severity.value == "info")
        total_count = len(findings)

        # Progressive disclosure: collapse INFO if many findings
        # Spec says: "INFO findings collapsed if > 10 total findings"
        # Clarified to: collapse if info_count > 10 AND total_count > 10
        collapse_info = (info_count > 10 and total_count > 10) and not verbose

        self.console.print()

        shown_count = 0
        for finding in sorted_findings:
            # Skip INFO if collapsing
            if collapse_info and finding.severity.value == "info":
                continue

            # Severity label (8 chars wide, colored)
            sev_label = finding.severity.value.upper()
            sev_color = SEVERITY_COLORS.get(finding.severity.value, "white")
            sev_text = f"[{sev_color}]{sev_label:<8}[/{sev_color}]"

            # Title (bold white)
            title = f"[bold white]{finding.title}[/bold white]"

            # First line: severity + title
            self.console.print(f"  {sev_text} {title}")

            # Second line: tool + evidence (indented, dim)
            evidence_parts = [finding.tool_id]
            if finding.evidence:
                evidence_parts.append(finding.evidence[:60])  # Truncate long evidence

            evidence_text = " • ".join(evidence_parts)
            self.console.print(f"           [dim]{evidence_text}[/dim]")

            # Blank line between findings
            self.console.print()
            shown_count += 1

        # Show collapsed INFO count
        if collapse_info and info_count > 0:
            self.console.print(f"  [dim]INFO      + {info_count} informational findings (use -v to show)[/dim]")
            self.console.print()

    def error_display(self, error_type: str, message: str, suggestions: list[str] | None = None) -> None:
        """Display formatted error with suggestions.

        Args:
            error_type: Error category (e.g., "Docker not running")
            message: Main error message
            suggestions: Optional list of recovery suggestions
        """
        content = f"[red]✗ {error_type}[/red]\n\n{message}"

        if suggestions:
            content += "\n\n" + "\n".join(suggestions)

        self.console.print()
        self.console.print(
            Panel(
                content,
                border_style="red",
                padding=(1, 2),
            )
        )

    @staticmethod
    def _format_duration(duration_ms: int) -> str:
        """Format duration according to spec: ms < 1000, s < 60, m >= 60.

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            Formatted string (e.g., "230ms", "1.2s", "2m 15s")
        """
        if duration_ms < 1000:
            return f"{duration_ms}ms"
        elif duration_ms < 60000:
            seconds = duration_ms / 1000
            return f"{seconds:.1f}s"
        else:
            minutes = duration_ms // 60000
            seconds = (duration_ms % 60000) / 1000
            if seconds > 0:
                return f"{minutes}m {seconds:.0f}s"
            else:
                return f"{minutes}m"
