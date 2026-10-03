from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
from unittest.mock import patch
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.room_store import RoomStore, StorageError
from jessica.web.rooms import Registry
from jessica.core.serialize import state_to_dict
from test_online_rooms import http, request, started, envelope


@contextmanager
def store_at(path):
    store = RoomStore(path)
    try:
        yield store
    finally:
        store.close()


def test_lobby_restart_and_only_hashed_credentials_on_disk():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store:
            registry = Registry(store)
            created = registry.create("Ana")
            token, code = created["credential"], created["room"]["code"]
            room = registry.get(code)
            with room.lock:
                member = room.authenticate(token)
                room.select(member, "humanos")
                room.mark_ready(member, True)
            before = room.public(member)
            assert token not in json.dumps(store.load())
            with http(registry) as base:
                with urlopen(base + "/") as response:
                    html = response.read().decode("utf-8")
                assert "Salas e ações aceitas são salvas no servidor" in html
                assert "Persistência não confirmada" not in html
                for route in ("/saves/online/rooms.sqlite3", "/static/../../saves/online/rooms.sqlite3"):
                    assert request(base, route, token=token)[0] >= 400
        with store_at(path) as store:
            room = Registry(store).get(code)
            member = room.authenticate(token)
            assert room.public(member) == before
            assert not room.listeners


def test_restart_preserves_state_rng_views_events_and_next_turns():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store, http(Registry(store)) as base:
            code, tokens, room = started(base)
            command = envelope(base, code, tokens[0])
            assert request(base, f"/rooms/{code}/actions", command, tokens[0])[0] == 200
            before = room.record()
            snapshots = [room.snapshot(room.authenticate(t)) for t in tokens]
        with store_at(path) as store:
            restored = Registry(store).get(code)
            assert restored.record() == before
            assert [restored.snapshot(restored.authenticate(t)) for t in tokens] == snapshots
            for index in range(50):
                if room.match["state"].turn >= 3:
                    break
                pid, actions = next((m.player_id, room.snapshot(m)["actions"]) for m in room.members if room.snapshot(m)["actions"])
                action = next((a for kind in ("end_turn", "night_pass", "night_window_done", "finish_night")
                               for a in actions if a["type"] == kind), actions[0])
                command = {"revision": room.revision, "command_id": f"next-{index}", "action": action}
                room.store = None
                assert room.apply(room.members[pid - 1], command) == restored.apply(restored.members[pid - 1], command)
                assert state_to_dict(room.match["state"]) == state_to_dict(restored.match["state"])
            assert room.match["state"].turn == 3


def test_concurrent_command_and_retry_after_restart_are_not_duplicated():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store, http(Registry(store)) as base:
            code, tokens, room = started(base)
            command = envelope(base, code, tokens[0])
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(lambda _: request(base, f"/rooms/{code}/actions", command, tokens[0]), range(2)))
            assert responses[0] == responses[1] and responses[0][0] == 200
            before = room.record()
        with store_at(path) as store, http(Registry(store)) as base:
            assert request(base, f"/rooms/{code}/actions", command, tokens[0]) == responses[0]
            from jessica.web import online_server
            assert online_server.ROOMS.get(code).record() == before
            assert len(before["commands"]) == 1


def test_storage_failure_does_not_change_state_rng_revision_or_notify():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store, http(Registry(store)) as base:
        code, tokens, room = started(base)
        command = envelope(base, code, tokens[0])
        before, disk, updates = room.record(), store.load(), []
        room.listeners.add(updates.append)
        with patch.object(store, "save", side_effect=StorageError("disk full")):
            assert request(base, f"/rooms/{code}/actions", command, tokens[0])[0] == 503
        assert room.record() == before and store.load() == disk and updates == []
        assert request(base, f"/rooms/{code}/actions", command, tokens[0])[0] == 200
        assert updates == [before["revision"] + 1]


def test_failed_lobby_write_is_atomic_and_creation_is_not_published():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store:
        registry = Registry(store)
        created = registry.create("Ana")
        room = registry.get(created["room"]["code"])
        member = room.authenticate(created["credential"])
        before, disk = room.record(), store.load()
        with patch.object(store, "save", side_effect=StorageError("disk full")):
            for operation in (lambda: room.select(member, "humanos"), lambda: room.join("Beto"), lambda: registry.create("Cris")):
                try:
                    operation()
                    raise AssertionError("Falha de gravação ignorada")
                except ValueError as exc:
                    assert exc.status == 503
        assert room.record() == before and store.load() == disk and len(registry.rooms) == 1


def test_damaged_or_future_database_is_preserved_and_refused():
    for mode in ("version", "payload", "schema"):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "rooms.sqlite3"
            with store_at(path) as store:
                Registry(store).create("Ana")
            with closing(sqlite3.connect(path)) as connection, connection:
                if mode == "version":
                    connection.execute("PRAGMA user_version=99")
                elif mode == "payload":
                    connection.execute("UPDATE rooms SET payload='{}'")
                else:
                    connection.execute("DROP TABLE rooms")
            before = path.read_bytes()
            try:
                with store_at(path) as store:
                    Registry(store)
                raise AssertionError("Banco inválido aceito")
            except StorageError:
                pass
            assert path.read_bytes() == before


def test_database_has_only_one_owner_and_releases_after_close():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path):
            try:
                with store_at(path):
                    raise AssertionError("Dois servidores no mesmo banco")
            except StorageError:
                pass
        with store_at(path):
            pass


def test_pending_armor_decision_and_private_view_survive_restart():
    from test_night_web import night
    from jessica.core import night_actions
    from jessica.core.models import Troop
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store, http(Registry(store)) as base:
            code, tokens, room = started(base)
            state = night()
            state.seed = room.seed
            for pid in (1, 2):
                player = state.players[pid - 1]
                player.units = [Troop(id=f"u{pid}", owner_id=pid, house="center", life=4, life_max=4)]
                player.armor_active_until_turn, player.city.gold = state.turn, 8
            state.players[1].hand = ["PENA"]
            night_actions.prepare(state)
            room.match = {"state": state, "events": []}
            command = envelope(base, code, tokens[0], "night_attack", "attack")
            assert request(base, f"/rooms/{code}/actions", command, tokens[0])[1]["pending"]
            before = room.record()
        with store_at(path) as store, http(Registry(store)) as base:
            _, attacker = request(base, f"/rooms/{code}/snapshot", token=tokens[0])
            assert attacker["actions"] == [] and "PENA" not in json.dumps(attacker)
            defense = envelope(base, code, tokens[1], "armor_payment", "defense")
            assert request(base, f"/rooms/{code}/actions", defense, tokens[0])[0] == 403
            assert request(base, f"/rooms/{code}/actions", defense, tokens[1])[0] == 200
            assert before["match"]["state"]["web_reaction"]


def test_finished_match_and_result_are_restored():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store, http(Registry(store)) as base:
            code, _, room = started(base)
            room.match["state"].game_over = True
            room.match["state"].winner_id = 1
            room._commit()
            before = room.record()
        with store_at(path) as store:
            room = Registry(store).get(code)
            assert room.record() == before and room.match["state"].winner_id == 1


def free_port_pair():
    for _ in range(20):
        with socket.socket() as http_socket, socket.socket() as ws_socket:
            http_socket.bind(("127.0.0.1", 0))
            port = http_socket.getsockname()[1]
            if port == 65535:
                continue
            try:
                ws_socket.bind(("127.0.0.1", port + 1))
                return port
            except OSError:
                continue
    raise AssertionError("Sem portas de teste")


@contextmanager
def process_server(path, port, host="127.0.0.1", extra_args=()):
    process = subprocess.Popen([sys.executable, "-u", "-B", "-m", "jessica.web.online_server", "--port", str(port), "--storage", str(path), "--host", host, *extra_args],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    ready, lines = threading.Event(), []

    def output():
        for line in process.stdout:
            lines.append(line)
            if "WebSocket" in line:
                ready.set()

    reader = threading.Thread(target=output, daemon=True)
    reader.start()
    try:
        assert ready.wait(10) and process.poll() is None, "Servidor de teste não iniciou"
        yield f"http://{host}:{port}"
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        reader.join(timeout=5)
        process.stdout.close()


def test_process_crash_and_restart_preserves_accepted_command():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        port = free_port_pair()
        with process_server(path, port) as base:
            from test_online_rooms import lobby, prepare
            code, tokens = lobby(base)
            prepare(base, code, tokens, [("humanos", "miyamoto"), ("anoes", "ori"), ("orcs", "arken"), ("fadas", "luna")])
            assert request(base, f"/rooms/{code}/start", {}, tokens[0])[0] == 200
            command = envelope(base, code, tokens[0])
            result = request(base, f"/rooms/{code}/actions", command, tokens[0])
            assert result[0] == 200
            before = request(base, f"/rooms/{code}/snapshot", token=tokens[0])[1]
        with process_server(path, port) as base:
            assert request(base, f"/rooms/{code}/snapshot", token=tokens[0])[1] == before
            assert request(base, f"/rooms/{code}/actions", command, tokens[0]) == result
            assert request(base, f"/rooms/{code}/snapshot", token=tokens[0])[1] == before


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
