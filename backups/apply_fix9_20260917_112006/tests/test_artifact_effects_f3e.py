"""Testes F3e: J-clubs e Q-clubs."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, summon_troop, ActionError,
)
from jessica.core.combat import resolve_attack, Attack
from jessica.core.turn import day_order, end_turn
from jessica.core.constants import TroopArchetype, Phase, CENTER


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
    return t


def test_j_c_requires_target_player():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_C")
    try:
        play_artifact(state, 1, "J_C")
        raise AssertionError("Deveria exigir alvo")
    except ActionError as e:
        print(f"OK  - Jc sem alvo bloqueado: {e}")


def test_j_c_cannot_target_self():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_C")
    try:
        play_artifact(state, 1, "J_C", choice={"target_player_id": 1})
        raise AssertionError("Deveria bloquear auto-alvo")
    except ValueError as e:
        print(f"OK  - Jc nao pode ter voce mesmo: {e}")


def test_j_c_marks_skip_for_target_who_has_not_played():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")
    p1.has_played_day_this_turn = True
    p2.has_played_day_this_turn = False
    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})
    assert p2.skip_day_turn == state.turn
    assert p2.skip_night_turn == state.turn
    print(f"OK  - Jc: J2 (nao jogou) pula Dia e Noite do turno {state.turn}")


def test_j_c_marks_skip_for_target_who_has_played():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")
    p1.has_played_day_this_turn = True
    p2.has_played_day_this_turn = True
    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})
    assert p2.skip_night_turn == state.turn
    assert p2.skip_day_turn == state.turn + 1
    print(f"OK  - Jc: J2 (ja jogou) pula Noite atual + Dia {state.turn + 1}")


def test_j_c_day_order_skips_target():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")
    p2.has_played_day_this_turn = False
    p1.has_played_day_this_turn = True
    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})
    order = day_order(state)
    assert 2 not in order, f"J2 deveria estar pulado: {order}"
    print(f"OK  - day_order omite J2 (pulado): {order}")


def test_q_c_requires_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    try:
        play_artifact(state, 1, "Q_C")
        raise AssertionError("Deveria exigir alvo")
    except ActionError as e:
        print(f"OK  - Qc sem alvo bloqueado: {e}")


def test_q_c_cannot_target_own_unit():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    own = _make_troop(state, 1, life=4)
    try:
        play_artifact(state, 1, "Q_C", choice={"unit_id": own.id})
        raise AssertionError("Deveria bloquear unidade propria")
    except ValueError as e:
        print(f"OK  - Qc nao pode controlar unidade propria: {e}")


def test_q_c_takes_control():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=4)
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    p1_ids = {u.id for u in p1.units}
    p2_ids = {u.id for u in p2.units}
    assert enemy.id in p1_ids
    assert enemy.id not in p2_ids
    assert enemy.original_owner_id == 2
    assert enemy.owner_id == 1
    print(f"OK  - Qc: {enemy.id} passou para J1")


def test_q_c_returns_control_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=4)
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    end_turn(state)
    p1_ids = {u.id for u in p1.units}
    p2_ids = {u.id for u in p2.units}
    assert enemy.id not in p1_ids
    assert enemy.id in p2_ids
    assert enemy.owner_id == 2
    print("OK  - Qc: unidade volta ao dono no fim do turno")


def test_q_c_can_attack_original_owner():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=4, house="center")
    own = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    resolve_attack(state, Attack(enemy.id, "unit", own.id))
    assert not enemy.is_alive()
    print("OK  - Qc: controlada pode atacar unidade do dono original")


def test_q_c_controlled_dies_permanently():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=2, house="center")
    own = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    resolve_attack(state, Attack(enemy.id, "unit", own.id))
    p1_ids = {u.id for u in p1.units}
    p2_ids = {u.id for u in p2.units}
    assert enemy.id not in p1_ids
    assert enemy.id not in p2_ids
    print("OK  - Qc: se controlada morre, morre")


def run_all():
    tests = [
        test_j_c_requires_target_player,
        test_j_c_cannot_target_self,
        test_j_c_marks_skip_for_target_who_has_not_played,
        test_j_c_marks_skip_for_target_who_has_played,
        test_j_c_day_order_skips_target,
        test_q_c_requires_target,
        test_q_c_cannot_target_own_unit,
        test_q_c_takes_control,
        test_q_c_returns_control_at_end_turn,
        test_q_c_can_attack_original_owner,
        test_q_c_controlled_dies_permanently,
    ]
    print("=== Testes F3e ===\n")
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
