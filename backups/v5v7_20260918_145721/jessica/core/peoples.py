"""Passivas dos povos."""
from __future__ import annotations
from .state import get_player, log, bump_stat
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


ACTION_TO_BET = {
    "raise_city_life": BET_HEART,
    "lose_city_life": BET_HEART,
    "play_artifact": BET_CLUB,
    "buy_artifact_gold": BET_DIAMOND,
    "buy_artifact_magic": BET_DIAMOND,
    "transmute_artifact_magic": BET_DIAMOND,
    "sell_artifact": BET_DIAMOND,
    "summon_hero": BET_SPADE,
    "summon_troop": BET_SPADE,
    "kill": BET_SPADE,
}


def unit_signature(u: Unit) -> dict:
    if isinstance(u, Hero):
        return {"kind": "hero", "id": u.hero_id}
    return {"kind": "troop", "id": u.archetype.value}


def is_empalado(player: Player, sig: dict) -> bool:
    return sig in player.empalados


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
        gnomo.correct_bets += 1
        setattr(gnomo, f"bet_{suit}_target", None)
        actor = get_player(state, actor_id)
        log(state, f"{gnomo.name}: Aposta {suit} cumprida por {actor.name}. "
                   f"(Total: {gnomo.correct_bets} corretas)")


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
        if p.people != PEOPLE_FILHOS:
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


def reset_gnomos_bets(state: GameState) -> None:
    for p in state.players:
        if p.people != PEOPLE_GNOMOS:
            continue
        if not p.city.is_alive():
            continue
        p.bet_H_target = None
        p.bet_C_target = None
        p.bet_D_target = None
        p.bet_S_target = None
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
        u.life = max(0, u.life - 1)
        log(state, f"  1 dano em {u.id}: {u.life}/{u.life_max}.")
    for other in state.players:
        dead = [u for u in other.units if not u.is_alive()]
        for d in dead:
            log(state, f"  {d.id} morreu (Roca).")
        other.units = [u for u in other.units if u.is_alive()]


def on_unit_moved(state: GameState, player_id: int, unit: Unit) -> None:
    player = get_player(state, player_id)
    if player.people == PEOPLE_FAE:
        player.city.magic += 1
        log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id}.")
        return
    if (player.people == PEOPLE_GNOMOS
            and isinstance(unit, Hero) and unit.hero_id == "sao_tome"):
        effective = sao_tome_effective_peoples(state, player)
        if PEOPLE_FAE in effective:
            player.city.magic += 1
            log(state, f"{player.name} (Sao Tome herda Fadas): +1 Magia ao mover.")


def on_unit_killed_by(state: GameState, killer_player_id: int,
                      dead_unit: Unit, killer_unit: Unit | None = None) -> None:
    killer_player = get_player(state, killer_player_id)
    victim_owner = get_player(state, dead_unit.owner_id)

    if killer_player.people == PEOPLE_FAE and isinstance(killer_unit, Hero):
        if not state.shop.is_empty():
            card = state.shop.draw_random(state.rng)
            killer_player.hand.append(card)
            log(state, f"{killer_player.name} (Fadas): {killer_unit.id} matou "
                       f"{dead_unit.id} e ganhou {card}.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if not heroes.has_ability(u.hero_id, "gain_max_life_on_kill"):
            continue
        if u.house == dead_unit.house:
            ganho = dead_unit.statuses.get("life_at_death", dead_unit.life_max)
            u.life_max += ganho
            log(state, f"  {u.id} (Miyamoto) +{ganho} vida maxima.")

    if killer_player.people == PEOPLE_LOBISOMENS:
        sig = unit_signature(dead_unit)
        if sig not in killer_player.infectados:
            killer_player.infectados.append(sig)
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

    if (isinstance(killer_unit, Hero) and killer_unit.hero_id == "sao_tome"
            and killer_player.people == PEOPLE_GNOMOS):
        effective = sao_tome_effective_peoples(state, killer_player)
        if PEOPLE_VAMPIRES in effective:
            before = killer_unit.life
            killer_unit.life = min(killer_unit.life_max, killer_unit.life + 2)
            if killer_unit.life != before:
                log(state, f"  Sao Tome curou +{killer_unit.life - before} (Sede de Sangue).")
        if PEOPLE_LOBISOMENS in effective:
            sig = unit_signature(dead_unit)
            if sig not in killer_player.infectados:
                killer_player.infectados.append(sig)
                log(state, f"  {dead_unit.id} infectado por Sao Tome (Maldicao da Lua).")

    bump_stat(state, killer_player_id, "kills")
    on_action_performed(state, killer_player_id, "kill")


def has_vovo_bonus(state: GameState, attacker: Unit) -> bool:
    if not isinstance(attacker, Troop):
        return False
    owner = get_player(state, attacker.owner_id)
    for u in owner.units:
        if (isinstance(u, Hero) and u.is_alive()
                and u.hero_id == "vovo_gamba"
                and u.house == attacker.house):
            return True
    return False


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
    if owner.people != PEOPLE_LOBISOMENS:
        return False
    return is_lua_cheia(state, owner.id)


def apply_lua_cheia_effects(state: GameState) -> None:
    for p in state.players:
        if p.people != PEOPLE_LOBISOMENS:
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
            if has_lupa:
                if u.statuses.get("lupa_resist_until_turn", -1) < state.turn:
                    u.resistance_stacks += 1
                    u.statuses["lupa_resist_until_turn"] = state.turn
            if has_cigana:
                u.statuses["invisivel_until_turn"] = state.turn
            if has_luarado and isinstance(u, Hero) and u.hero_id == "luarado":
                u.max_moves_this_turn = 2
                u.has_moved_this_turn = False
                u.moves_this_turn = 0


def _flip_infected(state: GameState, lobisomem: Player) -> None:
    if not lobisomem.infectados:
        return
    sigs_hero = {e["id"] for e in lobisomem.infectados if e["kind"] == "hero"}
    sigs_troop = {e["id"] for e in lobisomem.infectados if e["kind"] == "troop"}

    for other in state.players:
        if other.id == lobisomem.id:
            continue
        if not other.city.is_alive():
            continue
        for u in list(other.units):
            if not u.is_alive():
                continue
            if u.original_owner_id is not None:
                continue
            matches = False
            if isinstance(u, Hero) and u.hero_id in sigs_hero:
                matches = True
            elif isinstance(u, Troop) and u.archetype.value in sigs_troop:
                matches = True
            if not matches:
                continue
            other.units.remove(u)
            lobisomem.units.append(u)
            u.original_owner_id = other.id
            u.owner_id = lobisomem.id
            u.statuses["lobisomem_until_turn"] = state.turn
            log(state, f"  {u.id} ({other.name}) virou Lobisomem (controlado por {lobisomem.name}).")


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
    return max(0, 3 - magic_cost_reduction(player, state))


def base_troop_slots() -> dict[str, int]:
    return {"light": 1, "medium": 1, "heavy": 1}


def extra_troop_slots(player: Player, state: GameState | None = None) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    if player.people == PEOPLE_MORTOS_VIVOS:
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
