from http.client import HTTPConnection
import json
from pathlib import Path
import subprocess
import socket
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.request import Request, ProxyHandler, build_opener
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.network import valid_host, local_addresses, choose_local_address, allowed_hosts, allowed_origins
from test_online_rooms import http, started, request, envelope
from test_online_persistence import process_server, free_port_pair


def test_only_specific_loopback_or_rfc1918_ipv4_are_allowed():
    for host in ("127.0.0.1", "127.0.0.2", "10.1.2.3", "172.16.0.1", "172.31.255.254", "192.168.1.10"):
        assert valid_host(host) == host
    for host in ("0.0.0.0", "8.8.8.8", "172.32.0.1", "169.254.1.1", "224.0.0.1", "::1", "example.com", "192.168.1.1:8767"):
        try:
            valid_host(host)
            raise AssertionError("Endereço indevido aceito")
        except ValueError:
            pass


def test_discovery_filters_public_link_local_and_duplicate_addresses():
    addresses = ("192.168.1.10", "192.168.1.10", "127.0.0.1", "169.254.1.1", "8.8.8.8", "10.0.0.2")
    entries = [(None, None, None, None, (address, 0)) for address in addresses]
    with patch("jessica.web.network.socket.getaddrinfo", return_value=entries):
        assert local_addresses() == ["10.0.0.2", "192.168.1.10"]


def test_selection_default_cancel_invalid_and_empty_network():
    with patch("jessica.web.network.local_addresses", return_value=["192.168.1.10"]), patch("builtins.print"):
        with patch("builtins.input", return_value=""):
            assert choose_local_address() == "192.168.1.10"
        for answer in ("0", "2", "invalid"):
            with patch("builtins.input", return_value=answer):
                try:
                    choose_local_address()
                    raise AssertionError("Escolha inválida aceita")
                except ValueError:
                    pass
    with patch("jessica.web.network.local_addresses", return_value=[]):
        try:
            choose_local_address()
            raise AssertionError("Rede ausente aceita")
        except ValueError:
            pass


def test_hosts_and_origins_are_explicit_without_wildcards():
    assert allowed_hosts("192.168.1.10", 8767) == {"192.168.1.10:8767"}
    assert allowed_origins("192.168.1.10", 8767) == ["http://192.168.1.10:8767"]
    assert allowed_hosts("127.0.0.1", 8767) == {"127.0.0.1:8767", "localhost:8767"}
    assert allowed_origins("192.168.1.10", 80) == ["http://192.168.1.10"]
    assert "192.168.1.10" in allowed_hosts("192.168.1.10", 80)


def test_http_rejects_untrusted_host_origin_and_duplicate_host():
    with http() as base:
        code, tokens, room = started(base)
        before = room.record()
        route = f"/rooms/{code}/snapshot"
        for headers in ({"Host":"untrusted.example"}, {"Origin":"http://untrusted.example"}, {"Origin":"null"}):
            status, response = request(base, route, token=tokens[0], headers=headers)
            assert status == 403 and "view" not in response
        command = envelope(base, code, tokens[0])
        assert request(base, f"/rooms/{code}/actions", command, tokens[0], headers={"Host":"untrusted.example"})[0] == 403
        for _ in range(20):
            assert request(base, f"/rooms/{code}/actions", command, tokens[0], headers={"Origin":"http://untrusted.example"})[0] == 403
        assert request(base, route, token=tokens[0], headers={"Origin":base})[0] == 200
        parsed = urlparse(base)
        connection = HTTPConnection(parsed.hostname, parsed.port)
        try:
            connection.putrequest("GET", route, skip_host=True)
            connection.putheader("Host", parsed.netloc)
            connection.putheader("Host", "untrusted.example")
            connection.endheaders()
            response = connection.getresponse()
            assert response.status == 403 and "view" not in json.loads(response.read())
        finally:
            connection.close()
        assert room.record() == before


def test_public_binding_is_refused_before_creating_storage():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "must-not-create.sqlite3"
        for host in ("0.0.0.0", "8.8.8.8", "example.com"):
            result = subprocess.run([sys.executable, "-B", "-m", "jessica.web.online_server", "--host", host, "--storage", str(path)],
                                    capture_output=True, text=True, timeout=10)
            assert result.returncode == 2 and not path.exists()


def test_real_server_binds_only_the_selected_loopback_interface():
    from websockets.sync.client import connect
    opener = build_opener(ProxyHandler({}))
    with TemporaryDirectory() as folder, process_server(Path(folder) / "rooms.sqlite3", free_port_pair(), "127.0.0.2") as base:
        with opener.open(Request(base + "/rooms", data=b'{"name":"Ana"}', headers={"Content-Type":"application/json"}), timeout=5) as response:
            created = json.load(response)
        assert created["room"]["you"] == 1
        parsed = urlparse(base)
        try:
            with socket.create_connection(("127.0.0.1", parsed.port), timeout=0.5):
                raise AssertionError("Servidor escutando em outra interface")
        except OSError:
            pass
        with connect(f"ws://{parsed.hostname}:{parsed.port + 1}/updates", origin=base, proxy=None) as ws:
            ws.send(json.dumps({"version":1, "code":created["room"]["code"], "credential":created["credential"]}))
            assert json.loads(ws.recv(timeout=2))["revision"] == 1


def test_launchers_keep_local_default_and_add_explicit_lan_mode():
    launcher = Path("JOGAR.cmd").read_text()
    assert 'if /i "%~1"=="rede" goto online' in launcher
    assert 'if /i "%~1"=="rede" goto rede' in launcher
    assert '-m jessica.web.online_server --lan' in launcher
    assert '-m jessica.main' in launcher and '-m jessica.web.server' in launcher
    assert 'JOGAR.cmd" rede' in Path("JOGAR_REDE_LOCAL.cmd").read_text()


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
