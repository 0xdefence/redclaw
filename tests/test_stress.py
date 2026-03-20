"""Stress tests for RedClaw output system with extreme cases."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import StringIO

import pytest
from rich.console import Console

from redclaw.models import Scan, Finding, ScanStatus, Severity
from redclaw.output.display import DisplayComponents
from redclaw.output.stealth import format_scan_stealth
from redclaw.output.json_output import format_scan_json


class TestStressOutput:
    """Stress tests with extreme datasets and edge cases."""

    def test_1000_findings(self):
        """Test with 1000 findings."""
        scan = Scan(
            id="stress1",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei"],
            duration_ms=300000,
        )

        # Create 1000 findings
        for i in range(1000):
            scan.findings.append(
                Finding(
                    title=f"Finding {i+1}",
                    severity=Severity.INFO if i % 2 == 0 else Severity.LOW,
                    description=f"Description {i+1}",
                    tool_id="nuclei",
                    target="example.com",
                    evidence=f"/path/{i+1}",
                )
            )

        # Test normal mode (should use progressive disclosure)
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        display.scan_summary(scan)
        output = buffer.getvalue()

        assert "Scan complete" in output
        # Should show counts
        assert "500" in output or "1000" in output

    def test_extremely_long_strings(self):
        """Test with extremely long strings."""
        scan = Scan(
            id="longstr",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei"],
            duration_ms=5000,
        )

        # Finding with 10,000 character title
        scan.findings.append(
            Finding(
                title="A" * 10000,
                severity=Severity.HIGH,
                description="B" * 10000,
                tool_id="nuclei",
                target="example.com",
                evidence="C" * 10000,
            )
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        # Should not crash, should truncate
        display.findings_list(scan.findings, verbose=False)
        output = buffer.getvalue()

        assert output  # Should produce output
        assert len(output) < 50000  # Should truncate

    def test_all_unicode_ranges(self):
        """Test with Unicode from various ranges."""
        scan = Scan(
            id="unicode",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei"],
            duration_ms=5000,
        )

        unicode_tests = [
            "Chinese: 中文字符",
            "Japanese: 日本語の文字",
            "Korean: 한국어 문자",
            "Arabic: العربية",
            "Hebrew: עברית",
            "Russian: Русский",
            "Greek: Ελληνικά",
            "Emoji: 🔥 💻 🚀 ⚠️ ✅ ❌",
            "Math: ∑ ∫ ∂ √ π ∞",
            "Symbols: © ® ™ € £ ¥",
        ]

        for i, text in enumerate(unicode_tests):
            scan.findings.append(
                Finding(
                    title=text,
                    severity=Severity.INFO,
                    description=text,
                    tool_id="nuclei",
                    target="example.com",
                    evidence=text,
                )
            )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        # Should handle all Unicode
        display.findings_list(scan.findings, verbose=True)
        output = buffer.getvalue()

        assert output  # Should produce output

    def test_zero_width_terminal(self):
        """Test with extremely narrow terminal."""
        scan = Scan(
            id="narrow",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nmap"],
            duration_ms=5000,
        )

        scan.findings.append(
            Finding(
                title="Test finding",
                severity=Severity.HIGH,
                description="Test",
                tool_id="nmap",
                target="example.com",
                evidence="test",
            )
        )

        # Very narrow terminal
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=40)
        display = DisplayComponents(console)

        # Should not crash
        display.scan_summary(scan)
        output = buffer.getvalue()

        assert output

    def test_maximum_terminal_width(self):
        """Test with very wide terminal."""
        scan = Scan(
            id="wide",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nmap"],
            duration_ms=5000,
        )

        scan.findings.append(
            Finding(
                title="Test finding with a reasonably long title",
                severity=Severity.HIGH,
                description="Test",
                tool_id="nmap",
                target="example.com",
                evidence="test",
            )
        )

        # Very wide terminal
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=300)
        display = DisplayComponents(console)

        display.scan_summary(scan)
        output = buffer.getvalue()

        assert output

    def test_special_control_characters(self):
        """Test with control characters and special sequences."""
        scan = Scan(
            id="control",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei"],
            duration_ms=5000,
        )

        # Findings with control characters
        scan.findings.append(
            Finding(
                title="Finding with\ttab\nand\rnewlines",
                severity=Severity.HIGH,
                description="Test\x00null\x1bESC",
                tool_id="nuclei",
                target="example.com",
                evidence="test",
            )
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        # Should handle control characters
        display.findings_list(scan.findings, verbose=False)
        output = buffer.getvalue()

        assert output

    def test_json_serialization_large_dataset(self):
        """Test JSON serialization with large dataset."""
        scan = Scan(
            id="jsonlarge",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nuclei", "nmap", "ffuf"],
            duration_ms=500000,
        )

        # 500 findings with complex data
        for i in range(500):
            scan.findings.append(
                Finding(
                    title=f"Finding {i+1} with various special chars: ™ © €",
                    severity=Severity.HIGH if i % 3 == 0 else Severity.INFO,
                    description=f"Long description " * 50,
                    tool_id=["nuclei", "nmap", "ffuf"][i % 3],
                    target="example.com",
                    evidence=f"/path/to/evidence/{i+1}",
                    references=[
                        f"https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-{i}",
                        f"https://nvd.nist.gov/vuln/detail/CVE-2024-{i}",
                    ],
                    metadata={
                        "index": i,
                        "test_data": "x" * 100,
                        "nested": {"key": "value", "count": i},
                    },
                )
            )

        # Should serialize successfully
        json_str = format_scan_json(scan, compact=False)

        # Verify valid JSON
        data = json.loads(json_str)
        assert len(data["findings"]) == 500
        assert data["finding_counts"]["high"] > 0

    def test_stealth_mode_large_dataset(self, capsys):
        """Test stealth mode with large dataset."""
        scan = Scan(
            id="stealthlg",
            target="example.com",
            profile="full",
            status=ScanStatus.COMPLETED,
            tools_used=["nmap", "nuclei", "ffuf"],
            duration_ms=600000,
        )

        # 1000 findings
        for i in range(1000):
            scan.findings.append(
                Finding(
                    title=f"Finding {i+1}",
                    severity=Severity.INFO,
                    description="Test",
                    tool_id=["nmap", "nuclei", "ffuf"][i % 3],
                    target="example.com",
                    evidence="test",
                )
            )

        format_scan_stealth(scan, "0.1.0")
        captured = capsys.readouterr()

        # Should show total
        assert "1000" in captured.out
        assert "[DONE]" in captured.out

    def test_empty_values_everywhere(self):
        """Test with empty strings and None values throughout."""
        scan = Scan(
            id="",
            target="",
            profile="",
            status=ScanStatus.COMPLETED,
            tools_used=[],
            duration_ms=0,
        )

        scan.findings.append(
            Finding(
                title="",
                severity=Severity.INFO,
                description="",
                tool_id="",
                target="",
                evidence="",
            )
        )

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        # Should not crash
        display.scan_summary(scan)
        display.findings_list(scan.findings, verbose=False)
        output = buffer.getvalue()

        assert output  # Should produce some output

    def test_mixed_severity_distribution(self):
        """Test with various severity distributions."""
        test_cases = [
            # (critical, high, medium, low, info)
            (100, 0, 0, 0, 0),  # All critical
            (0, 0, 0, 0, 100),  # All info
            (50, 30, 15, 4, 1),  # Decreasing
            (1, 4, 15, 30, 50),  # Increasing
            (20, 20, 20, 20, 20),  # Even distribution
        ]

        for crit, high, med, low, info in test_cases:
            scan = Scan(
                id="sev",
                target="example.com",
                profile="full",
                status=ScanStatus.COMPLETED,
                tools_used=["nuclei"],
                duration_ms=5000,
            )

            # Add findings with specified distribution
            severities = (
                [Severity.CRITICAL] * crit
                + [Severity.HIGH] * high
                + [Severity.MEDIUM] * med
                + [Severity.LOW] * low
                + [Severity.INFO] * info
            )

            for i, sev in enumerate(severities):
                scan.findings.append(
                    Finding(
                        title=f"Finding {i}",
                        severity=sev,
                        description="Test",
                        tool_id="nuclei",
                        target="example.com",
                        evidence="test",
                    )
                )

            buffer = StringIO()
            console = Console(file=buffer, force_terminal=True, width=120)
            display = DisplayComponents(console)

            # Should handle all distributions
            display.scan_summary(scan)
            output = buffer.getvalue()

            assert output
            assert "Scan complete" in output or "complete" in output

    def test_concurrent_rendering(self):
        """Test that rendering is thread-safe (basic check)."""
        import threading

        results = []

        def render_scan(scan_id):
            scan = Scan(
                id=scan_id,
                target="example.com",
                profile="full",
                status=ScanStatus.COMPLETED,
                tools_used=["nmap"],
                duration_ms=5000,
            )

            for i in range(10):
                scan.findings.append(
                    Finding(
                        title=f"Finding {i}",
                        severity=Severity.INFO,
                        description="Test",
                        tool_id="nmap",
                        target="example.com",
                        evidence="test",
                    )
                )

            buffer = StringIO()
            console = Console(file=buffer, force_terminal=True, width=120)
            display = DisplayComponents(console)

            display.scan_summary(scan)
            results.append(buffer.getvalue())

        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=render_scan, args=(f"thread{i}",))
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()

        # All should have produced output
        assert len(results) == 10
        assert all(r for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
