"""Regressões do lote de playtest do terminal."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (summon_hero, move_unit, barba_mar_de_chamas,
                                  barba_combater_como_heroi, barba_resolver_mar_de_chamas)
from jessica.core.constants import Phase
from jessica.core.models import Hero, Troop
from jessica.core import peoples
from jessica.core.serialize import state_to_dict, state_from_dict


def make_state(people="dragoes", hero="barba_negra"):
    state, _ = run_setup(
        all_peoples=[people, "humanos", "orcs", "fadas"],
        heroes_by_people={people: [hero], "humanos": ["miyamoto"],
                          "orcs": ["arken"], "fadas": ["ainai"]},
        choices={1: {"povo": people, "heroi": hero},
                 2: {"povo": "humanos", "heroi": "miyamoto"},
                 3: {"povo": "orcs", "heroi": "arken"},
                 4: {"povo": "fadas", "heroi": "ainai"}}, seed=77)
    return state


def test_barba_prepara_de_dia_e_resolve_de_noite():
    state = make_state()
    barba = peoples.dragon_base(state.players[0])
    assert barba.life == barba.life_max == 3
    enemy = Troop(id="alvo", owner_id=2, house=barba.house, life=2, life_max=4)
    state.players[1].units.append(enemy)
    state.phase = Phase.DAY
    barba_mar_de_chamas(state, 1)
    assert enemy.life == 2
    barba_combater_como_heroi(state, 1)
    assert barba.statuses["barba_hero_mode_turn"] == state.turn
    state.phase = Phase.NIGHT
    barba_resolver_mar_de_chamas(state)
    assert enemy.life == 1


def test_valtherion_imune_a_infeccao():
    state = make_state(hero="valtherion")
    valtherion = peoples.dragon_base(state.players[0])
    assert not peoples.add_infection(state.players[1], valtherion)
    assert not state.players[1].infectados


def test_belial_cresce_sozinho():
    state = make_state("demonios", "belial")
    demon = state.players[0]
    demon.city.magic = 10
    belial = summon_hero(state, 1)
    before = belial.life_max
    peoples.apply_belial_night_start(state)
    assert belial.life_max == before + 1
    assert belial.life == before + 1


def test_rogue_pacto_e_bonus_persistem():
    state = make_state("demonios", "rogue_devil")
    demon = state.players[0]
    demon.city.magic = 20
    rogue = summon_hero(state, 1)
    assert rogue.life == 0 and demon.demon_pact_offers
    peoples.make_demon_pact(state, 1, 1, "sacrifique_militar", "capa")
    assert rogue.life == rogue.life_max == 1
    restored = state_from_dict(state_to_dict(state))
    owner = restored.players[0]
    assert owner.rogue_life_bonus == 1 and owner.rogue_items == ["capa"]
    owner.units = [u for u in owner.units if not (isinstance(u, Hero)
                                                  and u.hero_id == "rogue_devil")]
    revived = summon_hero(restored, 1)
    assert revived.life == revived.life_max == 1
    assert revived.statuses["rogue_items"] == ["capa"]


def test_rogue_quest_da_vida_ao_firmar_e_ao_cumprir():
    state = make_state("demonios", "rogue_devil")
    demon = state.players[0]
    demon.city.magic = 10
    rogue = summon_hero(state, 1)
    pact = peoples.make_demon_pact(state, 1, 1, "banho_sangue", "adaga")
    assert rogue.life == rogue.life_max == 1
    assert not pact["completed"]
    pact["completed"] = True
    peoples._demon_pact_reward(state, pact)
    assert rogue.life == rogue.life_max == 2


def test_luarado_custa_dois_e_anda_na_lua_ao_invocar():
    state = make_state("lobisomens", "luarado")
    wolf = state.players[0]
    wolf.city.magic = 2
    order = state.turn_order
    state.curuna_id = order[(order.index(1) + 1) % len(order)]
    luarado = summon_hero(state, 1)
    assert wolf.city.magic == 0 and luarado.max_moves_this_turn == 1
    move_unit(state, 1, luarado.id, "center")
    assert luarado.house == "center"


def run_all():
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"FALHOU - {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n=== {passed} passaram, {failed} falharam ===")


if __name__ == "__main__":
    run_all()
