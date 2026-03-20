"""Tools command — list and search available tools."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from redclaw.cli.main import pass_context, ClawContext


@click.group(invoke_without_command=True)
@click.pass_context
def tools(ctx: click.Context) -> None:
    """List and search available tools."""
    if ctx.invoked_subcommand is None:
        _list_tools()


@tools.command("list")
def tools_list() -> None:
    """List all registered tools."""
    _list_tools()


@tools.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=5, help="Maximum results to show")
@click.option("--semantic/--simple", default=True, help="Use semantic search (default) or simple text match")
def tools_search(query: str, limit: int, semantic: bool) -> None:
    """Search for tools matching QUERY using semantic search.

    Examples:
        claw tools search "find open ports"
        claw tools search "web vulnerabilities" --limit 3
        claw tools search "dns" --simple
    """
    console = Console()

    if semantic:
        _semantic_search(query, limit, console)
    else:
        _simple_search(query, console)


def _semantic_search(query: str, limit: int, console: Console) -> None:
    """Perform semantic search using the intelligence layer."""
    from redclaw.intelligence import HybridSearch

    search = HybridSearch()
    results = search.search(query, limit=limit)

    if not results:
        console.print(f"[yellow]No tools matching '{query}'[/yellow]")
        return

    console.print(Panel(
        f"[bold]Query:[/bold] {query}\n[bold]Results:[/bold] {len(results)} tools found",
        title="[bold cyan]Semantic Search[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    table = Table(title="Search Results")
    table.add_column("Score", justify="right", width=8)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Name", width=20)
    table.add_column("Category", width=12)
    table.add_column("Risk", width=10)
    table.add_column("Rationale", max_width=45)

    for r in results:
        risk_color = {"passive": "green", "active": "yellow", "intrusive": "red"}.get(r.risk_level, "white")
        score_str = f"[bold]{r.score:.2f}[/bold]" if r.score >= 0.5 else f"{r.score:.2f}"

        table.add_row(
            score_str,
            r.tool_id,
            r.name,
            r.category,
            f"[{risk_color}]{r.risk_level}[/{risk_color}]",
            r.description[:45],
        )

    console.print(table)


def _simple_search(query: str, console: Console) -> None:
    """Perform simple text search."""
    from redclaw.tools import create_default_registry

    registry = create_default_registry()
    query_lower = query.lower()

    matches = [
        t for t in registry.list_tools()
        if query_lower in t.id.lower()
        or query_lower in t.name.lower()
        or query_lower in t.description.lower()
        or query_lower in t.category.value.lower()
    ]

    if not matches:
        console.print(f"[yellow]No tools matching '{query}'[/yellow]")
        return

    table = Table(title=f"Tools matching '{query}'")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Risk")
    table.add_column("Description", max_width=50)

    for t in matches:
        risk_color = {"passive": "green", "active": "yellow", "intrusive": "red"}.get(t.risk_level.value, "white")
        table.add_row(t.id, t.name, t.category.value, f"[{risk_color}]{t.risk_level.value}[/{risk_color}]", t.description[:50])

    console.print(table)


@tools.command("recommend")
@click.argument("objective")
@click.option("--limit", "-l", default=5, help="Maximum recommendations")
def tools_recommend(objective: str, limit: int) -> None:
    """Get tool recommendations for an OBJECTIVE.

    Examples:
        claw tools recommend "scan a web application for vulnerabilities"
        claw tools recommend "enumerate subdomains and open ports"
    """
    from redclaw.intelligence import ToolGraph

    console = Console()
    graph = ToolGraph()
    recommendations = graph.recommend_tools(objective, limit=limit)

    if not recommendations:
        console.print(f"[yellow]No recommendations for '{objective}'[/yellow]")
        return

    # Show intent analysis
    intents = graph.analyze_query(objective)
    intent_str = ", ".join(f"{cat.value}: {score:.2f}" for cat, score in intents.items() if score > 0.1)

    console.print(Panel(
        f"[bold]Objective:[/bold] {objective}\n[bold]Detected intents:[/bold] {intent_str or 'general'}",
        title="[bold cyan]Tool Recommendations[/bold cyan]",
        border_style="cyan",
    ))
    console.print()

    table = Table()
    table.add_column("Rank", justify="center", width=6)
    table.add_column("Score", justify="right", width=8)
    table.add_column("Tool", style="cyan", width=12)
    table.add_column("Rationale", max_width=55)

    for i, (tool_id, score, rationale) in enumerate(recommendations, 1):
        score_color = "green" if score >= 0.5 else "yellow" if score >= 0.3 else "dim"
        table.add_row(
            str(i),
            f"[{score_color}]{score:.2f}[/{score_color}]",
            tool_id,
            rationale[:55],
        )

    console.print(table)


def _list_tools() -> None:
    from redclaw.tools import create_default_registry

    registry = create_default_registry()
    console = Console()

    table = Table(title="Available Tools")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Risk")
    table.add_column("Timeout", justify="right")
    table.add_column("Description", max_width=50)

    for t in registry.list_tools():
        risk_color = {"passive": "green", "active": "yellow", "intrusive": "red"}.get(t.risk_level.value, "white")
        table.add_row(
            t.id, t.name, t.category.value,
            f"[{risk_color}]{t.risk_level.value}[/{risk_color}]",
            f"{t.default_timeout}s",
            t.description[:50],
        )

    console.print(table)
