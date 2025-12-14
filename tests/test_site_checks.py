from pathlib import Path

import mtg_decks.site_checks as site_checks

from mtg_decks.site_checks import REQUIRED_SITE_FILES, validate_site_assets


def test_site_assets_are_present_by_default(tmp_path: Path):
    site_root = Path(__file__).resolve().parents[1] / "site"

    assert validate_site_assets(site_root=site_root, log_path=tmp_path / "error.log")


def test_missing_asset_is_logged(tmp_path: Path):
    site_root = tmp_path / "site"
    site_root.mkdir()

    for rel_path in REQUIRED_SITE_FILES:
        if rel_path == "upload.html":
            continue
        target = site_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok", encoding="utf-8")

    log_path = tmp_path / "error.log"
    result = validate_site_assets(site_root=site_root, log_path=log_path)

    assert result is False
    contents = log_path.read_text(encoding="utf-8")
    assert "upload.html" in contents
    assert "Missing site asset" in contents


def test_missing_site_root_is_logged(tmp_path: Path):
    site_root = tmp_path / "site"
    log_path = tmp_path / "error.log"

    result = validate_site_assets(site_root=site_root, log_path=log_path)

    assert result is False
    contents = log_path.read_text(encoding="utf-8")
    assert "Site root does not exist" in contents
    assert str(site_root) in contents


def test_validate_prefers_existing_cwd(monkeypatch, tmp_path: Path):
    site_root = tmp_path / "site"
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MTG_DECKS_SITE_ROOT", raising=False)
    monkeypatch.setattr(site_checks, "SITE_ROOT", tmp_path / "missing" / "site")

    for rel_path in site_checks.REQUIRED_SITE_FILES:
        target = site_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok", encoding="utf-8")

    log_path = tmp_path / "error.log"
    assert site_checks.validate_site_assets(log_path=log_path)
    contents = log_path.read_text(encoding="utf-8")
    assert str(site_root) in contents
