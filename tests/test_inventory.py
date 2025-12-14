from pathlib import Path

from mtg_decks.importer import CardData, CardResolver
from mtg_decks.inventory import SpareCard, SparesInventory, build_spare_cards


class FakeResolver(CardResolver):
    def __init__(self, mapping: dict[str, CardData]):
        self.mapping = mapping

    def resolve(self, query: str):  # pragma: no cover - trivial passthrough
        return self.mapping.get(query)


def test_build_spare_cards_normalizes_names_and_boxes():
    resolver = FakeResolver(
        {
            "sol rng": CardData(
                name="Sol Ring", type_line="Artifact", cmc=1, prices={"gbp": "1.00"}
            )
        }
    )

    cards = build_spare_cards(
        "2, sol rng\n1 Arcane Signet", resolver=resolver, box="Staples"
    )

    assert [card.name for card in cards] == ["Sol Ring", "Arcane Signet"]
    assert [card.count for card in cards] == [2, 1]
    assert all(card.box == "Staples" for card in cards)
    assert cards[0].cmc == 1
    assert cards[0].type_line == "Artifact"
    assert cards[1].cmc is None


def test_inventory_merge_prices_and_write(tmp_path: Path):
    inventory_path = tmp_path / "inventory.md"
    inventory_path.write_text(
        "\n".join(
            [
                "# Spare Card Inventory",
                "",
                "Currency: GBP",
                "",
                "| Name | Count | Box | CMC | Type | Unit Value | Total Value |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| Sol Ring (LOTRs) | 4 | LOTRs | 1 | Artifact | Unknown | Unknown |",
            ]
        ),
        encoding="utf-8",
    )

    resolver = FakeResolver(
        {
            "Sol Ring (LOTRs)": CardData(
                name="Sol Ring (LOTRs)", type_line="Artifact", cmc=1, prices={"gbp": "2"}
            ),
            "Arcane Signet": CardData(
                name="Arcane Signet", type_line="Artifact", cmc=2, prices={"gbp": "1.5"}
            ),
        }
    )

    inventory = SparesInventory(inventory_path)
    entries, missing = inventory.add_cards(
        [
            SpareCard(
                name="Sol Ring (LOTRs)", count=1, box="LOTRs", cmc=1, type_line="Artifact"
            ),
            SpareCard(
                name="Arcane Signet", count=3, box="Binder", cmc=2, type_line="Artifact"
            ),
        ],
        currency="gbp",
        resolver=resolver,
        sort_by="name",
    )

    by_name = {entry.name: (entry, price) for entry, price in entries}
    assert by_name["Sol Ring (LOTRs)"][0].count == 5
    assert by_name["Arcane Signet"][0].count == 3
    assert missing == []

    rendered = inventory_path.read_text(encoding="utf-8")
    assert "| Sol Ring (LOTRs) | 5 | LOTRs | 1 | Artifact | £2.00 | £10.00 |" in rendered
    assert "| Arcane Signet | 3 | Binder | 2 | Artifact | £1.50 | £4.50 |" in rendered


def test_inventory_search_filters_and_sorts(tmp_path: Path):
    resolver = FakeResolver(
        {
            "Arcane Signet": CardData(
                name="Arcane Signet", type_line="Artifact", cmc=2, prices={"gbp": "3"}
            ),
            "Mystic Remora": CardData(
                name="Mystic Remora",
                type_line="Enchantment",
                cmc=1,
                prices={"gbp": "1"},
            ),
        }
    )

    inventory = SparesInventory(tmp_path / "spares.md")
    inventory.add_cards(
        [
            SpareCard(
                name="Arcane Signet", count=1, box="Binder", cmc=2, type_line="Artifact"
            ),
            SpareCard(
                name="Mystic Remora", count=2, box="Binder", cmc=1, type_line="Enchantment"
            ),
        ],
        currency="gbp",
        resolver=resolver,
        sort_by="name",
    )

    entries, missing = inventory.search(
        currency="gbp", resolver=resolver, query="binder", sort_by="value"
    )

    assert missing == []
    assert [entry.name for entry, _ in entries] == [
        "Arcane Signet",
        "Mystic Remora",
    ]

    enchantments, _ = inventory.search(
        currency="gbp", resolver=resolver, query="chant", boxes={"Binder"}
    )
    assert [entry.name for entry, _ in enchantments] == ["Mystic Remora"]


def test_inventory_load_handles_missing_numbers(tmp_path: Path):
    inventory_path = tmp_path / "spares.md"
    inventory_path.write_text(
        "\n".join(
            [
                "# Spare Card Inventory",
                "",
                "Currency: USD",
                "",
                "| Name | Count | Box | CMC | Type | Unit Value | Total Value |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| Sol Ring | unknown | Staples | NaN | Artifact | Unknown | Unknown |",
                "| Island | 5 | Bulk |  | Basic Land | Unknown | Unknown |",
            ]
        ),
        encoding="utf-8",
    )

    inventory = SparesInventory(inventory_path)
    loaded = inventory.load()

    by_name = {entry.name: entry for entry in loaded}
    assert by_name["Sol Ring"].count == 1
    assert by_name["Sol Ring"].cmc is None
    assert by_name["Island"].count == 5
    assert by_name["Island"].cmc is None
    assert by_name["Island"].type_line == "Basic Land"
