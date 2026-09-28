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


def test_valtherion_rejeita_controle_mas_aceita_rei_de_paus():
    from jessica.core.actions import play_artifact
    state = make_state(hero="valtherion")
    owner, enemy = state.players[:2]
    valtherion = peoples.dragon_base(owner)
    owner.hand = ["K_C"]
    play_artifact(state, owner.id, "K_C", choice={"unit_id": valtherion.id})
    assert valtherion.double_damage and valtherion.resistance_stacks == 1
    enemy.hand = ["Q_C"]
    try:
        play_artifact(state, enemy.id, "Q_C", choice={"unit_id": valtherion.id})
    except ValueError:
        pass
    else:
        raise AssertionError("Valtherion foi controlado")
    assert valtherion.owner_id == owner.id and "Q_C" in enemy.hand


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


def test_rogue_quest_recompensa_apenas_ao_firmar():
    state = make_state("demonios", "rogue_devil")
    demon = state.players[0]
    demon.city.magic = 10
    rogue = summon_hero(state, 1)
    hand_before = len(demon.hand)
    pact = peoples.make_demon_pact(state, 1, 1, "banho_sangue", "adaga")
    assert rogue.life == rogue.life_max == 1
    assert not pact["completed"]
    assert len(demon.hand) == hand_before + 1
    assert "adaga" in rogue.statuses["rogue_items"]
    pact["completed"] = True
    peoples._demon_pact_reward(state, pact)
    assert rogue.life == rogue.life_max == 1
    assert len(demon.hand) == hand_before + 1


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


def test_cabaca_rola_cada_caroco_uma_vez_por_turno():
    from jessica.core.actions import cast_spell, ActionError
    state = make_state("gigantes", "caroco")
    player = state.players[0]
    player.units = [Hero(id=f"caroco_{i}", owner_id=1, house="center",
                         life=2, life_max=2, hero_id="caroco") for i in range(2)]
    cast_spell(state, 1, {"hero_id": "caroco"})
    assert sum("[ROLL] Cabaca Cheia" in line for line in state.event_log) == 2
    state = state_from_dict(state_to_dict(state))
    before = state_to_dict(state)
    try:
        cast_spell(state, 1, {"hero_id": "caroco"})
    except ActionError:
        pass
    else:
        raise AssertionError("Carocos repetiram rolagens")
    assert state_to_dict(state) == before
    state.players[0].units.append(Hero(id="caroco_novo", owner_id=1, house="center",
                                      life=2, life_max=2, hero_id="caroco"))
    cast_spell(state, 1, {"hero_id": "caroco"})
    assert sum("[ROLL] Cabaca Cheia" in line for line in state.event_log) == 3
    state.turn += 1
    cast_spell(state, 1, {"hero_id": "caroco"})
    assert sum("[ROLL] Cabaca Cheia" in line for line in state.event_log) == 6


def test_log_inclui_partida_inteira_com_separacao_de_turnos():
    from io import StringIO
    from unittest.mock import patch
    from rich.console import Console
    from jessica import main
    state = make_state()
    state.turn = 2
    state.event_log = ["[T1 day] Primeiro jogador coletou 2 Magia.",
                       "[T2 day] Segundo jogador invocou um heroi."]
    output = StringIO()
    with patch.object(main, "console", Console(file=output, width=120, color_system=None)):
        main.show_turn_log(state)
    text = output.getvalue()
    assert "Primeiro jogador coletou" in text and "Segundo jogador invocou" in text
    assert text.index("TURNO 1") < text.index("Primeiro jogador") < text.index("TURNO 2")


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
