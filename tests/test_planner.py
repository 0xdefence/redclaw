"""Tests for ScanPlanner (without Docker)."""
import os

from redclaw.core.planner import ScanPlanner
from redclaw.models import ScanStatus


class TestPlannerValidation:
    """Test planner handles invalid inputs correctly (no Docker needed)."""

    def setup_method(self) -> None:
        self.planner = ScanPlanner()

    def test_blocked_target(self) -> None:
        scan = self.planner.run_scan("127.0.0.1")
        assert scan.status == ScanStatus.FAILED
        assert scan.error is not None
        assert "private" in scan.error.lower() or "reserved" in scan.error.lower()

    def test_unknown_tool(self) -> None:
        scan = self.planner.run_scan("example.com", tools=["nonexistent_tool"])
        assert scan.status == ScanStatus.FAILED
        assert "unknown tool" in (scan.error or "").lower()

    def test_unknown_profile(self) -> None:
        try:
            self.planner.run_scan("example.com", profile_name="nonexistent_profile")
            assert False, "Should have raised"
        except ValueError as e:
            assert "unknown profile" in str(e).lower()
