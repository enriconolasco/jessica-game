"""Prova mínima dos contratos headless v0.1."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.headless import (
    ACTION_VERSION, apply_action, legal_actions, view_for_player,
)
from jessica.core.serialize import state_to_dict
from jessica.core.setup import run_setup


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"],
            "anoes": ["ori"],
            "orcs": ["arken"],
            "fadas": ["ainai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"},
        },
        seed=20260922,
        turn_order=[1, 2, 3, 4],
    )
    return state


def test_legal_actions_enumerates_collect_splits_without_mutation():
    state = make_state()
    before = state_to_dict(state)
    actions = legal_actions(state, 1)
    assert [a["params"] for a in actions] == [
        {"gold": 0, "magic": 2},
        {"gold": 1, "magic": 1},
        {"gold": 2, "magic": 0},
    ]
    assert state_to_dict(state) == before


def test_apply_action_uses_core_and_emits_public_event():
    state = make_state()
    action = {
        "version": ACTION_VERSION,
        "type": "collect_resources",
        "player_id": 1,
        "params": {"gold": 1, "magic": 1},
    }
    result = apply_action(state, action)
    assert result["success"] is True
    assert result["error"] is None
    assert result["events"][0]["type"] == "resources_collected"
    assert result["events"][0]["visibility"]["kind"] == "public"
    assert state.players[0].city.gold == 1
    assert state.players[0].city.magic == 1
    assert state.players[0].has_collected_this_turn
    assert legal_actions(state, 1) == []


def test_rejected_action_is_atomic():
    state = make_state()
    before = state_to_dict(state)
    result = apply_action(state, {
        "version": ACTION_VERSION,
        "type": "collect_resources",
        "player_id": 1,
        "params": {"gold": 3, "magic": -1},
    })
    assert result["success"] is False
    assert result["error"]["code"] == "not_legal"
    assert state_to_dict(state) == before


def test_same_state_and_action_are_deterministic():
    state_a = make_state()
    state_b = make_state()
    action = legal_actions(state_a, 1)[1]
    assert apply_action(state_a, action) == apply_action(state_b, action)
    assert state_to_dict(state_a) == state_to_dict(state_b)


def test_player_view_hides_opponent_hand_shop_order_and_rng():
    state = make_state()
    state.players[0].hand = ["A_H"]
    state.players[1].hand = ["SECRET_OPPONENT_CARD"]
    state.players[1].pending_artifact_choice = {"secret": "HIDDEN_CHOICE"}
    view = view_for_player(state, 1)
    encoded = json.dumps(view, sort_keys=True)
    assert view["self"]["hand"] == ["A_H"]
    assert view["players"][1]["hand_count"] == 1
    assert "SECRET_OPPONENT_CARD" not in encoded
    assert "HIDDEN_CHOICE" not in encoded
    assert "deck" not in view["shop"]
    assert "rng" not in view


def test_terminal_collection_uses_engine_port():
    from jessica import main as main_mod

    state = make_state()
    calls = []
    original_apply = main_mod.apply_engine_action
    original_ask = main_mod.IntPrompt.ask

    def tracked_apply(current_state, action):
        calls.append(action)
        return original_apply(current_state, action)

    try:
        main_mod.apply_engine_action = tracked_apply
        main_mod.IntPrompt.ask = lambda *args, **kwargs: 1
        main_mod._do_action(state, 1, "1")
    finally:
        main_mod.apply_engine_action = original_apply
        main_mod.IntPrompt.ask = original_ask

    assert calls[0]["type"] == "collect_resources"
    assert calls[0]["params"] == {"gold": 1, "magic": 1}
    assert state.players[0].city.gold == 1
    assert state.players[0].city.magic == 1


def run_all():
    tests = [
        test_legal_actions_enumerates_collect_splits_without_mutation,
        test_apply_action_uses_core_and_emits_public_event,
        test_rejected_action_is_atomic,
        test_same_state_and_action_are_deterministic,
        test_player_view_hides_opponent_hand_shop_order_and_rng,
        test_terminal_collection_uses_engine_port,
    ]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"FALHOU - {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n=== {passed} passaram, {failed} falharam ===")


if __name__ == "__main__":
    run_all()
