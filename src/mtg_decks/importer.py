from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from .deck import Deck, slugify
from .rules import CommanderRules, load_decklist


@dataclass
class CardData:
    """Basic information returned from a card lookup."""

    name: str
    type_line: str | None = None
    color_identity: list[str] | None = None
    prices: dict[str, str] | None = None


class CardResolver:
    """Abstract card resolver that can normalize user-provided names."""

    def resolve(self, query: str) -> CardData | None:  # pragma: no cover - interface
        raise NotImplementedError


class ScryfallResolver(CardResolver):
    """Resolve card names using Scryfall's fuzzy matching API."""

    def __init__(self, base_url: str = "https://api.scryfall.com") -> None:
        self.base_url = base_url.rstrip("/")

    def resolve(self, query: str) -> CardData | None:
        url = f"{self.base_url}/cards/named?fuzzy={urllib.parse.quote(query)}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        return CardData(
            name=payload.get("name", query),
            type_line=payload.get("type_line"),
            color_identity=payload.get("color_identity") or payload.get("colors"),
            prices=payload.get("prices"),
        )


@dataclass
class ImportResult:
    path: Path
    warnings: list[str]
    commander: str
    cards: list[str]


def parse_import_rows(text: str) -> list[tuple[int, str]]:
    """Parse newline or CSV-based input into (count, card_name) tuples."""

    rows: list[tuple[int, str]] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row or not "".join(row).strip():
            continue

        if len(row) >= 2:
            count_text, name = row[0].strip(), ",".join(row[1:]).strip()
        else:
            line = row[0].strip()
            parts = line.split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                count_text, name = parts[0], parts[1]
            else:
                count_text, name = "1", line

        count = int(count_text) if count_text.isdigit() else 1
        rows.append((count, name))

    return rows


def import_deck(
    *,
    library_root: Path,
    deck_name: str,
    commander: str,
    card_source: str | Path,
    colors: Iterable[str] | None = None,
    theme: str | None = None,
    notes: str | None = None,
    deck_format: str = "Commander",
    overwrite: bool = False,
    resolver: CardResolver | None = None,
    rules: CommanderRules | None = None,
) -> ImportResult:
    """Import a deck from free-form card input or CSV and write it to disk."""

    if isinstance(card_source, Path):
        card_text = Path(card_source).read_text(encoding="utf-8")
    else:
        card_text = card_source

    entries = parse_import_rows(card_text)
    if not entries:
        raise ValueError("No cards provided to import")

    resolver = resolver or ScryfallResolver()
    warnings: list[str] = []

    resolved_commander = resolver.resolve(commander)
    commander_name = (resolved_commander.name if resolved_commander else commander).strip()
    if commander_name.casefold() != commander.casefold():
        warnings.append(f"Commander resolved as '{commander_name}' (input: '{commander}')")
    if resolved_commander is None:
        warnings.append(f"Commander lookup failed for '{commander}'; using provided text")

    deck_colors = list(colors or [])
    if not deck_colors and resolved_commander and resolved_commander.color_identity:
        deck_colors = list(resolved_commander.color_identity)

    normalized_cards: list[tuple[int, str]] = []
    for count, name in entries:
        resolved = resolver.resolve(name)
        normalized = (resolved.name if resolved else name).strip()
        if resolved is None:
            warnings.append(f"Using '{name}' as-is (lookup failed)")
        elif normalized.casefold() != name.casefold():
            warnings.append(f"Resolved '{name}' to '{normalized}'")
        normalized_cards.append((count, normalized))

    # Remove explicit commander entries from the imported list to prevent doubles.
    filtered_cards: list[tuple[int, str]] = []
    for count, name in normalized_cards:
        if name.casefold() == commander_name.casefold():
            if count > 1:
                warnings.append("Commander provided multiple times; keeping a single copy")
            continue
        filtered_cards.append((count, name))

    decklist_lines = [f"- [Commander] {commander_name}"]
    for count, name in filtered_cards:
        prefix = f"{count}x " if count > 1 else ""
        decklist_lines.append(f"- {prefix}{name}")

    deck = Deck(
        name=deck_name,
        commander=commander_name,
        colors=deck_colors,
        theme=theme,
        notes=notes,
        format=deck_format,
        created=date.today().isoformat(),
    )

    deck_path = Path(library_root) / f"{slugify(deck_name)}.md"
    if deck_path.exists() and not overwrite:
        raise FileExistsError(f"Deck already exists: {deck_path}")

    markdown = deck.to_markdown(decklist_lines=decklist_lines)
    deck_path.write_text(markdown, encoding="utf-8")

    if rules is not None:
        counts, commander_entries = load_decklist(deck_path)
        violations = rules.validate(deck, counts, commander_entries)
        if violations:
            deck_path.unlink(missing_ok=True)
            raise ValueError("; ".join(violations))

    return ImportResult(
        path=deck_path,
        warnings=warnings,
        commander=commander_name,
        cards=decklist_lines,
    )
