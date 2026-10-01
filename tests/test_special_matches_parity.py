"""Partidas completas com Bases Dragões e recompensa/quest de Rogue."""
import os
import sys
from collections import Counter
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from test_mixed_matches_parity import match, choose_day
from jessica.core.headless import apply_action
from jessica.core.serialize import state_to_dict


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


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                counts, turn = test()
                passed += 1
                print(f"PARTIDA - {name}: vitória T{turn}; decisões {sum(counts.values())}")
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(1 if failed else 0)
