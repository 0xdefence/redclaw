"""RedClaw banner and branding."""
from __future__ import annotations

import os
import shutil

# ANSI color codes (used for banner to avoid Rich markup issues with block chars)
BRIGHT_RED = "\033[91m"
MID_RED = "\033[31m"
DIM_RED = "\033[2;31m"
DIM_GREY = "\033[2m"
RESET = "\033[0m"

# Full banner with claw marks
BANNER_FULL = f"""{BRIGHT_RED}     ╱╲    ╱╲    ╱╲
    ╱  ╲  ╱  ╲  ╱  ╲
   ╱    ╲╱    ╲╱    ╲
  ╱                   ╲
 ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲{RESET}
{BRIGHT_RED}  ██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗{RESET}
{BRIGHT_RED}  ██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║{RESET}
{MID_RED}  ██████╔╝█████╗  ██║  ██║██║     ██║     ███████║██║ █╗ ██║{RESET}
{MID_RED}  ██╔══██╗██╔══╝  ██║  ██║██║     ██║     ██╔══██║██║███╗██║{RESET}
{DIM_RED}  ██║  ██║███████╗██████╔╝╚██████╗███████╗██╔══██║╚███╔███╔╝{RESET}
{DIM_RED}  ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝{RESET}"""

# Compact banner (no claw marks) for narrow terminals
BANNER_COMPACT = f"""{BRIGHT_RED}  ██████╗ ███████╗██████╗  ██████╗██╗      █████╗ ██╗    ██╗{RESET}
{BRIGHT_RED}  ██╔══██╗██╔════╝██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║{RESET}
{MID_RED}  ██████╔╝█████╗  ██║  ██║██║     ██║     ███████║██║ █╗ ██║{RESET}
{MID_RED}  ██╔══██╗██╔══╝  ██║  ██║██║     ██║     ██╔══██║██║███╗██║{RESET}
{DIM_RED}  ██║  ██║███████╗██████╔╝╚██████╗███████╗██╔══██║╚███╔███╔╝{RESET}
{DIM_RED}  ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝{RESET}"""

# Stealth banner (minimal, single line)
STEALTH_BANNER = f"{DIM_RED}redclaw v{{version}}{RESET}"


def print_banner(version: str, stealth: bool = False) -> None:
    """Print the RedClaw banner with ANSI colors.

    Args:
        version: Current version string
        stealth: If True, use minimal stealth banner

    Notes:
        - Uses raw ANSI codes (not Rich) to avoid markup conflicts with block chars
        - Respects NO_COLOR environment variable
        - Auto-switches to compact banner for narrow terminals (< 70 cols)
    """
    # Check for NO_COLOR environment variable
    no_color = os.environ.get("NO_COLOR", "").lower() in ("1", "true", "yes")

    if stealth:
        # Stealth mode: single line, minimal
        banner = STEALTH_BANNER.format(version=version)
        if no_color:
            banner = _strip_ansi(banner)
        print(banner)
    else:
        # Normal mode: full banner with optional claw marks
        terminal_width = shutil.get_terminal_size((80, 24)).columns

        # Use compact banner if terminal is narrow
        if terminal_width < 70:
            banner = BANNER_COMPACT
        else:
            banner = BANNER_FULL

        # Strip colors if NO_COLOR is set
        if no_color:
            banner = _strip_ansi(banner)

        print(banner)

        # Version and tagline
        tagline = f"  v{version} — offensive security engine"
        if no_color:
            print(tagline)
        else:
            print(f"  {DIM_GREY}{tagline}{RESET}")
        print()


def print_banner_rich(version: str, stealth: bool = False) -> None:
    """Print the RedClaw banner using Rich (not recommended - use print_banner instead).

    DEPRECATED: Use print_banner() instead. Rich markup conflicts with block
    characters, so we use raw ANSI codes for the banner.

    Args:
        version: Current version string
        stealth: If True, use minimal stealth banner
    """
    # Fall back to ANSI banner for better rendering
    print_banner(version, stealth)


def _strip_ansi(text: str) -> str:
    """Strip ANSI color codes from text.

    Args:
        text: Text with ANSI codes

    Returns:
        Plain text without ANSI codes
    """
    import re
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r"\033\[[0-9;]*m")
    return ansi_escape.sub("", text)


