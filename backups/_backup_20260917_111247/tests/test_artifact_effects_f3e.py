"""Testes F3e: J♣ Travessura Gnômica e Q♣ Maldição das Almas Acorrentadas."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, summon_troop, ActionError,
)
from jessica.core.combat import resolve_attack, Attack
from jessica.core.turn import start_turn, start_player_day, day_order, end_day, end_turn
from jessica.core.constants import TroopArchetype, Phase, CENTER


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


# -------- J♣ --------

def test_j_c_requires_target_player():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_C")
    try:
        play_artifact(state, 1, "J_C")
        raise AssertionError("Deveria exigir alvo")
    except ActionError as e:
        print(f"OK  - J♣ sem alvo bloqueado: {e}")


def test_j_c_cannot_target_self():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_C")
    try:
        play_artifact(state, 1, "J_C", choice={"target_player_id": 1})
        raise AssertionError("Deveria bloquear auto-alvo")
    except ValueError as e:
        print(f"OK  - J♣ não pode ter você mesmo: {e}")


def test_j_c_marks_skip_for_target_who_has_not_played():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")

    p1.has_played_day_this_turn = True
    p2.has_played_day_this_turn = False

    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})

    assert p2.skip_day_turn == state.turn, f"skip_day {p2.skip_day_turn}"
    assert p2.skip_night_turn == state.turn
    print(f"OK  - J♣: J2 (não jogou) pula Dia e Noite do turno {state.turn}")


def test_j_c_marks_skip_for_target_who_has_played():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")

    p1.has_played_day_this_turn = True
    p2.has_played_day_this_turn = True

    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})

    assert p2.skip_night_turn == state.turn
    assert p2.skip_day_turn == state.turn + 1, f"skip_day {p2.skip_day_turn}"
    print(f"OK  - J♣: J2 (já jogou) pula Noite atual + Dia {state.turn + 1}")


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


# -------- Q♣ --------

def test_q_c_requires_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    try:
        play_artifact(state, 1, "Q_C")
        raise AssertionError("Deveria exigir alvo")
    except ActionError as e:
        print(f"OK  - Q♣ sem alvo bloqueado: {e}")


def test_q_c_cannot_target_own_unit():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    own = _make_troop(state, 1, life=4)

    try:
        play_artifact(state, 1, "Q_C", choice={"unit_id": own.id})
        raise AssertionError("Deveria bloquear unidade própria")
    except ValueError as e:
        print(f"OK  - Q♣ não pode controlar unidade própria: {e}")


def test_q_c_takes_control():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("Q_C")

    enemy = _make_troop(state, 2, life=4)
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})

    p1_ids = {u.id for u in p1.units}
    p2_ids = {u.id for u in p2.units}
    assert enemy.id in p1_ids, "Unidade deveria estar com o controlador"
    assert enemy.id not in p2_ids, "Unidade não deveria estar com o dono original"
    assert enemy.original_owner_id == 2
    assert enemy.owner_id == 1
    print(f"OK  - Q♣: {enemy.id} passou para J1")


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
    assert enemy.id not in p1_ids, "Unidade deveria ter voltado"
    assert enemy.id in p2_ids, "Unidade deveria estar com o dono original"
    assert enemy.owner_id == 2
    assert enemy.original_owner_id is None
    print("OK  - Q♣: unidade volta ao dono no fim do turno")


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
    print("OK  - Q♣: controlada pode atacar unidade do dono original")


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
    assert enemy.id not in p2_ids, "Unidade controlada morreu, não volta"
    print("OK  - Q♣: se controlada morre, morre")


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
    print("=== Rodando testes de artifact_effects F3e ===\n")
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