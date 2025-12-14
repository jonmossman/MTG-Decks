from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """Populate os.environ with values from a simple KEY=VALUE .env file.

    Existing environment variables always win so callers can layer files without
    clobbering explicit runtime configuration.
    """

    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if "=" not in trimmed:
            continue
        key, value = trimmed.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class AppConfig:
    """Container for runtime configuration values."""

    default_currency: str
    valuation_source: str
    valuation_cache_path: Path
    env_path: Path | None = None


def load_config(env_path: str | Path | None = ".env") -> AppConfig:
    """Load configuration from the environment or a .env file.

    Environment variables take precedence over .env entries and sensible
    defaults are provided for all fields so the CLI can function without any
    configuration present.
    """

    env_file = Path(env_path) if env_path is not None else None
    if env_file is not None:
        _load_env_file(env_file)

    default_currency = os.getenv("MTG_DECKS_CURRENCY", "GBP")
    valuation_source = os.getenv("MTG_DECKS_VALUATION_SOURCE", "scryfall")
    valuation_cache = os.getenv("MTG_DECKS_VALUATION_CACHE", "valuation-cache.json")

    return AppConfig(
        default_currency=default_currency,
        valuation_source=valuation_source,
        valuation_cache_path=Path(valuation_cache),
        env_path=env_file,
    )

