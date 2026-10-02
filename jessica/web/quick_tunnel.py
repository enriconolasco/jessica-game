"""Piloto gratuito, sob demanda; nenhum serviço instalado ou iniciado ao importar."""
import argparse
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler
from .network import external_origin

ROOT = Path(__file__).resolve().parents[2]
URL_PATTERN = re.compile(r"https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com(?![a-z0-9.:-])")


def tunnel_origin(line):
    match = URL_PATTERN.search(line)
    return external_origin(match.group()) if match else None


def available_ports(port):
    if not 1024 <= port <= 65533:
        raise ValueError("Use --port entre 1024 e 65533 (reserva três portas locais).")
    sockets = []
    try:
        for value in range(port, port + 3):
            listener = socket.socket()
            sockets.append(listener)
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(("127.0.0.1", value))
    except OSError as exc:
        raise ValueError("Portas ocupadas. Mantenha o servidor atual e escolha outro trio com --port.") from exc
    finally:
        for listener in sockets:
            listener.close()


class Children:
    def __init__(self):
        self.processes = []
        self.readers = []
        self.origin = None
        self.lock = threading.Lock()

    def start(self, name, args, env):
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                 errors="replace", creationflags=flags)
        self.processes.append((name, child))
        def drain():
            for line in child.stdout:
                if name == "túnel":
                    origin = tunnel_origin(line)
                    if origin:
                        with self.lock:
                            self.origin = origin
        reader = threading.Thread(target=drain, daemon=True)
        self.readers.append(reader)
        reader.start()
        return child

    def check(self):
        for name, child in self.processes:
            if child.poll() is not None:
                raise RuntimeError(f"O processo {name} encerrou (código {child.returncode}).")

    def close(self):
        # Fecha primeiro o acesso externo, depois apenas os filhos deste iniciador.
        for name, child in self.processes:
            if child.poll() is None:
                try:
                    if name == "motor" and os.name == "nt":
                        child.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        child.terminate()
                    child.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=5)
        for reader in self.readers:
            reader.join(timeout=2)
        for _, child in self.processes:
            child.stdout.close()


def wait_ready(children, origin, port, timeout=30):
    deadline = time.monotonic() + timeout
    opener = build_opener(ProxyHandler({}))
    while time.monotonic() < deadline:
        children.check()
        try:
            req = Request(f"http://127.0.0.1:{port}/catalog", headers={"Host": origin.removeprefix("https://")})
            with opener.open(req, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Servidor/proxy não iniciou em 30 segundos. Nenhuma sala foi criada.")


def main():
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal.default_int_handler)
    parser = argparse.ArgumentParser(description="Piloto com amigos via túnel gratuito; PC precisa ficar ligado.")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--storage", type=Path, default=ROOT / "saves/online/rooms.sqlite3")
    args = parser.parse_args()
    tools = {}
    for name in ("cloudflared", "caddy"):
        portable = ROOT / "tools/runtime" / (name + (".exe" if os.name == "nt" else ""))
        tools[name] = str(portable) if portable.is_file() else shutil.which(name)
    missing = [name for name, path in tools.items() if not path]
    if missing:
        parser.error("Instale as ferramentas gratuitas no PATH: " + ", ".join(missing) + ". Veja docs/ONLINE_AMIGOS.md. Nada iniciado.")
    try:
        available_ports(args.port)
    except ValueError as exc:
        parser.error(str(exc))
    env = {key: value for key, value in os.environ.items() if not key.startswith("TUNNEL_")}
    env["PYTHONIOENCODING"] = "utf-8"
    children = Children()
    try:
        print("Iniciando túnel gratuito temporário. Compartilhe o link só com convidados.", flush=True)
        children.start("túnel", [tools["cloudflared"], "tunnel", "--config", str(ROOT / "deploy/cloudflared-quick.yml"),
                                 "--no-autoupdate", "--url", f"http://127.0.0.1:{args.port + 2}"], env)
        deadline = time.monotonic() + 30
        while children.origin is None and time.monotonic() < deadline:
            children.check()
            time.sleep(0.1)
        if children.origin is None:
            raise RuntimeError("Túnel não forneceu um link em 30 segundos. Confira sua conexão.")
        origin = children.origin
        env.update(JESSICA_TUNNEL_HOST=origin.removeprefix("https://"), JESSICA_HTTP_PORT=str(args.port),
                   JESSICA_WS_PORT=str(args.port + 1), JESSICA_PROXY_PORT=str(args.port + 2))
        config = str(ROOT / "deploy/Caddyfile.quick-tunnel")
        checked = subprocess.run([tools["caddy"], "validate", "--config", config, "--adapter", "caddyfile"],
                                 env=env, capture_output=True, timeout=10)
        if checked.returncode:
            raise RuntimeError("Caddy recusou a configuração local; não iniciou o motor.")
        children.start("motor", [sys.executable, "-u", "-m", "jessica.web.online_server", "--port", str(args.port),
                                 "--storage", str(args.storage.resolve()), "--external-origin", origin], env)
        wait_ready(children, origin, args.port)
        children.start("proxy", [tools["caddy"], "run", "--config", config, "--adapter", "caddyfile"], env)
        wait_ready(children, origin, args.port + 2)
        print(f"Abra no PC e nos celulares: {origin}\nCrie uma sala e compartilhe seu convite. Ctrl+C encerra este iniciador.", flush=True)
        print("Sem conta, domínio ou hospedagem paga. Mantenha o PC ligado; link muda ao reiniciar. HTTPS externo ainda precisa de playtest.", flush=True)
        while True:
            children.check()
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Erro: {exc} Nenhum outro servidor foi encerrado.", file=sys.stderr)
        return 1
    finally:
        children.close()


if __name__ == "__main__":
    raise SystemExit(main())
