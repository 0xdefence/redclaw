"""Performance benchmarks for RedClaw output system."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from io import StringIO

import pytest
from rich.console import Console

from redclaw.models import Scan, Finding, ScanStatus, Severity
from redclaw.output.display import DisplayComponents
from redclaw.output.banner import print_banner
from redclaw.output.stealth import format_scan_stealth
from redclaw.output.json_output import format_scan_json


def create_scan_with_findings(count: int) -> Scan:
    """Create a scan with specified number of findings."""
    scan = Scan(
        id="bench",
        target="example.com",
        profile="full",
        status=ScanStatus.COMPLETED,
        tools_used=["nuclei"],
        duration_ms=50000,
        started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )

    for i in range(count):
        scan.findings.append(
            Finding(
                title=f"Benchmark finding {i+1}",
                severity=Severity.INFO,
                description=f"Description {i+1}",
                tool_id="nuclei",
                target="example.com",
                evidence=f"/path/{i+1}",
            )
        )

    return scan


class TestPerformanceBenchmarks:
    """Performance benchmarks for output rendering."""

    def test_benchmark_banner_rendering(self, benchmark):
        """Benchmark banner rendering performance."""

        def render_banner():
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                print_banner("0.1.0", stealth=False)
            finally:
                sys.stdout = old_stdout
            return True

        benchmark(render_banner)

    def test_benchmark_scan_header(self, benchmark):
        """Benchmark scan header rendering."""
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        def render():
            buffer.seek(0)
            buffer.truncate()
            display.scan_header("example.com", "full", ["nmap", "nuclei"], "abc123")

        benchmark(render)

    def test_benchmark_scan_summary_small(self, benchmark):
        """Benchmark scan summary with 10 findings."""
        scan = create_scan_with_findings(10)
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        def render():
            buffer.seek(0)
            buffer.truncate()
            display.scan_summary(scan)

        benchmark(render)

    def test_benchmark_scan_summary_medium(self, benchmark):
        """Benchmark scan summary with 100 findings."""
        scan = create_scan_with_findings(100)
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        def render():
            buffer.seek(0)
            buffer.truncate()
            display.scan_summary(scan)

        benchmark(render)

    def test_benchmark_scan_summary_large(self, benchmark):
        """Benchmark scan summary with 1000 findings."""
        scan = create_scan_with_findings(1000)
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        def render():
            buffer.seek(0)
            buffer.truncate()
            display.scan_summary(scan)

        benchmark(render)

    def test_benchmark_findings_list_small(self, benchmark):
        """Benchmark findings list with 10 findings."""
        scan = create_scan_with_findings(10)
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        def render():
            buffer.seek(0)
            buffer.truncate()
            display.findings_list(scan.findings, verbose=False)

        benchmark(render)

    def test_benchmark_findings_list_large(self, benchmark):
        """Benchmark findings list with 100 findings."""
        scan = create_scan_with_findings(100)
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        def render():
            buffer.seek(0)
            buffer.truncate()
            display.findings_list(scan.findings, verbose=False)

        benchmark(render)

    def test_benchmark_json_serialization_small(self, benchmark):
        """Benchmark JSON serialization with 10 findings."""
        scan = create_scan_with_findings(10)

        def serialize():
            return format_scan_json(scan, compact=False)

        benchmark(serialize)

    def test_benchmark_json_serialization_large(self, benchmark):
        """Benchmark JSON serialization with 1000 findings."""
        scan = create_scan_with_findings(1000)

        def serialize():
            return format_scan_json(scan, compact=False)

        benchmark(serialize)

    def test_benchmark_stealth_mode_small(self, benchmark):
        """Benchmark stealth mode with 10 findings."""
        scan = create_scan_with_findings(10)

        def render():
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                format_scan_stealth(scan, "0.1.0")
            finally:
                sys.stdout = old_stdout

        benchmark(render)

    def test_benchmark_stealth_mode_large(self, benchmark):
        """Benchmark stealth mode with 1000 findings."""
        scan = create_scan_with_findings(1000)

        def render():
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                format_scan_stealth(scan, "0.1.0")
            finally:
                sys.stdout = old_stdout

        benchmark(render)


class TestMemoryUsage:
    """Memory usage tests for large datasets."""

    def test_memory_large_dataset(self):
        """Test memory usage with large dataset."""
        import sys

        # Get memory usage before
        import gc

        gc.collect()

        # Create large scan
        scan = create_scan_with_findings(1000)

        # Render
        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        display.scan_summary(scan)
        display.findings_list(scan.findings, verbose=False)

        # Output should be reasonable size
        output = buffer.getvalue()
        output_size = len(output)

        # Output should be less than 1MB for 1000 findings
        assert output_size < 1024 * 1024

        # Clean up
        del scan
        del buffer
        del console
        del display
        gc.collect()


class TestScalabilityManual:
    """Manual scalability tests (not run by default)."""

    @pytest.mark.skip(reason="Manual performance test")
    def test_scalability_10000_findings(self):
        """Test with 10,000 findings (manual test)."""
        print("\nTesting with 10,000 findings...")

        scan = create_scan_with_findings(10000)

        buffer = StringIO()
        console = Console(file=buffer, force_terminal=True, width=120)
        display = DisplayComponents(console)

        start = time.perf_counter()
        display.scan_summary(scan)
        end = time.perf_counter()

        print(f"Scan summary: {(end - start) * 1000:.2f}ms")

        start = time.perf_counter()
        json_str = format_scan_json(scan, compact=True)
        end = time.perf_counter()

        print(f"JSON serialization: {(end - start) * 1000:.2f}ms")
        print(f"JSON size: {len(json_str) / 1024:.2f}KB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
