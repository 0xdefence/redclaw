"""Results commands — list scans, view details, generate reports."""
from __future__ import annotations

import click
from rich.console import Console

from redclaw.cli.main import pass_context, ClawContext

console = Console()


@click.command()
@click.argument("scan_id", required=False)
@click.option("-n", "--limit", default=20, help="Number of recent scans to show")
@click.option("--target", default=None, help="Filter by target")
def results(scan_id: str | None, limit: int, target: str | None) -> None:
    """List recent scans or view a specific scan."""
    from redclaw.storage import Database
    from redclaw.output.console import print_scan_list, print_scan_detail

    db = Database()

    if scan_id:
        scan = db.get_scan(scan_id)
        if scan is None:
            console.print(f"[red]Scan '{scan_id}' not found[/red]")
            raise SystemExit(1)
        print_scan_detail(scan)
    else:
        scans = db.list_scans(limit=limit, target=target)
        if not scans:
            console.print("[yellow]No scans found. Run 'claw scan <target>' first.[/yellow]")
            return
        print_scan_list(scans)


@click.command()
@click.argument("scan_id")
@click.option("-f", "--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
@click.option("-o", "--output", "output_path", default=None, help="Output file path")
def report(scan_id: str, fmt: str, output_path: str | None) -> None:
    """Generate a report for a scan."""
    from redclaw.storage import Database
    from redclaw.output.report import generate_report

    db = Database()
    scan = db.get_scan(scan_id)
    if scan is None:
        console.print(f"[red]Scan '{scan_id}' not found[/red]")
        raise SystemExit(1)

    content = generate_report(scan, fmt)

    if output_path:
        with open(output_path, "w") as f:
            f.write(content)
        console.print(f"[green]Report saved to {output_path}[/green]")
    else:
        console.print(content)
