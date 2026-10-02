"""Probe opt-in: abre e encerra um túnel gratuito, somente com sala/banco fictícios."""
import json
from pathlib import Path
from queue import Queue, Empty
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
from urllib.request import build_opener, ProxyHandler, Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.quick_tunnel import available_ports
from test_online_persistence import free_port_pair
from test_online_notifications import connect, authenticate


def main():
    if not hasattr(signal, "CTRL_BREAK_EVENT"):
        raise RuntimeError("Este probe de encerramento requer Windows.")
    for _ in range(10):
        port = free_port_pair()
        try:
            available_ports(port)
            break
        except ValueError:
            continue
    else:
        raise RuntimeError("Sem trio de portas livre")
    with TemporaryDirectory(prefix="jessica-free-tunnel-check-") as folder:
        process = subprocess.Popen([sys.executable, "-u", "-B", "-m", "jessica.web.quick_tunnel", "--port", str(port),
                                    "--storage", str(Path(folder) / "rooms.sqlite3")], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        messages = Queue()
        def read():
            for line in process.stdout:
                messages.put(line)
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            origin = None
            deadline = time.monotonic() + 45
            while origin is None and time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Iniciador encerrou antes do link")
                try:
                    line = messages.get(timeout=1)
                except Empty:
                    continue
                if line.startswith("Abra no PC e nos celulares: "):
                    origin = line.split(": ", 1)[1].strip()
            assert origin, "Sem link no prazo"
            opener = build_opener(ProxyHandler({}))
            req = Request(origin + "/rooms", data=b'{"name":"Probe temporario"}',
                          headers={"Content-Type": "application/json", "Origin": origin})
            for attempt in range(8):
                try:
                    with opener.open(req, timeout=5) as response:
                        assert response.status == 201
                        created = json.load(response)
                    break
                except OSError:
                    if attempt == 7:
                        raise
                    time.sleep(1)
            code, token = created["room"]["code"], created["credential"]
            with connect(origin.replace("https:", "wss:") + "/updates", origin=origin, proxy=None, open_timeout=10) as ws:
                assert authenticate(ws, code, token) == 1
            req = Request(origin + "/rooms/" + code, headers={"Origin": origin, "Authorization": "Bearer " + token})
            with opener.open(req, timeout=5) as response:
                assert json.load(response)["you"] == 1
        finally:
            if process.poll() is None:
                process.send_signal(signal.CTRL_BREAK_EVENT)
                process.wait(timeout=25)
            reader.join(timeout=2)
            process.stdout.close()
            assert process.returncode == 0, "Iniciador não encerrou normalmente"
            for value in range(port, port + 3):
                try:
                    with __import__("socket").create_connection(("127.0.0.1", value), timeout=0.2):
                        raise AssertionError("Processo filho continuou escutando após encerrar")
                except OSError:
                    pass
    print("Túnel HTTPS/WSS gratuito aprovado; sala temporária encerrada, três portas liberadas e banco de teste removido.")


if __name__ == "__main__":
    main()
