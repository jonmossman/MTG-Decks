from pathlib import Path

from pathlib import Path

import pytest

from mtg_decks import __version__, cli
from mtg_decks import importer as importer_module
from mtg_decks.library import DeckLibrary


@pytest.fixture()
def deck_dir(tmp_path: Path) -> Path:
    return tmp_path / "decks"


def test_cli_create_then_list_and_show(deck_dir: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = cli.main(
        [
            "--dir",
            str(deck_dir),
            "create",
            "Test Deck",
            "Test Commander",
            "--colors",
            "U",
            "--format",
            "Standard",
        ]
    )
    assert exit_code == 0
    assert (deck_dir / "test-deck.md").exists()

    cli.main(["--dir", str(deck_dir), "list"])
    listed = capsys.readouterr().out
    assert "Test Deck (U) :: Commander: Test Commander" in listed

    cli.main(["--dir", str(deck_dir), "show", "test-deck"])
    shown = capsys.readouterr().out
    assert "Format: Standard" in shown


def test_cli_version_flag(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_cli_create_duplicate_returns_error(deck_dir: Path, capsys: pytest.CaptureFixture[str]):
    cli.main(["--dir", str(deck_dir), "create", "Dup Deck", "Dup Commander"])
    exit_code = cli.main(["--dir", str(deck_dir), "create", "Dup Deck", "Dup Commander"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Deck already exists" in captured.err


def test_cli_create_with_template(deck_dir: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    template = tmp_path / "template.md"
    template.write_text("Commander: {commander}\nNotes: {notes}", encoding="utf-8")

    cli.main(
        [
            "--dir",
            str(deck_dir),
            "create",
            "Template Deck",
            "Template Commander",
            "--notes",
            "Uses a template",
            "--template",
            str(template),
        ]
    )

    created_file = deck_dir / "template-deck.md"
    content = created_file.read_text(encoding="utf-8")
    assert "Commander: Template Commander" in content
    assert "Notes: Uses a template" in content


def test_cli_import_creates_deck_and_reports_warnings(
    deck_dir: Path,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeResolver(importer_module.CardResolver):
        def __init__(self) -> None:
            self.mapping = {
                "sol rng": importer_module.CardData(name="Sol Ring"),
                "Arcane Signet": importer_module.CardData(name="Arcane Signet"),
                "Atraxa": importer_module.CardData(
                    name="Atraxa, Praetors' Voice", color_identity=["W", "U", "B", "G"]
                ),
            }

        def resolve(self, query: str):
            return self.mapping.get(query)

    monkeypatch.setattr(importer_module, "ScryfallResolver", lambda: FakeResolver())

    card_file = tmp_path / "cards.csv"
    card_file.write_text("2, sol rng\nArcane Signet", encoding="utf-8")

    exit_code = cli.main(
        [
            "--dir",
            str(deck_dir),
            "import",
            "Imported Deck",
            "Atraxa",
            "--file",
            str(card_file),
        ]
    )

    assert exit_code == 0
    created = deck_dir / "imported-deck.md"
    assert created.exists()

    output = capsys.readouterr().out
    assert "Imported deck" in output
    assert "Warnings:" in output


def test_cli_value_reports_total_and_missing(
    deck_dir: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck_path = deck_dir / "valued.md"
    deck_path.write_text(
        "\n".join(
            [
                "---",
                "name: Valued Deck",
                "commander: Test Commander",
                "format: Commander",
                "---",
                "",
                "## Decklist",
                "- [Commander] Test Commander",
                "- Sol Ring",
                "- Arcane Signet",
            ]
        ),
        encoding="utf-8",
    )

    class FakeValuation:
        def __init__(self):
            self.currency = "gbp"
            self.missing_prices = ["Arcane Signet"]

        def formatted_total(self) -> str:
            return "£10.00"

    def fake_value_deck(name_or_slug: str, *, currency: str, resolver=None):
        assert currency.lower() == "gbp"
        return FakeValuation()

    monkeypatch.setattr(DeckLibrary, "value_deck", staticmethod(fake_value_deck))

    exit_code = cli.main(["--dir", str(deck_dir), "value", "valued", "--currency", "GBP"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Total value (GBP): £10.00" in output
    assert "Arcane Signet" in output


def test_cli_validate_reports_success_and_writes_log(
    deck_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck = deck_dir / "valid.md"
    deck.write_text(
        "\n".join(
            [
                "---",
                "name: Valid Deck",
                "commander: Test Commander",
                "format: Commander",
                "---",
                "",
                "## Decklist",
                "- [Commander] Test Commander",
                "- Arcane Signet",
            ]
        ),
        encoding="utf-8",
    )

    log_path = tmp_path / "validation.log"
    exit_code = cli.main(
        [
            "--dir",
            str(deck_dir),
            "validate",
            "--deck-size",
            "2",
            "--log",
            str(log_path),
        ]
    )

    assert exit_code == 0
    assert "All decks valid." in capsys.readouterr().out
    assert log_path.read_text(encoding="utf-8").strip() == "All decks valid."


def test_cli_validate_reports_errors_with_rules(deck_dir: Path, capsys: pytest.CaptureFixture[str]):
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck = deck_dir / "invalid.md"
    deck.write_text(
        "\n".join(
            [
                "---",
                "name: Invalid Deck",
                "commander: Test Commander",
                "format: Commander",
                "---",
                "",
                "## Decklist",
                "- [Commander] Not The Commander",
                "- Arcane Signet",
                "- Black Lotus",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = cli.main(
        [
            "--dir",
            str(deck_dir),
            "validate",
            "--deck-size",
            "3",
            "--ban",
            "Black Lotus",
            "--max-commanders",
            "2",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Black Lotus" in captured.err
    assert "Commander 'Test Commander' not marked" in captured.err
