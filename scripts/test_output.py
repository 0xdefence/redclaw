#!/usr/bin/env python3
"""Visual testing script for RedClaw CLI output.

Run this script to see all output modes and components rendered in your terminal.
This helps verify that colors, formatting, and layouts match the spec.

Usage:
    python scripts/test_output.py              # Show all demos
    python scripts/test_output.py banner       # Just banner
    python scripts/test_output.py scan         # Just scan output
    python scripts/test_output.py stealth      # Just stealth mode
    python scripts/test_output.py json         # Just JSON mode
    python scripts/test_output.py errors       # Just error displays
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path so we can import redclaw modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from redclaw.models import Scan, Finding, ScanStatus, Severity
from redclaw.output.banner import print_banner
from redclaw.output.display import DisplayComponents
from redclaw.output.stealth import format_scan_stealth
from redclaw.output.json_output import JSONOutput
from redclaw.output.errors import ErrorDisplay


def create_sample_scan() -> Scan:
    """Create a sample scan with findings for demo."""
    scan = Scan(
        id="a8f2c1",
        target="example.com",
        profile="full",
        status=ScanStatus.COMPLETED,
        tools_used=["dig", "whois", "nmap", "nuclei", "ffuf"],
        duration_ms=77700,
        started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2024, 1, 1, 12, 1, 17, tzinfo=timezone.utc),
    )

    # Add sample findings
    scan.findings = [
        Finding(
            title="RCE via path traversal (CVE-2024-1234)",
            severity=Severity.HIGH,
            description="Remote code execution vulnerability via path traversal",
            tool_id="nuclei",
            target="example.com",
            evidence="/api/v1/upload",
        ),
        Finding(
            title="Backup file found: /backup.sql.bak",
            severity=Severity.MEDIUM,
            description="Sensitive backup file exposed",
            tool_id="ffuf",
            target="example.com",
            evidence="Status 200, 12KB",
        ),
        Finding(
            title="Admin panel exposed: /admin/login",
            severity=Severity.LOW,
            description="Admin login page publicly accessible",
            tool_id="ffuf",
            target="example.com",
            evidence="Status 200, 3.1KB",
        ),
        Finding(
            title="Unencrypted HTTP endpoint",
            severity=Severity.LOW,
            description="HTTP endpoint found without HTTPS redirect",
            tool_id="nmap",
            target="example.com",
            evidence="Port 80 open",
        ),
        Finding(
            title="Old TLS version detected",
            severity=Severity.LOW,
            description="TLS 1.1 is deprecated",
            tool_id="nmap",
            target="example.com",
            evidence="Port 443",
        ),
    ]

    # Add INFO findings
    for i in range(12):
        scan.findings.append(
            Finding(
                title=f"DNS record {i+1}",
                severity=Severity.INFO,
                description="DNS A record found",
                tool_id="dig",
                target="example.com",
                evidence=f"93.184.216.{34+i}",
            )
        )

    return scan


def demo_banner():
    """Demo: Banner rendering."""
    console = Console()

    console.print("\n[bold cyan]═══ Banner Demo ═══[/bold cyan]\n")

    console.print("[yellow]Normal mode:[/yellow]")
    print_banner("0.1.0", stealth=False)

    console.print("\n[yellow]Stealth mode:[/yellow]")
    print_banner("0.1.0", stealth=True)

    console.print()


def demo_scan_lifecycle():
    """Demo: Complete scan lifecycle output."""
    console = Console()
    display = DisplayComponents(console)

    console.print("\n[bold cyan]═══ Scan Lifecycle Demo ═══[/bold cyan]\n")

    # 1. Banner
    print_banner("0.1.0")

    # 2. Scan header
    display.scan_header("example.com", "full", ["dig", "whois", "nmap", "nuclei", "ffuf"], "a8f2c1")

    # 3. Tool progress
    tools = [
        ("dig", "running DNS lookup...", 5, 230, False),
        ("whois", "querying registrar...", 1, 1200, False),
        ("nmap", "scanning 1000 ports...", 3, 12400, False),
        ("nuclei", "running 4,218 templates...", 2, 45200, True),
        ("ffuf", "fuzzing directories...", 8, 18700, False),
    ]

    for tool_id, description, count, duration, has_findings in tools:
        display.tool_progress_start(tool_id, description)
        time.sleep(0.3)  # Simulate work
        display.tool_progress_done(tool_id, "success", count, duration, has_findings)

    # 4. Summary and findings
    scan = create_sample_scan()
    display.scan_summary(scan)
    display.findings_list(scan.findings, verbose=False)


def demo_stealth_mode():
    """Demo: Stealth mode output."""
    console = Console()

    console.print("\n[bold cyan]═══ Stealth Mode Demo ═══[/bold cyan]\n")

    scan = create_sample_scan()
    format_scan_stealth(scan, "0.1.0")


def demo_json_mode():
    """Demo: JSON mode output."""
    console = Console()

    console.print("\n[bold cyan]═══ JSON Mode Demo ═══[/bold cyan]\n")
    console.print("[yellow]Pretty-printed:[/yellow]\n")

    scan = create_sample_scan()
    json_out = JSONOutput(compact=False)
    json_out.output_scan(scan)

    console.print("\n[yellow]Compact:[/yellow]\n")
    json_out_compact = JSONOutput(compact=True)
    json_out_compact.output_scan(scan)


def demo_error_displays():
    """Demo: Error display formats."""
    console = Console()
    errors = ErrorDisplay(console)

    console.print("\n[bold cyan]═══ Error Displays Demo ═══[/bold cyan]\n")

    console.print("[yellow]1. Docker not running:[/yellow]")
    errors.docker_not_running()

    console.print("\n[yellow]2. Tool not found:[/yellow]")
    errors.tool_not_found("nmap")

    console.print("\n[yellow]3. Target blocked:[/yellow]")
    errors.target_blocked(
        "192.168.1.1",
        "is in private range 192.168.0.0/16",
        "REDCLAW_ALLOW_PRIVATE_NETWORKS",
    )

    console.print("\n[yellow]4. API key missing:[/yellow]")
    errors.api_key_missing()

    console.print("\n[yellow]5. Generic error:[/yellow]")
    errors.generic_error(
        "Scan failed",
        "Unable to connect to target",
        ["Check network connection", "Verify target is reachable", "Try again with --verbose"],
    )


def demo_edge_cases():
    """Demo: Edge cases and special scenarios."""
    console = Console()
    display = DisplayComponents(console)

    console.print("\n[bold cyan]═══ Edge Cases Demo ═══[/bold cyan]\n")

    # Empty scan
    console.print("[yellow]1. Scan with no findings:[/yellow]\n")
    empty_scan = Scan(
        id="empty1",
        target="safe.com",
        profile="quick",
        status=ScanStatus.COMPLETED,
        tools_used=["nmap"],
        duration_ms=1234,
        findings=[],
    )
    display.scan_summary(empty_scan)

    # Failed scan
    console.print("\n[yellow]2. Failed scan:[/yellow]\n")
    failed_scan = Scan(
        id="fail1",
        target="error.com",
        profile="full",
        status=ScanStatus.FAILED,
        tools_used=["nmap"],
        duration_ms=500,
        error="Connection refused",
    )
    display.scan_summary(failed_scan)

    # All severity levels
    console.print("\n[yellow]3. All severity levels:[/yellow]\n")
    all_sev_scan = create_sample_scan()
    # Add CRITICAL finding
    all_sev_scan.findings.insert(
        0,
        Finding(
            title="Unauthenticated RCE",
            severity=Severity.CRITICAL,
            description="Critical vulnerability",
            tool_id="nuclei",
            target="example.com",
            evidence="CVE-2024-9999",
        ),
    )
    display.findings_list(all_sev_scan.findings, verbose=False)


def demo_tool_failures():
    """Demo: Tool failure states."""
    console = Console()
    display = DisplayComponents(console)

    console.print("\n[bold cyan]═══ Tool Failures Demo ═══[/bold cyan]\n")

    display.scan_header("example.com", "full", None, "fail123")

    # Various failure modes
    display.tool_progress_start("nmap", "scanning ports...")
    time.sleep(0.2)
    display.tool_progress_done("nmap", "failed", None, 2100, False)

    display.tool_progress_start("nuclei", "running templates...")
    time.sleep(0.2)
    display.tool_progress_done("nuclei", "timeout", None, 300000, False)

    display.tool_progress_start("ffuf", "fuzzing directories...")
    time.sleep(0.2)
    display.tool_progress_done("ffuf", "blocked", None, 100, False)


def main():
    """Run all demos or specific demo based on argument."""
    if len(sys.argv) > 1:
        demo_name = sys.argv[1].lower()

        demos = {
            "banner": demo_banner,
            "scan": demo_scan_lifecycle,
            "stealth": demo_stealth_mode,
            "json": demo_json_mode,
            "errors": demo_error_displays,
            "edge": demo_edge_cases,
            "failures": demo_tool_failures,
        }

        if demo_name in demos:
            demos[demo_name]()
        else:
            print(f"Unknown demo: {demo_name}")
            print(f"Available demos: {', '.join(demos.keys())}")
            sys.exit(1)
    else:
        # Run all demos
        demo_banner()
        demo_scan_lifecycle()
        demo_stealth_mode()
        demo_json_mode()
        demo_error_displays()
        demo_edge_cases()
        demo_tool_failures()

        console = Console()
        console.print("\n[bold green]✓ All demos complete![/bold green]\n")


if __name__ == "__main__":
    main()
