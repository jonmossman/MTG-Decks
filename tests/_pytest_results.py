from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
import time

RESULTS_FILENAME = "pytest-results.md"
_SESSION_START: float | None = None


def format_timestamp(now: datetime | None = None) -> str:
    timestamp = now or datetime.now(timezone.utc)
    return timestamp.strftime("%Y-%m-%d %H:%M:%SZ")


def mark_session_start() -> None:
    global _SESSION_START
    _SESSION_START = time.time()


def write_results_markdown(
    target_path: Path,
    *,
    collected: int,
    stats: Mapping[str, int],
    exitstatus: int,
    duration_seconds: float | None,
) -> Path:
    lines = [
        "# Pytest results",
        "",
        "<!-- Auto-generated: overwritten on every pytest run -->",
        f"- Run at: {format_timestamp()}",
        f"- Exit status: {exitstatus}",
        f"- Duration: {duration_seconds:.2f}s" if duration_seconds is not None else "- Duration: unknown",
        f"- Collected: {collected}",
        f"- Passed: {stats.get('passed', 0)}",
        f"- Failed: {stats.get('failed', 0)}",
        f"- Errors: {stats.get('error', 0)}",
        f"- Skipped: {stats.get('skipped', 0)}",
        f"- XFailed: {stats.get('xfailed', 0)}",
        f"- XPassed: {stats.get('xpassed', 0)}",
    ]

    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target_path


def capture_and_write_results(session, exitstatus: int) -> None:
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return

    stats = {key: len(reporter.stats.get(key, [])) for key in (
        "passed",
        "failed",
        "error",
        "skipped",
        "xfailed",
        "xpassed",
    )}
    collected = getattr(reporter, "_numcollected", 0)

    duration = time.time() - _SESSION_START if _SESSION_START is not None else None

    target_path = Path(session.config.rootpath) / RESULTS_FILENAME
    write_results_markdown(
        target_path,
        collected=collected,
        stats=stats,
        exitstatus=exitstatus,
        duration_seconds=duration,
    )
