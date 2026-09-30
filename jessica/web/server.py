from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from . import saves

from ..core import heroes, spells
from ..core.constants import (DEFAULT_CITY_LIFE_MAX, DEFAULT_CITY_LIFE_START,
                              DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC)
from ..core.headless import SAVE_VERSION, apply_action, legal_actions, view_for_player
from ..core.serialize import state_from_dict, state_to_dict
from ..core.setup import run_setup
from ..core.turn import start_player_day, start_turn


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
ASSETS = ROOT.parent.parent / "assets"
SAVES = ROOT.parent.parent / "saves" / "web"
MATCHES: dict[str, dict] = {}
LOCK = threading.RLock()
PEOPLES = ("humanos", "anoes", "orcs", "fadas", "vampiros", "lobisomens",
           "gigantes", "mortos_vivos", "filhos_floresta", "gnomos_duendes",
           "dragoes", "demonios")
PEOPLE_NAMES = {
    "humanos": "Humanos", "anoes": "Anões", "orcs": "Orcs", "fadas": "Fadas",
    "vampiros": "Vampiros", "lobisomens": "Lobisomens", "gigantes": "Gigantes",
    "mortos_vivos": "Mortos-vivos", "filhos_floresta": "Filhos da Floresta",
    "gnomos_duendes": "Gnomos e Duendes", "dragoes": "Dragões", "demonios": "Demônios",
}


def _catalog() -> dict:
    entries = []
    for people in PEOPLES:
        spell = spells.spell_for_people(people)
        entries.append({
            "id": people,
            "label": PEOPLE_NAMES[people],
            "heroes": [{"id": hero.hero_id, "name": hero.name, "life": hero.life,
                        "abilities": list(hero.abilities)}
                       for hero in heroes.heroes_for_people(people)],
            "spell": None if spell is None else {
                "id": spell.spell_id, "name": spell.name,
                "description": spell.description,
            },
        })
    return {"peoples": entries, "defaults": {
        "city_life": DEFAULT_CITY_LIFE_START, "city_life_max": DEFAULT_CITY_LIFE_MAX,
        "gold": DEFAULT_STARTING_GOLD, "magic": DEFAULT_STARTING_MAGIC,
    }}


def _new_state(seed: int, player_setup: list[dict] | None = None,
               config: dict | None = None):
    if player_setup is None:
        player_setup = [
            {"name": "Jogador 1", "people": "humanos", "hero_id": "miyamoto"},
            {"name": "Jogador 2", "people": "anoes", "hero_id": "ori"},
            {"name": "Jogador 3", "people": "orcs", "hero_id": "arken"},
            {"name": "Jogador 4", "people": "fadas", "hero_id": "ainai"},
        ]
    if len(player_setup) != 4:
        raise ValueError("A partida local requer exatamente quatro jogadores.")
    selected = [str(item.get("people", "")) for item in player_setup]
    if any(people not in PEOPLES for people in selected):
        raise ValueError("Há um povo desconhecido na configuração.")
    if len(set(selected)) != 4:
        raise ValueError("Cada jogador deve escolher um povo diferente.")
    choices = {}
    names = {}
    heroes_by_people = {people: [hero.hero_id for hero in heroes.heroes_for_people(people)]
                        for people in PEOPLES}
    for player_id, item in enumerate(player_setup, 1):
        people = selected[player_id - 1]
        name = str(item.get("name", "")).strip()
        if not name or len(name) > 40:
            raise ValueError("Cada jogador precisa de um nome com até 40 caracteres.")
        hero_id = "" if people == "mortos_vivos" else str(item.get("hero_id", ""))
        if people != "mortos_vivos" and hero_id not in heroes_by_people[people]:
            raise ValueError(f"Herói inválido para {PEOPLE_NAMES[people]}.")
        names[player_id] = name
        choices[player_id] = {"povo": people, "heroi": hero_id}
    config = config or {}
    values = {
        "city_life": int(config.get("city_life", DEFAULT_CITY_LIFE_START)),
        "city_life_max": int(config.get("city_life_max", DEFAULT_CITY_LIFE_MAX)),
        "gold_start": int(config.get("gold", DEFAULT_STARTING_GOLD)),
        "magic_start": int(config.get("magic", DEFAULT_STARTING_MAGIC)),
    }
    if (values["city_life"] < 1 or values["city_life_max"] < values["city_life"]
            or values["gold_start"] < 0 or values["magic_start"] < 0):
        raise ValueError("Configuração inicial inválida.")
    state, _ = run_setup(list(PEOPLES), heroes_by_people, choices, seed,
                         turn_order=[1, 2, 3, 4], **values)
    for player in state.players:
        player.name = names[player.id]
    start_turn(state)
    pending = next((p for p in state.players if p.people == "gnomos_duendes"
                    and p.city.is_alive() and p.bets_need_realocacao), None)
    state.active_player_id = pending.id if pending else state.curuna_id
    if pending is None:
        start_player_day(state, state.active_player_id)
    return state


def _snapshot(match_id: str) -> dict:
    match = MATCHES[match_id]
    return {"version": SAVE_VERSION, "state": state_to_dict(match["state"]),
            "events": match["events"], "name": match.get("name", "Partida local")}


def _save(match_id: str, name: str | None = None) -> str:
    SAVES.mkdir(parents=True, exist_ok=True)
    payload = _snapshot(match_id)
    payload["kind"] = "manual" if name is not None else "autosave"
    if name is not None:
        payload["name"] = name
    path = SAVES / f"{uuid.uuid4().hex[:12] if name is not None else match_id}.json"
    saves.write(path, payload)
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
        if not 0 <= length <= 10 * 1024 * 1024:
            raise ValueError("Arquivo excede o limite de 10 MB.")
        body = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("Conteúdo da requisição inválido.")
        return body

    def _parts(self):
        return [p for p in urlparse(self.path).path.split("/") if p]

    def do_GET(self):
        parts = self._parts()
        if not parts:
            return self._file("index.html", "text/html; charset=utf-8")
        if parts == ["catalog"]:
            return self._json(200, _catalog())
        if parts == ["saves"]:
            with LOCK:
                return self._json(200, saves.list_saved(SAVES))
        if parts[0] == "static" and len(parts) == 2:
            mime = "text/css" if parts[1].endswith(".css") else "text/javascript"
            return self._file(parts[1], mime)
        if parts[0] == "assets" and len(parts) > 1:
            path = (ASSETS / Path(*parts[1:])).resolve()
            try:
                path.relative_to(ASSETS.resolve())
            except ValueError:
                return self._json(404, {"error": "Arquivo não encontrado."})
            if not path.is_file():
                return self._json(404, {"error": "Arquivo não encontrado."})
            mime = "image/svg+xml" if path.suffix == ".svg" else "application/octet-stream"
            return self._send_file(path, mime)
        if len(parts) == 3 and parts[0] == "matches":
            match_id, resource = parts[1], parts[2]
            with LOCK:
                match = MATCHES.get(match_id)
                if not match:
                    return self._json(404, {"error": "Partida não encontrada."})
                state = match["state"]
                if resource == "export":
                    return self._json(200, _snapshot(match_id))
                query = parse_qs(urlparse(self.path).query)
                player_id = int(query.get("player_id", [state.active_player_id or 1])[0])
                if resource == "view":
                    return self._json(200, view_for_player(state, player_id))
                if resource == "actions":
                    return self._json(200, legal_actions(state, player_id))
                if resource == "events":
                    visible = [event for event in match["events"]
                               if event.get("visibility", {}).get("kind") == "public"
                               or player_id in event.get("visibility", {}).get("player_ids", [])]
                    return self._json(200, visible)
        self._json(404, {"error": "Rota não encontrada."})

    def do_POST(self):
        parts = self._parts()
        try:
            body = self._body()
        except (UnicodeError, ValueError) as exc:
            return self._json(422, {"error": str(exc)})
        with LOCK:
            if parts == ["matches"]:
                try:
                    state = _new_state(int(body.get("seed", 20260923)),
                                       body.get("players"), body.get("config"))
                except (TypeError, ValueError) as exc:
                    return self._json(422, {"error": str(exc)})
                match_id = uuid.uuid4().hex[:12]
                MATCHES[match_id] = {"state": state, "events": []}
                _save(match_id)
                return self._json(201, {"match_id": match_id})
            if parts in (["matches", "load"], ["matches", "import"]):
                try:
                    if parts[-1] == "load":
                        path = saves.save_path(SAVES, body.get("save_id"))
                        if not path.is_file():
                            return self._json(404, {"error": "Save não encontrado."})
                        payload = saves.read(path)
                    else:
                        payload = body
                    state, events, name = saves.validate(payload)
                except saves.VersionError as exc:
                    return self._json(409, {"error": str(exc)})
                except (OSError, ValueError) as exc:
                    return self._json(422, {"error": str(exc)})
                match_id = uuid.uuid4().hex[:12]
                MATCHES[match_id] = {"state": state, "events": events, "name": name}
                _save(match_id)
                return self._json(201, {"match_id": match_id})
            if len(parts) == 3 and parts[0] == "matches":
                match_id, resource = parts[1], parts[2]
                match = MATCHES.get(match_id)
                if not match:
                    return self._json(404, {"error": "Partida não encontrada."})
                if resource == "dream-preview":
                    from ..core.interaction_actions import dream_preview
                    from ..core.actions import ActionError
                    from ..core.combat import CombatError
                    try:
                        result = dream_preview(match["state"], body.get("player_id"), body.get("choice"))
                    except (ActionError, CombatError, TypeError, ValueError) as exc:
                        return self._json(422, {"error": str(exc)})
                    return self._json(200, result)
                if resource == "actions":
                    result = apply_action(match["state"], body)
                    if result["success"]:
                        match["events"].extend(result["events"])
                        _save(match_id)
                    return self._json(200 if result["success"] else 422, result)
                if resource == "save":
                    name = body.get("name", "Partida local")
                    if not isinstance(name, str) or not name.strip() or len(name) > 60:
                        return self._json(422, {"error": "Nome do save deve ter de 1 a 60 caracteres."})
                    return self._json(200, {"save_id": Path(_save(match_id, name.strip())).stem,
                                            "version": SAVE_VERSION})
        self._json(404, {"error": "Rota não encontrada."})

    def _file(self, name: str, mime: str) -> None:
        path = STATIC / name
        if not path.is_file():
            return self._json(404, {"error": "Arquivo não encontrado."})
        return self._send_file(path, mime)

    def _send_file(self, path: Path, mime: str) -> None:
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
