from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import time
from pathlib import Path
import json

from tests import _pytest_results


def test_write_results_markdown_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "pytest-results.md"
    stats = {"passed": 3, "failed": 1, "skipped": 0, "error": 0, "xfailed": 0, "xpassed": 0}

    _pytest_results.write_results_markdown(
        target,
        collected=4,
        stats=stats,
        exitstatus=1,
        duration_seconds=0.5,
        coverage_percent=80.123,
    )
    first = target.read_text(encoding="utf-8")

    stats["failed"] = 0
    stats["passed"] = 4
    _pytest_results.write_results_markdown(
        target,
        collected=4,
        stats=stats,
        exitstatus=0,
        duration_seconds=0.25,
        coverage_percent=None,
    )
    second = target.read_text(encoding="utf-8")

    assert "Exit status: 1" in first
    assert "Failed: 1" in first
    assert "Coverage: 80.12%" in first
    assert "Exit status: 0" in second
    assert "Failed: 0" in second
    assert "Passed: 4" in second
    assert "Coverage: unavailable" in second


def test_format_timestamp_uses_provided_datetime() -> None:
    fixed = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert _pytest_results.format_timestamp(fixed) == "2024-01-02 03:04:05Z"


def test_session_duration_uses_recorded_start(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "pytest-results.md"
    original_start = _pytest_results._SESSION_START
    monkeypatch.setattr(
        _pytest_results,
        "_SESSION_START",
        (_pytest_results._SESSION_START or time.time()) - 1.5,
    )

    _pytest_results.write_results_markdown(
        target,
        collected=1,
        stats={},
        exitstatus=0,
        duration_seconds=time.time() - _pytest_results._SESSION_START,
        coverage_percent=None,
    )

    content = target.read_text(encoding="utf-8")
    assert "Duration:" in content

    _pytest_results._SESSION_START = original_start


def test_capture_and_write_results_reports_write_failures(monkeypatch, tmp_path, capsys) -> None:
    class DummyReporter:
        def __init__(self) -> None:
            self.stats = {"passed": [object()], "failed": [], "error": [], "skipped": [], "xfailed": [], "xpassed": []}
            self._numcollected = 1

    class DummyPluginManager:
        def __init__(self, reporter) -> None:
            self._reporter = reporter

        def get_plugin(self, name: str):
            return self._reporter if name == "terminalreporter" else None

    class DummyConfig:
        def __init__(self, root: Path, reporter) -> None:
            self.rootpath = root
            self.pluginmanager = DummyPluginManager(reporter)

    class DummySession:
        def __init__(self, root: Path, reporter) -> None:
            self.config = DummyConfig(root, reporter)

    reporter = DummyReporter()
    session = DummySession(tmp_path, reporter)

    unwritable_target = tmp_path / "nope" / "pytest-results.md"
    monkeypatch.setenv(_pytest_results.RESULTS_ENV_VAR, str(unwritable_target))
    monkeypatch.chdir(tmp_path)

    real_write = _pytest_results.write_results_markdown

    def flakey_write(target_path: Path, **kwargs):
        if target_path == unwritable_target:
            raise PermissionError("read-only volume")
        return real_write(target_path, **kwargs)

    monkeypatch.setattr(_pytest_results, "write_results_markdown", flakey_write)

    _pytest_results.capture_and_write_results(
        session, exitstatus=0, finalize_coverage_run=False
    )

    stderr = capsys.readouterr().err
    assert "Could not write results" in stderr
    assert "Wrote fallback report" in stderr

    fallback = tmp_path / _pytest_results.RESULTS_FILENAME
    assert fallback.exists()


def test_capture_and_write_results_uses_override(monkeypatch, tmp_path) -> None:
    class DummyReporter:
        def __init__(self) -> None:
            self.stats = {"passed": [object()], "failed": [], "error": [], "skipped": [], "xfailed": [], "xpassed": []}
            self._numcollected = 1

    class DummyPluginManager:
        def __init__(self, reporter) -> None:
            self._reporter = reporter

        def get_plugin(self, name: str):
            return self._reporter if name == "terminalreporter" else None

    class DummyConfig:
        def __init__(self, root: Path, reporter) -> None:
            self.rootpath = root
            self.pluginmanager = DummyPluginManager(reporter)

    class DummySession:
        def __init__(self, root: Path, reporter) -> None:
            self.config = DummyConfig(root, reporter)

    reporter = DummyReporter()
    session = DummySession(tmp_path, reporter)

    monkeypatch.setenv(_pytest_results.RESULTS_ENV_VAR, str(tmp_path / "pytest-results.md"))

    _pytest_results.capture_and_write_results(
        session, exitstatus=0, finalize_coverage_run=False, coverage_percent_override=42.0
    )

    content = (tmp_path / "pytest-results.md").read_text(encoding="utf-8")
    assert "Coverage: 42.00%" in content


def test_finalize_coverage_reports_percentage(tmp_path: Path) -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "mtg_decks"
    sample_file = package_root / "site_checks.py"

    sample_lines = _pytest_results._code_lines(sample_file)
    trace_data = {sample_file: {min(sample_lines)}}

    percent = _pytest_results.finalize_coverage(trace_data, package_root)

    assert percent is not None
    assert percent > 0


def test_aggregate_coverage_combines_worker_traces(tmp_path: Path) -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "mtg_decks"
    sample_file = package_root / "site_checks.py"
    traces = [
        {min(_pytest_results._code_lines(sample_file))},
        {max(_pytest_results._code_lines(sample_file))},
    ]

    for idx, lines in enumerate(traces, start=1):
        dump = {
            "package_root": str(package_root),
            "files": {str(sample_file): sorted(lines)},
            "percent": None,
        }
        (tmp_path / f"trace-w{idx}.json").write_text(
            json.dumps(dump, indent=2), encoding="utf-8"
        )

    percent = _pytest_results.aggregate_coverage(tmp_path)

    assert percent is not None
    assert percent > 0


def test_trace_functions_ignore_non_package_frames(tmp_path: Path) -> None:
    class DummyCode:
        def __init__(self, filename: Path) -> None:
            self.co_filename = str(filename)

    class DummyFrame:
        def __init__(self, filename: Path, lineno: int) -> None:
            self.f_code = DummyCode(filename)
            self.f_lineno = lineno

    original_root = _pytest_results._PACKAGE_ROOT
    original_data = _pytest_results._TRACE_DATA
    try:
        package_root = Path(__file__).resolve().parents[1] / "src" / "mtg_decks"
        _pytest_results._PACKAGE_ROOT = package_root
        _pytest_results._TRACE_DATA = defaultdict(set)

        outside = DummyFrame(tmp_path / "outside.py", lineno=5)
        handler = _pytest_results._trace_calls(outside, "call", None)
        assert handler is _pytest_results._trace_calls

        inside = DummyFrame(package_root / "inside.py", lineno=12)
        handler = _pytest_results._trace_calls(inside, "call", None)
        assert handler is _pytest_results._trace_lines

        _pytest_results._trace_lines(inside, "line", None)
        recorded = _pytest_results._TRACE_DATA[Path(inside.f_code.co_filename).resolve()]
        assert inside.f_lineno in recorded
    finally:
        _pytest_results._PACKAGE_ROOT = original_root
        _pytest_results._TRACE_DATA = original_data
