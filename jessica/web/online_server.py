"""API online isolada: não expõe endpoints administrativos do hotseat."""
from urllib.parse import urlparse
from . import server
from .rooms import Registry, RoomError

ROOMS = Registry()


class Handler(server.Handler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _credential(self):
        authorization = self.headers.get("Authorization", "")
        return authorization[7:] if authorization.startswith("Bearer ") else None

    def do_GET(self):
        parts = self._parts()
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
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://{self.headers.get('Host')}", f"https://{self.headers.get('Host')}"):
                raise RoomError(403, "Origem da requisição não permitida.")
            if urlparse(self.path).query:
                raise RoomError(422, "Parâmetros não são aceitos na URL.")
            if not 0 <= int(self.headers.get("Content-Length", "0")) <= 65536:
                raise RoomError(413, "Comando excede o limite de 64 KB.")
            parts, body = self._parts(), self._body()
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
        except (UnicodeError, ValueError, TypeError):
            return self._json(422, {"error": "Conteúdo da requisição inválido."})


def main():
    global ROOMS
    import argparse
    import asyncio
    import threading
    from .notifications import serve_notifications
    from .room_store import RoomStore, StorageError
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767, help="Porta HTTP; WebSocket usa a próxima porta.")
    parser.add_argument("--storage", type=Path, default=server.ASSETS.parent / "saves" / "online" / "rooms.sqlite3",
                        help="Banco privado do servidor; não é um save enviado pelo jogador.")
    args = parser.parse_args()
    port = args.port
    if not 1 <= port <= 65534:
        parser.error("Use uma porta entre 1 e 65534.")
    address = ("127.0.0.1", port)

    class OnlineHTTPServer(server.ThreadingHTTPServer):
        allow_reuse_address = False

    store = None
    try:
        store = RoomStore(args.storage)
        ROOMS = Registry(store)
    except StorageError as exc:
        if store:
            store.close()
        parser.error(str(exc))
    try:
        httpd = OnlineHTTPServer(address, Handler)
    except OSError:
        store.close()
        parser.error("Porta HTTP indisponível. Mantenha o servidor atual ou escolha outra com --port.")

    async def run():
        async with serve_notifications(ROOMS, "127.0.0.1", port + 1,
                                       [f"http://127.0.0.1:{port}", f"http://localhost:{port}"]):
            print(f"Jéssica online (protótipo): http://{address[0]}:{address[1]} · WebSocket {port + 1}", flush=True)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                await asyncio.Future()
            finally:
                httpd.shutdown()
                thread.join()

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
