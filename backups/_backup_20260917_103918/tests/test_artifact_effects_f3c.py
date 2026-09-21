"""Testes F3c: J-heart e J-spades."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import play_artifact, summon_troop, ActionError
from jessica.core.combat import resolve_attack, Attack
from jessica.core.turn import end_turn
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero, Troop


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["Miyamoto Musashi", "Besouro Mangangá", "Iúna"],
            "anoes": ["Barbadourada"], "orcs": ["Arken"], "fadas": ["Ainai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "Miyamoto Musashi"},
            2: {"povo": "anoes", "heroi": "Barbadourada"},
            3: {"povo": "orcs", "heroi": "Arken"},
            4: {"povo": "fadas", "heroi": "Ainai"},
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


def test_j_h_requires_hero_id():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_H")
    try:
        play_artifact(state, 1, "J_H")
        raise AssertionError("Deveria exigir hero_id")
    except (ActionError, ValueError) as e:
        print(f"OK  - J-heart sem escolha bloqueado: {e}")


def test_j_h_cannot_summon_same_hero_as_setup():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_H")
    try:
        play_artifact(state, 1, "J_H", choice={"hero_id": "miyamoto"})
        raise AssertionError("Deveria bloquear mesmo heroi do setup")
    except ValueError as e:
        print(f"OK  - J-heart bloqueia heroi do setup: {e}")


def test_j_h_summons_extra_hero():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_H")
    play_artifact(state, 1, "J_H", choice={"hero_id": "iuna"})
    extras = [u for u in p.units if isinstance(u, Hero) and u.hero_id == "iuna"]
    assert len(extras) == 1, f"Esperado 1 heroi iuna, veio {len(extras)}"
    assert extras[0].life == 2, f"Iuna tem 2 de vida, veio {extras[0].life}"
    assert extras[0].house == "city_1"
    assert any(a.card_id == "J_H" for a in p.field_artifacts)
    print("OK  - J-heart invocou Iuna (heroi extra)")


def test_j_h_returns_to_shop_on_hero_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("J_H")
    play_artifact(state, 1, "J_H", choice={"hero_id": "iuna"})
    hero = next(u for u in p.units if isinstance(u, Hero) and u.hero_id == "iuna")
    hero.house = "center"
    enemy = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    shop_before = state.shop.size()
    resolve_attack(state, Attack(enemy.id, "unit", hero.id))
    assert not hero.is_alive(), "Iuna deveria ter morrido"
    assert not any(a.card_id == "J_H" for a in p.field_artifacts), "J-heart deveria ter saido"
    assert state.shop.size() == shop_before + 1
    print("OK  - J-heart volta a Loja quando o heroi morre")


def test_j_h_allows_principal_hero_to_coexist():
    state = make_state()
    p = state.players[0]
    p.city.magic = 5
    from jessica.core.actions import summon_hero
    summon_hero(state, 1)
    p.hand.append("J_H")
    play_artifact(state, 1, "J_H", choice={"hero_id": "iuna"})
    heroes_ = [u for u in p.units if isinstance(u, Hero)]
    assert len(heroes_) == 2, f"Esperado 2 herois, veio {len(heroes_)}"
    print("OK  - J-heart coexiste com o heroi principal")


def test_j_s_requires_house():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    try:
        play_artifact(state, 1, "J_S")
        raise AssertionError("Deveria exigir casa")
    except (ActionError, ValueError) as e:
        print(f"OK  - J-spades sem escolha bloqueado: {e}")


def test_j_s_summons_special_troop_in_center():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": CENTER})
    specials = [u for u in p.units
                if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL]
    assert len(specials) == 1
    t = specials[0]
    assert t.life == 5
    assert t.house == CENTER
    print("OK  - J-spades invocou tropa 5 no Centro")


def test_j_s_summons_in_enemy_city():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": "city_2"})
    t = next(u for u in p.units
             if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL)
    assert t.house == "city_2"
    print("OK  - J-spades invocou tropa na Cidade do J2")


def test_j_s_invalid_house():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    try:
        play_artifact(state, 1, "J_S", choice={"house": "marte"})
        raise AssertionError("Deveria bloquear casa invalida")
    except ValueError as e:
        print(f"OK  - J-spades casa invalida bloqueada: {e}")


def test_j_s_returns_to_shop_on_troop_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": CENTER})
    t = next(u for u in p.units
             if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL)
    enemy = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    shop_before = state.shop.size()
    resolve_attack(state, Attack(enemy.id, "unit", t.id))
    assert not t.is_alive(), "Tropa de 5 deveria ter morrido"
    assert not any(a.card_id == "J_S" for a in p.field_artifacts)
    assert state.shop.size() == shop_before + 1
    print("OK  - J-spades volta a Loja quando a tropa morre")


def test_j_s_only_one_special_troop_at_a_time():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": CENTER})
    p.hand.append("J_S")
    try:
        play_artifact(state, 1, "J_S", choice={"house": CENTER})
        raise AssertionError("Deveria bloquear segunda tropa special")
    except ValueError as e:
        print(f"OK  - J-spades so 1 tropa special viva: {e}")


def run_all():
    tests = [
        test_j_h_requires_hero_id,
        test_j_h_cannot_summon_same_hero_as_setup,
        test_j_h_summons_extra_hero,
        test_j_h_returns_to_shop_on_hero_death,
        test_j_h_allows_principal_hero_to_coexist,
        test_j_s_requires_house,
        test_j_s_summons_special_troop_in_center,
        test_j_s_summons_in_enemy_city,
        test_j_s_invalid_house,
        test_j_s_returns_to_shop_on_troop_death,
        test_j_s_only_one_special_troop_at_a_time,
    ]
    print("=== Testes artifact_effects F3c ===\n")
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
