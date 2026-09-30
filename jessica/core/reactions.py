"""Suspende uma transação para decisões reativas, reproduzindo o mesmo RNG."""
from copy import deepcopy
from .combat import armor_policy, armor_hit_context


class ArmorRequired(Exception):
    def __init__(self, player, damage):
        from .headless import view_for_player
        context = dict(armor_hit_context.get())
        state = context.pop("_state")
        self.preview = view_for_player(state, player.id)
        self.request = {"player_id": player.id, "damage": damage,
                        "gold_available": player.city.gold, "max_gold": min(damage, player.city.gold),
                        **deepcopy(context)}


def legal(state, pid):
    from .headless import ACTION_VERSION
    request = state.web_reaction.get("request", {})
    if type(pid) is not int or pid != request.get("player_id"):
        return []
    return [{"version": ACTION_VERSION, "type": "armor_payment", "player_id": pid,
             "params": {"gold": 0}, "label": "Armadura de Ouro: escolher pagamento",
             "selection": {"kind": "armor", **request}}]


def apply(state, action, execute):
    from .headless import ACTION_VERSION, EVENT_VERSION, _error, view_for_player
    pending = deepcopy(state.web_reaction)
    if pending:
        request = pending["request"]
        params = action.get("params") if isinstance(action, dict) else None
        if (not isinstance(action, dict) or action.get("version") != ACTION_VERSION
                or action.get("type") != "armor_payment" or type(action.get("player_id")) is not int
                or action["player_id"] != request["player_id"] or not isinstance(params, dict)
                or set(params) != {"gold"} or type(params["gold"]) is not int
                or not 0 <= params["gold"] <= request["max_gold"]):
            return _error("not_legal", "Resolva o pagamento da Armadura de Ouro.")
        pending["payments"].append(params["gold"])
        original = pending["action"]
    else:
        original = action
        pending = {"action": deepcopy(action), "payments": [],
                   "origin_active_player_id": state.active_player_id}
    trial = deepcopy(state)
    trial.web_reaction = {}
    trial.active_player_id = pending["origin_active_player_id"]
    index = 0

    def decide(player, damage):
        nonlocal index
        if min(damage, player.city.gold) <= 0:
            return 0
        if index == len(pending["payments"]):
            raise ArmorRequired(player, damage)
        payment = pending["payments"][index]
        index += 1
        return payment

    try:
        with armor_policy(decide):
            result = execute(trial, original)
    except ArmorRequired as required:
        pending["request"] = required.request
        pending["preview"] = {key: required.preview[key] for key in
                              ("players", "board", "conditions", "shop", "demon_pacts", "self")}
        state.web_reaction = pending
        state.active_player_id = required.request["player_id"]
        pid = state.active_player_id
        event = {"version": EVENT_VERSION, "type": "armor_payment_requested", "turn": state.turn,
                 "phase": state.phase.value, "participants": [pid], "data": required.request,
                 "visibility": {"kind": "private", "player_ids": [pid]}}
        projection = {"version": EVENT_VERSION, "type": "player_view_updated", "turn": state.turn,
                      "phase": state.phase.value, "participants": [pid],
                      "data": {"view": view_for_player(state, pid)},
                      "visibility": {"kind": "private", "player_ids": [pid]}}
        return {"success": True, "error": None, "events": [event, projection]}
    if result["success"]:
        state.__dict__.update(trial.__dict__)
    return result
