"""Passivas dos povos."""
from __future__ import annotations
from .state import get_player, log, bump_stat, sync_house_priority
from .models import GameState, Player, Unit, Hero, Troop
from .constants import (
    TroopArchetype, CENTER, CITY_HOUSES,
    BET_HEART, BET_CLUB, BET_DIAMOND, BET_SPADE, ALL_BETS, FILHOS_BONUS_TURN,
)
from . import heroes


PEOPLE_HUMANS = "humanos"
PEOPLE_DWARVES = "anoes"
PEOPLE_ORCS = "orcs"
PEOPLE_FAE = "fadas"
PEOPLE_VAMPIRES = "vampiros"
PEOPLE_LOBISOMENS = "lobisomens"
PEOPLE_GIGANTES = "gigantes"
PEOPLE_MORTOS_VIVOS = "mortos_vivos"
PEOPLE_FILHOS = "filhos_floresta"
PEOPLE_GNOMOS = "gnomos_duendes"
PEOPLE_DRAGOES = "dragoes"
PEOPLE_DEMONIOS = "demonios"

def has_luide_bonus(player: Player) -> bool:
    return player.people == PEOPLE_VAMPIRES and any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa"
        for u in player.units)

DEMON_PACTS = {
    "sacrifique_futuro": "Sacrifique seu Futuro",
    "sacrifique_militar": "Sacrifique sua capacidade Militar",
    "sacrifique_mente": "Sacrifique a Mente de suas Tropas",
    "cabecas_herois": "Ofereca cabecas de herois de cada povo",
    "banho_sangue": "Ofereca um banho de sangue",
    "vida_lider": "Ofereca a vida de um lider",
}
DEMON_SACRIFICE_PACTS = {"sacrifique_futuro", "sacrifique_militar", "sacrifique_mente"}
ROGUE_ITEMS = ("capa", "adaga", "relogio", "bracelete")


ACTION_TO_BET = {
    "play_artifact": BET_CLUB,
    "base_life_gained": BET_HEART,
    "artifact_obtained": BET_DIAMOND,
    "unit_summoned": BET_SPADE,
}


def unit_signature(u: Unit) -> dict:
    if isinstance(u, Hero):
        return {"kind": "hero", "id": u.hero_id}
    return {"kind": "troop", "id": u.archetype.value}


def infection_record(u: Unit) -> dict:
    record = unit_signature(u)
    record["unit_id"] = u.id
    record["owner_id"] = u.original_owner_id or u.owner_id
    return record


def infection_matches(record: dict, unit: Unit) -> bool:
    owner_id = unit.original_owner_id or unit.owner_id
    recorded_owner = record.get("owner_id")
    if recorded_owner is not None and recorded_owner != owner_id:
        return False
    if record.get("unit_id") == unit.id:
        return True
    sig = unit_signature(unit)
    return record.get("kind") == sig["kind"] and record.get("id") == sig["id"]


def add_infection(infector: Player, unit: Unit) -> bool:
    if isinstance(unit, Hero) and unit.hero_id == "valtherion":
        return False
    record = infection_record(unit)
    for existing in infector.infectados:
        if (existing.get("kind") == record["kind"]
                and existing.get("id") == record["id"]
                and existing.get("owner_id") == record["owner_id"]
                and existing.get("unit_id") == record["unit_id"]):
            return False
    infector.infectados.append(record)
    return True


def is_unit_infected(state: GameState, unit: Unit) -> bool:
    return any(
        infection_matches(record, unit)
        for player in state.players
        for record in player.infectados
    )


def dragon_rank_count(player: Player, rank: str) -> int:
    return sum(1 for card_id in player.canastra if card_id.startswith(f"{rank}_"))


def dragon_has_suit(player: Player, suit: str) -> bool:
    return any(card_id.endswith(f"_{suit}") for card_id in player.canastra)


def dragon_heroes(player: Player, state: GameState | None = None) -> list[Hero]:
    return [u for u in player.units
            if isinstance(u, Hero) and u.is_alive()
            and (heroes.get_hero(u.hero_id).people == PEOPLE_DRAGOES
                 or (state is not None and player.people == PEOPLE_GNOMOS
                     and PEOPLE_DRAGOES in sao_tome_effective_peoples(state, player)))]


def dragon_base(player: Player) -> Hero | None:
    return next((u for u in dragon_heroes(player)
                 if u.statuses.get("dragon_base")), None)


def sync_dragon_base_city(player: Player) -> None:
    base = dragon_base(player)
    if base is None:
        if player.people == PEOPLE_DRAGOES and player.chosen_hero_id in (
                "barba_negra", "valtherion"):
            player.city.life = 0
        return
    player.city.life = base.life
    player.city.life_max = base.life_max


def apply_dragon_canastra_to_hero(state: GameState, player: Player, unit: Hero) -> None:
    """Aplica os efeitos persistentes da Canastra a um Dragao recem-invocado."""
    inherits = (player.people == PEOPLE_GNOMOS
                and PEOPLE_DRAGOES in sao_tome_effective_peoples(state, player))
    if player.people != PEOPLE_DRAGOES and not inherits:
        return
    if dragon_has_suit(player, "H") and not unit.statuses.get("dragon_heart_resistance"):
        unit.resistance_stacks += 1
        unit.statuses["dragon_heart_resistance"] = True
    if dragon_has_suit(player, "C"):
        unit.max_moves_this_turn = max(2, unit.max_moves_this_turn)
        # Invocado normalmente ja gastou 1 movimento; Paus libera o segundo.
        unit.has_moved_this_turn = unit.moves_this_turn >= unit.max_moves_this_turn


def hero_life_with_persistent_bonus(player: Player, hero_def,
                                    state: GameState | None = None) -> int:
    life = hero_def.life
    if hero_def.hero_id == "miyamoto":
        life += player.miyamoto_life_max_bonus
    if hero_def.hero_id == "garoche":
        life += player.garoche_life_max_bonus
    if hero_def.hero_id == "purpura" and state is not None:
        life += state.turn // 2
    if hero_def.hero_id == "rogue_devil":
        life += player.rogue_life_bonus + int("bracelete" in player.rogue_items)
    if hero_def.people == PEOPLE_DRAGOES:
        life += 2 * dragon_rank_count(player, "Q")
    return life


def is_empalado(player: Player, sig: dict) -> bool:
    return sig in player.empalados or any(e.get("sig") == sig for e in player.dwarf_empalados)


def clear_dwarf_impales_for_curuna(state: GameState) -> None:
    for victim in state.players:
        victim.dwarf_empalados = [
            e for e in victim.dwarf_empalados
            if e.get("dwarf_owner_id") != state.curuna_id
        ]


def apply_dragon_turn_start(state: GameState) -> None:
    for player in state.players:
        inherits = (player.people == PEOPLE_GNOMOS
                    and PEOPLE_DRAGOES in sao_tome_effective_peoples(state, player))
        if ((player.people != PEOPLE_DRAGOES and not inherits)
                or not player.city.is_alive()):
            continue
        kings = dragon_rank_count(player, "K")
        if kings:
            player.city.magic += kings
            state.morning_gains.append(
                {"pid": player.id, "kind": "Sangue Encantado", "magic": kings}
            )
            log(state, f"{player.name} (Dragoes): +{kings} Magia pela Canastra.")
        for unit in dragon_heroes(player, state):
            unit.max_moves_this_turn = 2 if dragon_has_suit(player, "C") else 1
            unit.has_moved_this_turn = unit.moves_this_turn >= unit.max_moves_this_turn
            if state.turn == 1 and unit.statuses.get("summoned_turn") == 1:
                unit.moves_this_turn = unit.max_moves_this_turn
                unit.has_moved_this_turn = True
            if unit.hero_id == "purpura" and state.turn % 2 == 0:
                unit.life_max += 1
                unit.life += 1
                log(state, f"{player.name}: Purpura cresceu para {unit.life}/{unit.life_max}.")
        sync_dragon_base_city(player)


def on_action_performed(state: GameState, actor_id: int, action: str) -> None:
    suit = ACTION_TO_BET.get(action)
    if suit is None:
        return
    for gnomo in state.players:
        if gnomo.people != PEOPLE_GNOMOS:
            continue
        if not gnomo.city.is_alive():
            continue
        target = getattr(gnomo, f"bet_{suit}_target", None)
        if target is None:
            continue
        if target != actor_id:
            continue
        previous = sao_tome_effective_peoples(state, gnomo)
        gnomo.correct_bets += 1
        setattr(gnomo, f"bet_{suit}_target", None)
        _sao_tome_passives_lost(state, gnomo,
                                previous - sao_tome_effective_peoples(state, gnomo))
        actor = get_player(state, actor_id)
        log(state, f"{gnomo.name}: Aposta {suit} cumprida por {actor.name}. "
                   f"(Total: {gnomo.correct_bets} corretas)")


def on_unit_summoned(state: GameState, actor_id: int, unit: Unit | None = None) -> None:
    on_action_performed(state, actor_id, "unit_summoned")
    if isinstance(unit, Hero) and unit.hero_id == "rogue_devil":
        owner = get_player(state, actor_id)
        unit.statuses["rogue_items"] = list(owner.rogue_items)
        if "adaga" in owner.rogue_items:
            unit.statuses["demon_execute_weaker"] = True
        if "bracelete" in owner.rogue_items:
            unit.statuses["rogue_resist_heroes"] = True
        owner.demon_pact_offers.append({
            "source": "rogue_devil", "demon_player_id": actor_id,
            "unit_id": unit.id, "turn": state.turn,
        })
    if isinstance(unit, Hero) and unit.hero_id == "tuza":
        unit.resistance_stacks += 1
        unit.statuses["tuza_resistance"] = True


def demon_mind_pact_active(state: GameState, player_id: int) -> bool:
    return active_demon_pact(state, player_id, "sacrifique_mente") is not None


def demon_military_pact_active(state: GameState, player_id: int) -> bool:
    return active_demon_pact(state, player_id, "sacrifique_militar") is not None


def on_artifact_obtained(state: GameState, actor_id: int) -> None:
    on_action_performed(state, actor_id, "artifact_obtained")


def on_base_life_gained(state: GameState, actor_id: int, amount: int) -> None:
    if amount > 0:
        on_action_performed(state, actor_id, "base_life_gained")
    enforce_demon_pact_penalties(state)


def enforce_demon_pact_penalties(state: GameState) -> None:
    for pact in state.demon_pacts:
        if pact["pact_id"] != "sacrifique_futuro" or pact.get("released"):
            continue
        owner = get_player(state, pact["owner_id"])
        base = dragon_base(owner)
        if base is not None:
            base.life_max = 4
            base.life = min(base.life, 4)
            sync_dragon_base_city(owner)
        else:
            owner.city.life_max = 4
            owner.city.life = min(owner.city.life, 4)


def active_demon_pact(state: GameState, player_id: int, pact_id: str) -> dict | None:
    return next((p for p in state.demon_pacts
                 if p["owner_id"] == player_id and p["pact_id"] == pact_id
                 and not p.get("released", False)), None)


def available_demon_pacts(state: GameState) -> list[str]:
    used = {p["pact_id"] for p in state.demon_pacts}
    return [pact_id for pact_id in DEMON_PACTS if pact_id not in used]


def _demon_pact_reward(state: GameState, pact: dict) -> None:
    if pact.get("rewarded"):
        return
    owner = get_player(state, pact["owner_id"])
    if pact.get("rogue_pact") and not pact.get("rogue_life_awarded"):
        owner.rogue_life_bonus += 1
        rogue = next((u for u in owner.units if isinstance(u, Hero)
                      and u.hero_id == "rogue_devil"), None)
        if rogue is not None:
            rogue.life_max += 1
            rogue.life += 1
        pact["rogue_life_awarded"] = True
    item = pact.get("rogue_item")
    if item:
        if item not in owner.rogue_items:
            owner.rogue_items.append(item)
        rogue = next((u for u in owner.units if isinstance(u, Hero)
                      and u.hero_id == "rogue_devil"), None)
        if rogue is not None:
            items = list(rogue.statuses.get("rogue_items", []))
            if item not in items:
                items.append(item)
                rogue.statuses["rogue_items"] = items
                if item == "adaga":
                    rogue.statuses["demon_execute_weaker"] = True
                elif item == "bracelete":
                    rogue.life_max += 1
                    rogue.life += 1
                    rogue.statuses["rogue_resist_heroes"] = True
                log(state, f"{owner.name}: Rogue Devil recebeu {item}.")
    if state.shop.is_empty():
        pact["reward_pending"] = True
        return
    card = state.shop.draw_random(state.rng)
    owner.hand.append(card)
    pact["rewarded"] = True
    pact["reward_pending"] = False
    on_artifact_obtained(state, owner.id)
    log(state, f"{owner.name}: pacto {DEMON_PACTS[pact['pact_id']]} concedeu {card}.")


def make_demon_pact(state: GameState, demon_player_id: int, owner_id: int,
                     pact_id: str, rogue_buff: str | None = None,
                     rogue_pact: bool = False) -> dict:
    demon = get_player(state, demon_player_id)
    owner = get_player(state, owner_id)
    inherits = (demon.people == PEOPLE_GNOMOS
                and PEOPLE_DEMONIOS in sao_tome_effective_peoples(state, demon))
    if (demon.people != PEOPLE_DEMONIOS and not inherits) or not demon.city.is_alive():
        raise ValueError("Jogador de Demonios indisponivel.")
    if pact_id not in available_demon_pacts(state):
        raise ValueError("Pacto indisponivel.")
    pact = {"pact_id": pact_id, "demon_player_id": demon_player_id,
            "owner_id": owner_id, "turn": state.turn, "completed": False,
            "rewarded": False, "released": False}
    if pact_id == "sacrifique_futuro":
        base = dragon_base(owner)
        pact["old_life_max"] = base.life_max if base is not None else owner.city.life_max
        if base is not None:
            base.life_max = 4
            base.life = 4
            sync_dragon_base_city(owner)
        else:
            owner.city.life_max = 4
            owner.city.life = 4
    elif pact_id == "cabecas_herois":
        pact["required_peoples"] = sorted({p.people for p in state.players
                                            if p.id != owner_id and p.city.is_alive()})
        pact["killed_peoples"] = []
    elif pact_id == "banho_sangue":
        pact["blood_turn"] = -1
        pact["blood_count"] = 0
    if rogue_buff is not None:
        aliases = {"invisibilidade": "capa", "execucao": "adaga"}
        rogue_item = aliases.get(rogue_buff, rogue_buff)
        if owner_id != demon_player_id or rogue_item not in ROGUE_ITEMS:
            raise ValueError("Item de Rogue Devil invalido.")
        rogue = next((u for u in owner.units if isinstance(u, Hero)
                      and u.hero_id == "rogue_devil"), None)
        if rogue is None:
            raise ValueError("Rogue Devil nao esta em campo.")
        if rogue_item in rogue.statuses.get("rogue_items", []):
            raise ValueError("Rogue Devil ja possui este item.")
        pact["rogue_item"] = rogue_item
        rogue_pact = True
    if rogue_pact:
        if owner_id != demon_player_id:
            raise ValueError("Pacto de Rogue Devil deve pertencer ao invocador.")
        rogue = next((u for u in owner.units if isinstance(u, Hero)
                      and u.hero_id == "rogue_devil"), None)
        if rogue is None:
            raise ValueError("Rogue Devil nao esta em campo.")
        pact["rogue_pact"] = True
    state.demon_pacts.append(pact)
    if pact_id in DEMON_SACRIFICE_PACTS:
        pact["completed"] = True
    if pact["completed"] or rogue_pact:
        _demon_pact_reward(state, pact)
    log(state, f"{owner.name} firmou {DEMON_PACTS[pact_id]} com {demon.name}.")
    return pact


def release_demon_pacts(state: GameState, demon_player_id: int) -> None:
    for pact in state.demon_pacts:
        if pact["demon_player_id"] != demon_player_id or pact.get("released"):
            continue
        owner = get_player(state, pact["owner_id"])
        if pact["pact_id"] == "sacrifique_futuro":
            base = dragon_base(owner)
            if base is not None:
                base.life_max = max(base.life_max, pact.get("old_life_max", 4))
                sync_dragon_base_city(owner)
            else:
                owner.city.life_max = max(owner.city.life_max, pact.get("old_life_max", 4))
        pact["released"] = True


def can_take_tuza_pact(state: GameState, player_id: int) -> int | None:
    if state.phase.value != "day":
        return None
    if player_id == state.curuna_id:
        return None
    demon = get_player(state, state.curuna_id)
    inherits = (demon.people == PEOPLE_GNOMOS
                and PEOPLE_DEMONIOS in sao_tome_effective_peoples(state, demon))
    if (demon.people != PEOPLE_DEMONIOS and not inherits) or not demon.city.is_alive():
        return None
    if not any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "tuza"
               for u in demon.units):
        return None
    return demon.id


def resolve_pending_demon_rewards(state: GameState) -> None:
    for pact in state.demon_pacts:
        if pact.get("reward_pending"):
            _demon_pact_reward(state, pact)


def on_any_unit_death(state: GameState, dead_unit: Unit) -> None:
    if isinstance(dead_unit, Hero) and dead_unit.hero_id == "sao_tome":
        owner = get_player(state, dead_unit.owner_id)
        inherited = {
            other.people for other in state.players
            if other.id != owner.id and sao_tome_has_aposta_em(owner, other.id)
        }
        _sao_tome_passives_lost(state, owner, inherited)
    for demon in state.players:
        inherits = (demon.people == PEOPLE_GNOMOS
                    and PEOPLE_DEMONIOS in sao_tome_effective_peoples(state, demon))
        if (demon.people == PEOPLE_DEMONIOS or inherits) and demon.city.is_alive():
            demon.city.magic += 1
            log(state, f"{demon.name} (Banco de Almas): +1 Magia.")
    killer_id = dead_unit.killed_by_player_id
    if killer_id is None:
        return
    killer = get_player(state, killer_id)
    if isinstance(dead_unit, Hero):
        victim_people = get_player(state, dead_unit.owner_id).people
        for pact in state.demon_pacts:
            if (pact["owner_id"] == killer_id and pact["pact_id"] == "cabecas_herois"
                    and not pact.get("completed")):
                killed = set(pact.get("killed_peoples", []))
                killed.add(victim_people)
                pact["killed_peoples"] = sorted(killed)
                if set(pact["required_peoples"]).issubset(killed):
                    pact["completed"] = True
                    _demon_pact_reward(state, pact)
    if isinstance(dead_unit, (Troop, Hero)) and state.phase.value == "night":
        for pact in state.demon_pacts:
            if (pact["owner_id"] == killer_id and pact["pact_id"] == "banho_sangue"
                    and not pact.get("completed")):
                if pact.get("blood_turn") != state.turn:
                    pact["blood_turn"], pact["blood_count"] = state.turn, 0
                pact["blood_count"] += 1
                if pact["blood_count"] >= 3:
                    pact["completed"] = True
                    _demon_pact_reward(state, pact)


def on_city_destroyed_for_pacts(state: GameState, destroyer_id: int) -> None:
    for pact in state.demon_pacts:
        if (pact["owner_id"] == destroyer_id and pact["pact_id"] == "vida_lider"
                and not pact.get("completed")):
            pact["completed"] = True
            _demon_pact_reward(state, pact)


def apply_belial_night_start(state: GameState) -> None:
    any_death = False
    for demon in state.players:
        belial = next((u for u in demon.units if isinstance(u, Hero) and u.is_alive()
                       and u.hero_id == "belial"), None)
        inherits = (demon.people == PEOPLE_GNOMOS
                    and PEOPLE_DEMONIOS in sao_tome_effective_peoples(state, demon))
        if (demon.people != PEOPLE_DEMONIOS and not inherits) or belial is None:
            continue
        belial.life_max += 1
        belial.life += 1
        for player in state.players:
            for unit in player.units:
                if (not unit.is_alive() or unit.house != belial.house
                        or unit.statuses.get("dragon_base")):
                    continue
                if player.id == demon.id:
                    if unit is not belial:
                        unit.life = min(unit.life_max, unit.life + 1)
                else:
                    from .combat import apply_area_damage
                    apply_area_damage(state, belial, unit, 1)
                    if not unit.is_alive():
                        any_death = True
        log(state, f"{demon.name}: Belial espalhou as Chamas no inicio da Noite.")
    if any_death:
        from .combat import _cleanup_dead
        _cleanup_dead(state)


def sao_tome_has_aposta_em(player: Player, target_id: int) -> bool:
    return (
        player.bet_H_target == target_id
        or player.bet_C_target == target_id
        or player.bet_D_target == target_id
        or player.bet_S_target == target_id
    )


def sao_tome_effective_peoples(state: GameState, player: Player) -> set[str]:
    if player.people != PEOPLE_GNOMOS:
        return {player.people}
    has_sao_tome = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
        for u in player.units
    )
    if not has_sao_tome:
        return {PEOPLE_GNOMOS}
    result = {PEOPLE_GNOMOS}
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        if sao_tome_has_aposta_em(player, other.id):
            result.add(other.people)
    return result


def _sao_tome_passives_lost(state: GameState, player: Player,
                            lost: set[str]) -> None:
    if PEOPLE_DRAGOES in lost and player.canastra:
        queens = dragon_rank_count(player, "Q")
        if queens:
            for unit in [u for u in player.units
                         if isinstance(u, Hero) and u.is_alive()]:
                unit.life_max = max(1, unit.life_max - 2 * queens)
        player.hand.extend(player.canastra)
        player.canastra.clear()
        for unit in [u for u in player.units if isinstance(u, Hero) and u.is_alive()]:
            if unit.statuses.pop("dragon_heart_resistance", False):
                unit.resistance_stacks = max(0, unit.resistance_stacks - 1)
            unit.max_moves_this_turn = 1
            unit.has_moved_this_turn = unit.moves_this_turn >= 1
        log(state, f"{player.name}: perdeu Envolvimento Cosmologico; Canastra voltou a mao.")
    if PEOPLE_MORTOS_VIVOS in lost:
        removed = [u for u in player.units
                   if isinstance(u, Hero) and u.hero_id != "sao_tome"
                   and u.statuses.get("sao_tome_undead_summon")]
        if removed:
            player.units = [u for u in player.units if u not in removed]
            log(state, f"{player.name}: perdeu a passiva dos Mortos-Vivos; "
                       f"{len(removed)} heroi(s) invocado(s) por ela desapareceram.")


def sao_tome_target_eliminated(state: GameState, target_id: int) -> None:
    target_people = get_player(state, target_id).people
    for player in state.players:
        if (player.people == PEOPLE_GNOMOS
                and sao_tome_has_aposta_em(player, target_id)):
            _sao_tome_passives_lost(state, player, {target_people})


def sao_tome_dano_lobisomem(state: GameState, attacker) -> bool:
    if not (isinstance(attacker, Hero) and attacker.hero_id == "sao_tome"):
        return False
    owner = get_player(state, attacker.owner_id)
    if owner.people != PEOPLE_GNOMOS:
        return False
    effective = sao_tome_effective_peoples(state, owner)
    if PEOPLE_LOBISOMENS not in effective:
        return False
    for other in state.players:
        if other.id == owner.id:
            continue
        if not sao_tome_has_aposta_em(owner, other.id):
            continue
        if other.people != PEOPLE_LOBISOMENS:
            continue
        if is_lua_cheia(state, other.id):
            return True
    return False


def apply_filhos_bonus(state: GameState) -> None:
    if state.turn != FILHOS_BONUS_TURN:
        return
    for p in state.players:
        inherits = (p.people == PEOPLE_GNOMOS
                    and PEOPLE_FILHOS in sao_tome_effective_peoples(state, p))
        if p.people != PEOPLE_FILHOS and not inherits:
            continue
        if not p.city.is_alive():
            continue
        if p.filhos_bonus_recebido:
            continue
        ganho_vida = min(2, p.city.life_max - p.city.life)
        p.city.life += ganho_vida
        p.city.gold += 2
        p.city.magic += 2
        p.filhos_bonus_recebido = True
        log(state, f"{p.name} (Filhos): Florescimento Exuberante (+{ganho_vida} Vida, +2 Ouro, +2 Magia).")
        on_base_life_gained(state, p.id, ganho_vida)


def reset_gnomos_bets(state: GameState) -> None:
    for p in state.players:
        if p.people != PEOPLE_GNOMOS:
            continue
        if not p.city.is_alive():
            continue
        previous = sao_tome_effective_peoples(state, p)
        p.bet_H_target = None
        p.bet_C_target = None
        p.bet_D_target = None
        p.bet_S_target = None
        _sao_tome_passives_lost(state, p,
                                previous - sao_tome_effective_peoples(state, p))
        p.bets_need_realocacao = True
        log(state, f"{p.name} (Gnomos): apostas serao re-alocadas.")


def draw_spell_copia(state: GameState, player: Player) -> None:
    from . import spells as spells_mod
    peoples_participantes = set()
    for p in state.players:
        if p.people and p.people != PEOPLE_GNOMOS:
            peoples_participantes.add(p.people)
    if not peoples_participantes:
        player.spell_copia_id = None
        return
    candidatos = []
    for people in peoples_participantes:
        sp = spells_mod.spell_for_people(people)
        if sp is not None:
            candidatos.append(sp.spell_id)
    if not candidatos:
        player.spell_copia_id = None
        return
    player.spell_copia_id = state.rng.choice(candidatos)
    player.spell_copia_turn = state.turn
    log(state, f"{player.name} (Gnomos): feitico copiado sorteado: {player.spell_copia_id}.")


def reroll_spell_copia(state: GameState, player_id: int) -> str:
    player = get_player(state, player_id)
    if player.people != PEOPLE_GNOMOS:
        raise ValueError("Apenas Gnomos podem rerrolar a Imitacao.")
    if not any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
               for u in player.units):
        raise ValueError("Sao Tome precisa estar vivo.")
    if player.spell_copia_turn != state.turn or not player.spell_copia_id:
        raise ValueError("Nenhum feitico deste turno para rerrolar.")
    if player.spell_copia_rerolled_turn == state.turn:
        raise ValueError("Sao Tome ja rerrolou neste turno.")
    if player.has_cast_spell_this_turn:
        raise ValueError("O feitico ja foi usado neste turno.")
    from . import spells as spells_mod
    candidates = []
    for other in state.players:
        if other.people and other.people != PEOPLE_GNOMOS:
            spell = spells_mod.spell_for_people(other.people)
            if spell is not None and spell.spell_id not in candidates:
                candidates.append(spell.spell_id)
    alternatives = [spell_id for spell_id in candidates
                    if spell_id != player.spell_copia_id]
    pool = alternatives or candidates
    if not pool:
        raise ValueError("Nao ha outro feitico disponivel.")
    previous = player.spell_copia_id
    player.spell_copia_id = state.rng.choice(pool)
    player.spell_copia_rerolled_turn = state.turn
    log(state, f"{player.name}: Sao Tome rerrolou {previous} -> {player.spell_copia_id}.")
    return player.spell_copia_id


def on_player_morning(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    p = player.people
    if p == PEOPLE_DWARVES:
        _dwarves_mineiro_carreiro(state, player)
    elif p == PEOPLE_HUMANS:
        _humans_roca_de_quilombo(state, player)
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive() and u.hero_id == "barbadourada":
            n = len(player.hand)
            if n > 0:
                player.city.magic += n
                log(state, f"{player.name}: Barbadourada - +{n} Magia.")
    if p == PEOPLE_GNOMOS:
        _sao_tome_extra_passives(state, player)


def _sao_tome_extra_passives(state: GameState, player: Player) -> None:
    has_sao_tome = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
        for u in player.units
    )
    if not has_sao_tome:
        return
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        if not sao_tome_has_aposta_em(player, other.id):
            continue
        op = other.people
        if op == PEOPLE_DWARVES:
            _dwarves_mineiro_carreiro(state, player)
        elif op == PEOPLE_HUMANS:
            _humans_roca_de_quilombo(state, player)


def _dwarves_mineiro_carreiro(state: GameState, player: Player) -> None:
    count = sum(1 for u in player.units if u.is_alive())
    player.city.gold += count
    log(state, f"{player.name} (Anoes): Mineiro Carreiro - +{count} Ouro.")


def _humans_roca_de_quilombo(state: GameState, player: Player) -> None:
    from .state import record_action
    num_penas = sum(1 for a in player.field_artifacts if a.card_id == "PENA")
    num_dice = 1 + num_penas
    rolls = [state.rng.randint(1, 4) for _ in range(num_dice)]
    record_action(state, player.id, "roll", source="roca_humanos",
                  dice=num_dice, results=list(rolls))
    log(state, f"{player.name} (Humanos): Roca - {num_dice}D4 = {rolls}.")
    for r in rolls:
        _apply_roca_result(state, player, r)


def _apply_roca_result(state: GameState, player: Player, result: int) -> None:
    if result == 1:
        player.city.magic += 1
        log(state, "  +1 Magia.")
    elif result == 2:
        player.city.gold += 1
        log(state, "  +1 Ouro.")
    elif result == 3:
        player.pending_heals += 1
        log(state, f"  Cura 2 pendente ({player.pending_heals}).")
    elif result == 4:
        _roca_dano(state, player)


def _roca_dano(state: GameState, player: Player) -> None:
    home = f"city_{player.id}"
    enemies = []
    for other in state.players:
        if other.id == player.id:
            continue
        for u in other.units:
            if u.house == home and u.is_alive():
                enemies.append(u)
    if not enemies:
        log(state, "  Dano: sem inimigos na Cidade.")
        return
    for u in enemies:
        before = u.life
        u.life = max(0, u.life - 1)
        if not u.is_alive():
            u.statuses["life_at_death"] = before
            u.killed_by_player_id = player.id
        log(state, f"  1 dano em {u.id}: {u.life}/{u.life_max}.")
    from .combat import _cleanup_dead
    _cleanup_dead(state)


def on_unit_moved(state: GameState, player_id: int, unit: Unit) -> None:
    from .state import record_action
    player = get_player(state, player_id)
    if player.people == PEOPLE_FAE:
        player.city.magic += 1
        log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id} (Asas Encantadas).")
        record_action(state, player_id, "trigger",
                      source="asas_encantadas", magic=1, unit_id=unit.id)
        return
    if player.people == PEOPLE_GNOMOS:
        effective = sao_tome_effective_peoples(state, player)
        if PEOPLE_FAE in effective:
            player.city.magic += 1
            log(state, f"{player.name} (Sao Tome herda Fadas): +1 Magia ao mover {unit.id}.")
            record_action(state, player_id, "trigger",
                          source="asas_encantadas_sao_tome", magic=1, unit_id=unit.id)


def on_unit_killed_by(state: GameState, killer_player_id: int,
                      dead_unit: Unit, killer_unit: Unit | None = None) -> None:
    killer_player = get_player(state, killer_player_id)
    victim_owner = get_player(state, dead_unit.owner_id)

    if (isinstance(killer_unit, Hero) and killer_unit.hero_id == "rogue_devil"
            and "capa" in killer_unit.statuses.get("rogue_items", [])):
        killer_unit.statuses["invisivel_until_turn"] = state.turn
        log(state, f"  {killer_unit.id} ficou invisivel pela Capa.")

    if isinstance(killer_unit, Hero) and isinstance(dead_unit, Hero):
        for demon in state.players:
            inherits = (demon.people == PEOPLE_GNOMOS
                        and PEOPLE_DEMONIOS in sao_tome_effective_peoples(state, demon))
            if ((demon.people == PEOPLE_DEMONIOS or inherits) and demon.city.is_alive()
                    and any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "belial"
                            for u in demon.units)):
                killer_player.demon_pact_offers.append({
                    "source": "belial", "demon_player_id": demon.id,
                    "turn": state.turn,
                })

    if (isinstance(killer_unit, Hero)
            and killer_unit.hero_id == "miyamoto"):
        ganho = max(0, int(dead_unit.statuses.get("life_at_death", 0)))
        if ganho:
            killer_player.miyamoto_life_max_bonus += ganho
            killer_unit.life_max += ganho
            log(state, f"  {killer_unit.id} (Miyamoto) +{ganho} vida maxima "
                       f"(acumulado: {killer_player.miyamoto_life_max_bonus}).")

    if (isinstance(killer_unit, Hero)
            and killer_unit.hero_id == "bein"):
        sig = unit_signature(dead_unit)
        entry = {"sig": sig, "dwarf_owner_id": killer_player_id}
        if entry not in victim_owner.dwarf_empalados:
            victim_owner.dwarf_empalados.append(entry)
            log(state, f"  {dead_unit.id} empalado por Soneca ate os Anoes serem Curuna.")

    inherits_fae = (killer_player.people == PEOPLE_GNOMOS
                    and PEOPLE_FAE in sao_tome_effective_peoples(state, killer_player))
    if ((killer_player.people == PEOPLE_FAE or inherits_fae)
            and isinstance(killer_unit, Hero)
            and isinstance(dead_unit, Hero)):
        if not state.shop.is_empty():
            card = state.shop.draw_random(state.rng)
            killer_player.hand.append(card)
            on_artifact_obtained(state, killer_player_id)
            log(state, f"{killer_player.name} (Fadas): {killer_unit.id} matou "
                       f"Heroi {dead_unit.id} e ganhou {card}.")

    inherits_wolf = (killer_player.people == PEOPLE_GNOMOS
                     and PEOPLE_LOBISOMENS in sao_tome_effective_peoples(
                         state, killer_player))
    if killer_player.people == PEOPLE_LOBISOMENS or inherits_wolf:
        if add_infection(killer_player, dead_unit):
            log(state, f"  {dead_unit.id} infectado pela Maldicao da Lua.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if heroes.has_ability(u.hero_id, "empala_on_kill"):
            sig = unit_signature(dead_unit)
            if sig not in victim_owner.empalados:
                victim_owner.empalados.append(sig)
                log(state, f"  {dead_unit.id} empalado por Dracula (dono {victim_owner.name}).")
                # Dracula cura 2 ao empalar
                if u.life < u.life_max:
                    before = u.life
                    u.life = min(u.life_max, u.life + 2)
                    log(state, f"  {u.id} curou +{u.life - before} (Empalar).")
            if killer_player.spell_cooldown_until_turn > state.turn:
                killer_player.spell_cooldown_until_turn = 0
                log(state, "  Dracula: feitico sai da recarga.")

    if isinstance(dead_unit, Hero) and dead_unit.hero_id == "baoba_ba":
        victim_owner.baoba_pagamentos = 0
        victim_owner.baoba_invocado = False
        log(state, f"  {victim_owner.name}: Baoba-ba morreu. Pagamentos zerados.")

    if isinstance(dead_unit, Hero) and "espectro_until_turn" not in dead_unit.statuses:
        for p in state.players:
            for u in p.units:
                if (isinstance(u, Hero) and u.is_alive()
                        and u.hero_id == "cobra"):
                    state.espectros_pendentes.append({
                        "hero_id": dead_unit.hero_id,
                        "house": dead_unit.house,
                        "owner_of_cobra": p.id,
                        "original_owner_id": dead_unit.owner_id,
                    })
                    log(state, f"  Espectro agendado: {dead_unit.hero_id} em {dead_unit.house}.")

    if killer_player.people == PEOPLE_GNOMOS and killer_unit is not None:
        effective = sao_tome_effective_peoples(state, killer_player)
        if PEOPLE_VAMPIRES in effective:
            before = killer_unit.life
            killer_unit.life = min(killer_unit.life_max, killer_unit.life + 2)
            if killer_unit.life != before:
                log(state, f"  Sao Tome curou +{killer_unit.life - before} (Sede de Sangue).")

    bump_stat(state, killer_player_id, "kills")
    on_action_performed(state, killer_player_id, "kill")


def has_vovo_bonus(state: GameState, attacker: Unit) -> bool:
    """Vovo Gamba concede +1 dano GLOBAL a todas as tropas do dono (v5v10)."""
    p = get_player(state, attacker.owner_id)
    if p.people != "orcs":
        return False
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba"
               for u in p.units)
def valendar_is_alive(player: Player) -> bool:
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "valendar"
               for u in player.units)


def luna_is_alive(player: Player) -> bool:
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
               for u in player.units)


SUIT_FLIP = {"H": "D", "D": "H", "S": "C", "C": "S"}


def sonho_lucido_flip(card_id: str) -> str:
    from . import artifacts
    d = artifacts.ARTIFACT_CATALOG.get(card_id)
    if d is None or not d.suit:
        return card_id
    other_suit = SUIT_FLIP[d.suit]
    new_id = f"{d.rank}_{other_suit}"
    if new_id in artifacts.ARTIFACT_CATALOG:
        return new_id
    return card_id


def is_lua_cheia(state: GameState, lobisomem_player_id: int) -> bool:
    order = state.turn_order
    if not order:
        return False
    if lobisomem_player_id not in order:
        return False
    idx = order.index(lobisomem_player_id)
    next_pid = order[(idx + 1) % len(order)]
    return state.curuna_id == next_pid


def is_lobisomem_ativo(state: GameState, unit: Unit) -> bool:
    if unit.statuses.get("lobisomem_until_turn", -1) >= state.turn:
        return True
    owner = get_player(state, unit.owner_id)
    if (owner.people == PEOPLE_GNOMOS
            and PEOPLE_LOBISOMENS in sao_tome_effective_peoples(state, owner)):
        return is_lua_cheia(state, owner.id)
    if owner.people != PEOPLE_LOBISOMENS:
        return False
    return is_lua_cheia(state, owner.id)


def apply_lua_cheia_effects(state: GameState) -> None:
    for p in state.players:
        inherits = (p.people == PEOPLE_GNOMOS
                    and PEOPLE_LOBISOMENS in sao_tome_effective_peoples(state, p))
        if p.people != PEOPLE_LOBISOMENS and not inherits:
            continue
        if not p.city.is_alive():
            continue
        if not is_lua_cheia(state, p.id):
            continue

        log(state, f"--- LUA CHEIA para {p.name} ---")
        _flip_infected(state, p)

        has_lupa = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "lupa_lider"
                       for u in p.units)
        has_cigana = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "cigana"
                         for u in p.units)
        has_luarado = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luarado"
                          for u in p.units)

        for u in p.units:
            if not u.is_alive():
                continue
            apply_lua_cheia_unit_buffs(state, p, u, has_lupa, has_cigana)
            if has_luarado and isinstance(u, Hero) and u.hero_id == "luarado":
                u.max_moves_this_turn = 2
                u.has_moved_this_turn = False
                u.moves_this_turn = 0


def apply_lua_cheia_unit_buffs(state: GameState, player: Player, unit: Unit,
                               has_lupa: bool | None = None,
                               has_cigana: bool | None = None) -> None:
    if not is_lua_cheia(state, player.id):
        return
    apply_lobisomem_hero_buffs(state, player, unit, has_lupa, has_cigana)


def apply_lobisomem_hero_buffs(state: GameState, player: Player, unit: Unit,
                               has_lupa: bool | None = None,
                               has_cigana: bool | None = None) -> None:
    if has_lupa is None:
        has_lupa = any(isinstance(u, Hero) and u.is_alive()
                       and u.hero_id == "lupa_lider" for u in player.units)
    if has_cigana is None:
        has_cigana = any(isinstance(u, Hero) and u.is_alive()
                         and u.hero_id == "cigana" for u in player.units)
    if has_lupa and unit.statuses.get("lupa_resist_until_turn", -1) < state.turn:
        unit.resistance_stacks += 1
        unit.statuses["lupa_resist_until_turn"] = state.turn
    if has_cigana:
        unit.statuses["invisivel_until_turn"] = state.turn


def _flip_infected(state: GameState, lobisomem: Player) -> None:
    if not lobisomem.infectados:
        return
    used: set[str] = set()
    for record in lobisomem.infectados:
        owners = [get_player(state, record["owner_id"])] \
            if record.get("owner_id") is not None else list(state.players)
        chosen = None
        chosen_owner = None
        for other in owners:
            if other.id == lobisomem.id or not other.city.is_alive():
                continue
            candidates = [u for u in other.units
                          if u.id not in used and u.is_alive()
                          and u.original_owner_id is None
                          and not (isinstance(u, Hero) and u.hero_id == "valtherion")
                          and infection_matches(record, u)]
            exact = next((u for u in candidates
                          if u.id == record.get("unit_id")), None)
            if exact is not None or candidates:
                chosen = exact or candidates[0]
                chosen_owner = other
                break
        if chosen is None or chosen_owner is None:
            continue
        used.add(chosen.id)
        record["unit_id"] = chosen.id
        record["owner_id"] = chosen_owner.id
        chosen_owner.units.remove(chosen)
        lobisomem.units.append(chosen)
        chosen.original_owner_id = chosen_owner.id
        chosen.owner_id = lobisomem.id
        chosen.statuses["lobisomem_until_turn"] = state.turn
        sync_house_priority(state, chosen.house)
        log(state, f"  {chosen.id} ({chosen_owner.name}) virou Lobisomem "
                   f"(controlado por {lobisomem.name}).")


def apply_cova_rasa(state: GameState) -> None:
    """Amaldicoa todas unidades inimigas na mesma casa da Cova Rasa."""
    for p in state.players:
        for u in p.units:
            if not (isinstance(u, Hero) and u.is_alive() and u.hero_id == "cova_rasa"):
                continue
            if not p.city.is_alive():
                continue
            home = u.house
            total = 0
            for other in state.players:
                if other.id == p.id:
                    continue
                for enemy in other.units:
                    if enemy.house == home and enemy.is_alive():
                        enemy.statuses["amaldicoado_until_turn"] = state.turn
                        total += 1
            log(state, f"{p.name}: Cova Rasa amaldicoou {total} inimigo(s) em {home}.")


def apply_presenca_magnetica(state: GameState) -> None:
    """Joao Grandao forca inimigos da casa a ataca-lo (ordem: maior vida -> menor).
    Consome ataques normais. Joao retalia. Se morrer, restantes cancelam."""
    from .combat import resolve_attack, Attack, CombatError, _effective_max_attacks, _attacks_used

    triggered = [e for e in state.pending_effects
                 if e["kind"] == "JOAO_PRESENCA" and e["due_turn"] == state.turn]
    for e in triggered:
        state.pending_effects.remove(e)
        owner = get_player(state, e["player_id"])
        joao = next((u for u in owner.units
                     if isinstance(u, Hero) and u.is_alive() and u.hero_id == "joao_grandao"),
                    None)
        if joao is None:
            continue
        home = joao.house
        enemies = []
        for other in state.players:
            if other.id == owner.id:
                continue
            for u in other.units:
                if u.house == home and u.is_alive():
                    enemies.append(u)
        enemies.sort(key=lambda u: u.life, reverse=True)
        log(state, f"Presenca Magnetica em {home}: {len(enemies)} inimigo(s) forcado(s).")
        for enemy in enemies:
            if not joao.is_alive():
                log(state, "  Joao morreu - restantes cancelados.")
                break
            if not enemy.is_alive():
                continue
            max_atk = _effective_max_attacks(state, enemy)
            while _attacks_used(enemy) < max_atk:
                if not joao.is_alive():
                    break
                try:
                    resolve_attack(state, Attack(enemy.id, "unit", joao.id))
                except CombatError as ex:
                    log(state, f"  {enemy.id} nao pode atacar: {ex}")
                    break


def magic_cost_reduction(player: Player, state: GameState | None = None) -> int:
    if player.people == PEOPLE_ORCS:
        return 1
    if player.people == PEOPLE_GNOMOS and state is not None:
        if PEOPLE_ORCS in sao_tome_effective_peoples(state, player):
            return 1
    return 0


def hero_summon_cost(player: Player, state: GameState | None = None) -> int:
    if player.people == PEOPLE_GIGANTES:
        return 4
    if player.people == PEOPLE_MORTOS_VIVOS:
        return 2
    if player.people == PEOPLE_GNOMOS and state is not None:
        effective = sao_tome_effective_peoples(state, player)
        if PEOPLE_MORTOS_VIVOS in effective:
            return 2
        if PEOPLE_GIGANTES in effective:
            return 4
    return max(0, 3 - magic_cost_reduction(player, state))


def base_troop_slots() -> dict[str, int]:
    return {"light": 1, "medium": 1, "heavy": 1}


def extra_troop_slots(player: Player, state: GameState | None = None) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    if player.people == PEOPLE_MORTOS_VIVOS:
        # MV: 3 tropas base + 2 (ghoul/esqueleto) SO com Zoia viva. Sem "extra".
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
               for u in player.units):
            return {"ghoul": 1, "esqueleto": 1}
    if player.people == PEOPLE_GNOMOS and state is not None:
        effective = sao_tome_effective_peoples(state, player)
        result: dict[str, int] = {}
        if PEOPLE_ORCS in effective:
            result["extra"] = 1
        return result
    return {}

def max_troops_of_archetype(player: Player, archetype: TroopArchetype,
                            state: GameState | None = None) -> int:
    base = base_troop_slots().get(archetype.value, 0)
    extras = extra_troop_slots(player, state)
    return base + extras.get(archetype.value, 0)


def available_archetypes(player: Player, state: GameState | None = None) -> list[TroopArchetype]:
    result = [TroopArchetype.LIGHT, TroopArchetype.MEDIUM, TroopArchetype.HEAVY]
    extras = extra_troop_slots(player, state)
    if "extra" in extras:
        result.append(TroopArchetype.EXTRA)
    if "ghoul" in extras:
        result.append(TroopArchetype.GHOUL)
    if "esqueleto" in extras:
        result.append(TroopArchetype.ESQUELETO)
    return result


def compute_hero_max_attacks_in_house(state: GameState, unit: Unit, ability: str) -> int:
    if not (isinstance(unit, Hero) and unit.is_alive()):
        return 1
    if not heroes.has_ability(unit.hero_id, ability):
        return 1
    max_life_house = unit.life
    for p in state.players:
        for u in p.units:
            if u.id == unit.id:
                continue
            if u.house == unit.house and u.is_alive():
                if u.life > max_life_house:
                    max_life_house = u.life
    return 2 if unit.life >= max_life_house else 1


def miyamoto_attacks_remaining(state: GameState, player: Player) -> int:
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto":
            from .combat import _effective_max_attacks
            total = _effective_max_attacks(state, u)
            return max(0, total - u.attacks_made_this_day)
    return 0


def has_7_dwarves_chosen(player: Player) -> bool:
    return player.chosen_hero_id == "seven_dwarves"


def alive_dwarf_count(state: GameState, player: Player) -> int:
    return sum(1 for u in player.units
               if isinstance(u, Hero) and u.is_alive() and heroes.is_seven_dwarf(u.hero_id))
