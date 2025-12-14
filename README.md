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
The project uses a `src/` layout and is configured for editable installs, so `pip install -e .` will expose the `mtg-decks`
CLI without extra flags. By default the CLI looks for decks in `./decks`. Point to another directory with `--dir /path/to/decks`
on any command.

## Quick start (CLI)
```bash
mtg-decks list
mtg-decks show "Tidus, Yuna's Guardian"
mtg-decks create "Bear Brigade" "Kudo, King Among Bears" --colors W G --theme "Bear tribal tokens"
mtg-decks import "Messy Deck" "Kudo, King Among Bears" --cards $'2 sol rng\n1 arcane signet'
mtg-decks value "Tidus, Yuna's Guardian" --currency gbp
```
Typical `list` and `show` output:
```
Tidus, Yuna's Guardian (W, U, B, R, G) :: Commander: Tidus, Yuna's Guardian

Tidus, Yuna's Guardian
Commander: Tidus, Yuna's Guardian
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
| `mtg-decks spares import --box <label> [--cards text | --file csv] [--sort name|value|cmc]` | Add spare cards to `spares.md`, tagging them with a storage box and pricing them. |
| `mtg-decks spares search [--query text] [--box label] [--sort name|value|cmc]` | Filter and sort spare cards with live pricing so you can find the right box. |

Add `--dir PATH` to any command to work against a different deck folder. Check the tool version with `mtg-decks --version`.

## Deck file layout
Decks use YAML-style front matter followed by Markdown content. A minimal example:
```markdown
---
name: Kudo Bears
commander: Kudo, King Among Bears
colors: W, G
theme: Bear tribal tokens and buffs
format: Commander
created: 2024-07-20
notes: Flood the board with efficient bears and anthem effects.
---

# Kudo Bears

**Commander:** Kudo, King Among Bears
**Theme:** Bear tribal tokens and buffs
**Colors:** W, G
**Format:** Commander

## Decklist
- [Commander] Kudo, King Among Bears
- Ayula, Queen Among Bears
- Bearscape
- Guardian Project
- Kodama's Reach
```

### Filenames and slugs
- Filenames are derived from deck names (e.g., `"Kudo Bears"` → `kudo-bears.md`).
- Use names or slugs interchangeably with the CLI (`mtg-decks show kudo-bears`).

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

## Importing rough decklists
Quickly bootstrap decks from messy sources by letting the importer normalize entries:
```bash
mtg-decks import "Uploaded Deck" "Tidus, Yuna's Guardian" --file cards.csv --overwrite
# or
mtg-decks import "Uploaded Deck" "Tidus, Yuna's Guardian" --cards $'2 sol rng\n1 arcane signet' --theme "Big dragons"
```
How the importer works under the hood:
- Parses newline or CSV rows into `(count, name)` pairs and tolerates suffixes such as `2x`/`3X` when they lead the entry.
- Uses Scryfall's fuzzy matcher to normalize commander and card names; falls back to your text when a lookup fails.
- Uses the commander's color identity unless `--colors` is provided.
- Removes explicit commander entries from the decklist so you do not end up with duplicates in the Markdown output.
- Writes a Markdown file in your decks directory using the deck slug (`<deck-name>.md`).
- Optionally enforces `CommanderRules` if you pass `--rules` in Python, deleting the generated file again when validation fails.

Usage tips for adding decks:
- CSVs must be `count,name` and text can be free-form lines like `2 Sol Ring` or `1x Arcane Signet`.
- Pass `--overwrite` if you are re-importing a deck to update an existing file.
- To import from another site such as Moxfield, export the decklist as text or CSV and feed it directly:
  ```bash
  mtg-decks import "<Deck Name>" "<Commander>" --file exported.csv --theme "Copied from Moxfield" --overwrite
  # or, when you copied the decklist into your clipboard, paste it into --cards
  mtg-decks import "<Deck Name>" "<Commander>" --cards "$'<pasted deck text>'"
  ```
Behavior and tips:
- Accepts CSV rows (`quantity,name`) or newline-separated text (`2 Sol Ring`).
- Handles common count suffixes like `2x Sol Ring` or `2X Sol Ring` in addition to bare numbers.
- Uses Scryfall's fuzzy matcher to clean up names; falls back to your input when lookups fail.
- Infers colors from the commander unless `--colors` is supplied.
- You can enforce `CommanderRules` during import from Python:
  ```python
  from pathlib import Path
  from mtg_decks import CommanderRules, DeckLibrary

  library = DeckLibrary("decks")
  result = library.import_deck(
      "Uploaded Deck",
      "Tidus, Yuna's Guardian",
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
mtg-decks value "Tidus, Yuna's Guardian" --currency gbp
```
From Python, reuse the same logic and control the currency or resolver:
```python
from mtg_decks import DeckLibrary

library = DeckLibrary("decks")
valuation = library.value_deck("Tidus, Yuna's Guardian", currency="usd")
print(valuation.total, valuation.formatted_total())
print("Missing prices:", valuation.missing_prices)
```
`--currency`/`currency` should match a Scryfall price key (`gbp`, `usd`, `eur`, etc.). Missing prices are reported separately so you know which cards need manual prices.

Valuations are cached in `valuation-cache.json` (configurable) so repeat runs only fetch prices when a deck has never been
valued or its last valuation is from a previous calendar month. Cache hits keep network traffic low when you are checking
prices frequently.

To track how totals change over time, run a batch valuation and write a timestamped Markdown report:
```bash
PYTHONPATH=src mtg-decks value-all --currency usd --report valuation-report.md
```
Commit or archive each `valuation-report.md` snapshot so you can diff how deck prices move between runs.
Use `--source` (or `MTG_DECKS_VALUATION_SOURCE`) to pick the price provider; `scryfall` is supported today.

## Tracking spare cards and storage boxes
Catalog extra cards alongside your decks to keep box locations and valuations in sync. The `spares` command writes a Markdown inventory (`spares.md` by default) and lets you search or sort it.

Import cards from a CSV or pasted text while tagging the storage box:
```bash
mtg-decks spares import --box "Staples" --cards $'2 Sol Ring\n1 Arcane Signet'
mtg-decks spares import --box "Cube Box" --file spares.csv --sort value
```
Each run merges counts with existing entries, prices the cards, and rewrites `spares.md` with a table that includes count, box, type line, converted mana cost, and both unit and total value.
CSV rows can be `Count,Name` or `Name,Count`, and optional header rows (e.g., `Count,Name`) are ignored.

Search the inventory with filters and sorting:
```bash
mtg-decks spares search --query artifact --sort value
mtg-decks spares search --box "Staples" --box "Cube Box" --sort cmc
```
Search matches names, type lines, and box labels, and you can order results by name, total value, or CMC. Missing prices are called out so you know which cards need manual values.

Inventory path tips:
- Pass `--spares-file inventory.md` (or another path) to reuse an existing Markdown ledger.
- The tool preserves your currency preference in the file header and rewrites the table with updated prices on every import.

### Configuring valuation defaults
- `MTG_DECKS_CURRENCY`: default pricing currency (e.g., `USD`, `EUR`, `GBP`).
- `MTG_DECKS_VALUATION_SOURCE`: preferred price source (defaults to `scryfall`).
- `MTG_DECKS_VALUATION_CACHE`: path to the valuation cache file (defaults to `valuation-cache.json`).

You can set these as environment variables or create a simple `.env` file next to the CLI entrypoint (copy `.env.example` to
get started):

```
# .env
MTG_DECKS_CURRENCY=usd
MTG_DECKS_VALUATION_CACHE=.data/valuation-cache.json
```

## Templates and customization
`create` and `import` accept `--template path/to/template.md` to render the body with placeholders like `{name}`, `{commander}`, `{colors}`, `{format}`, `{created}`, and `{notes}`. Store templates alongside your decks or in a dedicated folder for reuse.

## Operational considerations
- **Rate limits and retries**: Scryfall asks clients to respect a modest rate limit. If you script bulk imports or valuation, add backoff/retry logic and consider caching responses on disk so repeated runs do not re-fetch the same card data.
- **Offline workflows**: The importer and valuer accept custom resolvers; plug in a local cache or fixture data when traveling or running CI without internet access so commands keep working.
- **Change control**: Treat `decks/` like source code—review diffs of generated Markdown, keep validation logs in CI artifacts, and run `pytest` on pull requests to catch rule violations before merging.
- **Data provenance**: When fuzzy matching card names, keep the original CSV/text around for auditability and note any resolver warnings in commit messages or deck notes so you remember which entries were guesses.
- **Merge permissions**: List both of your GitHub handles (for this repo: `@jonmossman` and `@jmossman`) in `.github/CODEOWNERS` and enable branch protection that requires code-owner review so only you can approve merges no matter which handle authored the commit.

## Handling merge conflicts
If you pull or merge and see `CONFLICT` messages, it usually means the same deck Markdown or README section changed on both branches.

- Run `git status` to see the conflicted files, then `git diff --merge <file>` to view conflict markers.
- Keep the up-to-date command/validation docs from `README.md` and re-run `PYTHONPATH=src pytest` after fixing conflicts.
- For deck files, ensure the final file still has 100 cards, required commander tags, and valid front matter before committing.

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
