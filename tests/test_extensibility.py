"""Tests for Phase 3: Extensibility — YAML tools, plugins, file storage."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ─── YAML Tool Loader Tests ───────────────────────────────────────────────────


class TestYAMLToolLoader:
    """Tests for YAML tool loading functionality."""

    def test_load_yaml_simple(self, tmp_path: Path) -> None:
        """Test loading a simple YAML file."""
        from redclaw.tools.loader import load_yaml

        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("""
id: test_tool
binary: testtool
name: Test Tool
description: A test tool
""")

        data = load_yaml(yaml_file)
        assert data["id"] == "test_tool"
        assert data["binary"] == "testtool"
        assert data["name"] == "Test Tool"

    def test_yaml_tool_config_from_dict(self) -> None:
        """Test creating YAMLToolConfig from dict."""
        from redclaw.tools.loader import YAMLToolConfig
        from redclaw.models import ToolCategory, RiskLevel

        data = {
            "id": "my_tool",
            "binary": "mytool",
            "name": "My Tool",
            "description": "Tool description",
            "category": "scanning",
            "risk_level": "active",
            "default_timeout": 60,
            "args": ["-t", "{{target}}"],
            "output_format": "json",
        }

        config = YAMLToolConfig.from_dict(data)
        assert config.id == "my_tool"
        assert config.binary == "mytool"
        assert config.category == ToolCategory.SCANNING
        assert config.risk_level == RiskLevel.ACTIVE
        assert config.default_timeout == 60
        assert config.output_format == "json"

    def test_dynamic_tool_creation(self, tmp_path: Path) -> None:
        """Test creating a DynamicTool from YAML."""
        from redclaw.tools.loader import load_tool_from_yaml

        yaml_file = tmp_path / "scanner.yaml"
        yaml_file.write_text("""
id: custom_scanner
binary: scanner
name: Custom Scanner
description: A custom security scanner
category: scanning
risk_level: active
default_timeout: 120
args:
  - "--target"
  - "{{target}}"
  - "--format"
  - "json"
output_format: json
""")

        tool = load_tool_from_yaml(yaml_file)
        assert tool is not None
        assert tool.meta.id == "custom_scanner"
        assert tool.meta.binary == "scanner"

    def test_dynamic_tool_build_args(self, tmp_path: Path) -> None:
        """Test argument building with template substitution."""
        from redclaw.tools.loader import load_tool_from_yaml

        yaml_file = tmp_path / "tool.yaml"
        yaml_file.write_text("""
id: test
binary: test
args:
  - "-t"
  - "{{target}}"
  - "-p"
  - "{{port}}"
output_format: text
""")

        tool = load_tool_from_yaml(yaml_file)
        assert tool is not None

        args = tool.build_args("example.com", port=8080)
        assert args == ["-t", "example.com", "-p", "8080"]

    def test_dynamic_tool_parse_json(self, tmp_path: Path) -> None:
        """Test JSON output parsing."""
        from redclaw.tools.loader import load_tool_from_yaml

        yaml_file = tmp_path / "tool.yaml"
        yaml_file.write_text("""
id: test
binary: test
output_format: json
""")

        tool = load_tool_from_yaml(yaml_file)
        assert tool is not None

        result = tool.parse_output('{"status": "ok", "count": 5}')
        assert result["status"] == "ok"
        assert result["count"] == 5

    def test_dynamic_tool_parse_jsonl(self, tmp_path: Path) -> None:
        """Test JSONL output parsing."""
        from redclaw.tools.loader import load_tool_from_yaml

        yaml_file = tmp_path / "tool.yaml"
        yaml_file.write_text("""
id: test
binary: test
output_format: jsonl
""")

        tool = load_tool_from_yaml(yaml_file)
        assert tool is not None

        raw = '{"item": 1}\n{"item": 2}\n{"item": 3}'
        result = tool.parse_output(raw)
        assert result["total"] == 3
        assert len(result["items"]) == 3

    def test_dynamic_tool_extract_findings_iterate(self, tmp_path: Path) -> None:
        """Test finding extraction with iterate rule."""
        from redclaw.tools.loader import load_tool_from_yaml

        yaml_file = tmp_path / "tool.yaml"
        yaml_file.write_text("""
id: test
binary: test
output_format: json
findings:
  - type: iterate
    field: results
    mappings:
      title: name
      severity: level
      description: desc
""")

        tool = load_tool_from_yaml(yaml_file)
        assert tool is not None

        parsed = {
            "results": [
                {"name": "Finding 1", "level": "high", "desc": "Description 1"},
                {"name": "Finding 2", "level": "low", "desc": "Description 2"},
            ]
        }

        findings = tool.extract_findings(parsed, "example.com")
        assert len(findings) == 2
        assert findings[0].title == "Finding 1"
        assert findings[0].severity.value == "high"

    def test_load_custom_tools_from_directory(self, tmp_path: Path) -> None:
        """Test loading multiple custom tools from a directory."""
        from redclaw.tools.loader import load_custom_tools
        from redclaw.tools.registry import ToolRegistry

        # Create two tool files
        (tmp_path / "tool1.yaml").write_text("""
id: tool1
binary: bin1
name: Tool 1
""")
        (tmp_path / "tool2.yml").write_text("""
id: tool2
binary: bin2
name: Tool 2
""")

        registry = ToolRegistry()
        count = load_custom_tools(tmp_path, registry)

        assert count == 2
        assert registry.get("tool1") is not None
        assert registry.get("tool2") is not None


class TestPluginManagement:
    """Tests for plugin installation and management."""

    def test_get_plugin_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Test plugin directory creation."""
        from redclaw.tools.loader import get_plugin_directory
        from redclaw.models import get_config

        config = get_config()
        monkeypatch.setattr(config, "data_dir", tmp_path)

        plugins_dir = get_plugin_directory()
        assert plugins_dir.exists()
        assert plugins_dir.name == "plugins"

    def test_install_tool_yaml(self, tmp_path: Path, monkeypatch) -> None:
        """Test installing a tool YAML file."""
        from redclaw.tools.loader import install_tool_yaml, get_plugin_directory
        from redclaw.models import get_config

        config = get_config()
        monkeypatch.setattr(config, "data_dir", tmp_path)

        # Create a source YAML
        source = tmp_path / "source" / "my_tool.yaml"
        source.parent.mkdir()
        source.write_text("""
id: my_tool
binary: echo
name: My Tool
""")

        success, message = install_tool_yaml(source)
        assert success
        assert "Installed" in message

        # Check it's in the plugins directory
        plugins_dir = get_plugin_directory()
        assert (plugins_dir / "my_tool.yaml").exists()

    def test_install_tool_yaml_no_overwrite(self, tmp_path: Path, monkeypatch) -> None:
        """Test that install doesn't overwrite without --force."""
        from redclaw.tools.loader import install_tool_yaml, get_plugin_directory
        from redclaw.models import get_config

        config = get_config()
        monkeypatch.setattr(config, "data_dir", tmp_path)

        # Create source
        source = tmp_path / "source" / "tool.yaml"
        source.parent.mkdir()
        source.write_text("id: tool\nbinary: echo")

        # Install first time
        install_tool_yaml(source)

        # Try to install again
        success, message = install_tool_yaml(source, overwrite=False)
        assert not success
        assert "already exists" in message

    def test_list_installed_tools(self, tmp_path: Path, monkeypatch) -> None:
        """Test listing installed plugins."""
        from redclaw.tools.loader import list_installed_tools, get_plugin_directory
        from redclaw.models import get_config

        config = get_config()
        monkeypatch.setattr(config, "data_dir", tmp_path)

        plugins_dir = get_plugin_directory()
        (plugins_dir / "t1.yaml").write_text("id: t1\nbinary: b1")
        (plugins_dir / "t2.yml").write_text("id: t2\nbinary: b2")

        installed = list_installed_tools()
        ids = [t[0] for t in installed]

        assert "t1" in ids
        assert "t2" in ids

    def test_uninstall_tool(self, tmp_path: Path, monkeypatch) -> None:
        """Test uninstalling a plugin."""
        from redclaw.tools.loader import uninstall_tool, get_plugin_directory
        from redclaw.models import get_config

        config = get_config()
        monkeypatch.setattr(config, "data_dir", tmp_path)

        plugins_dir = get_plugin_directory()
        (plugins_dir / "removeme.yaml").write_text("id: removeme\nbinary: echo")

        success, message = uninstall_tool("removeme")
        assert success
        assert not (plugins_dir / "removeme.yaml").exists()


# ─── File Storage Tests ───────────────────────────────────────────────────────


class TestFileStorage:
    """Tests for raw output file storage."""

    def test_save_raw_output(self, tmp_path: Path) -> None:
        """Test saving raw tool output."""
        from redclaw.storage.files import save_raw_output

        output_file = save_raw_output(
            scan_id="scan123",
            tool_id="nmap",
            raw_output="PORT   STATE SERVICE\n22/tcp open  ssh",
            command="nmap -sV example.com",
            data_dir=tmp_path,
        )

        assert output_file.exists()
        content = output_file.read_text()
        assert "nmap" in content
        assert "22/tcp" in content
        assert "example.com" in content

    def test_get_raw_output(self, tmp_path: Path) -> None:
        """Test retrieving raw output."""
        from redclaw.storage.files import save_raw_output, get_raw_output

        save_raw_output(
            scan_id="scan456",
            tool_id="nuclei",
            raw_output='{"finding": "test"}',
            command="nuclei -u example.com",
            data_dir=tmp_path,
        )

        output = get_raw_output("scan456", "nuclei", data_dir=tmp_path)
        assert output is not None
        assert '{"finding": "test"}' in output

    def test_get_raw_output_not_found(self, tmp_path: Path) -> None:
        """Test retrieving non-existent output."""
        from redclaw.storage.files import get_raw_output

        output = get_raw_output("nonexistent", "nmap", data_dir=tmp_path)
        assert output is None

    def test_list_scan_outputs(self, tmp_path: Path) -> None:
        """Test listing all outputs for a scan."""
        from redclaw.storage.files import save_raw_output, list_scan_outputs

        save_raw_output("scan789", "nmap", "output1", "cmd1", data_dir=tmp_path)
        save_raw_output("scan789", "nuclei", "output2", "cmd2", data_dir=tmp_path)

        outputs = list_scan_outputs("scan789", data_dir=tmp_path)
        tool_ids = [t[0] for t in outputs]

        assert len(outputs) == 2
        assert "nmap" in tool_ids
        assert "nuclei" in tool_ids

    def test_list_all_runs(self, tmp_path: Path) -> None:
        """Test listing all scan runs."""
        from redclaw.storage.files import save_raw_output, list_all_runs

        save_raw_output("run1", "nmap", "out", "cmd", data_dir=tmp_path)
        save_raw_output("run2", "nmap", "out", "cmd", data_dir=tmp_path)
        save_raw_output("run3", "nmap", "out", "cmd", data_dir=tmp_path)

        runs = list_all_runs(data_dir=tmp_path)
        assert len(runs) == 3
        assert "run1" in runs
        assert "run2" in runs
        assert "run3" in runs

    def test_delete_run_outputs(self, tmp_path: Path) -> None:
        """Test deleting outputs for a scan."""
        from redclaw.storage.files import save_raw_output, delete_run_outputs, list_scan_outputs

        save_raw_output("to_delete", "nmap", "out", "cmd", data_dir=tmp_path)
        save_raw_output("to_delete", "nuclei", "out", "cmd", data_dir=tmp_path)

        result = delete_run_outputs("to_delete", data_dir=tmp_path)
        assert result is True

        outputs = list_scan_outputs("to_delete", data_dir=tmp_path)
        assert len(outputs) == 0


# ─── Banner Tests ─────────────────────────────────────────────────────────────


class TestBanner:
    """Tests for banner and branding."""

    def test_print_banner(self, capsys) -> None:
        """Test banner output."""
        from redclaw.output.banner import print_banner

        print_banner("1.0.0")
        captured = capsys.readouterr()
        assert "REDCLAW" in captured.out or "██" in captured.out

    def test_print_banner_stealth(self, capsys) -> None:
        """Test stealth banner output."""
        from redclaw.output.banner import print_banner

        print_banner("1.0.0", stealth=True)
        captured = capsys.readouterr()
        assert "1.0.0" in captured.out
        # Stealth mode should be minimal
        assert "██" not in captured.out

    # test_get_crab_art removed - get_crab_art function not in spec and was removed


# ─── Integration Tests ────────────────────────────────────────────────────────


class TestExtensibilityIntegration:
    """Integration tests for the extensibility system."""

    def test_registry_with_custom_tools(self, tmp_path: Path) -> None:
        """Test that custom tools integrate with the registry."""
        from redclaw.tools.loader import load_custom_tools
        from redclaw.tools import create_default_registry

        # Create a custom tool
        (tmp_path / "custom.yaml").write_text("""
id: custom_enum
binary: enumerate
name: Custom Enumerator
description: Custom enumeration tool
category: enumeration
risk_level: active
args:
  - "-u"
  - "{{target}}"
output_format: text
""")

        registry = create_default_registry()
        initial_count = registry.count

        load_custom_tools(tmp_path, registry)

        assert registry.count == initial_count + 1
        assert registry.get("custom_enum") is not None

    def test_custom_tool_in_category_filter(self, tmp_path: Path) -> None:
        """Test that custom tools appear in category filters."""
        from redclaw.tools.loader import load_custom_tools
        from redclaw.tools import create_default_registry

        (tmp_path / "recon.yaml").write_text("""
id: custom_recon
binary: recon
category: recon
risk_level: passive
""")

        registry = create_default_registry()
        load_custom_tools(tmp_path, registry)

        recon_tools = registry.filter_by_category("recon")
        tool_ids = [t.meta.id for t in recon_tools]

        assert "custom_recon" in tool_ids
        assert "dig" in tool_ids  # Built-in recon tool
