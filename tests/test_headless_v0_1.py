"""Prova mínima dos contratos headless v0.1."""
import json
import os
import sys
import tempfile
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.headless import (
    ACTION_VERSION, apply_action, apply_event_to_view, legal_actions,
    view_for_player,
)
from jessica.core.actions import (build_monument, collect_resources, move_unit,
                                  raise_city_life, summon_troop)
from jessica.core.constants import TroopArchetype
from jessica.core.serialize import load_from_file, save_to_file, state_to_dict
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


def _state_with_movable_unit():
    state = make_state()
    state.players[0].city.gold = state.players[0].city.magic = 20
    unit = summon_troop(state, 1, TroopArchetype.LIGHT, 1, "city_1")
    unit.statuses.pop("summoned_turn", None)
    unit.moves_this_turn = 0
    unit.has_moved_this_turn = False
    return state, unit


def test_move_action_matches_core_and_projects_event():
    state, unit = _state_with_movable_unit()
    direct = deepcopy(state)
    before_view = view_for_player(state, 2)
    action = next(a for a in legal_actions(state, 1)
                  if a["type"] == "move_unit" and a["params"]["unit_id"] == unit.id)
    result = apply_action(state, action)
    move_unit(direct, 1, unit.id, "center")
    assert result["success"] is True
    assert result["events"][0]["type"] == "unit_moved"
    assert state_to_dict(state) == state_to_dict(direct)
    projected = apply_event_to_view(before_view, result["events"][0])
    viewed = next(u for u in projected["board"]["units"] if u["id"] == unit.id)
    assert viewed["house"] == "center"


def test_legal_actions_enumerates_collect_splits_without_mutation():
    state = make_state()
    before = state_to_dict(state)
    actions = legal_actions(state, 1)
    assert [a["params"] for a in actions if a["type"] == "collect_resources"] == [
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
    assert not any(a["type"] == "collect_resources" for a in legal_actions(state, 1))


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
    assert json.loads(json.dumps(view)) == view


def test_serialized_action_keeps_meaning():
    state_a = make_state()
    state_b = make_state()
    action = legal_actions(state_a, 1)[2]
    restored = json.loads(json.dumps(action))
    assert apply_action(state_a, action) == apply_action(state_b, restored)
    assert state_to_dict(state_a) == state_to_dict(state_b)


def test_event_reconstructs_resource_change_in_player_view():
    state = make_state()
    before = view_for_player(state, 2)
    result = apply_action(state, legal_actions(state, 1)[1])
    projected = apply_event_to_view(before, result["events"][0])
    after = view_for_player(state, 2)
    assert projected["players"] == after["players"]
    assert projected["events"] == result["events"]


def test_old_and_new_collection_flows_match():
    old_state = make_state()
    new_state = make_state()
    collect_resources(old_state, 1, 1, 1)
    result = apply_action(new_state, legal_actions(new_state, 1)[1])
    assert result["success"]
    assert state_to_dict(old_state) == state_to_dict(new_state)


def test_save_load_after_headless_action():
    state = make_state()
    apply_action(state, legal_actions(state, 1)[1])
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "headless-save.json")
        save_to_file(state, path)
        restored = load_from_file(path)
    assert state_to_dict(restored) == state_to_dict(state)
    assert view_for_player(restored, 1) == view_for_player(state, 1)


def test_terminal_collection_uses_engine_port():
    from jessica import main as main_mod

    state = make_state()
    calls = []
    original_apply = main_mod.apply_engine_action
    original_pick = main_mod.pick_index

    def tracked_apply(current_state, action):
        calls.append(action)
        return original_apply(current_state, action)

    try:
        main_mod.apply_engine_action = tracked_apply
        main_mod.pick_index = lambda *args, **kwargs: 1
        main_mod._do_action(state, 1, "1")
    finally:
        main_mod.apply_engine_action = original_apply
        main_mod.pick_index = original_pick

    assert calls[0]["type"] == "collect_resources"
    assert calls[0]["params"] == {"gold": 1, "magic": 1}
    assert state.players[0].city.gold == 1
    assert state.players[0].city.magic == 1


def test_economic_actions_emit_events_and_match_direct_core():
    direct = make_state()
    port = make_state()
    for state in (direct, port):
        state.players[0].city.gold = 20
    raise_city_life(direct, 1, 2)
    action = next(a for a in legal_actions(port, 1)
                  if a["type"] == "raise_city_life" and a["params"] == {"times": 2})
    result = apply_action(port, action)
    assert result["success"] and result["events"][0]["type"] == "city_life_raised"
    assert state_to_dict(direct) == state_to_dict(port)

    direct.players[0].city.life = direct.players[0].city.life_max
    port.players[0].city.life = port.players[0].city.life_max
    build_monument(direct, 1)
    action = next(a for a in legal_actions(port, 1) if a["type"] == "build_monument")
    result = apply_action(port, action)
    assert result["success"] and result["events"][0]["type"] == "monument_built"
    assert state_to_dict(direct) == state_to_dict(port)


def test_economic_events_reconstruct_view_and_rejection_is_atomic():
    state = make_state()
    state.players[0].city.gold = 10
    before_view = view_for_player(state, 2)
    action = next(a for a in legal_actions(state, 1)
                  if a["type"] == "raise_city_life" and a["params"] == {"times": 1})
    result = apply_action(state, action)
    projected = apply_event_to_view(before_view, result["events"][0])
    assert projected["players"] == view_for_player(state, 2)["players"]

    before = state_to_dict(state)
    rejected = apply_action(state, {"version": ACTION_VERSION,
                                    "type": "raise_city_life", "player_id": 1,
                                    "params": {"times": 99}})
    assert not rejected["success"] and state_to_dict(state) == before


def test_terminal_economic_actions_use_engine_port():
    from jessica import main as main_mod
    state = make_state()
    state.players[0].city.gold = 30
    calls = []
    original_apply = main_mod.apply_engine_action
    original_ask = main_mod.IntPrompt.ask
    try:
        main_mod.apply_engine_action = lambda current, action: (
            calls.append(action) or original_apply(current, action))
        main_mod.IntPrompt.ask = lambda *args, **kwargs: 1
        main_mod._do_action(state, 1, "2")
        state.players[0].city.life = state.players[0].city.life_max
        main_mod._do_action(state, 1, "6")
    finally:
        main_mod.apply_engine_action = original_apply
        main_mod.IntPrompt.ask = original_ask
    assert [a["type"] for a in calls] == ["raise_city_life", "build_monument"]


def test_summon_actions_match_core_and_project_event():
    direct = make_state()
    port = make_state()
    for state in (direct, port):
        state.players[0].city.gold = 20
        state.players[0].city.magic = 20
    from jessica.core.actions import summon_troop
    from jessica.core.constants import TroopArchetype
    summon_troop(direct, 1, TroopArchetype.LIGHT, 3)
    action = next(a for a in legal_actions(port, 1)
                  if a["type"] == "summon_troop"
                  and a["params"] == {"archetype": "light", "life": 3,
                                      "house": "city_1"})
    before = view_for_player(port, 2)
    result = apply_action(port, action)
    assert result["success"] and result["events"][0]["type"] == "unit_summoned"
    assert state_to_dict(direct) == state_to_dict(port)
    projected = apply_event_to_view(before, result["events"][0])
    assert projected["players"] == view_for_player(port, 2)["players"]
    assert projected["board"] == view_for_player(port, 2)["board"]


def test_terminal_summons_use_engine_port():
    from jessica import main as main_mod
    state = make_state()
    p = state.players[0]
    p.city.gold = p.city.magic = 20
    calls = []
    original_apply = main_mod.apply_engine_action
    original_pick = main_mod.pick_index
    original_ask = main_mod.IntPrompt.ask
    try:
        main_mod.apply_engine_action = lambda current, action: (
            calls.append(action) or original_apply(current, action))
        main_mod.pick_index = lambda *args, **kwargs: 0
        main_mod.IntPrompt.ask = lambda *args, **kwargs: 1
        main_mod._do_action(state, 1, "3")
        main_mod._do_action(state, 1, "4")
    finally:
        main_mod.apply_engine_action = original_apply
        main_mod.pick_index = original_pick
        main_mod.IntPrompt.ask = original_ask
    assert [a["type"] for a in calls] == ["summon_troop", "summon_hero"]


def test_end_turn_advances_active_player_and_enters_night_after_last():
    state = make_state()
    state.active_player_id = 1
    for expected in (2, 3, 4, None):
        action = next(a for a in legal_actions(state, state.active_player_id)
                      if a["type"] == "end_turn")
        result = apply_action(state, action)
        assert result["success"] is True
        assert result["events"][0]["type"] == "player_turn_ended"
        assert state.active_player_id == expected
    assert state.phase.value == "night"


def run_all():
    tests = [
        test_legal_actions_enumerates_collect_splits_without_mutation,
        test_apply_action_uses_core_and_emits_public_event,
        test_rejected_action_is_atomic,
        test_same_state_and_action_are_deterministic,
        test_player_view_hides_opponent_hand_shop_order_and_rng,
        test_serialized_action_keeps_meaning,
        test_event_reconstructs_resource_change_in_player_view,
        test_old_and_new_collection_flows_match,
        test_save_load_after_headless_action,
        test_terminal_collection_uses_engine_port,
        test_economic_actions_emit_events_and_match_direct_core,
        test_economic_events_reconstruct_view_and_rejection_is_atomic,
        test_terminal_economic_actions_use_engine_port,
        test_summon_actions_match_core_and_project_event,
        test_terminal_summons_use_engine_port,
        test_move_action_matches_core_and_projects_event,
        test_end_turn_advances_active_player_and_enters_night_after_last,
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
