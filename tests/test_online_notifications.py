import asyncio
from contextlib import contextmanager, ExitStack
import json
from pathlib import Path
from queue import Queue
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus
from jessica.web import online_server
from jessica.web.notifications import serve_notifications
from test_online_rooms import http, started, request, envelope


@contextmanager
def websocket_server(base):
    ready = Queue()
    loop = asyncio.new_event_loop()

    async def run():
        async with serve_notifications(online_server.ROOMS, "127.0.0.1", 0, [base]) as listener:
            ready.put((listener.sockets[0].getsockname()[1], asyncio.current_task()))
            await asyncio.Future()

    def worker():
        try:
            loop.run_until_complete(run())
        except asyncio.CancelledError:
            pass
        finally:
            loop.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    port, task = ready.get(timeout=5)
    try:
        yield f"ws://127.0.0.1:{port}/updates"
    finally:
        loop.call_soon_threadsafe(task.cancel)
        thread.join(timeout=5)
        assert not thread.is_alive()


def authenticate(socket, code, token):
    socket.send(json.dumps({"version": 1, "code": code, "credential": token}))
    packet = json.loads(socket.recv(timeout=2))
    assert set(packet) == {"type", "version", "revision"}
    assert packet["type"] == "room_changed" and packet["version"] == 1
    return packet["revision"]


def no_update(socket):
    try:
        socket.recv(timeout=0.1)
    except TimeoutError:
        return
    raise AssertionError("Revisão indevida foi enviada")


def test_four_sessions_updates_deduplication_and_failed_action():
    with http() as base, websocket_server(base) as url, ExitStack() as stack:
        code, tokens, room = started(base)
        clients = [stack.enter_context(connect(url, origin=base)) for _ in tokens]
        assert [authenticate(ws, code, token) for ws, token in zip(clients, tokens)] == [room.revision] * 4
        command = envelope(base, code, tokens[0])
        status, result = request(base, f"/rooms/{code}/actions", command, tokens[0])
        assert status == 200
        for ws in clients:
            assert json.loads(ws.recv(timeout=2)) == {"type": "room_changed", "version": 1, "revision": result["revision"]}
        assert request(base, f"/rooms/{code}/actions", command, tokens[0])[1] == result
        for ws in clients:
            no_update(ws)
        bad = {**command, "command_id": "invalid", "revision": room.revision,
               "action": {"type": "move_unit", "version": 1, "player_id": 1, "params": {}}}
        assert request(base, f"/rooms/{code}/actions", bad, tokens[0])[0] == 422
        no_update(clients[0])


def test_lobby_push_and_rooms_are_isolated():
    with http() as base, websocket_server(base) as url:
        _, first = request(base, "/rooms", {"name": "Ana"})
        _, other = request(base, "/rooms", {"name": "Outra"})
        code = first["room"]["code"]
        with connect(url, origin=base) as own, connect(url, origin=base) as isolated:
            authenticate(own, code, first["credential"])
            authenticate(isolated, other["room"]["code"], other["credential"])
            assert request(base, f"/rooms/{code}/join", {"name": "Beto"})[0] == 201
            assert json.loads(own.recv(timeout=2))["revision"] == 2
            no_update(isolated)


def test_reconnect_has_current_revision_and_same_identity():
    with http() as base, websocket_server(base) as url:
        code, tokens, room = started(base)
        with connect(url, origin=base) as ws:
            authenticate(ws, code, tokens[1])
        command = envelope(base, code, tokens[0])
        assert request(base, f"/rooms/{code}/actions", command, tokens[0])[0] == 200
        with connect(url, origin=base) as ws:
            assert authenticate(ws, code, tokens[1]) == room.revision
            assert request(base, f"/rooms/{code}/snapshot", token=tokens[1])[1]["player_id"] == 2


def test_credentials_and_actions_cannot_use_websocket():
    with http() as base, websocket_server(base) as url:
        code, tokens, room = started(base)
        for route, auth in [(url, {"version": 1, "code": code, "credential": "wrong"}),
                            (url + "?credential=" + tokens[0], {}), (url, {"version": True, "code": code, "credential": tokens[0]})]:
            with connect(route, origin=base) as ws:
                try:
                    ws.send(json.dumps(auth))
                    ws.recv(timeout=2)
                    raise AssertionError("Credencial/protocolo inválido aceito")
                except ConnectionClosed as exc:
                    assert exc.rcvd.code == 1008
        with connect(url, origin=base) as ws:
            authenticate(ws, code, tokens[0])
            ws.send(json.dumps({"type": "end_turn"}))
            try:
                ws.recv(timeout=2)
                raise AssertionError("Ação por WebSocket aceita")
            except ConnectionClosed as exc:
                assert exc.rcvd.code == 1008
        assert request(base, f"/rooms/{code}/snapshot", token=tokens[0])[1]["revision"] == room.revision
    assert not room.listeners


def test_origin_is_checked_before_authentication():
    with http() as base, websocket_server(base) as url:
        try:
            with connect(url, origin="https://untrusted.example"):
                raise AssertionError("Origem externa aceita")
        except InvalidStatus as exc:
            assert exc.response.status_code == 403


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
