from __future__ import annotations

import argparse
import sys
from importlib import import_module
from pathlib import Path
from textwrap import dedent
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]


def _load_baseline_module():
    sys.path.insert(0, str(ROOT))
    try:
        return import_module("tests.test_html_baseline")
    finally:
        sys.path.pop(0)


def _gather_hashes(expected: Dict[str, str]):
    baseline = _load_baseline_module()
    hashes: dict[str, str] = {}
    missing: list[str] = []

    for rel_path in expected:
        path = ROOT / rel_path
        if not path.exists():
            missing.append(rel_path)
            continue
        hashes[rel_path] = baseline.sha256_hex(path)

    return hashes, missing


def _format_mapping(mapping: dict[str, str]) -> list[str]:
    lines = ["EXPECTED_SHA256 = {"]
    for rel_path, digest in mapping.items():
        lines.append(f'    "{rel_path}": "{digest}",')
    lines.append("}")
    return lines


def _rewrite_test_file(mapping: dict[str, str]) -> None:
    baseline_path = ROOT / "tests" / "test_html_baseline.py"
    lines = baseline_path.read_text(encoding="utf-8").splitlines()

    start = None
    end = None
    for idx, line in enumerate(lines):
        if line.startswith("EXPECTED_SHA256 = {"):
            start = idx
            break
    if start is None:
        raise RuntimeError("Could not locate EXPECTED_SHA256 declaration in test_html_baseline.py")

    brace_depth = 0
    for idx in range(start, len(lines)):
        brace_depth += lines[idx].count("{")
        brace_depth -= lines[idx].count("}")
        if brace_depth == 0:
            end = idx
            break
    if end is None:
        raise RuntimeError("Could not find end of EXPECTED_SHA256 mapping in test_html_baseline.py")

    new_block = _format_mapping(mapping)
    updated = lines[:start] + new_block + lines[end + 1 :]
    baseline_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the HTML snapshot hashes used by the pytest baseline check.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent(
            """
            Use --write when an intentional HTML change has landed on main and you want to
            update tests/test_html_baseline.py. Without --write the script prints the new
            mapping so you can review it manually.
            """
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Overwrite tests/test_html_baseline.py with the refreshed mapping",
    )
    args = parser.parse_args()

    baseline = _load_baseline_module()
    hashes, missing = _gather_hashes(baseline.EXPECTED_SHA256)

    if missing:
        missing_list = "\n - ".join(missing)
        print(f"Missing files, cannot compute hashes:\n - {missing_list}", file=sys.stderr)
        return 1

    if args.write:
        _rewrite_test_file(hashes)
        print("Updated tests/test_html_baseline.py with fresh hashes.")
    else:
        print("Paste this mapping into tests/test_html_baseline.py if the HTML changes were intentional:\n")
        for line in _format_mapping(hashes):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
