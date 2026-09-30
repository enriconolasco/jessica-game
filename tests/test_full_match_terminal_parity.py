"""Partidas completas por ações gerais: cada povo assume o atacante uma vez."""
import os
import sys
from collections import defaultdict
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica.core import actions, night_actions
from jessica.core.constants import Phase, TroopArchetype
from jessica.core.headless import legal_actions, apply_action
from jessica.core.turn import day_order, end_day, end_turn, start_turn, start_player_day
from jessica.core.state import log
from jessica.web import server
from test_night_terminal_parity import compare, mechanics
from test_web_cycle_parity import step


def direct_day(state, action):
    kind, pid, params = action["type"], action["player_id"], action["params"]
    if kind == "collect_resources":
        actions.collect_resources(state, pid, params["gold"], params["magic"])
    elif kind == "summon_troop":
        actions.summon_troop(state, pid, TroopArchetype(params["archetype"]),
                             params["life"], params["house"])
    elif kind == "move_unit":
        actions.move_unit(state, pid, **params)
    elif kind == "allocate_bets":
        assert all(v is None for v in params["bets"].values())
        state.players[pid - 1].bets_need_realocacao = False
        start_player_day(state, day_order(state)[0])
    else:
        assert kind == "end_turn"
        state.players[pid - 1].has_played_day_this_turn = True
        order = day_order(state)
        following = order[order.index(pid) + 1:]
        if following:
            start_player_day(state, following[0])
        else:
            end_day(state)


def day_choice(state, available):
    for kind in ("allocate_bets", "collect_resources"):
        chosen = next((a for a in available if a["type"] == kind), None)
        if chosen:
            return chosen
    if state.active_player_id == 1:
        player = state.players[0]
        if not player.units:
            summons = [a for a in available if a["type"] == "summon_troop"]
            if summons:
                return max(summons, key=lambda a: a["params"]["life"])
        target = next((p.id for p in state.players[1:] if p.city.is_alive()), None)
        if player.units and target:
            unit = player.units[0]
            destination = f"city_{target}" if unit.house == "center" else "center"
            if unit.house != f"city_{target}":
                move = next((a for a in available if a["type"] == "move_unit"
                    and a["params"] == {"unit_id": unit.id, "destination": destination}), None)
                if move:
                    return move
    return next(a for a in available if a["type"] == "end_turn")


def full_night(state):
    trial = deepcopy(state)
    plan = defaultdict(list)
    for _ in range(80):
        if trial.game_over:
            break
        available = legal_actions(trial, trial.active_player_id)
        finish = next((a for a in available if a["type"] == "finish_night"), None)
        if finish:
            break
        attack = next((a for a in available if a["type"] == "night_attack"
                       and a["player_id"] == 1 and a["params"]["target_type"] == "city"), None)
        action = attack or next(a for a in available if a["type"] == "night_pass")
        if attack:
            p = attack["params"]
            plan[p["attacker_unit_id"]].append((p["target_type"], p["target_id"]))
        assert apply_action(trial, action)["success"]
    else:
        raise AssertionError("Noite sem término")
    state, _ = compare(state, dict(plan))
    if state.game_over:
        return state
    direct = deepcopy(state)
    log(direct, f"--- Fim da Noite (Turno {direct.turn}) ---")
    end_turn(direct)
    if not direct.game_over:
        start_turn(direct)
        if not any(p.city.is_alive() and p.people == "gnomos_duendes"
                   and p.bets_need_realocacao for p in direct.players):
            start_player_day(direct, day_order(direct)[0])
    action = next(a for a in legal_actions(state, state.active_player_id) if a["type"] == "finish_night")
    state = step(state, action)
    assert mechanics(state) == mechanics(direct)
    return state


def test_twelve_complete_matches_to_victory_equal_terminal():
    catalog = {p["id"]: p for p in server._catalog()["peoples"]}
    for index, attacker in enumerate(server.PEOPLES):
        peoples = [attacker] + [p for p in server.PEOPLES if p != attacker][:3]
        players = [{"name": f"J{i+1}", "people": p, "hero_id": catalog[p]["heroes"][0]["id"]}
                   for i, p in enumerate(peoples)]
        # Púrpura mantém uma Base convencional neste roteiro de ações gerais.
        for p in players:
            if p["people"] == "dragoes":
                p["hero_id"] = "purpura"
        state = server._new_state(110 + index, players,
            {"order_mode": "fixed", "city_life": 1, "gold": 20, "magic": 20})
        for _ in range(240):
            if state.game_over:
                break
            if state.phase == Phase.NIGHT:
                state = full_night(state)
            else:
                action = day_choice(state, legal_actions(state, state.active_player_id))
                direct = deepcopy(state)
                direct_day(direct, action)
                state = step(state, action)
                assert mechanics(state) == mechanics(direct), (attacker, action)
        else:
            raise AssertionError(f"Partida de {attacker} não terminou")
        assert state.winner_id == 1, attacker


if __name__ == "__main__":
    try:
        test_twelve_complete_matches_to_victory_equal_terminal()
        print("1 passaram, 0 falharam")
    except Exception as exc:
        print(f"FALHOU - partidas completas: {type(exc).__name__}: {exc}")
        print("0 passaram, 1 falharam")
