from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import scripts.refresh_html_hashes as refresh


def _reset_imports():
    sys.modules.pop("tests", None)
    sys.modules.pop("tests.test_html_baseline", None)


def _write_fake_baseline(root: Path, mapping: dict[str, str]) -> None:
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    baseline = tests_dir / "test_html_baseline.py"
    mapping_lines = ["EXPECTED_SHA256 = {"]
    for rel_path, digest in mapping.items():
        mapping_lines.append(f'    "{rel_path}": "{digest}",')
    mapping_lines.append("}")
    baseline.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import hashlib",
                "",
                "def sha256_hex(path: Path) -> str:",
                "    return hashlib.sha256(path.read_bytes()).hexdigest()",
                "",
                *mapping_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_gather_hashes_reports_missing_and_uses_sha(tmp_path, monkeypatch):
    index = tmp_path / "index.html"
    inventory = tmp_path / "inventory.html"
    index.write_text("<html>index</html>\n", encoding="utf-8")
    inventory.write_text("<html>inventory</html>\n", encoding="utf-8")

    mapping = {
        "index.html": hashlib.sha256(index.read_bytes()).hexdigest(),
        "inventory.html": hashlib.sha256(inventory.read_bytes()).hexdigest(),
        "missing.html": "placeholder",
    }
    _write_fake_baseline(tmp_path, mapping)
    _reset_imports()
    monkeypatch.setattr(refresh, "ROOT", tmp_path)

    baseline_module = refresh._load_baseline_module()
    hashes, missing = refresh._gather_hashes(baseline_module.EXPECTED_SHA256)

    assert hashes == {
        "index.html": hashlib.sha256(index.read_bytes()).hexdigest(),
        "inventory.html": hashlib.sha256(inventory.read_bytes()).hexdigest(),
    }
    assert missing == ["missing.html"]


def test_rewrite_test_file_replaces_mapping_block(tmp_path, monkeypatch):
    original_mapping = {"index.html": "old", "inventory.html": "old"}
    _write_fake_baseline(tmp_path, original_mapping)
    _reset_imports()
    monkeypatch.setattr(refresh, "ROOT", tmp_path)

    new_mapping = {"index.html": "newhash", "inventory.html": "newhash", "extra.html": "added"}
    refresh._rewrite_test_file(new_mapping)

    updated = (tmp_path / "tests" / "test_html_baseline.py").read_text(encoding="utf-8")
    assert "\"extra.html\": \"added\"" in updated
    assert "\"inventory.html\": \"old\"" not in updated
    assert updated.strip().endswith("}")
