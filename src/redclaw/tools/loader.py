"""Custom tool loader — load tool definitions from YAML files.

Enables users to define custom tools without writing Python code.
Tools are defined in YAML with command templates and output parsers.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from redclaw.models import ToolMeta, ToolCategory, RiskLevel, Finding, Severity, get_config
from redclaw.tools.base import BaseTool
from redclaw.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from redclaw.core.executor import DockerExecutor


@dataclass
class YAMLToolConfig:
    """Configuration for a YAML-defined tool."""
    id: str
    name: str
    description: str
    binary: str
    category: ToolCategory
    risk_level: RiskLevel
    default_timeout: int
    args_template: list[str]
    output_format: str  # json, jsonl, xml, text
    parser_config: dict[str, Any]
    finding_rules: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "YAMLToolConfig":
        """Create config from parsed YAML dict."""
        category = ToolCategory(data.get("category", "scanning"))
        risk_level = RiskLevel(data.get("risk_level", "active"))

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description", ""),
            binary=data["binary"],
            category=category,
            risk_level=risk_level,
            default_timeout=data.get("default_timeout", 120),
            args_template=data.get("args", []),
            output_format=data.get("output_format", "text"),
            parser_config=data.get("parser", {}),
            finding_rules=data.get("findings", []),
        )


class DynamicTool(BaseTool):
    """A tool created dynamically from YAML configuration."""

    def __init__(self, config: YAMLToolConfig) -> None:
        self.config = config
        self.meta = ToolMeta(
            id=config.id,
            name=config.name,
            description=config.description,
            category=config.category,
            risk_level=config.risk_level,
            binary=config.binary,
            default_timeout=config.default_timeout,
        )

    def build_args(self, target: str, **kwargs: object) -> list[str]:
        """Build CLI arguments from template."""
        args = []
        for template in self.config.args_template:
            # Replace {{target}} with actual target
            arg = template.replace("{{target}}", target)

            # Replace {{kwarg_name}} with kwargs
            for key, value in kwargs.items():
                arg = arg.replace(f"{{{{{key}}}}}", str(value))

            # Skip args with unreplaced templates (optional args not provided)
            if "{{" not in arg:
                args.append(arg)

        return args

    def parse_output(self, raw: str) -> dict:
        """Parse output based on configured format."""
        if self.config.output_format == "json":
            return self._parse_json(raw)
        elif self.config.output_format == "jsonl":
            return self._parse_jsonl(raw)
        elif self.config.output_format == "xml":
            return self._parse_xml(raw)
        else:
            return self._parse_text(raw)

    def _parse_json(self, raw: str) -> dict:
        """Parse JSON output."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw, "parse_error": "Invalid JSON"}

    def _parse_jsonl(self, raw: str) -> dict:
        """Parse JSONL (one JSON object per line)."""
        items = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return {"items": items, "total": len(items)}

    def _parse_xml(self, raw: str) -> dict:
        """Parse XML output."""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(raw)
            return self._xml_to_dict(root)
        except Exception:
            return {"raw": raw, "parse_error": "Invalid XML"}

    def _xml_to_dict(self, element) -> dict:
        """Convert XML element to dict recursively."""
        result: dict[str, Any] = {}
        if element.attrib:
            result["@attrs"] = element.attrib
        if element.text and element.text.strip():
            result["@text"] = element.text.strip()
        for child in element:
            child_dict = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_dict)
            else:
                result[child.tag] = child_dict
        return result

    def _parse_text(self, raw: str) -> dict:
        """Parse text output using configured regex patterns."""
        parser_config = self.config.parser_config
        result: dict[str, Any] = {"raw": raw, "lines": raw.splitlines()}

        # Extract fields using regex patterns
        patterns = parser_config.get("patterns", {})
        for field_name, pattern in patterns.items():
            matches = re.findall(pattern, raw, re.MULTILINE)
            result[field_name] = matches

        # Key-value extraction
        if parser_config.get("key_value"):
            delimiter = parser_config.get("kv_delimiter", ":")
            kv_pairs = {}
            for line in raw.splitlines():
                if delimiter in line:
                    parts = line.split(delimiter, 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower().replace(" ", "_")
                        value = parts[1].strip()
                        kv_pairs[key] = value
            result["key_values"] = kv_pairs

        return result

    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        """Extract findings based on configured rules."""
        findings = []

        for rule in self.config.finding_rules:
            rule_type = rule.get("type", "match")

            if rule_type == "match":
                findings.extend(self._apply_match_rule(rule, parsed, target))
            elif rule_type == "iterate":
                findings.extend(self._apply_iterate_rule(rule, parsed, target))
            elif rule_type == "regex":
                findings.extend(self._apply_regex_rule(rule, parsed, target))

        return findings

    def _apply_match_rule(self, rule: dict, parsed: dict, target: str) -> list[Finding]:
        """Apply a simple match rule."""
        findings = []
        field = rule.get("field", "raw")
        pattern = rule.get("pattern", "")
        value = self._get_nested_value(parsed, field)

        if value and pattern:
            if isinstance(value, str) and re.search(pattern, value):
                findings.append(self._create_finding(rule, target, value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and re.search(pattern, item):
                        findings.append(self._create_finding(rule, target, item))

        return findings

    def _apply_iterate_rule(self, rule: dict, parsed: dict, target: str) -> list[Finding]:
        """Apply an iterate rule over a list field."""
        findings = []
        field = rule.get("field", "items")
        items = self._get_nested_value(parsed, field)

        if isinstance(items, list):
            for item in items:
                finding = self._create_finding_from_item(rule, target, item)
                if finding:
                    findings.append(finding)

        return findings

    def _apply_regex_rule(self, rule: dict, parsed: dict, target: str) -> list[Finding]:
        """Apply a regex extraction rule."""
        findings = []
        field = rule.get("field", "raw")
        pattern = rule.get("pattern", "")
        value = self._get_nested_value(parsed, field)

        if value and pattern:
            if isinstance(value, str):
                matches = re.findall(pattern, value, re.MULTILINE)
                for match in matches:
                    finding = self._create_finding(rule, target, match if isinstance(match, str) else str(match))
                    findings.append(finding)

        return findings

    def _get_nested_value(self, data: dict, field: str) -> Any:
        """Get a nested value from dict using dot notation."""
        parts = field.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                value = value[idx] if idx < len(value) else None
            else:
                return None
        return value

    def _create_finding(self, rule: dict, target: str, evidence: str) -> Finding:
        """Create a finding from a rule match."""
        severity_str = rule.get("severity", "info")
        severity = Severity(severity_str) if severity_str in [s.value for s in Severity] else Severity.INFO

        return Finding(
            title=rule.get("title", "Finding"),
            severity=severity,
            description=rule.get("description", ""),
            tool_id=self.config.id,
            target=target,
            evidence=evidence[:500],  # Truncate evidence
            remediation=rule.get("remediation", ""),
            references=rule.get("references", []),
        )

    def _create_finding_from_item(self, rule: dict, target: str, item: Any) -> Finding | None:
        """Create a finding from an iterated item."""
        if not isinstance(item, dict):
            return None

        # Use field mappings from rule
        mappings = rule.get("mappings", {})

        title_field = mappings.get("title", "title")
        severity_field = mappings.get("severity", "severity")
        description_field = mappings.get("description", "description")

        title = item.get(title_field, rule.get("title", "Finding"))
        severity_str = item.get(severity_field, rule.get("severity", "info"))
        description = item.get(description_field, rule.get("description", ""))

        severity = Severity(severity_str) if severity_str in [s.value for s in Severity] else Severity.INFO

        return Finding(
            title=str(title),
            severity=severity,
            description=str(description),
            tool_id=self.config.id,
            target=target,
            evidence=json.dumps(item)[:500],
            remediation=rule.get("remediation", ""),
            references=rule.get("references", []),
            metadata={"source_item": item},
        )


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file. Uses tomllib-style parsing or PyYAML if available."""
    content = path.read_text()

    # Try PyYAML first
    try:
        import yaml
        return yaml.safe_load(content)
    except ImportError:
        pass

    # Fallback to simple YAML subset parser
    return _simple_yaml_parse(content)


def _simple_yaml_parse(content: str) -> dict[str, Any]:
    """Parse a simple YAML subset (key: value, lists, nested dicts)."""
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[Any] | None = None
    indent_stack: list[tuple[int, str, dict]] = []

    for line in content.splitlines():
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # Handle list items
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if current_list is not None:
                # Parse value (could be string, number, etc.)
                current_list.append(_parse_yaml_value(value))
            continue

        # Handle key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            # Nested dict
            while indent_stack and indent <= indent_stack[-1][0]:
                indent_stack.pop()

            target = result
            for _, _, d in indent_stack:
                target = d

            if value:
                target[key] = _parse_yaml_value(value)
                current_list = None
            else:
                # Check if next line is a list
                target[key] = []
                current_list = target[key]
                current_key = key

    return result


def _parse_yaml_value(value: str) -> Any:
    """Parse a YAML value to appropriate Python type."""
    # Remove quotes
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return value[1:-1]

    # Boolean
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False

    # Number
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    return value


def load_tool_from_yaml(path: Path) -> DynamicTool | None:
    """Load a single tool from a YAML file."""
    try:
        data = load_yaml(path)
        if not data or "id" not in data or "binary" not in data:
            return None
        config = YAMLToolConfig.from_dict(data)
        return DynamicTool(config)
    except Exception:
        return None


def load_custom_tools(directory: Path, registry: ToolRegistry) -> int:
    """Load custom tool definitions from YAML files in a directory.

    Returns number of tools loaded.
    """
    if not directory.exists():
        return 0

    count = 0
    for yaml_file in directory.glob("*.yaml"):
        tool = load_tool_from_yaml(yaml_file)
        if tool:
            registry.register(tool)
            count += 1

    for yml_file in directory.glob("*.yml"):
        tool = load_tool_from_yaml(yml_file)
        if tool:
            registry.register(tool)
            count += 1

    return count


def get_plugin_directory() -> Path:
    """Get the user's plugin directory (~/.redclaw/plugins/)."""
    config = get_config()
    plugins_dir = config.data_dir / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return plugins_dir


def install_tool_yaml(source: Path, overwrite: bool = False) -> tuple[bool, str]:
    """Install a YAML tool definition to the plugins directory.

    Args:
        source: Path to the YAML file
        overwrite: Whether to overwrite existing tool

    Returns:
        (success, message) tuple
    """
    if not source.exists():
        return False, f"File not found: {source}"

    if not source.suffix.lower() in (".yaml", ".yml"):
        return False, "File must be .yaml or .yml"

    # Validate the tool definition
    tool = load_tool_from_yaml(source)
    if tool is None:
        return False, "Invalid tool definition: missing 'id' or 'binary'"

    # Check binary availability
    binary = tool.meta.binary
    if not shutil.which(binary):
        return False, f"Warning: Binary '{binary}' not found in PATH"

    # Copy to plugins directory
    plugins_dir = get_plugin_directory()
    dest = plugins_dir / source.name

    if dest.exists() and not overwrite:
        return False, f"Tool already exists: {dest}. Use --force to overwrite."

    shutil.copy2(source, dest)
    return True, f"Installed tool '{tool.meta.id}' to {dest}"


def list_installed_tools() -> list[tuple[str, Path]]:
    """List all installed custom tools.

    Returns:
        List of (tool_id, file_path) tuples
    """
    plugins_dir = get_plugin_directory()
    tools = []

    for path in plugins_dir.glob("*.yaml"):
        tool = load_tool_from_yaml(path)
        if tool:
            tools.append((tool.meta.id, path))

    for path in plugins_dir.glob("*.yml"):
        tool = load_tool_from_yaml(path)
        if tool:
            tools.append((tool.meta.id, path))

    return tools


def uninstall_tool(tool_id: str) -> tuple[bool, str]:
    """Uninstall a custom tool.

    Args:
        tool_id: ID of the tool to uninstall

    Returns:
        (success, message) tuple
    """
    plugins_dir = get_plugin_directory()

    for path in list(plugins_dir.glob("*.yaml")) + list(plugins_dir.glob("*.yml")):
        tool = load_tool_from_yaml(path)
        if tool and tool.meta.id == tool_id:
            path.unlink()
            return True, f"Uninstalled tool '{tool_id}'"

    return False, f"Tool '{tool_id}' not found in plugins"
