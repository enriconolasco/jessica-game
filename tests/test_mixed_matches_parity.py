"""Partidas mistas até vitória, com feitiços/habilidades e save após cada ação."""
import os
import sys
from collections import defaultdict
from copy import deepcopy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core import actions, interaction_actions, peoples
from jessica.core.constants import Phase
from jessica.core.headless import legal_actions
from jessica.core.models import Hero, Troop
from jessica.core.state import log
from jessica.core.turn import day_order, end_turn, start_turn, start_player_day
from jessica.web.server import _new_state
from test_full_match_terminal_parity import direct_day
from test_night_terminal_parity import compare, mechanics
from test_web_cycle_parity import step


def choose_day(state, choices, used):
    pid, turn = state.active_player_id, state.turn
    player = state.players[pid - 1]
    if choices and all(a["type"] == "demon_pact" for a in choices):
        return choices[0]
    for kind in ("allocate_bets", "resolve_artifact_choice", "collect_resources"):
        candidate = next((a for a in choices if a["type"] == kind), None)
        if candidate:
            if kind == "allocate_bets":
                targets = [p.id for p in state.players if p.id != pid and p.city.is_alive()]
                candidate = deepcopy(candidate)
                candidate["params"]["bets"] = {suit: targets[0] if targets else None for suit in "HCDS"}
            return candidate
    if not any(isinstance(u, Hero) and u.is_alive() for u in player.units):
        candidate = next((a for a in choices if a["type"] == "summon_hero"), None)
        if candidate:
            return candidate
    if pid == 1 and not any(isinstance(u, Troop) and u.is_alive() for u in player.units):
        candidates = [a for a in choices if a["type"] == "summon_troop"]
        if candidates:
            return max(candidates, key=lambda a: a["params"]["life"])
    for kind in ("buy_artifact_gold", "play_artifact", "cast_spell", "hero_ability"):
        key = (0 if kind == "buy_artifact_gold" else turn, pid, kind)
        if key in used:
            continue
        candidates = [a for a in choices if a["type"] == kind]
        if kind == "cast_spell" and pid == 1 and player.people == "filhos_floresta":
            if (0, pid, "decompor") in used:
                continue
            candidates = [a for a in candidates if a["params"]["choice"].get("kind") == "city"]
            if candidates:
                used.add((0, pid, "decompor"))
        if kind == "play_artifact":
            candidates = [a for a in candidates if a["params"]["card_id"] in ("J_S", "Q_H", "K_C")]
        if candidates:
            used.add(key)
            return candidates[0]
    if pid == 1:
        target = next((p.id for p in state.players[1:] if p.city.is_alive()), None)
        for unit in player.units:
            if target is None or not unit.is_alive() or unit.house == f"city_{target}":
                continue
            destination = f"city_{target}" if unit.house == "center" else "center"
            candidate = next((a for a in choices if a["type"] == "move_unit"
                              and a["params"] == {"unit_id": unit.id, "destination": destination}), None)
            if candidate:
                return candidate
    else:
        destination = f"city_{pid}" if (0, pid, "buy_artifact_gold") in used else "center"
        candidate = next((a for a in choices if a["type"] == "move_unit"
                          and a["params"]["destination"] == destination), None)
        if candidate:
            return candidate
    return next(a for a in choices if a["type"] == "end_turn")


def direct_action(state, action):
    if action["type"] == "allocate_bets":
        player = state.players[action["player_id"] - 1]
        for suit, target in action["params"]["bets"].items():
            if target is None:
                setattr(player, f"bet_{suit}_target", None)
            else:
                actions.gnomo_alocar_aposta(state, player.id, suit, target)
        player.bets_need_realocacao = False
        if not any(p.morning_done_this_turn for p in state.players):
            start_player_day(state, day_order(state)[0])
    elif action["type"] in interaction_actions.LABELS:
        interaction_actions.execute(state, action)
    elif action["type"] == "buy_artifact_gold":
        actions.buy_artifact_with_gold(state, action["player_id"])
    elif action["type"] == "summon_hero":
        actions.summon_hero(state, action["player_id"], force_hero_id=action["params"].get("hero_id"))
    else:
        direct_day(state, action)


def choose_night(state, choices):
    for kind in ("armor_payment", "night_window_done", "night_setup", "night_resolve_choice", "night_skip_clock"):
        candidates = [a for a in choices if a["type"] == kind]
        if candidates:
            if kind == "armor_payment":
                return next(a for a in candidates if a["params"]["gold"] == 0)
            if kind == "night_setup":
                return next(a for a in candidates if a["params"].get("position") ==
                            state.players[a["player_id"] - 1].vovo_position
                            or a["params"].get("return") is False
                            or a["params"]["kind"] in ("aiquara", "besouro"))
            return candidates[0]
    attacks = [a for a in choices if a["type"] == "night_attack" and a["player_id"] == 1]
    if attacks:
        return next((a for a in attacks if a["params"]["target_type"] == "city"), attacks[0])
    return next((a for a in choices if a["type"] == "night_pass"),
                next((a for a in choices if a["type"] == "night_attack"), None))


def finish_night(state, counts, on_step=None, night_policy=None):
    trial, plan = deepcopy(state), defaultdict(list)
    for _ in range(120):
        if trial.game_over:
            break
        choices = legal_actions(trial, trial.active_player_id)
        if not choices:
            choices = next((items for p in trial.players if (items := legal_actions(trial, p.id))), [])
        assert choices, f"Noite bloqueada T{trial.turn}"
        if choices[0]["type"] == "finish_night":
            break
        action = (night_policy or choose_night)(trial, choices)
        counts[action["type"]] += 1
        if action["type"] == "night_attack":
            params = action["params"]
            plan[params["attacker_unit_id"]].append((params["target_type"], params["target_id"]))
        before = deepcopy(trial) if on_step else None
        trial = step(trial, action)
        if on_step:
            on_step(before, action, trial)
    else:
        raise AssertionError("Noite excedeu limite de decisões")
    state, _ = compare(state, dict(plan))
    assert mechanics(state) == mechanics(trial), "Roteiro noturno divergente do replay"
    if state.game_over:
        return state
    direct = deepcopy(state)
    log(direct, f"--- Fim da Noite (Turno {direct.turn}) ---")
    end_turn(direct)
    if not direct.game_over:
        start_turn(direct)
        if not any(p.city.is_alive() and p.people == peoples.PEOPLE_GNOMOS
                   and p.bets_need_realocacao for p in direct.players):
            start_player_day(direct, day_order(direct)[0])
    action = next(a for a in legal_actions(state, state.active_player_id) if a["type"] == "finish_night")
    state = step(state, action)
    assert mechanics(state) == mechanics(direct), "Transição de manhã divergente"
    counts["finish_night"] += 1
    return state


def match(group, seed, day_policy=None, on_step=None, night_policy=None):
    players = [{"name": f"J{pid}", "people": people, "hero_id": hero}
               for pid, (people, hero) in enumerate(group, 1)]
    state = _new_state(seed, players, {"city_life": 2, "gold": 25, "magic": 25, "order_mode": "fixed"})
    used, counts = set(), defaultdict(int)
    for _ in range(420):
        if state.game_over:
            break
        if state.phase == Phase.NIGHT:
            state = finish_night(state, counts, on_step, night_policy)
            continue
        action = (day_policy or choose_day)(state, legal_actions(state, state.active_player_id), used)
        before = deepcopy(state) if on_step else None
        direct = deepcopy(state)
        direct_action(direct, action)
        state = step(state, action)
        assert mechanics(state) == mechanics(direct), (state.turn, action)
        if on_step:
            on_step(before, action, state)
        counts[action["type"]] += 1
    else:
        raise AssertionError(f"Partida não terminou: T{state.turn}, {dict(counts)}")
    assert state.winner_id == 1
    assert counts["cast_spell"] >= 4 and counts["summon_hero"] >= 3 and counts["night_attack"] >= 3, dict(counts)
    return dict(counts), state.turn


def test_partida_humanos_anoes_orcs_fadas():
    return match([("humanos", "miyamoto"), ("anoes", "ori"),
           ("orcs", "vovo_gamba"), ("fadas", "luna")], 901)


def test_partida_vampiros_lobisomens_gigantes_mortos_vivos():
    return match([("vampiros", "dracula"), ("lobisomens", "cigana"),
           ("gigantes", "caroco"), ("mortos_vivos", "cova_rasa")], 902)


def test_partida_filhos_gnomos_dragoes_demonios():
    return match([("filhos_floresta", "guarari"), ("gnomos_duendes", "sao_tome"),
           ("dragoes", "purpura"), ("demonios", "tuza")], 903)


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                counts, turn = test()
                passed += 1
                print(f"PARTIDA - {name}: vitória T{turn}; feitiços {counts.get('cast_spell', 0)}; "
                      f"Armadura {counts.get('armor_payment', 0)}; decisões {sum(counts.values())}")
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(1 if failed else 0)
