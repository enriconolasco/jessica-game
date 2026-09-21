"""Testes: Don (ataques extras) e Din (Anoes atacam cidade)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop
from jessica.core.combat import (
    resolve_attack, Attack, _effective_max_attacks,
)
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["seven_dwarves"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "Os 7 Anões"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def _summon_all_7(state, pid):
    p = state.players[pid - 1]
    p.city.magic = 30
    for _ in range(7):
        summon_hero(state, pid)
    return {u.hero_id: u for u in p.units if isinstance(u, Hero)}


def test_don_extra_attacks_per_dwarf_nearby():
    """Don: 1 ataque extra por Anao proximo."""
    state = make_state()
    state.phase = Phase.NIGHT
    dwarves = _summon_all_7(state, 2)
    don = dwarves["don"]
    don.house = CENTER
    # 3 anoes na mesma casa
    dwarves["dain"].house = CENTER
    dwarves["buin"].house = CENTER
    # Calcula ataques: 1 base + 2 = 3
    max_atk = _effective_max_attacks(state, don)
    assert max_atk == 3, f"Don deveria ter 3 ataques (1 + 2), veio {max_atk}"
    print(f"OK  - Don: {max_atk} ataques com 2 anoes proximos")


def test_don_no_extra_attacks_alone():
    state = make_state()
    state.phase = Phase.NIGHT
    dwarves = _summon_all_7(state, 2)
    don = dwarves["don"]
    don.house = CENTER
    # Move todos os outros pra longe
    for hid, u in dwarves.items():
        if hid != "don":
            u.house = "city_2"
    max_atk = _effective_max_attacks(state, don)
    assert max_atk == 1, f"Don sozinho deveria ter 1 ataque, veio {max_atk}"
    print("OK  - Don sozinho: 1 ataque")


def test_din_allows_dwarf_to_attack_city():
    """Din na mesma casa permite outro Anao atacar Cidade."""
    state = make_state()
    state.phase = Phase.NIGHT
    dwarves = _summon_all_7(state, 2)
    din = dwarves["din"]
    dain = dwarves["dain"]
    # Dain vai pra cidade 1 (atacante)
    dain.house = "city_1"
    dain.attacks_made_this_night = 0
    # Sem Din: deve dar erro
    from jessica.core.combat import CombatError
    try:
        resolve_attack(state, Attack(dain.id, "city", "1"))
        raise AssertionError("Deveria bloquear ataque de anao a cidade sem Din")
    except CombatError as e:
        print(f"OK  - Sem Din: anao bloqueado: {e}")
    # Com Din na mesma casa: deve permitir
    din.house = "city_1"
    before = state.players[0].city.life
    resolve_attack(state, Attack(dain.id, "city", "1"))
    after = state.players[0].city.life
    assert after == before - 1, f"Cidade 1 deveria perder 1 de vida, caiu {before - after}"
    print(f"OK  - Com Din: anao atacou Cidade (vida {before} -> {after})")


def run_all():
    tests = [
        test_don_extra_attacks_per_dwarf_nearby,
        test_don_no_extra_attacks_alone,
        test_din_allows_dwarf_to_attack_city,
    ]
    print("=== Testes Don/Din ===\n")
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
