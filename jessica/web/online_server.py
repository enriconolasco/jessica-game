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
            return self._json(200, {"mode": "online-api-prototype", "version": 1,
                "message": "API de salas em teste; interface online ainda não disponível."})
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
                else:
                    raise RoomError(422, "Operação ou parâmetros inválidos.")
                return self._json(200, result)
        except RoomError as exc:
            return self._json(exc.status, {"error": str(exc)})
        except (UnicodeError, ValueError, TypeError):
            return self._json(422, {"error": "Conteúdo da requisição inválido."})


def main():
    address = ("127.0.0.1", 8767)
    print(f"Jéssica online API (protótipo): http://{address[0]}:{address[1]}")
    server.ThreadingHTTPServer(address, Handler).serve_forever()


if __name__ == "__main__":
    main()
