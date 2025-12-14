import textwrap
from pathlib import Path

import pytest

from mtg_decks import DeckLibrary
from mtg_decks.importer import CardData, CardResolver
from mtg_decks.valuation import DeckValuer


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
