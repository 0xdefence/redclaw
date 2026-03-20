"""Nmap tool wrapper with XML output parser."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from redclaw.models import ToolMeta, ToolCategory, RiskLevel, Finding, Severity
from redclaw.tools.base import BaseTool


SCAN_PROFILES = {
    "quick": ["-sT", "-sV", "-F", "--open", "-oX", "-"],
    "full": ["-sT", "-sV", "-sC", "-p-", "--open", "-oX", "-"],
    "stealth": ["-sS", "-sV", "-T2", "--open", "-oX", "-"],
    "udp": ["-sU", "-sV", "--top-ports", "100", "-oX", "-"],
}


class NmapTool(BaseTool):
    meta = ToolMeta(
        id="nmap",
        name="Nmap Port Scanner",
        description="Network exploration and port scanning. Discovers open ports, running services, OS detection.",
        category=ToolCategory.SCANNING,
        risk_level=RiskLevel.ACTIVE,
        binary="nmap",
        default_timeout=300,
    )

    def build_args(self, target: str, **kwargs: object) -> list[str]:
        profile = str(kwargs.get("profile", "quick"))
        flags = SCAN_PROFILES.get(profile, SCAN_PROFILES["quick"])
        return flags + [target]

    def parse_output(self, raw: str) -> dict:
        """Parse nmap XML output. Falls back to text parsing if XML fails."""
        # Try XML first (preferred)
        try:
            return self._parse_xml(raw)
        except ET.ParseError:
            return self._parse_text(raw)

    def _parse_xml(self, raw: str) -> dict:
        """Parse nmap -oX output."""
        # Extract just the XML portion if mixed with text
        xml_start = raw.find("<?xml")
        if xml_start == -1:
            xml_start = raw.find("<nmaprun")
        if xml_start == -1:
            raise ET.ParseError("No XML found in output")

        root = ET.fromstring(raw[xml_start:])
        result: dict = {
            "hosts": [],
            "scan_info": {},
        }

        # Scan info
        scaninfo = root.find("scaninfo")
        if scaninfo is not None:
            result["scan_info"] = {
                "type": scaninfo.get("type", ""),
                "protocol": scaninfo.get("protocol", ""),
                "services": scaninfo.get("services", ""),
            }

        # Hosts
        for host_el in root.findall("host"):
            host: dict = {"address": "", "hostname": "", "ports": [], "os": ""}

            addr = host_el.find("address")
            if addr is not None:
                host["address"] = addr.get("addr", "")

            hostnames = host_el.find("hostnames")
            if hostnames is not None:
                hn = hostnames.find("hostname")
                if hn is not None:
                    host["hostname"] = hn.get("name", "")

            ports_el = host_el.find("ports")
            if ports_el is not None:
                for port_el in ports_el.findall("port"):
                    state = port_el.find("state")
                    service = port_el.find("service")
                    port = {
                        "port": int(port_el.get("portid", "0")),
                        "protocol": port_el.get("protocol", "tcp"),
                        "state": state.get("state", "") if state is not None else "",
                        "service": service.get("name", "") if service is not None else "",
                        "version": service.get("version", "") if service is not None else "",
                        "product": service.get("product", "") if service is not None else "",
                    }
                    host["ports"].append(port)

            os_el = host_el.find("os")
            if os_el is not None:
                osmatch = os_el.find("osmatch")
                if osmatch is not None:
                    host["os"] = osmatch.get("name", "")

            result["hosts"].append(host)

        return result

    def _parse_text(self, raw: str) -> dict:
        """Fallback: parse nmap text output."""
        ports: list[dict] = []
        for line in raw.splitlines():
            match = re.match(
                r"(\d+)/(tcp|udp)\s+(open|filtered)\s+(\S+)\s*(.*)", line
            )
            if match:
                ports.append({
                    "port": int(match.group(1)),
                    "protocol": match.group(2),
                    "state": match.group(3),
                    "service": match.group(4),
                    "version": match.group(5).strip(),
                    "product": "",
                })

        return {"hosts": [{"address": "", "hostname": "", "ports": ports, "os": ""}]}

    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        findings: list[Finding] = []
        for host in parsed.get("hosts", []):
            for port in host.get("ports", []):
                if port.get("state") != "open":
                    continue
                svc = port.get("service", "unknown")
                ver = port.get("version", "")
                product = port.get("product", "")
                desc = f"Port {port['port']}/{port['protocol']} running {svc}"
                if product:
                    desc += f" ({product}"
                    if ver:
                        desc += f" {ver}"
                    desc += ")"

                findings.append(Finding(
                    title=f"Open port {port['port']}/{port['protocol']} — {svc}",
                    severity=Severity.INFO,
                    description=desc,
                    tool_id="nmap",
                    target=target,
                    evidence=f"{port['port']}/{port['protocol']} open {svc} {product} {ver}".strip(),
                    metadata=port,
                ))
        return findings
