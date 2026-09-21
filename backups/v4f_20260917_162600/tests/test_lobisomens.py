"""Testes: Lobisomens."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop
from jessica.core.combat import resolve_attack, Attack
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["lobisomens", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "lobisomens": ["lupa_lider", "cigana", "luarado"],
            "humanos": ["miyamoto"], "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "lobisomens", "heroi": "lupa_lider"},
            2: {"povo": "humanos", "heroi": "miyamoto"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def _troop(state, pid, arche, life=4, house="center"):
    p = state.players[pid-1]
    p.city.gold = 20
    p.city.magic = 10
    t = summon_troop(state, pid, arche, life)
    t.house = house
    return t


def test_lua_cheia_detection():
    """Lua cheia = jogador lobisomem é o último (curuna é o próximo)."""
    state = make_state()
    order = state.turn_order
    # Força curuna para o proximo do lobisomem
    idx = order.index(1)  # J1 é lobisomem
    next_pid = order[(idx + 1) % len(order)]
    state.curuna_id = next_pid
    assert peoples.is_lua_cheia(state, 1) is True
    # Força curuna para o lobisomem mesmo -> não é lua cheia
    state.curuna_id = 1
    assert peoples.is_lua_cheia(state, 1) is False
    print("OK  - Lua Cheia detectada corretamente")


def test_dobro_de_dano_em_lua_cheia():
    state = make_state()
    state.phase = Phase.NIGHT
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    lob = _troop(state, 1, TroopArchetype.HEAVY, 4, "center")
    victim = _troop(state, 2, TroopArchetype.HEAVY, 8, "center")
    resolve_attack(state, Attack(lob.id, "unit", victim.id))
    # Sem lua cheia: lob 4 vs vit 8 -> vit 4, lob morre (tomou 8)
    # Com lua cheia: lob 4x2=8 -> vit morre; lob toma 8 -> morre.
    assert not victim.is_alive(), f"Vitima deveria morrer com dano dobrado, vida {victim.life}"
    print("OK  - Dobro de dano em Lua Cheia matou vitima de 8")


def test_infeccao_registrada_ao_matar():
    state = make_state()
    state.phase = Phase.NIGHT
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    lob = _troop(state, 1, TroopArchetype.HEAVY, 4, "center")
    victim = _troop(state, 2, TroopArchetype.HEAVY, 8, "center")
    resolve_attack(state, Attack(lob.id, "unit", victim.id))
    p1 = state.players[0]
    assert {"kind": "troop", "id": "heavy"} in p1.infectados
    print("OK  - Tropa heavy infectada registrada")


def test_cigana_ataca_cidade_em_lua_cheia():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    p1.chosen_hero_id = "cigana"
    # Remove Lupa viva antes de invocar Cigana
    p1.units = []
    cigana = summon_hero(state, 1)
    cigana.house = "city_2"
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    city2 = state.players[1].city
    before = city2.life
    resolve_attack(state, Attack(cigana.id, "city", "2"))
    assert city2.life == before - 1, f"Cidade deveria perder 1, veio {city2.life}"
    print("OK  - Cigana atacou Cidade em Lua Cheia")


def test_lupa_resistencia_em_lua_cheia():
    from jessica.core.actions import cast_spell
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 10
    # J1 = lupa_lider
    lupa = summon_hero(state, 1)
    t1 = summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    # Forçar lua cheia e chamar apply
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    peoples.apply_lua_cheia_effects(state)
    assert lupa.resistance_stacks >= 1
    assert t1.resistance_stacks >= 1
    print("OK  - Lupa concedeu resistencia a todos em Lua Cheia")


def run_all():
    tests = [
        test_lua_cheia_detection,
        test_dobro_de_dano_em_lua_cheia,
        test_infeccao_registrada_ao_matar,
        test_cigana_ataca_cidade_em_lua_cheia,
        test_lupa_resistencia_em_lua_cheia,
    ]
    print("=== Testes Lobisomens ===\n")
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
