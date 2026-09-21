from __future__ import annotations
from .constants import Phase, MONUMENT_BONUS_INTERVAL, FILHOS_BONUS_TURN
from .actions import apply_gold_interest, reset_unit_flags
from .state import (
    get_player, log, mark_summoned, snapshot_turn_start_priority,
)
from .models import GameState, Hero, Troop
from . import artifacts_effects, peoples


class TurnError(Exception):
    pass


def start_turn(state: GameState) -> list[tuple[int, int]]:
    if state.game_over:
        raise TurnError("Partida ja encerrada.")
    log(state, f"--- Inicio do Turno {state.turn} (Dia) ---")
    state.phase = Phase.DAY
    state.morning_gains = []
    # A fotografia vem antes de invocacoes, transformacoes e movimentos do turno.
    snapshot_turn_start_priority(state)
    # Reset deve preceder qualquer bonus ou invocacao do novo turno.
    reset_unit_flags(state)
    interest = apply_gold_interest(state)
    artifacts_effects.on_turn_start(state)
    if state.turn % MONUMENT_BONUS_INTERVAL == 0:
        _monument_bonus(state)
    _process_espectros(state)
    _process_caroco_turn1(state)
    _process_gigantes_turn(state)
    peoples.apply_lua_cheia_effects(state)
    peoples.apply_filhos_bonus(state)
    _reset_gnomos_bets_e_sorteio(state)
    # Guarari possui dois movimentos normais em todo turno.
    for player in state.players:
        for unit in player.units:
            if (isinstance(unit, Hero) and unit.is_alive()
                    and unit.hero_id == "guarari"
                    and unit.statuses.get("summoned_turn") != state.turn):
                unit.max_moves_this_turn = max(2, unit.max_moves_this_turn)
    return interest


def _reset_gnomos_bets_e_sorteio(state: GameState) -> None:
    peoples.reset_gnomos_bets(state)
    for p in state.players:
        if p.people == peoples.PEOPLE_GNOMOS and p.city.is_alive():
            if p.spell_copia_turn != state.turn:
                peoples.draw_spell_copia(state, p)


def _monument_bonus(state: GameState) -> None:
    for player in state.players:
        if not player.city.is_alive():
            continue
        if not player.city.has_monument:
            continue
        if state.shop.is_empty():
            continue
        card = state.shop.draw_random(state.rng)
        player.hand.append(card)
        log(state, f"{player.name}: Monumento concedeu {card}.")


def _process_espectros(state: GameState) -> None:
    if not state.espectros_pendentes:
        return
    pend = state.espectros_pendentes
    state.espectros_pendentes = []
    for e in pend:
        owner = get_player(state, e["owner_of_cobra"])
        if not owner.city.is_alive():
            continue
        from . import heroes
        hdef = heroes.get_hero(e["hero_id"])
        n = sum(1 for u in owner.units if isinstance(u, Hero))
        unit_id = f"p{owner.id}_spectre_{e['hero_id']}_{n}"
        hero = Hero(id=unit_id, owner_id=owner.id, house=e["house"],
                    life=hdef.life, life_max=hdef.life,
                    hero_id=hdef.hero_id, has_moved_this_turn=True)
        hero.statuses["espectro_until_turn"] = state.turn
        owner.units.append(hero)
        mark_summoned(state, owner, hero)
        log(state, f"{owner.name}: Espectro de {hdef.name} surgiu em {e['house']}.")


def _process_caroco_turn1(state: GameState) -> None:
    if state.turn != 1:
        return
    for player in state.players:
        if player.people != peoples.PEOPLE_GIGANTES:
            continue
        if player.chosen_hero_id != "caroco":
            continue
        if not player.city.is_alive():
            continue
        if any(isinstance(u, Hero) and u.hero_id == "caroco" for u in player.units):
            continue
        hero = Hero(id=f"p{player.id}_caroco_free",
                    owner_id=player.id, house=f"city_{player.id}",
                    life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
        player.units.append(hero)
        mark_summoned(state, player, hero)
        log(state, f"{player.name}: Caroco invocado gratuitamente (turno 1).")
    # Gnomos: Zebum gratis no turno 1
    for player in state.players:
        if player.people != peoples.PEOPLE_GNOMOS:
            continue
        if player.chosen_hero_id != "zebum":
            continue
        if not player.city.is_alive():
            continue
        if any(isinstance(u, Hero) and u.hero_id == "zebum" for u in player.units):
            continue
        hero = Hero(id=f"p{player.id}_zebum_free",
                    owner_id=player.id, house=f"city_{player.id}",
                    life=3, life_max=3, hero_id="zebum", has_moved_this_turn=True)
        player.units.append(hero)
        mark_summoned(state, player, hero)
        log(state, f"{player.name}: Zebum invocado gratuitamente (turno 1).")


def _process_gigantes_turn(state: GameState) -> None:
    if state.turn % 4 != 0:
        return
    for player in state.players:
        if player.people != peoples.PEOPLE_GIGANTES:
            continue
        if not player.city.is_alive():
            continue
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                if u.hero_id in ("joao_grandao", "pe_descalco"):
                    u.life_max *= 2
                    u.life = u.life_max
                    log(state, f"{player.name}: {u.hero_id} vida dobrada ({u.life_max}).")
        if any(isinstance(u, Hero) and u.hero_id == "caroco" for u in player.units):
            player.carocos_gerados += 1
            n = sum(1 for u in player.units if isinstance(u, Hero))
            unit_id = f"p{player.id}_caroco_extra_{n}"
            hero = Hero(id=unit_id, owner_id=player.id, house=f"city_{player.id}",
                        life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
            player.units.append(hero)
            mark_summoned(state, player, hero)
            log(state, f"{player.name}: novo Caroco gerado.")


def start_player_day(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    if player.skip_day_turn == state.turn:
        log(state, f"{player.name} esta pulado (Jc).")
        player.has_played_day_this_turn = True
        return
    if not player.morning_done_this_turn:
        player.morning_done_this_turn = True
        peoples.on_player_morning(state, player_id)
    artifacts_effects.on_player_day_start(state, player_id)


def day_order(state: GameState) -> list[int]:
    if not state.turn_order:
        raise TurnError("turn_order nao definido.")
    alive = {p.id for p in state.alive_players()}
    idx = state.turn_order.index(state.curuna_id)
    ordered = state.turn_order[idx:] + state.turn_order[:idx]
    result: list[int] = []
    for pid in ordered:
        if pid not in alive:
            continue
        p = get_player(state, pid)
        if state.phase == Phase.DAY and p.skip_day_turn == state.turn:
            continue
        if state.phase == Phase.NIGHT and p.skip_night_turn == state.turn:
            continue
        result.append(pid)
    return result


def _luna_return(state: GameState) -> None:
    for player in state.players:
        for u in player.units:
            if (isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
                    and "luna_origin_house" in u.statuses):
                origin = u.statuses.pop("luna_origin_house")
                if origin != u.house:
                    log(state, f"  Luna retorna de {u.house} para {origin}.")
                    u.house = origin


def end_day(state: GameState) -> None:
    if state.phase != Phase.DAY:
        raise TurnError("Nao esta na fase do Dia.")
    state.deaths_this_night = []
    artifacts_effects.on_night_start(state)
    pass  # v5v10 #13: Luna agora é perguntada via UI (_try_luna_return em main.py)
    state.phase = Phase.NIGHT
    log(state, f"--- Fase da Noite (Turno {state.turn}) ---")


def _snapshot_timeline(state: GameState) -> None:
    entry = {"turn": state.turn, "resources": {}}
    for p in state.players:
        entry["resources"][p.id] = {
            "gold": p.city.gold,
            "magic": p.city.magic,
            "life": p.city.life,
            "life_max": p.city.life_max,
        }
    state.timeline.append(entry)


def end_turn(state: GameState) -> None:
    # v5v10 #05: limpa 2x da UI (efeito expira no fim do turno)
    for _p in state.players:
        for _u in _p.units:
            try:
                _u.double_damage = False
            except Exception:
                pass
    from .victory import check_victory
    artifacts_effects.on_end_turn(state)
    _remove_espectros(state)
    _snapshot_timeline(state)
    check_victory(state)
    if state.game_over:
        return
    alive = {p.id for p in state.alive_players()}
    idx = state.turn_order.index(state.curuna_id)
    for offset in range(1, len(state.turn_order) + 1):
        candidate = state.turn_order[(idx + offset) % len(state.turn_order)]
        if candidate in alive:
            state.curuna_id = candidate
            break
    state.turn += 1


def _remove_espectros(state: GameState) -> None:
    for p in state.players:
        p.units = [u for u in p.units
                   if u.statuses.get("espectro_until_turn", -1) != state.turn]


# --- v5v9b: prioridade de declaração noturna --------------------------------
def snapshot_night_start(state):
    """Compatibilidade: a prioridade agora e fotografada no inicio do turno."""
    snapshot_turn_start_priority(state)

def night_start_priority(state, pid, uid) -> int:
    """0 = já estava no início da noite, 1 = chegou depois (declara por último)."""
    snap = getattr(state, "night_start_positions", None) or {}
    return 0 if f"{pid}:{uid}" in snap else 1
# ----------------------------------------------------------------------------
