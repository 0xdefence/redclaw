"""Nuclei template-based vulnerability scanner wrapper."""
from __future__ import annotations

import json
import re

from redclaw.models import ToolMeta, ToolCategory, RiskLevel, Finding, Severity
from redclaw.tools.base import BaseTool


class NucleiTool(BaseTool):
    meta = ToolMeta(
        id="nuclei",
        name="Nuclei Scanner",
        description="Fast template-based vulnerability scanner. Detects CVEs, misconfigurations, and security issues using community templates.",
        category=ToolCategory.SCANNING,
        risk_level=RiskLevel.INTRUSIVE,
        binary="nuclei",
        default_timeout=300,
    )

    def build_args(self, target: str, **kwargs: object) -> list[str]:
        args = ["-u", target, "-jsonl", "-silent"]

        # Severity filter
        severity = kwargs.get("severity")
        if severity:
            args.extend(["-severity", str(severity)])

        # Tag filter (e.g., cve, xss, sqli)
        tags = kwargs.get("tags")
        if tags:
            args.extend(["-tags", str(tags)])

        # Template filter
        templates = kwargs.get("templates")
        if templates:
            args.extend(["-t", str(templates)])

        # Rate limiting
        rate_limit = kwargs.get("rate_limit", 150)
        args.extend(["-rate-limit", str(rate_limit)])

        return args

    def parse_output(self, raw: str) -> dict:
        """Parse nuclei JSONL output."""
        results: list[dict] = []

        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
                results.append({
                    "template_id": entry.get("template-id", ""),
                    "name": entry.get("info", {}).get("name", ""),
                    "severity": entry.get("info", {}).get("severity", "info"),
                    "description": entry.get("info", {}).get("description", ""),
                    "matched_at": entry.get("matched-at", ""),
                    "matcher_name": entry.get("matcher-name", ""),
                    "host": entry.get("host", ""),
                    "type": entry.get("type", ""),
                    "extracted_results": entry.get("extracted-results", []),
                    "curl_command": entry.get("curl-command", ""),
                    "tags": entry.get("info", {}).get("tags", []),
                    "reference": entry.get("info", {}).get("reference", []),
                })
            except json.JSONDecodeError:
                # Handle non-JSON lines (status messages, etc.)
                continue

        return {"findings": results, "count": len(results)}

    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        findings: list[Finding] = []

        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }

        for item in parsed.get("findings", []):
            sev_str = item.get("severity", "info").lower()
            severity = severity_map.get(sev_str, Severity.INFO)

            title = item.get("name", "Unknown vulnerability")
            template_id = item.get("template_id", "")
            if template_id:
                title = f"[{template_id}] {title}"

            description = item.get("description", "")
            if not description:
                description = f"Nuclei detected {item.get('name', 'an issue')} at {item.get('matched_at', target)}"

            references = item.get("reference", [])
            if isinstance(references, str):
                references = [references]

            findings.append(Finding(
                title=title[:100],
                severity=severity,
                description=description,
                tool_id="nuclei",
                target=target,
                evidence=item.get("matched_at", ""),
                references=references,
                metadata={
                    "template_id": template_id,
                    "tags": item.get("tags", []),
                    "type": item.get("type", ""),
                    "curl_command": item.get("curl_command", ""),
                },
            ))

        return findings
