"""Rich console output helpers."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from redclaw.models import Scan, ScanStatus, Severity

console = Console()

SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
    "info": "dim",
}

STATUS_ICONS = {
    "pending": "[dim]⏳[/dim]",
    "running": "[yellow]⚡[/yellow]",
    "completed": "[green]✓[/green]",
    "failed": "[red]✗[/red]",
    "cancelled": "[dim]⊘[/dim]",
}


def print_scan_header(target: str, profile: str, tools: list[str] | None) -> None:
    """Print scan start banner."""
    tool_str = ", ".join(tools) if tools else f"profile: {profile}"
    console.print(Panel(
        f"[bold]Target:[/bold] {target}\n[bold]Tools:[/bold] {tool_str}",
        title="[bold cyan]RedClaw Scan[/bold cyan]",
        border_style="cyan",
    ))
    console.print()


def print_tool_progress(tool_id: str, status: str, detail: str) -> None:
    """Print a tool execution progress line."""
    icon = "⚡" if status == "running" else ("✓" if status == "success" else "✗")
    color = "yellow" if status == "running" else ("green" if status == "success" else "red")
    console.print(f"  [{color}]{icon}[/{color}] [bold]{tool_id}[/bold] — {detail}")


def print_scan_summary(scan: Scan) -> None:
    """Print scan completion summary with findings table."""
    console.print()

    # Status line
    status_icon = STATUS_ICONS.get(scan.status.value, "?")
    console.print(f"{status_icon} Scan [bold]{scan.id}[/bold] — {scan.status.value} in {scan.duration_ms}ms")

    if scan.error:
        console.print(f"  [red]Error: {scan.error}[/red]")
        return

    if not scan.findings:
        console.print("  [dim]No findings[/dim]")
        return

    # Findings summary
    counts = scan.finding_counts
    parts: list[str] = []
    for sev in ["critical", "high", "medium", "low", "info"]:
        if counts.get(sev, 0) > 0:
            color = SEVERITY_COLORS[sev]
            parts.append(f"[{color}]{counts[sev]} {sev}[/{color}]")
    console.print(f"  Findings: {', '.join(parts)}")
    console.print()

    # Findings table (skip info if too many)
    show_info = len(scan.findings) <= 20
    table = Table(title="Findings", show_lines=True)
    table.add_column("Severity", width=10)
    table.add_column("Tool", width=8)
    table.add_column("Title", max_width=60)
    table.add_column("Evidence", max_width=40)

    for f in scan.findings:
        if not show_info and f.severity == Severity.INFO:
            continue
        color = SEVERITY_COLORS.get(f.severity.value, "white")
        table.add_row(
            f"[{color}]{f.severity.value.upper()}[/{color}]",
            f.tool_id,
            f.title[:60],
            f.evidence[:40] if f.evidence else "",
        )

    if not show_info:
        info_count = counts.get("info", 0)
        if info_count > 0:
            table.add_row("[dim]INFO[/dim]", "—", f"[dim]{info_count} informational findings hidden[/dim]", "")

    console.print(table)


def print_scan_list(scans: list[Scan]) -> None:
    """Print a table of recent scans."""
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
        status_icon = STATUS_ICONS.get(s.status.value, "?")
        findings = str(len(s.findings)) if s.findings else "—"
        duration = f"{s.duration_ms}ms" if s.duration_ms else "—"
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


def print_scan_detail(scan: Scan) -> None:
    """Print detailed view of a single scan."""
    console.print(Panel(
        f"[bold]ID:[/bold] {scan.id}\n"
        f"[bold]Target:[/bold] {scan.target}\n"
        f"[bold]Profile:[/bold] {scan.profile}\n"
        f"[bold]Status:[/bold] {scan.status.value}\n"
        f"[bold]Tools:[/bold] {', '.join(scan.tools_used)}\n"
        f"[bold]Duration:[/bold] {scan.duration_ms}ms\n"
        f"[bold]Started:[/bold] {scan.started_at.isoformat()}\n"
        f"[bold]Findings:[/bold] {len(scan.findings)}",
        title=f"[bold]Scan {scan.id}[/bold]",
        border_style="cyan",
    ))

    if scan.error:
        console.print(f"\n[red]Error: {scan.error}[/red]")

    if scan.findings:
        console.print()
        print_scan_summary(scan)
