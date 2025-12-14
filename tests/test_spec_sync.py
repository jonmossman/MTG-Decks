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


def test_missing_markdown_is_reported_gracefully(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    md_path = tmp_path / "missing.md"
    html_path = tmp_path / "spec.html"

    exit_code = spec_sync.main(["--rewrite-md", "--write", "--md", str(md_path), "--html", str(html_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing.md" in captured.err
    assert "Provide --md" in captured.err


def test_local_fallback_is_used_when_packaged_defaults_are_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    markdown = tmp_path / "FUNCTIONAL_SPEC.md"
    markdown.write_text("# Heading\n\nDetails", encoding="utf-8")

    # Simulate running the module when the packaged defaults are unavailable by pointing to fake paths.
    fake_md = Path("/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/FUNCTIONAL_SPEC.md")
    fake_html = Path("/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/functional-spec.html")

    monkeypatch.chdir(tmp_path)

    exit_code = spec_sync.main(["--rewrite-md", "--write", "--md", str(fake_md), "--html", str(fake_html)])

    assert exit_code == 0
    generated_html = tmp_path / "functional-spec.html"
    assert generated_html.exists()
    contents = generated_html.read_text(encoding="utf-8")
    assert "Functional Specification" in contents
