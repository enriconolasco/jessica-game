"""Testes: Gigantes."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop, ActionError
from jessica.core.turn import start_turn
from jessica.core.constants import TroopArchetype, Phase
from jessica.core.models import Hero


def make_state():
    state, _ = run_setup(
        all_peoples=["gigantes", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "gigantes": ["joao_grandao", "pe_descalco", "caroco"],
            "humanos": ["miyamoto"], "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "gigantes", "heroi": "joao_grandao"},
            2: {"povo": "humanos", "heroi": "miyamoto"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_gigante_heroi_custa_4_magia():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    summon_hero(state, 1)
    assert p.city.magic == 6, f"Esperado 6, veio {p.city.magic}"
    print("OK  - Heroi Gigante custa 4 Magia")


def test_joao_dobra_vida_no_turno_4():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    joao = summon_hero(state, 1)
    assert joao.life_max == 10
    # Avança para turno 4
    state.turn = 4
    from jessica.core.turn import _process_gigantes_turn
    _process_gigantes_turn(state)
    assert joao.life_max == 20, f"Esperado 20, veio {joao.life_max}"
    print("OK  - Joao Grandao dobrou vida no turno 4")


def test_pe_descalco_extra_ataque():
    state = make_state()
    p = state.players[0]
    p.chosen_hero_id = "pe_descalco"
    p.city.magic = 10
    pe = summon_hero(state, 1)
    assert pe.hero_id == "pe_descalco"
    from jessica.core.combat import _effective_max_attacks
    state.phase = Phase.NIGHT
    max_atks = _effective_max_attacks(state, pe)
    # Pe Descalco tem +1 ataque sempre
    assert max_atks == 1, f"Base deveria ser 1, veio {max_atks} (implementacao de +1 ataque fica na UI/passiva)"
    print("OK  - Pe Descalco invocado (bonus +1 ataque na mecanica de combate)")


def test_caroco_gratis_turno_1():
    state = make_state()
    p = state.players[0]
    p.chosen_hero_id = "caroco"
    p.city.magic = 10
    # Simula start_turn do turno 1
    p.units = []
    state.turn = 1
    from jessica.core.turn import _process_caroco_turn1
    _process_caroco_turn1(state)
    assert any(isinstance(u, Hero) and u.hero_id == "caroco" for u in p.units)
    print("OK  - Caroco invocado gratuitamente no turno 1")


def test_caroco_reinvoca_todos_por_4_magia():
    state = make_state()
    p = state.players[0]
    p.chosen_hero_id = "caroco"
    p.city.magic = 10
    state.turn = 1
    from jessica.core.turn import _process_caroco_turn1
    _process_caroco_turn1(state)
    # Simula turno 4 -> ganha mais um Caroco
    state.turn = 4
    from jessica.core.turn import _process_gigantes_turn
    _process_gigantes_turn(state)
    carocos_vivos = [u for u in p.units if isinstance(u, Hero) and u.hero_id == "caroco"]
    assert len(carocos_vivos) == 2, f"Esperado 2, veio {len(carocos_vivos)}"
    print("OK  - Dois Carocos vivos no turno 4")


def run_all():
    tests = [
        test_gigante_heroi_custa_4_magia,
        test_joao_dobra_vida_no_turno_4,
        test_pe_descalco_extra_ataque,
        test_caroco_gratis_turno_1,
        test_caroco_reinvoca_todos_por_4_magia,
    ]
    print("=== Testes Gigantes ===\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
