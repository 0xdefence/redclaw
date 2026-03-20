"""Plan command — generate execution plans from natural language objectives."""
from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from redclaw.cli.main import pass_context, ClawContext


@click.command()
@click.argument("objective")
@click.option("--max-steps", "-m", default=6, help="Maximum steps in the plan")
@click.option("--execute", "-x", is_flag=True, help="Execute the plan after confirmation")
@click.option("--target", "-t", help="Target for execution (required with --execute)")
@pass_context
def plan(ctx: ClawContext, objective: str, max_steps: int, execute: bool, target: str | None) -> None:
    """Generate an execution plan for OBJECTIVE.

    Creates a workflow of tools to run based on your natural language objective.
    Use --execute to run the plan after confirmation.

    Examples:
        claw plan "scan a web server for vulnerabilities"
        claw plan "enumerate subdomains and check for open ports" --max-steps 4
        claw plan "full reconnaissance" --execute --target example.com
    """
    from redclaw.intelligence import WorkflowGenerator, ToolGraph

    console = Console()

    # Generate workflow
    generator = WorkflowGenerator()
    workflow = generator.generate(objective, max_steps=max_steps)

    # Display the plan
    _display_plan(workflow, console)

    # Execute if requested
    if execute:
        if not target:
            console.print("\n[red]Error: --target is required when using --execute[/red]")
            raise SystemExit(1)

        if workflow.requires_confirmation:
            console.print("\n[yellow]⚠ This plan includes intrusive scans that may affect the target.[/yellow]")

        if not click.confirm("\nExecute this plan?"):
            console.print("[dim]Plan cancelled.[/dim]")
            return

        _execute_plan(workflow, target, console, ctx.verbose)


def _display_plan(workflow, console: Console) -> None:
    """Display a workflow plan."""
    # Header
    console.print(Panel(
        f"[bold]Objective:[/bold] {workflow.objective}\n"
        f"[bold]Steps:[/bold] {len(workflow.steps)}\n"
        f"[bold]Estimated duration:[/bold] {workflow.estimated_duration_s}s\n"
        f"[bold]Requires confirmation:[/bold] {'Yes' if workflow.requires_confirmation else 'No'}",
        title="[bold cyan]Execution Plan[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    # Reasoning
    console.print(f"[dim]{workflow.reasoning}[/dim]")
    console.print()

    # Steps table
    table = Table(title="Plan Steps")
    table.add_column("Step", justify="center", width=6)
    table.add_column("Tool", style="cyan", width=12)
    table.add_column("Risk", width=10)
    table.add_column("Args", width=25)
    table.add_column("Depends On", width=15)
    table.add_column("Rationale", max_width=35)

    for i, step in enumerate(workflow.steps, 1):
        risk_color = {"passive": "green", "active": "yellow", "intrusive": "red"}.get(step.risk_level, "white")
        args_str = ", ".join(f"{k}={v}" for k, v in step.args.items()) if step.args else "—"
        deps_str = ", ".join(step.depends_on) if step.depends_on else "—"

        table.add_row(
            str(i),
            step.tool_id,
            f"[{risk_color}]{step.risk_level}[/{risk_color}]",
            args_str[:25],
            deps_str,
            step.rationale[:35],
        )

    console.print(table)

    # Dependency tree
    if any(step.depends_on for step in workflow.steps):
        console.print()
        tree = Tree("[bold]Execution Order[/bold]")
        _build_tree(workflow.steps, tree)
        console.print(tree)


def _build_tree(steps, tree) -> None:
    """Build a dependency tree for visualization."""
    # Find root steps (no dependencies)
    added = set()

    def add_step(step, parent):
        if step.tool_id in added:
            return
        added.add(step.tool_id)

        risk_color = {"passive": "green", "active": "yellow", "intrusive": "red"}.get(step.risk_level, "white")
        node = parent.add(f"[{risk_color}]{step.tool_id}[/{risk_color}]")

        # Find and add dependents
        for s in steps:
            if step.tool_id in s.depends_on:
                add_step(s, node)

    # Start with root nodes
    for step in steps:
        if not step.depends_on:
            add_step(step, tree)


def _execute_plan(workflow, target: str, console: Console, verbose: bool) -> None:
    """Execute a workflow plan."""
    from redclaw.intelligence import WorkflowGenerator
    from redclaw.core import ScanPlanner

    console.print(f"\n[bold]Executing plan against target: {target}[/bold]\n")

    # Convert workflow to tool list
    tool_ids = [step.tool_id for step in workflow.steps]

    # Build tool kwargs from workflow
    tool_kwargs = {}
    for step in workflow.steps:
        if step.args:
            tool_kwargs[step.tool_id] = step.args

    # Run via ScanPlanner
    planner = ScanPlanner()

    def on_start(tool_id: str, tgt: str) -> None:
        console.print(f"  [yellow]⚡[/yellow] Running [bold]{tool_id}[/bold]...")

    def on_done(tool_id: str, result) -> None:
        status = getattr(result, "status", "unknown")
        duration = getattr(result, "duration_ms", 0)
        findings = len(getattr(result, "findings", []))
        icon = "✓" if status == "success" else "✗"
        color = "green" if status == "success" else "red"
        console.print(f"  [{color}]{icon}[/{color}] [bold]{tool_id}[/bold] — {duration}ms, {findings} findings")

    try:
        scan = planner.run_scan(
            target=target,
            profile_name="custom",
            tools=tool_ids,
            on_tool_start=on_start,
            on_tool_done=on_done,
        )
    except Exception as exc:
        console.print(f"\n[red]Execution failed: {exc}[/red]")
        raise SystemExit(1)

    # Summary
    console.print()
    if scan.error:
        console.print(f"[red]Error: {scan.error}[/red]")
    else:
        console.print(f"[green]✓[/green] Plan completed in {scan.duration_ms}ms")
        console.print(f"  Scan ID: [cyan]{scan.id}[/cyan]")
        console.print(f"  Findings: {len(scan.findings)}")

        if scan.findings:
            counts = scan.finding_counts
            parts = []
            for sev in ["critical", "high", "medium", "low", "info"]:
                if counts.get(sev, 0) > 0:
                    parts.append(f"{counts[sev]} {sev}")
            console.print(f"  Breakdown: {', '.join(parts)}")
