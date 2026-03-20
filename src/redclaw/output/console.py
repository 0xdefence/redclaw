"""Console output facade — routes to appropriate output mode (normal/stealth/JSON)."""
from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from redclaw.models import Scan, ScanStatus, Severity
from redclaw.output.display import DisplayComponents, SEVERITY_COLORS, STATUS_ICONS
from redclaw.output.stealth import StealthOutput
from redclaw.output.json_output import JSONOutput

if TYPE_CHECKING:
    from redclaw.models import Finding


class OutputMode(str, Enum):
    """Output mode for CLI."""
    NORMAL = "normal"
    STEALTH = "stealth"
    JSON = "json"


# Global console instance
console = Console()


def print_scan_header(
    target: str,
    profile: str,
    tools: list[str] | None = None,
    scan_id: str | None = None,
    output_mode: OutputMode = OutputMode.NORMAL,
) -> None:
    """Print scan start header.

    Args:
        target: Target domain/IP
        profile: Scan profile name
        tools: List of tool IDs (if specified)
        scan_id: Scan ID (optional)
        output_mode: Output mode (normal, stealth, json)
    """
    if output_mode == OutputMode.JSON:
        # JSON mode: no header, progress goes to stderr
        return
    elif output_mode == OutputMode.STEALTH:
        # Stealth mode: minimal banner
        return  # Banner printed separately

    # Normal mode: use display components
    display = DisplayComponents(console)
    display.scan_header(target, profile, tools, scan_id)


def print_tool_progress(
    tool_id: str,
    status: str,
    detail: str = "",
    count: int | None = None,
    duration_ms: int | None = None,
    has_findings: bool = False,
    output_mode: OutputMode = OutputMode.NORMAL,
) -> None:
    """Print a tool execution progress line.

    Args:
        tool_id: Tool identifier
        status: running, success, failed, timeout, or blocked
        detail: Detail string (for running state)
        count: Number of results/findings
        duration_ms: Execution duration in milliseconds
        has_findings: True if there are security findings
        output_mode: Output mode (normal, stealth, json)
    """
    if output_mode == OutputMode.JSON:
        # JSON mode: no progress output
        return

    display = DisplayComponents(console)

    if status == "running":
        display.tool_progress_start(tool_id, detail)
    else:
        display.tool_progress_done(tool_id, status, count, duration_ms, has_findings)


def print_scan_summary(
    scan: Scan,
    verbose: bool = False,
    output_mode: OutputMode = OutputMode.NORMAL,
) -> None:
    """Print scan completion summary with findings.

    Args:
        scan: Scan object with results
        verbose: If True, show all INFO findings
        output_mode: Output mode (normal, stealth, json)
    """
    if output_mode == OutputMode.JSON:
        # JSON mode: output handled separately
        from redclaw.output.json_output import JSONOutput
        json_out = JSONOutput(compact=False)
        json_out.output_scan(scan)
        return
    elif output_mode == OutputMode.STEALTH:
        # Stealth mode: minimal output
        from redclaw.output.stealth import format_scan_stealth
        format_scan_stealth(scan, version="0.1.0")
        return

    # Normal mode: use display components
    display = DisplayComponents(console)
    display.scan_summary(scan)
    display.findings_list(scan.findings, verbose=verbose)


def print_scan_list(scans: list[Scan]) -> None:
    """Print a table of recent scans.

    Args:
        scans: List of Scan objects
    """
    table = Table(title="Recent Scans")
    table.add_column("ID", style="cyan", width=14)
    table.add_column("Target", max_width=30)
    table.add_column("Profile", width=10)
    table.add_column("Status", width=12)
    table.add_column("Tools", max_width=20)
    table.add_column("Findings", justify="right", width=10)
    table.add_column("Duration", justify="right", width=10)
    table.add_column("Date", width=20)

    for s in scans:
        # Status icon
        if s.status == ScanStatus.COMPLETED:
            status_icon = "[green]✓[/green]"
        elif s.status == ScanStatus.FAILED:
            status_icon = "[red]✗[/red]"
        elif s.status == ScanStatus.RUNNING:
            status_icon = "[yellow]⚡[/yellow]"
        else:
            status_icon = "[dim]⊘[/dim]"

        # Format values
        findings = str(len(s.findings)) if s.findings else "—"

        # Format duration
        if s.duration_ms:
            if s.duration_ms < 1000:
                duration = f"{s.duration_ms}ms"
            elif s.duration_ms < 60000:
                duration = f"{s.duration_ms / 1000:.1f}s"
            else:
                duration = f"{s.duration_ms // 60000}m {(s.duration_ms % 60000) // 1000}s"
        else:
            duration = "—"

        table.add_row(
            s.id,
            s.target,
            s.profile,
            f"{status_icon} {s.status.value}",
            ", ".join(s.tools_used[:3]),
            findings,
            duration,
            s.started_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


def print_scan_detail(scan: Scan, verbose: bool = False) -> None:
    """Print detailed view of a single scan.

    Args:
        scan: Scan object
        verbose: If True, show all findings including INFO
    """
    # Format duration
    if scan.duration_ms:
        if scan.duration_ms < 1000:
            duration = f"{scan.duration_ms}ms"
        elif scan.duration_ms < 60000:
            duration = f"{scan.duration_ms / 1000:.1f}s"
        else:
            duration = f"{scan.duration_ms // 60000}m {(scan.duration_ms % 60000) // 1000}s"
    else:
        duration = "—"

    console.print(Panel(
        f"[bold]ID:[/bold] {scan.id}\n"
        f"[bold]Target:[/bold] {scan.target}\n"
        f"[bold]Profile:[/bold] {scan.profile}\n"
        f"[bold]Status:[/bold] {scan.status.value}\n"
        f"[bold]Tools:[/bold] {', '.join(scan.tools_used)}\n"
        f"[bold]Duration:[/bold] {duration}\n"
        f"[bold]Started:[/bold] {scan.started_at.isoformat()}\n"
        f"[bold]Findings:[/bold] {len(scan.findings)}",
        title=f"[bold]Scan {scan.id}[/bold]",
        border_style="cyan",
    ))

    if scan.error:
        console.print(f"\n[red]Error: {scan.error}[/red]")

    if scan.findings:
        # Use display components for findings list
        display = DisplayComponents(console)
        display.findings_list(scan.findings, verbose=verbose)


def get_output_mode() -> OutputMode:
    """Detect output mode from environment/flags.

    Returns:
        OutputMode enum value
    """
    # Check for stealth mode
    if os.environ.get("REDCLAW_STEALTH", "").lower() in ("1", "true", "yes"):
        return OutputMode.STEALTH

    # Check for JSON mode
    if os.environ.get("REDCLAW_JSON", "").lower() in ("1", "true", "yes"):
        return OutputMode.JSON

    return OutputMode.NORMAL
