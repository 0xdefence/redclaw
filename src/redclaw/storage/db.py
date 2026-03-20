"""SQLite storage for scans, findings, and audit logs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import sqlite_utils

from redclaw.models import Scan, ScanStatus, Finding, Severity, get_config


class Database:
    """SQLite storage backend."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_config().db_path
        assert self.db_path is not None
        self._db: sqlite_utils.Database | None = None

    @property
    def db(self) -> sqlite_utils.Database:
        if self._db is None:
            self._db = sqlite_utils.Database(str(self.db_path))
            self._ensure_schema()
        return self._db

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        db = self._db
        assert db is not None

        if "scans" not in db.table_names():
            db["scans"].create(
                {
                    "id": str,
                    "target": str,
                    "profile": str,
                    "status": str,
                    "tools_used": str,  # JSON array
                    "started_at": str,
                    "finished_at": str,
                    "duration_ms": int,
                    "error": str,
                },
                pk="id",
            )
            db["scans"].create_index(["target"])
            db["scans"].create_index(["status"])
            db["scans"].create_index(["started_at"])

        if "findings" not in db.table_names():
            db["findings"].create(
                {
                    "id": int,
                    "scan_id": str,
                    "title": str,
                    "severity": str,
                    "description": str,
                    "tool_id": str,
                    "target": str,
                    "evidence": str,
                    "remediation": str,
                    "references": str,  # JSON array
                    "metadata": str,    # JSON object
                },
                pk="id",
                foreign_keys=[("scan_id", "scans")],
            )
            db["findings"].create_index(["scan_id"])
            db["findings"].create_index(["severity"])
            db["findings"].create_index(["tool_id"])

        if "tool_results" not in db.table_names():
            db["tool_results"].create(
                {
                    "id": int,
                    "scan_id": str,
                    "tool_id": str,
                    "target": str,
                    "command": str,
                    "raw_output": str,
                    "parsed": str,      # JSON
                    "status": str,
                    "exit_code": int,
                    "duration_ms": int,
                    "error": str,
                },
                pk="id",
                foreign_keys=[("scan_id", "scans")],
            )

        if "audit_log" not in db.table_names():
            db["audit_log"].create(
                {
                    "id": int,
                    "timestamp": str,
                    "event": str,
                    "tool_id": str,
                    "target": str,
                    "details": str,   # JSON
                },
                pk="id",
            )
            db["audit_log"].create_index(["timestamp"])
            db["audit_log"].create_index(["event"])

    # ── Scan CRUD ─────────────────────────────────────────────────

    def save_scan(self, scan: Scan) -> None:
        """Insert or update a scan record."""
        self.db["scans"].upsert(
            {
                "id": scan.id,
                "target": scan.target,
                "profile": scan.profile,
                "status": scan.status.value,
                "tools_used": json.dumps(scan.tools_used),
                "started_at": scan.started_at.isoformat(),
                "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
                "duration_ms": scan.duration_ms,
                "error": scan.error,
            },
            pk="id",
        )

    def get_scan(self, scan_id: str) -> Scan | None:
        """Get a scan by ID."""
        try:
            row = self.db["scans"].get(scan_id)
        except sqlite_utils.db.NotFoundError:
            return None

        scan = Scan(
            id=row["id"],
            target=row["target"],
            profile=row["profile"],
            status=ScanStatus(row["status"]),
            tools_used=json.loads(row["tools_used"]) if row["tools_used"] else [],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            duration_ms=row["duration_ms"],
            error=row["error"],
        )

        # Load findings
        scan.findings = self.get_findings(scan_id)
        return scan

    def list_scans(self, limit: int = 20, target: str | None = None) -> list[Scan]:
        """List recent scans, optionally filtered by target."""
        where_clauses = []
        params: list[object] = []

        if target:
            where_clauses.append("target = ?")
            params.append(target)

        where = " AND ".join(where_clauses) if where_clauses else None

        rows = self.db["scans"].rows_where(
            where, params, order_by="-started_at", limit=limit
        )

        scans: list[Scan] = []
        for row in rows:
            scans.append(Scan(
                id=row["id"],
                target=row["target"],
                profile=row["profile"],
                status=ScanStatus(row["status"]),
                tools_used=json.loads(row["tools_used"]) if row["tools_used"] else [],
                started_at=datetime.fromisoformat(row["started_at"]),
                finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
                duration_ms=row["duration_ms"],
                error=row["error"],
            ))
        return scans

    # ── Findings ──────────────────────────────────────────────────

    def save_finding(self, scan_id: str, finding: Finding) -> None:
        """Save a finding linked to a scan."""
        self.db["findings"].insert(
            {
                "scan_id": scan_id,
                "title": finding.title,
                "severity": finding.severity.value,
                "description": finding.description,
                "tool_id": finding.tool_id,
                "target": finding.target,
                "evidence": finding.evidence,
                "remediation": finding.remediation,
                "references": json.dumps(finding.references),
                "metadata": json.dumps(finding.metadata),
            }
        )

    def save_findings(self, scan_id: str, findings: list[Finding]) -> None:
        """Save multiple findings."""
        for f in findings:
            self.save_finding(scan_id, f)

    def get_findings(self, scan_id: str) -> list[Finding]:
        """Get all findings for a scan."""
        rows = self.db["findings"].rows_where("scan_id = ?", [scan_id])
        findings: list[Finding] = []
        for row in rows:
            findings.append(Finding(
                title=row["title"],
                severity=Severity(row["severity"]),
                description=row["description"],
                tool_id=row["tool_id"],
                target=row["target"],
                evidence=row.get("evidence", ""),
                remediation=row.get("remediation", ""),
                references=json.loads(row["references"]) if row.get("references") else [],
                metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
            ))
        return findings

    # ── Tool Results ──────────────────────────────────────────────

    def save_tool_result(self, scan_id: str, result: dict) -> None:
        """Save a raw tool result."""
        self.db["tool_results"].insert(
            {
                "scan_id": scan_id,
                "tool_id": result.get("tool_id", ""),
                "target": result.get("target", ""),
                "command": result.get("command", ""),
                "raw_output": result.get("raw_output", "")[:50000],  # Limit stored output
                "parsed": json.dumps(result.get("parsed", {})),
                "status": result.get("status", ""),
                "exit_code": result.get("exit_code", 0),
                "duration_ms": result.get("duration_ms", 0),
                "error": result.get("error"),
            }
        )

    # ── Audit Log ─────────────────────────────────────────────────

    def log_event(self, event: str, tool_id: str = "", target: str = "", details: dict | None = None) -> None:
        """Write an audit log entry."""
        self.db["audit_log"].insert(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "tool_id": tool_id,
                "target": target,
                "details": json.dumps(details or {}),
            }
        )

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """Get recent audit log entries."""
        return list(self.db["audit_log"].rows_where(order_by="-timestamp", limit=limit))
