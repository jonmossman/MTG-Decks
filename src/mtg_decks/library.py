from __future__ import annotations

import datetime as _dt
import logging
from pathlib import Path
from typing import Iterable

from .deck import Deck, slugify
from .importer import import_deck as import_deck_from_source
from .rules import load_decklist
from .valuation import DeckValuation, DeckValuer


logger = logging.getLogger(__name__)


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

    def validate_decks(
        self,
        *,
        log_path: str | Path | None = None,
        rules=None,
    ) -> list[str]:
        """Validate deck files and optionally write a log of any errors.

        The log file is overwritten on each invocation so callers do not need
        to manually clear previous results.
        """

        errors: list[str] = []
        for path in self.deck_files():
            try:
                deck = Deck.from_file(path)
                if not deck.name:
                    raise ValueError("Deck name is required")
                if not deck.commander:
                    raise ValueError("Commander is required")

                if rules is not None:
                    card_counts, commander_entries = load_decklist(path)
                    for issue in rules.validate(deck, card_counts, commander_entries):
                        message = f"{path}: {issue}"
                        errors.append(message)
                        logger.error(message)
            except Exception as exc:
                message = f"{path}: {exc}"
                errors.append(message)
                logger.error(message)

        if log_path is not None:
            Path(log_path).write_text(
                "\n".join(errors or ["All decks valid."]), encoding="utf-8"
            )

        return errors

    def create_deck(
        self,
        name: str,
        commander: str,
        *,
        colors: Iterable[str] | None = None,
        theme: str | None = None,
        notes: str | None = None,
        created: str | None = None,
        deck_format: str = "Commander",
        template: str | Path | None = None,
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
            format=deck_format,
            notes=notes,
            path=target,
        )
        template_text = None
        if template is not None:
            template_path = Path(template)
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")
            template_text = template_path.read_text(encoding="utf-8")

        target.write_text(deck.to_markdown(body_template=template_text), encoding="utf-8")
        return target

    def read_deck(self, name_or_slug: str) -> Deck:
        slug = slugify(name_or_slug)
        path = self.root / f"{slug}.md"
        if not path.exists():
            raise FileNotFoundError(f"Deck not found: {path}")
        return Deck.from_file(path)

    def import_deck(
        self,
        deck_name: str,
        commander: str,
        *,
        card_source: str | Path,
        colors: Iterable[str] | None = None,
        theme: str | None = None,
        notes: str | None = None,
        deck_format: str = "Commander",
        overwrite: bool = False,
        resolver=None,
        rules=None,
    ):
        """Import a decklist from free-form text or CSV using an external resolver."""

        return import_deck_from_source(
            library_root=self.root,
            deck_name=deck_name,
            commander=commander,
            card_source=card_source,
            colors=colors,
            theme=theme,
            notes=notes,
            deck_format=deck_format,
            overwrite=overwrite,
            resolver=resolver,
            rules=rules,
        )

    def value_deck(
        self,
        name_or_slug: str,
        *,
        currency: str = "gbp",
        resolver=None,
        cache=None,
        now: _dt.datetime | None = None,
    ):
        """Estimate the total value of a deck using card price lookups."""

        deck = self.read_deck(name_or_slug)
        if deck.path is None:
            raise FileNotFoundError("Deck is missing a path to load card entries")

        current_time = now or _dt.datetime.utcnow()
        if cache is not None:
            cached = cache.get(deck.name, currency=currency, now=current_time)
            if cached is not None:
                return cached

        card_counts, _ = load_decklist(deck.path)
        valuer = DeckValuer(resolver=resolver)
        valuation = valuer.value_counts(card_counts, currency=currency)

        if cache is not None:
            cache.store(deck.name, valuation, as_of=current_time)
            cache.save()

        return valuation

    def value_all(
        self,
        *,
        currency: str = "gbp",
        resolver=None,
        cache=None,
        now: _dt.datetime | None = None,
    ) -> dict[str, DeckValuation]:
        """Estimate the value of every deck in the library.

        Returns a mapping of deck name to valuation results so callers can
        format reports or compare how totals shift over time.
        """

        valuer = DeckValuer(resolver=resolver)
        results: dict[str, DeckValuation] = {}
        current_time = now or _dt.datetime.utcnow()

        for path in self.deck_files():
            deck = Deck.from_file(path)

            if cache is not None:
                cached = cache.get(deck.name, currency=currency, now=current_time)
                if cached is not None:
                    results[deck.name] = cached
                    continue

            card_counts, _ = load_decklist(path)
            valuation = valuer.value_counts(card_counts, currency=currency)
            results[deck.name] = valuation

            if cache is not None:
                cache.store(deck.name, valuation, as_of=current_time)

        if cache is not None:
            cache.save()

        return results

    def show(self, name_or_slug: str) -> str:
        deck = self.read_deck(name_or_slug)
        lines = [deck.name]
        lines.append(f"Commander: {deck.commander}")
        if deck.colors:
            lines.append(f"Colors: {', '.join(deck.colors)}")
        if deck.theme:
            lines.append(f"Theme: {deck.theme}")
        if deck.format:
            lines.append(f"Format: {deck.format}")
        if deck.notes:
            lines.append(f"Notes: {deck.notes}")
        if deck.created:
            lines.append(f"Created: {deck.created}")
        if deck.updated:
            lines.append(f"Updated: {deck.updated}")
        return "\n".join(lines)
