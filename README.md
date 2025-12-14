# MTG-Decks

A tiny Python-powered library for storing and reviewing your Commander decks as Markdown files. Each deck lives in its own `.md` file with lightweight front matter, making it easy to track colors, themes, commanders, and notes.

## Quick start
1. Install the project in editable mode so you can use the CLI:
   ```bash
   pip install -e .
   ```
2. List existing deck files (by default they live in `./decks`):
   ```bash
   mtg-decks list
   ```
3. Show details for a specific deck using its name or slug:
   ```bash
   mtg-decks show "The Ur-Dragon, Eternal Sky Tyrant"
   ```
4. Create a new deck file from the CLI:
   ```bash
   mtg-decks create "Atraxa Superfriends" "Atraxa, Praetors' Voice" --colors W U B G --theme "Superfriends control"
   ```

## Deck file layout
Decks are regular Markdown files with a YAML-style front matter block. For example:

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

## Game Plan
- Develop mana rocks early and deploy planeswalkers on curve.
- Protect the board with counterspells and sweepers.
- Close the game with ultimate abilities and token swarms.

## Decklist
- [Commander] Atraxa, Praetors' Voice
- Teferi, Temporal Archmage
- Oko, Thief of Crowns
- Smothering Tithe
- Doubling Season
- ...add the rest of your list here...
```

## Project structure
- `decks/`: your deck markdown files. A sample `ur-dragon.md` is included to get you started.
- `src/mtg_decks/`: Python helpers and the CLI.
- `tests/`: small unit tests that keep the parser honest.

Happy brewing!
