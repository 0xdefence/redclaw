"""Raw output file persistence.

Saves raw tool output to files alongside SQLite storage for debugging
and manual inspection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from redclaw.models import get_config


def save_raw_output(
    scan_id: str,
    tool_id: str,
    raw_output: str,
    command: str,
    data_dir: Path | None = None,
) -> Path:
    """Save raw tool output to .claw/runs/<scan_id>/<tool_id>.txt

    Args:
        scan_id: The scan identifier
        tool_id: The tool that produced the output
        raw_output: The raw stdout from the tool
        command: The command that was executed
        data_dir: Optional override for data directory

    Returns:
        Path to the saved file
    """
    config = get_config()
    base_dir = data_dir or config.data_dir
    run_dir = base_dir / "runs" / scan_id
    run_dir.mkdir(parents=True, exist_ok=True)

    output_file = run_dir / f"{tool_id}.txt"
    output_file.write_text(
        f"# Tool: {tool_id}\n"
        f"# Command: {command}\n"
        f"# Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
        f"# ---\n\n"
        f"{raw_output}"
    )
    return output_file


def get_raw_output(scan_id: str, tool_id: str, data_dir: Path | None = None) -> str | None:
    """Retrieve raw output for a specific tool run.

    Args:
        scan_id: The scan identifier
        tool_id: The tool that produced the output
        data_dir: Optional override for data directory

    Returns:
        Raw output string or None if not found
    """
    config = get_config()
    base_dir = data_dir or config.data_dir
    output_file = base_dir / "runs" / scan_id / f"{tool_id}.txt"

    if output_file.exists():
        return output_file.read_text()
    return None


def list_scan_outputs(scan_id: str, data_dir: Path | None = None) -> list[tuple[str, Path]]:
    """List all raw outputs for a scan.

    Args:
        scan_id: The scan identifier
        data_dir: Optional override for data directory

    Returns:
        List of (tool_id, file_path) tuples
    """
    config = get_config()
    base_dir = data_dir or config.data_dir
    run_dir = base_dir / "runs" / scan_id

    if not run_dir.exists():
        return []

    outputs = []
    for f in run_dir.glob("*.txt"):
        tool_id = f.stem
        outputs.append((tool_id, f))

    return outputs


def list_all_runs(data_dir: Path | None = None) -> list[str]:
    """List all scan IDs with saved outputs.

    Args:
        data_dir: Optional override for data directory

    Returns:
        List of scan IDs
    """
    config = get_config()
    base_dir = data_dir or config.data_dir
    runs_dir = base_dir / "runs"

    if not runs_dir.exists():
        return []

    return [d.name for d in runs_dir.iterdir() if d.is_dir()]


def delete_run_outputs(scan_id: str, data_dir: Path | None = None) -> bool:
    """Delete all raw outputs for a scan.

    Args:
        scan_id: The scan identifier
        data_dir: Optional override for data directory

    Returns:
        True if deleted, False if not found
    """
    import shutil

    config = get_config()
    base_dir = data_dir or config.data_dir
    run_dir = base_dir / "runs" / scan_id

    if run_dir.exists():
        shutil.rmtree(run_dir)
        return True
    return False


def cleanup_old_runs(days: int = 30, data_dir: Path | None = None) -> int:
    """Clean up runs older than N days.

    Args:
        days: Delete runs older than this many days
        data_dir: Optional override for data directory

    Returns:
        Number of runs deleted
    """
    import shutil
    from datetime import timedelta

    config = get_config()
    base_dir = data_dir or config.data_dir
    runs_dir = base_dir / "runs"

    if not runs_dir.exists():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = 0

    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue

        # Check modification time of any file in the directory
        try:
            latest_mtime = max(
                f.stat().st_mtime for f in run_dir.glob("*") if f.is_file()
            )
            mtime = datetime.fromtimestamp(latest_mtime, tz=timezone.utc)

            if mtime < cutoff:
                shutil.rmtree(run_dir)
                deleted += 1
        except (ValueError, OSError):
            # Empty directory or permission error
            continue

    return deleted
