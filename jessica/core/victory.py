from __future__ import annotations
from typing import Optional
from .state import log
from .models import GameState


def check_victory(state: GameState) -> Optional[int]:
    if state.game_over:
        return state.winner_id

    alive = state.alive_players()

    if len(alive) == 1:
        state.game_over = True
        state.winner_id = alive[0].id
        log(state, f"Vitória! {alive[0].name} é a última Cidade viva.")
        return state.winner_id

    if len(alive) == 0:
        state.game_over = True
        state.winner_id = None
        log(state, "Empate! Nenhuma Cidade sobreviveu.")
        return None

    return None


def is_game_over(state: GameState) -> bool:
    return state.game_over