import os, sys
from copy import deepcopy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica.core import combat, night_actions
from jessica.core.headless import apply_action, legal_actions, view_for_player
from jessica.core.models import Troop, Hero
from jessica.core.serialize import state_to_dict, state_from_dict
from jessica.core.constants import Phase
from test_night_web import night


def test_armor_two_decisions_atomic_save_and_core_parity():
    state = night()
    for pid, life in ((1, 4), (2, 3)):
        p = state.players[pid - 1]
        p.units = [Troop(id=f"u{pid}", owner_id=pid, house="center", life=life, life_max=life)]
        p.armor_active_until_turn = state.turn
        p.city.gold = 8
    night_actions.prepare(state)
    original = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
    before = state_to_dict(state)
    direct = deepcopy(state)
    result = apply_action(state, original)
    assert result["success"] and state.active_player_id == 2
    assert state.players[0].units[0].life == 4 and state.players[1].units[0].life == 3
    assert state.rng.to_dict() == before["rng"]
    assert not view_for_player(state, 1)["self"]["armor_reaction"]
    assert view_for_player(state, 2)["self"]["armor_reaction"]["max_gold"] == 4
    pending = state_to_dict(state)
    decision = legal_actions(state, 2)[0]
    decision["params"] = {"gold": 2}
    assert not apply_action(state, dict(decision, player_id=1))["success"]
    assert state_to_dict(state) == pending
    restored = state_from_dict(pending)
    assert apply_action(state, decision) == apply_action(restored, decision)
    assert view_for_player(state, 1)["players"][1]["city"]["gold"] == 6
    assert state.players[1].city.gold == 8
    assert state.active_player_id == 1 and state.web_reaction
    second = legal_actions(state, 1)[0]
    second["params"] = {"gold": 0}
    assert apply_action(state, second) == apply_action(restored, second)
    payments = iter((2, 0))
    with combat.armor_policy(lambda player, damage: next(payments)):
        combat.resolve_attack(direct, combat.Attack(**original["params"]))
    night_actions.advance(direct)
    assert not state.web_reaction
    assert state_to_dict(state) == state_to_dict(direct) == state_to_dict(restored)


def test_armor_day_attack_can_decline_and_reject_bool():
    state = night()
    state.phase = Phase.DAY
    state.active_player_id = 1
    state.players[0].units = [Hero(id="m", owner_id=1, house="center", life=4, life_max=4, hero_id="miyamoto")]
    state.players[1].units = [Troop(id="t", owner_id=2, house="center", life=4, life_max=4)]
    state.players[1].armor_active_until_turn = state.turn
    state.players[1].city.gold = 4
    attack = next(a for a in legal_actions(state, 1) if a["type"] == "day_attack")
    assert apply_action(state, attack)["success"]
    choice = legal_actions(state, 2)[0]
    before = state_to_dict(state)
    assert not apply_action(state, dict(choice, params={"gold": True}))["success"]
    assert state_to_dict(state) == before
    assert apply_action(state, choice)["success"]
    assert state.players[1].city.gold == 4 and not state.web_reaction


def test_queries_never_call_terminal_prompt_or_mutate():
    state = night()
    for pid in (1, 2):
        p = state.players[pid - 1]
        p.units = [Troop(id=f"u{pid}", owner_id=pid, house="center", life=4, life_max=4)]
        p.armor_active_until_turn = state.turn
        p.city.gold = 5
    night_actions.prepare(state)
    before = state_to_dict(state)
    called = []
    old = combat._armor_choice_fn
    combat.set_armor_choice_fn(lambda p, d: called.append((p.id, d)) or 0)
    try:
        legal_actions(state, 1)
        view_for_player(state, 1)
        assert not called and state_to_dict(state) == before
        action = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
        assert apply_action(state, action)["success"]
        request = view_for_player(state, 2)["self"]["armor_reaction"]
        assert request["unit_id"] == "u2" and request["source_id"] == "u1"
        assert not called
    finally:
        combat.set_armor_choice_fn(old)


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test(); passed += 1
            except Exception as exc:
                failed += 1; print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
