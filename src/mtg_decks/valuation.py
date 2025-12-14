from __future__ import annotations

import json
from dataclasses import dataclass, field
import datetime as _dt
from pathlib import Path

from .importer import CardResolver, CardData, ScryfallResolver


_CURRENCY_SYMBOLS = {"usd": "$", "eur": "€", "gbp": "£"}


@dataclass
class DeckValuation:
    currency: str
    total: float
    missing_prices: list[str] = field(default_factory=list)

    def formatted_total(self) -> str:
        symbol = _CURRENCY_SYMBOLS.get(self.currency.lower())
        formatted = f"{self.total:,.2f}"
        return f"{symbol}{formatted}" if symbol else f"{self.currency.upper()} {formatted}"


class DeckValuer:
    """Look up card prices and estimate deck value in a given currency."""

    def __init__(self, resolver: CardResolver | None = None) -> None:
        self.resolver = resolver or ScryfallResolver()

    def price_card(self, name: str, currency: str = "gbp") -> float | None:
        card: CardData | None = self.resolver.resolve(name)
        if card is None or not card.prices:
            return None

        raw_price = card.prices.get(currency.lower()) or card.prices.get(currency.upper())
        if not raw_price:
            return None
        try:
            return float(raw_price)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None

    def value_counts(self, card_counts: dict[str, int], *, currency: str = "gbp") -> DeckValuation:
        total = 0.0
        missing: list[str] = []

        for name, count in card_counts.items():
            price = self.price_card(name, currency=currency)
            if price is None:
                missing.append(name)
                continue
            total += price * count

        return DeckValuation(currency=currency, total=total, missing_prices=missing)


class ValuationCache:
    """Cache deck valuations to avoid redundant price lookups."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data = {"decks": {}}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._data = {"decks": {}}
        self._data.setdefault("decks", {})
        self._loaded = True

    def _entry_is_current(self, valued_at: str, *, now: _dt.datetime) -> bool:
        try:
            timestamp = _dt.datetime.fromisoformat(valued_at)
        except ValueError:
            return False
        return timestamp.year == now.year and timestamp.month == now.month

    def get(self, deck_name: str, *, currency: str, now: _dt.datetime | None = None) -> DeckValuation | None:
        self.load()
        entry = self._data.get("decks", {}).get(deck_name)
        if not entry:
            return None
        if entry.get("currency", "").lower() != currency.lower():
            return None

        current_time = now or _dt.datetime.utcnow()
        if not self._entry_is_current(entry.get("valued_at", ""), now=current_time):
            return None

        return DeckValuation(
            currency=entry.get("currency", currency),
            total=float(entry.get("total", 0.0)),
            missing_prices=list(entry.get("missing_prices", [])),
        )

    def store(
        self,
        deck_name: str,
        valuation: DeckValuation,
        *,
        as_of: _dt.datetime | None = None,
    ) -> None:
        self.load()
        timestamp = (as_of or _dt.datetime.utcnow()).replace(microsecond=0).isoformat()
        self._data.setdefault("decks", {})[deck_name] = {
            "currency": valuation.currency,
            "total": valuation.total,
            "missing_prices": list(valuation.missing_prices),
            "valued_at": timestamp,
        }

    def save(self) -> None:
        self.load()
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")


def render_valuation_report(
    valuations: dict[str, DeckValuation], *, currency: str, as_of: _dt.datetime | None = None
) -> str:
    """Render a Markdown report for a batch of deck valuations.

    Args:
        valuations: Mapping of deck name to valuation results.
        currency: Three-letter currency code used for the valuation.
        as_of: Optional datetime describing when the prices were fetched. If omitted,
            UTC "now" is used.
    """

    timestamp = (as_of or _dt.datetime.utcnow()).replace(microsecond=0).isoformat() + "Z"
    lines = ["# Deck Valuation Report", f"As of: {timestamp}", "", ""]

    for name, valuation in sorted(valuations.items(), key=lambda item: item[0].lower()):
        lines.append(f"## {name}")
        lines.append(f"- **Total ({currency.upper()}):** {valuation.formatted_total()}")
        if valuation.missing_prices:
            lines.append(f"- **Price lookups needed ({len(valuation.missing_prices)}):**")
            for card in sorted(valuation.missing_prices, key=str.lower):
                lines.append(f"  - {card}")
        else:
            lines.append("- **Price lookups needed:** None")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
