"""Testes F3d: J-diamonds e Q-diamonds (novo fluxo)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, summon_troop, resolve_pending_artifact_choice, ActionError,
)
from jessica.core.combat import resolve_attack, Attack
from jessica.core.turn import end_day, end_turn, start_turn, start_player_day
from jessica.core.constants import TroopArchetype, Phase, CENTER


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["Miyamoto Musashi"],
            "anoes": ["Barbadourada"],
            "orcs": ["Arken"],
            "fadas": ["Ainai"],
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


def test_j_d_schedules_effect():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    assert len(state.pending_effects) == 1
    e = state.pending_effects[0]
    assert e["kind"] == "J_D"
    assert e["player_id"] == 1
    assert e["due_turn"] == state.turn + 3
    print(f"OK  - J-diamonds agendado para turno {e[\'due_turn\']}")


def test_j_d_triggers_pending_choice():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    state.turn = 4
    start_player_day(state, 1)
    assert p.pending_artifact_choice is not None
    assert p.pending_artifact_choice["kind"] == "J_D"
    assert len(p.pending_artifact_choice["cards"]) == 3
    print(f"OK  - J-diamonds dispara escolha: {p.pending_artifact_choice[\'cards\']}")


def test_j_d_resolution_keeps_2_of_3():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    state.turn = 4
    start_player_day(state, 1)
    cards = p.pending_artifact_choice["cards"]
    kept = cards[:2]
    shop_before = state.shop.size()
    resolve_pending_artifact_choice(state, 1, kept_cards=kept)
    assert p.pending_artifact_choice is None
    for c in kept:
        assert c in p.hand
    assert state.shop.size() == shop_before + 2
    assert not any(a.card_id == "J_D" for a in p.field_artifacts)
    print("OK  - J-diamonds resolveu: 2 pra mao, 1 + J-diamonds pra Loja")


def test_j_d_resolution_requires_pick_2():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    state.turn = 4
    start_player_day(state, 1)
    cards = p.pending_artifact_choice["cards"]
    try:
        resolve_pending_artifact_choice(state, 1, kept_cards=cards[:1])
        raise AssertionError("Deveria exigir 2")
    except ActionError as e:
        print(f"OK  - J-diamonds exige 2: {e}")


def test_j_d_persists_in_pending_effects():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    from jessica.core.serialize import state_to_dict, state_from_dict
    s2 = state_from_dict(state_to_dict(state))
    assert len(s2.pending_effects) == 1
    print("OK  - J-diamonds pendente sobrevive a serializacao")


def test_q_d_requires_unit():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_D")
    try:
        play_artifact(state, 1, "Q_D")
        raise AssertionError("Deveria exigir unit_id")
    except ActionError as e:
        print(f"OK  - Q-diamonds sem escolha bloqueado: {e}")


def test_q_d_marks_target_only():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6)
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    qd = next(a for a in p.field_artifacts if a.card_id == "Q_D")
    assert qd.extra["target_unit_id"] == target.id
    assert "resource" not in qd.extra
    print("OK  - Q-diamonds marcou alvo (sem recurso)")


def test_q_d_creates_pending_choice_on_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    assert not target.is_alive()
    assert p1.pending_artifact_choice is not None
    assert p1.pending_artifact_choice["kind"] == "Q_D"
    assert p1.pending_artifact_choice["dead_unit_max_life"] == 6
    assert p1.pending_artifact_choice["killer_id"] == 3
    print("OK  - Q-diamonds gera escolha pendente na morte")


def test_q_d_gold_reward_to_owner_and_killer():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    gold1_before = state.players[0].city.gold
    gold3_before = state.players[2].city.gold
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="gold")
    assert state.players[0].city.gold == gold1_before + 6
    assert state.players[2].city.gold == gold3_before + 6
    print("OK  - Q-diamonds: +6 Ouro pro dono e pro matador")


def test_q_d_magic_reward():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    m1_before = state.players[0].city.magic
    m3_before = state.players[2].city.magic
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="magic")
    assert state.players[0].city.magic == m1_before + 6
    assert state.players[2].city.magic == m3_before + 6
    print("OK  - Q-diamonds: +6 Magia pro dono e pro matador")


def test_q_d_no_double_when_owner_is_killer():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 1, archetype=TroopArchetype.LIGHT, life=4, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    gold1_before = state.players[0].city.gold
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="gold")
    assert state.players[0].city.gold == gold1_before + 4
    print("OK  - Q-diamonds: owner ganha 1 vez")


def test_q_d_returns_to_shop_after_resolution():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    shop_before = state.shop.size()
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="gold")
    assert not any(a.card_id == "Q_D" for a in p1.field_artifacts)
    assert state.shop.size() == shop_before + 1
    print("OK  - Q-diamonds volta a Loja apos resolucao")


def test_q_d_no_reward_if_target_survives():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.LIGHT, life=2, house="center")
    gold1_before = state.players[0].city.gold
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    assert target.is_alive()
    assert p1.pending_artifact_choice is None
    assert state.players[0].city.gold == gold1_before
    assert any(a.card_id == "Q_D" for a in p1.field_artifacts)
    print("OK  - Q-diamonds sem recompensa se alvo sobrevive")


def run_all():
    tests = [
        test_j_d_schedules_effect,
        test_j_d_triggers_pending_choice,
        test_j_d_resolution_keeps_2_of_3,
        test_j_d_resolution_requires_pick_2,
        test_j_d_persists_in_pending_effects,
        test_q_d_requires_unit,
        test_q_d_marks_target_only,
        test_q_d_creates_pending_choice_on_death,
        test_q_d_gold_reward_to_owner_and_killer,
        test_q_d_magic_reward,
        test_q_d_no_double_when_owner_is_killer,
        test_q_d_returns_to_shop_after_resolution,
        test_q_d_no_reward_if_target_survives,
    ]
    print("=== Testes artifact_effects F3d ===\n")
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
