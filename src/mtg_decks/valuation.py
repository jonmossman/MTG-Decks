from __future__ import annotations

from dataclasses import dataclass, field

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
