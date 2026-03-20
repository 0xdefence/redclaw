"""DNS tools — dig and whois wrappers."""
from __future__ import annotations

import re

from redclaw.models import ToolMeta, ToolCategory, RiskLevel, Finding, Severity
from redclaw.tools.base import BaseTool


class DigTool(BaseTool):
    meta = ToolMeta(
        id="dig",
        name="DNS Lookup (dig)",
        description="DNS record lookup — A, AAAA, MX, NS, TXT, SOA records for a domain.",
        category=ToolCategory.RECON,
        risk_level=RiskLevel.PASSIVE,
        binary="dig",
        default_timeout=30,
    )

    def build_args(self, target: str, **kwargs: object) -> list[str]:
        record_type = str(kwargs.get("record_type", "ANY"))
        return [target, record_type, "+noall", "+answer", "+authority"]

    def parse_output(self, raw: str) -> dict:
        records: list[dict] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = line.split()
            if len(parts) >= 5:
                records.append({
                    "name": parts[0],
                    "ttl": parts[1],
                    "class": parts[2],
                    "type": parts[3],
                    "data": " ".join(parts[4:]),
                })
        return {"records": records}

    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        findings: list[Finding] = []
        records = parsed.get("records", [])
        for rec in records:
            findings.append(Finding(
                title=f"DNS {rec['type']} record: {rec['data'][:60]}",
                severity=Severity.INFO,
                description=f"{rec['name']} {rec['ttl']}s {rec['class']} {rec['type']} {rec['data']}",
                tool_id="dig",
                target=target,
                evidence=f"{rec['type']}: {rec['data']}",
                metadata=rec,
            ))
        return findings


class WhoisTool(BaseTool):
    meta = ToolMeta(
        id="whois",
        name="WHOIS Lookup",
        description="Domain registration lookup — registrar, creation date, expiry, name servers.",
        category=ToolCategory.RECON,
        risk_level=RiskLevel.PASSIVE,
        binary="whois",
        default_timeout=30,
    )

    def build_args(self, target: str, **kwargs: object) -> list[str]:
        return [target]

    def parse_output(self, raw: str) -> dict:
        result: dict = {
            "registrar": "",
            "creation_date": "",
            "expiry_date": "",
            "name_servers": [],
            "status": [],
            "registrant": "",
            "raw_fields": {},
        }

        for line in raw.splitlines():
            line = line.strip()
            if ":" not in line or line.startswith("%") or line.startswith("#"):
                continue

            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if not value:
                continue

            result["raw_fields"][key] = value

            if "registrar" in key and not result["registrar"]:
                result["registrar"] = value
            elif "creation" in key or "created" in key:
                result["creation_date"] = value
            elif "expir" in key:
                result["expiry_date"] = value
            elif "name server" in key or "nserver" in key:
                result["name_servers"].append(value)
            elif "status" in key:
                result["status"].append(value)
            elif "registrant" in key and "name" in key:
                result["registrant"] = value

        return result

    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        findings: list[Finding] = []

        registrar = parsed.get("registrar", "Unknown")
        created = parsed.get("creation_date", "Unknown")
        expiry = parsed.get("expiry_date", "Unknown")
        ns_list = parsed.get("name_servers", [])

        summary = f"Registrar: {registrar}, Created: {created}, Expires: {expiry}"
        if ns_list:
            summary += f", NS: {', '.join(ns_list[:4])}"

        findings.append(Finding(
            title=f"WHOIS info for {target}",
            severity=Severity.INFO,
            description=summary,
            tool_id="whois",
            target=target,
            evidence=summary,
            metadata=parsed,
        ))
        return findings
