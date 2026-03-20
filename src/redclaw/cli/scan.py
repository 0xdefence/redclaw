"""Scan commands — scan, recon, portscan, webscan, aiscan."""
from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
@click.option("-p", "--profile", default="quick", help="Scan profile: quick, recon, full, web, stealth, vuln, enum")
@click.option("-t", "--tools", multiple=True, help="Override profile with specific tools (repeatable)")
@click.option("--ai", is_flag=True, help="Use AI to select tools based on target analysis")
@pass_context
def scan(ctx: ClawContext, target: str, profile: str, tools: tuple[str, ...], ai: bool) -> None:
    """Run a security scan against TARGET.

    Examples:
        claw scan example.com
        claw scan example.com --profile full
        claw scan example.com --tools nmap,nikto
        claw scan example.com --ai
    """
    if ai:
        _run_ai_scan(target, f"Comprehensive security scan of {target}", ctx.verbose)
    else:
        tool_list = list(tools) if tools else None
        _run_scan(target, profile, tool_list, ctx.verbose)


@click.command()
@click.argument("target")
@click.argument("objective", required=False, default=None)
@click.option("--max-steps", "-m", default=10, help="Maximum reasoning steps")
@pass_context
def aiscan(ctx: ClawContext, target: str, objective: str | None, max_steps: int) -> None:
    """AI-powered security scan with autonomous tool selection.

    Uses a ReAct (Reasoning and Acting) loop to autonomously select and run
    appropriate security tools based on the objective and findings.

    Requires OPENROUTER_API_KEY to be set.

    Examples:
        claw aiscan example.com
        claw aiscan example.com "find all web vulnerabilities"
        claw aiscan example.com "enumerate subdomains and open ports" --max-steps 5
    """
    objective = objective or f"Perform a comprehensive security assessment of {target}"
    _run_ai_scan(target, objective, ctx.verbose, max_steps)


def _run_ai_scan(target: str, objective: str, verbose: bool, max_steps: int = 10) -> None:
    """Run an AI-powered scan using ReAct loop."""
    from redclaw.agent import ReActLoop, ReActStep, get_agent
    from redclaw.agent.memory import WorkingMemory
    from redclaw.core.executor import DockerExecutor

    agent = get_agent()

    if not agent.is_available:
        console.print(Panel(
            "[red]AI features require an API key.[/red]\n\n"
            "Set one of:\n"
            "  • OPENROUTER_API_KEY\n"
            "  • REDCLAW_OPENROUTER_API_KEY\n\n"
            "Get a key at: https://openrouter.ai/",
            title="[bold red]API Key Required[/bold red]",
            border_style="red",
        ))
        raise SystemExit(1)

    console.print(Panel(
        f"[bold]Target:[/bold] {target}\n"
        f"[bold]Objective:[/bold] {objective}\n"
        f"[bold]Max steps:[/bold] {max_steps}",
        title="[bold cyan]AI-Powered Scan[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    # Setup
    executor = DockerExecutor()
    memory = WorkingMemory()
    react = ReActLoop(agent=agent, max_steps=max_steps)

    def on_step(step: ReActStep) -> None:
        """Callback for each ReAct step."""
        icon = "🤔" if step.type.value == "thought" else "⚡" if step.type.value == "action" else "✅"

        if step.thought:
            console.print(f"\n[dim]Step {step.step_num}:[/dim]")
            console.print(f"  {icon} [italic]{step.thought[:100]}{'...' if len(step.thought) > 100 else ''}[/italic]")

        if step.action and step.action != "finish":
            console.print(f"  → Running [bold cyan]{step.action}[/bold cyan]")

        if step.observation:
            obs_lines = step.observation.split("\n")[:3]
            for line in obs_lines:
                console.print(f"    [dim]{line[:80]}[/dim]")

    console.print("[bold]Starting ReAct loop...[/bold]")

    try:
        result = react.run(
            goal=objective,
            target=target,
            executor=executor,
            memory=memory,
            on_step=on_step,
        )
    except Exception as exc:
        console.print(f"\n[red]Error: {exc}[/red]")
        raise SystemExit(1)

    # Display results
    console.print()
    _display_ai_results(result)


def _display_ai_results(result) -> None:
    """Display AI scan results."""
    if result.success:
        console.print(Panel(
            f"[green]✓[/green] Completed in {result.total_duration_ms}ms\n"
            f"[bold]Steps:[/bold] {len(result.steps)}\n"
            f"[bold]Tools used:[/bold] {', '.join(result.tools_used) or 'None'}\n"
            f"[bold]Findings:[/bold] {len(result.findings)}",
            title="[bold green]Scan Complete[/bold green]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[red]✗[/red] {result.error}",
            title="[bold red]Scan Failed[/bold red]",
            border_style="red",
        ))
        return

    # Show final answer if available
    if result.final_answer:
        answer = result.final_answer
        if isinstance(answer, dict):
            if "summary" in answer:
                console.print(f"\n[bold]Summary:[/bold]\n{answer['summary']}")
            if "findings" in answer and answer["findings"]:
                console.print(f"\n[bold]Key Findings:[/bold]")
                for f in answer["findings"][:10]:
                    if isinstance(f, dict):
                        console.print(f"  • {f.get('title', f)}")
                    else:
                        console.print(f"  • {f}")

    # Show findings table
    if result.findings:
        console.print()
        table = Table(title="Findings")
        table.add_column("Severity", width=10)
        table.add_column("Tool", width=10)
        table.add_column("Title", max_width=50)

        severity_colors = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "low": "cyan",
            "info": "dim",
        }

        for f in result.findings[:20]:
            sev = f.get("severity", "info")
            color = severity_colors.get(sev, "white")
            table.add_row(
                f"[{color}]{sev.upper()}[/{color}]",
                f.get("tool_id", "?"),
                f.get("title", "Unknown")[:50],
            )

        if len(result.findings) > 20:
            table.add_row("...", "...", f"[dim]{len(result.findings) - 20} more findings[/dim]")

        console.print(table)


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
