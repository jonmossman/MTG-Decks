from pathlib import Path

import pytest

from mtg_decks import importer
from mtg_decks.library import DeckLibrary
from mtg_decks.rules import CommanderRules


class FakeResolver(importer.CardResolver):
    def __init__(self, mapping: dict[str, importer.CardData]):
        self.mapping = mapping

    def resolve(self, query: str):
        return self.mapping.get(query)


def test_parse_import_rows_handles_csv_and_lines():
    rows = importer.parse_import_rows(
        "2, Sol Ring\n4x Arcane Signet\n1 Arcane Signet\nMystic Remora"
    )
    assert rows == [
        (2, "Sol Ring"),
        (4, "Arcane Signet"),
        (1, "Arcane Signet"),
        (1, "Mystic Remora"),
    ]


def test_import_deck_normalizes_names_and_infers_colors(tmp_path: Path):
    deck_dir = tmp_path / "decks"
    deck_dir.mkdir()

    resolver = FakeResolver(
        {
            "Cloud": importer.CardData(
                name="Cloud, Ex-SOLDIER", color_identity=["W", "U", "B", "G"]
            ),
            "sol rng": importer.CardData(name="Sol Ring"),
            "arcane signet": importer.CardData(name="Arcane Signet"),
        }
    )

    result = importer.import_deck(
        library_root=deck_dir,
        deck_name="Messy Import",
        commander="Cloud",
        card_source="2, sol rng\narcane signet",
        resolver=resolver,
    )

    assert result.path.exists()
    assert any("Cloud" in warning for warning in result.warnings)

    library = DeckLibrary(deck_dir)
    deck = library.read_deck("messy-import")
    assert deck.colors == ["W", "U", "B", "G"]

    content = result.path.read_text(encoding="utf-8")
    assert "- [Commander] Cloud, Ex-SOLDIER" in content
    assert "- 2x Sol Ring" in content
    assert "- Arcane Signet" in content


def test_import_deck_enforces_rules_and_rolls_back(tmp_path: Path):
    deck_dir = tmp_path / "decks"
    deck_dir.mkdir()

    resolver = FakeResolver(
        {
            "Commander": importer.CardData(name="Commander", color_identity=["W"]),
            "Plains": importer.CardData(name="Plains"),
        }
    )

    with pytest.raises(ValueError) as excinfo:
        importer.import_deck(
            library_root=deck_dir,
            deck_name="Too Short",
            commander="Commander",
            card_source="Plains",
            resolver=resolver,
            rules=CommanderRules(deck_size=3),
        )

    assert "exactly 3 cards" in str(excinfo.value)
    assert not (deck_dir / "too-short.md").exists()
