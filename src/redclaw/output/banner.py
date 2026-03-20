"""RedClaw banner and branding."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

# Red ANSI colours
RED = "\033[91m"
DIM_RED = "\033[2;31m"
RESET = "\033[0m"

BANNER = f"""{RED}
    ██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗
    ██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║
    ██████╔╝█████╗  ██║  ██║██║     ██║     ███████║██║ █╗ ██║
    ██╔══██╗██╔══╝  ██║  ██║██║     ██║     ██╔══██║██║███╗██║
    ██║  ██║███████╗██████╔╝╚██████╗███████╗██╔══██║╚███╔███╔╝
    ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
{RESET}"""

STEALTH_BANNER = f"{DIM_RED}RedClaw v{{version}}{RESET}"


def print_banner(version: str, stealth: bool = False) -> None:
    """Print the RedClaw banner.

    Args:
        version: Current version string
        stealth: If True, use minimal stealth banner
    """
    if stealth:
        print(STEALTH_BANNER.format(version=version))
    else:
        print(BANNER)
        print(f"  {DIM_RED}v{version} — CLI offensive security engine{RESET}")
        print()


def print_banner_rich(version: str, stealth: bool = False, console: Console | None = None) -> None:
    """Print the RedClaw banner using Rich formatting.

    Args:
        version: Current version string
        stealth: If True, use minimal stealth banner
        console: Rich console (creates one if not provided)
    """
    console = console or Console()

    if stealth:
        console.print(f"[dim red]RedClaw v{version}[/dim red]")
    else:
        console.print(Panel.fit(
            "[bold red]"
            "██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗\n"
            "██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║\n"
            "██████╔╝█████╗  ██║  ██║██║     ██║     ███████║██║ █╗ ██║\n"
            "██╔══██╗██╔══╝  ██║  ██║██║     ██║     ██╔══██║██║███╗██║\n"
            "██║  ██║███████╗██████╔╝╚██████╗███████╗██╔══██║╚███╔███╔╝\n"
            "╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝\n"
            "[/bold red]"
            f"\n[dim]v{version} — CLI offensive security engine[/dim]",
            border_style="red",
            padding=(0, 2),
        ))
        console.print()


# ASCII crab for fun (optional small variant)
CRAB_SMALL = r"""
    /\___/\
   (  o o  )
   (  =^=  )
    )------(
   (  claw  )
"""

CRAB_MEDIUM = r"""
      /)  /)
    /' `--' `\
   (  (  O O  )
    \  \__o__/
     `.    /
       `--'
"""


def get_crab_art(size: str = "small") -> str:
    """Get ASCII crab art.

    Args:
        size: "small" or "medium"

    Returns:
        ASCII art string
    """
    if size == "medium":
        return CRAB_MEDIUM
    return CRAB_SMALL
