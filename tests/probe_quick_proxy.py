"""Integração opcional com Caddy real, somente loopback; nunca abre túnel externo."""
from contextlib import ExitStack
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.quick_tunnel import ROOT, available_ports, wait_ready, Children
from test_online_persistence import free_port_pair, process_server
from test_online_rooms import request
from test_online_notifications import connect, authenticate, InvalidStatus


def main():
    caddy = ROOT / "tools/runtime/caddy.exe"
    if not caddy.is_file():
        raise RuntimeError("Probe requer tools/runtime/caddy.exe; não instala nem baixa automaticamente.")
    for _ in range(10):
        port = free_port_pair()
        try:
            available_ports(port)
            break
        except ValueError:
            continue
    else:
        raise RuntimeError("Sem trio de portas local livre")
    origin = "https://pilot.trycloudflare.com"
    headers = {"Host": "pilot.trycloudflare.com", "Origin": origin}
    env = {**os.environ, "JESSICA_TUNNEL_HOST": "pilot.trycloudflare.com", "JESSICA_HTTP_PORT": str(port),
           "JESSICA_WS_PORT": str(port + 1), "JESSICA_PROXY_PORT": str(port + 2)}
    config = str(ROOT / "deploy/Caddyfile.quick-tunnel")
    checked = subprocess.run([str(caddy), "validate", "--config", config, "--adapter", "caddyfile"], env=env,
                             capture_output=True, timeout=10)
    assert checked.returncode == 0, "Configuração Caddy inválida"
    with TemporaryDirectory() as folder, process_server(Path(folder) / "rooms.sqlite3", port,
                                                       extra_args=("--external-origin", origin)):
        children = Children()
        try:
            children.start("proxy", [str(caddy), "run", "--config", config, "--adapter", "caddyfile"], env)
            wait_ready(children, origin, port + 2)
            base = f"http://127.0.0.1:{port + 2}"
            connection = HTTPConnection("127.0.0.1", port + 2)
            try:
                connection.request("GET", "/catalog")
                response = connection.getresponse()
                assert response.status == 403
                response.read()
            finally:
                connection.close()
            assert request(base, "/catalog", headers={**headers, "Origin": "https://evil.example"})[0] == 403
            _, created = request(base, "/rooms", {"name": "Ana"}, headers=headers)
            code, tokens = created["room"]["code"], [created["credential"]]
            for name in ("Beto", "Cris", "Dani"):
                status, joined = request(base, f"/rooms/{code}/join", {"name": name}, headers=headers)
                assert status == 201
                tokens.append(joined["credential"])
            for token, (people, hero) in zip(tokens, [("humanos", "miyamoto"), ("anoes", "ori"), ("orcs", "arken"), ("fadas", "luna")]):
                assert request(base, f"/rooms/{code}/select", {"people": people, "hero_id": hero}, token, headers)[0] == 200
                assert request(base, f"/rooms/{code}/ready", {"ready": True}, token, headers)[0] == 200
            assert request(base, f"/rooms/{code}/start", {}, tokens[0], headers)[0] == 200
            with ExitStack() as stack:
                channels = []
                for token in tokens:
                    sock = stack.enter_context(socket.create_connection(("127.0.0.1", port + 2), timeout=3))
                    channel = stack.enter_context(connect("ws://pilot.trycloudflare.com/updates", sock=sock, origin=origin, proxy=None))
                    channels.append(channel)
                    authenticate(channel, code, token)
                _, snapshot = request(base, f"/rooms/{code}/snapshot", token=tokens[0], headers=headers)
                action = next(a for a in snapshot["actions"] if a["type"] == "collect_resources")
                command = {"revision": snapshot["revision"], "command_id": "proxy-collect", "action": action}
                assert request(base, f"/rooms/{code}/actions", command, tokens[1], headers)[0] == 403
                status, applied = request(base, f"/rooms/{code}/actions", command, tokens[0], headers)
                assert status == 200 and applied["success"]
                for channel in channels:
                    packet = json.loads(channel.recv(timeout=3))
                    assert set(packet) == {"type", "version", "revision"} and packet["revision"] == applied["revision"]
                assert request(base, f"/rooms/{code}/actions", command, tokens[0], headers)[1] == applied
                for index, token in enumerate(tokens, 1):
                    status, view = request(base, f"/rooms/{code}/snapshot", token=token, headers=headers)
                    assert status == 200 and view["player_id"] == index and view["revision"] == applied["revision"]
            try:
                with socket.create_connection(("127.0.0.1", port + 2), timeout=3) as sock:
                    with connect("ws://pilot.trycloudflare.com/updates", sock=sock, origin="https://evil.example", proxy=None):
                        raise AssertionError("Origem WS externa indevida aceita")
            except InvalidStatus as exc:
                assert exc.response.status_code == 403
        finally:
            children.close()
    print("Proxy Caddy real: quatro sessões HTTP/WS, origem restrita, ação/deduplicação e visões individuais aprovadas. Sem túnel/TLS externo.")


if __name__ == "__main__":
    main()
