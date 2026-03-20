"""Error display formatting with helpful recovery suggestions."""
from __future__ import annotations

import sys
from rich.console import Console
from rich.panel import Panel


class ErrorDisplay:
    """Formatted error display following the UX specification."""

    def __init__(self, console: Console | None = None):
        """Initialize error display.

        Args:
            console: Rich console instance (creates one if not provided)
        """
        self.console = console or Console(stderr=True)

    def docker_not_running(self) -> None:
        """Display error when Docker is not running."""
        self.console.print()
        self.console.print(
            Panel(
                "[red]✗ Docker is not running[/red]\n\n"
                "RedClaw needs Docker to execute security tools.\n"
                "Start Docker Desktop or run: [cyan]systemctl start docker[/cyan]\n\n"
                "Or use [cyan]--local[/cyan] to run tools from your system PATH.",
                border_style="red",
                padding=(1, 2),
            )
        )

    def tool_not_found(self, tool_id: str, install_commands: dict[str, str] | None = None) -> None:
        """Display error when a tool is not found in local mode.

        Args:
            tool_id: Tool identifier (e.g., "nmap")
            install_commands: Optional dict of platform -> install command
        """
        content = f"[red]✗ {tool_id} not found in PATH[/red]\n\n"

        # Default install commands for common tools
        if install_commands is None:
            install_commands = self._default_install_commands(tool_id)

        if install_commands:
            content += "Install it:\n"
            for platform, cmd in install_commands.items():
                content += f"  [cyan]{cmd}[/cyan]  ({platform})\n"
            content += "\n"

        content += "Or use [cyan]--docker[/cyan] to run tools in a container."

        self.console.print()
        self.console.print(
            Panel(
                content,
                border_style="red",
                padding=(1, 2),
            )
        )

    def target_blocked(self, target: str, reason: str, override_hint: str | None = None) -> None:
        """Display error when target is blocked by policy.

        Args:
            target: Blocked target
            reason: Why it was blocked (e.g., "is in private range 192.168.0.0/16")
            override_hint: Optional environment variable to override
        """
        content = f"[red]⊘ Target blocked:[/red] {target} {reason}\n\n"

        if override_hint:
            content += f"Set [cyan]{override_hint}=true[/cyan] to override."
        else:
            content += "This target is blocked by RedClaw's security policy."

        self.console.print()
        self.console.print(
            Panel(
                content,
                border_style="yellow",
                padding=(1, 2),
            )
        )

    def api_key_missing(self) -> None:
        """Display error when API key is required but missing."""
        self.console.print()
        self.console.print(
            Panel(
                "[red]⊘ AI features require an API key[/red]\n\n"
                "Set one of:\n"
                "  [cyan]export OPENROUTER_API_KEY=sk-...[/cyan]\n"
                "  [cyan]export REDCLAW_OPENROUTER_API_KEY=sk-...[/cyan]\n\n"
                "Get a key: [link=https://openrouter.ai/]https://openrouter.ai/[/link]\n"
                "Or use [cyan]--no-llm[/cyan] for deterministic-only scanning.",
                border_style="red",
                padding=(1, 2),
            )
        )

    def generic_error(self, title: str, message: str, suggestions: list[str] | None = None) -> None:
        """Display a generic formatted error.

        Args:
            title: Error title
            message: Main error message
            suggestions: Optional list of recovery suggestions
        """
        content = f"[red]✗ {title}[/red]\n\n{message}"

        if suggestions:
            content += "\n\n"
            for suggestion in suggestions:
                content += f"  • {suggestion}\n"

        self.console.print()
        self.console.print(
            Panel(
                content,
                border_style="red",
                padding=(1, 2),
            )
        )

    @staticmethod
    def _default_install_commands(tool_id: str) -> dict[str, str]:
        """Get default install commands for common tools.

        Args:
            tool_id: Tool identifier

        Returns:
            Dict of platform -> install command
        """
        commands = {
            "nmap": {
                "macOS": "brew install nmap",
                "Debian/Ubuntu": "apt install nmap",
                "Arch": "pacman -S nmap",
            },
            "nikto": {
                "macOS": "brew install nikto",
                "Debian/Ubuntu": "apt install nikto",
                "Arch": "pacman -S nikto",
            },
            "dig": {
                "macOS": "brew install bind",
                "Debian/Ubuntu": "apt install dnsutils",
                "Arch": "pacman -S bind-tools",
            },
            "whois": {
                "macOS": "brew install whois",
                "Debian/Ubuntu": "apt install whois",
                "Arch": "pacman -S whois",
            },
            "nuclei": {
                "Go": "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
            },
            "ffuf": {
                "Go": "go install github.com/ffuf/ffuf/v2@latest",
            },
            "gobuster": {
                "Go": "go install github.com/OJ/gobuster/v3@latest",
            },
        }
        return commands.get(tool_id, {})


def print_error(
    title: str,
    message: str,
    suggestions: list[str] | None = None,
    use_stderr: bool = True,
) -> None:
    """Convenience function to print a formatted error.

    Args:
        title: Error title
        message: Main error message
        suggestions: Optional recovery suggestions
        use_stderr: If True, print to stderr (default)
    """
    console = Console(stderr=use_stderr)
    display = ErrorDisplay(console)
    display.generic_error(title, message, suggestions)


def exit_with_error(
    title: str,
    message: str,
    suggestions: list[str] | None = None,
    exit_code: int = 1,
) -> None:
    """Print error and exit.

    Args:
        title: Error title
        message: Main error message
        suggestions: Optional recovery suggestions
        exit_code: Exit code (default: 1)
    """
    print_error(title, message, suggestions, use_stderr=True)
    sys.exit(exit_code)
