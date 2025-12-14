from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mtg_decks.deck import Deck, slugify
from mtg_decks.library import DeckLibrary


class DeckTests(unittest.TestCase):
    def test_slugify_simple(self):
        self.assertEqual(slugify("Atraxa Superfriends"), "atraxa-superfriends")
        self.assertEqual(slugify("  Chaos ! Control  "), "chaos-control")

    def test_round_trip_markdown(self):
        deck = Deck(
            name="Atraxa Superfriends",
            commander="Atraxa, Praetors' Voice",
            colors=["W", "U", "B", "G"],
            theme="Superfriends control",
            notes="Protect your walkers",
        )
        text = deck.to_markdown()
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "atraxa-superfriends.md"
            path.write_text(text, encoding="utf-8")
            loaded = Deck.from_file(path)
            self.assertEqual(loaded.name, deck.name)
            self.assertEqual(loaded.commander, deck.commander)
            self.assertEqual(loaded.colors, deck.colors)
            self.assertEqual(loaded.theme, deck.theme)
            self.assertEqual(loaded.notes, deck.notes)


class LibraryTests(unittest.TestCase):
    def test_create_and_read_deck(self):
        with TemporaryDirectory() as temp_dir:
            library = DeckLibrary(temp_dir)
            path = library.create_deck(
                "Niv-Mizzet Spells", "Niv-Mizzet Reborn", colors=["W", "U", "B", "R", "G"], theme="5c goodstuff"
            )
            self.assertTrue(path.exists())
            loaded = library.read_deck("niv-mizzet-spells")
            self.assertEqual(loaded.commander, "Niv-Mizzet Reborn")
            self.assertIn("niv-mizzet-spells.md", str(path))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
