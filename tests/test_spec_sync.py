from pathlib import Path

import pytest

from mtg_decks import spec_sync


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clear_error_log():
    error_path = PROJECT_ROOT / "error.log"
    if error_path.exists():
        error_path.unlink()
    yield
    if error_path.exists():
        error_path.unlink()


def test_functional_spec_html_is_current():
    assert spec_sync.spec_is_in_sync()


def test_error_is_logged_when_files_diverge(tmp_path: Path):
    md_path = tmp_path / "spec.md"
    html_path = tmp_path / "spec.html"
    error_log = tmp_path / "error.log"

    md_path.write_text("# Heading\n\nDetails", encoding="utf-8")
    html_path.write_text("mismatch", encoding="utf-8")

    result = spec_sync.spec_is_in_sync(md_path=md_path, html_path=html_path, error_log=error_log)

    assert result is False
    assert error_log.exists()
    contents = error_log.read_text(encoding="utf-8")
    assert "out of sync" in contents
