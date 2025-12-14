from __future__ import annotations

import os
import shutil
from pathlib import Path

try:  # pragma: no cover - optional dependency
    import xdist  # type: ignore

    HAS_XDIST = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_XDIST = False

from tests._pytest_results import (
    aggregate_coverage,
    capture_and_write_results,
    finalize_coverage,
    mark_session_start,
    start_coverage,
)


def pytest_configure(config) -> None:  # pragma: no cover - exercised in test suite
    if hasattr(config, "workerinput"):
        dump_target = config.workerinput.get("coverage_dump")
        if dump_target:
            os.environ["PYTEST_COVERAGE_DUMP"] = dump_target
        return

    num_processes = getattr(config.option, "numprocesses", 0)
    if HAS_XDIST and config.pluginmanager.hasplugin("xdist") and num_processes not in (0, "no", None):
        dump_dir = Path(config.rootpath) / ".pytest_cache" / "coverage-traces"
        shutil.rmtree(dump_dir, ignore_errors=True)
        dump_dir.mkdir(parents=True, exist_ok=True)
        config._coverage_dump_dir = dump_dir


if HAS_XDIST:
    def pytest_configure_node(node):  # pragma: no cover - exercised in test suite
        dump_dir = getattr(node.config, "_coverage_dump_dir", None)
        if dump_dir is None:
            dump_dir = Path(node.config.rootpath) / ".pytest_cache" / "coverage-traces"
            dump_dir.mkdir(parents=True, exist_ok=True)

        dump_path = dump_dir / f"trace-{node.workerid}.json"
        node.workerinput["coverage_dump"] = str(dump_path)


def pytest_sessionstart(session) -> None:  # pragma: no cover - exercised in test suite
    if hasattr(session.config, "workerinput"):
        mark_session_start()
        start_coverage(Path(session.config.rootpath))
        return

    num_processes = getattr(session.config.option, "numprocesses", 0)
    if HAS_XDIST and session.config.pluginmanager.hasplugin("xdist") and num_processes not in (0, "no", None):
        return

    mark_session_start()
    start_coverage(Path(session.config.rootpath))


def pytest_sessionfinish(session, exitstatus: int) -> None:  # pragma: no cover - exercised in test suite
    if hasattr(session.config, "workerinput"):
        finalize_coverage()
        return

    num_processes = getattr(session.config.option, "numprocesses", 0)
    if HAS_XDIST and session.config.pluginmanager.hasplugin("xdist") and num_processes not in (0, "no", None):
        dump_dir = getattr(session.config, "_coverage_dump_dir", None)
        coverage_percent = aggregate_coverage(dump_dir) if dump_dir else None
        capture_and_write_results(
            session,
            exitstatus,
            finalize_coverage_run=False,
            coverage_percent_override=coverage_percent,
        )
        return

    capture_and_write_results(session, exitstatus)
