"""
Testes das ações do Dia.
Rode com:  python tests/test_actions.py
"""
import sys
import os

# Garante que o pacote "jessica" seja encontrado
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    collect_resources,
    raise_city_life,
    apply_gold_interest,
    ActionError,
)


def make_state():
    return run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["m"],
            "anoes": ["b"],
            "orcs": ["g"],
            "fadas": ["ai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "m"},
            2: {"povo": "anoes", "heroi": "b"},
            3: {"povo": "orcs", "heroi": "g"},
            4: {"povo": "fadas", "heroi": "ai"},
        },
        seed=20260916,
    )


def test_collect_once():
    state, _ = make_state()
    collect_resources(state, 1, 2, 0)
    city = state.players[0].city
    assert city.gold == 2, f"Ouro esperado 2, veio {city.gold}"
    assert city.magic == 0, f"Magia esperada 0, veio {city.magic}"
    print("OK  - coleta simples funcionou")


def test_collect_twice_blocked():
    state, _ = make_state()
    collect_resources(state, 1, 2, 0)
    try:
        collect_resources(state, 1, 0, 2)
        raise AssertionError("Deveria ter bloqueado a segunda coleta")
    except ActionError as e:
        print(f"OK  - segunda coleta bloqueada: {e}")


def test_collect_invalid_amount():
    state, _ = make_state()
    try:
        collect_resources(state, 1, 1, 0)
        raise AssertionError("Deveria ter bloqueado coleta de 1 recurso")
    except ActionError as e:
        print(f"OK  - coleta inválida bloqueada: {e}")


def test_raise_city_life():
    state, _ = make_state()
    collect_resources(state, 1, 2, 0)  # pega 2 de ouro
    raise_city_life(state, 1, 1)       # gasta 2, sobe +1
    city = state.players[0].city
    assert city.life == 3, f"Vida esperada 3, veio {city.life}"
    assert city.gold == 0, f"Ouro esperado 0, veio {city.gold}"
    print("OK  - subir vida da cidade funcionou")


def test_raise_city_life_insufficient_gold():
    state, _ = make_state()
    try:
        raise_city_life(state, 1, 1)
        raise AssertionError("Deveria ter bloqueado por ouro insuficiente")
    except ActionError as e:
        print(f"OK  - ouro insuficiente bloqueado: {e}")


def test_gold_interest():
    state, _ = make_state()
    # Dá 32 de ouro direto para testar o rendimento
    state.players[0].city.gold = 32
    apply_gold_interest(state)
    assert state.players[0].city.gold == 38, (
        f"Ouro esperado 38, veio {state.players[0].city.gold}"
    )
    print("OK  - rendimento de ouro (32 -> 38) funcionou")


def run_all():
    tests = [
        test_collect_once,
        test_collect_twice_blocked,
        test_collect_invalid_amount,
        test_raise_city_life,
        test_raise_city_life_insufficient_gold,
        test_gold_interest,
    ]
    print("=== Rodando testes de actions.py ===\n")
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