"""Testes F3a: Q-heart e Q-spades."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import play_artifact, summon_troop
from jessica.core.combat import resolve_attack, Attack, CombatError
from jessica.core.turn import end_turn
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


def test_q_h_invulnerable_vs_unit():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    t1 = _make_troop(state, 1, house="center", life=4)
    t2 = _make_troop(state, 2, house="center", life=4)
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert t1.life == 4, f"t1 deveria continuar com 4, veio {t1.life}"
    assert not t2.is_alive(), "t2 deveria ter morrido"
    print("OK  - Qh: invulnerabilidade bloqueia dano recebido")


def test_q_h_blocks_city_attack():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    t1 = _make_troop(state, 1, house="city_2", life=4)
    try:
        resolve_attack(state, Attack(t1.id, "city", "2"))
        raise AssertionError("Deveria ter bloqueado ataque a Cidade")
    except CombatError as e:
        print(f"OK  - Qh: ataque a Cidade bloqueado: {e}")


def test_q_h_blocks_retaliation():
    state = make_state()
    state.phase = Phase.NIGHT
    t1 = _make_troop(state, 1, house="city_2", life=4)
    before = t1.life
    resolve_attack(state, Attack(t1.id, "city", "2"))
    assert t1.life == before - 1, f"Deveria perder 1, veio {before} -> {t1.life}"
    print("OK  - Sem Qh: retaliacao normal (1 de dano)")


def test_q_s_doubles_damage_unit_vs_unit():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_S")
    play_artifact(state, 1, "Q_S")
    t1 = _make_troop(state, 1, archetype=TroopArchetype.LIGHT, life=4, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t1.is_alive(), f"t1 deveria morrer (tomou 6), veio {t1.life}"
    assert not t2.is_alive(), f"t2 deveria morrer (tomou 8), veio {t2.life}"
    print("OK  - Qs: dobro de dano (t1 4x2=8 mata t2 com 6)")


def test_no_q_s_does_not_kill():
    state = make_state()
    state.phase = Phase.NIGHT
    t1 = _make_troop(state, 1, archetype=TroopArchetype.LIGHT, life=4, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t1.is_alive(), f"t1 deveria morrer, veio {t1.life}"
    assert t2.is_alive(), "t2 deveria sobreviver sem Qs"
    assert t2.life == 2, f"t2 deveria ficar com 2, veio {t2.life}"
    print("OK  - Sem Qs: mesmo ataque nao mata t2 (fica com 2)")


def test_q_s_doubles_damage_to_city():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_S")
    play_artifact(state, 1, "Q_S")
    t1 = _make_troop(state, 1, house="city_2", life=4)
    city2 = state.players[1].city
    life_before = city2.life
    resolve_attack(state, Attack(t1.id, "city", "2"))
    assert city2.life == life_before - 2, f"Esperado {life_before - 2}, veio {city2.life}"
    print(f"OK  - Qs: dobro contra Cidade ({life_before} -> {city2.life})")


def test_q_h_and_q_s_return_to_shop_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    shop_after_play = state.shop.size()
    end_turn(state)
    assert not any(a.card_id == "Q_H" for a in p1.field_artifacts)
    assert state.shop.size() == shop_after_play + 1
    print("OK  - Qh volta a Loja ao fim do turno")


def test_q_s_flag_clears_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("Q_S")
    play_artifact(state, 1, "Q_S")
    assert p1.double_damage_until_end_night is True
    end_turn(state)
    assert p1.double_damage_until_end_night is False
    print("OK  - Qs flag limpa ao fim do turno")


def test_q_h_flags_clear_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    assert p1.invulnerable_until_end_turn is True
    end_turn(state)
    assert p1.invulnerable_until_end_turn is False
    print("OK  - Qh flags limpam ao fim do turno")


def run_all():
    tests = [
        test_q_h_invulnerable_vs_unit,
        test_q_h_blocks_city_attack,
        test_q_h_blocks_retaliation,
        test_q_s_doubles_damage_unit_vs_unit,
        test_no_q_s_does_not_kill,
        test_q_s_doubles_damage_to_city,
        test_q_h_and_q_s_return_to_shop_at_end_turn,
        test_q_s_flag_clears_at_end_turn,
        test_q_h_flags_clear_at_end_turn,
    ]
    print("=== Testes F3a ===\n")
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
