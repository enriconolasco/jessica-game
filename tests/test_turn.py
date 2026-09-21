"""
Testes do loop de turno e vitória.
Rode com:  python tests/test_turn.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.turn import start_turn, day_order, end_day, end_turn
from jessica.core.victory import check_victory
from jessica.core.constants import Phase


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["m"], "anoes": ["b"], "orcs": ["g"], "fadas": ["ai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "m"},
            2: {"povo": "anoes", "heroi": "b"},
            3: {"povo": "orcs", "heroi": "g"},
            4: {"povo": "fadas", "heroi": "ai"},
        },
        seed=20260916,
    )
    return state


def test_start_turn_sets_day():
    state = make_state()
    state.phase = Phase.NIGHT
    start_turn(state)
    assert state.phase == Phase.DAY, "Fase deveria ser DIA após start_turn"
    print("OK  - start_turn coloca a fase em DIA")


def test_day_order_starts_with_curuna():
    state = make_state()
    start_turn(state)
    order = day_order(state)
    assert order[0] == state.curuna_id, "Dia deve começar pelo Curuna"
    assert len(order) == 4, f"Esperado 4 jogadores no Dia, veio {len(order)}"
    print(f"OK  - Ordem do Dia começa pelo Curuna: {order}")


def test_end_turn_rotates_curuna():
    state = make_state()
    start_turn(state)
    first_curuna = state.curuna_id
    end_turn(state)
    assert state.curuna_id != first_curuna, "Curuna deveria ter mudado"
    assert state.turn == 2, f"Turno esperado 2, veio {state.turn}"
    print(f"OK  - Curuna rotacionou de {first_curuna} para {state.curuna_id}")


def test_victory_when_one_city_left():
    state = make_state()
    # Destrói 3 cidades
    state.players[1].city.life = 0
    state.players[2].city.life = 0
    state.players[3].city.life = 0
    winner = check_victory(state)
    assert winner == 1, f"Vencedor esperado 1, veio {winner}"
    assert state.game_over is True
    print("OK  - Vitória detectada quando sobra 1 Cidade")


def test_no_victory_with_many_alive():
    state = make_state()
    winner = check_victory(state)
    assert winner is None, "Não deveria haver vencedor com 4 vivos"
    assert state.game_over is False
    print("OK  - Sem vitória com 4 Cidades vivas")


def test_day_order_skips_dead_players():
    state = make_state()
    state.players[1].city.life = 0   # Jogador 2 morto
    start_turn(state)
    order = day_order(state)
    assert 2 not in order, "Jogador morto não deve aparecer no Dia"
    print(f"OK  - Ordem do Dia ignora eliminados: {order}")


def run_all():
    tests = [
        test_start_turn_sets_day,
        test_day_order_starts_with_curuna,
        test_end_turn_rotates_curuna,
        test_victory_when_one_city_left,
        test_no_victory_with_many_alive,
        test_day_order_skips_dead_players,
    ]
    print("=== Rodando testes de turn.py / victory.py ===\n")
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== Resultado: {passed} passaram, {failed} falharam ===")


if __name__ == "__main__":
    run_all()