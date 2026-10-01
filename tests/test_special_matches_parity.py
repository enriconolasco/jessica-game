"""Partidas completas com Bases Dragões e recompensa/quest de Rogue."""
import os
import sys
from collections import Counter
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from test_mixed_matches_parity import match, choose_day
from test_night_terminal_parity import compare
from test_web_cycle_parity import step
from jessica.web.server import _new_state
from jessica.core.headless import apply_action, legal_actions
from jessica.core.serialize import state_to_dict
from jessica.core.models import Hero, Troop
from jessica.core.constants import Phase, TroopArchetype
from jessica.core.heroes import HERO_CATALOG


def dragon_policy(state, choices, used):
    key = (state.turn, state.active_player_id, "cast_spell")
    spell = next((a for a in choices if a["type"] == "cast_spell"
                  and state.players[a["player_id"] - 1].people == "dragoes"), None)
    if spell and key not in used:
        used.add(key)
        return spell
    return choose_day(state, choices, used)


def test_barba_negra_and_rogue_complete_match():
    seen = Counter()

    def observe(before, action, after):
        params = action["params"]
        if action["type"] == "hero_ability":
            seen[params["ability"]] += 1
        if action["type"] == "cast_spell" and action["player_id"] == 2:
            seen["canastra"] += 1
        if action["type"] == "demon_pact":
            player = after.players[action["player_id"] - 1]
            old = before.players[player.id - 1]
            assert len(player.hand) == len(old.hand) + 1
            assert player.rogue_life_bonus == old.rogue_life_bonus + 1
            seen["rogue_pact"] += 1
        if action["type"] == "summon_hero" and action["player_id"] == 4:
            player = after.players[3]
            if player.rogue_life_bonus:
                rogue = next(u for u in player.units if getattr(u, "hero_id", None) == "rogue_devil")
                assert set(rogue.statuses.get("rogue_items", [])) == set(player.rogue_items)
                assert rogue.life == rogue.life_max == player.rogue_life_bonus + int("bracelete" in player.rogue_items)
                seen["resummon"] += 1

    counts, turn = match([("humanos", "miyamoto"), ("dragoes", "barba_negra"),
                          ("orcs", "vovo_gamba"), ("demonios", "rogue_devil")],
                         904, day_policy=dragon_policy, on_step=observe)
    assert seen["barba_flames"] and seen["barba_combat"] and seen["canastra"], seen
    assert seen["rogue_pact"] >= 1 and seen["resummon"] and counts["night_attack"] >= 3
    return counts, turn


def test_valtherion_and_rogue_complete_match():
    seen = Counter()

    def observe(before, action, after):
        if action["type"] == "hero_ability" and action["params"]["ability"] == "valtherion":
            seen["chamado"] += 1
        if action["type"] == "cast_spell" and action["player_id"] == 2:
            seen["canastra"] += 1

    result = match([("humanos", "miyamoto"), ("dragoes", "valtherion"),
                    ("orcs", "vovo_gamba"), ("demonios", "rogue_devil")],
                   905, day_policy=dragon_policy, on_step=observe)
    assert seen["chamado"] and seen["canastra"], seen
    return result


def test_rogue_quest_rewards_only_at_signing_in_complete_match():
    seen = Counter()

    def policy(state, choices, used):
        offer = next((a for a in choices if a["type"] == "demon_pact"
                      and a["params"].get("pact_id") == "vida_lider"
                      and a["params"].get("item") == "bracelete"), None)
        return offer or choose_day(state, choices, used)

    def observe(before, action, after):
        old, player = before.players[0], after.players[0]
        if action["type"] == "demon_pact" and action["player_id"] == 1:
            assert player.rogue_life_bonus == old.rogue_life_bonus + 1
            assert len(player.hand) == len(old.hand) + 1
            assert after.shop.size() == before.shop.size() - 1
            assert action["params"]["item"] in player.rogue_items
            seen["signed"] += 1
        for index, pact in enumerate(after.demon_pacts):
            if (pact["pact_id"] != "vida_lider" or not pact["completed"]
                    or index >= len(before.demon_pacts) or before.demon_pacts[index]["completed"]):
                continue
            assert pact["rogue_pact"] and pact["rewarded"]
            assert player.rogue_life_bonus == old.rogue_life_bonus
            assert player.rogue_items == old.rogue_items
            control = deepcopy(before)
            control.demon_pacts.pop(index)
            assert apply_action(control, action)["success"]
            assert player.hand == control.players[0].hand
            assert after.shop.deck == control.shop.deck
            assert state_to_dict(after)["rng"] == state_to_dict(control)["rng"]
            seen["completed_without_reward"] += 1

    result = match([("demonios", "rogue_devil"), ("dragoes", "barba_negra"),
                    ("orcs", "vovo_gamba"), ("fadas", "luna")],
                   906, day_policy=policy, on_step=observe)
    assert seen["signed"] and seen["completed_without_reward"], seen
    return result


def quest_case(pact_id, seed):
    setup = [("demonios", "rogue_devil"), ("humanos", "miyamoto"),
             ("orcs", "arken"), ("fadas", "luna")]
    state = _new_state(seed, [{"name": f"J{pid}", "people": people, "hero_id": hero}
        for pid, (people, hero) in enumerate(setup, 1)], {"magic": 25, "order_mode": "fixed"})
    plan = {}
    for pid, archetype, life in ((2, TroopArchetype.LIGHT, 4), (3, TroopArchetype.MEDIUM, 6),
                                 (4, TroopArchetype.HEAVY, 8)):
        hid = setup[pid - 1][1]
        state.players[pid - 1].units = [Hero(id=f"enemy{pid}", owner_id=pid, house="center",
            life=1, life_max=HERO_CATALOG[hid].life, hero_id=hid)]
        uid = f"troop{pid}"
        state.players[0].units.append(Troop(id=uid, owner_id=1, house="center", life=life,
                                           life_max=life, archetype=archetype))
        plan[uid] = [("unit", f"enemy{pid}")]
    state = step(state, next(a for a in legal_actions(state, 1) if a["type"] == "summon_hero"))
    before = state_to_dict(state)
    state = step(state, next(a for a in legal_actions(state, 1) if a["type"] == "demon_pact"
        and a["params"]["pact_id"] == pact_id and a["params"]["item"] == "bracelete"))
    pact = state.demon_pacts[0]
    assert pact["rogue_pact"] and pact["rewarded"] and not pact["completed"]
    assert state.players[0].rogue_life_bonus == 1 and state.players[0].rogue_items == ["bracelete"]
    assert len(state.players[0].hand) == len(before["players"][0]["hand"]) + 1
    while state.phase == Phase.DAY:
        state = step(state, next(a for a in legal_actions(state, state.active_player_id)
                                if a["type"] == "end_turn"))
    before = deepcopy(state)
    state, trace = compare(state, plan)
    assert len(trace) == 3 and state.demon_pacts[0]["completed"]
    assert state.players[0].hand == before.players[0].hand
    assert state.players[0].rogue_life_bonus == before.players[0].rogue_life_bonus
    assert state.players[0].rogue_items == before.players[0].rogue_items
    assert state.shop.deck == before.shop.deck
    assert state_to_dict(state)["rng"] == state_to_dict(before)["rng"]
    return {"night_attack": len(trace)}, state.turn


def test_rogue_blood_quest_has_no_completion_reward():
    return quest_case("banho_sangue", 907)


def test_rogue_hero_peoples_quest_has_no_completion_reward():
    return quest_case("cabecas_herois", 908)


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                counts, turn = test()
                passed += 1
                print(f"CENÁRIO - {name}: T{turn}; decisões {sum(counts.values())}")
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(1 if failed else 0)
