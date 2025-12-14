from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable

from .deck import Deck


DeckCounts = dict[str, int]


def parse_decklist(markdown: str) -> tuple[DeckCounts, set[str]]:
    """Extract card counts and commander markers from a Markdown decklist section."""

    lines = markdown.splitlines()
    decklist_start = None
    for idx, line in enumerate(lines):
        if line.strip().lower() == "## decklist":
            decklist_start = idx + 1
            break
    if decklist_start is None:
        raise ValueError("No '## Decklist' section found")

    card_counts: DeckCounts = {}
    commander_names: set[str] = set()
    bullet_pattern = re.compile(r"^(?P<count>\d+)x?\s+(?P<name>.+)$")

    for line in lines[decklist_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") and not stripped.startswith("-"):
            break
        if not stripped.startswith("-"):
            continue

        entry = stripped.lstrip("-").strip()
        is_commander = False
        if entry.lower().startswith("[commander]"):
            is_commander = True
            entry = entry[len("[commander]") :].strip()

        match = bullet_pattern.match(entry)
        if match:
            count = int(match.group("count"))
            name = match.group("name").strip()
        else:
            count = 1
            name = entry

        card_counts[name] = card_counts.get(name, 0) + count
        if is_commander:
            commander_names.add(name)

    return card_counts, commander_names


@dataclass
class CommanderRules:
    """Configurable validation for Commander deck construction."""

    deck_size: int = 100
    expected_format: str = "Commander"
    allow_duplicate_basics: bool = True
    require_commander_tag: bool = True
    max_commander_entries: int = 1
    basic_lands: Iterable[str] = field(
        default_factory=lambda: {
            "Plains",
            "Island",
            "Swamp",
            "Mountain",
            "Forest",
            "Wastes",
            "Snow-Covered Plains",
            "Snow-Covered Island",
            "Snow-Covered Swamp",
            "Snow-Covered Mountain",
            "Snow-Covered Forest",
        }
    )
    banned_cards: Iterable[str] = field(default_factory=set)

    def validate(
        self, deck: Deck, card_counts: DeckCounts, commander_entries: set[str]
    ) -> list[str]:
        errors: list[str] = []

        if deck.format and deck.format.lower() != self.expected_format.lower():
            errors.append(f"Deck format must be {self.expected_format}")

        total_cards = sum(card_counts.values())
        if total_cards != self.deck_size:
            errors.append(f"Deck must contain exactly {self.deck_size} cards (found {total_cards})")

        normalized_basics = {name.casefold() for name in self.basic_lands}
        normalized_banned = {name.casefold() for name in self.banned_cards}
        for name, count in card_counts.items():
            if name.casefold() in normalized_banned:
                errors.append(f"Card '{name}' is banned in {self.expected_format}")
            if count > 1 and not (
                self.allow_duplicate_basics and name.casefold() in normalized_basics
            ):
                errors.append(f"Card '{name}' appears {count} times; only basics may repeat")

        commander_present = False
        missing_commander_reported = False

        if commander_entries:
            if len(commander_entries) > self.max_commander_entries:
                errors.append(
                    f"Deck lists {len(commander_entries)} commanders; maximum is {self.max_commander_entries}"
                )

            for name in commander_entries:
                if name.casefold() == deck.commander.casefold():
                    commander_present = True
                    if card_counts.get(name, 0) != 1:
                        errors.append("Commander must appear exactly once in the decklist")

            if not commander_present:
                errors.append(
                    f"Commander '{deck.commander}' not marked in the Decklist section"
                )
                missing_commander_reported = True
        else:
            if self.require_commander_tag:
                errors.append("Commander entry missing from decklist")
                missing_commander_reported = True
            elif deck.commander.casefold() in (name.casefold() for name in card_counts):
                commander_present = True

        if not commander_present and not missing_commander_reported:
            errors.append("Commander entry missing from decklist")

        return errors


def load_decklist(path: Path) -> tuple[DeckCounts, set[str]]:
    return parse_decklist(path.read_text(encoding="utf-8"))
