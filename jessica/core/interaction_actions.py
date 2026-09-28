"""Adaptadores de escolhas do Dia. As regras são executadas pelo core existente."""
from copy import deepcopy
from itertools import combinations
import json

from . import actions as core, artifacts_effects, heroes, peoples
from . import spell_choices
from .artifacts import card_display
from .constants import CENTER, CITY_HOUSES, Phase, TroopArchetype
from .models import Hero
from .state import get_player

LABELS = {
    "play_artifact": "Jogar artefato", "resolve_artifact_choice": "Resolver escolha pendente",
    "use_pena": "Usar Pena", "use_heal": "Usar cura", "hero_ability": "Habilidade de herói",
    "demon_pact": "Firmar pacto", "decline_pact": "Recusar pacto",
    "cast_spell": "Usar feitiço", "reroll_spell": "São Tomé: rerrolar feitiço",
}
ABILITIES = {
    "arken": (core.arken_espolia, "Arken: Espoliar"),
    "tintin": (core.tintin_ficar_invisivel, "Dunga: invisibilidade"),
    "dandara": (core.dandara_invisibilidade, "Dandara: invisibilidade"),
    "purpura": (core.purpura_invisibilidade, "Púrpura: invisibilidade"),
    "barba_flames": (core.barba_mar_de_chamas, "Barba Negra: preparar Mar de Chamas"),
    "barba_combat": (core.barba_combater_como_heroi, "Barba Negra: combater como herói"),
    "baoba": (core.baoba_pagar_magia, "Baobá: pagar Magia"),
    "bimbo_hide": (core.bimbo_invisibilidade, "Bimbo: invisibilidade"),
    "bimbo_artifact": (core.bimbo_gastar_5, "Bimbo: obter artefato"),
    "guarari": (core.transformar_em_centauro, "Guarari: transformar aliado"),
    "valtherion": (core.valtherion_chamado, "Valtherion: Chamado"),
}


def blocked_by_choice(player):
    return bool(player.pending_artifact_choice or any(
        offer.get("source") == "rogue_devil" for offer in player.demon_pact_offers))


def _offer(kind, pid, params, description):
    from .headless import ACTION_VERSION
    return {"version": ACTION_VERSION, "type": kind, "player_id": pid,
            "params": params, "label": LABELS[kind], "description": description}


def artifact_choices(state, player, card):
    kind = artifacts_effects.choice_type(card)
    if kind in ("own_unit", "any_unit", "any_enemy_unit"):
        for owner in state.players:
            if not owner.city.is_alive() or (kind == "own_unit" and owner.id != player.id):
                continue
            if kind == "any_enemy_unit" and owner.id == player.id:
                continue
            for unit in owner.units:
                if unit.is_alive():
                    name = heroes.hero_name(unit.hero_id) if isinstance(unit, Hero) else unit.id
                    yield {"unit_id": unit.id}, f"{name} ({owner.name}, {unit.life}/{unit.life_max})"
    elif kind == "people_hero":
        if player.chosen_hero_id != "seven_dwarves":
            for hero in heroes.heroes_for_people(player.people):
                yield {"hero_id": hero.hero_id}, hero.name
    elif kind == "house":
        yield {"house": CENTER}, "Centro"
        for owner in state.players:
            if owner.city.is_alive():
                yield {"house": f"city_{owner.id}"}, f"Cidade de {owner.name}"
    elif kind == "any_player":
        for owner in state.players:
            if owner.id != player.id and owner.city.is_alive():
                yield {"target_player_id": owner.id}, owner.name
    else:
        yield {}, ""


def _candidates(state, player):
    pid = player.id
    pending = player.pending_artifact_choice
    if pending:
        if pending["kind"] in ("J_D", "BOIN"):
            count = pending.get("pick", 1)
            unique = dict.fromkeys(combinations(pending["cards"], count))
            for cards in unique:
                yield _offer("resolve_artifact_choice", pid, {"kept_cards": list(cards)},
                             "Ficar com " + ", ".join(card_display(card) for card in cards))
        elif pending["kind"] == "Q_D":
            for resource, label in (("gold", "Ouro"), ("magic", "Magia")):
                yield _offer("resolve_artifact_choice", pid, {"resource": resource},
                             f"Receber {pending['dead_unit_max_life']} {label}")
        return
    rogue_pending = any(o.get("source") == "rogue_devil" for o in player.demon_pact_offers)
    for index, offer in enumerate(player.demon_pact_offers):
        rogue = offer.get("source") == "rogue_devil"
        if rogue_pending and not rogue:
            continue
        items = [i for i in peoples.ROGUE_ITEMS if i not in player.rogue_items] if rogue else [None]
        for pact in peoples.available_demon_pacts(state):
            for item in items or [None]:
                yield _offer("demon_pact", pid, {"offer_index": index, "pact_id": pact,
                                               "item": item},
                             peoples.DEMON_PACTS[pact] + (f" · item: {item}" if item else ""))
        if not rogue:
            yield _offer("decline_pact", pid, {"offer_index": index}, "Recusar oferta de pacto")
    if rogue_pending:
        return
    spell = spell_choices.effective_spell(player)
    if spell is not None:
        for choice, description in spell_choices.choices(state, player):
            yield _offer("cast_spell", pid, {"choice": choice},
                         spell.name + (f" → {description}" if description else ""))
    if player.people == peoples.PEOPLE_GNOMOS:
        yield _offer("reroll_spell", pid, {}, "São Tomé: sortear outra opção de feitiço")
    tuza = peoples.can_take_tuza_pact(state, pid)
    if tuza is not None:
        for pact in peoples.available_demon_pacts(state):
            yield _offer("demon_pact", pid, {"demon_player_id": tuza, "pact_id": pact},
                         f"Tuza: {peoples.DEMON_PACTS[pact]}")
    for card in dict.fromkeys(player.hand):
        if card == "PENA":
            for give, label in ((False, "Usar Pena"), (True, "Entregar Pena a Iúna")):
                yield _offer("use_pena", pid, {"give_to_iuna": give}, label)
        else:
            for choice, label in artifact_choices(state, player, card):
                yield _offer("play_artifact", pid, {"card_id": card, "choice": choice},
                             card_display(card) + (f" → {label}" if label else ""))
    living = {u.hero_id for u in player.units if isinstance(u, Hero) and u.is_alive()}
    aliases = {"barba_negra": ("barba_flames", "barba_combat"),
               "bimbo_do_mal": ("bimbo_hide", "bimbo_artifact")}
    for hero in sorted(living):
        for ability in aliases.get(hero, (hero,)):
            if ability in ABILITIES and ability not in ("guarari", "valtherion"):
                yield _offer("hero_ability", pid, {"ability": ability, "args": {}}, ABILITIES[ability][1])
    if player.people == "filhos_floresta" and player.chosen_hero_id == "baoba_ba":
        yield _offer("hero_ability", pid, {"ability": "baoba", "args": {}}, ABILITIES["baoba"][1])
    for unit in player.units:
        if not unit.is_alive():
            continue
        if player.pending_heals:
            yield _offer("use_heal", pid, {"unit_id": unit.id}, f"Curar {unit.id} ({unit.life}/{unit.life_max})")
        if "guarari" in living:
            yield _offer("hero_ability", pid, {"ability": "guarari", "args": {"unit_id": unit.id}},
                         f"Guarari: transformar {unit.id}")
    if "valtherion" in living:
        for kind in (TroopArchetype.DRAGON_LIGHT, TroopArchetype.DRAGON_MEDIUM, TroopArchetype.DRAGON_HEAVY):
            yield _offer("hero_ability", pid, {"ability": "valtherion", "args": {"archetype": kind.value}},
                         f"Chamado: {kind.value}")


def execute(state, action):
    pid, kind, params = action["player_id"], action["type"], action["params"]
    player = get_player(state, pid)
    if kind == "play_artifact":
        core.play_artifact(state, pid, **params)
    elif kind == "cast_spell":
        core.cast_spell(state, pid, params["choice"])
    elif kind == "reroll_spell":
        peoples.reroll_spell_copia(state, pid)
    elif kind == "resolve_artifact_choice":
        core.resolve_pending_artifact_choice(state, pid, **params)
    elif kind == "use_pena":
        core.use_or_give_pena(state, pid, "PENA", **params)
    elif kind == "use_heal":
        core.use_heal(state, pid, params["unit_id"])
    elif kind == "hero_ability":
        args = dict(params["args"])
        if "archetype" in args:
            args["archetype"] = TroopArchetype(args["archetype"])
        ABILITIES[params["ability"]][0](state, pid, **args)
    elif kind == "decline_pact":
        player.demon_pact_offers.pop(params["offer_index"])
    elif kind == "demon_pact":
        if "offer_index" in params:
            offer = player.demon_pact_offers[params["offer_index"]]
            peoples.make_demon_pact(state, offer["demon_player_id"], pid, params["pact_id"],
                                   params["item"], rogue_pact=offer.get("source") == "rogue_devil")
            player.demon_pact_offers.pop(params["offer_index"])
        else:
            peoples.make_demon_pact(state, params["demon_player_id"], pid, params["pact_id"])


def legal_interactions(state, player_id):
    try:
        player = get_player(state, player_id)
    except ValueError:
        return []
    if (state.game_over or state.phase != Phase.DAY or not player.city.is_alive()
            or state.active_player_id not in (None, player_id)):
        return []
    result = []
    for candidate in _candidates(state, player):
        try:
            execute(deepcopy(state), candidate)
        except (core.ActionError, ValueError):
            continue
        result.append(candidate)
    return result


def apply_interaction(state, action):
    from .headless import EVENT_VERSION, _error, view_for_player
    if type(action.get("player_id")) is not int or not isinstance(action.get("params"), dict):
        return _error("invalid_action", "Jogador ou parâmetros inválidos.")
    try:
        params = json.dumps(action["params"], sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return _error("invalid_action", "Parâmetros inválidos.")
    legal = next((a for a in legal_interactions(state, action["player_id"])
                  if a["type"] == action["type"]
                  and json.dumps(a["params"], sort_keys=True) == params), None)
    if legal is None:
        return _error("not_legal", "Escolha indisponível no estado atual.")
    trial = deepcopy(state)
    try:
        execute(trial, legal)
    except (core.ActionError, ValueError) as exc:
        return _error("domain_error", str(exc))
    pid = action["player_id"]
    private = action["type"] in ("resolve_artifact_choice", "decline_pact", "use_pena", "reroll_spell")
    event = {"version": EVENT_VERSION, "type": "interaction_resolved", "turn": trial.turn,
             "phase": trial.phase.value, "participants": [pid],
             "data": {"player_id": pid, "action_type": action["type"]},
             "visibility": {"kind": "private" if private else "public",
                            "player_ids": [pid] if private else []}}
    for key in ("card_id", "ability", "pact_id"):
        if key in legal["params"]:
            event["data"][key] = legal["params"][key]
    if action["type"] in ("cast_spell", "reroll_spell"):
        spell = spell_choices.effective_spell(get_player(trial, pid))
        event["data"]["spell_id"] = spell.spell_id if spell else None
    projection = {"version": EVENT_VERSION, "type": "player_view_updated", "turn": trial.turn,
                  "phase": trial.phase.value, "participants": [pid],
                  "data": {"view": view_for_player(trial, pid)},
                  "visibility": {"kind": "private", "player_ids": [pid]}}
    state.__dict__.update(trial.__dict__)
    return {"success": True, "error": None, "events": [event, projection]}
