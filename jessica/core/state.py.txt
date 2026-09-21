from __future__ import annotations
from .constants import (
    DEFAULT_NUM_PLAYERS,
    DEFAULT_CITY_LIFE_START,
    DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD,
    DEFAULT_STARTING_MAGIC,
    DEFAULT_SEED,
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


def get_city(state: GameState, player_id: int) -> City:
    return get_player(state, player_id).city


def log(state: GameState, message: str) -> None:
    state.event_log.append(f"[T{state.turn} {state.phase.value}] {message}")


def record_action(state: GameState, player_id: int, action: str, **params) -> None:
    state.action_log.append({
        "turn": state.turn,
        "phase": state.phase.value,
        "player_id": player_id,
        "action": action,
        "params": params,
    })