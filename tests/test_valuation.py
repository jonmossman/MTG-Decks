import datetime as _dt
import textwrap
from pathlib import Path

import pytest

from mtg_decks import DeckLibrary
from mtg_decks.importer import CardData, CardResolver
from mtg_decks.valuation import (
    DeckValuation,
    DeckValuer,
    ValuationCache,
    render_valuation_report,
)


class FakePriceResolver(CardResolver):
    def __init__(self, mapping: dict[str, CardData]):
        self.mapping = mapping

    def resolve(self, query: str):
        return self.mapping.get(query)


def test_deck_valuer_sums_prices_and_tracks_missing():
    resolver = FakePriceResolver(
        {
            "Sol Ring": CardData(name="Sol Ring", prices={"gbp": "1.50"}),
            "Arcane Signet": CardData(name="Arcane Signet", prices={"gbp": "2.25"}),
        }
    )

    valuer = DeckValuer(resolver=resolver)
    valuation = valuer.value_counts({"Sol Ring": 2, "Arcane Signet": 1, "Mystic Remora": 1})

    assert valuation.currency == "gbp"
    assert valuation.total == pytest.approx(5.25)
    assert valuation.formatted_total() == "£5.25"
    assert "Mystic Remora" in valuation.missing_prices


def test_library_value_deck_supports_configurable_currency(tmp_path: Path):
    deck_dir = tmp_path / "decks"
    deck_dir.mkdir()
    deck_path = deck_dir / "priced.md"
    deck_path.write_text(
        textwrap.dedent(
            """
            ---
            name: Priced Deck
            commander: Budget Boss
            format: Commander
            ---

            ## Decklist
            - [Commander] Budget Boss
            - 2x Sol Ring
            - Arcane Signet
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    resolver = FakePriceResolver(
        {
            "Budget Boss": CardData(name="Budget Boss", prices={"usd": "3.00"}),
            "Sol Ring": CardData(name="Sol Ring", prices={"usd": "1.00"}),
            "Arcane Signet": CardData(name="Arcane Signet", prices={"usd": "0.75"}),
        }
    )

    library = DeckLibrary(deck_dir)
    valuation = library.value_deck("priced", currency="usd", resolver=resolver)

    assert valuation.total == pytest.approx(5.75)
    assert valuation.formatted_total().startswith("$")
    assert not valuation.missing_prices


def test_library_value_all_returns_mapping_for_every_deck(tmp_path: Path):
    deck_dir = tmp_path / "decks"
    deck_dir.mkdir()

    (deck_dir / "one.md").write_text(
        textwrap.dedent(
            """
            ---
            name: First Deck
            commander: One Boss
            format: Commander
            ---

            ## Decklist
            - [Commander] One Boss
            - Sol Ring
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (deck_dir / "two.md").write_text(
        textwrap.dedent(
            """
            ---
            name: Second Deck
            commander: Two Boss
            format: Commander
            ---

            ## Decklist
            - [Commander] Two Boss
            - Arcane Signet
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    resolver = FakePriceResolver(
        {
            "One Boss": CardData(name="One Boss", prices={"usd": "3.00"}),
            "Sol Ring": CardData(name="Sol Ring", prices={"usd": "1.00"}),
            "Two Boss": CardData(name="Two Boss", prices={"usd": "0.50"}),
        }
    )

    library = DeckLibrary(deck_dir)
    valuations = library.value_all(currency="usd", resolver=resolver)

    assert set(valuations.keys()) == {"First Deck", "Second Deck"}
    assert valuations["First Deck"].total == pytest.approx(4.0)
    assert valuations["Second Deck"].missing_prices == ["Arcane Signet"]


def test_render_valuation_report_orders_and_formats_results():
    valuations = {
        "B Deck": DeckValuation(currency="usd", total=12.5, missing_prices=["Mystic Remora"]),
        "A Deck": DeckValuation(currency="usd", total=3.0, missing_prices=[]),
    }

    report = render_valuation_report(valuations, currency="usd", as_of=_dt.datetime(2024, 1, 1))

    assert "# Deck Valuation Report" in report
    assert "As of: 2024-01-01T00:00:00Z" in report
    sections = [line for line in report.splitlines() if line.startswith("## ")]
    assert sections == ["## A Deck", "## B Deck"]
    assert "Price lookups needed (1):" in report


def test_value_all_reuses_cache_within_month(tmp_path: Path):
    deck_dir = tmp_path / "decks"
    deck_dir.mkdir()
    deck_path = deck_dir / "cached.md"
    deck_path.write_text(
        textwrap.dedent(
            """
            ---
            name: Cached Deck
            commander: Cache Boss
            format: Commander
            ---

            ## Decklist
            - [Commander] Cache Boss
            - Sol Ring
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    cache_path = tmp_path / "valuation-cache.json"
    cache = ValuationCache(cache_path)
    cached_valuation = DeckValuation(currency="usd", total=10.0, missing_prices=[])
    as_of = _dt.datetime(2024, 2, 15)
    cache.store("Cached Deck", cached_valuation, as_of=as_of)
    cache.save()

    class CountingResolver(CardResolver):
        def __init__(self):
            self.calls = 0

        def resolve(self, query: str):
            self.calls += 1
            return CardData(name=query, prices={"usd": "1.00"})

    resolver = CountingResolver()
    library = DeckLibrary(deck_dir)
    valuations = library.value_all(
        currency="usd", resolver=resolver, cache=ValuationCache(cache_path), now=as_of
    )

    assert valuations["Cached Deck"].total == pytest.approx(10.0)
    assert resolver.calls == 0


def test_value_all_refreshes_cache_for_outdated_month(tmp_path: Path):
    deck_dir = tmp_path / "decks"
    deck_dir.mkdir()
    deck_path = deck_dir / "stale.md"
    deck_path.write_text(
        textwrap.dedent(
            """
            ---
            name: Stale Deck
            commander: Stale Boss
            format: Commander
            ---

            ## Decklist
            - [Commander] Stale Boss
            - Arcane Signet
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    cache_path = tmp_path / "valuation-cache.json"
    cache = ValuationCache(cache_path)
    cache.store(
        "Stale Deck",
        DeckValuation(currency="usd", total=1.0, missing_prices=["Arcane Signet"]),
        as_of=_dt.datetime(2024, 1, 1),
    )
    cache.save()

    class CountingResolver(CardResolver):
        def __init__(self):
            self.calls = 0

        def resolve(self, query: str):
            self.calls += 1
            return CardData(name=query, prices={"usd": "2.00"})

    resolver = CountingResolver()
    as_of = _dt.datetime(2024, 2, 1)
    library = DeckLibrary(deck_dir)
    valuations = library.value_all(
        currency="usd", resolver=resolver, cache=ValuationCache(cache_path), now=as_of
    )

    assert valuations["Stale Deck"].total == pytest.approx(4.0)
    assert resolver.calls > 0

    refreshed_cache = ValuationCache(cache_path)
    refreshed_cache.load()
    cached_entry = refreshed_cache.get("Stale Deck", currency="usd", now=as_of)
    assert cached_entry is not None
    assert cached_entry.total == pytest.approx(4.0)
