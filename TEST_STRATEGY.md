# Test strategy

This repository favors small, file-scoped tests that stay isolated so they can run in
parallel when `pytest-xdist` is available.

## Layout
- `tests/test_cli.py` covers end-to-end CLI flows without touching the network by
  stubbing resolvers and deck libraries.
- Library units such as `library.py`, `rules.py`, and `valuation.py` are tested in
  their dedicated modules to keep fixtures lightweight.
- Reporting helpers (`tests/_pytest_results.py`) are exercised through
  `test_pytest_results_report.py` to ensure coverage accounting stays accurate.

## Running the suite
- Default: `PYTHONPATH=src pytest -q` (writes results and coverage into
  `pytest-results.md`).
- Parallel (faster when `pytest-xdist` is installed):
  `PYTHONPATH=src pytest -q -n 2` (or `-n auto`). Coverage traces from each worker
  are merged before `pytest-results.md` is written.
- Debug coverage traces by setting `PYTEST_COVERAGE_DUMP=/tmp/trace.json` to keep
  the per-file line data.

## Speed tips
- Tests avoid network calls by design; keep new fixtures using local files or
  stubs/mocks.
- Keep CLI and importer fixtures using temporary directories to avoid lockstep
  file contention in parallel runs.
- When adding long-running checks, prefer smaller parametrized cases so workers
  can balance the load evenly.
