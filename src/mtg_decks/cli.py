from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .library import DeckLibrary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Store and review Commander decks as Markdown files."
    )
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
    create_parser.set_defaults(func=cmd_create)

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
        )
    except FileExistsError as exc:  # pragma: no cover - user facing
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Created deck at {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
