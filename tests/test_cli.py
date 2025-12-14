from pathlib import Path

import pytest

from mtg_decks import __version__, cli
from mtg_decks import importer as importer_module
from mtg_decks import valuation as valuation_module
from mtg_decks.library import DeckLibrary
from mtg_decks.valuation import DeckValuation


@pytest.fixture()
def deck_dir(tmp_path: Path) -> Path:
    return tmp_path / "decks"


@pytest.fixture(autouse=True)
def fast_resolver(monkeypatch: pytest.MonkeyPatch):
    class FastResolver(importer_module.CardResolver):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def resolve(self, query: str):
            self.calls.append(query)
            return importer_module.CardData(
                name=query,
                prices={"usd": "0.01", "gbp": "0.01"},
                type_line="Artifact",
                cmc=1,
            )

    resolver = FastResolver()
    monkeypatch.setattr(importer_module, "ScryfallResolver", lambda: resolver)
    monkeypatch.setattr(cli, "ScryfallResolver", lambda: resolver)
    monkeypatch.setattr(valuation_module, "ScryfallResolver", lambda: resolver)
    return resolver


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
                "Cloud": importer_module.CardData(
                    name="Cloud, Ex-SOLDIER", color_identity=["W", "U", "B", "G"]
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
            "Cloud",
            "--file",
            str(card_file),
        ]
    )

    assert exit_code == 0
    created = deck_dir / "imported-deck.md"
    assert created.exists()


class StubResolver(importer_module.CardResolver):
    def __init__(self, prices: dict[str, str]):
        self.calls: list[str] = []
        self.prices = prices

    def resolve(self, query: str):
        self.calls.append(query)
        return importer_module.CardData(
            name=query,
            prices=self.prices,
            type_line="Artifact",
            cmc=2,
        )


def _write_simple_deck(deck_dir: Path, name: str, card_lines: list[str] | None = None) -> Path:
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck_path = deck_dir / f"{name}.md"
    card_lines = card_lines or [
        "- [Commander] Captain {name}",
        "- Sol Ring",
        "- Arcane Signet",
    ]
    rendered_cards = "\n".join(card_lines).format(name=name)
    deck_path.write_text(
        f"""
        ---
        name: {name}
        commander: Captain {name}
        format: Commander
        ---

        ## Decklist
        {rendered_cards}
        """
        .strip()
        + "\n",
        encoding="utf-8",
    )
    return deck_path


def test_cli_value_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    deck_dir = tmp_path / "decks"
    _write_simple_deck(deck_dir, "valued")

    stub_resolver = StubResolver({"usd": "1.00"})
    monkeypatch.setattr(cli, "ScryfallResolver", lambda: stub_resolver)

    report_path = tmp_path / "report.md"
    exit_code = cli.main(
        [
            "--dir",
            str(deck_dir),
            "value-all",
            "--currency",
            "usd",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "valued" in output.lower()
    assert report_path.exists()

    single_exit = cli.main(
        ["--dir", str(deck_dir), "value", "valued", "--currency", "usd"]
    )
    assert single_exit == 0
    single_output = capsys.readouterr().out
    assert "Total value" in single_output


def test_cli_validate_and_spares(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    deck_dir = tmp_path / "decks"
    _write_simple_deck(deck_dir, "valid")

    validate_exit = cli.main(
        ["--dir", str(deck_dir), "validate", "--deck-size", "3", "--expected-format", "Commander"]
    )
    assert validate_exit == 0
    assert "All decks valid" in capsys.readouterr().out

    stub_resolver = StubResolver({"usd": "2.50"})
    monkeypatch.setattr(cli, "ScryfallResolver", lambda: stub_resolver)

    spares_file = tmp_path / "spares.md"
    import_exit = cli.main(
        [
            "spares",
            "import",
            "--spares-file",
            str(spares_file),
            "--cards",
            "3 Sol Ring\n1 Arcane Signet",
            "--box",
            "A1",
            "--currency",
            "usd",
            "--sort",
            "value",
        ]
    )
    assert import_exit == 0
    import_output = capsys.readouterr().out
    assert "Updated inventory" in import_output

    search_exit = cli.main(
        [
            "spares",
            "search",
            "--spares-file",
            str(spares_file),
            "--sort",
            "value",
            "--currency",
            "usd",
        ]
    )
    assert search_exit == 0
    search_output = capsys.readouterr().out
    assert "| Name |" in search_output
    assert "Sol Ring" in search_output


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

    def fake_value_deck(name_or_slug: str, *, currency: str, resolver=None, cache=None):
        assert currency.lower() == "gbp"
        return FakeValuation()

    monkeypatch.setattr(DeckLibrary, "value_deck", staticmethod(fake_value_deck))

    exit_code = cli.main(["--dir", str(deck_dir), "value", "valued", "--currency", "GBP"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Total value (GBP): £10.00" in output
    assert "Arcane Signet" in output


def test_cli_value_all_writes_report_and_prints_totals(
    deck_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    deck_dir.mkdir(parents=True, exist_ok=True)
    report_path = tmp_path / "valuation-report.md"

    valuations = {
        "Alpha": DeckValuation(currency="gbp", total=10.0, missing_prices=[]),
        "Bravo": DeckValuation(currency="gbp", total=0.0, missing_prices=["Unknown Card"]),
    }

    def fake_value_all(self, *, currency: str, resolver=None, cache=None, now=None):
        assert currency.lower() == "gbp"
        return valuations

    monkeypatch.setattr(DeckLibrary, "value_all", fake_value_all)

    exit_code = cli.main(
        [
            "--dir",
            str(deck_dir),
            "value-all",
            "--currency",
            "GBP",
            "--report",
            str(report_path),
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Alpha: £10.00" in output
    assert "Wrote valuation report" in output
    report_text = report_path.read_text(encoding="utf-8")
    assert "As of:" in report_text
    assert "Unknown Card" in report_text


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
