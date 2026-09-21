"""Testes F4a: passivas de Anões e Orcs."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import summon_troop, summon_hero, ActionError
from jessica.core.turn import start_player_day
from jessica.core.constants import TroopArchetype
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["Miyamoto Musashi"],
            "anoes": ["Barbadourada"],
            "orcs": ["Arken"],
            "fadas": ["Ainai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "Miyamoto Musashi"},
            2: {"povo": "anoes", "heroi": "Barbadourada"},
            3: {"povo": "orcs", "heroi": "Arken"},
            4: {"povo": "fadas", "heroi": "Ainai"},
        },
        seed=20260916,
    )
    return state


def test_dwarf_with_no_units_gets_no_gold():
    state = make_state()
    p = state.players[1]
    p.city.gold = 10
    p.morning_done_this_turn = False
    start_player_day(state, 2)
    assert p.city.gold == 10, f"Sem unidades ganhou ouro: {p.city.gold}"
    print("OK  - Anao sem unidades: 0 ouro")


def test_dwarf_gets_gold_per_unit():
    state = make_state()
    p = state.players[1]
    p.city.gold = 100
    p.city.magic = 5
    summon_troop(state, 2, TroopArchetype.LIGHT, 4)
    summon_troop(state, 2, TroopArchetype.MEDIUM, 6)
    p.city.gold = 0
    p.morning_done_this_turn = False
    start_player_day(state, 2)
    assert p.city.gold == 2, f"Esperado 2 ouro (2 tropas), veio {p.city.gold}"
    print("OK  - Anao com 2 tropas: +2 ouro")


def test_orc_pays_less_magic_for_troop():
    state = make_state()
    p = state.players[2]
    p.city.magic = 5
    p.city.gold = 10
    summon_troop(state, 3, TroopArchetype.LIGHT, 4)
    assert p.city.magic == 5, f"Orc gastou magia: {5 - p.city.magic}"
    assert p.city.gold == 6, f"Ouro: esperado 6, veio {p.city.gold}"
    print("OK  - Orc: tropa custa 0 magia")


def test_orc_pays_less_magic_for_hero():
    state = make_state()
    p = state.players[2]
    p.city.magic = 5
    summon_hero(state, 3)
    assert p.city.magic == 3, f"Orc deveria gastar 2, gastou {5 - p.city.magic}"
    print("OK  - Orc: heroi custa 2 magia")


def test_non_orc_pays_full_magic():
    state = make_state()
    p = state.players[0]
    p.city.magic = 5
    p.city.gold = 10
    summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    assert p.city.magic == 4, f"Deveria gastar 1, gastou {5 - p.city.magic}"
    print("OK  - Nao-Orc paga custo cheio")


def test_orc_has_extra_archetype():
    state = make_state()
    p = state.players[2]
    available = peoples.available_archetypes(p)
    extra = [a for a in available if a.value == "extra"]
    assert len(extra) == 1, f"Orc deveria ter extra: {available}"
    print("OK  - Orc tem arquetipo extra")


def test_non_orc_does_not_have_extra():
    state = make_state()
    p = state.players[0]
    available = peoples.available_archetypes(p)
    extra = [a for a in available if a.value == "extra"]
    assert len(extra) == 0, f"Nao-Orc nao deveria ter extra: {available}"
    print("OK  - Nao-Orc nao tem extra")


def test_orc_can_summon_extra_troop():
    state = make_state()
    p = state.players[2]
    p.city.magic = 5
    p.city.gold = 10
    t = summon_troop(state, 3, TroopArchetype.EXTRA, 4)
    assert t.life_max == 4
    print("OK  - Orc invocou tropa extra (4 vida)")


def run_all():
    tests = [
        test_dwarf_with_no_units_gets_no_gold,
        test_dwarf_gets_gold_per_unit,
        test_orc_pays_less_magic_for_troop,
        test_orc_pays_less_magic_for_hero,
        test_non_orc_pays_full_magic,
        test_orc_has_extra_archetype,
        test_non_orc_does_not_have_extra,
        test_orc_can_summon_extra_troop,
    ]
    print("=== Testes peoples F4a ===\n")
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
