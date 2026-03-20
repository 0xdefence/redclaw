"""Nikto web vulnerability scanner wrapper."""
from __future__ import annotations

import re

from redclaw.models import ToolMeta, ToolCategory, RiskLevel, Finding, Severity
from redclaw.tools.base import BaseTool


class NiktoTool(BaseTool):
    meta = ToolMeta(
        id="nikto",
        name="Nikto Web Scanner",
        description="Web server scanner that tests for dangerous files, outdated server versions, and server configuration issues.",
        category=ToolCategory.SCANNING,
        risk_level=RiskLevel.INTRUSIVE,
        binary="nikto",
        default_timeout=120,
    )

    def build_args(self, target: str, **kwargs: object) -> list[str]:
        args = ["-h", target, "-maxtime", "60"]
        if kwargs.get("ssl"):
            args.append("-ssl")
        if kwargs.get("tuning"):
            args.extend(["-Tuning", str(kwargs["tuning"])])
        return args

    def parse_output(self, raw: str) -> dict:
        """Parse nikto text output into structured data."""
        result: dict = {
            "target": "",
            "port": 0,
            "server": "",
            "items": [],
            "summary": "",
        }

        for line in raw.splitlines():
            line = line.strip()

            # Target info
            target_match = re.match(r"\+ Target IP:\s+(.+)", line)
            if target_match:
                result["target"] = target_match.group(1)

            port_match = re.match(r"\+ Target Port:\s+(\d+)", line)
            if port_match:
                result["port"] = int(port_match.group(1))

            server_match = re.match(r"\+ Server:\s+(.+)", line)
            if server_match:
                result["server"] = server_match.group(1)

            # Finding lines start with "+ " and contain OSVDB or vulnerability info
            if line.startswith("+ ") and not line.startswith("+ Target") and not line.startswith("+ Server") and not line.startswith("+ Start") and not line.startswith("+ End"):
                item: dict = {"text": line[2:], "osvdb": None, "uri": None}

                osvdb_match = re.search(r"OSVDB-(\d+)", line)
                if osvdb_match:
                    item["osvdb"] = f"OSVDB-{osvdb_match.group(1)}"

                uri_match = re.search(r"(/\S+)", line)
                if uri_match:
                    item["uri"] = uri_match.group(1)

                result["items"].append(item)

            # Summary
            if "requests" in line.lower() and "error" in line.lower():
                result["summary"] = line

        return result

    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        findings: list[Finding] = []
        for item in parsed.get("items", []):
            text = item.get("text", "")

            # Classify severity based on keywords
            severity = Severity.INFO
            text_lower = text.lower()
            if any(w in text_lower for w in ["vulnerability", "exploit", "injection", "rce", "xss"]):
                severity = Severity.HIGH
            elif any(w in text_lower for w in ["outdated", "deprecated", "insecure", "missing header"]):
                severity = Severity.MEDIUM
            elif any(w in text_lower for w in ["directory listing", "backup", "default"]):
                severity = Severity.LOW

            refs: list[str] = []
            if item.get("osvdb"):
                refs.append(item["osvdb"])

            findings.append(Finding(
                title=text[:100],
                severity=severity,
                description=text,
                tool_id="nikto",
                target=target,
                evidence=item.get("uri", ""),
                references=refs,
                metadata=item,
            ))
        return findings
