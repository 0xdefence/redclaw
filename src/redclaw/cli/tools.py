"""Tools command — list, search, and manage available tools."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from redclaw.cli.main import pass_context, ClawContext


@click.group(invoke_without_command=True)
@click.pass_context
def tools(ctx: click.Context) -> None:
    """List, search, and manage available tools."""
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
    from redclaw.tools.loader import load_custom_tools, get_plugin_directory

    registry = create_default_registry()

    # Load custom plugins
    plugin_dir = get_plugin_directory()
    custom_count = load_custom_tools(plugin_dir, registry)

    console = Console()

    table = Table(title=f"Available Tools ({registry.count} total, {custom_count} custom)")
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


# ─── Plugin Management Commands ───────────────────────────────────────────────


@tools.command("add")
@click.argument("yaml_file", type=click.Path(exists=True, path_type=Path))
@click.option("--force", "-f", is_flag=True, help="Overwrite existing tool")
def tools_add(yaml_file: Path, force: bool) -> None:
    """Add a custom tool from a YAML definition file.

    The YAML file should define the tool's id, binary, args, and output parsing rules.

    Examples:
        claw tools add my_scanner.yaml
        claw tools add /path/to/custom_tool.yaml --force
    """
    from redclaw.tools.loader import install_tool_yaml, load_tool_from_yaml

    console = Console()

    # Preview the tool
    tool = load_tool_from_yaml(yaml_file)
    if tool:
        console.print(Panel(
            f"[bold]ID:[/bold] {tool.meta.id}\n"
            f"[bold]Name:[/bold] {tool.meta.name}\n"
            f"[bold]Binary:[/bold] {tool.meta.binary}\n"
            f"[bold]Category:[/bold] {tool.meta.category.value}\n"
            f"[bold]Risk:[/bold] {tool.meta.risk_level.value}\n"
            f"[bold]Description:[/bold] {tool.meta.description}",
            title="[bold cyan]Tool Preview[/bold cyan]",
            border_style="cyan",
        ))

    success, message = install_tool_yaml(yaml_file, overwrite=force)

    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]✗[/red] {message}")
        raise SystemExit(1)


@tools.command("remove")
@click.argument("tool_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def tools_remove(tool_id: str, yes: bool) -> None:
    """Remove a custom tool plugin.

    Only custom tools installed via 'claw tools add' can be removed.
    Built-in tools cannot be removed.

    Examples:
        claw tools remove my_custom_scanner
        claw tools remove custom_tool --yes
    """
    from redclaw.tools.loader import uninstall_tool, list_installed_tools

    console = Console()

    # Check if tool exists in plugins
    installed = list_installed_tools()
    tool_ids = [t[0] for t in installed]

    if tool_id not in tool_ids:
        console.print(f"[red]✗[/red] Tool '{tool_id}' is not a custom plugin (or doesn't exist)")
        console.print(f"[dim]Installed plugins: {', '.join(tool_ids) or 'none'}[/dim]")
        raise SystemExit(1)

    if not yes:
        click.confirm(f"Remove tool '{tool_id}'?", abort=True)

    success, message = uninstall_tool(tool_id)

    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]✗[/red] {message}")
        raise SystemExit(1)


@tools.command("plugins")
def tools_plugins() -> None:
    """List installed custom tool plugins.

    Shows all custom tools installed in ~/.redclaw/plugins/
    """
    from redclaw.tools.loader import list_installed_tools, get_plugin_directory

    console = Console()
    plugins_dir = get_plugin_directory()
    installed = list_installed_tools()

    console.print(Panel(
        f"[bold]Plugin directory:[/bold] {plugins_dir}\n"
        f"[bold]Installed plugins:[/bold] {len(installed)}",
        title="[bold cyan]Custom Plugins[/bold cyan]",
        border_style="cyan",
    ))

    if not installed:
        console.print("\n[dim]No custom plugins installed.[/dim]")
        console.print("[dim]Use 'claw tools add <yaml_file>' to install a plugin.[/dim]")
        return

    table = Table()
    table.add_column("ID", style="cyan")
    table.add_column("File")

    for tool_id, path in installed:
        table.add_row(tool_id, path.name)

    console.print()
    console.print(table)


@tools.command("template")
@click.argument("output_file", type=click.Path(path_type=Path), default="custom_tool.yaml")
def tools_template(output_file: Path) -> None:
    """Generate a template YAML file for creating custom tools.

    Examples:
        claw tools template
        claw tools template my_tool.yaml
    """
    console = Console()

    template = '''# Custom Tool Definition for RedClaw
# See https://github.com/0xdefence/redclaw for documentation

# Required: unique identifier for the tool
id: my_custom_tool

# Required: the binary to execute
binary: mytool

# Tool metadata
name: My Custom Tool
description: A custom security scanning tool
category: scanning  # scanning, enumeration, recon, exploitation, reporting
risk_level: active  # passive, active, intrusive
default_timeout: 120

# Command line arguments (use {{target}} and {{kwarg_name}} for substitution)
args:
  - "-t"
  - "{{target}}"
  - "--output"
  - "json"

# Output parsing configuration
output_format: json  # json, jsonl, xml, text

# For text output, define regex patterns
parser:
  patterns:
    ips: "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}"
    ports: "\\d+/tcp|\\d+/udp"
  key_value: false

# Finding extraction rules
findings:
  # Iterate over a JSON array
  - type: iterate
    field: results
    mappings:
      title: name
      severity: risk_level
      description: details
    remediation: "Review and fix the identified issue"

  # Match a regex pattern
  - type: regex
    field: raw
    pattern: "CRITICAL: (.+)"
    title: Critical Finding
    severity: critical
    description: "A critical issue was detected"
'''

    if output_file.exists():
        if not click.confirm(f"File '{output_file}' exists. Overwrite?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

    output_file.write_text(template)
    console.print(f"[green]✓[/green] Created template: {output_file}")
    console.print(f"[dim]Edit the file, then run: claw tools add {output_file}[/dim]")
