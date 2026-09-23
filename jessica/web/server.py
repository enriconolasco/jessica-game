from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..core.headless import SAVE_VERSION, apply_action, legal_actions, view_for_player
from ..core.serialize import state_from_dict, state_to_dict
from ..core.setup import run_setup
from ..core.turn import start_player_day, start_turn


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
SAVES = ROOT.parent.parent / "saves" / "web"
MATCHES: dict[str, dict] = {}
LOCK = threading.RLock()


def _new_state(seed: int):
    peoples = ["humanos", "anoes", "orcs", "fadas"]
    heroes = {"humanos": ["miyamoto"], "anoes": ["ori"],
              "orcs": ["arken"], "fadas": ["ainai"]}
    choices = {i + 1: {"povo": people, "heroi": heroes[people][0]}
               for i, people in enumerate(peoples)}
    state, _ = run_setup(peoples, heroes, choices, seed, turn_order=[1, 2, 3, 4])
    start_turn(state)
    state.active_player_id = state.curuna_id
    start_player_day(state, state.active_player_id)
    return state


def _save(match_id: str) -> str:
    SAVES.mkdir(parents=True, exist_ok=True)
    payload = {"version": SAVE_VERSION, "state": state_to_dict(MATCHES[match_id]["state"])}
    path = SAVES / f"{match_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.name


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _parts(self):
        return [p for p in urlparse(self.path).path.split("/") if p]

    def do_GET(self):
        parts = self._parts()
        if not parts:
            return self._file("index.html", "text/html; charset=utf-8")
        if parts[0] == "static" and len(parts) == 2:
            mime = "text/css" if parts[1].endswith(".css") else "text/javascript"
            return self._file(parts[1], mime)
        if len(parts) == 3 and parts[0] == "matches":
            match_id, resource = parts[1], parts[2]
            with LOCK:
                match = MATCHES.get(match_id)
                if not match:
                    return self._json(404, {"error": "Partida não encontrada."})
                state = match["state"]
                query = parse_qs(urlparse(self.path).query)
                player_id = int(query.get("player_id", [state.active_player_id or 1])[0])
                if resource == "view":
                    return self._json(200, view_for_player(state, player_id))
                if resource == "actions":
                    return self._json(200, legal_actions(state, player_id))
                if resource == "events":
                    return self._json(200, match["events"])
        self._json(404, {"error": "Rota não encontrada."})

    def do_POST(self):
        parts = self._parts()
        body = self._body()
        with LOCK:
            if parts == ["matches"]:
                match_id = uuid.uuid4().hex[:12]
                MATCHES[match_id] = {"state": _new_state(int(body.get("seed", 20260923))),
                                     "events": []}
                _save(match_id)
                return self._json(201, {"match_id": match_id})
            if parts == ["matches", "load"]:
                save_id = str(body.get("save_id", ""))
                path = SAVES / f"{Path(save_id).stem}.json"
                if not path.is_file():
                    return self._json(404, {"error": "Save não encontrado."})
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("version") != SAVE_VERSION:
                    return self._json(409, {"error": "Versão de save incompatível."})
                match_id = uuid.uuid4().hex[:12]
                MATCHES[match_id] = {"state": state_from_dict(payload["state"]), "events": []}
                return self._json(201, {"match_id": match_id})
            if len(parts) == 3 and parts[0] == "matches":
                match_id, resource = parts[1], parts[2]
                match = MATCHES.get(match_id)
                if not match:
                    return self._json(404, {"error": "Partida não encontrada."})
                if resource == "actions":
                    result = apply_action(match["state"], body)
                    if result["success"]:
                        match["events"].extend(result["events"])
                        _save(match_id)
                    return self._json(200 if result["success"] else 422, result)
                if resource == "save":
                    return self._json(200, {"save_id": Path(_save(match_id)).stem,
                                            "version": SAVE_VERSION})
        self._json(404, {"error": "Rota não encontrada."})

    def _file(self, name: str, mime: str) -> None:
        path = STATIC / name
        if not path.is_file():
            return self._json(404, {"error": "Arquivo não encontrado."})
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, _format, *args):
        return


def main() -> None:
    address = ("127.0.0.1", 8765)
    print(f"Jéssica web: http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, Handler).serve_forever()


if __name__ == "__main__":
    main()
