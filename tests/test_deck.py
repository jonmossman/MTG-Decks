import logging
import textwrap
from pathlib import Path

import pytest

from mtg_decks.deck import Deck, slugify
from mtg_decks.library import DeckLibrary
from mtg_decks.rules import CommanderRules


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Limit Break", "limit-break"),
        ("  Chaos ! Control  ", "chaos-control"),
        ("only$$$symbols###", "onlysymbols"),
        ("", "deck"),
    ],
)
def test_slugify_variations(text, expected):
    assert slugify(text) == expected


def test_round_trip_markdown(tmp_path: Path):
    deck = Deck(
        name="Limit Break",
        commander="Cloud, Ex-SOLDIER",
        colors=["W", "U", "B", "G"],
        theme="Superfriends control",
        notes="Protect your walkers",
        created="2024-01-01",
        updated="2024-01-02",
    )
    path = tmp_path / "limit-break.md"
    path.write_text(deck.to_markdown(), encoding="utf-8")

    loaded = Deck.from_file(path)
    assert loaded.name == deck.name
    assert loaded.commander == deck.commander
    assert loaded.colors == deck.colors
    assert loaded.theme == deck.theme
    assert loaded.notes == deck.notes
    assert loaded.created == deck.created
    assert loaded.updated == deck.updated
    assert "## Decklist" in deck.to_markdown()


def test_front_matter_validation_requires_colon(tmp_path: Path):
    path = tmp_path / "invalid.md"
    path.write_text(
        """---
name: Bad Deck
colors W U B
---
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        Deck.from_file(path)


def test_requires_commander_in_front_matter(tmp_path: Path):
    path = tmp_path / "missing.md"
    path.write_text(
        """---
name: Missing Commander
---
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        Deck.from_file(path)


def test_requires_closing_front_matter_delimiter(tmp_path: Path):
    path = tmp_path / "unterminated.md"
    path.write_text(
        """---
name: Missing Commander
commander: No Close
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        Deck.from_file(path)


def test_custom_template_rendering(tmp_path: Path):
    deck = Deck(
        name="Custom Deck",
        commander="Custom Commander",
        colors=["R"],
        created="2024-06-01",
        format="Modern",
    )
    body = textwrap.dedent(
        """
        # {name}
        Commander: {commander}
        Colors: {colors}
        Format: {format}
        Created: {created}
        Missing: {missing_field}
        """
    )
    content = deck.to_markdown(body_template=body)
    assert "Commander: Custom Commander" in content
    assert "Format: Modern" in content
    assert "Missing:" in content
    assert "Missing:\n\n## Decklist" in content


def test_library_create_and_read_deck(tmp_path: Path):
    library = DeckLibrary(tmp_path)
    path = library.create_deck(
        "Niv-Mizzet Spells",
        "Niv-Mizzet Reborn",
        colors=["W", "U", "B", "R", "G"],
        theme="5c goodstuff",
        deck_format="Commander",
        notes="Cast lots of multicolored spells",
    )
    assert path.exists()

    loaded = library.read_deck("niv-mizzet-spells")
    assert loaded.commander == "Niv-Mizzet Reborn"
    assert "niv-mizzet-spells.md" in str(path)
    assert "Notes: Cast lots of multicolored spells" in library.show("niv-mizzet-spells")


def test_library_prevents_duplicate_creation(tmp_path: Path):
    library = DeckLibrary(tmp_path)
    library.create_deck("Duplicate Deck", "First Commander")
    with pytest.raises(FileExistsError):
        library.create_deck("Duplicate Deck", "Second Commander")


def test_library_show_includes_metadata(tmp_path: Path):
    library = DeckLibrary(tmp_path)
    library.create_deck(
        "Metadata Deck",
        "Meta Commander",
        colors=["U", "G"],
        theme="Tempo",
        notes="Keep mana open",
        deck_format="Modern",
        created="2024-03-02",
    )
    output = library.show("metadata-deck")
    assert "Metadata Deck" in output
    assert "Commander: Meta Commander" in output
    assert "Colors: U, G" in output
    assert "Format: Modern" in output
    assert "Notes: Keep mana open" in output
    assert "Created: 2024-03-02" in output


def test_library_requires_existing_template(tmp_path: Path):
    library = DeckLibrary(tmp_path)
    with pytest.raises(FileNotFoundError):
        library.create_deck(
            "Template Deck",
            "Template Commander",
            template=tmp_path / "missing-template.md",
        )


def test_repository_decks_validate_clean(tmp_path: Path):
    repo_root = Path(__file__).resolve().parent.parent
    deck_root = repo_root / "decks"
    log_file = tmp_path / "validation.log"

    library = DeckLibrary(deck_root)
    errors = library.validate_decks(log_path=log_file, rules=CommanderRules())

    assert errors == []
    assert log_file.read_text(encoding="utf-8").strip() == "All decks valid."


def test_validate_logs_errors_and_overwrites(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    library = DeckLibrary(tmp_path)
    bad_deck = tmp_path / "invalid.md"
    bad_deck.write_text(
        """---
name: Bad Deck
---
""",
        encoding="utf-8",
    )

    log_file = tmp_path / "validation.log"
    log_file.write_text("old logs", encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        errors = library.validate_decks(log_path=log_file)

    assert len(errors) == 1
    assert "commander" in errors[0]
    assert "old logs" not in log_file.read_text(encoding="utf-8")
    assert caplog.records and caplog.records[0].levelname == "ERROR"
