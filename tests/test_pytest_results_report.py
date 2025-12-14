from __future__ import annotations

from datetime import datetime, timezone
import time
from pathlib import Path

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
    )
    second = target.read_text(encoding="utf-8")

    assert "Exit status: 1" in first
    assert "Failed: 1" in first
    assert "Exit status: 0" in second
    assert "Failed: 0" in second
    assert "Passed: 4" in second


def test_format_timestamp_uses_provided_datetime() -> None:
    fixed = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert _pytest_results.format_timestamp(fixed) == "2024-01-02 03:04:05Z"


def test_session_duration_uses_recorded_start(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "pytest-results.md"
    _pytest_results.mark_session_start()
    monkeypatch.setattr(_pytest_results, "_SESSION_START", _pytest_results._SESSION_START - 1.5)

    _pytest_results.write_results_markdown(
        target,
        collected=1,
        stats={},
        exitstatus=0,
        duration_seconds=time.time() - _pytest_results._SESSION_START,
    )

    content = target.read_text(encoding="utf-8")
    assert "Duration:" in content


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

    _pytest_results.capture_and_write_results(session, exitstatus=0)

    stderr = capsys.readouterr().err
    assert "Could not write results" in stderr
    assert "Wrote fallback report" in stderr

    fallback = tmp_path / _pytest_results.RESULTS_FILENAME
    assert fallback.exists()
