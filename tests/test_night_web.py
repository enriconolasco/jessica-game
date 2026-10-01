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
    assert state.web_night["queue"][0]["house"] == "city_1"
    state.players[0].units.append(Hero(id="hero", owner_id=1, house="center",
                                     life=4, life_max=4, hero_id="unknown_hero"))
    assert legal_actions(state, 1) == []
    assert view_for_player(state, 1)["night_limitations"]


def test_ainai_opening_save_and_single_use():
    state = night()
    p = state.players[0]
    p.units = [Hero(id="ainai", owner_id=1, house="center", life=4, life_max=4, hero_id="ainai")]
    state.fae_fallen_this_turn = [(1, "city_2"), (2, "city_3")]
    night_actions.prepare(state)
    before = state_to_dict(state)
    options = legal_actions(state, 1)
    assert state_to_dict(state) == before
    action = next(a for a in options if a["type"] == "night_ainai")
    assert action["params"] == {"destination": "city_2"}
    restored = state_from_dict(before)
    assert apply_action(state, action) == apply_action(restored, action)
    assert state_to_dict(state) == state_to_dict(restored)
    assert state.players[0].units[0].house == "city_2"
    assert state.players[0].city.magic == p.city.magic + 1
    assert not apply_action(state, action)["success"]


def test_luide_reentry_save_and_death_gate():
    state = night()
    p = state.players[0]
    p.people = "vampiros"
    p.units = [Hero(id="luide", owner_id=1, house="city_4", life=8, life_max=8, hero_id="luide_vampa")]
    state.players[1].units = [Troop(id="enemy", owner_id=2, house="center", life=8, life_max=8)]
    state.players[2].units = [Troop(id="local_enemy", owner_id=3, house="city_4", life=8, life_max=8)]
    night_actions.prepare(state)
    assert "center" in state.web_night["processed"]
    action = next(a for a in legal_actions(state, 1) if a["type"] == "night_luide_move")
    restored = state_from_dict(state_to_dict(state))
    assert apply_action(state, action) == apply_action(restored, action)
    assert state_to_dict(state) == state_to_dict(restored)
    assert any(a["type"] == "night_attack" for a in legal_actions(state, 1))
    passed = next(a for a in legal_actions(state, 1) if a["type"] == "night_pass")
    assert apply_action(state, passed)["success"]
    assert any(a["type"] == "night_window_done" for a in legal_actions(state, 1))
    state.players[0].units[0].life = 0
    assert not any(a["type"].startswith("night_luide") for a in legal_actions(state, 1))


def test_luide_spell_then_move_to_future_house():
    state = night()
    p = state.players[0]
    p.people = "vampiros"
    p.city.magic = 20
    p.units = [Hero(id="luide", owner_id=1, house="center", life=8, life_max=8, hero_id="luide_vampa")]
    state.players[1].units = [Troop(id="enemy", owner_id=2, house="center", life=8, life_max=8)]
    state.players[2].units = [Troop(id="future", owner_id=3, house="city_4", life=8, life_max=8)]
    night_actions.prepare(state)
    spell = next(a for a in legal_actions(state, 1) if a["type"] == "night_luide_spell")
    assert apply_action(state, spell)["success"]
    move = next(a for a in legal_actions(state, 1) if a["type"] == "night_luide_move"
                and a["params"]["destination"] == "city_4")
    assert apply_action(state, move)["success"]
    for _ in range(12):
        actions = legal_actions(state, state.active_player_id)
        if state.web_night["queue"][0].get("house") == "city_4":
            break
        action = next(a for a in actions if a["type"] in ("night_window_done", "night_pass"))
        assert apply_action(state, action)["success"]
    assert any(e.get("unit_id") == "luide" and e["house"] == "city_4" for e in state.web_night["queue"])


def test_ainai_after_house_reopens_processed_location():
    state = night()
    state.players[0].units = [Hero(id="ainai", owner_id=1, house="city_1", life=4, life_max=4, hero_id="ainai")]
    state.players[1].units = [Troop(id="enemy", owner_id=2, house="center", life=4, life_max=4)]
    state.fae_fallen_this_turn = [(1, "center")]
    night_actions.prepare(state)
    decline = next(a for a in legal_actions(state, 1) if a["type"] == "night_window_done")
    assert apply_action(state, decline)["success"]
    assert "center" in state.web_night["processed"]
    teleport = next(a for a in legal_actions(state, 1) if a["type"] == "night_ainai")
    assert apply_action(state, teleport)["success"]
    assert any(a["type"] == "night_attack" for a in legal_actions(state, 1))


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
        setup = next((a for a in legal_actions(state, 1) if a["type"] == "night_setup"), None)
        if setup:
            assert apply_action(state, setup)["success"]
        before = state_to_dict(state)
        action = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
        assert state_to_dict(state) == before, hero_id
        direct = state_from_dict(before)
        combat.resolve_attack(direct, combat.Attack(**action["params"]))
        night_actions.advance(direct)
        assert apply_action(state, action)["success"], hero_id
        assert state_to_dict(state) == state_to_dict(direct), hero_id


def test_belial_pact_deferral_does_not_block_night_after_save():
    for beneficiary in (1, 2):
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
        if beneficiary == 2:
            state.players[1].demon_pact_offers = state.players[0].demon_pact_offers
            state.players[0].demon_pact_offers = []
        state = state_from_dict(state_to_dict(state))
        before = state_to_dict(state)
        offers = legal_actions(state, 1)
        assert [a["type"] for a in offers] == ["finish_night"]
        assert legal_actions(state, 2) == [] and state_to_dict(state) == before
        assert apply_action(state, offers[0])["success"]
        assert state.phase == Phase.DAY and state.players[beneficiary - 1].demon_pact_offers
        assert not state.demon_pacts


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


def test_vovo_flames_luna_order_save_and_return():
    state = night()
    state.players[0].units.append(Hero(id="vovo", owner_id=1, house="center",
                                     life=3, life_max=3, hero_id="vovo_gamba"))
    state.players[1].units.append(Hero(id="luna", owner_id=2, house="center",
                                     life=2, life_max=2, hero_id="luna",
                                     statuses={"luna_origin_house": "city_2"}))
    state.players[2].people = "dragoes"
    state.players[2].units.append(Hero(id="barba", owner_id=3, house="center",
                                     life=3, life_max=3, hero_id="barba_negra",
                                     statuses={"mar_chamas_queued_turn": state.turn}))
    night_actions.prepare(state)
    assert state.active_player_id == 1 and state.players[1].units[0].life == 2
    state = state_from_dict(state_to_dict(state))
    before = state_to_dict(state)
    offers = legal_actions(state, 1)
    assert len(offers) == 4 and state_to_dict(state) == before
    invalid = deepcopy(offers[0])
    invalid["params"]["position"] = True
    assert not apply_action(state, invalid)["success"]
    assert state_to_dict(state) == before
    assert apply_action(state, offers[1])["success"]
    assert state.players[0].vovo_position == 2
    assert state.players[1].units[0].life == 1 and state.active_player_id == 2
    state = state_from_dict(state_to_dict(state))
    offers = legal_actions(state, 2)
    assert len(offers) == 2
    assert apply_action(state, next(a for a in offers if a["params"]["return"]))["success"]
    luna = state.players[1].units[0]
    assert luna.house == "city_2" and "luna_origin_house" not in luna.statuses
    assert state.web_night["ready"] and not state.web_night["setup"]
    assert luna.life == 1


def test_luna_may_decline_return_without_moving():
    state = night()
    state.players[0].units.append(Hero(id="luna", owner_id=1, house="center",
                                     life=2, life_max=2, hero_id="luna",
                                     statuses={"luna_origin_house": "city_1"}))
    offer = next(a for a in legal_actions(state, 1) if a["params"].get("return") is False)
    assert apply_action(state, offer)["success"]
    assert state.players[0].units[0].house == "center"
    assert not any(a["type"] == "night_setup" for a in legal_actions(state, 1))


def test_mandinga_jd_scheduled_save_and_once_per_night():
    from jessica.core.actions import besouro_mandinga
    state = night()
    p = state.players[0]
    p.units.append(Hero(id="besouro", owner_id=1, house="center", life=4, life_max=4, hero_id="besouro"))
    p.hand = ["J_D", "PENA"]
    night_actions.prepare(state)
    before = state_to_dict(state)
    offers = legal_actions(state, 1)
    assert not any(a["params"].get("card_id") == "PENA" for a in offers)
    action = next(a for a in offers if a["type"] == "night_mandinga")
    assert state_to_dict(state) == before
    direct = state_from_dict(before)
    besouro_mandinga(direct, 1, **action["params"])
    direct.web_night["setup"].pop(0)
    night_actions.advance(direct)
    assert apply_action(state, action)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    assert state.players[0].pending_artifact_choice is None
    assert any(e["kind"] == "J_D" and e["due_turn"] == state.turn + 3 for e in state.pending_effects)
    state = state_from_dict(state_to_dict(state))
    assert not apply_action(state, action)["success"]
    assert state.players[0].besouro_mandinga_used_turn == state.turn


def test_aiquara_opening_control_parity_save_and_limits():
    from jessica.core.actions import aiquara_atacar
    state = night()
    state.players[0].units.append(Hero(id="aiquara", owner_id=1, house="center",
                                     life=2, life_max=2, hero_id="aiquara"))
    state.players[1].units.append(Troop(id="controlled", owner_id=2, house="center", life=4, life_max=4))
    state.players[2].units.append(Troop(id="target", owner_id=3, house="center", life=2, life_max=4))
    state.players[3].units.append(Hero(id="immune", owner_id=4, house="center",
                                     life=20, life_max=20, hero_id="valtherion"))
    night_actions.prepare(state)
    state = state_from_dict(state_to_dict(state))
    before = state_to_dict(state)
    choices = legal_actions(state, 1)
    assert not any(a["type"] == "night_attack" for a in choices)
    assert not any(a["params"].get("enemy_unit_id") == "immune" for a in choices)
    assert state_to_dict(state) == before and legal_actions(state, 2) == []
    action = next(a for a in choices if a["type"] == "night_aiquara"
                  and a["params"]["enemy_unit_id"] == "controlled" and a["params"]["target_id"] == "target")
    direct = state_from_dict(before)
    aiquara_atacar(direct, 1, **action["params"])
    direct.web_night["setup"].pop(0)
    night_actions.advance(direct)
    assert apply_action(state, action)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    before = state_to_dict(state)
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before
    dead = state_from_dict(before)
    next(u for u in dead.players[0].units if u.id == "aiquara").life = 0
    assert not apply_action(dead, action)["success"]


def test_barba_base_nao_oferece_alvo_para_heroi_ate_ativar_modo():
    from test_playtest_round4 import make_state
    from jessica.core import peoples
    state = make_state()
    barba = peoples.dragon_base(state.players[0])
    barba.house = "center"
    state.players[1].units = [Hero(id="enemy", owner_id=2, house="center", life=4, life_max=4, hero_id="miyamoto")]
    state.phase = Phase.NIGHT
    assert not any(a["type"] == "night_attack" for a in legal_actions(state, 2))
    state.phase = Phase.DAY
    from jessica.core.actions import barba_combater_como_heroi
    barba_combater_como_heroi(state, 1)
    state.phase = Phase.NIGHT
    skip = next(a for a in legal_actions(state, 1) if a["type"] == "night_pass")
    assert apply_action(state, skip)["success"]
    assert any(a["type"] == "night_attack" and a["params"]["target_id"] == barba.id
               for a in legal_actions(state, 2))


def test_luide_empty_house_still_opens_window():
    state = night()
    p = state.players[0]
    p.people, p.city.magic = "vampiros", 20
    p.units = [Hero(id="luide", owner_id=1, house="center", life=8, life_max=8,
                    hero_id="luide_vampa"),
               Troop(id="alone", owner_id=1, house="city_1", life=4, life_max=4,
                     moves_this_turn=1, max_moves_this_turn=1)]
    night_actions.prepare(state)
    choices = legal_actions(state, 1)
    assert any(a["type"] == "night_luide_move" for a in choices)
    assert not any(a["type"] == "night_attack" for a in choices)
    assert apply_action(state, next(a for a in choices if a["type"] == "night_window_done"))["success"]
    assert state.web_night["queue"][0]["house"] == "city_1"
    choices = legal_actions(state, 1)
    spell = next(a for a in choices if a["type"] == "night_luide_spell" and a["params"]["unit_id"] == "alone")
    restored = state_from_dict(state_to_dict(state))
    assert apply_action(state, spell) == apply_action(restored, spell)
    assert state_to_dict(state) == state_to_dict(restored)
    move = next(a for a in legal_actions(state, 1) if a["type"] == "night_luide_move"
                and a["params"] == {"unit_id": "alone", "destination": "center"})
    assert apply_action(state, move)["success"]
    assert apply_action(state, next(a for a in legal_actions(state, 1)
                                   if a["type"] == "night_window_done"))["success"]
    assert [a["type"] for a in legal_actions(state, 1)] == ["finish_night"]
    assert not state.combats_this_night


def test_luide_dead_does_not_open_empty_windows():
    state = night()
    p = state.players[0]
    p.people = "vampiros"
    p.units = [Hero(id="luide", owner_id=1, house="center", life=0, life_max=8,
                    hero_id="luide_vampa"),
               Troop(id="alone", owner_id=1, house="city_1", life=4, life_max=4)]
    night_actions.prepare(state)
    assert [a["type"] for a in legal_actions(state, 1)] == ["finish_night"]


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
