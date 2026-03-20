"""RedClaw CLI entry point."""
from __future__ import annotations

import click

from redclaw import __version__


class ClawContext:
    """Shared context for all CLI commands."""
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose


pass_context = click.make_pass_decorator(ClawContext, ensure=True)


@click.group()
@click.version_option(version=__version__, prog_name="RedClaw")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """RedClaw — CLI security scanner."""
    ctx.ensure_object(ClawContext)
    ctx.obj.verbose = verbose


# Register command groups
from redclaw.cli.scan import scan, recon, portscan, webscan  # noqa: E402
from redclaw.cli.tools import tools  # noqa: E402
from redclaw.cli.results import results, report  # noqa: E402
from redclaw.cli.system import init, status, config  # noqa: E402

cli.add_command(scan)
cli.add_command(recon)
cli.add_command(portscan)
cli.add_command(webscan)
cli.add_command(tools)
cli.add_command(results)
cli.add_command(report)
cli.add_command(init)
cli.add_command(status)
cli.add_command(config)


if __name__ == "__main__":
    cli()
