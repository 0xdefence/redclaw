"""Tools command — list and search available tools."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

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
def tools_search(query: str) -> None:
    """Search for tools matching QUERY."""
    from redclaw.tools import create_default_registry

    registry = create_default_registry()
    console = Console()
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
