from __future__ import annotations
import json
from .models import City, Player, Unit, Hero, Troop, GameState, ArtifactOnField
from .artifacts import Shop
from .rng import DeterministicRNG
from .constants import Phase, TroopArchetype


def city_to_dict(c: City) -> dict:
    return {"owner_id": c.owner_id, "life": c.life, "life_max": c.life_max,
            "gold": c.gold, "magic": c.magic, "has_monument": c.has_monument}


def city_from_dict(d: dict) -> City:
    return City(owner_id=d["owner_id"], life=d["life"], life_max=d["life_max"],
                gold=d["gold"], magic=d["magic"], has_monument=d["has_monument"])


def unit_to_dict(u: Unit) -> dict:
    kind = "hero" if isinstance(u, Hero) else "troop"
    d = {"kind": kind, "id": u.id, "owner_id": u.owner_id, "house": u.house,
         "life": u.life, "life_max": u.life_max,
         "has_moved_this_turn": u.has_moved_this_turn,
         "double_damage": u.double_damage,
         "resistance_stacks": u.resistance_stacks,
         "attacks_made_this_night": u.attacks_made_this_night,
         "max_attacks_this_night": u.max_attacks_this_night,
         "attacks_made_this_day": u.attacks_made_this_day,
         "max_attacks_this_day": u.max_attacks_this_day,
         "hero_can_attack_city": u.hero_can_attack_city,
         "killed_by_player_id": u.killed_by_player_id,
         "killed_by_unit_id": u.killed_by_unit_id,
         "original_owner_id": u.original_owner_id,
         "statuses": dict(u.statuses),
         "moves_this_turn": u.moves_this_turn,
         "max_moves_this_turn": u.max_moves_this_turn,
         "infectado": u.infectado,
         "bloqueado_mover_proximo": u.bloqueado_mover_proximo}
    if kind == "hero":
        d["hero_id"] = u.hero_id
    else:
        d["archetype"] = u.archetype.value
    return d


def unit_from_dict(d: dict) -> Unit:
    common = dict(id=d["id"], owner_id=d["owner_id"], house=d["house"],
                  life=d["life"], life_max=d["life_max"],
                  has_moved_this_turn=d["has_moved_this_turn"],
                  double_damage=d.get("double_damage", False),
                  resistance_stacks=d.get("resistance_stacks", 0),
                  attacks_made_this_night=d.get("attacks_made_this_night", 0),
                  max_attacks_this_night=d.get("max_attacks_this_night", 1),
                  attacks_made_this_day=d.get("attacks_made_this_day", 0),
                  max_attacks_this_day=d.get("max_attacks_this_day", 0),
                  hero_can_attack_city=d.get("hero_can_attack_city", False),
                  killed_by_player_id=d.get("killed_by_player_id", None),
                  killed_by_unit_id=d.get("killed_by_unit_id", None),
                  original_owner_id=d.get("original_owner_id", None),
                  statuses=dict(d.get("statuses", {})),
                  moves_this_turn=d.get("moves_this_turn", 0),
                  max_moves_this_turn=d.get("max_moves_this_turn", 1),
                  infectado=d.get("infectado", False),
                  bloqueado_mover_proximo=d.get("bloqueado_mover_proximo", False))
    if d["kind"] == "hero":
        return Hero(**common, hero_id=d["hero_id"])
    return Troop(**common, archetype=TroopArchetype(d["archetype"]))


def artifact_on_field_to_dict(a: ArtifactOnField) -> dict:
    return {"card_id": a.card_id, "owner_id": a.owner_id, "extra": dict(a.extra)}


def artifact_on_field_from_dict(d: dict) -> ArtifactOnField:
    return ArtifactOnField(card_id=d["card_id"], owner_id=d["owner_id"],
                           extra=dict(d.get("extra", {})))


def player_to_dict(p: Player) -> dict:
    return {
        "id": p.id, "name": p.name, "people": p.people,
        "chosen_hero_id": p.chosen_hero_id,
        "spell_cooldown_until_turn": p.spell_cooldown_until_turn,
        "has_collected_this_turn": p.has_collected_this_turn,
        "has_cast_spell_this_turn": p.has_cast_spell_this_turn,
        "morning_done_this_turn": p.morning_done_this_turn,
        "has_played_day_this_turn": p.has_played_day_this_turn,
        "artifacts_bought_gold_today": p.artifacts_bought_gold_today,
        "artifacts_bought_magic_today": p.artifacts_bought_magic_today,
        "pending_heals": p.pending_heals,
        "arken_espolia_used_turn": p.arken_espolia_used_turn,
        "vovo_position": p.vovo_position,
        "sonho_lucido_used_turn": p.sonho_lucido_used_turn,
        "sonho_lucido_pending_turn": p.sonho_lucido_pending_turn,
        "sonho_lucido_multi_turn": p.sonho_lucido_multi_turn,
        "vender_por_magia_turn": p.vender_por_magia_turn,
        "andar_duas_vezes_turn": p.andar_duas_vezes_turn,
        "bater_primeiro_turn": p.bater_primeiro_turn,
        "pena_added_once": p.pena_added_once,
        "besouro_mandinga_used_turn": p.besouro_mandinga_used_turn,
        "carocos_gerados": p.carocos_gerados,
        "empalados": list(p.empalados),
        "dwarf_empalados": [dict(e) for e in p.dwarf_empalados],
        "infectados": [dict(e) for e in p.infectados],
        "filhos_bonus_recebido": p.filhos_bonus_recebido,
        "baoba_pagamentos": p.baoba_pagamentos,
        "baoba_invocado": p.baoba_invocado,
        "bet_H_target": p.bet_H_target,
        "bet_C_target": p.bet_C_target,
        "bet_D_target": p.bet_D_target,
        "bet_S_target": p.bet_S_target,
        "correct_bets": p.correct_bets,
        "zebum_herois": list(p.zebum_herois),
        "spell_copia_id": p.spell_copia_id,
        "spell_copia_turn": p.spell_copia_turn,
        "bets_need_realocacao": p.bets_need_realocacao,
        "zebum_seven_dwarves": p.zebum_seven_dwarves,
        "garoche_life_max_bonus": p.garoche_life_max_bonus,
        "miyamoto_life_max_bonus": p.miyamoto_life_max_bonus,
        "canastra": list(p.canastra),
        "canastra_moves_turn": p.canastra_moves_turn,
        "canastra_moved_cards": list(p.canastra_moved_cards),
        "canastra_resonance_uses": p.canastra_resonance_uses,
        "demon_pact_offers": [dict(e) for e in p.demon_pact_offers],
        "devaneio_ativo_turn": p.devaneio_ativo_turn,
        "stats": dict(p.stats),
        "hand": list(p.hand),
        "field_artifacts": [artifact_on_field_to_dict(a) for a in p.field_artifacts],
        "units": [unit_to_dict(u) for u in p.units],
        "city": city_to_dict(p.city),
        "double_damage_until_end_night": p.double_damage_until_end_night,
        "invulnerable_until_end_turn": p.invulnerable_until_end_turn,
        "no_city_attacks_until_end_turn": p.no_city_attacks_until_end_turn,
        "armor_gold_cap_per_hit": p.armor_gold_cap_per_hit,
        "armor_active_until_turn": p.armor_active_until_turn,
        "pending_artifact_choice": p.pending_artifact_choice,
        "skip_day_turn": p.skip_day_turn,
        "skip_night_turn": p.skip_night_turn,
    }


def player_from_dict(d: dict) -> Player:
    return Player(
        id=d["id"], name=d["name"], people=d["people"],
        chosen_hero_id=d["chosen_hero_id"],
        spell_cooldown_until_turn=d.get("spell_cooldown_until_turn", 0),
        has_collected_this_turn=d["has_collected_this_turn"],
        has_cast_spell_this_turn=d["has_cast_spell_this_turn"],
        morning_done_this_turn=d.get("morning_done_this_turn", False),
        has_played_day_this_turn=d.get("has_played_day_this_turn", False),
        artifacts_bought_gold_today=d["artifacts_bought_gold_today"],
        artifacts_bought_magic_today=d["artifacts_bought_magic_today"],
        pending_heals=d.get("pending_heals", 0),
        arken_espolia_used_turn=d.get("arken_espolia_used_turn", -1),
        vovo_position=d.get("vovo_position", 1),
        sonho_lucido_used_turn=d.get("sonho_lucido_used_turn", -1),
        sonho_lucido_pending_turn=d.get("sonho_lucido_pending_turn", -1),
        sonho_lucido_multi_turn=d.get("sonho_lucido_multi_turn", -1),
        vender_por_magia_turn=d.get("vender_por_magia_turn", -1),
        andar_duas_vezes_turn=d.get("andar_duas_vezes_turn", -1),
        bater_primeiro_turn=d.get("bater_primeiro_turn", -1),
        pena_added_once=d.get("pena_added_once", False),
        besouro_mandinga_used_turn=d.get("besouro_mandinga_used_turn", -1),
        carocos_gerados=d.get("carocos_gerados", 0),
        empalados=list(d.get("empalados", [])),
        dwarf_empalados=[dict(e) for e in d.get("dwarf_empalados", [])],
        infectados=[dict(e) for e in d.get("infectados", [])],
        filhos_bonus_recebido=d.get("filhos_bonus_recebido", False),
        baoba_pagamentos=d.get("baoba_pagamentos", 0),
        baoba_invocado=d.get("baoba_invocado", False),
        bet_H_target=d.get("bet_H_target", None),
        bet_C_target=d.get("bet_C_target", None),
        bet_D_target=d.get("bet_D_target", None),
        bet_S_target=d.get("bet_S_target", None),
        correct_bets=d.get("correct_bets", 0),
        zebum_herois=list(d.get("zebum_herois", [])),
        spell_copia_id=d.get("spell_copia_id", None),
        spell_copia_turn=d.get("spell_copia_turn", -1),
        bets_need_realocacao=d.get("bets_need_realocacao", False),
        zebum_seven_dwarves=d.get("zebum_seven_dwarves", False),
        garoche_life_max_bonus=d.get("garoche_life_max_bonus", 0),
        miyamoto_life_max_bonus=d.get("miyamoto_life_max_bonus", 0),
        canastra=list(d.get("canastra", [])),
        canastra_moves_turn=d.get("canastra_moves_turn", -1),
        canastra_moved_cards=list(d.get("canastra_moved_cards", [])),
        canastra_resonance_uses=d.get("canastra_resonance_uses", 0),
        demon_pact_offers=[dict(e) for e in d.get("demon_pact_offers", [])],
        devaneio_ativo_turn=d.get("devaneio_ativo_turn", -1),
        stats=dict(d.get("stats", {})),
        hand=list(d["hand"]),
        field_artifacts=[artifact_on_field_from_dict(a) for a in d.get("field_artifacts", [])],
        units=[unit_from_dict(u) for u in d["units"]],
        city=city_from_dict(d["city"]),
        double_damage_until_end_night=d.get("double_damage_until_end_night", False),
        invulnerable_until_end_turn=d.get("invulnerable_until_end_turn", False),
        no_city_attacks_until_end_turn=d.get("no_city_attacks_until_end_turn", False),
        armor_gold_cap_per_hit=d.get("armor_gold_cap_per_hit", 0),
        armor_active_until_turn=d.get("armor_active_until_turn", -1),
        pending_artifact_choice=d.get("pending_artifact_choice", None),
        skip_day_turn=d.get("skip_day_turn", None),
        skip_night_turn=d.get("skip_night_turn", None),
    )


def state_to_dict(s: GameState) -> dict:
    return {
        "seed": s.seed, "rng": s.rng.to_dict(),
        "players": [player_to_dict(p) for p in s.players],
        "turn_order": list(s.turn_order),
        "shop": {"deck": list(s.shop.deck)},
        "turn": s.turn, "phase": s.phase.value,
        "curuna_id": s.curuna_id,
        "event_log": list(s.event_log),
        "action_log": list(s.action_log),
        "game_over": s.game_over, "winner_id": s.winner_id,
        "pending_effects": [dict(e) for e in s.pending_effects],
        "deaths_this_night": list(s.deaths_this_night),
        "dain_kills": [dict(e) for e in s.dain_kills],
        "espectros_pendentes": [dict(e) for e in s.espectros_pendentes],
        "lobisomens_transformados": [dict(e) for e in s.lobisomens_transformados],
        "fae_fallen_this_turn": [list(t) for t in s.fae_fallen_this_turn],
        "timeline": [dict(e) for e in s.timeline],
        "morning_gains": [dict(e) for e in s.morning_gains],
        "night_start_positions": dict(s.night_start_positions),
        "night_priority_by_house": {
            house: list(queue)
            for house, queue in s.night_priority_by_house.items()
        },
        "demon_pacts": [dict(e) for e in s.demon_pacts],
    }


def state_from_dict(d: dict) -> GameState:
    state = GameState(seed=d["seed"], rng=DeterministicRNG.from_dict(d["rng"]))
    state.players = [player_from_dict(p) for p in d["players"]]
    state.turn_order = list(d["turn_order"])
    state.shop = Shop(deck=list(d["shop"]["deck"]))
    state.turn = d["turn"]
    state.phase = Phase(d["phase"])
    state.curuna_id = d["curuna_id"]
    state.event_log = list(d["event_log"])
    state.action_log = list(d["action_log"])
    state.game_over = d["game_over"]
    state.winner_id = d["winner_id"]
    state.pending_effects = [dict(e) for e in d.get("pending_effects", [])]
    state.deaths_this_night = list(d.get("deaths_this_night", []))
    state.dain_kills = [dict(e) for e in d.get("dain_kills", [])]
    state.espectros_pendentes = [dict(e) for e in d.get("espectros_pendentes", [])]
    state.lobisomens_transformados = [dict(e) for e in d.get("lobisomens_transformados", [])]
    state.fae_fallen_this_turn = [tuple(t) for t in d.get("fae_fallen_this_turn", [])]
    state.timeline = [dict(e) for e in d.get("timeline", [])]
    state.morning_gains = [dict(e) for e in d.get("morning_gains", [])]
    state.night_start_positions = dict(d.get("night_start_positions", {}))
    state.night_priority_by_house = {
        house: list(queue)
        for house, queue in d.get("night_priority_by_house", {}).items()
    }
    state.demon_pacts = [dict(e) for e in d.get("demon_pacts", [])]
    # Compatibilidade com saves produzidos pelos patches v5v9 antigos.
    for pid_s, value in d.get("miyamoto_bonus", {}).items():
        player = next((p for p in state.players if str(p.id) == str(pid_s)), None)
        if player is not None:
            player.miyamoto_life_max_bonus = int(value)
    return state


def save_to_file(state: GameState, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state_to_dict(state), f, ensure_ascii=False, indent=2)


def load_from_file(path: str) -> GameState:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return state_from_dict(data)
