import os, sys, json, tempfile, threading
from contextlib import contextmanager
from pathlib import Path
from copy import deepcopy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica.web import server, session, saves
from jessica.core import heroes, artifacts, night_actions
from jessica.core.headless import legal_actions, apply_action, view_for_player
from jessica.core.models import Hero
from jessica.core.serialize import state_to_dict
from jessica.core.setup import roll_d20_order
from jessica.core.state import make_rng
from test_web_vertical import _request, _error_request


@contextmanager
def http():
    old_saves = server.SAVES
    with tempfile.TemporaryDirectory() as tmp:
        server.SAVES = Path(tmp)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{httpd.server_port}"
        finally:
            httpd.shutdown(); httpd.server_close(); server.SAVES = old_saves


def test_catalog_covers_every_hero_artifact_people_and_pact():
    catalog = server._catalog()
    assert {h["id"] for h in catalog["heroes"]} == set(heroes.HERO_CATALOG)
    assert {a["id"] for a in catalog["artifacts"]} == set(artifacts.ARTIFACT_CATALOG)
    assert len(catalog["peoples"]) == 12 and len(catalog["pacts"]) == 6
    assert all(h["description"] for h in catalog["heroes"])
    assert all(p["passive"] and p["spell"]["description"] for p in catalog["peoples"])
    assert "ent" not in {h["id"] for p in catalog["peoples"] for h in p["heroes"]}
    assert set(heroes.HERO_CATALOG) - {"ent", "seven_dwarves"} <= night_actions.SUPPORTED_HEROES


def test_d20_order_uses_terminal_setup_rng_and_preview():
    with http() as base:
        _, order = _request(base, "/setup-order?seed=49")
        expected = roll_d20_order(make_rng(49), 4)
        assert order["turn_order"] == [1, 2, 3, 4] and order["initial_curuna_id"] == expected[0]
        _, created = _request(base, "/matches", "POST", {"seed":49, "config":{"order_mode":"d20"}})
        state = server.MATCHES[created["match_id"]]["state"]
        assert state.turn_order == [1, 2, 3, 4] and state.curuna_id == expected[0]


def test_undo_mola_save_import_and_invalid_restore():
    with http() as base:
        _, created = _request(base, "/matches", "POST", {"seed":73})
        mid = created["match_id"]; match = server.MATCHES[mid]
        baseline = state_to_dict(match["state"])
        _, actions = _request(base, f"/matches/{mid}/actions")
        collect = next(a for a in actions if a["type"] == "collect_resources")
        _request(base, f"/matches/{mid}/actions", "POST", collect)
        _request(base, f"/matches/{mid}/system", "POST", {"operation":"undo"})
        assert state_to_dict(match["state"]) == baseline
        _, actions = _request(base, f"/matches/{mid}/actions")
        _request(base, f"/matches/{mid}/actions", "POST", next(a for a in actions if a["type"] == "end_turn"))
        assert match["state"].active_player_id == 2 and session.controls(match)["mola"]
        _, export = _request(base, f"/matches/{mid}/export")
        _, imported = _request(base, "/matches/import", "POST", export)
        restored = server.MATCHES[imported["match_id"]]
        assert session.controls(restored)["mola"]
        _request(base, f"/matches/{imported['match_id']}/system", "POST", {"operation":"mola"})
        assert state_to_dict(restored["state"]) == baseline
        assert len(restored["history"]) == 1
        before = state_to_dict(restored["state"])
        assert _error_request(base, f"/matches/{imported['match_id']}/system", {"operation":"mola"})[0] == 422
        assert state_to_dict(restored["state"]) == before
        export["history"][0]["snapshot"]["history"] = []
        assert _error_request(base, "/matches/import", export)[0] == 422


def test_checkpoint_clears_even_before_gnomes_morning():
    match = {"state":server._new_state(31), "events":[]}
    session.checkpoint(match)
    assert match["history"]
    match["state"].turn += 1
    match["state"].players[0].morning_done_this_turn = False
    session.checkpoint(match)
    assert not match["history"]


def test_conditions_reports_and_events_do_not_reveal_private_payloads():
    state = server._new_state(31)
    p = state.players[1]
    p.hand = ["PENA"]
    p.pending_artifact_choice = {"secret":"hidden-choice"}
    p.units = [Hero(id="soneca", owner_id=2, house="center", life=2, life_max=2, hero_id="bein")]
    p.units[0].statuses["private-note"] = "hidden-status"
    p.dwarf_empalados = [{"sig":{"kind":"hero", "id":"miyamoto"}, "dwarf_owner_id":2}]
    p.infectados = [{"kind":"hero", "id":"arken", "owner_id":3, "unit_id":"arken", "secret":"hidden-infection"}]
    view = view_for_player(state, 1)
    serialized = json.dumps(view)
    assert all(secret not in serialized for secret in ("hidden-choice", "hidden-status", "hidden-infection"))
    assert any(c["condition"] == "Empalado por Soneca" for c in view["conditions"])
    assert any(c.get("controller_id") == 2 and c["owner_id"] == 3 for c in view["conditions"])
    before = session.public_snapshot(state)
    state.players[0].city.magic += 1
    state.players[0].hand.append("K_H")
    event = session.changes(before, state, {})[0]
    assert "K_H" not in json.dumps(event) and "PENA" not in json.dumps(event)
    assert any(c["field"] == "magic" for c in event["data"]["changes"])
    assert any(c["field"] == "hand_count" for c in event["data"]["changes"])


def test_full_match_to_victory_through_structured_actions():
    state = server._new_state(42, config={"city_life":1, "gold":20, "magic":20})
    summoned = False
    for _ in range(180):
        if state.game_over:
            break
        pid = state.active_player_id
        actions = legal_actions(state, pid)
        assert actions, (state.turn, state.phase, pid)
        action = None
        if pid == 1 and state.phase.value == "day":
            target = next((p.id for p in state.players[1:] if p.city.is_alive()), None)
            if not summoned:
                action = next((a for a in actions if a["type"] == "summon_troop"
                               and a["params"]["archetype"] == "light" and a["params"]["life"] == 4), None)
                summoned = action is not None
            if action is None and target:
                unit = next((u for u in state.players[0].units if u.is_alive()), None)
                destination = f"city_{target}" if unit and unit.house == "center" else "center"
                if unit and unit.house != f"city_{target}":
                    action = next((a for a in actions if a["type"] == "move_unit"
                                   and a["params"]["destination"] == destination), None)
        if action is None and pid == 1:
            action = next((a for a in actions if a["type"] == "night_attack"
                           and a["params"].get("target_type") == "city"), None)
        if action is None:
            action = next((a for kind in ("end_turn", "night_pass", "night_window_done", "finish_night")
                           for a in actions if a["type"] == kind), actions[0])
        result = apply_action(state, action)
        assert result["success"], result
        state, _, _ = saves.validate({"version":saves.SAVE_VERSION, "state":state_to_dict(state), "events":[]})
    assert state.game_over and state.winner_id == 1, (state.turn, state.winner_id)


def test_all_twelve_spell_flows_match_direct_core():
    from jessica.core.actions import cast_spell
    from jessica.core.models import Troop
    for people in server.PEOPLES:
        chosen = [people] + [p for p in server.PEOPLES if p != people][:3]
        rows = [{"name":f"J{i}", "people":p,
                 "hero_id":"" if p == "mortos_vivos" else heroes.heroes_for_people(p)[0].hero_id}
                for i, p in enumerate(chosen, 1)]
        state = server._new_state(23, rows, {"gold":100, "magic":100})
        actions = legal_actions(state, 1)
        allocation = next((a for a in actions if a["type"] == "allocate_bets"), None)
        if allocation:
            allocation["params"] = {"bets":{s:2 for s in "HCDS"}}
            assert apply_action(state, allocation)["success"]
        summon = next((a for a in legal_actions(state, 1) if a["type"] == "summon_hero"), None)
        if summon:
            assert apply_action(state, summon)["success"]
        p = state.players[0]
        for u in p.units:
            u.house = "city_2"
        if people != "dragoes":
            p.units.append(Troop(id="ally", owner_id=1, house="city_2", life=4, life_max=4))
        state.players[1].units.append(Troop(id="enemy", owner_id=2, house="city_2", life=4, life_max=4))
        p.hand = ["J_H", "Q_D", "K_C", "K_S"]
        before = state_to_dict(state)
        action = next((a for a in legal_actions(state, 1) if a["type"] in ("cast_spell", "sacrifice_spell")), None)
        assert action is not None, people
        assert state_to_dict(state) == before
        direct = deepcopy(state)
        params = action["params"]
        choice = params["choice"] if action["type"] == "cast_spell" else params
        cast_spell(direct, 1, deepcopy(choice))
        result = apply_action(state, action)
        assert result["success"], (people, result)
        assert state_to_dict(state) == state_to_dict(direct), people


def test_empty_house_announcements_and_public_event_projection():
    from jessica.core.headless import apply_event_to_view
    from jessica.core.turn import end_day
    state = server._new_state(31)
    before = session.public_snapshot(state)
    view = view_for_player(state, 1)
    state.players[0].city.magic += 1
    events = session.changes(before, state, {})
    for event in events:
        view = apply_event_to_view(view, event)
    assert view["players"][0]["city"]["magic"] == state.players[0].city.magic
    end_day(state)
    night_actions.prepare(state)
    announcements = [e for e in session.public_events(state) if e["type"] == "combat_house_opened"]
    assert len(announcements) == 5 and all(not e["data"]["order"] for e in announcements)
    assert {e["data"]["house"] for e in announcements} == {"center", "city_1", "city_2", "city_3", "city_4"}


def test_http_armor_response_privacy_preview_history_and_save():
    from test_night_web import night
    from jessica.core.models import Troop
    with http() as base:
        _, created = _request(base, "/matches", "POST", {"seed":31})
        mid = created["match_id"]
        state = night()
        for pid in (1, 2):
            p = state.players[pid - 1]
            p.units = [Troop(id=f"u{pid}", owner_id=pid, house="center", life=4, life_max=4)]
            p.armor_active_until_turn = state.turn
            p.city.gold = 8
        state.players[1].hand = ["PENA"]
        night_actions.prepare(state)
        server.MATCHES[mid] = {"state":state, "events":[], "history":[]}
        route = f"/matches/{mid}/actions"
        attack = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
        _, result = _request(base, route, "POST", attack)
        assert result["pending"] and "PENA" not in json.dumps(result)
        _, view = _request(base, f"/matches/{mid}/view?player_id=1")
        assert "PENA" not in json.dumps(view)
        _, export = _request(base, f"/matches/{mid}/export")
        restored, _, _ = saves.validate(export)
        assert state_to_dict(restored) == state_to_dict(state)
        choice = legal_actions(state, 2)[0]; choice["params"] = {"gold":2}
        _, result = _request(base, route, "POST", choice)
        assert result["pending"] and "PENA" not in json.dumps(result)
        _, view = _request(base, f"/matches/{mid}/view?player_id=1")
        assert view["players"][1]["city"]["gold"] == 6
        choice = legal_actions(state, 1)[0]
        _, result = _request(base, route, "POST", choice)
        assert not result["pending"] and "PENA" not in json.dumps(result)
        changes = [c for e in result["events"] if e["type"] == "public_state_changed" for c in e["data"]["changes"]]
        assert any(c.get("player_id") == 2 and c.get("field") == "gold" and c["before"] == 8 and c["after"] == 6 for c in changes)


def test_browser_qa_scenarios_restore_their_required_decisions():
    from jessica.core.headless import SAVE_VERSION
    from serve_ui_scenarios import scenarios
    states = dict(scenarios())
    assert len(states) == 6
    for name, state in states.items():
        restored, _, _ = saves.validate({"version": SAVE_VERSION, "state": state_to_dict(state),
                                         "events": [], "history": [], "name": name})
        assert state_to_dict(restored) == state_to_dict(state)
        assert legal_actions(restored, restored.active_player_id)


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test(); passed += 1
            except Exception as exc:
                failed += 1; print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
