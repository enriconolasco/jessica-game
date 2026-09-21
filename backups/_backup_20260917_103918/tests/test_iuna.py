"""Testes: Iúna."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop
from jessica.core.combat import resolve_attack, Attack
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["iuna"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "Iúna"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def _make_troop(state, pid, archetype=TroopArchetype.LIGHT, life=4, house="center"):
    p = state.players[pid - 1]
    p.city.gold = max(p.city.gold, life + 5)
    p.city.magic = max(p.city.magic, 5)
    t = summon_troop(state, pid, archetype, life)
    t.house = house
    return t


def test_iuna_adds_penas_to_shop():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    before = state.shop.copies_of("PENA")
    assert before == 0, f"Penas já existem antes? {before}"
    summon_hero(state, 1)
    after = state.shop.copies_of("PENA")
    assert after == 4, f"Esperado 4 Penas, veio {after}"
    print("OK  - Iuna adicionou 4 Penas a Loja")


def test_iuna_takes_exactly_1_damage():
    """Iúna recebe exatamente 1 de dano, mesmo contra ataque de 10."""
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    iuna = summon_hero(state, 1)
    iuna.house = CENTER
    enemy = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=10, house=CENTER)
    life_before = iuna.life
    resolve_attack(state, Attack(enemy.id, "unit", iuna.id))
    assert iuna.life == life_before - 1, f"Iuna deveria perder exatamente 1, caiu {life_before - iuna.life}"
    print(f"OK  - Iuna recebe exatamente 1 de dano (vida {iuna.life})")


def test_iuna_takes_1_from_small_attacker_too():
    """Mesmo atacante pequeno: ela recebe 1."""
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    iuna = summon_hero(state, 1)
    iuna.house = CENTER
    enemy = _make_troop(state, 2, archetype=TroopArchetype.LIGHT, life=2, house=CENTER)
    life_before = iuna.life
    resolve_attack(state, Attack(enemy.id, "unit", iuna.id))
    assert iuna.life == life_before - 1, f"Esperado -1, caiu {life_before - iuna.life}"
    print(f"OK  - Iuna recebe 1 de dano de atacante pequeno")


def test_iuna_deals_1_to_4_damage():
    """Iúna dá 1D4 de dano ao atacar (não usa vida atual)."""
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    iuna = summon_hero(state, 1)
    iuna.house = CENTER
    target = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=10, house=CENTER)
    life_before = target.life
    resolve_attack(state, Attack(iuna.id, "unit", target.id))
    dmg = life_before - target.life
    assert 1 <= dmg <= 4, f"Dano fora do range 1-4: {dmg}"
    print(f"OK  - Iuna deu {dmg} de dano (1-4)")


def run_all():
    tests = [
        test_iuna_adds_penas_to_shop,
        test_iuna_takes_exactly_1_damage,
        test_iuna_takes_1_from_small_attacker_too,
        test_iuna_deals_1_to_4_damage,
    ]
    print("=== Testes Iuna ===\n")
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
