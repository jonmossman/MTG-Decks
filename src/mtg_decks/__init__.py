"""Utilities for storing and inspecting Commander decks as Markdown files."""

from .deck import Deck
from .importer import CardResolver, ImportResult, ScryfallResolver, import_deck
from .library import DeckLibrary
from .rules import CommanderRules, load_decklist, parse_decklist
from .valuation import DeckValuation, DeckValuer

__version__ = "0.1.0"

__all__ = [
    "CommanderRules",
    "Deck",
    "DeckLibrary",
    "ImportResult",
    "CardResolver",
    "ScryfallResolver",
    "import_deck",
    "DeckValuation",
    "DeckValuer",
    "__version__",
    "load_decklist",
    "parse_decklist",
]
