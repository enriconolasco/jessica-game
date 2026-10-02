import json
from pathlib import Path
import sys
import threading
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web import online_server, server
from jessica.web.rooms import Registry
from jessica.core.serialize import state_to_dict


@contextmanager
def http(registry=None):
    old = online_server.ROOMS
    online_server.ROOMS = registry if registry is not None else Registry()
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), online_server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with patch("jessica.web.rooms.secrets.randbits", return_value=42):
            yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join()
        online_server.ROOMS = old


def request(base, path, body=None, token=None, headers=None):
    hdr = {"Content-Type": "application/json", **(headers or {})}
    if token:
        hdr["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = Request(base + path, data=data, headers=hdr)
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        assert response.headers.get("Cache-Control") == "no-store"
        return response.status, json.load(response)


def lobby(base):
    status, created = request(base, "/rooms", {"name": "Ana"})
    assert status == 201
    code = created["room"]["code"]
    tokens = [created["credential"]]
    for name in ("Beto", "Cris", "Dani"):
        status, joined = request(base, f"/rooms/{code}/join", {"name": name})
        assert status == 201
        tokens.append(joined["credential"])
    assert len(set(tokens)) == 4
    return code, tokens


def started(base):
    code, tokens = lobby(base)
    for token, (people, hero) in zip(tokens, [("humanos", "miyamoto"), ("anoes", "ori"),
                                           ("orcs", "arken"), ("fadas", "luna")]):
        assert request(base, f"/rooms/{code}/select", {"people": people, "hero_id": hero}, token)[0] == 200
        assert request(base, f"/rooms/{code}/ready", {"ready": True}, token)[0] == 200
    assert request(base, f"/rooms/{code}/start", {}, tokens[0])[0] == 200
    return code, tokens, online_server.ROOMS.get(code)


def envelope(base, code, token, kind="collect_resources", command_id="command1"):
    status, snapshot = request(base, f"/rooms/{code}/snapshot", token=token)
    assert status == 200
    action = next(a for a in snapshot["actions"] if a["type"] == kind)
    return {"command_id": command_id, "revision": snapshot["revision"], "action": action}


def test_lobby_four_unique_sessions_and_host_start():
    with http() as base:
        code, tokens = lobby(base)
        assert request(base, "/rooms", {"name": "Seed conhecida", "seed": 42})[0] == 422
        route = f"/rooms/{code}"
        assert request(base, route)[0] == 401
        assert request(base, route + "/join", {"name": "Quinto"})[0] == 409
        assert request(base, route + "/start", {}, tokens[1])[0] == 403
        assert request(base, route + "/start", {}, tokens[0])[0] == 409
        for pid, token in enumerate(tokens, 1):
            status, public = request(base, route, token=token)
            assert status == 200 and public["you"] == pid
            serialized = json.dumps(public)
            assert all(t not in serialized for t in tokens)
            assert "credential_hash" not in serialized
            assert "seed" not in public
        assert request(base, route + "/select", {"people": "humanos", "hero_id": "miyamoto"}, tokens[0])[0] == 200
        assert request(base, route + "/select", {"people": "humanos", "hero_id": "besouro"}, tokens[1])[0] == 409
        assert request(base, route + "/select", {"people": "filhos_floresta", "hero_id": "ent"}, tokens[1])[0] == 422
        assert request(base, route + "/ready", {"ready": True}, tokens[0])[0] == 200
        assert request(base, route + "/select", {"people": "orcs", "hero_id": "arken"}, tokens[0])[0] == 409


def test_private_view_events_and_cross_room_credentials():
    with http() as base:
        code, tokens, room = started(base)
        room.match["state"].players[1].hand = ["PENA"]
        room.match["events"].append({"type": "test_private", "data": {"secret": "only-p2"},
            "visibility": {"kind": "private", "player_ids": [2]}})
        for pid, token in enumerate(tokens, 1):
            status, data = request(base, f"/rooms/{code}/snapshot", token=token)
            assert status == 200 and data["player_id"] == pid
            assert ("PENA" in json.dumps(data)) == (pid == 2)
            assert ("only-p2" in json.dumps(data)) == (pid == 2)
        _, other = request(base, "/rooms", {"name": "Outro"})
        assert request(base, f"/rooms/{code}/snapshot", token=other["credential"])[0] == 403
        assert request(base, f"/rooms/{code}/snapshot?player_id=2", token=tokens[0])[0] == 422


def test_impersonation_invalid_action_and_out_of_turn_preserve_state():
    with http() as base:
        code, tokens, room = started(base)
        route = f"/rooms/{code}/actions"
        command = envelope(base, code, tokens[0])
        before, revision = state_to_dict(room.match["state"]), room.revision
        command["action"]["player_id"] = 2
        assert request(base, route, command, tokens[0])[0] == 403
        command["action"]["player_id"] = 1
        assert request(base, route, command, tokens[1])[0] == 403
        command["action"]["player_id"] = 2
        assert request(base, route, command, tokens[1])[0] == 422
        command["action"]["player_id"] = 1
        command["action"]["params"] = {"gold": 9999, "magic": 2}
        assert request(base, route, command, tokens[0])[0] == 422
        assert state_to_dict(room.match["state"]) == before and room.revision == revision
        assert not room.commands


def test_idempotency_revision_conflicts_and_concurrent_requests():
    with http() as base:
        code, tokens, room = started(base)
        route = f"/rooms/{code}/actions"
        command = envelope(base, code, tokens[0])
        revision = room.revision
        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(lambda _: request(base, route, command, tokens[0]), range(2)))
        assert replies[0] == replies[1] and replies[0][0] == 200
        assert room.revision == revision + 1 and len(room.commands) == 1
        before = state_to_dict(room.match["state"])
        command["action"]["params"] = {"gold": 1, "magic": 1}
        assert request(base, route, command, tokens[0])[0] == 409
        command["command_id"] = "stale-other-id"
        assert request(base, route, command, tokens[0])[0] == 409
        assert state_to_dict(room.match["state"]) == before
        command = envelope(base, code, tokens[0], "end_turn", "end-day")
        assert request(base, route, command, tokens[0])[0] == 200
        assert request(base, f"/rooms/{code}/snapshot", token=tokens[0])[1]["actions"] == []
        status, own = request(base, f"/rooms/{code}/snapshot", token=tokens[1])
        assert status == 200 and own["view"]["active_player_id"] == 2 and own["actions"]


def test_hotseat_admin_routes_are_not_exposed():
    with http() as base:
        code, tokens, room = started(base)
        before = state_to_dict(room.match["state"])
        for path in ("/saves", "/matches/anything/export", "/matches/anything/view?player_id=2"):
            assert request(base, path, token=tokens[0])[0] >= 400
        for path in ("/matches", "/matches/import", "/matches/load", f"/rooms/{code}/system", f"/rooms/{code}/save"):
            assert request(base, path, {}, tokens[0])[0] >= 400
        assert request(base, f"/rooms/{code}/ready", {"ready": False}, tokens[0],
                       headers={"Origin": "https://untrusted.invalid"})[0] == 403
        assert state_to_dict(room.match["state"]) == before


def test_reconnect_with_same_credential_and_complete_day_night_cycle():
    with http() as base:
        code, tokens, room = started(base)
        for index in range(40):
            snapshots = [request(base, f"/rooms/{code}/snapshot", token=t)[1] for t in tokens]
            assert len({s["revision"] for s in snapshots}) == 1
            if room.match["state"].turn >= 2:
                break
            pid = next(i for i, s in enumerate(snapshots) if s["actions"])
            actions = snapshots[pid]["actions"]
            action = next((a for kind in ("end_turn", "night_pass", "night_window_done", "finish_night")
                           for a in actions if a["type"] == kind), actions[0])
            command = {"revision": snapshots[pid]["revision"], "command_id": f"cycle-{index}", "action": action}
            assert request(base, f"/rooms/{code}/actions", command, tokens[pid])[0] == 200
        assert room.match["state"].turn == 2
        _, restored = request(base, f"/rooms/{code}/snapshot", token=tokens[0])
        assert restored["player_id"] == 1 and restored["view"]["turn"] == 2


def test_armor_interrupt_belongs_to_defender_session():
    from test_night_web import night
    from jessica.core import night_actions
    from jessica.core.models import Troop
    with http() as base:
        code, tokens, room = started(base)
        state = night()
        for pid in (1, 2):
            player = state.players[pid - 1]
            player.units = [Troop(id=f"u{pid}", owner_id=pid, house="center", life=4, life_max=4)]
            player.armor_active_until_turn = state.turn
            player.city.gold = 8
        state.players[1].hand = ["PENA"]
        night_actions.prepare(state)
        room.match = {"state": state, "events": []}
        command = envelope(base, code, tokens[0], "night_attack", "attack")
        status, result = request(base, f"/rooms/{code}/actions", command, tokens[0])
        assert status == 200 and result["pending"] and "PENA" not in json.dumps(result)
        _, attacker = request(base, f"/rooms/{code}/snapshot", token=tokens[0])
        assert attacker["actions"] == [] and "PENA" not in json.dumps(attacker)
        defense = envelope(base, code, tokens[1], "armor_payment", "defense")
        assert request(base, f"/rooms/{code}/actions", defense, tokens[0])[0] == 403
        assert request(base, f"/rooms/{code}/actions", defense, tokens[1])[0] == 200


def test_online_page_uses_shared_client_but_not_local_setup():
    with http() as base:
        with urlopen(base + "/?room=ABCDEFG2") as response:
            html = response.read().decode("utf-8")
        assert 'id="onlineLobby"' in html and '/static/online.js' in html
        assert 'id="start" class="card" hidden' in html
        assert html.index('/static/online.js') < html.index('/static/app.js')
        assert '/static/presentation.js' in html
        with urlopen(base + "/static/online.js") as response:
            assert response.headers.get_content_type() == "text/javascript"
        local_html = server.STATIC.joinpath("index.html").read_text(encoding="utf-8")
        assert '/static/online.js' not in local_html


def test_dream_preview_authentication_turn_and_read_only_state():
    from jessica.core.models import Hero
    with http() as base:
        code, tokens, room = started(base)
        state = room.match["state"]
        player = state.players[0]
        player.people = "fadas"
        player.units = [Hero(id="luna", owner_id=1, hero_id="luna", house="city_1", life=2, life_max=2)]
        player.hand = ["Q_H"]
        before = state_to_dict(state)
        body = {"player_id":1, "choice":{"flip_cards":[], "artifact_choices":[]}}
        route = f"/rooms/{code}/dream-preview"
        assert request(base, route, body, tokens[1])[0] == 403
        status, result = request(base, route, body, tokens[0])
        assert status == 200 and result["options"]
        assert state_to_dict(state) == before


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test(); passed += 1
            except Exception as exc:
                failed += 1; print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(bool(failed))
