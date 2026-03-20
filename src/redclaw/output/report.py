"""Report generators — markdown and JSON."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from redclaw.models import Scan


def generate_report(scan: Scan, fmt: str = "markdown") -> str:
    """Generate a report in the specified format."""
    if fmt == "json":
        return _generate_json(scan)
    return _generate_markdown(scan)


def _generate_markdown(scan: Scan) -> str:
    """Generate a markdown report."""
    lines: list[str] = []
    lines.append(f"# Security Scan Report — {scan.target}")
    lines.append("")
    lines.append(f"**Scan ID:** {scan.id}")
    lines.append(f"**Target:** {scan.target}")
    lines.append(f"**Profile:** {scan.profile}")
    lines.append(f"**Status:** {scan.status.value}")
    lines.append(f"**Tools:** {', '.join(scan.tools_used)}")
    lines.append(f"**Duration:** {scan.duration_ms}ms")
    lines.append(f"**Started:** {scan.started_at.isoformat()}")
    if scan.finished_at:
        lines.append(f"**Finished:** {scan.finished_at.isoformat()}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    # Summary
    counts = scan.finding_counts
    lines.append("## Summary")
    lines.append("")
    lines.append(f"Total findings: **{len(scan.findings)}**")
    lines.append("")
    if counts:
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in ["critical", "high", "medium", "low", "info"]:
            if counts.get(sev, 0) > 0:
                lines.append(f"| {sev.upper()} | {counts[sev]} |")
        lines.append("")

    # Findings by severity
    if scan.findings:
        lines.append("## Findings")
        lines.append("")

        for sev in ["critical", "high", "medium", "low", "info"]:
            sev_findings = [f for f in scan.findings if f.severity.value == sev]
            if not sev_findings:
                continue
            lines.append(f"### {sev.upper()} ({len(sev_findings)})")
            lines.append("")
            for f in sev_findings:
                lines.append(f"**{f.title}**")
                lines.append(f"- Tool: {f.tool_id}")
                lines.append(f"- Description: {f.description}")
                if f.evidence:
                    lines.append(f"- Evidence: `{f.evidence}`")
                if f.remediation:
                    lines.append(f"- Remediation: {f.remediation}")
                if f.references:
                    lines.append(f"- References: {', '.join(f.references)}")
                lines.append("")

    return "\n".join(lines)


def _generate_json(scan: Scan) -> str:
    """Generate a JSON report."""
    data = {
        "scan_id": scan.id,
        "target": scan.target,
        "profile": scan.profile,
        "status": scan.status.value,
        "tools_used": scan.tools_used,
        "duration_ms": scan.duration_ms,
        "started_at": scan.started_at.isoformat(),
        "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
        "finding_counts": scan.finding_counts,
        "findings": [
            {
                "title": f.title,
                "severity": f.severity.value,
                "description": f.description,
                "tool_id": f.tool_id,
                "target": f.target,
                "evidence": f.evidence,
                "remediation": f.remediation,
                "references": f.references,
            }
            for f in scan.findings
        ],
    }
    return json.dumps(data, indent=2)
