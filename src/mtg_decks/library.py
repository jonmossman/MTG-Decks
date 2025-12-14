from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Iterable

from .deck import Deck, slugify


class DeckLibrary:
    """Manage a directory of Commander decks stored as Markdown files."""

    def __init__(self, root: Path | str = "decks") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def deck_files(self) -> list[Path]:
        return sorted(self.root.glob("*.md"))

    def load_decks(self) -> list[Deck]:
        return [Deck.from_file(path) for path in self.deck_files()]

    def list_summary(self) -> list[str]:
        summaries = []
        for deck in self.load_decks():
            colors = f" ({', '.join(deck.colors)})" if deck.colors else ""
            theme = f" — {deck.theme}" if deck.theme else ""
            summaries.append(f"{deck.name}{colors}{theme} :: Commander: {deck.commander}")
        return summaries

    def create_deck(
        self,
        name: str,
        commander: str,
        *,
        colors: Iterable[str] | None = None,
        theme: str | None = None,
        notes: str | None = None,
        created: str | None = None,
    ) -> Path:
        slug = slugify(name)
        target = self.root / f"{slug}.md"
        if target.exists():
            raise FileExistsError(f"Deck already exists: {target}")

        deck = Deck(
            name=name,
            commander=commander,
            colors=list(colors or []),
            theme=theme,
            created=created or _dt.date.today().isoformat(),
            notes=notes,
            path=target,
        )
        target.write_text(deck.to_markdown(), encoding="utf-8")
        return target

    def read_deck(self, name_or_slug: str) -> Deck:
        slug = slugify(name_or_slug)
        path = self.root / f"{slug}.md"
        if not path.exists():
            raise FileNotFoundError(f"Deck not found: {path}")
        return Deck.from_file(path)

    def show(self, name_or_slug: str) -> str:
        deck = self.read_deck(name_or_slug)
        lines = [deck.name]
        lines.append(f"Commander: {deck.commander}")
        if deck.colors:
            lines.append(f"Colors: {', '.join(deck.colors)}")
        if deck.theme:
            lines.append(f"Theme: {deck.theme}")
        if deck.notes:
            lines.append(f"Notes: {deck.notes}")
        if deck.created:
            lines.append(f"Created: {deck.created}")
        if deck.updated:
            lines.append(f"Updated: {deck.updated}")
        return "\n".join(lines)
