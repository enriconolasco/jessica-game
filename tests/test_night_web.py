"""Contrato da fatia noturna de tropas, sem janelas de heróis."""
import os
import sys
from copy import deepcopy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica.web.server import _new_state
from jessica.core import combat, night_actions
from jessica.core.constants import Phase
from jessica.core.models import Troop, Hero, ArtifactOnField
from jessica.core.headless import legal_actions, apply_action, view_for_player, apply_event_to_view
from jessica.core.serialize import state_to_dict, state_from_dict
from jessica.core.turn import end_day


def night():
    state = _new_state(72)
    for p in state.players:
        p.units = []
    end_day(state)
    return state


def test_empty_night_advances_turn_and_curuna():
    state = night()
    before = state_to_dict(state)
    choices = legal_actions(state, 1)
    assert state_to_dict(state) == before
    assert [a["type"] for a in choices] == ["finish_night"]
    assert apply_action(state, choices[0])["success"]
    assert state.turn == 2 and state.phase == Phase.DAY and state.curuna_id == 2
    assert state.active_player_id == 2


def test_attack_core_parity_save_rng_and_events():
    state = night()
    for pid in (1, 2):
        state.players[pid - 1].units.append(Troop(id=f"u{pid}", owner_id=pid,
                                               house="center", life=4, life_max=4))
    night_actions.prepare(state)
    before = state_to_dict(state)
    action = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
    assert state_to_dict(state) == before
    twin = state_from_dict(before)
    direct = deepcopy(state)
    combat.resolve_attack(direct, combat.Attack(**action["params"]))
    night_actions.advance(direct)
    view = view_for_player(state, 1)
    result = apply_action(state, action)
    assert result["success"] and result == apply_action(twin, action)
    assert state_to_dict(state) == state_to_dict(twin) == state_to_dict(direct)
    for event in result["events"]:
        view = apply_event_to_view(view, event)
    view["events"] = []
    assert view == view_for_player(state, 1)


def test_invalid_wrong_player_and_dead_unit_no_mutation():
    state = night()
    for pid in (1, 2):
        state.players[pid - 1].units.append(Troop(id=f"u{pid}", owner_id=pid,
                                               house="center", life=2, life_max=4))
    action = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
    before = state_to_dict(state)
    wrong = deepcopy(action)
    wrong["player_id"] = 2
    assert not apply_action(state, wrong)["success"]
    assert state_to_dict(state) == before
    state.players[0].units[0].life = 0
    before = state_to_dict(state)
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before


def test_house_order_and_special_guard():
    state = night()
    state.curuna_id = 2
    for pid, house in ((1, "city_2"), (2, "city_1"), (3, "center")):
        state.players[pid - 1].units.append(Troop(id=f"u{pid}", owner_id=pid,
                                               house=house, life=4, life_max=4))
    night_actions.prepare(state)
    houses = [e["house"] for e in state.web_night["queue"]]
    assert houses == ["city_1", "city_2"]
    state.players[0].units.append(Hero(id="hero", owner_id=1, house="center",
                                     life=4, life_max=4, hero_id="ainai"))
    assert legal_actions(state, 1) == []
    assert view_for_player(state, 1)["night_limitations"]


def test_supported_heroes_attack_and_retaliation_match_core():
    for hero_id in ("miyamoto", "arken", "ori"):
        state = night()
        state.players[0].units.append(Hero(id="attacker", owner_id=1, house="center",
                                          life=4, life_max=4, hero_id=hero_id))
        state.players[1].units.append(Troop(id="defender", owner_id=2, house="center",
                                          life=2, life_max=4))
        night_actions.prepare(state)
        action = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
        direct = deepcopy(state)
        combat.resolve_attack(direct, combat.Attack(**action["params"]))
        night_actions.advance(direct)
        assert apply_action(state, action)["success"]
        assert state_to_dict(state) == state_to_dict(direct)


def test_http_full_day_night_save_and_next_day():
    import tempfile
    import threading
    from pathlib import Path
    from jessica.web import server
    from test_web_vertical import _request
    previous = server.SAVES
    with tempfile.TemporaryDirectory() as tmp:
        server.SAVES = Path(tmp)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            _, created = _request(base, "/matches", "POST", {"seed": 7})
            mid = created["match_id"]
            for pid in (1, 2, 3, 4):
                _, choices = _request(base, f"/matches/{mid}/actions?player_id={pid}")
                action = next(a for a in choices if a["type"] == "end_turn")
                _, result = _request(base, f"/matches/{mid}/actions", "POST", action)
                assert result["success"]
            _, saved = _request(base, f"/matches/{mid}/save", "POST", {})
            _, loaded = _request(base, "/matches/load", "POST", {"save_id": saved["save_id"]})
            mid = loaded["match_id"]
            _, choices = _request(base, f"/matches/{mid}/actions?player_id=1")
            action = next(a for a in choices if a["type"] == "finish_night")
            _, result = _request(base, f"/matches/{mid}/actions", "POST", action)
            assert result["success"]
            _, view = _request(base, f"/matches/{mid}/view?player_id=2")
            assert view["turn"] == 2 and view["phase"] == "day" and view["active_player_id"] == 2
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join()
            server.SAVES = previous


def test_next_turn_reopens_gnome_bets_before_morning():
    state = night()
    state.players[2].people = "gnomos_duendes"
    action = legal_actions(state, 1)[0]
    assert apply_action(state, action)["success"]
    assert state.turn == 2 and state.curuna_id == 2 and state.active_player_id == 3
    assert not state.players[1].morning_done_this_turn
    offers = legal_actions(state, 3)
    assert offers[0]["type"] == "allocate_bets"
    assert apply_action(state, offers[0])["success"]
    assert state.active_player_id == 2 and state.players[1].morning_done_this_turn


def test_city_destruction_and_immediate_core_victory():
    state = night()
    state.players[2].city.life = state.players[3].city.life = 0
    state.players[1].city.life = 1
    state.players[0].units.append(Troop(id="siege", owner_id=1, house="city_2",
                                      life=4, life_max=4))
    action = next(a for a in legal_actions(state, 1)
                  if a["type"] == "night_attack" and a["params"]["target_type"] == "city")
    assert apply_action(state, action)["success"]
    assert state.players[1].city.life <= 0
    assert state.game_over and state.winner_id == 1
    assert legal_actions(state, 1) == []


def test_pass_persists_and_does_not_consume_attack_or_rng():
    state = night()
    for pid in (1, 2):
        state.players[pid - 1].units.append(Troop(id=f"u{pid}", owner_id=pid,
                                               house="center", life=4, life_max=4))
    rng_before = state.rng.to_dict()
    action = next(a for a in legal_actions(state, 1) if a["type"] == "night_pass")
    assert apply_action(state, action)["success"]
    assert state.rng.to_dict() == rng_before
    resumed = state_from_dict(state_to_dict(state))
    assert legal_actions(resumed, 1) == []
    assert any(a["type"] == "night_attack" for a in legal_actions(resumed, 2))


def test_qd_interrupts_combat_third_player_save_and_resumes():
    from jessica.core.actions import resolve_pending_artifact_choice
    state = night()
    state.players[0].units.append(Troop(id="attacker", owner_id=1, house="center",
                                      life=4, life_max=4))
    state.players[1].units.append(Troop(id="marked", owner_id=2, house="center",
                                      life=1, life_max=6))
    state.players[2].field_artifacts.append(ArtifactOnField(
        card_id="Q_D", owner_id=3, extra={"target_unit_id": "marked"}))
    attack = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
    assert apply_action(state, attack)["success"]
    assert state.active_player_id == 3
    assert legal_actions(state, 1) == []
    state = state_from_dict(state_to_dict(state))
    before = state_to_dict(state)
    offered = legal_actions(state, 3)
    assert len(offered) == 2 and all(a["type"] == "night_resolve_choice" for a in offered)
    assert state_to_dict(state) == before
    choice = next(a for a in offered if a["params"] == {"resource": "magic"})
    invalid = deepcopy(choice)
    invalid["params"] = {"resource": "unknown"}
    assert not apply_action(state, invalid)["success"]
    assert state_to_dict(state) == before
    direct = deepcopy(state)
    resolve_pending_artifact_choice(direct, 3, resource="magic")
    night_actions.advance(direct)
    result = apply_action(state, choice)
    assert result["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    assert all(e["visibility"]["kind"] == "private" for e in result["events"])
    assert not state.players[2].pending_artifact_choice
    assert any(a["type"] == "finish_night" for a in legal_actions(state, 1))


def test_supported_hero_catalog_parity_matrix():
    for hero_id in sorted(night_actions.SUPPORTED_HEROES):
        state = night()
        hero = Hero(id="hero", owner_id=1, house="center", life=10, life_max=10, hero_id=hero_id)
        if hero_id == "barba_negra":
            hero.statuses["barba_hero_mode_turn"] = state.turn
        state.players[0].units.append(hero)
        state.players[1].units.append(Troop(id="target", owner_id=2, house="center", life=1, life_max=4))
        night_actions.prepare(state)
        before = state_to_dict(state)
        action = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
        assert state_to_dict(state) == before, hero_id
        direct = state_from_dict(before)
        combat.resolve_attack(direct, combat.Attack(**action["params"]))
        night_actions.advance(direct)
        assert apply_action(state, action)["success"], hero_id
        assert state_to_dict(state) == state_to_dict(direct), hero_id


def test_belial_pact_interrupt_accept_decline_and_save():
    for accept in (True, False):
        state = night()
        state.players[0].units.append(Hero(id="killer", owner_id=1, house="center",
                                          life=8, life_max=8, hero_id="miyamoto"))
        state.players[1].units.append(Hero(id="victim", owner_id=2, house="center",
                                          life=1, life_max=1, hero_id="arken"))
        state.players[2].people = "demonios"
        state.players[2].units.append(Hero(id="belial", owner_id=3, house="city_3",
                                          life=2, life_max=2, hero_id="belial"))
        attack = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
        assert apply_action(state, attack)["success"]
        assert state.players[0].demon_pact_offers
        state = state_from_dict(state_to_dict(state))
        before = state_to_dict(state)
        offers = legal_actions(state, 1)
        assert offers and {a["type"] for a in offers} <= {"night_pact", "night_decline_pact"}
        assert legal_actions(state, 2) == [] and state_to_dict(state) == before
        action = next(a for a in offers if a["type"] == ("night_pact" if accept else "night_decline_pact"))
        if accept:
            action = next(a for a in offers if a["params"].get("pact_id") == "sacrifique_futuro")
        direct = state_from_dict(before)
        from jessica.core.interaction_actions import execute
        execute(direct, dict(action, type="demon_pact" if accept else "decline_pact"))
        night_actions.advance(direct)
        assert apply_action(state, action)["success"]
        assert state_to_dict(state) == state_to_dict(direct)
        assert not state.players[0].demon_pact_offers


def test_rogue_clock_once_at_night_end_and_save():
    state = night()
    state.players[1].units.append(Hero(id="rogue", owner_id=2, house="city_2",
                                     life=2, life_max=2, hero_id="rogue_devil",
                                     statuses={"rogue_items": ["relogio"]}))
    state.combats_this_night = ["center", "city_1"]
    night_actions.prepare(state)
    assert state.active_player_id == 2
    state = state_from_dict(state_to_dict(state))
    choices = legal_actions(state, 2)
    assert len(choices) == 3
    declined = state_from_dict(state_to_dict(state))
    skip = next(a for a in choices if a["type"] == "night_skip_clock")
    assert apply_action(declined, skip)["success"]
    assert declined.players[1].units[0].house == "city_2"
    assert legal_actions(declined, 1)[0]["type"] == "finish_night"
    action = next(a for a in choices if a["params"].get("destination") == "center")
    assert apply_action(state, action)["success"]
    assert state.players[1].units[0].house == "center"
    assert not any(a["type"] == "night_clock" for a in legal_actions(state, 2))
    assert legal_actions(state, 1)[0]["type"] == "finish_night"


def test_barba_flames_only_once_across_queries_and_save():
    state = night()
    state.players[0].people = "dragoes"
    state.players[0].units.append(Hero(id="barba", owner_id=1, house="center",
                                     life=3, life_max=3, hero_id="barba_negra",
                                     statuses={"mar_chamas_queued_turn": state.turn}))
    state.players[1].units.append(Troop(id="target", owner_id=2, house="center", life=4, life_max=4))
    before = state_to_dict(state)
    legal_actions(state, 1)
    view_for_player(state, 1)
    assert state_to_dict(state) == before
    night_actions.prepare(state)
    assert state.players[1].units[0].life == 3
    state = state_from_dict(state_to_dict(state))
    night_actions.prepare(state)
    assert state.players[1].units[0].life == 3


def test_night_rogue_quest_rewards_on_signing_and_rejects_repeat():
    state = night()
    p = state.players[0]
    p.people = "demonios"
    p.units.append(Hero(id="rogue", owner_id=1, house="city_1",
                        life=0, life_max=0, hero_id="rogue_devil"))
    p.demon_pact_offers = [{"source": "rogue_devil", "demon_player_id": 1, "turn": state.turn}]
    offered = legal_actions(state, 1)
    assert offered and all(a["type"] == "night_pact" for a in offered)
    action = next(a for a in offered if a["params"].get("pact_id") == "banho_sangue"
                  and a["params"].get("item") == "capa")
    hand_before = len(p.hand)
    assert apply_action(state, action)["success"]
    p = state.players[0]
    assert p.units[0].life == 1 and p.units[0].life_max == 1
    assert "capa" in p.rogue_items and len(p.hand) == hand_before + 1
    before = state_to_dict(state)
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test()
                passed += 1
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
