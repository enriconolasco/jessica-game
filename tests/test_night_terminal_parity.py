"""Compara a orquestração noturna do terminal com escolhas web restauradas."""
import os
import sys
from contextlib import ExitStack
from copy import deepcopy
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica import main as terminal
from jessica.core import combat, night_actions
from jessica.core.headless import apply_action, legal_actions, view_for_player
from jessica.core.models import Hero, Troop
from jessica.core.serialize import state_from_dict, state_to_dict
from jessica.core.state import snapshot_turn_start_priority, sync_house_priority
from jessica.web import session
from test_night_web import night


def mechanics(state):
    data = state_to_dict(state)
    for key in ("active_player_id", "web_night", "web_reaction"):
        data.pop(key, None)
    return data


def compare(state, plan, terminal_picker=None, web_windows=None, real_windows=(), artifact_choices=None,
            window_trace=None, decision_trace=None):
    direct = state_from_dict(state_to_dict(state))
    terminal_trace = []
    remaining = deepcopy(plan)

    def prompt(current, unit, targets):
        wanted = remaining.get(unit.id, [])
        if not wanted:
            return None
        kind, target = wanted[0]
        if not any(t[:2] == (kind, target) for t in targets):
            return None
        wanted.pop(0)
        attack = combat.Attack(unit.id, kind, target)
        terminal_trace.append(vars(attack))
        return attack

    with ExitStack() as patches:
        patches.enter_context(patch.object(combat, "_armor_choice_fn", lambda player, damage: 0))
        patches.enter_context(patch.object(terminal, "console", Mock()))
        for name in ("show_hud", "show_map", "_ask_vovo_position", "_try_luna_return",
                     "_ainai_prompt_all", "_try_besouro_mandinga", "_night_info_prompt",
                     "_mostrar_resumo_local"):
            if name not in real_windows:
                patches.enter_context(patch.object(terminal, name, lambda *a, **kw: None))
        if terminal_picker is None:
            patches.enter_context(patch.object(terminal, "_luide_janela_noturna", lambda *a, **kw: None))
        else:
            patches.enter_context(patch.object(terminal, "pick_index", terminal_picker))
        if artifact_choices is not None:
            patches.enter_context(patch.object(terminal, "_ask_choice_for_artifact",
                lambda current, pid, card: deepcopy(artifact_choices[card])))
        patches.enter_context(patch.object(terminal, "prompt_attack", prompt))
        terminal.run_night_phase(direct)

    remaining = deepcopy(plan)
    web_trace = []
    for _ in range(100):
        if state.game_over:
            break
        before = state_to_dict(state)
        choices = legal_actions(state, state.active_player_id)
        # Initial preparation may select a different player, without mutating queries.
        if not choices:
            for player in state.players:
                choices = legal_actions(state, player.id)
                if choices:
                    break
        for player in state.players:
            view_for_player(state, player.id)
        assert state_to_dict(state) == before
        assert choices, "Noite bloqueada sem explicação"
        if choices[0]["type"] == "finish_night":
            break
        scripted = next((a for a in choices if web_windows and a["type"] == web_windows[0]["type"]
                         and a["params"] == web_windows[0]["params"]), None)
        if scripted:
            action = scripted
            web_windows.pop(0)
        elif choices[0]["type"] == "armor_payment":
            action = next(a for a in choices if a["params"]["gold"] == 0)
        elif choices[0]["type"] == "night_setup":
            action = next(a for a in choices if a["params"].get("position") ==
                          state.players[a["player_id"] - 1].vovo_position
                          or a["params"].get("return") is False
                          or a["params"]["kind"] in ("besouro", "aiquara"))
        elif any(a["type"] == "night_window_done" for a in choices):
            action = next(a for a in choices if a["type"] == "night_window_done")
        else:
            action = None
            for candidate in choices:
                params = candidate["params"]
                wanted = remaining.get(params.get("attacker_unit_id"), [])
                if candidate["type"] == "night_attack" and wanted and (
                        params["target_type"], params["target_id"]) == wanted[0]:
                    action = candidate
                    wanted.pop(0)
                    web_trace.append(params)
                    break
            if action is None:
                action = next(a for a in choices if a["type"] == "night_pass")
        restored = state_from_dict(before)
        if window_trace is not None and action["type"] == "night_window_done":
            window_trace.append(len(state.web_night.get("processed", [])))
        result = apply_action(state, action)
        assert result["success"] and result == apply_action(restored, action)
        if decision_trace is not None:
            decision_trace.append(action["type"])
        assert state_to_dict(state) == state_to_dict(restored)
        state = restored
    else:
        raise AssertionError("Fila noturna não terminou")
    assert web_trace == terminal_trace, (web_trace, terminal_trace)
    assert mechanics(state) == mechanics(direct)
    return state, web_trace


def troop(state, pid, uid, house="center", life=8):
    unit = Troop(id=uid, owner_id=pid, house=house, life=life, life_max=life)
    state.players[pid - 1].units.append(unit)
    return unit


def test_armor_reaction_in_real_terminal_night_matches_web():
    state = night()
    troop(state, 1, "attacker")
    troop(state, 2, "defender")
    state.players[1].armor_active_until_turn = state.turn
    state.players[1].city.gold = 8
    decisions = []
    result, trace = compare(state, {"attacker": [("unit", "defender")]}, decision_trace=decisions)
    assert "armor_payment" in decisions and len(trace) == 1
    assert result.players[1].city.gold == 8


def test_occupation_arrival_and_reentry_priority():
    state = night()
    state.curuna_id = 3
    troop(state, 3, "old3")
    troop(state, 1, "old1")
    snapshot_turn_start_priority(state)
    troop(state, 4, "new4")
    sync_house_priority(state, "center")
    troop(state, 2, "new2")
    sync_house_priority(state, "center")
    state.players[2].units[0].house = "city_3"
    sync_house_priority(state, "center", "city_3")
    state.players[2].units[0].house = "center"
    sync_house_priority(state, "city_3", "center")
    for player in state.players:
        for unit in player.units:
            unit.resistance_stacks = 4
    state, trace = compare(state, {uid: [("unit", target)] for uid, target in
        (("old1", "new2"), ("new4", "new2"), ("new2", "old3"), ("old3", "new4"))})
    assert [a["attacker_unit_id"] for a in trace] == ["old1", "new4", "new2", "old3"]


def test_house_order_for_every_curuna():
    for pid in range(1, 5):
        state = night()
        state.curuna_id = pid
        plan = {}
        for target in range(1, 5):
            owner = target % 4 + 1
            unit = troop(state, owner, f"siege{target}", f"city_{target}")
            plan[unit.id] = [("city", str(target))]
        _, trace = compare(state, plan)
        order = terminal.day_order(state)
        assert [a["target_id"] for a in trace] == [str(p) for p in reversed(order)]


def test_death_cancels_remaining_attacks():
    state = night()
    state.players[0].people = "gigantes"
    state.players[0].units = [Hero(id="pe", owner_id=1, house="center", life=1,
                                 life_max=2, hero_id="pe_descalco")]
    troop(state, 2, "enemy")
    _, trace = compare(state, {"pe": [("unit", "enemy"), ("unit", "enemy")]})
    assert len(trace) == 1


def test_vovo_death_removes_damage_for_next_ally():
    state = night()
    state.players[0].people = "orcs"
    state.players[0].units = [Hero(id="vovo", owner_id=1, house="center", life=1,
                                 life_max=2, hero_id="vovo_gamba")]
    troop(state, 1, "ally")
    troop(state, 2, "enemy", life=20)
    final, trace = compare(state, {"vovo": [("unit", "enemy")], "ally": [("unit", "enemy")]})
    assert len(trace) == 2
    assert not any(u.id == "vovo" for u in final.players[0].units)
    assert final.players[1].units[0].life == 10  # 1+1 com Vovó, depois 8 sem ela.


def test_first_strike_and_vovo_reordering():
    for first in (False, True):
        state = night()
        troop(state, 1, "one")
        state.players[1].units = [Hero(id="vovo", owner_id=2, house="center", life=10,
                                     life_max=10, hero_id="vovo_gamba")]
        state.players[1].vovo_position = 3
        troop(state, 3, "three")
        for player in state.players:
            for unit in player.units:
                unit.resistance_stacks = 4
        snapshot_turn_start_priority(state)
        if first:
            state.players[2].bater_primeiro_turn = state.turn
        _, trace = compare(state, {u: [("unit", t)] for u, t in
            (("one", "three"), ("three", "one"), ("vovo", "one"))})
        assert [a["attacker_unit_id"] for a in trace] == (
            ["three", "one", "vovo"] if first else ["one", "three", "vovo"])


def test_skipped_player_remains_target_but_cannot_declare():
    state = night()
    troop(state, 1, "one").resistance_stacks = 4
    troop(state, 2, "skipped").resistance_stacks = 4
    state.players[1].skip_night_turn = state.turn
    final, trace = compare(state, {"one": [("unit", "skipped")], "skipped": [("unit", "one")]})
    assert len(trace) == 1 and final.players[1].units[0].attacks_made_this_night == 0


def test_iuna_random_damage_and_retaliation_preserve_rng():
    from jessica.core.state import make_rng
    for seed in range(8):
        for attacking in (False, True):
            state = night()
            state.rng = make_rng(seed)
            state.players[0].units = [Hero(id="iuna", owner_id=1, house="center", life=6,
                                         life_max=6, hero_id="iuna", resistance_stacks=2)]
            troop(state, 2, "enemy").resistance_stacks = 2
            _, trace = compare(state, {"iuna": [("unit", "enemy")]} if attacking else
                               {"enemy": [("unit", "iuna")]})
            assert len(trace) == 1


def test_controlled_troop_declares_for_controller_against_original_owner():
    from jessica.core.actions import play_artifact
    from jessica.core.constants import Phase
    from jessica.core.turn import end_day
    state = night()
    controlled = troop(state, 2, "controlled")
    troop(state, 2, "original_ally").resistance_stacks = 4
    controlled.resistance_stacks = 4
    state.phase = Phase.DAY
    state.players[0].hand = ["Q_C"]
    play_artifact(state, 1, "Q_C", choice={"unit_id": controlled.id})
    end_day(state)
    final, trace = compare(state, {"controlled": [("unit", "original_ally")]})
    assert len(trace) == 1
    assert final.players[0].units[0].owner_id == 1
    assert final.players[0].units[0].original_owner_id == 2


def test_occupied_house_without_targets_announces_no_combat():
    for condition in ("alone", "hidden", "spoiled"):
        state = night()
        one = troop(state, 1, "one")
        if condition == "hidden":
            one.statuses["invisivel_until_turn"] = state.turn
            other = troop(state, 2, "two")
            other.statuses["invisivel_until_turn"] = state.turn
        if condition == "spoiled":
            one.statuses["cannot_attack_on_turn"] = state.turn
            other = troop(state, 2, "two")
            other.statuses["cannot_attack_on_turn"] = state.turn
        night_actions.prepare(state)
        announcements = session.public_events(state)
        center = next(e for e in announcements if e["type"] == "combat_house_opened"
                      and e["data"]["house"] == "center")
        assert center["data"]["order"] == []
        assert [a["type"] for a in legal_actions(state, 1)] == ["finish_night"]


def test_luide_spell_move_and_attack_future_or_processed_house():
    for reentry, local_enemy in ((False, False), (False, True), (True, False), (True, True)):
        state = night()
        origin, destination = ("city_4", "center") if reentry else ("center", "city_4")
        state.players[0].people = "vampiros"
        state.players[0].city.magic = 20
        state.players[0].units = [Hero(id="luide", owner_id=1, house=origin, life=8,
                                     life_max=8, hero_id="luide_vampa")]
        if reentry or local_enemy:
            troop(state, 2, "center_enemy")
        if not reentry or local_enemy:
            troop(state, 3, "city_enemy", "city_4")
        selected = ["Lancar feitico", "Mover unidade"]

        def picker(title, labels):
            if "(Luide Vampa)" in title:
                return labels.index(selected.pop(0)) if selected else len(labels) - 1
            if title == "Destino":
                return 0 if destination == "center" else 3
            return 0

        windows = [{"type": "night_luide_spell", "params": {"unit_id": "luide"}},
                   {"type": "night_luide_move", "params": {"unit_id": "luide", "destination": destination}}]
        target = "center_enemy" if reentry else "city_enemy"
        final, trace = compare(state, {"luide": [("unit", target)]}, picker, windows)
        assert len(trace) == 1 and not selected and not windows
        assert final.players[0].units[0].house == destination


def test_luna_return_after_flames_before_declarations():
    for returning in (False, True):
        state = night()
        state.players[0].people = "fadas"
        state.players[0].units = [Hero(id="luna", owner_id=1, house="center", life=2,
            life_max=2, hero_id="luna", resistance_stacks=2,
            statuses={"luna_origin_house": "city_1"})]
        state.players[1].people = "dragoes"
        state.players[1].units = [Hero(id="barba", owner_id=2, house="center", life=3,
            life_max=3, hero_id="barba_negra", statuses={"mar_chamas_queued_turn": state.turn})]
        troop(state, 3, "enemy", "city_1" if returning else "center", life=1).resistance_stacks = 1
        windows = [{"type": "night_setup", "params": {"kind": "luna", "return": returning}}]
        final, trace = compare(state, {"luna": [("unit", "enemy")]},
            lambda title, labels: 0 if returning else 1, windows, ("_try_luna_return",))
        assert len(trace) == 1 and not windows
        luna = final.players[0].units[0]
        assert luna.house == ("city_1" if returning else "center")


def test_mandinga_summoned_hero_enters_declaration_queue():
    state = night()
    state.players[0].units = [Hero(id="besouro", owner_id=1, house="center", life=4,
                                 life_max=4, hero_id="besouro")]
    state.players[0].hand = ["J_H"]
    troop(state, 2, "enemy", "city_1", life=1)
    choice = {"hero_id": "iuna"}
    windows = [{"type": "night_mandinga", "params": {"card_id": "J_H", "choice": choice}}]
    final, trace = compare(state, {"p1_hero_extra_1": [("unit", "enemy")]},
        lambda title, labels: 1 if title == "Mandinga:" else len(labels) - 1,
        windows, ("_try_besouro_mandinga",), {"J_H": choice})
    assert len(trace) == 1 and not windows
    assert final.players[0].besouro_mandinga_used_turn == final.turn


def test_ainai_after_combat_reopens_processed_house():
    state = night()
    state.players[0].people = "fadas"
    state.players[0].units = [Hero(id="ainai", owner_id=1, house="city_1", life=4,
        life_max=4, hero_id="ainai", resistance_stacks=1),
        Troop(id="fallen", owner_id=1, house="center", life=1, life_max=4)]
    enemy = troop(state, 2, "enemy", life=4)
    enemy.resistance_stacks = 2
    windows = [{"type": "night_ainai", "params": {"destination": "center"}}]
    final, trace = compare(state, {"fallen": [("unit", "enemy")], "ainai": [("unit", "enemy")]},
        lambda title, labels: 1 if title == "Teleporte de Ainai?" else len(labels) - 1,
        windows, ("_ainai_prompt_all",))
    assert [a["attacker_unit_id"] for a in trace] == ["fallen", "ainai"]
    assert not windows and final.players[0].units[0].house == "center"


def test_ainai_window_timing_matches_terminal_including_empty_houses():
    state = night()
    state.players[0].people = "fadas"
    state.players[0].units = [Hero(id="ainai", owner_id=1, house="city_1", life=4,
                                 life_max=4, hero_id="ainai")]
    state.fae_fallen_this_turn = [(1, "center")]
    troop(state, 2, "enemy", "city_2")
    original = terminal._ainai_prompt_all
    expected, actual = [], []

    def observe(current, pids, processed_houses=None):
        expected.append(len(processed_houses or []))
        return original(current, pids, processed_houses)

    with patch.object(terminal, "_ainai_prompt_all", observe):
        compare(state, {}, lambda title, labels: 0, real_windows=("_ainai_prompt_all",),
                window_trace=actual)
    assert actual == expected, (actual, expected)


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test()
                passed += 1
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
