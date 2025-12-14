# MTG-Decks Functional Specification

## Purpose
MTG-Decks is a Python library and CLI for authoring, validating, importing, valuing, and searching Magic: The Gathering Commander decks stored as Markdown files. It also manages a catalog of spare cards so a collector can see what is available, where it is stored, and how much it is worth. This specification captures the expected behaviors, user flows, and data contracts that guide development and QA.

## Scope and goals
- Preserve decks as front-matter Markdown so they can be versioned, linted, and edited in any tool.
- Offer parity between CLI commands and Python APIs for deck creation, import, validation, valuation, and spare-card inventory management.
- Minimize external dependencies by relying only on Scryfall for card resolution and price data, with facilities for offline or cached operation.
- Keep workflows fast (sub-second for tests and typical commands) and deterministic by isolating filesystem effects to the configured deck and inventory paths.
- Provide predictable flows for organizing physical collections: labeling boxes, merging duplicate entries, and updating counts when cards move between decks and spares.

### Out of scope
- Running in non-Python environments.
- Managing game-play statistics or analytics beyond deck metadata and card lists.
- Real-time synchronization with remote stores (Git remotes are manual).

## Users and primary use cases
- **Deck authors**: Create and edit Commander deck files, import messy lists, and keep prices up to date.
- **Developers**: Script deck operations through the Python API, swap in custom resolvers, and integrate with CI.
- **Organizers/collectors**: Track spare cards and storage boxes, sort by value or CMC, and search inventory quickly.

## Data model
- **Deck file**: Markdown with YAML-like front matter: `name`, `commander`, optional `colors`, `theme`, `format` (default `Commander`), `created`, `updated`, and free-form `notes`. The body may include templated content and a `## Decklist` section with `- [Commander] ...` and card bullets that accept prefixes like `2x` or `2X`. Multiple sections (e.g., `## Ramp`, `## Removal`) are allowed; all list items are parsed as card lines unless explicitly marked as comments.
- **Spares inventory**: Markdown table containing count, name, box label, type line, CMC, unit value, and total value, plus a header storing the preferred currency. Rows represent discrete storage locations; two boxes holding the same card create two rows rather than aggregating.
- **Valuation cache**: JSON keyed by deck name and currency with totals, timestamps, and per-card resolved prices to avoid repeat network lookups within the same calendar month. Cache records include a `source` to identify which resolver produced the data.
- **Reports**: Optional Markdown valuation reports and inventory snapshots saved to disk with a datestamped filename so collection history can be tracked over time.

## Functional requirements
### Deck library
- **Deck discovery**: Load and list `*.md` files from the configured root. Slugs are derived from names (e.g., `My Deck` → `my-deck.md`). Hidden files and non-Markdown files are ignored. A missing directory is treated as empty but never created implicitly.
- **Summaries**: `list` outputs `"Name (colors) — theme :: Commander: <name>"` entries; ordering matches sorted filenames. Colors default to color identity of the commander when absent.
- **Show**: Print name, commander, colors, theme, format, notes, created, and updated fields when present. Show also surfaces counts of main-deck cards, unique card names, and total deck value if a cache entry exists.

### Deck creation
- Inputs: deck name, commander, optional colors/theme/notes/format, and optional body template path.
- Behavior: Fail if the target slug already exists. If a template path is provided, require it to exist. Write a new Markdown deck with populated front matter and optional templated body; `created` defaults to today’s ISO date. `updated` remains unset until the deck is modified by later commands.
- Metadata validation: Commander and name must be non-empty strings; colors accept the characters `WUBRGC` and are normalized to uppercase sorted order.
- Template substitution: Templates can include front-matter placeholders and a `{decklist}` marker. When no decklist placeholder is present, a `## Decklist` heading followed by the commander line is appended automatically.

### Deck import
- Inputs: deck name, commander, and card source as free-form text, inline CSV, or file path; optional colors/theme/notes/format; optional overwrite flag; optional validation rules and resolver.
- Parsing: Accept header rows like `Count,Name` or `Name,Count`; recognize counts with `x` suffixes; default counts to `1` when missing. Sideboard or maybeboard markers such as `SB:` or `Maybe:` are ignored rather than written.
- Resolution: Use Scryfall fuzzy matching by default. Normalize commander and card names; warn when lookups fail or names change. Infer colors from commander color identity when not supplied. Double-faced and split cards are stored under their front face name while retaining the card’s color identity and CMC from the resolver.
- Output: Write a Markdown deck containing the commander plus normalized cards (excluding commander duplicates). Decklist entries are sorted alphabetically by name, with counts preserved. If rules are supplied and violations occur, delete the written file and raise a validation error.
- Overwrite protection: Reject writes when a deck already exists unless `overwrite=True`.
- Post-processing: Set `updated` to today’s date after successful import. Optionally emit a valuation report immediately when `--value-after` is supplied.

### Deck validation
- Inputs: optional Commander ruleset (deck size, singleton enforcement, commander tagging, banned cards, partner/background allowances, etc.) and optional log path.
- Behavior: Parse each decklist, validate per rules, and collect errors. Write a fresh log file on every run when `log_path` is provided. Return a list of issues; include parsing failures and missing required metadata.
- Supported rules: enforce 100-card size (or custom target), allow up to two commanders when partner/background rules permit, flag duplicates outside the commander zone, and block banned-card names (case-insensitive). Logs include file path, line numbers, and suggested fixes.
- Exit conditions: Validation returns a non-zero exit code when any error is present so CI can fail fast.

### Valuation
- Inputs: deck name or slug (or all decks), currency (defaults to `gbp`), optional resolver, optional cache, optional clock override.
- Behavior: Parse decklists, resolve prices, and total values while reporting cards with missing prices. Cache lookups per deck/currency/month when provided. `value-all` returns a mapping of deck names to valuations and updates the cache once at the end.
- Pricing rules: Use market prices by default; fallback to `0` for missing prices while emitting warnings. Totals reflect `count * unit_price` per card and sum across main deck only (commander included).
- Reports: CLI supports generating Markdown valuation reports that can be committed over time. Reports include per-card line items sorted by descending unit price, deck subtotal, missing-price list, timestamp, and resolver identity. Re-running on the same day replaces the previous report for that day.
- Cache invalidation: Cache entries expire after a calendar month rollover or when invoked with `--refresh-cache`, forcing fresh lookups.

### Spares inventory
- **Import**: Accept card text or CSV with an associated `--box` label; normalize counts and names through the resolver; price entries; merge with existing inventory; and rewrite the Markdown table sorted by name, value, or CMC. Missing prices are flagged but do not halt processing. When merging, rows with identical normalized names and box labels are collapsed by summing counts and recomputing total value.
- **Transfer between boxes**: Support a `--move` mode that decrements counts from one box and increments another, deleting rows whose counts reach zero so the inventory always reflects physical storage.
- **De-duping with decks**: An optional `--sync-decks` flag can subtract deck contents from the spare pool to show only true extras, using the same resolver normalization to avoid mismatches.
- **Search**: Filter inventory by query text and/or box label and order results by name, value, or CMC. Output includes counts, boxes, type lines, and pricing details. Query text matches against name and type line with case-insensitive substring logic. Empty results return a friendly "no matches" message rather than failing.
- **Snapshots and audit**: `spares export` writes the current table to CSV for spreadsheets. `spares report` generates a Markdown summary with totals per box, top 10 most valuable cards, and collection grand total. Both commands respect the current resolver and currency settings.

### Templates and customization
- Body templates for `create` and `import` accept placeholders `{name}`, `{commander}`, `{colors}`, `{format}`, `{created}`, and `{notes}`. Templates may live alongside decks or in any specified path.
- Custom resolvers can replace Scryfall for offline or cached operation; callers supply them to importer or valuer helpers.

### CLI surface
| Command | Purpose | Key options |
| --- | --- | --- |
| `mtg-decks list` | Print one-line summaries for each deck in the target directory. | `--dir` to target another folder. |
| `mtg-decks show <name-or-slug>` | Display metadata for a single deck. | `--dir` |
| `mtg-decks create <name> <commander>` | Create a new deck file. | `--colors`, `--theme`, `--notes`, `--format`, `--template`, `--dir` |
| `mtg-decks import <name> <commander>` | Import a deck from text or CSV. | `--cards` or `--file`, `--colors`, `--theme`, `--notes`, `--format`, `--overwrite`, `--dir`, `--value-after` |
| `mtg-decks validate` | Validate all decks in the directory. | `--log`, `--deck-size`, `--ban`, partner/background toggles, `--dir` |
| `mtg-decks value <name-or-slug>` | Price a single deck. | `--currency`, resolver flags, `--dir`, cache path env var, `--refresh-cache` |
| `mtg-decks value-all` | Price every deck and optionally emit a report. | `--currency`, `--report`, resolver flags, `--dir`, `--refresh-cache` |
| `mtg-decks spares import` | Add spare cards to the inventory and price them. | `--box`, `--cards` or `--file`, `--sort`, `--spares-file`, `--currency` |
| `mtg-decks spares move` | Move spares between boxes. | `--from`, `--to`, `--cards` or `--file`, `--spares-file`, `--currency` |
| `mtg-decks spares search` | Query spare cards by text/box with sorting. | `--query`, `--box`, `--sort`, `--spares-file`, `--currency` |
| `mtg-decks spares export` | Save the spare inventory as CSV. | `--spares-file`, `--out` |
| `mtg-decks spares report` | Summarize spare inventory totals. | `--spares-file`, `--currency` |
| `mtg-decks --version` | Show the installed CLI version. | n/a |

### Configuration and environment
- Deck root defaults to `./decks`; override with `--dir` or by passing a custom path to `DeckLibrary`.
- Valuation defaults can be set via environment variables: `MTG_DECKS_CURRENCY`, `MTG_DECKS_VALUATION_SOURCE`, and `MTG_DECKS_VALUATION_CACHE` (can be set in `.env`).
- Resolver base URLs and cache paths are pluggable to support offline or rate-limited contexts.
- Spare inventory path defaults to `./inventory.md` but can be overridden per command. Box labels are free-form strings and are case-sensitive.
- Commands read `.env` when present; environment variables always win over front matter or CLI defaults.

### Error handling
- File-system conflicts (existing deck, missing template) raise explicit exceptions and do not overwrite existing data.
- Failed imports with rule violations remove the partially written deck before surfacing the error.
- Network failures during resolution fall back to user-provided names and record warnings rather than aborting operations unless no cards are supplied.
- Spares operations never reduce counts below zero; attempts to move or subtract more cards than available surface a descriptive error and leave the inventory unchanged.
- Pricing warnings (missing price, stale cache, or resolver errors) are accumulated and printed after command output so users do not miss them.

## Non-functional considerations
- **Performance**: Command execution should complete quickly for typical deck sizes; valuation caches minimize repeat network calls. Spares import of 1,000 cards should complete in under 3 seconds on modern hardware.
- **Determinism**: Validation logs and generated files are rewritten in full on each run to keep diffs meaningful. Inventory tables are rewritten with stable column order and spacing.
- **Testability**: The pytest suite uses temporary directories and fake resolvers; it must run without network access and finish in under a second.
- **Portability**: Uses a pure-Python `src/` layout with editable installs (`pip install -e .`) and no platform-specific dependencies.
- **Auditability**: Reports and logs include timestamps and resolver names so historical valuations can be reconstructed and trusted.

## Acceptance criteria
- All CLI commands and Python APIs described above are available and behave as specified.
- Deck creation, import, validation, valuation, and spares workflows succeed end-to-end using only local files and optional network access for Scryfall.
- Inventory commands can import, move, and report on cards across at least three boxes while keeping counts accurate and prices up to date.
- Tests pass via `pytest` after installing dev dependencies with `pip install -e .[dev]`.
- Documentation (README and this spec) remains consistent with implemented behavior.
