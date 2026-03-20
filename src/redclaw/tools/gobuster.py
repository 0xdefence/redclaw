"""Gobuster directory/DNS/vhost brute-forcing wrapper."""
from __future__ import annotations

import re

from redclaw.models import ToolMeta, ToolCategory, RiskLevel, Finding, Severity
from redclaw.tools.base import BaseTool


class GobusterTool(BaseTool):
    meta = ToolMeta(
        id="gobuster",
        name="Gobuster Scanner",
        description="Directory, DNS subdomain, and virtual host brute-forcing tool. Discovers hidden paths and subdomains.",
        category=ToolCategory.ENUMERATION,
        risk_level=RiskLevel.ACTIVE,
        binary="gobuster",
        default_timeout=120,
    )

    # Default wordlists (available in Kali)
    WORDLISTS = {
        "dir": "/usr/share/wordlists/dirb/common.txt",
        "dns": "/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
        "vhost": "/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
    }

    def build_args(self, target: str, **kwargs: object) -> list[str]:
        mode = str(kwargs.get("mode", "dir"))

        args = [mode]

        if mode == "dir":
            # Ensure target has protocol
            if not target.startswith(("http://", "https://")):
                target = f"http://{target}"
            args.extend(["-u", target])
        elif mode == "dns":
            args.extend(["-d", target])
        elif mode == "vhost":
            if not target.startswith(("http://", "https://")):
                target = f"http://{target}"
            args.extend(["-u", target])

        # Wordlist
        wordlist = kwargs.get("wordlist") or self.WORDLISTS.get(mode, self.WORDLISTS["dir"])
        args.extend(["-w", str(wordlist)])

        # Common options
        args.extend([
            "-q",  # Quiet mode (no banner)
            "--no-error",  # Don't show errors
            "-t", str(kwargs.get("threads", 10)),  # Threads
        ])

        # Extensions for dir mode
        if mode == "dir":
            extensions = kwargs.get("extensions", "php,html,txt,bak")
            if extensions:
                args.extend(["-x", str(extensions)])

        # Status codes to show (dir mode)
        if mode == "dir":
            status_codes = kwargs.get("status_codes", "200,204,301,302,307,401,403")
            args.extend(["-s", str(status_codes)])

        return args

    def parse_output(self, raw: str) -> dict:
        """Parse gobuster output."""
        results: list[dict] = []
        mode = "dir"  # Default

        for line in raw.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("=") or "Starting" in line or "Finished" in line:
                continue

            # Dir mode: /path (Status: 200) [Size: 1234]
            dir_match = re.match(r"(/\S+)\s+\(Status:\s*(\d+)\)(?:\s+\[Size:\s*(\d+)\])?", line)
            if dir_match:
                results.append({
                    "type": "directory",
                    "path": dir_match.group(1),
                    "status": int(dir_match.group(2)),
                    "size": int(dir_match.group(3)) if dir_match.group(3) else 0,
                })
                continue

            # DNS mode: Found: subdomain.example.com
            dns_match = re.match(r"Found:\s+(\S+)", line)
            if dns_match:
                results.append({
                    "type": "subdomain",
                    "host": dns_match.group(1),
                })
                mode = "dns"
                continue

            # VHost mode: Found: hostname (Status: 200) [Size: 1234]
            vhost_match = re.match(r"Found:\s+(\S+)\s+\(Status:\s*(\d+)\)", line)
            if vhost_match:
                results.append({
                    "type": "vhost",
                    "host": vhost_match.group(1),
                    "status": int(vhost_match.group(2)),
                })
                mode = "vhost"
                continue

            # Simple path format (some versions)
            if line.startswith("/"):
                parts = line.split()
                results.append({
                    "type": "directory",
                    "path": parts[0],
                    "status": 200,
                    "size": 0,
                })

        return {"results": results, "mode": mode, "count": len(results)}

    def extract_findings(self, parsed: dict, target: str) -> list[Finding]:
        findings: list[Finding] = []

        for item in parsed.get("results", []):
            item_type = item.get("type", "directory")

            if item_type == "directory":
                path = item.get("path", "")
                status = item.get("status", 200)
                size = item.get("size", 0)

                # Classify severity based on path/status
                severity = Severity.INFO
                if any(x in path.lower() for x in [".bak", ".old", ".backup", "admin", "config", ".env"]):
                    severity = Severity.MEDIUM
                elif status == 403:
                    severity = Severity.LOW
                elif any(x in path.lower() for x in ["upload", "shell", "cmd", "exec"]):
                    severity = Severity.HIGH

                findings.append(Finding(
                    title=f"Directory found: {path}",
                    severity=severity,
                    description=f"Gobuster discovered {path} (HTTP {status}, {size} bytes)",
                    tool_id="gobuster",
                    target=target,
                    evidence=f"{path} [Status: {status}] [Size: {size}]",
                    metadata=item,
                ))

            elif item_type == "subdomain":
                host = item.get("host", "")
                findings.append(Finding(
                    title=f"Subdomain found: {host}",
                    severity=Severity.INFO,
                    description=f"Gobuster DNS enumeration discovered subdomain: {host}",
                    tool_id="gobuster",
                    target=target,
                    evidence=host,
                    metadata=item,
                ))

            elif item_type == "vhost":
                host = item.get("host", "")
                status = item.get("status", 200)
                findings.append(Finding(
                    title=f"Virtual host found: {host}",
                    severity=Severity.LOW,
                    description=f"Gobuster discovered virtual host {host} (HTTP {status})",
                    tool_id="gobuster",
                    target=target,
                    evidence=f"{host} [Status: {status}]",
                    metadata=item,
                ))

        return findings
