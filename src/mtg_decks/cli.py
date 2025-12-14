from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .library import DeckLibrary
from .rules import CommanderRules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Store and review Commander decks as Markdown files."
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--dir",
        dest="deck_dir",
        default="decks",
        help="Directory where deck markdown files are stored (default: decks)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List decks in the library")
    list_parser.set_defaults(func=cmd_list)

    show_parser = subparsers.add_parser("show", help="Show details for a deck")
    show_parser.add_argument("name", help="Deck name or slug")
    show_parser.set_defaults(func=cmd_show)

    create_parser = subparsers.add_parser("create", help="Create a new deck file")
    create_parser.add_argument("name", help="Deck name")
    create_parser.add_argument("commander", help="Deck commander")
    create_parser.add_argument(
        "--colors",
        nargs="*",
        default=None,
        help="Color identity (e.g. W U B R G)",
    )
    create_parser.add_argument("--theme", help="Deck theme or archetype", default=None)
    create_parser.add_argument(
        "--notes", help="Short notes that appear in the file front matter", default=None
    )
    create_parser.add_argument(
        "--format",
        dest="deck_format",
        default="Commander",
        help="Deck format (e.g. Commander, Standard, Modern)",
    )
    create_parser.add_argument(
        "--template",
        type=Path,
        help="Path to a Markdown template body that will be rendered with deck details",
    )
    create_parser.set_defaults(func=cmd_create)

    import_parser = subparsers.add_parser(
        "import", help="Import a deck from text or CSV using card lookups"
    )
    import_parser.add_argument("name", help="Deck name")
    import_parser.add_argument("commander", help="Deck commander (fuzzy matched)")
    import_parser.add_argument(
        "--file",
        type=Path,
        dest="card_file",
        help="Path to a CSV or text file with card entries",
    )
    import_parser.add_argument(
        "--cards",
        dest="card_text",
        help="Inline card entries separated by newlines (e.g. '2 Sol Ring\\n1 Farseek')",
    )
    import_parser.add_argument(
        "--colors",
        nargs="*",
        default=None,
        help="Color identity to pin on the deck (otherwise inferred from the commander if available)",
    )
    import_parser.add_argument("--theme", help="Deck theme or archetype", default=None)
    import_parser.add_argument(
        "--notes", help="Short notes that appear in the file front matter", default=None
    )
    import_parser.add_argument(
        "--format",
        dest="deck_format",
        default="Commander",
        help="Deck format (e.g. Commander, Standard, Modern)",
    )
    import_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing deck file instead of failing",
    )
    import_parser.set_defaults(func=cmd_import)

    value_parser = subparsers.add_parser(
        "value", help="Estimate deck value using price lookups"
    )
    value_parser.add_argument("name", help="Deck name or slug")
    value_parser.add_argument(
        "--currency",
        default="GBP",
        help="Three-letter currency code to price cards in (default: GBP)",
    )
    value_parser.set_defaults(func=cmd_value)

    validate_parser = subparsers.add_parser(
        "validate", help="Validate deck files against Commander rules"
    )
    validate_parser.add_argument(
        "--log",
        type=Path,
        dest="log_path",
        help="Optional log file to write results (overwrites on each run)",
    )
    validate_parser.add_argument(
        "--deck-size",
        type=int,
        default=100,
        help="Expected card count for the decklist (default: 100)",
    )
    validate_parser.add_argument(
        "--expected-format",
        default="Commander",
        help="Expected deck format name (default: Commander)",
    )
    validate_parser.add_argument(
        "--max-commanders",
        type=int,
        default=1,
        help="Maximum number of commander entries allowed (default: 1)",
    )
    validate_parser.add_argument(
        "--allow-missing-commander-tag",
        action="store_true",
        help="Do not require commander entries to be tagged in the decklist",
    )
    validate_parser.add_argument(
        "--no-duplicate-basics",
        action="store_true",
        help="Flag duplicate basics as errors instead of allowing them",
    )
    validate_parser.add_argument(
        "--ban",
        action="append",
        dest="banned_cards",
        default=[],
        help="Card name to ban (repeat for multiple entries)",
    )
    validate_parser.set_defaults(func=cmd_validate)

    return parser


def cmd_list(args: argparse.Namespace) -> int:
    library = DeckLibrary(args.deck_dir)
    summaries = library.list_summary()
    if not summaries:
        print(f"No deck files found in {Path(args.deck_dir).resolve()}")
        return 0
    for line in summaries:
        print(line)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    library = DeckLibrary(args.deck_dir)
    try:
        output = library.show(args.name)
    except FileNotFoundError as exc:  # pragma: no cover - user facing
        print(str(exc), file=sys.stderr)
        return 1
    print(output)
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    library = DeckLibrary(args.deck_dir)
    try:
        path = library.create_deck(
            args.name,
            args.commander,
            colors=args.colors,
            theme=args.theme,
            notes=args.notes,
            deck_format=args.deck_format,
            template=args.template,
        )
    except FileExistsError as exc:  # pragma: no cover - user facing
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Created deck at {path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    if not args.card_text and not args.card_file:
        print("Provide --cards or --file with card entries", file=sys.stderr)
        return 2

    try:
        card_source: str | Path
        if args.card_text:
            card_source = args.card_text
        else:
            card_source = Path(args.card_file)

        library = DeckLibrary(args.deck_dir)
        result = library.import_deck(
            args.name,
            args.commander,
            card_source=card_source,
            colors=args.colors,
            theme=args.theme,
            notes=args.notes,
            deck_format=args.deck_format,
            overwrite=args.overwrite,
        )
    except FileExistsError as exc:  # pragma: no cover - user facing
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - user facing
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Imported deck to {result.path}")
    if result.warnings:
        print("Warnings:")
        for line in result.warnings:
            print(f"- {line}")
    return 0


def cmd_value(args: argparse.Namespace) -> int:
    library = DeckLibrary(args.deck_dir)
    try:
        valuation = library.value_deck(args.name, currency=args.currency)
    except FileNotFoundError as exc:  # pragma: no cover - user facing
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - user facing
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Total value ({args.currency.upper()}): {valuation.formatted_total()}")
    if valuation.missing_prices:
        print("Missing prices for:")
        for name in sorted(valuation.missing_prices):
            print(f"- {name}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    rules = CommanderRules(
        deck_size=args.deck_size,
        expected_format=args.expected_format,
        allow_duplicate_basics=not args.no_duplicate_basics,
        require_commander_tag=not args.allow_missing_commander_tag,
        max_commander_entries=args.max_commanders,
        banned_cards=set(args.banned_cards),
    )

    library = DeckLibrary(args.deck_dir)
    errors = library.validate_decks(log_path=args.log_path, rules=rules)
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1

    print("All decks valid.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
