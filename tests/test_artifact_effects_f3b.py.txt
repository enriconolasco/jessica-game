"""Testes F3b: K♠ Véu das Caçadoras e K♣ Pacto de Salomão."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


def _make_troop(state, pid, archetype=TroopArchetype.LIGHT, life=4, house="center"):
    p = state.players[pid - 1]
    p.city.gold = max(p.city.gold, life + 5)
    p.city.magic = max(p.city.magic, 5)
    t = summon_troop(state, pid, archetype, life)
    t.house = house
    return t


def _make_hero(state, pid, house="center"):
    p = state.players[pid - 1]
    p.city.magic = max(p.city.magic, 5)
    h = summon_hero(state, pid)
    h.house = house
    return h


# -------- K♠ --------

def test_k_s_requires_no_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    assert any(a.card_id == "K_S" for a in p.field_artifacts)
    print("OK  - K♠ jogado sem alvo")


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
    assert city2.life == life_before - 1, f"Cidade deveria perder 1, veio {city2.life}"
    print(f"OK  - K♠: Herói atacou Cidade ({life_before} → {city2.life})")


def test_without_k_s_hero_cannot_attack_city():
    state = make_state()
    hero = _make_hero(state, 1, house="city_2")
    end_day(state)

    try:
        resolve_attack(state, Attack(hero.id, "city", "2"))
        raise AssertionError("Deveria bloquear Herói atacando Cidade sem K♠")
    except CombatError as e:
        print(f"OK  - Sem K♠: Herói vs Cidade bloqueado: {e}")


def test_k_s_allows_two_attacks_for_nearby_troop():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")

    hero = _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)

    assert troop.max_attacks_this_night == 2, (
        f"Tropa deveria ter 2 ataques, tem {troop.max_attacks_this_night}"
    )
    print("OK  - K♠: tropa perto de Herói ganha 2 ataques")


def test_k_s_troop_without_hero_nearby_has_one_attack():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")

    hero = _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="city_1")
    end_day(state)

    assert troop.max_attacks_this_night == 1, (
        f"Tropa longe de Herói deveria ter 1 ataque, tem {troop.max_attacks_this_night}"
    )
    print("OK  - K♠: tropa longe de Herói mantém 1 ataque")


def test_two_attacks_actually_happen():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")

    hero = _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)

    troop.house = "city_2"
    city2 = state.players[1].city
    life_before = city2.life

    resolve_attack(state, Attack(troop.id, "city", "2"))
    assert troop.attacks_made_this_night == 1
    resolve_attack(state, Attack(troop.id, "city", "2"))
    assert troop.attacks_made_this_night == 2
    assert city2.life == life_before - 2, f"Esperado {life_before - 2}, veio {city2.life}"
    print("OK  - K♠: 2 ataques funcionaram (2 dano à Cidade)")


def test_k_s_returns_to_shop_at_end_turn():
    """K♠ dura só o turno em que foi usado."""
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    shop_after_play = state.shop.size()
    assert any(a.card_id == "K_S" for a in p.field_artifacts)

    end_turn(state)

    assert not any(a.card_id == "K_S" for a in p.field_artifacts), (
        "K♠ deveria ter saído do campo"
    )
    assert state.shop.size() == shop_after_play + 1, "K♠ deveria ter voltado à Loja"
    print("OK  - K♠ volta à Loja ao fim do turno")


def test_k_s_buffs_clear_at_end_turn():
    """Bônus de K♠ (atacar cidade, 2 ataques) limpam no fim do turno."""
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

    assert hero.hero_can_attack_city is False, "Bônus de K♠ deveria limpar"
    assert troop.max_attacks_this_night == 1, "Bônus de K♠ deveria limpar"
    print("OK  - K♠ buffs limpam no fim do turno")


# -------- K♣ --------

def test_k_c_requires_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_C")
    try:
        play_artifact(state, 1, "K_C")
        raise AssertionError("Deveria exigir alvo")
    except (ActionError, ValueError) as e:
        print(f"OK  - K♣ sem alvo bloqueado: {e}")


def test_k_c_applies_buffs():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_C")

    troop = _make_troop(state, 1, life=4)
    play_artifact(state, 1, "K_C", target_unit_id=troop.id)

    assert troop.double_damage is True, "Deveria ter dobro de dano"
    assert troop.resistance_stacks == 1, f"Deveria ter 1 resistência, tem {troop.resistance_stacks}"
    print("OK  - K♣: alvo ganhou dobro de dano e 1 resistência")


def test_k_c_doubles_damage():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("K_C")
    t1 = _make_troop(state, 1, life=4, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "K_C", target_unit_id=t1.id)

    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t2.is_alive(), f"t2 deveria morrer, veio {t2.life}"
    assert t1.life == 1, f"t1 deveria ficar com 1 (4-3), veio {t1.life}"
    print(f"OK  - K♣: dobro de dano + resistência (t1 vivo com {t1.life})")


def test_k_c_returns_to_shop_on_target_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("K_C")
    t1 = _make_troop(state, 1, life=2, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    play_artifact(state, 1, "K_C", target_unit_id=t1.id)

    shop_before = state.shop.size()
    resolve_attack(state, Attack(t1.id, "unit", t2.id))

    assert not t1.is_alive(), "t1 deveria ter morrido"
    assert not any(a.card_id == "K_C" for a in p.field_artifacts), (
        "K♣ deveria ter saído do campo"
    )
    assert state.shop.size() == shop_before + 1, "K♣ deveria ter voltado à Loja"
    print("OK  - K♣: volta à Loja quando o alvo morre")


def test_resistance_divides_damage():
    state = make_state()
    state.phase = Phase.NIGHT
    t1 = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=5, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=5, house="center")

    t2.resistance_stacks = 1
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert t2.life == 3, f"t2 deveria ficar com 3 (5-2), veio {t2.life}"
    print(f"OK  - Resistência 1 stack: 5 → 2 (t2 com {t2.life})")


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
    print("=== Rodando testes de artifact_effects F3b ===\n")
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