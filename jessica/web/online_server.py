"""API online isolada: não expõe endpoints administrativos do hotseat."""
from urllib.parse import urlparse
from . import server
from .rooms import Registry, RoomError
from .network import allowed_hosts, allowed_origins
from .online_limits import RequestLimits
import json
import re
import threading

ROOMS = Registry()


class OnlineHTTPServer(server.ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = False
    request_queue_size = 32

    def __init__(self, address, handler, max_connections=64):
        self.slots = threading.BoundedSemaphore(max_connections)
        self.limits = RequestLimits()
        super().__init__(address, handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


class Handler(server.Handler):
    timeout = 15
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _credential(self):
        authorization = self.headers.get("Authorization", "")
        return authorization[7:] if authorization.startswith("Bearer ") else None

    def _limited(self, category="api"):
        wait = self.server.limits.delay(self.client_address[0], category)
        if not wait:
            return False
        self.send_response(429)
        self.send_header("Retry-After", str(wait))
        payload = json.dumps({"error": "Servidor ocupado. Aguarde e reenvie o mesmo comando pendente."}).encode()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        return True

    def _body(self):
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get_all("Transfer-Encoding") or len(lengths) > 1:
            raise RoomError(400, "Enquadramento da requisição inválido.")
        raw_length = lengths[0] if lengths else "0"
        if not re.fullmatch(r"[0-9]{1,8}", raw_length):
            raise RoomError(400, "Tamanho da requisição inválido.")
        length = int(raw_length)
        if length > 65536:
            raise RoomError(413, "Comando excede o limite de 64 KB.")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Campo JSON duplicado")
                result[key] = value
            return result
        def invalid_number(_):
            raise ValueError("Número JSON inválido")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise RoomError(400, "Corpo da requisição incompleto.")
        body = json.loads(raw or b"{}", object_pairs_hook=unique, parse_constant=invalid_number)
        if not isinstance(body, dict):
            raise ValueError("Comando precisa ser um objeto")
        return body

    def _check_address(self):
        hosts = self.headers.get_all("Host", [])
        accepted = getattr(self.server, "allowed_hosts", None)
        if accepted is None:
            accepted = allowed_hosts(*self.server.server_address[:2])
        if len(hosts) != 1 or hosts[0].lower() not in accepted:
            self._json(403, {"error": "Endereço do servidor não permitido."})
            return False
        origins = self.headers.get_all("Origin", [])
        if len(origins) > 1 or origins and origins[0] != f"http://{hosts[0].lower()}":
            self._json(403, {"error": "Origem da requisição não permitida."})
            return False
        return True

    def do_GET(self):
        if not self._check_address():
            return
        parts = self._parts()
        if parts and parts[0] not in ("assets", "static") and self._limited():
            return
        if not parts:
            page = server.STATIC.joinpath("index.html").read_text(encoding="utf-8")
            lobby = server.STATIC.joinpath("online_lobby.html").read_text(encoding="utf-8")
            if ROOMS.store:
                lobby = lobby.replace("Persistência não confirmada nesta instância. Não reinicie durante a partida.",
                                      "Salas e ações aceitas são salvas no servidor e retomadas após reiniciar.")
            page = page.replace("<main>", "<main>" + lobby).replace("<span>Partida local</span>", "<span>Sala online · experimental</span>")
            page = page.replace('<section id="start" class="card">', '<section id="start" class="card" hidden>')
            page = page.replace('<script src="/static/presentation.js">', '<script src="/static/online.js"></script><script src="/static/presentation.js">')
            payload = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            return self.wfile.write(payload)
        if parts == ["catalog"] or (parts and parts[0] in ("assets", "static")):
            return super().do_GET()
        try:
            if urlparse(self.path).query:
                raise RoomError(422, "Identidade e credencial não são aceitas na URL.")
            if len(parts) not in (2, 3) or parts[0] != "rooms":
                raise RoomError(404, "Rota online não encontrada.")
            room = ROOMS.get(parts[1])
            with room.lock:
                member = room.authenticate(self._credential())
                if len(parts) == 2:
                    return self._json(200, room.public(member))
                if parts[2] != "snapshot":
                    raise RoomError(404, "Rota online não encontrada.")
                return self._json(200, room.snapshot(member))
        except RoomError as exc:
            return self._json(exc.status, {"error": str(exc)})

    def do_POST(self):
        try:
            if urlparse(self.path).query:
                raise RoomError(422, "Parâmetros não são aceitos na URL.")
            parts, body = self._parts(), self._body()
            if not self._check_address():
                return
            if self._limited() or parts == ["rooms"] and self._limited("create"):
                return
            if parts == ["rooms"]:
                if set(body) != {"name"}:
                    raise RoomError(422, "Informe apenas o nome.")
                return self._json(201, ROOMS.create(body["name"]))
            if len(parts) != 3 or parts[0] != "rooms":
                raise RoomError(404, "Rota online não encontrada.")
            room = ROOMS.get(parts[1])
            with room.lock:
                operation = parts[2]
                if operation == "join":
                    if set(body) != {"name"}:
                        raise RoomError(422, "Informe apenas o nome.")
                    return self._json(201, room.join(body["name"]))
                member = room.authenticate(self._credential())
                if operation == "select" and set(body) == {"people", "hero_id"}:
                    result = room.select(member, body["people"], body["hero_id"])
                elif operation == "ready" and set(body) == {"ready"}:
                    result = room.mark_ready(member, body["ready"])
                elif operation == "start" and not body:
                    result = room.start(member)
                elif operation == "credential" and set(body) == {"credential"}:
                    result = room.rotate_credential(member, body["credential"])
                elif operation == "actions":
                    result = room.apply(member, body)
                    return self._json(200 if result["success"] else 422, result)
                elif operation == "dream-preview" and set(body) == {"player_id", "choice"}:
                    from ..core.headless import legal_actions
                    from ..core.interaction_actions import dream_preview
                    if type(body["player_id"]) is not int or body["player_id"] != member.player_id:
                        raise RoomError(403, "Não é permitido consultar escolhas de outro jogador.")
                    if not room.match or not any(a["type"] == "dream_multi" for a in legal_actions(room.match["state"], member.player_id)):
                        raise RoomError(422, "Sonho Lúcido indisponível.")
                    result = dream_preview(room.match["state"], member.player_id, body["choice"])
                else:
                    raise RoomError(422, "Operação ou parâmetros inválidos.")
                return self._json(200, result)
        except RoomError as exc:
            return self._json(exc.status, {"error": str(exc)})
        except (UnicodeError, ValueError, TypeError, RecursionError):
            return self._json(422, {"error": "Conteúdo da requisição inválido."})


def main():
    global ROOMS
    import argparse
    import asyncio
    import threading
    from .notifications import serve_notifications
    from .room_store import RoomStore, StorageError
    from pathlib import Path
    from .network import choose_local_address, valid_host
    from .online_backups import OnlineBackups

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767, help="Porta HTTP; WebSocket usa a próxima porta.")
    binding = parser.add_mutually_exclusive_group()
    binding.add_argument("--host", default="127.0.0.1", help="IPv4 específico de loopback ou rede privada.")
    binding.add_argument("--lan", action="store_true", help="Escolher interativamente o IPv4 privado do PC.")
    parser.add_argument("--storage", type=Path, default=server.ASSETS.parent / "saves" / "online" / "rooms.sqlite3",
                        help="Banco privado do servidor; não é um save enviado pelo jogador.")
    parser.add_argument("--max-connections", type=int, default=64, help="Máximo de conexões HTTP simultâneas.")
    parser.add_argument("--max-rooms", type=int, default=256, help="Máximo de salas guardadas; não apaga salas existentes.")
    args = parser.parse_args()
    port = args.port
    if not 1 <= port <= 65534:
        parser.error("Use uma porta entre 1 e 65534.")
    if not 1 <= args.max_connections <= 1024 or not 1 <= args.max_rooms <= 10000:
        parser.error("Use 1–1024 conexões e 1–10000 salas.")
    try:
        host = choose_local_address() if args.lan else valid_host(args.host)
    except (ValueError, OSError, EOFError) as exc:
        parser.error(str(exc))
    address = (host, port)

    store = None
    try:
        store = RoomStore(args.storage)
        ROOMS = Registry(store, max_rooms=args.max_rooms)
    except StorageError as exc:
        if store:
            store.close()
        parser.error(str(exc))
    try:
        httpd = OnlineHTTPServer(address, Handler, args.max_connections)
        httpd.allowed_hosts = allowed_hosts(host, port)
    except OSError:
        store.close()
        parser.error("IP/porta HTTP indisponíveis. Confira o IP local, mantenha o servidor atual ou escolha outra porta com --port.")

    async def run():
        async with serve_notifications(ROOMS, host, port + 1, allowed_origins(host, port)):
            backups = OnlineBackups(store)
            await asyncio.to_thread(backups.checkpoint)
            async def backup_loop():
                while True:
                    await asyncio.sleep(60)
                    await asyncio.to_thread(backups.checkpoint)
            backup_task = asyncio.create_task(backup_loop())
            print(f"Jéssica online (protótipo): http://{address[0]}:{address[1]} · WebSocket {port + 1}", flush=True)
            print(f"Backups automáticos privados: {store.path.parent / 'backups'} (a cada hora com mudanças).", flush=True)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                await asyncio.Future()
            finally:
                httpd.shutdown()
                thread.join()
                httpd.server_close()
                backup_task.cancel()
                try:
                    await backup_task
                except asyncio.CancelledError:
                    pass
                await asyncio.to_thread(backups.checkpoint, force=True)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except OSError:
        parser.error("Porta WebSocket indisponível. Escolha outro par de portas com --port.")
    finally:
        httpd.server_close()
        store.close()


if __name__ == "__main__":
    main()
