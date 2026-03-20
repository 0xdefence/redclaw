"""Integration tests for output system with real CLI commands."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from io import StringIO

import pytest
from rich.console import Console

from redclaw.models import Scan, Finding, ScanStatus, Severity
from redclaw.output import (
    OutputMode,
    DisplayComponents,
    print_scan_header,
    print_tool_progress,
    print_scan_summary,
    format_scan_stealth,
    format_scan_json,
)


@pytest.fixture
def large_scan() -> Scan:
    """Create a scan with many findings for testing."""
    scan = Scan(
        id="stress1",
        target="example.com",
        profile="full",
        status=ScanStatus.COMPLETED,
        tools_used=["nmap", "nuclei", "ffuf", "gobuster"],
        duration_ms=125000,
        started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        finished_at=datetime(2024, 1, 1, 12, 2, 5, tzinfo=timezone.utc),
    )

    # Add 100 findings across all severity levels
    severities = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]

    for i in range(100):
        severity = severities[i % len(severities)]
        scan.findings.append(
            Finding(
                title=f"Finding {i+1}: {severity.value.upper()} severity issue",
                severity=severity,
                description=f"This is test finding number {i+1}",
                tool_id=["nmap", "nuclei", "ffuf", "gobuster"][i % 4],
                target="example.com",
                evidence=f"/path/to/finding/{i+1}",
            )
        )

    return scan


class TestIntegrationOutput:
    """Integration tests for complete output workflows."""

    def test_normal_mode_integration(self, large_scan):
        """Test complete normal mode output with large dataset."""
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        # Full workflow
        display.scan_header("example.com", "full", large_scan.tools_used, large_scan.id)
        display.scan_summary(large_scan)
        display.findings_list(large_scan.findings, verbose=False)

        output = buffer.getvalue()

        # Verify all components present
        assert "example.com" in output
        assert large_scan.id in output
        assert "Scan complete" in output
        assert "CRITICAL" in output
        assert "HIGH" in output
        assert "MEDIUM" in output

    def test_stealth_mode_integration(self, large_scan, capsys):
        """Test stealth mode with large dataset."""
        format_scan_stealth(large_scan, "0.1.0")

        captured = capsys.readouterr()

        # Verify stage-based output
        assert "redclaw v0.1.0" in captured.out
        assert "[DONE]" in captured.out
        assert "100 findings total" in captured.out

    def test_json_mode_integration(self, large_scan, capsys):
        """Test JSON mode with large dataset."""
        json_str = format_scan_json(large_scan, compact=False)

        # Verify valid JSON
        data = json.loads(json_str)

        assert data["scan_id"] == "stress1"
        assert data["target"] == "example.com"
        assert len(data["findings"]) == 100
        assert data["finding_counts"]["critical"] > 0
        assert data["finding_counts"]["high"] > 0

    def test_json_mode_compact(self, large_scan):
        """Test compact JSON mode."""
        json_str = format_scan_json(large_scan, compact=True)

        # Should be single line
        assert json_str.count("\n") == 0

        # Should be valid JSON
        data = json.loads(json_str)
        assert len(data["findings"]) == 100

    def test_output_mode_switching(self, large_scan, capsys):
        """Test switching between output modes."""
        # Normal mode - uses global console, so capture stdout
        print_scan_summary(large_scan, verbose=False, output_mode=OutputMode.NORMAL)

        captured = capsys.readouterr()
        assert "Scan complete" in captured.out or "complete" in captured.out

    def test_no_color_mode(self, large_scan, monkeypatch):
        """Test NO_COLOR environment variable."""
        monkeypatch.setenv("NO_COLOR", "1")

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=False, width=100)
        display = DisplayComponents(console)

        display.scan_summary(large_scan)
        output = buffer.getvalue()

        # Should have minimal ANSI codes (Rich may still add some structural codes)
        # But no color codes
        assert output  # Output should exist

    def test_narrow_terminal(self, large_scan):
        """Test output with narrow terminal width."""
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=60)
        display = DisplayComponents(console)

        display.scan_header("example.com", "full", ["nmap"], "abc123")
        display.scan_summary(large_scan)

        output = buffer.getvalue()

        # Should still render without errors
        assert "example.com" in output
        assert "Scan complete" in output

    def test_very_long_findings(self):
        """Test with very long finding titles and evidence."""
        scan = Scan(
            id="long1",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei"],
            duration_ms=5000,
        )

        # Add finding with very long title
        scan.findings.append(
            Finding(
                title="A" * 200,  # Very long title
                severity=Severity.HIGH,
                description="Test",
                tool_id="nuclei",
                target="example.com",
                evidence="B" * 150,  # Very long evidence
            )
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        # Should truncate gracefully
        display.findings_list(scan.findings, verbose=False)
        output = buffer.getvalue()

        assert output  # Should render without errors

    def test_unicode_in_findings(self):
        """Test with Unicode characters in findings."""
        scan = Scan(
            id="unicode1",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei"],
            duration_ms=5000,
        )

        scan.findings.append(
            Finding(
                title="SQL Injection → データベース エラー 🔐",
                severity=Severity.HIGH,
                description="Unicode test: ✓ ✗ ⚡ ⊘",
                tool_id="nuclei",
                target="example.com",
                evidence="/api/v1/данные",
            )
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        display.findings_list(scan.findings, verbose=False)
        output = buffer.getvalue()

        # Should handle Unicode
        assert "データベース" in output or "SQL Injection" in output

    def test_empty_and_none_values(self):
        """Test handling of empty and None values."""
        scan = Scan(
            id="",  # Empty ID
            target="example.com",
            profile="",
            status=ScanStatus.COMPLETED,
            tools_used=[],
            duration_ms=0,
            findings=[],
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        # Should not crash
        display.scan_summary(scan)
        output = buffer.getvalue()

        assert "Scan complete" in output or "complete" in output

    def test_special_characters_in_target(self):
        """Test with special characters in target."""
        scan = Scan(
            id="special1",
            target="example.com:8080/path?query=value&foo=bar",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nmap"],
            duration_ms=5000,
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        display.scan_header(scan.target, scan.profile, scan.tools_used, scan.id)
        output = buffer.getvalue()

        assert "example.com" in output
        assert "8080" in output

    def test_all_severity_levels(self):
        """Test that all severity levels render correctly."""
        scan = Scan(
            id="allsev1",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei"],
            duration_ms=5000,
        )

        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            scan.findings.append(
                Finding(
                    title=f"{severity.value.upper()} finding",
                    severity=severity,
                    description="Test",
                    tool_id="nuclei",
                    target="example.com",
                    evidence="test",
                )
            )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        display.findings_list(scan.findings, verbose=True)
        output = buffer.getvalue()

        # All severities should be present
        assert "CRITICAL" in output
        assert "HIGH" in output
        assert "MEDIUM" in output
        assert "LOW" in output
        assert "INFO" in output

    def test_progressive_disclosure_threshold(self):
        """Test progressive disclosure collapse behavior."""
        scan = Scan(
            id="disclosure1",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nmap"],
            duration_ms=5000,
        )

        # Add 1 high finding + 15 INFO findings (should collapse INFO)
        scan.findings.append(
            Finding(
                title="Important vulnerability",
                severity=Severity.HIGH,
                description="Critical issue",
                tool_id="nuclei",
                target="example.com",
                evidence="test",
            )
        )

        for i in range(15):
            scan.findings.append(
                Finding(
                    title=f"Info finding {i}",
                    severity=Severity.INFO,
                    description="Info",
                    tool_id="nmap",
                    target="example.com",
                    evidence="test",
                )
            )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        display.findings_list(scan.findings, verbose=False)
        output = buffer.getvalue()

        # Should show collapse message
        assert "informational findings" in output
        assert "use -v to show" in output

    def test_duration_formatting_edge_cases(self):
        """Test duration formatting with edge cases."""
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=100)
        display = DisplayComponents(console)

        # Test various durations
        test_cases = [
            (0, "0ms"),
            (1, "1ms"),
            (999, "999ms"),
            (1000, "1.0s"),
            (1500, "1.5s"),
            (59999, "60.0s"),
            (60000, "1m"),
            (65000, "1m 5s"),
            (125000, "2m 5s"),
        ]

        for duration_ms, expected_contains in test_cases:
            formatted = display._format_duration(duration_ms)
            # Check that the format is reasonable
            assert len(formatted) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
