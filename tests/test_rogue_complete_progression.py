"""Quests e aquisição de itens desde preparação normal até vitória, sem inserir unidades."""
import os
import sys
from collections import Counter
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from test_mixed_matches_parity import match, choose_day, choose_night
from jessica.core.models import Hero
from jessica.core import peoples
from jessica.core.headless import apply_action
from jessica.core.serialize import state_to_dict
from jessica.web import session


GROUP = [("demonios", "rogue_devil"), ("humanos", "miyamoto"),
         ("orcs", "arken"), ("fadas", "luna")]


def completed(state, pact_id):
    return any(p["pact_id"] == pact_id and p["completed"] for p in state.demon_pacts)


def progression(pact_id, seed, all_items=False):
    seen = Counter()
    pacts = ["sacrifique_futuro", "banho_sangue", "vida_lider", "cabecas_herois"]
    items = ["bracelete", "adaga", "relogio", "capa"]

    def policy(state, choices, used):
        player = state.players[state.active_player_id - 1]
        if player.id == 1:
            offers = [a for a in choices if a["type"] == "demon_pact"]
            if offers:
                index = len(player.rogue_items)
                wanted = pacts[min(index, 3)] if all_items else pact_id
                item = items[min(index, 3)] if all_items else "bracelete"
                return next((a for a in offers if a["params"]["pact_id"] == wanted
                             and a["params"].get("item") == item), offers[0])
        collect = next((a for a in choices if a["type"] == "collect_resources"), None)
        if collect:
            return collect
        if not any(isinstance(u, Hero) and u.is_alive() for u in player.units):
            summon = next((a for a in choices if a["type"] == "summon_hero"), None)
            if summon:
                return summon
        if all_items and player.id == 1 and len(player.rogue_items) < 4:
            sacrifice = next((a for a in choices if a["type"] == "sacrifice_spell"), None)
            return sacrifice or next(a for a in choices if a["type"] == "end_turn")
        if not all_items and not completed(state, pact_id):
            if player.id == 1:
                troops = [a for a in choices if a["type"] == "summon_troop"]
                if troops:
                    return max(troops, key=lambda a: a["params"]["life"])
            move = next((a for a in choices if a["type"] == "move_unit"
                         and a["params"]["destination"] == "center"), None)
            return move or next(a for a in choices if a["type"] == "end_turn")
        return choose_day(state, choices, used)

    def night_policy(state, choices):
        if not all_items and not completed(state, pact_id):
            attacks = [a for a in choices if a["type"] == "night_attack" and a["player_id"] == 1
                       and a["params"]["target_type"] == "unit"]
            units = {u.id: u for p in state.players for u in p.units}
            attacks = [a for a in attacks if not isinstance(units[a["params"]["attacker_unit_id"]], Hero)]
            if attacks:
                return max(attacks, key=lambda a: units[a["params"]["target_id"]].life)
            passed = next((a for a in choices if a["type"] == "night_pass"), None)
            return passed or choose_night(state, choices)
        return choose_night(state, choices)

    def observe(before, action, after):
        old, player = before.players[0], after.players[0]
        snapshot = state_to_dict(after)
        events = session.changes(session.public_snapshot(before), after, action)
        pact_changes = [c for e in events if e["type"] == "public_state_changed"
                        for c in e["data"]["changes"] if c["kind"] == "pact"]
        assert state_to_dict(after) == snapshot
        if action["type"] == "demon_pact" and action["player_id"] == 1:
            assert player.rogue_life_bonus == old.rogue_life_bonus + 1
            assert len(player.hand) == len(old.hand) + 1
            assert after.shop.size() == before.shop.size() - 1
            assert any(c["before"] is None and c["after"]["rogue_pact"] for c in pact_changes)
            seen["signed"] += 1
        if len(player.rogue_items) == 4:
            seen["four_items"] += 1
        if action["type"] == "sacrifice_spell" and action["player_id"] == 1:
            assert old.rogue_items == player.rogue_items
            assert old.rogue_life_bonus == player.rogue_life_bonus
            seen["sacrificed"] += 1
        if action["type"] == "summon_hero" and action["player_id"] == 1:
            rogue = next((u for u in player.units if getattr(u, "hero_id", None) == "rogue_devil"
                          and u.is_alive()), None)
            if rogue:
                assert set(rogue.statuses["rogue_items"]) == set(player.rogue_items)
                assert rogue.life == rogue.life_max == player.rogue_life_bonus + int("bracelete" in player.rogue_items)
                seen["restored"] += 1
        if action["type"] == "night_attack" and action["params"]["target_type"] == "city":
            attacker = next(u for u in old.units if u.id == action["params"]["attacker_unit_id"])
            if isinstance(attacker, Hero) and attacker.hero_id == "rogue_devil":
                assert peoples.rogue_can_attack_base(attacker)
                seen["rogue_base"] += 1
        for index, (old_pact, pact) in enumerate(zip(before.demon_pacts, after.demon_pacts)):
            if pact["completed"] and not old_pact["completed"] and pact["pact_id"] == pact_id:
                control = deepcopy(before)
                control.demon_pacts.pop(index)
                assert apply_action(control, action)["success"]
                other = control.players[0]
                assert player.hand == other.hand and player.rogue_life_bonus == other.rogue_life_bonus
                assert player.rogue_items == other.rogue_items and after.shop.deck == control.shop.deck
                assert state_to_dict(after)["rng"] == state_to_dict(control)["rng"]
                assert any(c["after"]["pact_id"] == pact_id and c["after"]["completed"]
                           and not c["before"]["completed"] for c in pact_changes)
                seen["quest_completed"] += 1

    result = match(GROUP, seed, day_policy=policy, on_step=observe, night_policy=night_policy)
    assert seen["signed"], seen
    if all_items:
        assert seen["four_items"] and seen["sacrificed"] >= 3 and seen["restored"] >= 3 and seen["rogue_base"], seen
    else:
        assert seen["quest_completed"], seen
    return result


def test_blood_quest_from_setup_to_victory():
    return progression("banho_sangue", 909)


def test_hero_peoples_quest_from_setup_to_victory():
    return progression("cabecas_herois", 910)


def test_four_items_from_invocation_to_victory():
    return progression("vida_lider", 911, all_items=True)


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                counts, turn = test()
                passed += 1
                print(f"PARTIDA - {name}: T{turn}; decisões {sum(counts.values())}", flush=True)
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}", flush=True)
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(1 if failed else 0)
