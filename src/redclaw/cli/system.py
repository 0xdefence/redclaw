"""System commands — init, status, config."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from redclaw.cli.main import pass_context, ClawContext

console = Console()


@click.command()
@click.option("--check", is_flag=True, help="Check only — don't build image")
def init(check: bool) -> None:
    """Initialize RedClaw — build Docker image, create database."""
    from redclaw.core import DockerExecutor
    from redclaw.storage import Database
    from redclaw.models import get_config

    config = get_config()
    executor = DockerExecutor(config)

    console.print("[bold]Initializing RedClaw...[/bold]\n")

    # Check Docker
    try:
        executor.client.ping()
        console.print("  [green]✓[/green] Docker is running")
    except RuntimeError as exc:
        console.print(f"  [red]✗[/red] Docker: {exc}")
        raise SystemExit(1)

    # Check/build image
    if executor.image_exists():
        console.print(f"  [green]✓[/green] Image '{config.docker_image}' exists")
    elif check:
        console.print(f"  [yellow]![/yellow] Image '{config.docker_image}' not found (check-only mode)")
    else:
        console.print(f"  [yellow]…[/yellow] Building image '{config.docker_image}'...")
        try:
            executor.build_image()
            console.print(f"  [green]✓[/green] Image built")
        except FileNotFoundError as exc:
            console.print(f"  [red]✗[/red] {exc}")
            raise SystemExit(1)

    # Check/start container
    if executor.container_running():
        console.print(f"  [green]✓[/green] Container '{config.container_name}' running")
    elif check:
        console.print(f"  [yellow]![/yellow] Container not running (check-only mode)")
    else:
        try:
            executor.ensure_container()
            console.print(f"  [green]✓[/green] Container started")
        except RuntimeError as exc:
            console.print(f"  [red]✗[/red] Container: {exc}")

    # Check database
    try:
        db = Database()
        _ = db.db  # Triggers schema creation
        console.print(f"  [green]✓[/green] Database at {config.db_path}")
    except Exception as exc:
        console.print(f"  [red]✗[/red] Database: {exc}")

    # Check tools in container
    if executor.container_running():
        tool_checks = executor.list_available_tools(["nmap", "nikto", "dig", "whois"])
        for name, (avail, version) in tool_checks.items():
            if avail:
                console.print(f"  [green]✓[/green] {name}: {version}")
            else:
                console.print(f"  [red]✗[/red] {name}: not found")

    console.print("\n[bold green]Ready.[/bold green]")


@click.command()
def status() -> None:
    """Show system health and configuration."""
    from redclaw.core import DockerExecutor
    from redclaw.models import get_config

    config = get_config()
    executor = DockerExecutor(config)
    health = executor.health_check()

    table = Table(title="RedClaw Status")
    table.add_column("Component")
    table.add_column("Status")

    for key, val in health.items():
        icon = "[green]✓[/green]" if val else "[red]✗[/red]"
        table.add_row(key.replace("_", " ").title(), f"{icon} {val}")

    table.add_row("Data Directory", str(config.data_dir))
    table.add_row("Database", str(config.db_path))
    table.add_row("Docker Image", config.docker_image)
    table.add_row("Container", config.container_name)

    console.print(table)


@click.group(invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """View or update configuration."""
    if ctx.invoked_subcommand is None:
        _show_config()


@config.command("show")
def config_show() -> None:
    """Show current configuration."""
    _show_config()


def _show_config() -> None:
    from redclaw.models import get_config
    cfg = get_config()

    table = Table(title="Configuration")
    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Data Directory", str(cfg.data_dir))
    table.add_row("Database", str(cfg.db_path))
    table.add_row("Docker Image", cfg.docker_image)
    table.add_row("Container Name", cfg.container_name)
    table.add_row("Container Timeout", f"{cfg.container_timeout}s")
    table.add_row("Allow Private Networks", str(cfg.allow_private_networks))
    table.add_row("Max Concurrent Scans", str(cfg.max_concurrent_scans))
    table.add_row("OpenRouter API Key", "***set***" if cfg.openrouter_api_key else "[dim]not set[/dim]")
    table.add_row("Verbose", str(cfg.verbose))

    console.print(table)
