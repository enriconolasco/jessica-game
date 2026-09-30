"""Contrato HTTP da prova web vertical."""
import json
import os
import sys
import tempfile
import threading
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.web import server


def _request(base, path, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read())


def _raw(base, path):
    with urllib.request.urlopen(base + path) as response:
        return response.status, response.headers.get_content_type(), response.read()


def _error_request(base, path, body):
    try:
        _request(base, path, "POST", body)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())
    raise AssertionError("A requisição deveria ter sido rejeitada")


def test_http_vertical_action_view_events_and_autosave():
    old_saves = server.SAVES
    with tempfile.TemporaryDirectory() as tmp:
        server.SAVES = Path(tmp)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            status, created = _request(base, "/matches", "POST", {"seed": 42})
            assert status == 201
            match_id = created["match_id"]
            _, view = _request(base, f"/matches/{match_id}/view?player_id=1")
            _, actions = _request(base, f"/matches/{match_id}/actions?player_id=1")
            action = next(a for a in actions if a["type"] == "collect_resources")
            _, result = _request(base, f"/matches/{match_id}/actions", "POST", action)
            _, events = _request(base, f"/matches/{match_id}/events")
            assert view["active_player_id"] == 1
            assert result["success"] is True
            assert events[-1]["type"] == "resources_collected"
            private = {"type": "artifact_obtained", "turn": 1, "phase": "day",
                       "data": {"card_id": "K_H"},
                       "visibility": {"kind": "private", "player_ids": [1]}}
            server.MATCHES[match_id]["events"].append(private)
            _, owner_events = _request(base, f"/matches/{match_id}/events?player_id=1")
            _, rival_events = _request(base, f"/matches/{match_id}/events?player_id=2")
            assert private in owner_events and private not in rival_events
            assert (Path(tmp) / f"{match_id}.json").is_file()
            status, mime, icon = _raw(base, "/assets/visual-direction-v0.2/icons/people-humanos-32.svg")
            assert status == 200 and mime == "image/svg+xml" and b"<svg" in icon
        finally:
            httpd.shutdown()
            server.SAVES = old_saves


def test_http_dream_preview_privacy_and_no_state_or_save_mutation():
    from jessica.core.models import Hero
    from jessica.core.serialize import state_to_dict
    with tempfile.TemporaryDirectory() as tmp:
        old_saves = server.SAVES
        server.SAVES = Path(tmp)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            _, created = _request(base, "/matches", "POST", {"seed": 72})
            match_id = created["match_id"]
            state = server.MATCHES[match_id]["state"]
            p = state.players[0]
            p.people = "fadas"
            p.chosen_hero_id = "luna"
            p.hand = ["J_D", "K_S"]
            p.units = [Hero(id="luna", owner_id=1, house="center", life=2, life_max=2, hero_id="luna")]
            before = state_to_dict(state)
            initial_events = list(server.MATCHES[match_id]["events"])
            save = (Path(tmp) / f"{match_id}.json").read_bytes()
            route = f"/matches/{match_id}/dream-preview"
            body = {"player_id": 1, "choice": {"flip_cards": ["J_D"],
                                                 "artifact_choices": [{"hero_id": "ainai"}]}}
            _, preview = _request(base, route, "POST", body)
            assert any(o["choice"]["artifact_choices"] == [{"unit_id": "p1_hero_extra_1"}]
                       for o in preview["options"])
            assert set(preview) == {"options"}
            body["player_id"] = 2
            assert _error_request(base, route, body)[0] == 422
            assert state_to_dict(state) == before
            assert (Path(tmp) / f"{match_id}.json").read_bytes() == save
            assert server.MATCHES[match_id]["events"] == initial_events
        finally:
            httpd.shutdown()
            server.SAVES = old_saves


def test_http_saves_list_snapshot_export_import_rng_and_validation():
    from copy import deepcopy
    from jessica.core.serialize import state_to_dict
    with tempfile.TemporaryDirectory() as tmp:
        old_saves = server.SAVES
        server.SAVES = Path(tmp)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            _, created = _request(base, "/matches", "POST", {"seed": 72})
            mid = created["match_id"]
            _, actions = _request(base, f"/matches/{mid}/actions?player_id=1")
            action = next(a for a in actions if a["type"] == "collect_resources")
            _request(base, f"/matches/{mid}/actions", "POST", action)
            _, saved = _request(base, f"/matches/{mid}/save", "POST", {"name": "Antes da noite"})
            sid = saved["save_id"]
            assert sid != mid
            snapshot_file = (Path(tmp) / f"{sid}.json").read_bytes()
            _, entries = _request(base, "/saves")
            manual = next(e for e in entries if e["save_id"] == sid)
            assert manual["name"] == "Antes da noite" and manual["kind"] == "manual"
            assert all("state" not in e and "events" not in e for e in entries)
            _, exported = _request(base, f"/matches/{mid}/export")
            _, imported = _request(base, "/matches/import", "POST", exported)
            twin_id = imported["match_id"]
            assert state_to_dict(server.MATCHES[mid]["state"]) == state_to_dict(server.MATCHES[twin_id]["state"])
            _, options = _request(base, f"/matches/{mid}/actions?player_id=1")
            end = next(a for a in options if a["type"] == "end_turn")
            _, first = _request(base, f"/matches/{mid}/actions", "POST", end)
            _, second = _request(base, f"/matches/{twin_id}/actions", "POST", end)
            assert first == second
            assert state_to_dict(server.MATCHES[mid]["state"]) == state_to_dict(server.MATCHES[twin_id]["state"])
            assert (Path(tmp) / f"{sid}.json").read_bytes() == snapshot_file
            _, loaded = _request(base, "/matches/load", "POST", {"save_id": sid})
            assert state_to_dict(server.MATCHES[loaded["match_id"]]["state"]) == exported["state"]
            before_ids = set(server.MATCHES)
            before_files = set(Path(tmp).glob("*.json"))
            wrong_version = dict(exported, version="save-future")
            assert _error_request(base, "/matches/import", wrong_version)[0] == 409
            corrupt = deepcopy(exported)
            corrupt["state"]["rng"]["state"] = "invalid"
            assert _error_request(base, "/matches/import", corrupt)[0] == 422
            assert _error_request(base, "/matches/load", {"save_id": "../outside"})[0] == 422
            assert set(server.MATCHES) == before_ids and set(Path(tmp).glob("*.json")) == before_files
            (Path(tmp) / "abcdef123456.json").write_text("invalid json", encoding="utf-8")
            _, entries = _request(base, "/saves")
            assert next(e for e in entries if e["save_id"] == "abcdef123456")["invalid"]
        finally:
            httpd.shutdown()
            server.SAVES = old_saves


def test_all_people_icons_and_map_template_exist():
    root = Path(__file__).resolve().parents[1] / "assets"
    files = ("humanos", "anoes", "orcs", "fadas", "vampiros", "lobisomens",
             "gigantes", "mortos-vivos", "filhos-floresta", "gnomos-duendes",
             "dragoes", "demonios")
    assert all((root / "visual-direction-v0.2" / "icons" / f"people-{name}-32.svg").is_file()
               for name in files)
    assert (root / "visual-direction-v0.1" / "map" / "minimap-template-cross-v0.1.svg").is_file()


def test_web_ui_expoe_area_privada_e_eventos_legiveis():
    root = Path(__file__).resolve().parents[1] / "jessica" / "web" / "static"
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    assert 'id="self"' in html
    assert 'id="handoff"' in html
    assert "function eventText" in js
    assert 'className = "action-select"' in js
    assert "pendingPlayerId" in js


def test_catalogo_e_setup_completo_da_partida_web():
    old_saves = server.SAVES
    with tempfile.TemporaryDirectory() as tmp:
        server.SAVES = Path(tmp)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        players = [
            {"name": "Ana", "people": "vampiros", "hero_id": "dandara"},
            {"name": "Beto", "people": "mortos_vivos", "hero_id": ""},
            {"name": "Cris", "people": "dragoes", "hero_id": "purpura"},
            {"name": "Dani", "people": "demonios", "hero_id": "tuza"},
        ]
        try:
            _, catalog = _request(base, "/catalog")
            assert len(catalog["peoples"]) == 12
            assert all(len(people["heroes"]) == 3 for people in catalog["peoples"])
            status, created = _request(base, "/matches", "POST", {
                "seed": 91, "players": players,
                "config": {"city_life": 3, "city_life_max": 7, "gold": 2, "magic": 1},
            })
            assert status == 201
            _, view = _request(base, f'/matches/{created["match_id"]}/view?player_id=1')
            assert [(p["name"], p["people"]) for p in view["players"]] == [
                (item["name"], item["people"]) for item in players]
            assert view["players"][0]["city"]["life"] == 3
            invalid = [dict(item) for item in players]
            invalid[1]["people"] = "vampiros"
            code, error = _error_request(base, "/matches", {"players": invalid})
            assert code == 422 and "diferente" in error["error"]
        finally:
            httpd.shutdown()
            server.SAVES = old_saves


def run_all():
    tests = [test_http_vertical_action_view_events_and_autosave,
             test_http_dream_preview_privacy_and_no_state_or_save_mutation,
             test_http_saves_list_snapshot_export_import_rng_and_validation,
             test_all_people_icons_and_map_template_exist,
             test_web_ui_expoe_area_privada_e_eventos_legiveis,
             test_catalogo_e_setup_completo_da_partida_web]
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
