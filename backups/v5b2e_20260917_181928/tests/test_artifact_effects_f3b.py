"""Testes F3b: K-spades e K-clubs."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, summon_troop, summon_hero, ActionError,
)
from jessica.core.combat import resolve_attack, Attack, CombatError
from jessica.core.turn import end_day, end_turn
from jessica.core.constants import TroopArchetype, Phase


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
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
    t.has_moved_this_turn = False
    return t


def _make_hero(state, pid, house="center"):
    p = state.players[pid - 1]
    p.city.magic = max(p.city.magic, 10)
    h = summon_hero(state, pid)
    h.house = house
    h.has_moved_this_turn = False
    return h


def test_k_s_requires_no_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    assert any(a.card_id == "K_S" for a in p.field_artifacts)
    print("OK  - Ks jogado sem alvo")


def test_k_s_lets_hero_attack_city():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    hero = _make_hero(state, 1, house="city_2")
    end_day(state)
    city2 = state.players[1].city
    life_before = city2.life
    resolve_attack(state, Attack(hero.id, "city", "2"))
    assert city2.life == life_before - 1
    print(f"OK  - Ks: Heroi atacou Cidade ({life_before} -> {city2.life})")


def test_without_k_s_hero_cannot_attack_city():
    state = make_state()
    hero = _make_hero(state, 1, house="city_2")
    end_day(state)
    try:
        resolve_attack(state, Attack(hero.id, "city", "2"))
        raise AssertionError("Deveria bloquear")
    except CombatError as e:
        print(f"OK  - Sem Ks: Heroi vs Cidade bloqueado: {e}")


def test_k_s_allows_two_attacks_for_nearby_troop():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)
    assert troop.max_attacks_this_night == 2, f"Esperado 2, veio {troop.max_attacks_this_night}"
    print("OK  - Ks: tropa perto de Heroi ganha 2 ataques")


def test_k_s_troop_without_hero_nearby_has_one_attack():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="city_1")
    end_day(state)
    assert troop.max_attacks_this_night == 1
    print("OK  - Ks: tropa longe mantem 1 ataque")


def test_two_attacks_actually_happen():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)
    troop.house = "city_2"
    city2 = state.players[1].city
    life_before = city2.life
    resolve_attack(state, Attack(troop.id, "city", "2"))
    assert troop.attacks_made_this_night == 1
    resolve_attack(state, Attack(troop.id, "city", "2"))
    assert troop.attacks_made_this_night == 2
    assert city2.life == life_before - 2
    print("OK  - Ks: 2 ataques funcionaram")


def test_k_s_returns_to_shop_at_end_turn():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    shop_after_play = state.shop.size()
    end_turn(state)
    assert not any(a.card_id == "K_S" for a in p.field_artifacts)
    assert state.shop.size() == shop_after_play + 1
    print("OK  - Ks volta a Loja")


def test_k_s_buffs_clear_at_end_turn():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    hero = _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)
    assert hero.hero_can_attack_city is True
    assert troop.max_attacks_this_night == 2
    end_turn(state)
    assert hero.hero_can_attack_city is False
    assert troop.max_attacks_this_night == 1
    print("OK  - Ks buffs limpam")


def test_k_c_requires_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_C")
    try:
        play_artifact(state, 1, "K_C")
        raise AssertionError("Deveria exigir alvo")
    except (ActionError, ValueError) as e:
        print(f"OK  - Kc sem alvo bloqueado: {e}")


def test_k_c_applies_buffs():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_C")
    troop = _make_troop(state, 1, life=4)
    play_artifact(state, 1, "K_C", choice={"unit_id": troop.id})
    assert troop.double_damage is True
    assert troop.resistance_stacks == 1
    print("OK  - Kc: alvo ganhou dobro e resistencia")


def test_k_c_doubles_damage():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("K_C")
    t1 = _make_troop(state, 1, life=4, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "K_C", choice={"unit_id": t1.id})
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t2.is_alive()
    assert t1.life == 1, f"t1 deveria ficar com 1, veio {t1.life}"
    print(f"OK  - Kc: dobro + resistencia (t1 com {t1.life})")


def test_k_c_returns_to_shop_on_target_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("K_C")
    t1 = _make_troop(state, 1, life=2, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    play_artifact(state, 1, "K_C", choice={"unit_id": t1.id})
    shop_before = state.shop.size()
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t1.is_alive()
    assert not any(a.card_id == "K_C" for a in p.field_artifacts)
    assert state.shop.size() == shop_before + 1
    print("OK  - Kc: volta a Loja quando alvo morre")


def test_resistance_divides_damage():
    state = make_state()
    state.phase = Phase.NIGHT
    t1 = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=5, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=5, house="center")
    t2.resistance_stacks = 1
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert t2.life == 3, f"t2 deveria ficar com 3, veio {t2.life}"
    print(f"OK  - Resistencia 1 stack: 5 -> 2")


def run_all():
    tests = [
        test_k_s_requires_no_target,
        test_k_s_lets_hero_attack_city,
        test_without_k_s_hero_cannot_attack_city,
        test_k_s_allows_two_attacks_for_nearby_troop,
        test_k_s_troop_without_hero_nearby_has_one_attack,
        test_two_attacks_actually_happen,
        test_k_s_returns_to_shop_at_end_turn,
        test_k_s_buffs_clear_at_end_turn,
        test_k_c_requires_target,
        test_k_c_applies_buffs,
        test_k_c_doubles_damage,
        test_k_c_returns_to_shop_on_target_death,
        test_resistance_divides_damage,
    ]
    print("=== Testes F3b ===\n")
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
