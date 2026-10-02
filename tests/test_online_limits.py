from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from http.client import HTTPConnection, RemoteDisconnected
import json
from pathlib import Path
import socket
import sys
import threading
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.online_limits import RequestLimits
from jessica.web.online_server import OnlineHTTPServer, Handler
from jessica.web.rooms import Registry, RoomError
from test_online_rooms import http, request
from test_online_persistence import store_at
from test_online_notifications import websocket_server, authenticate
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed


def test_rates_refill_independent_addresses_and_concurrent_budget():
    now = [0]
    limits = RequestLimits(clock=lambda: now[0])
    with ThreadPoolExecutor(max_workers=8) as pool:
        waits = list(pool.map(lambda _: limits.delay("one", "create"), range(20)))
    assert waits.count(0) == 8 and all(wait == 20 for wait in waits if wait)
    assert limits.delay("two", "create") == 0 and limits.delay("one") == 0
    now[0] = 20
    assert limits.delay("one", "create") == 0 and limits.delay("one", "create") == 20


def test_rate_memory_is_bounded_and_idle_keys_expire():
    now = [0]
    limits = RequestLimits(clock=lambda: now[0], max_keys=2)
    assert limits.delay("one") == limits.delay("two") == 0
    assert limits.delay("three") == 5 and len(limits.buckets) == 2
    now[0] = 601
    assert limits.delay("three") == 0 and len(limits.buckets) == 1


def test_api_overload_returns_retry_after_without_private_data_or_mutation():
    now = [0]
    limits = RequestLimits(clock=lambda: now[0])
    with patch("jessica.web.online_server.RequestLimits", return_value=limits), http() as base:
        _, created = request(base, "/rooms", {"name":"Ana"})
        token, code = created["credential"], created["room"]["code"]
        limits.buckets[("127.0.0.1", "api")] = (0, 0)
        try:
            urlopen(Request(base + f"/rooms/{code}", headers={"Authorization":f"Bearer {token}", "X-Forwarded-For":"untrusted"}))
            raise AssertionError("Orçamento excedido aceito")
        except HTTPError as response:
            assert response.code == 429 and int(response.headers["Retry-After"]) >= 1
            assert response.headers["Cache-Control"] == "no-store"
            assert set(json.load(response)) == {"error"}
        now[0] = 1
        assert request(base, f"/rooms/{code}", token=token)[1] == created["room"]


def test_creation_has_separate_budget_without_blocking_existing_players():
    now = [0]
    limits = RequestLimits(clock=lambda: now[0])
    with patch("jessica.web.online_server.RequestLimits", return_value=limits), http() as base:
        created = [request(base, "/rooms", {"name":f"Jogador {i}"}) for i in range(8)]
        assert all(status == 201 for status, _ in created)
        assert request(base, "/rooms", {"name":"Extra"})[0] == 429
        first = created[0][1]
        assert request(base, f"/rooms/{first['room']['code']}", token=first["credential"])[0] == 200
        now[0] = 20
        assert request(base, "/rooms", {"name":"Extra"})[0] == 201


def test_room_limit_preserves_existing_and_restores_over_limit_database():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store:
            registry = Registry(store, max_rooms=1)
            first = registry.create("Ana")
            before = store.load()
            try:
                registry.create("Beto")
                raise AssertionError("Limite de salas ignorado")
            except RoomError as exc:
                assert exc.status == 503
            assert store.load() == before
            assert registry.get(first["room"]["code"]).authenticate(first["credential"]).name == "Ana"
            registry.max_rooms = 2
            registry.create("Beto")
        with store_at(path) as store:
            registry = Registry(store, max_rooms=1)
            assert len(registry.rooms) == 2
            try:
                registry.create("Extra")
                raise AssertionError("Limite de salas ignorado após restaurar")
            except RoomError:
                pass
            assert len(store.load()) == 2


def test_ambiguous_deep_or_nonstandard_json_is_rejected_without_creating_rooms():
    from jessica.web import online_server
    with http() as base:
        for raw in ('{"name":"Ana","name":"Outra"}', '{"name":NaN}', '{"name":Infinity}', '[]', '{"name":' + '[' * 1100 + '0' + ']' * 1100 + '}'):
            try:
                urlopen(Request(base + "/rooms", data=raw.encode(), headers={"Content-Type":"application/json"}))
                raise AssertionError("JSON inválido aceito")
            except HTTPError as response:
                assert response.code == 422
                response.read()
        assert online_server.ROOMS.rooms == {}
        parsed = urlparse(base)
        for fields, expected in [([("Content-Length","0"),("Content-Length","0")],400),
                                 ([("Transfer-Encoding","chunked")],400),
                                 ([("Content-Length","-1")],400), ([("Content-Length","65537")],413)]:
            connection = HTTPConnection(parsed.hostname, parsed.port, timeout=3)
            try:
                connection.putrequest("POST", "/rooms")
                for key, value in fields:
                    connection.putheader(key, value)
                connection.endheaders()
                response = connection.getresponse()
                assert response.status == expected
                response.read()
            finally:
                connection.close()
        assert online_server.ROOMS.rooms == {}
        connection = HTTPConnection(parsed.hostname, parsed.port, timeout=3)
        try:
            connection.putrequest("POST", "/rooms")
            connection.putheader("Content-Length", "100")
            connection.endheaders()
            connection.send(b'{"name":"Ana"}')
            connection.sock.shutdown(socket.SHUT_WR)
            response = connection.getresponse()
            assert response.status == 400
            response.read()
        finally:
            connection.close()
        assert online_server.ROOMS.rooms == {}


def test_http_connection_cap_releases_slot_after_request_finishes():
    entered, release = threading.Event(), threading.Event()
    class Gate(Handler):
        def do_GET(self):
            entered.set()
            assert release.wait(3)
            self._json(200, {"ok":True})
    instance = OnlineHTTPServer(("127.0.0.1", 0), Gate, max_connections=1)
    worker = threading.Thread(target=instance.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{instance.server_port}"
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(request, base, "/one")
            assert entered.wait(2)
            try:
                request(base, "/extra")
                raise AssertionError("Segundo worker aceito")
            except (RemoteDisconnected, ConnectionError, OSError):
                pass
            finally:
                release.set()
            assert first.result(timeout=3)[0] == 200
        assert instance.slots.acquire(timeout=2)
        instance.slots.release()
        assert request(base, "/next")[0] == 200
    finally:
        release.set(); instance.shutdown(); instance.server_close(); worker.join()


def test_worker_start_failure_releases_reserved_slot():
    instance = OnlineHTTPServer(("127.0.0.1", 0), Handler, max_connections=1)
    try:
        with patch("jessica.web.server.ThreadingHTTPServer.process_request", side_effect=RuntimeError("Falha simulada")):
            try:
                instance.process_request(object(), ("127.0.0.1", 12345))
                raise AssertionError("Falha ignorada")
            except RuntimeError:
                pass
        assert instance.slots.acquire(blocking=False)
        instance.slots.release()
    finally:
        instance.server_close()


def test_websocket_cap_includes_unauthenticated_sessions():
    with http() as base, websocket_server(base, max_connections=2) as url, ExitStack() as stack:
        _, created = request(base, "/rooms", {"name":"Ana"})
        first = stack.enter_context(connect(url, origin=base))
        second = stack.enter_context(connect(url, origin=base))
        with connect(url, origin=base) as extra:
            try:
                extra.recv(timeout=2)
                raise AssertionError("Limite WS ignorado")
            except ConnectionClosed as exc:
                assert exc.rcvd.code == 1013
        first.close()
        assert authenticate(second, created["room"]["code"], created["credential"]) == 1
        with connect(url, origin=base) as renewed:
            assert authenticate(renewed, created["room"]["code"], created["credential"]) == 1


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
