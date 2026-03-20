"""Scan planner — orchestrates tool execution for a scan session."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from redclaw.models import Scan, ScanStatus, Finding, Severity, ToolResult
from redclaw.core.executor import DockerExecutor
from redclaw.core.policy import SecurityPolicy
from redclaw.core.profiles import get_profile, ScanProfile
from redclaw.tools import ToolRegistry, create_default_registry, BaseTool
from redclaw.storage import Database


class ScanPlanner:
    """Orchestrates a complete scan session."""

    def __init__(
        self,
        executor: DockerExecutor | None = None,
        registry: ToolRegistry | None = None,
        policy: SecurityPolicy | None = None,
        db: Database | None = None,
    ) -> None:
        self.executor = executor or DockerExecutor()
        self.registry = registry or create_default_registry()
        self.policy = policy or SecurityPolicy()
        self.db = db or Database()

    def run_scan(
        self,
        target: str,
        profile_name: str = "quick",
        tools: list[str] | None = None,
        on_tool_start: Callable[[str, str], None] | None = None,
        on_tool_done: Callable[[str, ToolResult], None] | None = None,
    ) -> Scan:
        """Execute a complete scan.

        Args:
            target: Target to scan
            profile_name: Scan profile name (quick, recon, full, web, stealth)
            tools: Override profile with explicit tool list
            on_tool_start: Callback(tool_id, target) when a tool starts
            on_tool_done: Callback(tool_id, result) when a tool finishes

        Returns:
            Completed Scan with findings
        """
        # 1. Validate target
        policy_check = self.policy.validate_target(target)
        if not policy_check.allowed:
            scan = Scan(target=target, profile=profile_name, status=ScanStatus.FAILED, error=policy_check.reason)
            self.db.save_scan(scan)
            return scan

        # 2. Determine tools
        if tools:
            tool_ids = tools
            tool_kwargs: dict[str, dict] = {}
        else:
            profile = get_profile(profile_name)
            tool_ids = profile.tools
            tool_kwargs = profile.tool_kwargs

        # 3. Validate all tools exist
        for tid in tool_ids:
            if self.registry.get(tid) is None:
                scan = Scan(target=target, profile=profile_name, status=ScanStatus.FAILED, error=f"Unknown tool: {tid}")
                self.db.save_scan(scan)
                return scan

        # 4. Create scan record
        scan = Scan(target=target, profile=profile_name, status=ScanStatus.RUNNING, tools_used=tool_ids)
        self.db.save_scan(scan)
        self.db.log_event("scan_started", target=target, details={"profile": profile_name, "tools": tool_ids})

        # 5. Execute tools sequentially
        all_findings: list[Finding] = []

        for tool_id in tool_ids:
            tool = self.registry.get_or_raise(tool_id)
            kwargs = tool_kwargs.get(tool_id, {})

            # Validate args
            args = tool.build_args(target, **kwargs)
            args_check = self.policy.validate_args(tool_id, args)
            if not args_check.allowed:
                self.db.log_event("tool_blocked", tool_id=tool_id, target=target, details={"reason": args_check.reason})
                continue

            if on_tool_start:
                on_tool_start(tool_id, target)

            # Execute
            try:
                result = tool.execute(self.executor, target, **kwargs)
            except Exception as exc:
                result = ToolResult(
                    tool_id=tool_id,
                    target=target,
                    command=f"{tool.meta.binary} {' '.join(args)}",
                    raw_output="",
                    status="error",
                    error=str(exc),
                )

            # Store result
            self.db.save_tool_result(scan.id, {
                "tool_id": result.tool_id,
                "target": result.target,
                "command": result.command,
                "raw_output": result.raw_output,
                "parsed": result.parsed,
                "status": result.status,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "error": result.error,
            })

            # Collect findings
            for f_dict in result.findings:
                finding = Finding(**f_dict) if isinstance(f_dict, dict) else f_dict
                all_findings.append(finding)

            self.db.log_event(
                "tool_executed",
                tool_id=tool_id,
                target=target,
                details={
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "findings": len(result.findings),
                },
            )

            scan.results.append({
                "tool_id": result.tool_id,
                "status": result.status,
                "duration_ms": result.duration_ms,
                "findings_count": len(result.findings),
            })

            if on_tool_done:
                on_tool_done(tool_id, result)

        # 6. Finalise scan
        scan.findings = all_findings
        scan.status = ScanStatus.COMPLETED
        scan.finished_at = datetime.now(timezone.utc)
        scan.duration_ms = int((scan.finished_at - scan.started_at).total_seconds() * 1000)

        # Save findings to DB
        self.db.save_findings(scan.id, all_findings)
        self.db.save_scan(scan)

        self.db.log_event(
            "scan_completed",
            target=target,
            details={
                "scan_id": scan.id,
                "duration_ms": scan.duration_ms,
                "findings": len(all_findings),
                "finding_counts": scan.finding_counts,
            },
        )

        return scan

    def run_single_tool(self, target: str, tool_id: str, **kwargs: object) -> ToolResult:
        """Run a single tool (no scan session overhead).

        Used for individual commands like `claw portscan` or `claw recon`.
        """
        # Validate target
        check = self.policy.validate_target(target)
        if not check.allowed:
            return ToolResult(
                tool_id=tool_id,
                target=target,
                command="",
                raw_output="",
                status="blocked",
                error=check.reason,
            )

        tool = self.registry.get_or_raise(tool_id)
        return tool.execute(self.executor, target, **kwargs)
