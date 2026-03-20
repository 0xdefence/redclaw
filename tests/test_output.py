"""Tests for RedClaw output modules."""
from __future__ import annotations

import json
import os
from io import StringIO
from datetime import datetime, timezone

import pytest
from rich.console import Console

from redclaw.models import Scan, Finding, ScanStatus, Severity
from redclaw.output.banner import print_banner, _strip_ansi
from redclaw.output.display import DisplayComponents
from redclaw.output.stealth import StealthOutput, format_scan_stealth
from redclaw.output.json_output import JSONOutput, format_scan_json
from redclaw.output.errors import ErrorDisplay


@pytest.fixture
def sample_scan() -> Scan:
    """Create a sample scan with findings for testing."""
    scan = Scan(
        id="abc123",
        target="example.com",
        profile="full",
        status=ScanStatus.COMPLETED,
        tools_used=["nmap", "nuclei", "ffuf"],
        duration_ms=45230,
        started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2024, 1, 1, 12, 0, 45, tzinfo=timezone.utc),
    )

    # Add findings
    scan.findings = [
        Finding(
            title="SQL Injection in login form",
            severity=Severity.HIGH,
            description="SQL injection vulnerability found",
            tool_id="nuclei",
            target="example.com",
            evidence="/login.php?id=1",
        ),
        Finding(
            title="Backup file found",
            severity=Severity.MEDIUM,
            description="Sensitive backup file exposed",
            tool_id="ffuf",
            target="example.com",
            evidence="/backup.sql.bak",
        ),
        Finding(
            title="Admin panel exposed",
            severity=Severity.LOW,
            description="Admin login page publicly accessible",
            tool_id="ffuf",
            target="example.com",
            evidence="/admin/login",
        ),
    ]

    for _ in range(12):
        scan.findings.append(
            Finding(
                title="Informational finding",
                severity=Severity.INFO,
                description="Some info",
                tool_id="nmap",
                target="example.com",
                evidence="port 80",
            )
        )

    return scan


class TestBanner:
    """Tests for banner module."""

    def test_print_banner_normal(self, capsys):
        """Test normal banner output."""
        print_banner("0.1.0", stealth=False)
        captured = capsys.readouterr()

        assert "REDCLAW" in captured.out or "██" in captured.out
        assert "0.1.0" in captured.out
        assert "offensive security engine" in captured.out

    def test_print_banner_stealth(self, capsys):
        """Test stealth banner output."""
        print_banner("0.1.0", stealth=True)
        captured = capsys.readouterr()

        assert "redclaw v0.1.0" in captured.out
        # Should be single line
        assert captured.out.count("\n") == 1

    def test_print_banner_no_color(self, capsys, monkeypatch):
        """Test banner with NO_COLOR environment variable."""
        monkeypatch.setenv("NO_COLOR", "1")
        print_banner("0.1.0", stealth=False)
        captured = capsys.readouterr()

        # Should have no ANSI codes
        assert "\033[" not in captured.out

    def test_strip_ansi(self):
        """Test ANSI code stripping."""
        text = "\033[91mRed\033[0m text"
        assert _strip_ansi(text) == "Red text"

        text_no_ansi = "Plain text"
        assert _strip_ansi(text_no_ansi) == "Plain text"


class TestDisplayComponents:
    """Tests for display components."""

    @pytest.fixture
    def display(self) -> DisplayComponents:
        """Create display components with string buffer."""
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        return DisplayComponents(console)

    def test_scan_header(self, display):
        """Test scan header rendering."""
        display.scan_header("example.com", "full", ["nmap", "nuclei"], "abc123")

        output = display.console.file.getvalue()
        assert "example.com" in output
        assert "full" in output
        assert "nmap" in output
        assert "abc123" in output

    def test_tool_progress_start(self, display):
        """Test tool progress start line."""
        display.tool_progress_start("nmap", "scanning 1000 ports...")

        output = display.console.file.getvalue()
        assert "nmap" in output
        assert "scanning" in output
        assert "ports" in output
        assert "⚡" in output

    def test_tool_progress_done_success(self, display):
        """Test tool progress completion (success)."""
        display.tool_progress_done(
            "nmap", "success", count=3, duration_ms=1230, has_findings=False
        )

        output = display.console.file.getvalue()
        assert "nmap" in output
        assert "3" in output
        # Duration should be present (Rich adds styling so check for parts)
        assert "2s" in output  # The seconds part
        assert "✓" in output

    def test_tool_progress_done_with_findings(self, display):
        """Test tool progress completion (with findings)."""
        display.tool_progress_done(
            "nuclei", "success", count=2, duration_ms=5000, has_findings=True
        )

        output = display.console.file.getvalue()
        assert "nuclei" in output
        assert "2" in output

    def test_scan_summary(self, display, sample_scan):
        """Test scan summary rendering."""
        display.scan_summary(sample_scan)

        output = display.console.file.getvalue()
        assert "Scan complete" in output
        assert sample_scan.id in output
        assert "HIGH" in output
        assert "MEDIUM" in output

    def test_findings_list(self, display, sample_scan):
        """Test findings list rendering."""
        display.findings_list(sample_scan.findings, verbose=False)

        output = display.console.file.getvalue()
        assert "SQL Injection" in output
        assert "Backup file" in output
        assert "Admin panel" in output
        # INFO findings should be collapsed
        assert "informational findings" in output
        assert "12" in output  # Count shown
        assert "use -v to show" in output

    def test_findings_list_verbose(self, display, sample_scan):
        """Test findings list with verbose mode."""
        display.findings_list(sample_scan.findings, verbose=True)

        output = display.console.file.getvalue()
        # All findings should be shown
        assert output.count("Informational finding") == 12

    def test_format_duration(self):
        """Test duration formatting."""
        display = DisplayComponents()

        assert display._format_duration(500) == "500ms"
        assert display._format_duration(1234) == "1.2s"
        assert display._format_duration(65000) == "1m 5s"
        assert display._format_duration(120000) == "2m"

    def test_error_display(self, display):
        """Test error display."""
        display.error_display(
            "Test Error",
            "This is a test error message",
            ["Suggestion 1", "Suggestion 2"],
        )

        output = display.console.file.getvalue()
        assert "Test Error" in output
        assert "This is a test error message" in output
        assert "Suggestion 1" in output


class TestStealthOutput:
    """Tests for stealth mode output."""

    def test_banner(self, capsys):
        """Test stealth banner."""
        stealth = StealthOutput("0.1.0")
        stealth.banner()

        captured = capsys.readouterr()
        assert "redclaw v0.1.0" in captured.out

    def test_tool_result_accumulation(self, capsys):
        """Test tool results are accumulated by stage."""
        stealth = StealthOutput("0.1.0")
        stealth.tool_result("dig", 5, None)
        stealth.tool_result("whois", 1, None)
        stealth.flush_stage("RECON")

        captured = capsys.readouterr()
        assert "[RECON]" in captured.out
        assert "5 dns records" in captured.out
        assert "whois result" in captured.out

    def test_scan_complete(self, capsys):
        """Test scan completion output."""
        stealth = StealthOutput("0.1.0")
        stealth.scan_complete(5, {"high": 1, "medium": 2, "low": 2})

        captured = capsys.readouterr()
        assert "[DONE]" in captured.out
        assert "5 findings total" in captured.out
        assert "1 high" in captured.out
        assert "2 medium" in captured.out

    def test_format_scan_stealth(self, sample_scan, capsys):
        """Test formatting complete scan in stealth mode."""
        format_scan_stealth(sample_scan, "0.1.0")

        captured = capsys.readouterr()
        assert "redclaw v0.1.0" in captured.out
        assert "[DONE]" in captured.out


class TestJSONOutput:
    """Tests for JSON output mode."""

    def test_output_scan(self, sample_scan, capsys):
        """Test JSON scan output."""
        json_out = JSONOutput(compact=False)
        json_out.output_scan(sample_scan)

        captured = capsys.readouterr()

        # Parse JSON
        data = json.loads(captured.out)

        assert data["scan_id"] == "abc123"
        assert data["target"] == "example.com"
        assert data["profile"] == "full"
        assert data["status"] == "completed"
        assert data["duration_ms"] == 45230
        assert len(data["findings"]) == 15

    def test_output_scan_compact(self, sample_scan, capsys):
        """Test compact JSON output."""
        json_out = JSONOutput(compact=True)
        json_out.output_scan(sample_scan)

        captured = capsys.readouterr()

        # Should be single line (plus newline)
        assert captured.out.count("\n") == 1

        # Should be valid JSON
        data = json.loads(captured.out)
        assert data["scan_id"] == "abc123"

    def test_format_scan_json(self, sample_scan):
        """Test format_scan_json utility."""
        json_str = format_scan_json(sample_scan, compact=False)

        data = json.loads(json_str)
        assert data["scan_id"] == "abc123"
        assert data["target"] == "example.com"

    def test_finding_serialization(self, sample_scan):
        """Test finding serialization includes all fields."""
        json_str = format_scan_json(sample_scan)
        data = json.loads(json_str)

        finding = data["findings"][0]
        assert "severity" in finding
        assert "title" in finding
        assert "description" in finding
        assert "tool_id" in finding
        assert "target" in finding
        assert "evidence" in finding
        assert "remediation" in finding
        assert "references" in finding
        assert "metadata" in finding


class TestErrorDisplay:
    """Tests for error display module."""

    @pytest.fixture
    def error_display(self) -> ErrorDisplay:
        """Create error display with string buffer."""
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100, stderr=False)
        return ErrorDisplay(console)

    def test_docker_not_running(self, error_display):
        """Test Docker not running error."""
        error_display.docker_not_running()

        output = error_display.console.file.getvalue()
        assert "Docker is not running" in output
        assert "--local" in output

    def test_tool_not_found(self, error_display):
        """Test tool not found error."""
        error_display.tool_not_found("nmap")

        output = error_display.console.file.getvalue()
        assert "nmap not found" in output
        assert "brew install nmap" in output or "apt install nmap" in output

    def test_target_blocked(self, error_display):
        """Test target blocked error."""
        error_display.target_blocked(
            "192.168.1.1",
            "is in private range 192.168.0.0/16",
            "REDCLAW_ALLOW_PRIVATE_NETWORKS",
        )

        output = error_display.console.file.getvalue()
        assert "192.168.1.1" in output
        assert "private range" in output
        assert "REDCLAW_ALLOW_PRIVATE_NETWORKS" in output

    def test_api_key_missing(self, error_display):
        """Test API key missing error."""
        error_display.api_key_missing()

        output = error_display.console.file.getvalue()
        assert "API key" in output
        assert "OPENROUTER_API_KEY" in output
        assert "openrouter.ai" in output

    def test_generic_error(self, error_display):
        """Test generic error display."""
        error_display.generic_error(
            "Test Error",
            "Something went wrong",
            ["Try this", "Or try that"],
        )

        output = error_display.console.file.getvalue()
        assert "Test Error" in output
        assert "Something went wrong" in output
        assert "Try this" in output
        assert "Or try that" in output


class TestIntegration:
    """Integration tests for complete output flows."""

    def test_complete_scan_lifecycle_normal(self, sample_scan):
        """Test complete scan output in normal mode."""
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        # Header
        display.scan_header("example.com", "full", ["nmap", "nuclei"], "abc123")

        # Tool progress
        display.tool_progress_start("nmap", "scanning ports...")
        display.tool_progress_done("nmap", "success", 3, 1200, False)

        # Summary and findings
        display.scan_summary(sample_scan)
        display.findings_list(sample_scan.findings, verbose=False)

        output = buffer.getvalue()

        # Verify all components present
        assert "example.com" in output
        assert "nmap" in output
        assert "Scan complete" in output
        assert "SQL Injection" in output

    def test_no_findings_scan(self):
        """Test scan output with no findings."""
        scan = Scan(
            id="xyz789",
            target="safe.com",
            profile="quick",
            status=ScanStatus.COMPLETED,
            tools_used=["nmap"],
            duration_ms=1000,
            findings=[],
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        display.scan_summary(scan)
        output = buffer.getvalue()

        assert "Scan complete" in output
        assert "No findings" in output

    def test_failed_scan(self):
        """Test failed scan output."""
        scan = Scan(
            id="fail123",
            target="error.com",
            profile="full",
            status=ScanStatus.FAILED,
            tools_used=[],
            duration_ms=0,
            error="Connection refused",
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        display.scan_summary(scan)
        output = buffer.getvalue()

        assert "Scan failed" in output or "failed" in output
        assert "Connection refused" in output
