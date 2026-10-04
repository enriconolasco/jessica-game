import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json

from jessica.core.heroes import HERO_CATALOG, SEVEN_DWARVES_ORDER
from jessica.core.artifacts import ARTIFACT_CATALOG
from jessica.core.spells import SPELL_CATALOG
from jessica.core.peoples import DEMON_PACTS, ROGUE_ITEMS

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT/"content/world/catalog-v0.1.json").read_text(encoding="utf-8"))


def test_ids_and_approved_places():
    ids = [e["id"] for k in ("places","peoples","heroes","artifacts","items","spells","pacts") for e in CATALOG[k]]
    assert len(ids) == len(set(ids))
    assert {p["name"] for p in CATALOG["places"]} == {"Várzea das Sete Voltas","Sertão da Pedra Miúda"}
    assert all(p["parent_region_id"] is None for p in CATALOG["places"])
    assert not CATALOG["historical_events"] and not CATALOG["world_structure"]["macroregions"]
    assert CATALOG["runtime_integration"] is False


def test_hero_inventory_matches_core_without_lore_invention():
    rows = {h["game_id"]:h for h in CATALOG["heroes"]}
    assert rows.keys() == HERO_CATALOG.keys()
    for hid, hero in HERO_CATALOG.items():
        row = rows[hid]
        assert (row["name"],row["people_id"],row["mechanical_reference"]["base_life"]) == (hero.name,hero.people,hero.life)
        assert row["mechanical_reference"]["ability_keys"] == list(hero.abilities)
        assert row["lore"]["personality"] is None and row["lore"]["biography"] is None
        assert row["lore"]["home_place_id"] is None
    assert rows["seven_dwarves"]["entry_kind"] == "group_option"
    assert {k for k,v in rows.items() if v["entry_kind"] == "individual_dwarf"} == set(SEVEN_DWARVES_ORDER)
    assert all(rows[k]["entry_kind"] == "summoned_during_match" for k in ("cobra","zoia","cova_rasa"))


def test_artifacts_spells_items_and_pacts_cover_current_definitions():
    artifacts = {a["game_id"]:a for a in CATALOG["artifacts"]}
    assert artifacts.keys() == ARTIFACT_CATALOG.keys()
    for aid, artifact in ARTIFACT_CATALOG.items():
        assert artifacts[aid]["name"] == artifact.name
        assert artifacts[aid]["mechanical_reference"]["declared_effect"] == artifact.description
        assert artifacts[aid]["lore"]["creator"] is None
    spells = {s["game_id"]:s for s in CATALOG["spells"]}
    assert spells.keys() == SPELL_CATALOG.keys()
    assert all(spells[k]["name"] == s.name for k,s in SPELL_CATALOG.items())
    assert {p["game_id"]:p["name"] for p in CATALOG["pacts"]} == DEMON_PACTS
    assert {i["game_id"] for i in CATALOG["items"]} == set(ROGUE_ITEMS)
    assert all(i["related_hero_id"] == "hero.rogue_devil" for i in CATALOG["items"])


def test_lore_links_and_incomplete_ui_are_explicit():
    peoples = {p["id"] for p in CATALOG["peoples"]}
    assert all(h["people_id"] in peoples for h in CATALOG["heroes"])
    flagged = {h["game_id"] for h in CATALOG["heroes"] if h["verified_runtime_note"]}
    assert flagged == {"miyamoto","vovo_gamba","din","belial","rogue_devil"}
    assert all(h["ui_reference"]["status"] != "confirmed_rule" for h in CATALOG["heroes"])
    reference = CATALOG["unresolved_references"][0]
    assert reference["source_artifact_id"] in {a["id"] for a in CATALOG["artifacts"]}


if __name__ == "__main__":
    passed = failed = 0
    for key, test in list(globals().items()):
        if not key.startswith("test_") or not callable(test): continue
        try: test(); passed += 1
        except Exception as error:
            print(f"FALHOU {key}: {error}"); failed += 1
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(bool(failed))
