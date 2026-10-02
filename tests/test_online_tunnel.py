from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web import quick_tunnel as tunnel


def test_only_cloudflare_https_origins_are_extracted():
    assert tunnel.tunnel_origin("| https://one-two-three.trycloudflare.com |") == "https://one-two-three.trycloudflare.com"
    for line in ("http://one.trycloudflare.com", "https://evil.example", "https://one.trycloudflare.com.evil.example",
                 "https://one.trycloudflare.com:444", "https://user@one.trycloudflare.com", "https://one.trycloudflare.com-extra"):
        assert tunnel.tunnel_origin(line) is None


def test_invalid_and_occupied_ports_preserve_existing_listener():
    for port in (0, 1023, 65534, 65535):
        try:
            tunnel.available_ports(port)
            raise AssertionError("Porta inválida aceita")
        except ValueError:
            pass
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); listener.listen()
        port = listener.getsockname()[1]
        try:
            tunnel.available_ports(port)
            raise AssertionError("Porta ocupada aceita")
        except ValueError:
            pass
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            pass


def test_missing_tools_never_start_or_install_anything():
    with TemporaryDirectory() as folder, patch.object(tunnel, "ROOT", Path(folder)), patch.object(tunnel.shutil, "which", return_value=None), \
         patch.object(sys, "argv", ["quick_tunnel"]), patch.object(tunnel.subprocess, "Popen") as spawn, redirect_stderr(StringIO()):
        try:
            tunnel.main()
            raise AssertionError("Dependências ausentes ignoradas")
        except SystemExit as exc:
            assert exc.code == 2
        spawn.assert_not_called()
        assert list(Path(folder).iterdir()) == []


def test_port_conflict_is_checked_before_opening_tunnel():
    with patch.object(tunnel.shutil, "which", return_value="tool"), patch.object(tunnel, "available_ports", side_effect=ValueError("ocupada")), \
         patch.object(sys, "argv", ["quick_tunnel"]), patch.object(tunnel.subprocess, "Popen") as spawn, redirect_stderr(StringIO()):
        try:
            tunnel.main()
            raise AssertionError("Porta ocupada ignorada")
        except SystemExit as exc:
            assert exc.code == 2
        spawn.assert_not_called()


class FakeChildren:
    def __init__(self):
        self.origin = None
        self.started = []
        self.closed = False

    def start(self, name, args, env):
        self.started.append((name, args, env.copy()))
        if name == "túnel":
            self.origin = "https://one-two.trycloudflare.com"

    def check(self):
        if len(self.started) == 3:
            raise KeyboardInterrupt()

    def close(self):
        self.closed = True


def run_mocked_launcher(validation=0):
    children = FakeChildren()
    with patch.object(tunnel, "Children", return_value=children), patch.object(tunnel.shutil, "which", return_value="tool"), \
         patch.object(tunnel, "available_ports"), patch.object(tunnel, "wait_ready") as ready, \
         patch.object(tunnel.subprocess, "run", return_value=SimpleNamespace(returncode=validation)), \
         patch.dict(os.environ, {"TUNNEL_TOKEN": "must-not-use"}), patch.object(sys, "argv", ["quick_tunnel", "--port", "8877"]), \
         redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        result = tunnel.main()
    return result, children, ready


def test_launcher_uses_one_origin_same_port_proxy_and_owned_cleanup():
    result, children, ready = run_mocked_launcher()
    assert result == 0 and children.closed
    assert [name for name, _, _ in children.started] == ["túnel", "motor", "proxy"]
    _, cloud, cloud_env = children.started[0]
    assert "--no-autoupdate" in cloud and "--config" in cloud
    assert cloud[-1] == "http://127.0.0.1:8879" and "TUNNEL_TOKEN" not in cloud_env
    _, engine, env = children.started[1]
    assert engine[engine.index("--external-origin") + 1] == children.origin
    assert env["JESSICA_TUNNEL_HOST"] == "one-two.trycloudflare.com"
    assert env["JESSICA_HTTP_PORT"] == "8877" and env["JESSICA_WS_PORT"] == "8878"
    assert env["JESSICA_PROXY_PORT"] == "8879" and ready.call_count == 2
    config = (tunnel.ROOT / "deploy/Caddyfile.quick-tunnel").read_text()
    assert "bind 127.0.0.1" in config and "admin off" in config and "auto_https off" in config
    assert "@tunnel host" in config and "handle /updates" in config
    assert "tls internal" not in config and "header_up Host" not in config
    assert 'JOGAR.cmd amigos' in (tunnel.ROOT / "JOGAR_AMIGOS.cmd").read_text()


def test_proxy_validation_failure_stops_tunnel_without_starting_engine():
    result, children, ready = run_mocked_launcher(validation=1)
    assert result == 1 and children.closed
    assert [name for name, _, _ in children.started] == ["túnel"]
    ready.assert_not_called()


def test_launcher_routes_shutdown_signals_through_cleanup():
    with patch.object(tunnel.signal, "signal") as handler:
        result, children, _ = run_mocked_launcher()
        assert result == 0 and children.closed
        handler.assert_any_call(tunnel.signal.SIGTERM, tunnel.signal.default_int_handler)
        if hasattr(tunnel.signal, "SIGBREAK"):
            handler.assert_any_call(tunnel.signal.SIGBREAK, tunnel.signal.default_int_handler)


def test_owned_processes_are_stopped_and_unrelated_process_survives():
    outsider = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    children = tunnel.Children()
    try:
        owned = children.start("túnel", [sys.executable, "-u", "-c",
                               "import time; print('https://one-two.trycloudflare.com', flush=True); time.sleep(30)"], os.environ.copy())
        deadline = time.monotonic() + 3
        while children.origin is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert children.origin == "https://one-two.trycloudflare.com"
        children.check()
        children.close()
        assert owned.poll() is not None and outsider.poll() is None
    finally:
        children.close()
        outsider.terminate(); outsider.wait(timeout=5)


def test_startup_timeout_has_bounded_wait_without_remote_requests():
    children = FakeChildren()
    opener = SimpleNamespace(open=lambda *a, **kw: (_ for _ in ()).throw(OSError("não pronto")))
    with patch.object(tunnel, "build_opener", return_value=opener), \
         patch.object(tunnel.time, "monotonic", side_effect=[0, 0.1, 31]), patch.object(tunnel.time, "sleep"):
        try:
            tunnel.wait_ready(children, "https://one.trycloudflare.com", 8767)
            raise AssertionError("Espera sem prazo")
        except RuntimeError:
            pass


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
