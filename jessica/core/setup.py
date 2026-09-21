from __future__ import annotations
from dataclasses import dataclass
from .constants import (
    DEFAULT_CITY_LIFE_START, DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC,
)
from .state import make_rng, create_empty_state, get_player, log
from .models import GameState
from .rng import DeterministicRNG
from . import heroes


FILHOS_PEOPLE = "filhos_floresta"


@dataclass
class SetupResult:
    turn_order: list[int]
    banned_peoples: list[str]
    chosen_peoples: dict[int, str]
    chosen_heroes: dict[int, str]


def roll_d20_order(rng: DeterministicRNG, num_players: int) -> list[int]:
    rolls: dict[int, int] = {i + 1: rng.randint(1, 20) for i in range(num_players)}
    while True:
        by_value: dict[int, list[int]] = {}
        for pid, val in rolls.items():
            by_value.setdefault(val, []).append(pid)
        tied_groups = [pids for pids in by_value.values() if len(pids) > 1]
        if not tied_groups:
            break
        for group in tied_groups:
            for pid in group:
                rolls[pid] = rng.randint(1, 20)
    ordered = sorted(rolls.items(), key=lambda kv: kv[1], reverse=True)
    return [pid for pid, _ in ordered]


def horario_from(order: list[int]) -> list[int]:
    if not order:
        return []
    return [order[0]] + list(reversed(order[1:]))


def run_setup(
    all_peoples: list[str],
    heroes_by_people: dict[str, list[str]],
    choices: dict[int, dict],
    seed: int,
    num_players: int = 4,
    turn_order: list[int] | None = None,
    city_life: int = DEFAULT_CITY_LIFE_START,
    city_life_max: int = DEFAULT_CITY_LIFE_MAX,
    gold_start: int = DEFAULT_STARTING_GOLD,
    magic_start: int = DEFAULT_STARTING_MAGIC,
) -> tuple[GameState, SetupResult]:
    rng = make_rng(seed)
    state = create_empty_state(
        num_players=num_players,
        city_life=city_life,
        city_life_max=city_life_max,
        seed=seed,
        gold_start=gold_start,
        magic_start=magic_start,
    )
    if turn_order is None:
        order = roll_d20_order(rng, num_players)
    else:
        order = list(turn_order)
    state.turn_order = order
    log(state, f"Ordem de turno (anti-horario): {order}")
    povo_order = horario_from(order)
    log(state, f"Ordem de povo (horario): {povo_order}")

    banned: list[str] = []
    reversed_order = list(reversed(order))
    for pid in reversed_order[:2]:
        if "ban" in choices[pid] and choices[pid]["ban"]:
            povo = choices[pid]["ban"]
            banned.append(povo)
            log(state, f"Jogador {pid} banou: {povo}")
    if banned:
        log(state, f"Povos disponiveis: {[p for p in all_peoples if p not in banned]}")
    else:
        log(state, "Nenhum povo banido.")

    chosen_peoples: dict[int, str] = {}
    for pid in povo_order:
        povo = choices[pid]["povo"]
        chosen_peoples[pid] = povo
        get_player(state, pid).people = povo
        log(state, f"Jogador {pid} escolheu: {povo}")

    chosen_heroes: dict[int, str] = {}
    for pid in povo_order:
        povo = choices[pid]["povo"]
        if povo == "mortos_vivos":
            chosen_heroes[pid] = ""
            get_player(state, pid).chosen_hero_id = None
            log(state, f"Jogador {pid} (Mortos-Vivos): escolha de heroi pulada.")
            continue
        raw_hero = choices[pid]["heroi"]
        canonical = heroes.resolve_hero_for_people(povo, raw_hero)
        chosen_heroes[pid] = canonical
        get_player(state, pid).chosen_hero_id = canonical
        log(state, f"Jogador {pid} escolheu heroi: {canonical}")

    # Filhos da Floresta: passiva Florescimento Exuberante (vida inicial 1)
    for pid in povo_order:
        if chosen_peoples[pid] == FILHOS_PEOPLE:
            p = get_player(state, pid)
            p.city.life = 1
            log(state, f"Jogador {pid} (Filhos): Florescimento Exuberante - vida inicial 1.")

    state.curuna_id = order[0]
    # Ordem de jogo fixa: anti-horario no mapa (baixo -> direita -> cima -> esquerda)
    state.turn_order = [1, 2, 3, 4]
    log(state, f"Ordem de jogo (anti-horaria): {state.turn_order}")
    log(state, f"Curuna inicial: J{state.curuna_id}")

    return state, SetupResult(
        turn_order=order,
        banned_peoples=banned,
        chosen_peoples=chosen_peoples,
        chosen_heroes=chosen_heroes,
    )
