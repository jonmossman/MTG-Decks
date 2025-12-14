"""Utilities for storing and inspecting Commander decks as Markdown files."""

from .deck import Deck
from .importer import CardResolver, ImportResult, ScryfallResolver, import_deck
from .inventory import SpareCard, SparesInventory, build_spare_cards
from .library import DeckLibrary
from .rules import CommanderRules, load_decklist, parse_decklist
from .valuation import DeckValuation, DeckValuer, ValuationCache

__version__ = "0.1.0"

__all__ = [
    "CommanderRules",
    "Deck",
    "DeckLibrary",
    "SpareCard",
    "SparesInventory",
    "build_spare_cards",
    "ImportResult",
    "CardResolver",
    "ScryfallResolver",
    "import_deck",
    "DeckValuation",
    "DeckValuer",
    "ValuationCache",
    "__version__",
    "load_decklist",
    "parse_decklist",
    "validate_site_assets",
]


def validate_site_assets(*args, **kwargs):
    from .site_checks import validate_site_assets as _validate_site_assets

    return _validate_site_assets(*args, **kwargs)
