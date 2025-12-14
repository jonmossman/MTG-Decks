import textwrap
from pathlib import Path

import pytest

from mtg_decks.deck import Deck
from mtg_decks.library import DeckLibrary
from mtg_decks.rules import CommanderRules, parse_decklist


def test_parse_decklist_extracts_counts_and_commander():
    markdown = textwrap.dedent(
        """
        # Sample Deck

        ## Decklist
        - [Commander] Atraxa, Praetors' Voice
        - 3x Island
        - Sol Ring
        - 2 Farseek
        - Forest
        """
    )

    card_counts, commanders = parse_decklist(markdown)

    assert commanders == {"Atraxa, Praetors' Voice"}
    assert card_counts["Atraxa, Praetors' Voice"] == 1
    assert card_counts["Island"] == 3
    assert card_counts["Farseek"] == 2
    assert card_counts["Sol Ring"] == 1


def test_commander_rules_flag_size_and_duplicate_issues():
    deck = Deck(
        name="Atraxa Superfriends",
        commander="Atraxa, Praetors' Voice",
        colors=["W", "U", "B", "G"],
    )
    card_counts = {
        "Atraxa, Praetors' Voice": 2,
        "Sol Ring": 2,
        "Island": 30,
    }
    card_counts.update({f"Card {idx}": 1 for idx in range(1, 68)})
    commanders = {"Atraxa, Praetors' Voice"}

    rules = CommanderRules()
    errors = rules.validate(deck, card_counts, commanders)

    assert "exactly 100 cards" in " ".join(errors)
    assert any("Sol Ring" in err for err in errors)
    assert any("Commander must appear exactly once" in err for err in errors)


def test_validate_decks_enforces_commander_rules(tmp_path: Path):
    deck_markdown = [
        "---",
        "name: Clean Commander Deck",
        "commander: Kudo, King Among Bears",
        "format: Commander",
        "---",
        "",
        "## Decklist",
        "- [Commander] Kudo, King Among Bears",
    ]
    deck_markdown.extend(f"- Plains" for _ in range(10))
    deck_markdown.extend(f"- Forest" for _ in range(10))
    deck_markdown.extend(f"- Utility Spell {idx}" for idx in range(1, 80))

    deck_dir = tmp_path / "decks"
    deck_dir.mkdir()
    deck_path = deck_dir / "clean.md"
    deck_path.write_text("\n".join(deck_markdown), encoding="utf-8")

    library = DeckLibrary(deck_dir)
    errors = library.validate_decks(rules=CommanderRules())

    assert errors == []


def _filler_counts(starting: dict[str, int], total: int = 100) -> dict[str, int]:
    counts = dict(starting)
    counts["Plains"] = counts.get("Plains", 0) + max(0, total - sum(counts.values()))
    return counts


def test_commander_tag_is_required_by_default():
    deck = Deck(name="Tagless", commander="Atraxa, Praetors' Voice")
    card_counts = _filler_counts({"Atraxa, Praetors' Voice": 1})

    rules = CommanderRules()
    errors = rules.validate(deck, card_counts, commander_entries=set())

    assert "Commander entry missing" in " ".join(errors)


def test_banned_cards_are_rejected():
    deck = Deck(name="Powered", commander="Atraxa, Praetors' Voice")
    card_counts = _filler_counts({"Atraxa, Praetors' Voice": 1, "Black Lotus": 1})

    rules = CommanderRules(banned_cards={"Black Lotus"})
    errors = rules.validate(deck, card_counts, commander_entries={"Atraxa, Praetors' Voice"})

    assert any("Black Lotus" in err for err in errors)


def test_partner_commanders_must_respect_limit():
    deck = Deck(name="Partners", commander="Tymna the Weaver")
    commanders = {"Tymna the Weaver", "Kraum, Ludevic's Opus"}
    card_counts = _filler_counts({name: 1 for name in commanders})

    strict_rules = CommanderRules()
    strict_errors = strict_rules.validate(deck, card_counts, commander_entries=commanders)
    assert any("maximum is 1" in err for err in strict_errors)

    partner_rules = CommanderRules(max_commander_entries=2)
    partner_errors = partner_rules.validate(deck, card_counts, commander_entries=commanders)
    assert not any("maximum" in err for err in partner_errors)
