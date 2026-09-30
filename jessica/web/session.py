"""Histórico e restauração locais, sem reimplementar regras do motor."""
from copy import deepcopy
from ..core.constants import Phase
from ..core.headless import EVENT_VERSION, view_for_player
from ..core.serialize import state_to_dict
from . import saves


def checkpoint(match):
    state = match["state"]
    history = match.setdefault("history", [])
    if history and history[0]["turn"] != state.turn:
        history.clear()
    if (state.phase != Phase.DAY or state.web_reaction or state.game_over
            or state.active_player_id is None):
        return
    player = next(p for p in state.players if p.id == state.active_player_id)
    if not player.morning_done_this_turn:
        return
    if any(h["player_id"] == player.id for h in history):
        return
    history.append({"player_id": player.id, "turn": state.turn,
                    "snapshot": {"version": saves.SAVE_VERSION, "state": state_to_dict(state),
                                 "events": deepcopy(match["events"]), "name": match.get("name", "Partida local")}})


def controls(match):
    state = match["state"]
    available = state.phase == Phase.DAY and not state.web_reaction and not state.game_over
    current = next((i for i, h in enumerate(match.get("history", []))
                    if h["turn"] == state.turn and h["player_id"] == state.active_player_id), None)
    return {"undo": available and current is not None,
            "mola": available and current is not None and current > 0}


def restore(match, operation):
    if operation not in ("undo", "mola") or not controls(match)[operation]:
        raise ValueError("Restauração indisponível nesta janela.")
    history = match["history"]
    current = next(i for i, h in enumerate(history) if h["player_id"] == match["state"].active_player_id)
    index = current - int(operation == "mola")
    state, events, _ = saves.validate(history[index]["snapshot"])
    match["state"] = state
    match["events"] = events
    del history[index + 1:]
    public = view_for_player(state, state.active_player_id)
    match["events"].append({"version": EVENT_VERSION, "type": "day_restored", "turn": state.turn,
                            "phase": state.phase.value, "participants": [state.active_player_id],
                            "data": {"player_id": state.active_player_id, "operation": operation,
                                     "public_after": {key: public[key] for key in
                                         ("players", "board", "conditions", "turn", "phase", "active_player_id", "curuna_id")}},
                            "visibility": {"kind": "public", "player_ids": []}})


def public_snapshot(state):
    if state.web_reaction:
        state = deepcopy(state)
        state.active_player_id = state.web_reaction["origin_active_player_id"]
        state.web_reaction = {}
    view = view_for_player(state, state.players[0].id)
    return {"players": view["players"], "board": view["board"], "conditions": view["conditions"],
            "turn": state.turn, "phase": state.phase.value,
            "log_index": len(state.event_log), "action_index": len(state.action_log),
            "announcement_index": len(state.web_night.get("announcements", []))}


def public_events(state, log_index=0, action_index=0, announcement_index=0):
    events = []
    def event(kind, data, turn=state.turn, phase=state.phase.value):
        return {"version": EVENT_VERSION, "type": kind, "turn": turn, "phase": phase,
                "participants": [], "data": data, "visibility": {"kind": "public", "player_ids": []}}
    for message in state.event_log[log_index:]:
        if "[ROLL] Cabaca Cheia" in message or "[ROLL] Iuna:" in message:
            events.append(event("public_roll", {"message": message.split("[ROLL]", 1)[1].strip()}))
    for record in state.action_log[action_index:]:
        if record["action"] == "roll" and record["params"].get("source") == "roca_humanos":
            events.append(event("public_roll", {"player_id": record["player_id"],
                "results": list(record["params"]["results"]), "source": "Roça de Quilombo"},
                record["turn"], record["phase"]))
    for announcement in state.web_night.get("announcements", [])[announcement_index:]:
        events.append(event("combat_house_opened", deepcopy(announcement), phase="night"))
    return events


def changes(before, state, action):
    after = public_snapshot(state)
    changes = []
    for old, new in zip(before["players"], after["players"]):
        for field in ("life", "life_max", "gold", "magic", "has_monument"):
            if (action.get("type") == "collect_resources" and action.get("player_id") == new["id"]
                    and field in ("gold", "magic")):
                continue
            if old["city"][field] != new["city"][field]:
                changes.append({"kind": "city", "player_id": new["id"], "name": new["name"],
                                "field": field, "before": old["city"][field], "after": new["city"][field]})
        for field in ("hand_count", "canastra", "field_artifacts"):
            if old[field] != new[field]:
                changes.append({"kind": "player", "player_id": new["id"], "name": new["name"],
                                "field": field, "before": old[field], "after": new[field]})
    old_units = {u["id"]: u for u in before["board"]["units"]}
    new_units = {u["id"]: u for u in after["board"]["units"]}
    for uid in sorted(old_units.keys() | new_units.keys()):
        old, new = old_units.get(uid), new_units.get(uid)
        if old != new:
            changes.append({"kind": "unit", "before": old, "after": new})
    if before["conditions"] != after["conditions"]:
        changes.append({"kind": "conditions", "after": after["conditions"]})
    index = before["announcement_index"] if before["turn"] == state.turn else 0
    events = public_events(state, before["log_index"], before["action_index"], index)
    if changes:
        events.append({"version": EVENT_VERSION, "type": "public_state_changed", "turn": state.turn,
             "phase": state.phase.value, "participants": [],
             "data": {"changes": changes, "from_turn": before["turn"], "from_phase": before["phase"]},
             "visibility": {"kind": "public", "player_ids": []}})
    return events
