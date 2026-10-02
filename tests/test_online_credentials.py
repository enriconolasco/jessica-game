from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.rooms import Registry
from jessica.web.room_store import StorageError
from test_online_rooms import http, request, started, envelope
from test_online_persistence import store_at
from test_online_notifications import websocket_server, authenticate
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

NEW = "a1" * 32


def test_rotation_keeps_identity_state_and_deduplicated_commands():
    with http() as base:
        code, tokens, room = started(base)
        command = envelope(base, code, tokens[0])
        result = request(base, f"/rooms/{code}/actions", command, tokens[0])
        before = deepcopy(room.record())
        status, rotated = request(base, f"/rooms/{code}/credential", {"credential":NEW}, tokens[0])
        assert status == 200 and rotated["you"] == 1 and rotated["revision"] == before["revision"] + 1
        assert NEW not in json.dumps(rotated) and NEW not in json.dumps(room.record())
        for key in ("seed", "match", "commands"):
            assert room.record()[key] == before[key]
        assert request(base, f"/rooms/{code}/snapshot", token=tokens[0])[0] == 403
        assert request(base, f"/rooms/{code}/actions", command, tokens[0])[0] == 403
        assert request(base, f"/rooms/{code}/snapshot", token=NEW)[1]["player_id"] == 1
        assert request(base, f"/rooms/{code}/actions", command, NEW) == result
        assert request(base, f"/rooms/{code}/snapshot", token=tokens[1])[1]["player_id"] == 2
        revision = room.revision
        assert request(base, f"/rooms/{code}/credential", {"credential":NEW}, NEW)[0] == 200
        assert room.revision == revision


def test_rotation_requires_authentication_exact_parameters_and_unique_token():
    with http() as base:
        code, tokens, room = started(base)
        before = deepcopy(room.record())
        for token, body, expected in [(None,{"credential":NEW},401), ("wrong",{"credential":NEW},403),
                (tokens[0],{"credential":"short"},422), (tokens[0],{"credential":None},422),
                (tokens[0],{"credential":NEW,"player_id":2},422), (tokens[0],{},422)]:
            assert request(base, f"/rooms/{code}/credential", body, token)[0] == expected
        assert room.record() == before
        assert request(base, f"/rooms/{code}/credential", {"credential":NEW}, tokens[1])[0] == 200
        before = deepcopy(room.record())
        assert request(base, f"/rooms/{code}/credential", {"credential":NEW}, tokens[0])[0] == 422
        assert room.record() == before
        assert request(base, f"/rooms/{code}", token=NEW)[1]["you"] == 2


def test_concurrent_rotations_accept_only_one_old_credential_request():
    with http() as base:
        code, tokens, room = started(base)
        revision = room.revision
        candidates = [NEW, "b2" * 32]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda token: request(base, f"/rooms/{code}/credential", {"credential":token}, tokens[0]), candidates))
        assert sorted(status for status, _ in results) == [200, 403]
        assert room.revision == revision + 1
        for candidate, (status, _) in zip(candidates, results):
            assert request(base, f"/rooms/{code}", token=candidate)[0] == (200 if status == 200 else 403)


def test_storage_failure_leaves_old_access_valid_and_candidate_uncommitted():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store, http(Registry(store)) as base:
        code, tokens, room = started(base)
        before = deepcopy(room.record())
        with patch.object(store, "save", side_effect=StorageError("Falha simulada")):
            assert request(base, f"/rooms/{code}/credential", {"credential":NEW}, tokens[0])[0] == 503
        assert room.record() == before and store.load()[0] == before
        assert request(base, f"/rooms/{code}", token=tokens[0])[0] == 200
        assert request(base, f"/rooms/{code}", token=NEW)[0] == 403


def test_rotation_survives_restart_and_backup_contains_only_hashes():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store, http(Registry(store)) as base:
            code, tokens, room = started(base)
            assert request(base, f"/rooms/{code}/credential", {"credential":NEW}, tokens[0])[0] == 200
            before = deepcopy(room.record())
            backup, _ = store.backup()
        for source in (path, backup):
            with store_at(source) as store, http(Registry(store)) as base:
                assert request(base, f"/rooms/{code}", token=tokens[0])[0] == 403
                assert request(base, f"/rooms/{code}/snapshot", token=NEW)[1]["player_id"] == 1
                assert store.load()[0] == before and NEW not in json.dumps(store.load())


def test_active_old_websocket_is_closed_and_other_player_stays_connected():
    with http() as base, websocket_server(base) as url:
        code, tokens, room = started(base)
        with connect(url, origin=base) as old, connect(url, origin=base) as unaffected:
            authenticate(old, code, tokens[0]); authenticate(unaffected, code, tokens[1])
            assert request(base, f"/rooms/{code}/credential", {"credential":NEW}, tokens[0])[0] == 200
            try:
                old.recv(timeout=2)
                raise AssertionError("Canal revogado permaneceu conectado")
            except ConnectionClosed as exc:
                assert exc.rcvd.code == 1008
            assert json.loads(unaffected.recv(timeout=2))["revision"] == room.revision
            with connect(url, origin=base) as renewed:
                assert authenticate(renewed, code, NEW) == room.revision
            with connect(url, origin=base) as rejected:
                rejected.send(json.dumps({"version":1,"code":code,"credential":tokens[0]}))
                try:
                    rejected.recv(timeout=2)
                    raise AssertionError("Reconexão revogada foi aceita")
                except ConnectionClosed as exc:
                    assert exc.rcvd.code == 1008


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
