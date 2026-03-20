"""Tool-specific output formatters for terminal display."""
from __future__ import annotations

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from redclaw.models import ToolResult

console = Console()


def format_tool_output(result: ToolResult) -> None:
    """Pretty-print a tool result based on its tool_id."""
    formatter = _FORMATTERS.get(result.tool_id, _format_generic)
    formatter(result)


def _format_nmap(result: ToolResult) -> None:
    """Format nmap output with port table."""
    from rich.table import Table

    parsed = result.parsed
    hosts = parsed.get("hosts", [])

    for host in hosts:
        addr = host.get("address", result.target)
        hostname = host.get("hostname", "")
        title = f"Nmap — {addr}"
        if hostname:
            title += f" ({hostname})"

        ports = host.get("ports", [])
        if not ports:
            console.print(f"[dim]No open ports found on {addr}[/dim]")
            continue

        table = Table(title=title)
        table.add_column("Port", style="cyan", width=8)
        table.add_column("State", width=8)
        table.add_column("Service", width=12)
        table.add_column("Product", max_width=20)
        table.add_column("Version", max_width=15)

        for p in ports:
            table.add_row(
                f"{p['port']}/{p['protocol']}",
                f"[green]{p['state']}[/green]" if p["state"] == "open" else p["state"],
                p.get("service", ""),
                p.get("product", ""),
                p.get("version", ""),
            )
        console.print(table)


def _format_whois(result: ToolResult) -> None:
    """Format whois output as key-value panel."""
    parsed = result.parsed
    lines: list[str] = []
    if parsed.get("registrar"):
        lines.append(f"[bold]Registrar:[/bold] {parsed['registrar']}")
    if parsed.get("creation_date"):
        lines.append(f"[bold]Created:[/bold] {parsed['creation_date']}")
    if parsed.get("expiry_date"):
        lines.append(f"[bold]Expires:[/bold] {parsed['expiry_date']}")
    if parsed.get("name_servers"):
        lines.append(f"[bold]Name Servers:[/bold] {', '.join(parsed['name_servers'][:4])}")
    if parsed.get("registrant"):
        lines.append(f"[bold]Registrant:[/bold] {parsed['registrant']}")

    content = "\n".join(lines) if lines else result.raw_output[:500]
    console.print(Panel(content, title=f"WHOIS — {result.target}", border_style="blue"))


def _format_dig(result: ToolResult) -> None:
    """Format dig output as DNS record table."""
    from rich.table import Table

    records = result.parsed.get("records", [])
    if not records:
        console.print(f"[dim]No DNS records found for {result.target}[/dim]")
        return

    table = Table(title=f"DNS — {result.target}")
    table.add_column("Type", style="cyan", width=8)
    table.add_column("TTL", justify="right", width=8)
    table.add_column("Data", max_width=50)

    for rec in records:
        table.add_row(rec.get("type", ""), rec.get("ttl", ""), rec.get("data", ""))

    console.print(table)


def _format_generic(result: ToolResult) -> None:
    """Generic fallback — show raw output with syntax highlighting."""
    if len(result.raw_output) > 2000:
        output = result.raw_output[:2000] + f"\n... ({len(result.raw_output)} chars total)"
    else:
        output = result.raw_output

    console.print(Panel(output, title=f"{result.tool_id} — {result.target}", border_style="dim"))


_FORMATTERS: dict[str, object] = {
    "nmap": _format_nmap,
    "whois": _format_whois,
    "dig": _format_dig,
    "nikto": _format_generic,
}
