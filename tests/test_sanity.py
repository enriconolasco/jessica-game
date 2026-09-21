"""Teste de sanidade."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()


def test_imports():
    from jessica.core import (
        constants, models, state, setup, actions, combat,
        turn, victory, serialize, artifacts, artifacts_effects,
        peoples, heroes, spells, rng,
    )
    print("OK  - todos os modulos carregam")


def test_heroes_catalog():
    from jessica.core import heroes
    # 12 base + 7 anoes individuais + 12 novos (vampiros/lobisomens/gigantes/mv)
    assert len(heroes.HERO_CATALOG) == 37, (
        f"Esperado 37 herois, tem {len(heroes.HERO_CATALOG)}"
    )
    for people in ("humanos", "orcs", "fadas", "vampiros", "lobisomens",
                   "gigantes", "mortos_vivos"):
        hs = heroes.heroes_for_people(people)
        assert len(hs) == 3, f"{people} tem {len(hs)} herois escolhiveis, esperado 3"
    anao = heroes.heroes_for_people("anoes")
    assert len(anao) == 3, f"anoes tem {len(anao)} herois escolhiveis, esperado 3"
    print("OK  - 31 herois no catalogo (3 escolhiveis por povo)")


def test_spells_catalog():
    from jessica.core import spells
    assert len(spells.SPELL_CATALOG) == 10, (
        f"Esperado 10 feiticos, tem {len(spells.SPELL_CATALOG)}"
    )
    for people in ("humanos", "anoes", "orcs", "fadas",
                   "vampiros", "lobisomens", "gigantes", "mortos_vivos"):
        sp = spells.spell_for_people(people)
        assert sp is not None, f"{people} sem feitico"
    print("OK  - 8 feiticos, 1 por povo")


def test_setup_runs():
    from jessica.core.setup import run_setup
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["garoche"], "fadas": ["ainai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "garoche"},
            4: {"povo": "fadas", "heroi": "ainai"},
        },
        seed=20260916,
    )
    assert len(state.players) == 4
    print("OK  - setup roda")


def test_unit_has_new_fields():
    from jessica.core.models import Unit
    u = Unit(id="x", owner_id=1, house="center", life=4, life_max=4)
    assert u.attacks_made_this_day == 0
    assert u.statuses == {}
    assert u.moves_this_turn == 0
    assert u.infectado is False
    print("OK  - Unit tem campos novos")


def test_player_has_new_fields():
    from jessica.core.models import Player, City
    c = City(owner_id=1, life=2, life_max=6)
    p = Player(id=1, name="X", people="humanos", city=c)
    assert p.spell_cooldown_until_turn == 0
    assert p.arken_espolia_used_turn == -1
    assert p.besouro_mandinga_used_turn == -1
    assert p.pena_added_once is False
    assert p.carocos_gerados == 0
    assert p.empalados == []
    assert p.infectados == []
    print("OK  - Player tem campos novos")


def run_all():
    tests = [
        test_imports,
        test_heroes_catalog,
        test_spells_catalog,
        test_setup_runs,
        test_unit_has_new_fields,
        test_player_has_new_fields,
    ]
    print("=== Sanidade ===\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
