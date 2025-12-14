# MTG-Decks

A tiny Python-powered library and CLI for storing Commander decks as Markdown. Decks live as
front-matter driven `.md` files so you can version them, lint them, and keep them readable in any editor.

## Highlights
- **CLI and library**: list, show, create, import, and price decks via `mtg-decks` or Python.
- **Commander rules**: validate 100-card singleton construction (with configurable partners/tags/bans).
- **Importer**: fuzzy matches messy CSV or inline entries against Scryfall and fills out decklists for you.
- **Valuation**: totals deck prices with configurable currencies and reports missing price data.
- **Templating**: render Markdown bodies from your own templates when creating or importing decks.

## Installation
```bash
pip install -e .
```
By default the CLI looks for decks in `./decks`. Point to another directory with `--dir /path/to/decks` on any command.

## Quick start (CLI)
```bash
mtg-decks list
mtg-decks show "The Ur-Dragon, Eternal Sky Tyrant"
mtg-decks create "Atraxa Superfriends" "Atraxa, Praetors' Voice" --colors W U B G --theme "Superfriends control"
mtg-decks import "Messy Deck" "Atraxa, Praetors' Voice" --cards $'2 sol rng\n1 arcane signet'
mtg-decks value "The Ur-Dragon, Eternal Sky Tyrant" --currency gbp
```
Typical `list` and `show` output:
```
The Ur-Dragon, Eternal Sky Tyrant (W, U, B, R, G) :: Commander: The Ur-Dragon

The Ur-Dragon, Eternal Sky Tyrant
Commander: The Ur-Dragon
Colors: W, U, B, R, G
Format: Commander
Created: 2024-06-21
```

## CLI commands
| Command | What it does |
| --- | --- |
| `mtg-decks list` | Show a one-line summary of each deck in the target directory. |
| `mtg-decks show <name-or-slug>` | Print commander, colors, theme, format, and dates for a single deck. |
| `mtg-decks create <name> <commander> [--colors ...] [--theme ...] [--notes ...] [--format ...] [--template path]` | Write a new Markdown deck with optional templated body content. Fails if the file already exists. |
| `mtg-decks import <name> <commander> --cards <text> | --file <csv>` | Fuzzy-match card entries against Scryfall, generate a decklist, and write/update a Markdown file (use `--overwrite` to replace an existing file). |
| `mtg-decks value <name-or-slug> [--currency GBP]` | Sum card prices via Scryfall price fields (`gbp`, `usd`, `eur`, etc.) and report missing values. |
| `mtg-decks validate [--log validation.log] [--deck-size 100] [--ban CARD]...` | Validate deck files against Commander rules and optionally write a fresh log file on each run. |

Add `--dir PATH` to any command to work against a different deck folder. Check the tool version with `mtg-decks --version`.

## Deck file layout
Decks use YAML-style front matter followed by Markdown content. A minimal example:
```markdown
---
name: Atraxa Superfriends
commander: Atraxa, Praetors' Voice
colors: W, U, B, G
theme: Superfriends control
format: Commander
created: 2024-06-21
notes: Lean into planeswalkers and proliferate engines.
---

# Atraxa Superfriends

**Commander:** Atraxa, Praetors' Voice
**Theme:** Superfriends control
**Colors:** W, U, B, G
**Format:** Commander

## Decklist
- [Commander] Atraxa, Praetors' Voice
- Teferi, Temporal Archmage
- Oko, Thief of Crowns
- Smothering Tithe
- Doubling Season
```

### Filenames and slugs
- Filenames are derived from deck names (e.g., `"Atraxa Superfriends"` → `atraxa-superfriends.md`).
- Use names or slugs interchangeably with the CLI (`mtg-decks show atraxa-superfriends`).

## Validation and rules
Use `CommanderRules` to enforce construction rules such as 100 cards, singleton enforcement, mandatory commander tags, and banned cards.
```python
from mtg_decks import CommanderRules, DeckLibrary

library = DeckLibrary("decks")
errors = library.validate_decks(
    rules=CommanderRules(
        require_commander_tag=True,
        max_commander_entries=2,  # allow partners/backgrounds
        banned_cards={"Black Lotus", "Ancestral Recall"},
    ),
    log_path="validation.log",
)
```
Notes:
- Logs are overwritten on every run so you always see the latest results.
- Validation parses the `## Decklist` section and flags wrong counts, duplicate non-basics, banned cards, or missing commanders.
- Run the same checks from the CLI with optional overrides: `mtg-decks validate --deck-size 3 --max-commanders 2 --ban "Black Lotus" --log validation.log`

## Importing rough decklists
Quickly bootstrap decks from messy sources by letting the importer normalize entries:
```bash
mtg-decks import "Uploaded Deck" "The Ur-Dragon" --file cards.csv --overwrite
# or
mtg-decks import "Uploaded Deck" "The Ur-Dragon" --cards $'2 sol rng\n1 arcane signet' --theme "Big dragons"
```
Behavior and tips:
- Accepts CSV rows (`quantity,name`) or newline-separated text (`2 Sol Ring`).
- Uses Scryfall's fuzzy matcher to clean up names; falls back to your input when lookups fail.
- Infers colors from the commander unless `--colors` is supplied.
- You can enforce `CommanderRules` during import from Python:
  ```python
  from pathlib import Path
  from mtg_decks import CommanderRules, DeckLibrary

  library = DeckLibrary("decks")
  result = library.import_deck(
      "Uploaded Deck",
      "The Ur-Dragon",
      card_source=Path("cards.csv"),
      rules=CommanderRules(),
      overwrite=True,
  )
  print(result.path, result.warnings)
  ```
- Network access is required for live Scryfall lookups; tests and offline usage can inject a custom resolver.

## Valuing decks
Estimate deck value from Scryfall price fields:
```bash
mtg-decks value "The Ur-Dragon, Eternal Sky Tyrant" --currency gbp
```
From Python, reuse the same logic and control the currency or resolver:
```python
from mtg_decks import DeckLibrary

library = DeckLibrary("decks")
valuation = library.value_deck("The Ur-Dragon, Eternal Sky Tyrant", currency="usd")
print(valuation.total, valuation.formatted_total())
print("Missing prices:", valuation.missing_prices)
```
`--currency`/`currency` should match a Scryfall price key (`gbp`, `usd`, `eur`, etc.). Missing prices are reported separately so you know which cards need manual prices.

## Templates and customization
`create` and `import` accept `--template path/to/template.md` to render the body with placeholders like `{name}`, `{commander}`, `{colors}`, `{format}`, `{created}`, and `{notes}`. Store templates alongside your decks or in a dedicated folder for reuse.

## Operational considerations
- **Rate limits and retries**: Scryfall asks clients to respect a modest rate limit. If you script bulk imports or valuation, add backoff/retry logic and consider caching responses on disk so repeated runs do not re-fetch the same card data.
- **Offline workflows**: The importer and valuer accept custom resolvers; plug in a local cache or fixture data when traveling or running CI without internet access so commands keep working.
- **Change control**: Treat `decks/` like source code—review diffs of generated Markdown, keep validation logs in CI artifacts, and run `pytest` on pull requests to catch rule violations before merging.
- **Data provenance**: When fuzzy matching card names, keep the original CSV/text around for auditability and note any resolver warnings in commit messages or deck notes so you remember which entries were guesses.

## Developing and testing
- Run the test suite: `PYTHONPATH=src pytest`
- If you are stubbing network calls, pass a custom resolver to importer/valuer helpers in your tests.

## Working with git remotes
This repository does not include a default `origin` remote. Add one if you plan to push:
```bash
git remote add origin <your-repo-url>
git fetch origin
```

Happy brewing!
