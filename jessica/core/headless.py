from __future__ import annotations

from copy import deepcopy
from collections import Counter

from .actions import (ActionError, build_monument, buy_artifact_with_gold,
                      collect_resources, move_unit, raise_city_life, sell_artifact,
                      summon_hero, summon_troop, transmute_artifact_with_magic)
from .constants import (CENTER, CITY_HOUSES, CITY_LIFE_COST_GOLD, MONUMENT_COST_GOLD, Phase,
                        RESOURCES_PER_DAY, TROOP_MAX_LIFE, TroopArchetype)
from .constants import MONUMENT_BONUS_INTERVAL
from .models import GameState, Hero, Troop, Unit
from .state import get_player
from .turn import day_order, end_day, start_player_day
from . import peoples
from . import interaction_actions
from . import night_actions
from .combat import armor_simulation


ACTION_VERSION = "action-v0.1"
EVENT_VERSION = "event-v0.1"
VIEW_VERSION = "view-v0.1"
SAVE_VERSION = "save-v0.1"
ACTION_LABELS = {
    "collect_resources": "Coletar recursos",
    "raise_city_life": "Aumentar vida da cidade",
    "build_monument": "Construir monumento",
    "summon_troop": "Invocar tropa",
    "summon_hero": "Invocar herói",
    "move_unit": "Mover unidade",
    "buy_artifact_gold": "Comprar artefato com Ouro",
    "transmute_artifact_magic": "Transmutar artefato com Magia",
    "sell_artifact": "Vender artefato",
    "end_turn": "Encerrar turno",
}

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
    "barba_hero_mode_turn", "mar_chamas_queued_turn", "mar_chamas_cooldown_until_turn",
    "rogue_items", "rogue_resist_heroes", "demon_execute_weaker",
    "cabaca_used_turn", "dragon_base", "dragon_heart_resistance", "permanent_centaur",
    "k_s_active", "can_attack_city_until_turn", "lupa_resist_until_turn",
}


def _action(action_type: str, player_id: int, **params) -> dict:
    return {
        "version": ACTION_VERSION,
        "type": action_type,
        "label": ACTION_LABELS[action_type],
        "player_id": player_id,
        "params": params,
    }


@armor_simulation
def legal_actions(state: GameState, player_id: int) -> list[dict]:
    """Enumera as ações já migradas para a porta v0.1."""
    if state.web_reaction:
        from .reactions import legal
        return legal(state, player_id)
    if state.phase == Phase.NIGHT:
        return night_actions.legal(state, player_id)
    try:
        player = get_player(state, player_id)
    except ValueError:
        return []
    if (state.game_over or state.phase != Phase.DAY or not player.city.is_alive()
            or state.active_player_id not in (None, player_id)):
        return []
    if interaction_actions.blocked_by_choice(state, player):
        return interaction_actions.legal_interactions(state, player_id)
    if player.skip_day_turn == state.turn:
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
    houses = [f"city_{player_id}"]
    baoba = next((u for u in player.units if isinstance(u, Hero) and u.is_alive()
                  and u.hero_id == "baoba_ba"), None)
    if baoba is not None and baoba.house not in houses:
        houses.append(baoba.house)
    for archetype in peoples.available_archetypes(player, state):
        for life in range(1, TROOP_MAX_LIFE[archetype.value] + 1):
            for house in houses:
                candidate = _action("summon_troop", player_id,
                                    archetype=archetype.value, life=life, house=house)
                trial = deepcopy(state)
                try:
                    summon_troop(trial, player_id, archetype, life, house)
                except (ActionError, ValueError):
                    continue
                actions.append(candidate)
    hero_choices = [None]
    if player.people == "mortos_vivos":
        from .heroes import heroes_for_people
        hero_choices = [h.hero_id for h in heroes_for_people("mortos_vivos")]
    elif (player.people == peoples.PEOPLE_GNOMOS
          and peoples.PEOPLE_MORTOS_VIVOS in
          peoples.sao_tome_effective_peoples(state, player)):
        hero_choices = ["bimbo_do_mal", "sao_tome", "zebum"]
    for hero_id in hero_choices:
        params = {} if hero_id is None else {"hero_id": hero_id}
        candidate = _action("summon_hero", player_id, **params)
        trial = deepcopy(state)
        try:
            summon_hero(trial, player_id, force_hero_id=hero_id)
        except (ActionError, ValueError):
            continue
        actions.append(candidate)
    for unit in player.units:
        if not unit.is_alive():
            continue
        destinations = [CENTER] if unit.house.startswith("city_") else list(CITY_HOUSES)
        for destination in destinations:
            candidate = _action("move_unit", player_id, unit_id=unit.id,
                                destination=destination)
            trial = deepcopy(state)
            try:
                move_unit(trial, player_id, unit.id, destination)
            except (ActionError, ValueError):
                continue
            actions.append(candidate)
    for action_type, operation in (
            ("buy_artifact_gold", buy_artifact_with_gold),
            ("transmute_artifact_magic", transmute_artifact_with_magic)):
        trial = deepcopy(state)
        try:
            operation(trial, player_id)
        except (ActionError, ValueError):
            continue
        actions.append(_action(action_type, player_id))
    for card_id in dict.fromkeys(player.hand):
        trial = deepcopy(state)
        try:
            sell_artifact(trial, player_id, card_id)
        except (ActionError, ValueError):
            continue
        actions.append(_action("sell_artifact", player_id, card_id=card_id))
    actions.append(_action("end_turn", player_id))
    actions.extend(interaction_actions.legal_interactions(state, player_id))
    return actions


def _error(code: str, message: str, **details) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
        "events": [],
    }


def apply_action(state: GameState, action: dict) -> dict:
    from .reactions import apply
    return apply(state, action, _apply_action_now)


def _apply_action_now(state: GameState, action: dict) -> dict:
    if not isinstance(action, dict):
        return _error("invalid_action", "Ação deve ser um objeto.")
    if action.get("version") != ACTION_VERSION:
        return _error("unsupported_action_version", "Versão de ação não suportada.")
    action_type = action.get("type")
    if isinstance(action_type, str) and action_type in night_actions.TYPES:
        return night_actions.apply(state, action)
    if isinstance(action_type, str) and action_type in interaction_actions.LABELS:
        return interaction_actions.apply_interaction(state, action)
    if action_type not in {"collect_resources", "raise_city_life", "build_monument",
                           "summon_troop", "summon_hero", "move_unit", "end_turn",
                           "buy_artifact_gold", "transmute_artifact_magic",
                           "sell_artifact"}:
        return _error("unsupported_action", "Tipo de ação ainda não adaptado.",
                      action_type=action.get("type"))

    player_id = action.get("player_id")
    params = action.get("params")
    if isinstance(player_id, bool) or not isinstance(player_id, int):
        return _error("invalid_action", "player_id inválido.")
    expected = {"collect_resources": {"gold", "magic"},
                "raise_city_life": {"times"}, "build_monument": set(),
                "summon_troop": {"archetype", "life", "house"},
                "summon_hero": set(),
                "move_unit": {"unit_id", "destination"},
                "buy_artifact_gold": set(),
                "transmute_artifact_magic": set(),
                "sell_artifact": {"card_id"},
                "end_turn": set()}[action_type]
    if action_type == "summon_hero" and isinstance(params, dict) and set(params) == {"hero_id"}:
        expected = {"hero_id"}
    if not isinstance(params, dict) or set(params) != expected:
        return _error("invalid_action", "Parâmetros inválidos para a ação.")
    numeric_keys = {"gold", "magic", "times", "life"} & set(params)
    if any(isinstance(params[key], bool) or not isinstance(params[key], int)
           for key in numeric_keys):
        return _error("invalid_action", "Parâmetros numéricos devem ser inteiros.")

    candidate = _action(action_type, player_id, **params)
    if candidate not in legal_actions(state, player_id):
        return _error("not_legal", "Ação não é legal no estado atual.")

    try:
        before = deepcopy(get_player(state, player_id).city)
        moved = None
        origin = None
        if action_type == "move_unit":
            moved = next(u for u in get_player(state, player_id).units
                         if u.id == params["unit_id"])
            origin = moved.house
        if action_type == "collect_resources":
            collect_resources(state, player_id, params["gold"], params["magic"])
        elif action_type == "raise_city_life":
            raise_city_life(state, player_id, params["times"])
        elif action_type == "build_monument":
            build_monument(state, player_id)
        elif action_type == "summon_troop":
            summoned = summon_troop(state, player_id, TroopArchetype(params["archetype"]),
                                    params["life"], params["house"])
        elif action_type == "summon_hero":
            summoned = summon_hero(state, player_id, force_hero_id=params.get("hero_id"))
        elif action_type == "move_unit":
            move_unit(state, player_id, params["unit_id"], params["destination"])
        elif action_type == "buy_artifact_gold":
            artifact = buy_artifact_with_gold(state, player_id)
        elif action_type == "transmute_artifact_magic":
            artifact = transmute_artifact_with_magic(state, player_id)
        elif action_type == "sell_artifact":
            artifact = params["card_id"]
            sell_artifact(state, player_id, artifact)
        else:
            player = get_player(state, player_id)
            player.has_played_day_this_turn = True
            order = day_order(state)
            index = order.index(player_id)
            if index + 1 < len(order):
                state.active_player_id = order[index + 1]
                start_player_day(state, state.active_player_id)
            else:
                state.active_player_id = None
                end_day(state)
                if not night_actions.blockers(state):
                    night_actions.prepare(state)
    except (ActionError, ValueError) as exc:
        return _error("domain_error", str(exc))

    event_types = {"collect_resources": "resources_collected",
                   "raise_city_life": "city_life_raised",
                   "build_monument": "monument_built",
                   "summon_troop": "unit_summoned",
                   "summon_hero": "unit_summoned",
                   "move_unit": "unit_moved",
                   "buy_artifact_gold": "artifact_obtained",
                   "transmute_artifact_magic": "artifact_obtained",
                   "sell_artifact": "artifact_sold",
                   "end_turn": "player_turn_ended"}
    after = get_player(state, player_id).city
    data = {"player_id": player_id}
    if action_type == "collect_resources":
        data.update(gold=params["gold"], magic=params["magic"])
    elif action_type == "raise_city_life":
        data.update(times=params["times"], gold_spent=before.gold - after.gold,
                    life_before=before.life, life_after=after.life)
    else:
        data.update(gold_spent=before.gold - after.gold)
    if action_type in {"summon_troop", "summon_hero"}:
        data.update(unit=_unit_view(summoned, state), city_gold_after=after.gold,
                    city_magic_after=after.magic)
    elif action_type == "move_unit":
        data.update(unit_id=moved.id, origin=origin, destination=moved.house,
                    moves_this_turn=moved.moves_this_turn, unit=_unit_view(moved, state))
    elif action_type == "end_turn":
        data.update(next_player_id=state.active_player_id, phase_after=state.phase.value)
    elif action_type in {"buy_artifact_gold", "transmute_artifact_magic"}:
        data.update(card_id=artifact, pending_choice=artifact is None,
                    gold_spent=before.gold - after.gold,
                    magic_spent=before.magic - after.magic)
    elif action_type == "sell_artifact":
        data.update(card_id=artifact, gold_after=after.gold, magic_after=after.magic)
    private = action_type in {"buy_artifact_gold", "transmute_artifact_magic"}
    public = view_for_player(state, player_id)
    data["public_after"] = {key: public[key] for key in ("players", "board", "conditions")}
    event = {
        "version": EVENT_VERSION,
        "type": event_types[action_type],
        "turn": state.turn,
        "phase": state.phase.value,
        "participants": [player_id],
        "data": data,
        "visibility": ({"kind": "private", "player_ids": [player_id]}
                       if private else {"kind": "public", "player_ids": []}),
    }
    return {"success": True, "error": None, "events": [event]}


def _public_statuses(unit: Unit) -> dict:
    return {
        key: deepcopy(value)
        for key, value in unit.statuses.items()
        if key in PUBLIC_STATUS_KEYS
    }


def _unit_view(unit: Unit, state: GameState | None = None) -> dict:
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
        "hero_can_attack_city": unit.hero_can_attack_city,
        "statuses": _public_statuses(unit),
    }
    if isinstance(unit, Hero):
        result["hero_id"] = unit.hero_id
    elif isinstance(unit, Troop):
        result["archetype"] = unit.archetype.value
    if state is not None:
        from .combat import _effective_max_attacks
        result["infected"] = peoples.is_unit_infected(state, unit)
        result["effective_max_attacks"] = _effective_max_attacks(state, unit)
        owner = get_player(state, unit.owner_id)
        result["owner_invulnerable"] = owner.invulnerable_until_end_turn
        result["armor_active"] = owner.armor_active_until_turn >= state.turn
        result["first_strike"] = owner.bater_primeiro_turn == state.turn
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
            "spell_cooldown_until_turn": player.spell_cooldown_until_turn,
            "armor_active_until_turn": player.armor_active_until_turn,
            "skip_day_turn": player.skip_day_turn,
            "skip_night_turn": player.skip_night_turn,
            "next_monument_turn": (state.turn // MONUMENT_BONUS_INTERVAL + 1) * MONUMENT_BONUS_INTERVAL
                if player.city.has_monument and player.city.is_alive() else None,
            "stats": {key: value for key, value in player.stats.items()
                      if key in {"gold_collected", "magic_collected", "troops_summoned", "heroes_summoned",
                                 "spells_cast", "damage_dealt", "damage_taken", "kills", "deaths",
                                 "artifacts_bought", "artifacts_played", "artifacts_sold"}},
            "city": {
                "life": player.city.life,
                "life_max": player.city.life_max,
                "gold": player.city.gold,
                "magic": player.city.magic,
                "has_monument": player.city.has_monument,
            },
            "hand_count": len(player.hand),
            "canastra": list(player.canastra),
            "field_artifacts": [artifact.card_id for artifact in player.field_artifacts],
            "active_artifacts": [{"card_id": a.card_id, "details": {
                key: deepcopy(value) for key, value in a.extra.items()
                if key in {"hero_unit_id", "troop_unit_id", "target_unit_id", "target_player_id", "original_owner_id"}}}
                for a in player.field_artifacts],
        })
        board["units"].extend(_unit_view(unit, state) for unit in player.units
                              if unit.is_alive())

    night_window = night_actions.public_window(state)
    active_player_id = state.active_player_id
    if night_window and not state.web_reaction:
        active_player_id = night_window["player_id"]
    view = {
        "version": VIEW_VERSION,
        "viewer_id": player_id,
        "turn": state.turn,
        "phase": state.phase.value,
        "curuna_id": state.curuna_id,
        "turn_order": list(state.turn_order),
        "active_player_id": active_player_id,
        "game_over": state.game_over,
        "winner_id": state.winner_id,
        "night_limitations": night_actions.blockers(state) if state.phase == Phase.NIGHT else [],
        "night_window": night_window,
        "players": players,
        "board": board,
        "shop": {"size": state.shop.size(), "counts": dict(Counter(state.shop.deck))},
        "demon_pacts": deepcopy(state.demon_pacts),
        "conditions": [entry for player in state.players
                       for entry in _condition_records(player)],
        "scheduled_effects": [{key: deepcopy(e.get(key)) for key in ("player_id", "kind", "due_turn")}
                              for e in state.pending_effects],
        "timeline": [{"turn": e.get("turn"), "resources": {
            str(pid): {k: v for k, v in values.items() if k in ("gold", "magic", "life")}
            for pid, values in e.get("resources", {}).items()}} for e in state.timeline],
        "self": {
            "armor_reaction": deepcopy(state.web_reaction.get("request"))
                if state.web_reaction.get("request", {}).get("player_id") == player_id else None,
            "spell_copia_id": viewer.spell_copia_id,
            "spell_cooldown_until_turn": viewer.spell_cooldown_until_turn,
            "has_cast_spell_this_turn": viewer.has_cast_spell_this_turn,
            "hand": list(viewer.hand),
            "pending_choice": deepcopy(viewer.pending_artifact_choice),
            "bets": {
                "H": viewer.bet_H_target,
                "C": viewer.bet_C_target,
                "D": viewer.bet_D_target,
                "S": viewer.bet_S_target,
            },
            "correct_bets": viewer.correct_bets,
            "demon_pact_offers": deepcopy(viewer.demon_pact_offers),
            "pending_heals": viewer.pending_heals,
            "baoba_payments": viewer.baoba_pagamentos,
            "rogue_items": list(viewer.rogue_items),
            "inherited_peoples": sorted(peoples.sao_tome_effective_peoples(state, viewer) - {peoples.PEOPLE_GNOMOS})
                if viewer.people == "gnomos_duendes" else [],
        },
        # event_log atual mistura texto público e privado; não é exposto.
        "events": [],
    }
    preview = state.web_reaction.get("preview")
    if preview:
        for key in ("players", "board", "conditions", "shop", "demon_pacts"):
            view[key] = deepcopy(preview[key])
        if state.web_reaction["request"]["player_id"] == player_id:
            view["self"].update({key: deepcopy(value) for key, value in preview["self"].items()
                                if key != "armor_reaction"})
    return view


def _condition_records(player):
    records = []
    for sig in player.empalados:
        records.append({"owner_id": player.id, "condition": "Empalado", "signature": deepcopy(sig)})
    for entry in player.dwarf_empalados:
        records.append({"owner_id": player.id, "condition": "Empalado por Soneca",
                        "signature": deepcopy(entry.get("sig", {})),
                        "release_curuna_id": entry.get("dwarf_owner_id")})
    for entry in player.infectados:
        records.append({"owner_id": entry.get("owner_id"), "controller_id": player.id,
                        "condition": "Infectado", "unit_id": entry.get("unit_id"),
                        "signature": {"kind": entry.get("kind"), "id": entry.get("id")}})
    return records


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
    if event.get("type") == "player_view_updated":
        updated = event.get("data", {}).get("view", {})
        if updated.get("viewer_id") != viewer_id:
            raise ValueError("Visão pertence a outro jogador.")
        projected = deepcopy(updated)
        projected["events"] = deepcopy(view.get("events", [])) + [deepcopy(event)]
        return projected
    if event.get("type") in ("interaction_resolved", "night_action_resolved", "armor_payment_requested"):
        projected["events"].append(deepcopy(event))
        return projected
    if event.get("type") in ("public_roll", "combat_house_opened", "day_restored", "public_state_changed"):
        data = event.get("data", {})
        for change in data.get("changes", []):
            if change["kind"] in ("city", "player"):
                player = next(p for p in projected["players"] if p["id"] == change["player_id"])
                target = player["city"] if change["kind"] == "city" else player
                target[change["field"]] = deepcopy(change["after"])
            elif change["kind"] == "unit":
                unit = change["after"] or change["before"]
                projected["board"]["units"] = [u for u in projected["board"]["units"] if u["id"] != unit["id"]]
                if change["after"] is not None:
                    projected["board"]["units"].append(deepcopy(change["after"]))
            elif change["kind"] == "conditions":
                projected["conditions"] = deepcopy(change["after"])
        projected.update(deepcopy(data.get("public_after", {})))
        projected["events"].append(deepcopy(event))
        return projected
    if event.get("type") in {"resources_collected", "city_life_raised", "monument_built",
                              "unit_summoned", "unit_moved", "player_turn_ended"}:
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
        elif event["type"] == "monument_built":
            player["city"]["gold"] -= data["gold_spent"]
            player["city"]["has_monument"] = True
        if event["type"] == "unit_summoned":
            player["city"]["gold"] = data["city_gold_after"]
            player["city"]["magic"] = data["city_magic_after"]
            projected["board"]["units"].append(deepcopy(data["unit"]))
        elif event["type"] == "unit_moved":
            unit = next((u for u in projected["board"]["units"]
                         if u["id"] == data["unit_id"]), None)
            if unit is None:
                raise ValueError("Unidade movida não existe na visão.")
            unit["house"] = data["destination"]
            unit["moves_this_turn"] = data["moves_this_turn"]
        elif event["type"] == "player_turn_ended":
            projected["active_player_id"] = data["next_player_id"]
            projected["phase"] = data["phase_after"]
    else:
        raise ValueError("Tipo de evento ainda não projetável.")
    projected.update(deepcopy(event.get("data", {}).get("public_after", {})))
    projected["events"].append(deepcopy(event))
    return projected
