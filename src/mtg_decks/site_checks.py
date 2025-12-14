"""Lightweight checks for the GitHub Pages assets to avoid 404s."""

from __future__ import annotations

import logging
from pathlib import Path

from .spec_sync import DEFAULT_ERROR_LOG, SITE_ROOT


REQUIRED_SITE_FILES = [
    "index.html",
    "decks.html",
    "inventory.html",
    "upload.html",
    "functional-spec.html",
    ".nojekyll",
]


def _configure_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("mtg_decks.site_checks")
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def validate_site_assets(site_root: Path = SITE_ROOT, log_path: Path = DEFAULT_ERROR_LOG) -> bool:
    """Ensure the published HTML assets exist and log a useful error when any are missing."""

    logger = _configure_logger(log_path)
    missing: list[Path] = []

    for rel_path in REQUIRED_SITE_FILES:
        candidate = site_root / rel_path
        if not candidate.exists():
            missing.append(candidate)

    if missing:
        for path in missing:
            logger.error("Missing site asset: %s", path)
        return False

    logger.info("All site assets present in %s", site_root)
    return True


def main() -> int:  # pragma: no cover - thin CLI wrapper
    return 0 if validate_site_assets() else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
