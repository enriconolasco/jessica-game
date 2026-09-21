"""Testes de configuração inicial (vida, ouro, magia)."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup


def make_state(**kwargs):
    params = dict(
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
    params.update(kwargs)
    state, _ = run_setup(**params)
    return state


def test_defaults():
    state = make_state()
    for p in state.players:
        assert p.city.life == 2, f"Vida padrão esperada 2, veio {p.city.life}"
        assert p.city.life_max == 6, f"Vida máx esperada 6, veio {p.city.life_max}"
        assert p.city.gold == 0
        assert p.city.magic == 0
    print("OK  - Defaults: vida 2/6, ouro 0, magia 0")


def test_custom_life():
    state = make_state(city_life=4, city_life_max=10)
    for p in state.players:
        assert p.city.life == 4
        assert p.city.life_max == 10
    print("OK  - Vida inicial 4/10 aplicada a todos")


def test_custom_gold_and_magic():
    state = make_state(gold_start=5, magic_start=3)
    for p in state.players:
        assert p.city.gold == 5, f"Ouro esperado 5, veio {p.city.gold}"
        assert p.city.magic == 3, f"Magia esperada 3, veio {p.city.magic}"
    print("OK  - Ouro 5 e Magia 3 aplicados a todos")


def test_all_custom():
    state = make_state(city_life=1, city_life_max=3, gold_start=10, magic_start=7)
    for p in state.players:
        assert p.city.life == 1
        assert p.city.life_max == 3
        assert p.city.gold == 10
        assert p.city.magic == 7
    print("OK  - Configuração completa aplicada")


def run_all():
    tests = [test_defaults, test_custom_life, test_custom_gold_and_magic, test_all_custom]
    print("=== Rodando testes de setup config ===\n")
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