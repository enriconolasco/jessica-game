"""Fatia noturna sem janelas especiais ainda dependentes do terminal."""
from copy import deepcopy
from . import combat, peoples
from .constants import CENTER, Phase
from .models import Hero
from .night_rules import find_targets, order_players_for_house
from .state import get_player, log
from .turn import day_order, end_turn, start_turn, start_player_day

TYPES = {"night_attack", "night_pass", "finish_night", "night_resolve_choice"}
SUPPORTED_HEROES = {"miyamoto", "arken", "ori"}


def public_window(state):
    if state.phase != Phase.NIGHT or blockers(state):
        return None
    trial = deepcopy(state)
    prepare(trial)
    advance(trial)
    queue = trial.web_night["queue"]
    if not queue:
        return {"house": None, "declaration_order": [], "unit_id": None}
    house = queue[0]["house"]
    return {"house": house, "unit_id": queue[0]["unit_id"],
            "declaration_order": list(dict.fromkeys(
                entry["player_id"] for entry in queue if entry["house"] == house))}


def blockers(state):
    result = []
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id not in SUPPORTED_HEROES
           for p in state.players for u in p.units):
        result.append("Há heróis com janelas noturnas ainda não adaptadas; nesta etapa: Miyamoto, Arken e Ori.")
    if any(p.demon_pact_offers for p in state.players):
        result.append("Há escolhas de pacto pendentes.")
    if any(p.pending_artifact_choice and p.pending_artifact_choice.get("kind")
           not in ("Q_D", "J_D", "BOIN") for p in state.players):
        result.append("Há uma escolha de artefato ainda não adaptada.")
    return result


def pending_owner(state):
    return next((p for p in state.players if p.pending_artifact_choice), None)


def prepare(state):
    if state.web_night.get("turn") == state.turn:
        return
    queue = []
    houses = [CENTER] + [f"city_{pid}" for pid in reversed(day_order(state))]
    for house in houses:
        pids = [pid for pid in day_order(state) if any(
            u.is_alive() and u.house == house for u in get_player(state, pid).units)]
        for pid in order_players_for_house(state, pids, house):
            queue.extend({"house": house, "player_id": pid, "unit_id": u.id}
                         for u in get_player(state, pid).units if u.is_alive() and u.house == house)
    state.web_night = {"turn": state.turn, "queue": queue}
    advance(state)


def attacks(state, entry):
    unit = combat._find_unit(state, entry["unit_id"])
    if unit is None or unit.house != entry["house"]:
        return []
    result = []
    for kind, target, label in find_targets(state, unit):
        attack = combat.Attack(unit.id, kind, target)
        try:
            combat.resolve_attack(deepcopy(state), attack)
        except (combat.CombatError, ValueError):
            continue
        result.append((attack, label))
    return result


def advance(state):
    pending = pending_owner(state)
    if pending is not None:
        state.active_player_id = pending.id
        return
    queue = state.web_night["queue"]
    while queue and not attacks(state, queue[0]):
        queue.pop(0)
    alive = [p.id for p in state.players if p.city.is_alive()]
    state.active_player_id = (queue[0]["player_id"] if queue else
                              state.curuna_id if state.curuna_id in alive else
                              alive[0] if alive else state.curuna_id)


def legal(state, pid):
    from .headless import ACTION_VERSION
    if state.phase != Phase.NIGHT or (state.game_over and pending_owner(state) is None) or blockers(state):
        return []
    trial = deepcopy(state)
    prepare(trial)
    advance(trial)
    if type(pid) is not int or pid != trial.active_player_id:
        return []
    pending = pending_owner(trial)
    if pending is not None:
        from .interaction_actions import _candidates
        options = []
        for candidate in _candidates(trial, pending):
            if candidate["type"] == "resolve_artifact_choice":
                candidate["type"] = "night_resolve_choice"
                options.append(candidate)
        return options
    def offer(kind, params, label):
        return {"version": ACTION_VERSION, "type": kind, "player_id": pid,
                "params": params, "label": label}
    queue = trial.web_night["queue"]
    if not queue:
        return [offer("finish_night", {}, "Encerrar Noite e iniciar próximo turno")]
    entry = queue[0]
    options = attacks(trial, entry)
    result = [offer("night_attack", vars(attack),
                    f"{entry['house']} · {entry['unit_id']} → {label}")
              for attack, label in options]
    if not peoples.demon_mind_pact_active(trial, pid):
        result.append(offer("night_pass", {"unit_id": entry["unit_id"]},
                            f"Não atacar com {entry['unit_id']}"))
    return result


def apply(state, action):
    from .headless import _error, EVENT_VERSION, view_for_player
    candidate = next((a for a in legal(state, action.get("player_id"))
                      if a["type"] == action.get("type") and a["params"] == action.get("params")), None)
    if candidate is None:
        return _error("not_legal", "Declaração noturna indisponível.")
    trial = deepcopy(state)
    prepare(trial)
    advance(trial)
    kind = candidate["type"]
    old_turn = trial.turn
    if kind == "night_resolve_choice":
        from .actions import resolve_pending_artifact_choice, ActionError
        try:
            resolve_pending_artifact_choice(trial, candidate["player_id"], **candidate["params"])
        except (ActionError, ValueError) as exc:
            return _error("domain_error", str(exc))
        advance(trial)
    elif kind == "night_attack":
        combat.resolve_attack(trial, combat.Attack(**candidate["params"]))
        advance(trial)
    elif kind == "night_pass":
        trial.web_night["queue"].pop(0)
        advance(trial)
    else:
        log(trial, f"--- Fim da Noite (Turno {trial.turn}) ---")
        end_turn(trial)
        if not trial.game_over:
            start_turn(trial)
            trial.web_night = {}
            pending = next((p for p in trial.players if p.city.is_alive()
                            and p.people == peoples.PEOPLE_GNOMOS and p.bets_need_realocacao), None)
            trial.active_player_id = pending.id if pending else trial.curuna_id
            if pending is None:
                start_player_day(trial, trial.active_player_id)
    pid = candidate["player_id"]
    event = {"version": EVENT_VERSION, "type": "night_action_resolved", "turn": old_turn,
             "phase": "night", "participants": [pid],
             "data": {"action_type": kind, **candidate["params"]},
             "visibility": {"kind": "private" if kind == "night_resolve_choice" else "public",
                            "player_ids": [pid] if kind == "night_resolve_choice" else []}}
    projection = {"version": EVENT_VERSION, "type": "player_view_updated", "turn": trial.turn,
                  "phase": trial.phase.value, "participants": [pid],
                  "data": {"view": view_for_player(trial, pid)},
                  "visibility": {"kind": "private", "player_ids": [pid]}}
    state.__dict__.update(trial.__dict__)
    return {"success": True, "error": None, "events": [event, projection]}
