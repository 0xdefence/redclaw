"""Scan commands — scan, recon, portscan, webscan."""
from __future__ import annotations

import click
from rich.console import Console

from redclaw.cli.main import pass_context, ClawContext

console = Console()


def _run_scan(target: str, profile: str, tools: list[str] | None, verbose: bool) -> None:
    """Shared scan execution logic."""
    from redclaw.core import ScanPlanner
    from redclaw.output.console import print_scan_header, print_tool_progress, print_scan_summary

    planner = ScanPlanner()
    print_scan_header(target, profile, tools)

    def on_start(tool_id: str, tgt: str) -> None:
        print_tool_progress(tool_id, "running", tgt)

    def on_done(tool_id: str, result: object) -> None:
        status = getattr(result, "status", "unknown")
        duration = getattr(result, "duration_ms", 0)
        findings_count = len(getattr(result, "findings", []))
        print_tool_progress(tool_id, status, f"{duration}ms, {findings_count} findings")

    try:
        scan = planner.run_scan(
            target=target,
            profile_name=profile,
            tools=tools or None,
            on_tool_start=on_start,
            on_tool_done=on_done,
        )
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    print_scan_summary(scan)


@click.command()
@click.argument("target")
@click.option("-p", "--profile", default="quick", help="Scan profile: quick, recon, full, web, stealth")
@click.option("-t", "--tools", multiple=True, help="Override profile with specific tools (repeatable)")
@pass_context
def scan(ctx: ClawContext, target: str, profile: str, tools: tuple[str, ...]) -> None:
    """Run a security scan against TARGET."""
    tool_list = list(tools) if tools else None
    _run_scan(target, profile, tool_list, ctx.verbose)


@click.command()
@click.argument("target")
@pass_context
def recon(ctx: ClawContext, target: str) -> None:
    """Passive reconnaissance — DNS + WHOIS lookup."""
    _run_scan(target, "recon", None, ctx.verbose)


@click.command()
@click.argument("target")
@click.option("-p", "--profile", default="quick", type=click.Choice(["quick", "full", "stealth", "udp"]))
@pass_context
def portscan(ctx: ClawContext, target: str, profile: str) -> None:
    """Port scan using Nmap."""
    _run_scan(target, profile, ["nmap"], ctx.verbose)


@click.command()
@click.argument("target")
@pass_context
def webscan(ctx: ClawContext, target: str) -> None:
    """Web vulnerability scan — Nmap + Nikto."""
    _run_scan(target, "web", None, ctx.verbose)
