from contextlib import contextmanager
from http.client import HTTPConnection
from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.network import configure_transport, external_origin
from jessica.web import online_server
from test_online_rooms import http, request
from test_online_notifications import websocket_server, authenticate, connect, InvalidStatus
from test_online_persistence import free_port_pair, process_server

ORIGIN = "https://jessica.example:9443"


def rejected_origin(value):
    try:
        external_origin(value)
    except ValueError:
        return
    raise AssertionError(f"Origem indevida aceita: {value!r}")


def test_https_origin_validation_and_canonicalization():
    assert external_origin("https://JESSICA.example:443") == "https://jessica.example"
    assert external_origin(ORIGIN) == ORIGIN
    assert external_origin("https://localhost:9443") == "https://localhost:9443"
    assert external_origin("https://127.0.0.1") == "https://127.0.0.1"
    for value in (None, "", "http://jessica.example", "https://user@jessica.example",
                  "https://user:pass@jessica.example", "https://jessica.example/", "https://jessica.example/path",
                  "https://jessica.example?", "https://jessica.example#", "https://jessica.example:0",
                  "https://jessica.example:65536", "https://jessica.example:", "https://[::1]",
                  "https://bad..example", "https://-bad.example", "https://bad-.example",
                  "https://*.example", "https://bad_example", "https://999.999.999.999",
                  "https://jéssica.example", " https://jessica.example", "\x00https://jessica.example",
                  "https://jessica.example\x7f", "https://jessica.example\n", "https://" + "a" * 64 + ".example"):
        rejected_origin(value)


def test_transport_default_and_proxy_have_disjoint_trust():
    backend = SimpleNamespace(server_address=("127.0.0.1", 8767))
    configure_transport(backend)
    assert backend.allowed_hosts == {"localhost:8767", "127.0.0.1:8767"}
    assert backend.external_origin is None
    assert backend.notification_origins == ["http://127.0.0.1:8767", "http://localhost:8767"]
    configure_transport(backend, ORIGIN)
    assert backend.allowed_hosts == {"jessica.example:9443"}
    assert backend.notification_origins == [ORIGIN]
    assert backend.external_origin == ORIGIN
    backend.server_address = ("192.168.1.10", 8767)
    try:
        configure_transport(backend, ORIGIN)
    except ValueError:
        return
    raise AssertionError("Proxy permitido sobre interface LAN")


@contextmanager
def configured_http(origin=ORIGIN):
    old = online_server.ROOMS
    from jessica.web.rooms import Registry
    import threading
    online_server.ROOMS = Registry()
    listener = online_server.OnlineHTTPServer(("127.0.0.1", 0), online_server.Handler)
    configure_transport(listener, origin)
    thread = threading.Thread(target=listener.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{listener.server_port}"
    finally:
        listener.shutdown(); listener.server_close(); thread.join()
        online_server.ROOMS = old


def test_proxy_http_accepts_only_explicit_host_and_https_origin():
    headers = {"Host": urlsplit(ORIGIN).netloc, "Origin": ORIGIN}
    with configured_http() as base:
        status, created = request(base, "/rooms", {"name": "Ana"}, headers=headers)
        assert status == 201
        code, token = created["room"]["code"], created["credential"]
        room = online_server.ROOMS.get(code)
        before = room.record()
        route = f"/rooms/{code}"
        assert request(base, route, token=token, headers=headers)[0] == 200
        assert request(base, route, token=token, headers={"Host": urlsplit(ORIGIN).netloc})[0] == 200
        for extra in ({"Origin": "http://jessica.example:9443"}, {"Origin": "https://evil.example"},
                      {"Origin": "null"}, {"Host": "evil.example"}, {"Host": "127.0.0.1:8767"}):
            status, result = request(base, route, token=token, headers={**headers, **extra})
            assert status == 403 and "players" not in result
        spoofed = {"Host": "evil.example", "Origin": "https://evil.example",
                   "X-Forwarded-Host": urlsplit(ORIGIN).netloc, "X-Forwarded-Proto": "https", "Forwarded": "proto=https;host=jessica.example:9443"}
        assert request(base, "/rooms", {"name": "Invasor"}, headers=spoofed)[0] == 403
        assert request(base, "/rooms", {"name": "Invasor"}, headers={**headers, "Origin": "https://evil.example"})[0] == 403
        assert room.record() == before and len(online_server.ROOMS.rooms) == 1


def test_proxy_rejects_duplicate_origins_and_hosts():
    with configured_http() as base:
        for duplicate in ("Host", "Origin"):
            parsed = urlsplit(base)
            connection = HTTPConnection(parsed.hostname, parsed.port)
            try:
                connection.putrequest("GET", "/", skip_host=True)
                connection.putheader("Host", urlsplit(ORIGIN).netloc)
                connection.putheader("Origin", ORIGIN)
                connection.putheader(duplicate, urlsplit(ORIGIN).netloc if duplicate == "Host" else ORIGIN)
                connection.endheaders()
                response = connection.getresponse()
                assert response.status == 403
                assert "error" in json.loads(response.read())
            finally:
                connection.close()


def test_page_advertises_transport_without_secrets_or_state():
    for proxy in (False, True):
        with (configured_http() if proxy else http()) as base:
            parsed = urlsplit(base)
            connection = HTTPConnection(parsed.hostname, parsed.port)
            try:
                connection.request("GET", "/", headers={"Host": urlsplit(ORIGIN).netloc} if proxy else {})
                response = connection.getresponse()
                assert response.status == 200
                html = response.read().decode("utf-8")
                assert ('<meta id="onlineTransport" content="same-origin">' in html) == proxy
                assert "<script src=\"/static/online.js\">" in html
                assert ORIGIN not in html
                assert "room_seed" not in html and "credential_digest" not in html
            finally:
                connection.close()


def test_proxy_websocket_origin_remains_strict_and_identity_authenticated():
    with configured_http() as base:
        _, created = request(base, "/rooms", {"name": "Ana"}, headers={"Host": urlsplit(ORIGIN).netloc, "Origin": ORIGIN})
        with websocket_server(ORIGIN) as ws_url:
            with connect(ws_url, origin=ORIGIN, proxy=None) as ws:
                assert authenticate(ws, created["room"]["code"], created["credential"]) == 1
            for origin in (None, "http://jessica.example:9443", "https://evil.example", base):
                try:
                    with connect(ws_url, origin=origin, proxy=None):
                        raise AssertionError("Origem WS indevida aceita")
                except InvalidStatus as exc:
                    assert exc.response.status_code == 403


def test_cli_refuses_bad_origin_and_non_loopback_before_storage():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "must-not-create.sqlite3"
        for args in (("--external-origin", "http://jessica.example"),
                     ("--external-origin", ORIGIN, "--host", "192.168.1.10")):
            result = subprocess.run([sys.executable, "-B", "-m", "jessica.web.online_server", "--storage", str(path), *args],
                                    capture_output=True, text=True, timeout=10)
            assert result.returncode == 2 and not path.exists()


def test_real_cli_routes_http_and_ws_using_configured_origin():
    with TemporaryDirectory() as folder:
        path, port = Path(folder) / "rooms.sqlite3", free_port_pair()
        with process_server(path, port, extra_args=("--external-origin", ORIGIN)) as base:
            headers = {"Host": urlsplit(ORIGIN).netloc, "Origin": ORIGIN}
            assert request(base, "/catalog")[0] == 403
            status, created = request(base, "/rooms", {"name": "Ana"}, headers=headers)
            assert status == 201
            with connect(f"ws://127.0.0.1:{port + 1}/updates", origin=ORIGIN, proxy=None) as ws:
                assert authenticate(ws, created["room"]["code"], created["credential"]) == 1
            try:
                with connect(f"ws://127.0.0.1:{port + 1}/updates", origin=base, proxy=None):
                    raise AssertionError("CLI preservou origem HTTP no modo proxy")
            except InvalidStatus as exc:
                assert exc.response.status_code == 403
        assert path.exists()


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
