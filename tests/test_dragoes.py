"""Testes das regras estruturais dos Dragoes."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (cast_spell, summon_hero, purpura_invisibilidade,
                                  valtherion_chamado)
from jessica.core.constants import TroopArchetype
from jessica.core.peoples import dragon_base, apply_dragon_turn_start
from jessica.core.serialize import state_to_dict, state_from_dict


def make_state(hero="purpura"):
    state, _ = run_setup(
        all_peoples=["dragoes", "humanos", "orcs", "fadas"],
        heroes_by_people={"dragoes": [hero], "humanos": ["miyamoto"],
                           "orcs": ["arken"], "fadas": ["ainai"]},
        choices={1: {"povo": "dragoes", "heroi": hero},
                 2: {"povo": "humanos", "heroi": "miyamoto"},
                 3: {"povo": "orcs", "heroi": "arken"},
                 4: {"povo": "fadas", "heroi": "ainai"}}, seed=51)
    return state


def test_canastra_add_remove_and_queen():
    state = make_state()
    p = state.players[0]
    p.city.magic = 20
    hero = summon_hero(state, 1)
    p.hand = ["Q_H"]
    cast_spell(state, 1, {"action": "add", "card_id": "Q_H"})
    assert hero.life_max == 5 and hero.life == 5 and p.canastra == ["Q_H"]
    cast_spell(state, 1, {"action": "remove", "card_id": "Q_H"})
    assert hero.life_max == 3 and hero.life == 5 and "Q_H" in p.hand


def test_suits_and_jack_reward():
    state = make_state()
    p = state.players[0]
    p.city.magic = 20
    hero = summon_hero(state, 1)
    p.hand = ["J_H", "J_D", "J_C"]
    gold = p.city.gold
    cast_spell(state, 1, {"action": "add", "card_id": "J_H"})
    assert p.city.gold == gold + 1 and hero.resistance_stacks == 1
    cast_spell(state, 1, {"action": "add", "card_id": "J_D"})
    assert p.city.gold == gold + 3 and p.spell_cooldown_until_turn == state.turn + 2


def test_purpura_growth_invisibility_and_save():
    state = make_state()
    state.turn = 4
    p = state.players[0]
    p.city.magic = 20
    hero = summon_hero(state, 1)
    assert hero.life_max == 5
    purpura_invisibilidade(state, 1)
    assert hero.statuses["purpura_cooldown_until_turn"] == 6
    restored = state_from_dict(state_to_dict(state))
    assert restored.players[0].units[0].life_max == 5


def test_moving_bases_and_chamado():
    state = make_state("valtherion")
    p = state.players[0]
    base = dragon_base(p)
    assert base is not None and p.city.life == base.life == 20
    p.hand = ["J_H", "Q_D", "K_C"]
    troop = valtherion_chamado(state, 1, TroopArchetype.DRAGON_LIGHT)
    assert troop.life == 3 and troop.life_max == 4 and troop.house == base.house


def test_king_morning_and_club_move():
    state = make_state()
    p = state.players[0]
    p.city.magic = 20
    hero = summon_hero(state, 1)
    p.canastra = ["K_D", "J_C"]
    magic = p.city.magic
    apply_dragon_turn_start(state)
    assert p.city.magic == magic + 1 and hero.max_moves_this_turn == 2


def run_all():
    tests = [test_canastra_add_remove_and_queen, test_suits_and_jack_reward,
             test_purpura_growth_invisibility_and_save, test_moving_bases_and_chamado,
             test_king_morning_and_club_move]
    passed = failed = 0
    for test in tests:
        try:
            test(); passed += 1
        except Exception as exc:
            failed += 1
            print(f"FALHOU - {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")


if __name__ == "__main__":
    run_all()
