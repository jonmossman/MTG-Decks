from __future__ import annotations

from tests._pytest_results import capture_and_write_results, mark_session_start


def pytest_sessionstart(session) -> None:  # pragma: no cover - exercised in test suite
    mark_session_start()


def pytest_sessionfinish(session, exitstatus: int) -> None:  # pragma: no cover - exercised in test suite
    capture_and_write_results(session, exitstatus)
