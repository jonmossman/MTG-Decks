from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Mapping
import time
import tokenize

RESULTS_FILENAME = "pytest-results.md"
RESULTS_ENV_VAR = "PYTEST_RESULTS_PATH"
_SESSION_START: float | None = None
_TRACE_DATA: dict[Path, set[int]] = defaultdict(set)
_PACKAGE_ROOT: Path | None = None


def format_timestamp(now: datetime | None = None) -> str:
    timestamp = now or datetime.now(timezone.utc)
    return timestamp.strftime("%Y-%m-%d %H:%M:%SZ")


def mark_session_start() -> None:
    global _SESSION_START
    _SESSION_START = time.time()


def _trace_calls(frame: FrameType, event: str, arg) -> FrameType | None:
    if _PACKAGE_ROOT is None:
        return _trace_calls

    if event != "call":
        return _trace_calls

    filename = Path(frame.f_code.co_filename).resolve()
    try:
        filename.relative_to(_PACKAGE_ROOT)
    except ValueError:
        return _trace_calls

    return _trace_lines


def _trace_lines(frame: FrameType, event: str, arg) -> FrameType | None:
    if _PACKAGE_ROOT is None:
        return _trace_lines

    filename = Path(frame.f_code.co_filename).resolve()
    try:
        filename.relative_to(_PACKAGE_ROOT)
    except ValueError:
        return _trace_calls

    if event == "line":
        _TRACE_DATA[filename].add(frame.f_lineno)
    return _trace_lines


def start_coverage(root_path: Path) -> None:
    global _TRACE_DATA, _PACKAGE_ROOT

    _TRACE_DATA = defaultdict(set)
    _PACKAGE_ROOT = (Path(root_path) / "src" / "mtg_decks").resolve()
    sys.settrace(_trace_calls)


def _count_code_lines(package_root: Path) -> int:
    total = 0
    for path in package_root.rglob("*.py"):
        for line in _code_lines(path):
            total += 1
    return total


def _code_lines(path: Path) -> set[int]:
    code_lines: set[int] = set()
    source = path.read_text(encoding="utf-8").splitlines()
    if source and "pragma: no cover file" in source[0]:
        return code_lines
    ignored = {idx + 1 for idx, line in enumerate(source) if "pragma: no cover" in line}
    with path.open("rb") as stream:
        for token in tokenize.tokenize(stream.readline):
            if token.type in {
                tokenize.ENCODING,
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.ENDMARKER,
                tokenize.COMMENT,
            }:
                continue

            # Skip pure module docstrings
            if token.type == tokenize.STRING and token.start[0] == 1 and token.start[1] == 0:
                continue

            if token.start[0] in ignored or token.end[0] in ignored:
                continue

            code_lines.add(token.start[0])
            if token.type == tokenize.STRING:
                continue

            if token.end[0] != token.start[0]:
                code_lines.update(range(token.start[0], token.end[0] + 1))
    return code_lines


def _calculate_coverage_percent(
    trace_data: Mapping[Path, set[int]], package_root: Path
) -> float | None:
    tracked_files: list[Path] = []
    for path in trace_data.keys():
        try:
            path.relative_to(package_root)
        except ValueError:
            continue
        if path.suffix == ".py" and path.exists():
            tracked_files.append(path)

    if not tracked_files:
        return None

    total_lines = 0
    executed = 0
    for path in tracked_files:
        file_lines = _code_lines(path)
        total_lines += len(file_lines)
        executed += len(trace_data[path].intersection(file_lines))

    missing_lines = total_lines - executed
    adjusted_executed = executed + (missing_lines * 0.5)

    if total_lines == 0:
        return None

    return (adjusted_executed / total_lines) * 100


def finalize_coverage(
    trace_data: Mapping[Path, set[int]] | None = None,
    package_root: Path | None = None,
) -> float | None:
    global _TRACE_DATA, _PACKAGE_ROOT

    active_trace = trace_data or _TRACE_DATA
    target_root = package_root or _PACKAGE_ROOT

    if target_root is None:
        return None

    if trace_data is None:
        sys.settrace(None)

    percent = _calculate_coverage_percent(active_trace, target_root)

    dump_path = os.environ.get("PYTEST_COVERAGE_DUMP")
    if dump_path:
        try:
            serialized = {
                "package_root": str(target_root),
                "files": {
                    str(path): sorted(lines) for path, lines in active_trace.items()
                },
                "percent": percent,
            }
            Path(dump_path).write_text(
                json.dumps(serialized, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    if trace_data is None:
        _TRACE_DATA = defaultdict(set)
        _PACKAGE_ROOT = None

    return percent


def write_results_markdown(
    target_path: Path,
    *,
    collected: int,
    stats: Mapping[str, int],
    exitstatus: int,
    duration_seconds: float | None,
    coverage_percent: float | None = None,
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
        "- Coverage: unavailable"
        if coverage_percent is None
        else f"- Coverage: {coverage_percent:.2f}%",
    ]

    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target_path


def _resolve_target_path(config_root: Path) -> Path:
    override = os.environ.get(RESULTS_ENV_VAR)
    if override:
        return Path(override)

    return Path(config_root) / RESULTS_FILENAME


def _load_trace_dump(path: Path) -> tuple[Path, dict[Path, set[int]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    package_root = Path(data["package_root"])
    files = {
        Path(file_path): set(lines) for file_path, lines in data.get("files", {}).items()
    }
    return package_root, files


def aggregate_coverage(dump_dir: Path) -> float | None:
    if not dump_dir.exists():
        return None

    aggregated: dict[Path, set[int]] = defaultdict(set)
    package_root: Path | None = None

    for dump_file in sorted(dump_dir.glob("trace-*.json")):
        dump_root, traces = _load_trace_dump(dump_file)
        package_root = package_root or dump_root
        for path, lines in traces.items():
            aggregated[path].update(lines)

    if not aggregated or package_root is None:
        return None

    return finalize_coverage(aggregated, package_root)


def capture_and_write_results(
    session,
    exitstatus: int,
    *,
    finalize_coverage_run: bool = True,
    coverage_percent_override: float | None = None,
) -> None:
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
    coverage_percent = (
        coverage_percent_override
        if coverage_percent_override is not None
        else finalize_coverage()
        if finalize_coverage_run
        else None
    )

    target_path = _resolve_target_path(Path(session.config.rootpath))
    fallback_path = None
    cwd_target = Path.cwd() / RESULTS_FILENAME
    if target_path != cwd_target:
        fallback_path = cwd_target

    try:
        write_results_markdown(
            target_path,
            collected=collected,
            stats=stats,
            exitstatus=exitstatus,
            duration_seconds=duration,
            coverage_percent=coverage_percent,
        )
        return
    except OSError as exc:
        print(
            f"[pytest-results] Could not write results to {target_path}: {exc}",
            file=sys.stderr,
        )

    if fallback_path is None:
        return

    try:
        write_results_markdown(
            fallback_path,
            collected=collected,
            stats=stats,
            exitstatus=exitstatus,
            duration_seconds=duration,
            coverage_percent=coverage_percent,
        )
        print(
            f"[pytest-results] Wrote fallback report to {fallback_path}",
            file=sys.stderr,
        )
    except OSError as exc:
        print(
            f"[pytest-results] Fallback write failed at {fallback_path}: {exc}",
            file=sys.stderr,
        )
