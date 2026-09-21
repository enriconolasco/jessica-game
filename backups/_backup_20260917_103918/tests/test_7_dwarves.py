"""Testes: Os 7 Anões."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, summon_troop, ActionError, SEVEN_DWARVES_COST,
)
from jessica.core.constants import TroopArchetype
from jessica.core.models import Hero
from jessica.core import heroes


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["seven_dwarves"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "Os 7 Anões"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_dwarves_block_troops():
    state = make_state()
    p = state.players[1]
    p.city.gold = 20
    p.city.magic = 10
    try:
        summon_troop(state, 2, TroopArchetype.LIGHT, 4)
        raise AssertionError("Deveria bloquear tropas")
    except ActionError as e:
        print(f"OK  - 7 Anoes bloqueiam tropas: {e}")


def test_summon_first_dwarf():
    state = make_state()
    p = state.players[1]
    p.city.magic = 10
    h = summon_hero(state, 2)
    assert h.hero_id == "dain"
    assert h.life == 1
    print("OK  - 1o anao (dain) invocado")


def test_summon_chain_in_order():
    state = make_state()
    p = state.players[1]
    p.city.magic = 20
    for expected in ["dain", "buin", "bein", "boin", "tintin", "don", "din"]:
        h = summon_hero(state, 2)
        assert h.hero_id == expected, f"Esperado {expected}, veio {h.hero_id}"
    print("OK  - Corrente completa dos 7 anoes invocada em ordem")


def test_chain_requires_prev_alive():
    state = make_state()
    p = state.players[1]
    p.city.magic = 20
    summon_hero(state, 2)  # dain
    # Mata dain
    dain = next(u for u in p.units if isinstance(u, Hero) and u.hero_id == "dain")
    dain.life = 0
    p.units = [u for u in p.units if u.is_alive()]
    # Tenta invocar buin: deveria falhar
    try:
        summon_hero(state, 2)
        raise AssertionError("Deveria bloquear sem dain vivo")
    except ActionError as e:
        print(f"OK  - Corrente bloqueia sem anao anterior: {e}")


def test_cost_is_2_magic():
    state = make_state()
    p = state.players[1]
    p.city.magic = 5
    summon_hero(state, 2)  # anões são -0 (não é orc)
    assert p.city.magic == 3
    print("OK  - Cada anao custa 2 magia")


def run_all():
    tests = [
        test_dwarves_block_troops,
        test_summon_first_dwarf,
        test_summon_chain_in_order,
        test_chain_requires_prev_alive,
        test_cost_is_2_magic,
    ]
    print("=== Testes 7 Anoes ===\n")
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
