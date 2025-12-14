from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Iterable

from .importer import CardResolver, ScryfallResolver, parse_import_rows
from .valuation import DeckValuer


@dataclass
class SpareCard:
    name: str
    count: int
    box: str
    cmc: float | None = None
    type_line: str | None = None

    def merge(self, other: "SpareCard") -> None:
        self.count += other.count
        if self.cmc is None:
            self.cmc = other.cmc
        if self.type_line is None:
            self.type_line = other.type_line


class SparesInventory:
    """Store spare card inventory data in a Markdown file."""

    def __init__(self, path: str | Path = "spares.md") -> None:
        self.path = Path(path)

    def load(self) -> list[SpareCard]:
        if not self.path.exists():
            return []

        entries: list[SpareCard] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            if set(stripped.replace("|", "").strip()) <= {"-", " ", ":"}:
                continue

            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or cells[0].lower() == "name":
                continue

            name = cells[0]
            count = _safe_int(cells[1]) if len(cells) > 1 else 1
            box = cells[2] if len(cells) > 2 else "Unsorted"
            cmc = _safe_float(cells[3]) if len(cells) > 3 else None
            type_line = cells[4] if len(cells) > 4 else None

            entries.append(SpareCard(name=name, count=count, box=box, cmc=cmc, type_line=type_line))

        return entries

    def add_cards(
        self,
        new_cards: Iterable[SpareCard],
        *,
        currency: str = "gbp",
        resolver: CardResolver | None = None,
        sort_by: str = "name",
    ) -> tuple[list[tuple[SpareCard, float | None]], list[str]]:
        existing = self.load()
        merged = _merge_cards(existing, list(new_cards))
        priced, missing = _price_cards(merged, currency=currency, resolver=resolver)
        sorted_entries = _sort_cards(priced, key=sort_by)
        self._write(sorted_entries, currency=currency)
        return sorted_entries, missing

    def search(
        self,
        *,
        currency: str = "gbp",
        resolver: CardResolver | None = None,
        query: str | None = None,
        boxes: set[str] | None = None,
        sort_by: str = "name",
    ) -> tuple[list[tuple[SpareCard, float | None]], list[str]]:
        entries = self.load()
        if query:
            query_lower = query.casefold()
            entries = [
                entry
                for entry in entries
                if query_lower in entry.name.casefold()
                or (entry.type_line and query_lower in entry.type_line.casefold())
                or query_lower in entry.box.casefold()
            ]

        if boxes:
            entries = [entry for entry in entries if entry.box in boxes]

        priced, missing = _price_cards(entries, currency=currency, resolver=resolver)
        priced = _sort_cards(priced, key=sort_by)
        return priced, missing

    def _write(self, entries: list[tuple[SpareCard, float | None]], *, currency: str) -> None:
        lines = ["# Spare Card Inventory", ""]
        lines.append(f"Currency: {currency.upper()}")
        lines.append("")
        lines.append("| Name | Count | Box | CMC | Type | Unit Value | Total Value |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")

        for entry, unit_price in entries:
            total = (unit_price or 0.0) * entry.count
            lines.append(
                "| {name} | {count} | {box} | {cmc} | {type_line} | {unit_value} | {total_value} |".format(
                    name=entry.name,
                    count=entry.count,
                    box=entry.box,
                    cmc="" if entry.cmc is None else _trim_trailing_zero(entry.cmc),
                    type_line=entry.type_line or "",
                    unit_value=_format_currency(unit_price, currency=currency),
                    total_value=_format_currency(total if unit_price is not None else None, currency=currency),
                )
            )

        self.path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_spare_cards(
    card_source: str | Path,
    *,
    resolver: CardResolver | None = None,
    box: str,
) -> list[SpareCard]:
    if isinstance(card_source, Path):
        card_text = Path(card_source).read_text(encoding="utf-8")
    else:
        card_text = card_source

    entries = parse_import_rows(card_text)
    if not entries:
        raise ValueError("No cards provided to import")

    resolver = resolver or ScryfallResolver()
    results: list[SpareCard] = []
    for count, name in entries:
        resolved = resolver.resolve(name)
        normalized = (resolved.name if resolved else name).strip()
        results.append(
            SpareCard(
                name=normalized,
                count=count,
                box=box,
                cmc=resolved.cmc if resolved else None,
                type_line=resolved.type_line if resolved else None,
            )
        )

    return results


def _merge_cards(existing: list[SpareCard], new_cards: list[SpareCard]) -> list[SpareCard]:
    by_key: dict[tuple[str, str], SpareCard] = {}
    for card in existing + new_cards:
        key = (card.name.casefold(), card.box)
        if key not in by_key:
            by_key[key] = SpareCard(
                name=card.name,
                count=card.count,
                box=card.box,
                cmc=card.cmc,
                type_line=card.type_line,
            )
        else:
            by_key[key].merge(card)
    return list(by_key.values())


def _price_cards(
    entries: list[SpareCard], *, currency: str, resolver: CardResolver | None = None
) -> tuple[list[tuple[SpareCard, float | None]], list[str]]:
    valuer = DeckValuer(resolver=resolver)
    priced: list[tuple[SpareCard, float | None]] = []
    missing: list[str] = []

    for entry in entries:
        unit_price = valuer.price_card(entry.name, currency=currency)
        if unit_price is None:
            missing.append(entry.name)
        priced.append((entry, unit_price))

    return priced, missing


def _sort_cards(
    entries: list[tuple[SpareCard, float | None]], *, key: str
) -> list[tuple[SpareCard, float | None]]:
    key = key.lower()

    if key == "value":
        return sorted(
            entries,
            key=lambda item: ((item[1] or 0.0) * item[0].count) * -1,
        )
    if key == "cmc":
        return sorted(entries, key=lambda item: (item[0].cmc is None, item[0].cmc or 0))
    return sorted(entries, key=lambda item: item[0].name.casefold())


def _format_currency(value: float | None, *, currency: str) -> str:
    if value is None:
        return "Unknown"
    symbol = {"usd": "$", "eur": "€", "gbp": "£"}.get(currency.lower())
    formatted = f"{value:,.2f}"
    return f"{symbol}{formatted}" if symbol else f"{currency.upper()} {formatted}"


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1


def _safe_float(value: str) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def _trim_trailing_zero(value: float) -> str:
    text = f"{value:g}"
    return text

