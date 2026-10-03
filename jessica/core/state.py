from __future__ import annotations
from .constants import (
    DEFAULT_NUM_PLAYERS,
    DEFAULT_CITY_LIFE_START,
    DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD,
    DEFAULT_STARTING_MAGIC,
    DEFAULT_SEED,
    CENTER,
    CITY_HOUSES,
)
from .models import City, Player, GameState
from .rng import DeterministicRNG


def make_rng(seed: int) -> DeterministicRNG:
    return DeterministicRNG(seed)


def create_city(owner_id: int, life: int, life_max: int,
                gold: int = DEFAULT_STARTING_GOLD,
                magic: int = DEFAULT_STARTING_MAGIC) -> City:
    return City(
        owner_id=owner_id,
        life=life,
        life_max=life_max,
        gold=gold,
        magic=magic,
        has_monument=False,
    )


def create_player(
    player_id: int,
    house: str,
    life: int,
    life_max: int,
    name: str | None = None,
    gold: int = DEFAULT_STARTING_GOLD,
    magic: int = DEFAULT_STARTING_MAGIC,
) -> Player:
    return Player(
        id=player_id,
        name=name or f"Jogador {player_id}",
        people="",
        city=create_city(player_id, life, life_max, gold, magic),
    )


def create_empty_state(
    num_players: int = DEFAULT_NUM_PLAYERS,
    city_life: int = DEFAULT_CITY_LIFE_START,
    city_life_max: int = DEFAULT_CITY_LIFE_MAX,
    seed: int = DEFAULT_SEED,
    gold_start: int = DEFAULT_STARTING_GOLD,
    magic_start: int = DEFAULT_STARTING_MAGIC,
) -> GameState:
    if type(num_players) is not int or not 2 <= num_players <= 5:
        raise ValueError("A partida precisa de 2 a 5 jogadores.")
    from .constants import CITY_HOUSES
    state = GameState(seed=seed, rng=make_rng(seed))
    for i in range(num_players):
        player = create_player(
            player_id=i + 1,
            house=CITY_HOUSES[i],
            life=city_life,
            life_max=city_life_max,
            gold=gold_start,
            magic=magic_start,
        )
        state.players.append(player)
    return state


def get_player(state: GameState, player_id: int) -> Player:
    for p in state.players:
        if p.id == player_id:
            return p
    raise ValueError(f"Jogador {player_id} não encontrado")


def city_houses(state):
    return tuple(f"city_{p.id}" for p in state.players)


def game_houses(state):
    return (CENTER, *city_houses(state))


def get_city(state: GameState, player_id: int) -> City:
    return get_player(state, player_id).city


def log(state: GameState, message: str) -> None:
    state.event_log.append(f"[T{state.turn} {state.phase.value}] {message}")


def bump_stat(state: GameState, player_id: int, key: str, amount: int = 1) -> None:
    player = get_player(state, player_id)
    player.stats[key] = player.stats.get(key, 0) + amount


def record_action(state: GameState, player_id: int, action: str, **params) -> None:
    state.action_log.append({
        "turn": state.turn,
        "phase": state.phase.value,
        "player_id": player_id,
        "action": action,
        "params": params,
    })


def curuna_order(state: GameState) -> list[int]:
    """Jogadores vivos a partir da Curuna, sem filtros de fase."""
    if not state.turn_order or state.curuna_id not in state.turn_order:
        return [p.id for p in state.players if p.city.is_alive()]
    alive = {p.id for p in state.players if p.city.is_alive()}
    idx = state.turn_order.index(state.curuna_id)
    order = state.turn_order[idx:] + state.turn_order[:idx]
    return [pid for pid in order if pid in alive]


def snapshot_turn_start_priority(state: GameState) -> None:
    """Fotografa ocupantes por jogador no inicio do turno.

    A prioridade pertence ao jogador. Trocar uma unidade por outra sem abandonar
    totalmente o local preserva a posicao do jogador.
    """
    houses = game_houses(state)
    order = curuna_order(state)
    state.night_priority_by_house = {}
    state.night_start_positions = {}
    for house in houses:
        state.night_priority_by_house[house] = [
            pid for pid in order
            if any(u.is_alive() and u.house == house
                   for u in get_player(state, pid).units)
        ]
    for player in state.players:
        for unit in player.units:
            if unit.is_alive():
                state.night_start_positions[f"{player.id}:{unit.id}"] = unit.house


def sync_house_priority(state: GameState, *houses: str) -> None:
    """Remove quem abandonou o local e poe novos ocupantes no fim."""
    if not state.night_priority_by_house:
        state.night_priority_by_house = {
            house: [] for house in game_houses(state)
        }
    for house in houses:
        if house not in game_houses(state):
            continue
        present = {
            p.id for p in state.players if p.city.is_alive()
            and any(u.is_alive() and u.house == house for u in p.units)
        }
        queue = [pid for pid in state.night_priority_by_house.get(house, [])
                 if pid in present]
        # Normalmente entra um jogador por vez. Se uma operacao inserir varios,
        # o desempate deterministico segue a Curuna.
        for pid in curuna_order(state):
            if pid in present and pid not in queue:
                queue.append(pid)
        state.night_priority_by_house[house] = queue


def declaration_order_for_house(state: GameState, house: str,
                                eligible: list[int] | None = None) -> list[int]:
    sync_house_priority(state, house)
    queue = list(state.night_priority_by_house.get(house, []))
    if eligible is None:
        return queue
    allowed = set(eligible)
    return [pid for pid in queue if pid in allowed]


def mark_summoned(state: GameState, player: Player, unit) -> None:
    """Regra geral: invocado no turno nao se move, mas ainda pode atacar."""
    from . import peoples
    unit.statuses["summoned_turn"] = state.turn
    unit.moves_this_turn = unit.max_moves_this_turn
    unit.has_moved_this_turn = True
    # Guarari e um Centauro permanente: excepcionalmente anda 1x ao ser invocado.
    if getattr(unit, "hero_id", None) == "guarari":
        unit.max_moves_this_turn = 1
        unit.moves_this_turn = 0
        unit.has_moved_this_turn = False
    if (getattr(unit, "hero_id", None) == "luarado"
            and peoples.is_lua_cheia(state, player.id)):
        unit.max_moves_this_turn = 1
        unit.moves_this_turn = 0
        unit.has_moved_this_turn = False
    if getattr(unit, "hero_id", None):
        if unit.hero_id not in player.summoned_hero_ids:
            player.summoned_hero_ids.append(unit.hero_id)
        peoples.apply_dragon_canastra_to_hero(state, player, unit)
    peoples.on_unit_summoned(state, player.id, unit)
    sync_house_priority(state, unit.house)
