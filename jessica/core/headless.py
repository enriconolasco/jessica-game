from __future__ import annotations

from copy import deepcopy

from .actions import (ActionError, build_monument, collect_resources,
                      raise_city_life)
from .constants import (CITY_LIFE_COST_GOLD, MONUMENT_COST_GOLD, Phase,
                        RESOURCES_PER_DAY)
from .models import GameState, Hero, Troop, Unit
from .state import get_player


ACTION_VERSION = "action-v0.1"
EVENT_VERSION = "event-v0.1"
VIEW_VERSION = "view-v0.1"
SAVE_VERSION = "save-v0.1"

PUBLIC_STATUS_KEYS = {
    "amaldicoado_until_turn",
    "cannot_attack_on_turn",
    "centauro_until_turn",
    "espectro_until_turn",
    "invisivel_until_turn",
    "invulneravel_until_turn",
    "lobisomem_until_turn",
    "morcego_until_turn",
    "sono_until_turn",
    "summoned_turn",
}


def _action(action_type: str, player_id: int, **params) -> dict:
    return {
        "version": ACTION_VERSION,
        "type": action_type,
        "player_id": player_id,
        "params": params,
    }


def legal_actions(state: GameState, player_id: int) -> list[dict]:
    """Enumera as ações já migradas para a porta v0.1."""
    try:
        player = get_player(state, player_id)
    except ValueError:
        return []
    if state.game_over or state.phase != Phase.DAY or not player.city.is_alive():
        return []
    actions = []
    if not player.has_collected_this_turn:
        actions.extend(
            _action("collect_resources", player_id, gold=gold,
                    magic=RESOURCES_PER_DAY - gold)
            for gold in range(RESOURCES_PER_DAY + 1)
        )
    is_moving_dragon_base = (
        player.people == "dragoes"
        and player.chosen_hero_id in ("barba_negra", "valtherion")
    )
    if state.turn < 13 and not is_moving_dragon_base:
        max_raise = min(
            player.city.life_max - player.city.life,
            player.city.gold // CITY_LIFE_COST_GOLD,
        )
        actions.extend(_action("raise_city_life", player_id, times=times)
                       for times in range(1, max_raise + 1))
    if (not player.city.has_monument
            and player.city.life == player.city.life_max
            and player.city.gold >= MONUMENT_COST_GOLD):
        actions.append(_action("build_monument", player_id))
    return actions


def _error(code: str, message: str, **details) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
        "events": [],
    }


def apply_action(state: GameState, action: dict) -> dict:
    if not isinstance(action, dict):
        return _error("invalid_action", "Ação deve ser um objeto.")
    if action.get("version") != ACTION_VERSION:
        return _error("unsupported_action_version", "Versão de ação não suportada.")
    action_type = action.get("type")
    if action_type not in {"collect_resources", "raise_city_life", "build_monument"}:
        return _error("unsupported_action", "Tipo de ação ainda não adaptado.",
                      action_type=action.get("type"))

    player_id = action.get("player_id")
    params = action.get("params")
    if isinstance(player_id, bool) or not isinstance(player_id, int):
        return _error("invalid_action", "player_id inválido.")
    expected = {"collect_resources": {"gold", "magic"},
                "raise_city_life": {"times"}, "build_monument": set()}[action_type]
    if not isinstance(params, dict) or set(params) != expected:
        return _error("invalid_action", "Parâmetros inválidos para a ação.")
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in params.values()):
        return _error("invalid_action", "Parâmetros numéricos devem ser inteiros.")

    candidate = _action(action_type, player_id, **params)
    if candidate not in legal_actions(state, player_id):
        return _error("not_legal", "Ação não é legal no estado atual.")

    try:
        before = deepcopy(get_player(state, player_id).city)
        if action_type == "collect_resources":
            collect_resources(state, player_id, params["gold"], params["magic"])
        elif action_type == "raise_city_life":
            raise_city_life(state, player_id, params["times"])
        else:
            build_monument(state, player_id)
    except (ActionError, ValueError) as exc:
        return _error("domain_error", str(exc))

    event_types = {"collect_resources": "resources_collected",
                   "raise_city_life": "city_life_raised",
                   "build_monument": "monument_built"}
    after = get_player(state, player_id).city
    data = {"player_id": player_id}
    if action_type == "collect_resources":
        data.update(gold=params["gold"], magic=params["magic"])
    elif action_type == "raise_city_life":
        data.update(times=params["times"], gold_spent=before.gold - after.gold,
                    life_before=before.life, life_after=after.life)
    else:
        data.update(gold_spent=before.gold - after.gold)
    event = {
        "version": EVENT_VERSION,
        "type": event_types[action_type],
        "turn": state.turn,
        "phase": state.phase.value,
        "participants": [player_id],
        "data": data,
        "visibility": {"kind": "public", "player_ids": []},
    }
    return {"success": True, "error": None, "events": [event]}


def _public_statuses(unit: Unit) -> dict:
    return {
        key: deepcopy(value)
        for key, value in unit.statuses.items()
        if key in PUBLIC_STATUS_KEYS
    }


def _unit_view(unit: Unit) -> dict:
    result = {
        "id": unit.id,
        "owner_id": unit.owner_id,
        "kind": "hero" if isinstance(unit, Hero) else "troop",
        "house": unit.house,
        "life": unit.life,
        "life_max": unit.life_max,
        "moves_this_turn": unit.moves_this_turn,
        "max_moves_this_turn": unit.max_moves_this_turn,
        "attacks_made_this_night": unit.attacks_made_this_night,
        "max_attacks_this_night": unit.max_attacks_this_night,
        "resistance_stacks": unit.resistance_stacks,
        "double_damage": unit.double_damage,
        "statuses": _public_statuses(unit),
    }
    if isinstance(unit, Hero):
        result["hero_id"] = unit.hero_id
    elif isinstance(unit, Troop):
        result["archetype"] = unit.archetype.value
    return result


def view_for_player(state: GameState, player_id: int) -> dict:
    viewer = get_player(state, player_id)
    players = []
    board = {"units": []}
    for player in state.players:
        players.append({
            "id": player.id,
            "name": player.name,
            "people": player.people,
            "chosen_hero_id": player.chosen_hero_id,
            "city": {
                "life": player.city.life,
                "life_max": player.city.life_max,
                "gold": player.city.gold,
                "magic": player.city.magic,
                "has_monument": player.city.has_monument,
            },
            "hand_count": len(player.hand),
            "canastra": list(player.canastra),
        })
        board["units"].extend(_unit_view(unit) for unit in player.units
                              if unit.is_alive())

    return {
        "version": VIEW_VERSION,
        "viewer_id": player_id,
        "turn": state.turn,
        "phase": state.phase.value,
        "curuna_id": state.curuna_id,
        "game_over": state.game_over,
        "winner_id": state.winner_id,
        "players": players,
        "board": board,
        "shop": {"size": state.shop.size()},
        "self": {
            "hand": list(viewer.hand),
            "pending_choice": deepcopy(viewer.pending_artifact_choice),
            "bets": {
                "H": viewer.bet_H_target,
                "C": viewer.bet_C_target,
                "D": viewer.bet_D_target,
                "S": viewer.bet_S_target,
            },
            "correct_bets": viewer.correct_bets,
        },
        # event_log atual mistura texto público e privado; não é exposto.
        "events": [],
    }


def apply_event_to_view(view: dict, event: dict) -> dict:
    """Projeta um evento v0.1 sem acessar o GameState completo."""
    if event.get("version") != EVENT_VERSION:
        raise ValueError("Versão de evento não suportada.")
    visibility = event.get("visibility", {})
    kind = visibility.get("kind")
    viewer_id = view.get("viewer_id")
    visible = kind == "public"
    if kind == "private":
        visible = viewer_id in event.get("participants", [])
    elif kind == "players":
        visible = viewer_id in visibility.get("player_ids", [])
    if not visible:
        raise ValueError("Evento não é visível para este jogador.")

    projected = deepcopy(view)
    if event.get("type") in {"resources_collected", "city_life_raised", "monument_built"}:
        data = event["data"]
        player = next((p for p in projected["players"]
                       if p["id"] == data["player_id"]), None)
        if player is None:
            raise ValueError("Participante do evento não existe na visão.")
        if event["type"] == "resources_collected":
            player["city"]["gold"] += data["gold"]
            player["city"]["magic"] += data["magic"]
        elif event["type"] == "city_life_raised":
            player["city"]["gold"] -= data["gold_spent"]
            player["city"]["life"] = data["life_after"]
        else:
            player["city"]["gold"] -= data["gold_spent"]
            player["city"]["has_monument"] = True
    else:
        raise ValueError("Tipo de evento ainda não projetável.")
    projected["events"].append(deepcopy(event))
    return projected
