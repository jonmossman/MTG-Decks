from pathlib import Path

import datetime as _dt

import pytest

from mtg_decks.deck import Deck
from mtg_decks.library import DeckLibrary
from mtg_decks.valuation import DeckValuation


@pytest.fixture()
def library(tmp_path: Path) -> DeckLibrary:
    return DeckLibrary(root=tmp_path)


def _write_basic_deck(path: Path, *, name: str) -> None:
    deck = Deck(
        name=name,
        commander="Cmdr",
        colors=["U"],
        format="Commander",
        path=path,
    )
    path.write_text(
        deck.to_markdown(decklist_lines=["- [Commander] Cmdr", "- Sol Ring"]),
        encoding="utf-8",
    )


def test_create_deck_missing_template_raises(library: DeckLibrary, tmp_path: Path) -> None:
    missing_template = tmp_path / "missing-template.md"

    with pytest.raises(FileNotFoundError):
        library.create_deck(
            "Template Deck",
            "Cmdr",
            template=missing_template,
        )


def test_show_includes_metadata(library: DeckLibrary) -> None:
    created = _dt.date(2024, 1, 2).isoformat()
    deck_path = library.root / "meta.md"
    deck = Deck(
        name="Meta Deck",
        commander="Meta Cmdr",
        colors=["W", "U"],
        theme="Artifacts",
        format="Commander",
        created=created,
        updated="2024-02-03",
        notes="Test notes",
        path=deck_path,
    )
    deck_path.write_text(deck.to_markdown(), encoding="utf-8")

    output = library.show("meta")

    assert "Meta Deck" in output
    assert "Commander: Meta Cmdr" in output
    assert "Colors: W, U" in output
    assert "Theme: Artifacts" in output
    assert "Format: Commander" in output
    assert f"Created: {created}" in output
    assert "Updated: 2024-02-03" in output
    assert "Notes: Test notes" in output


def test_value_deck_prefers_cache(monkeypatch: pytest.MonkeyPatch, library: DeckLibrary) -> None:
    deck_path = library.root / "cached.md"
    _write_basic_deck(deck_path, name="Cache Test")

    cached = DeckValuation(currency="usd", total=1.23, missing_prices=[])

    class FakeCache:
        def get(self, name: str, *, currency: str, now: _dt.datetime):
            return cached

    def _unexpected_valuer(*_, **__):  # pragma: no cover - defensive
        raise AssertionError("DeckValuer should not be called when cache hits")

    monkeypatch.setattr("mtg_decks.library.DeckValuer", _unexpected_valuer)

    valuation = library.value_deck("cached", currency="USD", cache=FakeCache())

    assert valuation is cached


def test_value_deck_stores_cache(monkeypatch: pytest.MonkeyPatch, library: DeckLibrary) -> None:
    deck_path = library.root / "cache-store.md"
    _write_basic_deck(deck_path, name="Cache Store")

    class FakeCache:
        def __init__(self) -> None:
            self.stored = None
            self.saved = False

        def get(self, name: str, *, currency: str, now: _dt.datetime):
            return None

        def store(self, name: str, valuation: DeckValuation, *, as_of: _dt.datetime):
            self.stored = (name, valuation.currency, valuation.total, as_of.date())

        def save(self):
            self.saved = True

    class FakeValuer:
        def __init__(self, resolver=None) -> None:
            self.resolver = resolver

        def value_counts(self, *_args, **_kwargs):
            return DeckValuation(currency="usd", total=9.99, missing_prices=[])

    cache = FakeCache()
    monkeypatch.setattr("mtg_decks.library.DeckValuer", FakeValuer)

    valuation = library.value_deck("cache-store", currency="USD", cache=cache)

    assert valuation.currency == "usd"
    assert cache.stored[0] == "Cache Store"
    assert cache.saved is True


def test_value_all_uses_cache_and_saves(monkeypatch: pytest.MonkeyPatch, library: DeckLibrary) -> None:
    first = library.root / "first.md"
    _write_basic_deck(first, name="Cached Deck")

    second = library.root / "second.md"
    _write_basic_deck(second, name="Needs Valuation")

    cached_val = DeckValuation(currency="usd", total=3.21, missing_prices=[])

    class FakeCache:
        def __init__(self) -> None:
            self.saved = False

        def get(self, name: str, *, currency: str, now: _dt.datetime):
            if name == "Cached Deck":
                return cached_val
            return None

        def store(self, name: str, valuation: DeckValuation, *, as_of: _dt.datetime):
            assert name == "Needs Valuation"
            assert valuation.total == 2.22

        def save(self):
            self.saved = True

    class FakeValuer:
        def __init__(self, resolver=None) -> None:
            self.resolver = resolver

        def value_counts(self, *_args, **_kwargs):
            return DeckValuation(currency="usd", total=2.22, missing_prices=[])

    cache = FakeCache()
    monkeypatch.setattr("mtg_decks.library.DeckValuer", FakeValuer)

    valuations = library.value_all(currency="USD", cache=cache)

    assert valuations["Cached Deck"] is cached_val
    assert valuations["Needs Valuation"].total == 2.22
    assert valuations["Needs Valuation"].currency == "usd"
    assert cache.saved is True
