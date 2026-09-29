"""Fatia noturna sem janelas especiais ainda dependentes do terminal."""
from copy import deepcopy
from . import combat, peoples
from .constants import CENTER, Phase
from .models import Hero
from .night_rules import find_targets, order_players_for_house, ainai_destinations, teleport_ainai
from .state import get_player, log
from .turn import day_order, end_turn, start_turn, start_player_day

TYPES = {"night_attack", "night_pass", "finish_night", "night_resolve_choice",
         "night_ainai", "night_luide_move", "night_luide_spell", "night_window_done",
         "night_pact", "night_decline_pact", "night_clock", "night_skip_clock", "night_setup", "night_mandinga", "night_aiquara"}
SUPPORTED_HEROES = {
    "miyamoto", "arken", "ori", "barbadourada", "dain", "buin", "bein", "boin",
    "tintin", "don", "din", "garoche", "valendar", "dracula", "dandara",
    "lupa_lider", "cigana", "luarado", "joao_grandao", "pe_descalco", "caroco",
    "cobra", "zoia", "cova_rasa", "guarari", "baoba_ba", "bimbo_do_mal",
    "sao_tome", "zebum", "barba_negra", "purpura", "valtherion", "belial", "tuza",
    "rogue_devil", "vovo_gamba", "luna", "besouro", "iuna", "aiquara", "ainai", "luide_vampa",
}


def public_window(state):
    if state.phase != Phase.NIGHT or blockers(state):
        return None
    trial = deepcopy(state)
    prepare(trial)
    advance(trial)
    queue = [e for e in trial.web_night["queue"] if "unit_id" in e]
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
        from .heroes import hero_name
        names = sorted({hero_name(u.hero_id) for p in state.players for u in p.units
                        if isinstance(u, Hero) and u.is_alive() and u.hero_id not in SUPPORTED_HEROES})
        result.append("Janelas noturnas ainda não adaptadas: " + ", ".join(names))
    if any(p.pending_artifact_choice and p.pending_artifact_choice.get("kind")
           not in ("Q_D", "J_D", "BOIN") for p in state.players):
        result.append("Há uma escolha de artefato ainda não adaptada.")
    return result


def pending_owner(state):
    return (next((p for p in state.players if p.pending_artifact_choice), None)
            or next((p for p in state.players if p.demon_pact_offers), None))


def prepare(state):
    if state.web_night.get("turn") == state.turn:
        return
    setup = []
    for p in state.players:
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba" for u in p.units):
            setup.append({"kind": "vovo", "player_id": p.id})
    setup.append({"kind": "flames"})
    for pid in day_order(state):
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "aiquara"
               and u.statuses.get("aiquara_attacked_turn") != state.turn
               for u in get_player(state, pid).units):
            setup.append({"kind": "aiquara", "player_id": pid})
    for pid in day_order(state):
        p = get_player(state, pid)
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
               and "luna_origin_house" in u.statuses for u in p.units):
            setup.append({"kind": "luna", "player_id": pid})
    setup.extend({"kind": "ainai", "player_id": pid} for pid in day_order(state))
    for pid in day_order(state):
        p = get_player(state, pid)
        if (p.hand and p.besouro_mandinga_used_turn != state.turn
                and any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro" for u in p.units)):
            setup.append({"kind": "besouro", "player_id": pid})
    state.web_night = {"turn": state.turn, "queue": [], "setup": setup, "ready": False}
    advance(state)


def house_entries(state, house):
    queue = []
    pids = [pid for pid in day_order(state) if any(
        u.is_alive() and u.house == house for u in get_player(state, pid).units)]
    for pid in order_players_for_house(state, pids, house):
        queue.append({"kind": "luide", "house": house, "player_id": pid})
        queue.extend({"house": house, "player_id": pid, "unit_id": u.id}
                     for u in get_player(state, pid).units if u.is_alive() and u.house == house)
    return queue


def build_queue(state):
    houses = [CENTER] + [f"city_{pid}" for pid in reversed(day_order(state))]
    state.web_night["queue"] = [{"kind": "house", "house": h} for h in houses]
    state.web_night["ready"] = True


def luide_alive(state, pid):
    p = get_player(state, pid)
    return p.people == "vampiros" and any(isinstance(u, Hero) and u.is_alive()
        and u.hero_id == "luide_vampa" for u in p.units)


def schedule_arrival(state, unit):
    if unit.house in state.web_night.get("processed", []):
        state.web_night["queue"].insert(0, {"house": unit.house,
            "player_id": unit.owner_id, "unit_id": unit.id})


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
    setup = state.web_night.get("setup", [])
    while setup:
        entry = setup[0]
        if entry["kind"] == "flames":
            from .actions import barba_resolver_mar_de_chamas
            setup.pop(0)
            barba_resolver_mar_de_chamas(state)
            if pending_owner(state) is not None:
                advance(state)
                return
            continue
        p = get_player(state, entry["player_id"])
        if entry["kind"] == "ainai" and not ainai_destinations(state, p):
            setup.pop(0)
            continue
        hid = "vovo_gamba" if entry["kind"] == "vovo" else entry["kind"]
        if not any(isinstance(u, Hero) and u.is_alive() and u.hero_id == hid for u in p.units):
            setup.pop(0)
            continue
        state.active_player_id = p.id
        return
    if not state.web_night.get("ready", True):
        build_queue(state)
    queue = state.web_night["queue"]
    while queue:
        entry = queue[0]
        kind = entry.get("kind")
        if kind == "house":
            queue.pop(0)
            queue[:0] = house_entries(state, entry["house"]) + [{"kind": "end_house", "house": entry["house"]}]
        elif kind == "end_house":
            queue.pop(0)
            state.web_night.setdefault("processed", []).append(entry["house"])
            queue[:0] = [{"kind": "ainai", "player_id": pid} for pid in day_order(state)]
        elif kind == "ainai":
            if ainai_destinations(state, get_player(state, entry["player_id"])):
                break
            queue.pop(0)
        elif kind == "luide":
            if luide_alive(state, entry["player_id"]) and (entry.get("opened") or any(
                    u.is_alive() and u.house == entry["house"] and find_targets(state, u)
                    for u in get_player(state, entry["player_id"]).units)):
                entry["opened"] = True
                break
            queue.pop(0)
        elif attacks(state, entry):
            break
        else:
            queue.pop(0)
    if not queue:
        clock = clock_owner(state)
        if clock is not None:
            state.active_player_id = clock.id
            return
    alive = [p.id for p in state.players if p.city.is_alive()]
    state.active_player_id = (queue[0]["player_id"] if queue else
                              state.curuna_id if state.curuna_id in alive else
                              alive[0] if alive else state.curuna_id)


def clock_owner(state):
    if not state.combats_this_night or state.game_over:
        return None
    done = state.web_night.get("clock_done", [])
    return next((p for p in state.players if p.id not in done and p.city.is_alive()
                 and any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "rogue_devil"
                         and "relogio" in u.statuses.get("rogue_items", []) for u in p.units)), None)


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
        from .interaction_actions import _candidates, execute
        options = []
        for candidate in _candidates(trial, pending):
            kinds = {"resolve_artifact_choice": "night_resolve_choice",
                     "demon_pact": "night_pact", "decline_pact": "night_decline_pact"}
            if candidate["type"] not in kinds:
                continue
            from .actions import ActionError
            try:
                execute(deepcopy(trial), candidate)
            except (ActionError, ValueError):
                continue
            candidate["type"] = kinds[candidate["type"]]
            options.append(candidate)
        return options
    def offer(kind, params, label):
        return {"version": ACTION_VERSION, "type": kind, "player_id": pid,
                "params": params, "label": label}
    setup = trial.web_night.get("setup", [])
    window = setup[0] if setup else (trial.web_night["queue"][0] if trial.web_night["queue"] else {})
    if window.get("kind") == "ainai":
        return [offer("night_ainai", {"destination": h}, f"Ainai: teleportar para {h}")
                for h in ainai_destinations(trial, get_player(trial, pid))] + [
                    offer("night_window_done", {}, "Não teleportar Ainai")]
    if window.get("kind") == "luide":
        from .actions import move_unit, cast_spell, ActionError
        result = [offer("night_window_done", {}, "Concluir janela de Luide e declarar combates")]
        player = get_player(trial, pid)
        for unit in player.units:
            if not unit.is_alive():
                continue
            if unit.house == window["house"]:
                for destination in [CENTER] + [f"city_{p.id}" for p in trial.players]:
                    try:
                        move_unit(deepcopy(trial), pid, unit.id, destination)
                    except (ActionError, ValueError):
                        continue
                    result.append(offer("night_luide_move", {"unit_id": unit.id, "destination": destination},
                                        f"Mover {unit.id} para {destination}"))
            if not player.has_cast_spell_this_turn:
                try:
                    cast_spell(deepcopy(trial), pid, {"unit_id": unit.id})
                except (ActionError, ValueError):
                    continue
                result.append(offer("night_luide_spell", {"unit_id": unit.id}, f"Feitiço vampiro: {unit.id}"))
        return result
    if setup:
        if setup[0]["kind"] == "aiquara":
            from .actions import aiquara_atacar, ActionError
            options = [offer("night_setup", {"kind": "aiquara"}, "Não usar controle de Aiquara")]
            for owner in trial.players:
                if owner.id == pid:
                    continue
                for unit in owner.units:
                    if not unit.is_alive():
                        continue
                    for target_type, target_id, label in find_targets(trial, unit):
                        params = {"enemy_unit_id": unit.id, "target_type": target_type, "target_id": target_id}
                        try:
                            aiquara_atacar(deepcopy(trial), pid, **params)
                        except (ActionError, combat.CombatError, ValueError):
                            continue
                        options.append(offer("night_aiquara", params, f"Aiquara: {unit.id} → {label}"))
            return options
        if setup[0]["kind"] == "besouro":
            from .actions import besouro_mandinga, ActionError
            from .interaction_actions import artifact_choices
            from .artifacts import card_display
            player = get_player(trial, pid)
            options = [offer("night_setup", {"kind": "besouro"}, "Não usar Mandinga")]
            for card in dict.fromkeys(player.hand):
                if card == "PENA":
                    continue
                for choice, label in artifact_choices(trial, player, card):
                    try:
                        besouro_mandinga(deepcopy(trial), pid, card, choice)
                    except (ActionError, ValueError):
                        continue
                    options.append(offer("night_mandinga", {"card_id": card, "choice": choice},
                                         f"Mandinga: {card_display(card)} {label}"))
            return options
        if setup[0]["kind"] == "vovo":
            return [offer("night_setup", {"kind": "vovo", "position": i},
                          f"Vovó: declarar na posição {i}") for i in range(1, 5)]
        return [offer("night_setup", {"kind": "luna", "return": value},
                      "Luna: retornar à origem" if value else "Luna: permanecer aqui")
                for value in (True, False)]
    queue = trial.web_night["queue"]
    if not queue:
        if clock_owner(trial) is not None:
            return ([offer("night_clock", {"destination": house}, f"Relógio: ir para {house}")
                     for house in dict.fromkeys(trial.combats_this_night)]
                    + [offer("night_skip_clock", {}, "Não usar Relógio de bolso")])
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
                      if a["type"] == action.get("type") and a["params"] == action.get("params")
                      and all(type(action["params"][k]) is type(v) for k, v in a["params"].items())), None)
    if candidate is None:
        return _error("not_legal", "Declaração noturna indisponível.")
    trial = deepcopy(state)
    prepare(trial)
    advance(trial)
    kind = candidate["type"]
    old_turn = trial.turn
    if kind in ("night_ainai", "night_window_done"):
        source = trial.web_night["setup"] or trial.web_night["queue"]
        source.pop(0)
        if kind == "night_ainai":
            unit = teleport_ainai(trial, get_player(trial, candidate["player_id"]), candidate["params"]["destination"])
            schedule_arrival(trial, unit)
        advance(trial)
    elif kind in ("night_luide_move", "night_luide_spell"):
        from .actions import move_unit, cast_spell
        if kind == "night_luide_move":
            move_unit(trial, candidate["player_id"], **candidate["params"])
            schedule_arrival(trial, combat._find_unit(trial, candidate["params"]["unit_id"]))
        else:
            cast_spell(trial, candidate["player_id"], candidate["params"])
        advance(trial)
    elif kind == "night_aiquara":
        from .actions import aiquara_atacar
        aiquara_atacar(trial, candidate["player_id"], **candidate["params"])
        trial.web_night["setup"].pop(0)
        advance(trial)
    elif kind == "night_mandinga":
        from .actions import besouro_mandinga
        besouro_mandinga(trial, candidate["player_id"], **candidate["params"])
        trial.web_night["setup"].pop(0)
        advance(trial)
    elif kind == "night_setup":
        p = get_player(trial, candidate["player_id"])
        if candidate["params"]["kind"] == "vovo":
            p.vovo_position = candidate["params"]["position"]
        elif candidate["params"].get("return"):
            from .night_rules import return_luna
            return_luna(trial, p)
        trial.web_night["setup"].pop(0)
        advance(trial)
    elif kind in ("night_pact", "night_decline_pact"):
        from .interaction_actions import execute
        original = dict(candidate, type="demon_pact" if kind == "night_pact" else "decline_pact")
        execute(trial, original)
        advance(trial)
    elif kind in ("night_clock", "night_skip_clock"):
        if kind == "night_clock":
            from .actions import rogue_clock_move
            rogue_clock_move(trial, candidate["player_id"], candidate["params"]["destination"])
        trial.web_night.setdefault("clock_done", []).append(candidate["player_id"])
        advance(trial)
    elif kind == "night_resolve_choice":
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
             "visibility": {"kind": "private" if kind in ("night_resolve_choice", "night_pact", "night_decline_pact") else "public",
                            "player_ids": [pid] if kind in ("night_resolve_choice", "night_pact", "night_decline_pact") else []}}
    projection = {"version": EVENT_VERSION, "type": "player_view_updated", "turn": trial.turn,
                  "phase": trial.phase.value, "participants": [pid],
                  "data": {"view": view_for_player(trial, pid)},
                  "visibility": {"kind": "private", "player_ids": [pid]}}
    state.__dict__.update(trial.__dict__)
    return {"success": True, "error": None, "events": [event, projection]}
