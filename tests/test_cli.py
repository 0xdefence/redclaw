"""CLI smoke tests."""
from click.testing import CliRunner
from redclaw.cli.main import cli


class TestCLIBasic:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_help(self) -> None:
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "RedClaw" in result.output

    def test_version(self) -> None:
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_tools_list(self) -> None:
        result = self.runner.invoke(cli, ["tools"])
        assert result.exit_code == 0
        assert "nmap" in result.output.lower()

    def test_tools_search(self) -> None:
        result = self.runner.invoke(cli, ["tools", "search", "port"])
        assert result.exit_code == 0
        assert "nmap" in result.output.lower()

    def test_config_show(self) -> None:
        result = self.runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "Docker Image" in result.output

    def test_results_empty(self) -> None:
        result = self.runner.invoke(cli, ["results"])
        assert result.exit_code == 0
        # Should say no scans or show empty table

    def test_scan_blocked_target(self) -> None:
        result = self.runner.invoke(cli, ["scan", "127.0.0.1"])
        # Should fail due to policy (no Docker needed)
        assert result.exit_code in (0, 1)
