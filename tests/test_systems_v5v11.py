"""Regressoes sistemicas do patch v5v11."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_troop, summon_hero, move_unit, play_artifact, cast_spell, ActionError,
)
from jessica.core.artifacts_effects import on_end_turn
from jessica.core.combat import resolve_attack, Attack, CombatError
from jessica.core.constants import CENTER, Phase, TroopArchetype
from jessica.core.state import snapshot_turn_start_priority, declaration_order_for_house
from jessica.core.serialize import state_to_dict, state_from_dict
from jessica.core.turn import start_turn
from jessica.core import peoples


def make_state(peoples_list=None, heroes=None):
    peoples_list = peoples_list or ["humanos", "anoes", "orcs", "fadas"]
    heroes = heroes or ["miyamoto", "ori", "arken", "ainai"]
    state, _ = run_setup(
        all_peoples=peoples_list,
        heroes_by_people={p: [h] for p, h in zip(peoples_list, heroes)},
        choices={i + 1: {"povo": p, "heroi": heroes[i]}
                 for i, p in enumerate(peoples_list)},
        seed=20260921,
    )
    for p in state.players:
        p.city.gold = 50
        p.city.magic = 50
    return state


def troop(state, pid, life=4, house=CENTER):
    unit = summon_troop(state, pid, TroopArchetype.LIGHT, life)
    unit.house = house
    unit.statuses.pop("summoned_turn", None)
    unit.moves_this_turn = 0
    unit.has_moved_this_turn = False
    return unit


def full_moon(state, pid):
    idx = state.turn_order.index(pid)
    state.curuna_id = state.turn_order[(idx + 1) % len(state.turn_order)]


def test_priority_is_per_player_and_updates_on_entry():
    state = make_state()
    state.turn_order = [1, 2, 3, 4]
    state.curuna_id = 2
    u1 = troop(state, 1)
    u2 = troop(state, 2)
    u2.max_moves_this_turn = 2
    snapshot_turn_start_priority(state)
    assert declaration_order_for_house(state, CENTER) == [2, 1]
    move_unit(state, 2, u2.id, "city_2")
    assert declaration_order_for_house(state, CENTER) == [1]
    move_unit(state, 2, u2.id, CENTER)
    assert declaration_order_for_house(state, CENTER) == [1, 2]
    restored = state_from_dict(state_to_dict(state))
    assert restored.night_priority_by_house[CENTER] == [1, 2]
    assert u1.is_alive()


def test_qc_preserves_actions_and_uses_controller_buffs():
    state = make_state()
    state.phase = Phase.NIGHT
    controlled = troop(state, 2, life=4)
    controlled.moves_this_turn = 1
    controlled.attacks_made_this_night = 1
    state.players[0].hand.extend(["Q_C", "Q_H"])
    play_artifact(state, 1, "Q_H")
    play_artifact(state, 1, "Q_C", choice={"unit_id": controlled.id})
    assert controlled.owner_id == 1
    assert controlled.moves_this_turn == 1
    assert controlled.attacks_made_this_night == 1
    assert state.players[0].invulnerable_until_end_turn
    on_end_turn(state)
    assert controlled.owner_id == 2 and controlled in state.players[1].units


def test_infected_full_moon_control_and_return():
    state = make_state(
        ["lobisomens", "humanos", "orcs", "fadas"],
        ["lupa_lider", "miyamoto", "arken", "ainai"],
    )
    summon_hero(state, 1)
    victim = troop(state, 2)
    assert peoples.add_infection(state.players[0], victim)
    full_moon(state, 1)
    start_turn(state)
    assert victim.owner_id == 1 and victim in state.players[0].units
    assert victim.resistance_stacks == 1
    assert peoples.is_unit_infected(state, victim)
    on_end_turn(state)
    assert victim.owner_id == 2 and victim in state.players[1].units
    assert victim.resistance_stacks == 0
    assert peoples.is_unit_infected(state, victim)


def test_miyamoto_kill_and_retaliation_gain_victim_life():
    state = make_state()
    state.phase = Phase.NIGHT
    miyamoto = summon_hero(state, 1)
    miyamoto.statuses.pop("summoned_turn", None)
    miyamoto.house = CENTER
    miyamoto.life = miyamoto.life_max = 10
    victim = troop(state, 2, life=3)
    resolve_attack(state, Attack(miyamoto.id, "unit", victim.id))
    assert state.players[0].miyamoto_life_max_bonus == 3
    assert miyamoto.life_max == 13
    state.players[0].units.remove(miyamoto)
    reincarnated = summon_hero(state, 1)
    assert reincarnated.life_max == 7

    state2 = make_state()
    state2.phase = Phase.NIGHT
    m2 = summon_hero(state2, 1)
    m2.statuses.pop("summoned_turn", None)
    m2.house = CENTER
    attacker = troop(state2, 2, life=2)
    resolve_attack(state2, Attack(attacker.id, "unit", m2.id))
    assert state2.players[0].miyamoto_life_max_bonus == 2


def test_summon_cannot_move_but_can_attack():
    state = make_state()
    summoned = summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    summoned.house = CENTER
    try:
        move_unit(state, 1, summoned.id, "city_1")
        raise AssertionError("Invocado moveu no mesmo turno")
    except ActionError:
        pass
    state.phase = Phase.NIGHT
    target = troop(state, 2, life=2)
    resolve_attack(state, Attack(summoned.id, "unit", target.id))
    assert not target.is_alive()


def test_dead_unit_cannot_use_second_attack():
    state = make_state()
    state.phase = Phase.NIGHT
    attacker = troop(state, 1, life=2)
    attacker.max_attacks_this_night = 2
    target = troop(state, 2, life=3)
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    assert not attacker.is_alive()
    try:
        resolve_attack(state, Attack(attacker.id, "unit", target.id))
        raise AssertionError("Morto atacou novamente")
    except CombatError:
        pass


def test_licantropo_gets_lupa_and_cigana_buffs_outside_full_moon():
    state = make_state(
        ["lobisomens", "humanos", "orcs", "fadas"],
        ["lupa_lider", "miyamoto", "arken", "ainai"],
    )
    state.curuna_id = 1
    summon_hero(state, 1)
    summon_hero(state, 1, force_hero_id="cigana")
    target = troop(state, 1)
    cast_spell(state, 1, {"unit_id": target.id})
    assert target.statuses.get("lobisomem_until_turn") == state.turn
    assert target.resistance_stacks == 1
    assert target.statuses.get("invisivel_until_turn") == state.turn


def test_guarari_can_move_once_on_summon_turn():
    state = make_state(
        ["filhos_floresta", "humanos", "orcs", "fadas"],
        ["guarari", "miyamoto", "arken", "ainai"],
    )
    guarari = summon_hero(state, 1)
    assert guarari.max_moves_this_turn == 1
    assert guarari.moves_this_turn == 0
    move_unit(state, 1, guarari.id, CENTER)
    try:
        move_unit(state, 1, guarari.id, "city_2")
        raise AssertionError("Guarari andou 2x no turno em que foi invocado")
    except ActionError:
        pass


def test_guarari_has_two_normal_moves_after_summon_turn():
    state = make_state(
        ["filhos_floresta", "humanos", "orcs", "fadas"],
        ["guarari", "miyamoto", "arken", "ainai"],
    )
    guarari = summon_hero(state, 1)
    state.turn = 2
    start_turn(state)
    assert guarari.max_moves_this_turn == 2
    move_unit(state, 1, guarari.id, CENTER)
    move_unit(state, 1, guarari.id, "city_2")
    assert guarari.house == "city_2"


def test_gnome_bets_are_requested_before_player_days():
    state = make_state(
        ["gnomos_duendes", "humanos", "orcs", "fadas"],
        ["bimbo_do_mal", "miyamoto", "arken", "ainai"],
    )
    start_turn(state)
    gnome = state.players[0]
    assert gnome.bets_need_realocacao

    from jessica import main as main_mod
    calls = []
    original = main_mod._gnomo_bets_menu
    try:
        main_mod._gnomo_bets_menu = lambda current_state, player: calls.append(player.id)
        main_mod._gnomos_bets_inicio_turno(state)
    finally:
        main_mod._gnomo_bets_menu = original
    assert calls == [gnome.id]


def run_all():
    tests = [
        test_priority_is_per_player_and_updates_on_entry,
        test_qc_preserves_actions_and_uses_controller_buffs,
        test_infected_full_moon_control_and_return,
        test_miyamoto_kill_and_retaliation_gain_victim_life,
        test_summon_cannot_move_but_can_attack,
        test_dead_unit_cannot_use_second_attack,
        test_licantropo_gets_lupa_and_cigana_buffs_outside_full_moon,
        test_guarari_can_move_once_on_summon_turn,
        test_guarari_has_two_normal_moves_after_summon_turn,
        test_gnome_bets_are_requested_before_player_days,
    ]
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
