"""Lightweight checks for the GitHub Pages assets to avoid 404s."""

from __future__ import annotations

import logging
import os
import sys
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

    formatter = logging.Formatter("%(levelname)s %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _candidate_site_roots(site_root: Path | None) -> list[Path]:
    candidates: list[Path] = []

    if site_root is not None:
        candidates.append(Path(site_root))
        return [candidates[0].resolve()]

    env_root = os.getenv("MTG_DECKS_SITE_ROOT")
    if env_root:
        candidates.append(Path(env_root))

    candidates.append(Path.cwd() / "site")
    candidates.append(SITE_ROOT)

    seen: set[Path] = set()
    unique_candidates: list[Path] = []

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(resolved)

    return unique_candidates


def _resolve_site_root(logger: logging.Logger, site_root: Path | None = None) -> Path:
    candidates = _candidate_site_roots(site_root)

    for candidate in candidates:
        if candidate.exists():
            logger.info("Using site root: %s", candidate)
            return candidate

    logger.warning("No candidate site roots exist; defaulting to %s", candidates[0])
    return candidates[0]


def validate_site_assets(site_root: Path | None = None, log_path: Path = DEFAULT_ERROR_LOG) -> bool:
    """Ensure the published HTML assets exist and log a useful error when any are missing."""

    logger = _configure_logger(log_path)
    resolved_site_root = _resolve_site_root(logger, site_root=site_root)
    logger.info("Checking site assets in %s", resolved_site_root)

    if not resolved_site_root.exists():
        logger.error("Site root does not exist: %s", resolved_site_root)
        return False

    missing: list[Path] = []

    for rel_path in REQUIRED_SITE_FILES:
        candidate = resolved_site_root / rel_path
        if not candidate.exists():
            missing.append(candidate)

    if missing:
        logger.error("Found %s missing site asset(s)", len(missing))
        for path in missing:
            logger.error("Missing site asset: %s", path)
        return False

    logger.info("All site assets present in %s", resolved_site_root)
    return True


def main() -> int:  # pragma: no cover - thin CLI wrapper
    return 0 if validate_site_assets() else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
