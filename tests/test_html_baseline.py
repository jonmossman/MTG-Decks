from __future__ import annotations

import hashlib
from pathlib import Path

# Snapshot of the HTML that matches the latest main branch merge.
# If you intentionally change an HTML page, update the hash map below once
# the new version is merged to main.
EXPECTED_SHA256 = {
    "index.html": "5dac7105e0fc9ed5b44699d4d6ad40e80747855c9c2cf05bdeadcd4b49f9cf37",
    "upload.html": "11c1e198f686af066366fc90fdbae80e5984bb81e73f8d092fc7c172871b812b",
    "decks.html": "5f78657dd5127a6c57d994761f869de57b11d942b41104f2f3536db626aa7214",
    "inventory.html": "7ba446dadceedd2d14ea1ca6315ce22c9e3ddb29712c38c4578c188ffc0d67b0",
    "functional-spec.html": "516c018082ae3bce3f38f6e50124016cf7e6965574d9406452df1fc03f987602",
}


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_html_files_match_main_snapshot():
    mismatches = []

    for rel_path, expected_hash in EXPECTED_SHA256.items():
        path = Path(rel_path)
        if not path.exists():
            mismatches.append(f"Missing file: {rel_path}")
            continue

        actual_hash = sha256_hex(path)
        if actual_hash != expected_hash:
            mismatches.append(
                f"{rel_path} changed (expected {expected_hash}, got {actual_hash})"
            )

    if mismatches:
        formatted = "\n".join(mismatches)
        raise AssertionError(
            "HTML drift detected compared to main snapshot.\n"
            + formatted
            + "\nUpdate EXPECTED_SHA256 only after merging intentional changes to main."
        )
