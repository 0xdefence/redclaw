"""Output formatters and report generators."""
from redclaw.output.console import (
    OutputMode,
    print_scan_header,
    print_tool_progress,
    print_scan_summary,
    print_scan_list,
    print_scan_detail,
    get_output_mode,
)
from redclaw.output.report import generate_report
from redclaw.output.formatters import format_tool_output
from redclaw.output.banner import print_banner, print_banner_rich
from redclaw.output.display import DisplayComponents
from redclaw.output.stealth import StealthOutput, format_scan_stealth
from redclaw.output.json_output import JSONOutput, format_scan_json
from redclaw.output.errors import ErrorDisplay, print_error, exit_with_error

__all__ = [
    # Output modes
    "OutputMode",
    "get_output_mode",

    # Console functions (legacy API)
    "print_scan_header",
    "print_tool_progress",
    "print_scan_summary",
    "print_scan_list",
    "print_scan_detail",

    # Banner
    "print_banner",
    "print_banner_rich",

    # Display components
    "DisplayComponents",

    # Specialized outputs
    "StealthOutput",
    "format_scan_stealth",
    "JSONOutput",
    "format_scan_json",

    # Errors
    "ErrorDisplay",
    "print_error",
    "exit_with_error",

    # Legacy
    "generate_report",
    "format_tool_output",
]
