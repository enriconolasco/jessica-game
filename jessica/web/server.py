from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from . import saves, session

from ..core import heroes, spells, artifacts, reference, peoples
from ..core.constants import (DEFAULT_CITY_LIFE_MAX, DEFAULT_CITY_LIFE_START,
                              DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC)
from ..core.headless import SAVE_VERSION, apply_action, legal_actions, view_for_player
from ..core.serialize import state_from_dict, state_to_dict
from ..core.setup import run_setup
from ..core.setup import roll_d20_order, horario_from
from ..core.state import make_rng
from ..core import constants
from ..core.turn import start_turn


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
            "passive": reference.PASSIVA_DESC.get(people, ""),
            "heroes": [{"id": hero.hero_id, "name": hero.name, "life": hero.life,
                        "description": reference.HERO_ABILITY_DESC.get(hero.hero_id, ""),
                        "abilities": list(hero.abilities)}
                       for hero in heroes.heroes_for_people(people)],
            "spell": None if spell is None else {
                "id": spell.spell_id, "name": spell.name,
                "description": reference.SPELL_NOTES.get(spell.spell_id, spell.description),
            },
        })
    return {"peoples": entries,
        "heroes": [{"id": h.hero_id, "name": h.name, "life": h.life, "people": h.people,
                    "description": reference.HERO_ABILITY_DESC.get(h.hero_id, "")}
                   for h in heroes.HERO_CATALOG.values()],
        "artifacts": [{"id": a.card_id, "name": artifacts.card_display(a.card_id),
                       "description": ("Ao ativar, +1 de vida máxima da Base; cura 1 toda manhã."
                                       if a.card_id == "K_H" else a.description)}
                      for a in artifacts.ARTIFACT_CATALOG.values()],
        "conditions": reference.STATUS_DESC,
        "pacts": [{"id": pid, "name": name, "description": reference.PACT_NOTES[pid]}
                  for pid, name in peoples.DEMON_PACTS.items()],
        "rogue_items": reference.ROGUE_NOTES,
        "rules": [
            "Vence a última Base viva. Se nenhuma sobreviver, há empate.",
            "O Curuna inicia o Dia; os jogadores seguem a ordem do mapa. Ao fim dos Dias começa a Noite; depois avança o turno e o Curuna. Apostas são alocadas antes do primeiro Dia.",
            f"Coleta: {constants.RESOURCES_PER_DAY} recursos por Dia, distribuídos entre Ouro e Magia, uma vez. Juros: um Ouro por cada {constants.GOLD_INTEREST_DIVISOR} acumulados no início do turno.",
            f"Invocação comum de tropa: {constants.TROOP_SUMMON_COST_MAGIC} Magia mais Ouro igual à vida escolhida. Limites usuais: pequena 4, média 6, grande 8; povos e efeitos podem alterar custos e disponibilidade.",
            f"Muralha: {constants.CITY_LIFE_COST_GOLD} Ouro por ponto, até a vida máxima; indisponível de T13 em diante. Monumento: {constants.MONUMENT_COST_GOLD} Ouro com vida completa; concede artefato em turnos múltiplos de quatro. Heróis-Base possuem restrições próprias.",
            f"Artefatos: compra {constants.ARTIFACT_GOLD_COST} Ouro ou transmutação {constants.ARTIFACT_MAGIC_COST} Magia; venda {constants.ARTIFACT_SELL_GOLD} Ouro, salvo modificadores. Cartas obtidas são privadas até serem reveladas por sua ativação.",
            "Movimento: Cidade → Centro ou Centro → Cidade viva. Unidade recém-invocada já consumiu seu movimento; efeitos de dois movimentos podem liberar um movimento adicional. Escolher uma opção não a executa: confirme no botão da ação.",
            "Combate: Centro primeiro, depois Cidades na ordem inversa do Dia. Prioridade é por jogador no local, atualizada por chegada/saída; ataques e retaliações usam o core. Heróis não atacam Bases sem autorização de um efeito. Consulte as exceções de cada herói.",
            "Recarga padrão: o feitiço usado fica indisponível no próximo turno; Ressonância Mágica, Arken e outros efeitos têm exceções. A HUD informa disponibilidade; uma ação ausente não é atualmente legal.",
        ],
        "defaults": {
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
    order_mode = config.get("order_mode", "fixed")
    if order_mode not in ("fixed", "d20"):
        raise ValueError("Modo de ordem inicial inválido.")
    state, _ = run_setup(list(PEOPLES), heroes_by_people, choices, seed,
                         turn_order=None if order_mode == "d20" else [1, 2, 3, 4], **values)
    for player in state.players:
        player.name = names[player.id]
    start_turn(state)
    from ..core.day_flow import open_day
    open_day(state)
    return state


def _snapshot(match_id: str) -> dict:
    match = MATCHES[match_id]
    return {"version": SAVE_VERSION, "state": state_to_dict(match["state"]),
            "events": match["events"], "name": match.get("name", "Partida local"),
            "history": match.get("history", []), "checkpoint_skip": match.get("checkpoint_skip", {})}


def _save(match_id: str, name: str | None = None) -> str:
    SAVES.mkdir(parents=True, exist_ok=True)
    payload = _snapshot(match_id)
    payload["kind"] = "manual" if name is not None else "autosave"
    if name is not None:
        payload["name"] = name
    path = SAVES / f"{saves.new_id(SAVES, MATCHES) if name is not None else match_id}.json"
    if name is None:
        saves.write_autosave(path, payload)
    else:
        saves.write(path, payload)
    return path.name


def _visible_events(events, player_id):
    return [event for event in events
            if event.get("visibility", {}).get("kind") == "public"
            or player_id in event.get("visibility", {}).get("player_ids", [])]


def _autosave(match_id):
    try:
        _save(match_id)
    except OSError:
        return "Não foi possível concluir o autosave. A partida permanece em memória; " \
               "exporte uma cópia antes de fechar o servidor."
    return None


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
        if parts == ["setup-order"]:
            try:
                seed = int(parse_qs(urlparse(self.path).query).get("seed", [20260923])[0])
                order = roll_d20_order(make_rng(seed), 4)
            except ValueError:
                return self._json(422, {"error": "Seed inválida."})
            fixed = [1, 2, 3, 4]
            index = fixed.index(order[0])
            return self._json(200, {"turn_order": fixed, "initial_curuna_id": order[0],
                                    "day_order": fixed[index:] + fixed[:index],
                                    "selection_order": horario_from(order)})
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
                    view = view_for_player(state, player_id)
                    view["local_controls"] = session.controls(match)
                    return self._json(200, view)
                if resource == "actions":
                    return self._json(200, legal_actions(state, player_id))
                if resource == "events":
                    return self._json(200, _visible_events(match["events"], player_id))
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
                match_id = saves.new_id(SAVES, MATCHES)
                MATCHES[match_id] = {"state": state, "events": session.public_events(state)}
                session.checkpoint(MATCHES[match_id])
                warning = _autosave(match_id)
                return self._json(201, {"match_id": match_id, "save_warning": warning})
            if parts in (["matches", "load"], ["matches", "import"]):
                warnings = []
                try:
                    if parts[-1] == "load":
                        path = saves.save_path(SAVES, body.get("save_id"))
                        if not path.is_file():
                            return self._json(404, {"error": "Save não encontrado."})
                        payload = saves.read(path)
                    else:
                        payload, warnings = saves.import_payload(body)
                    state, events, name = saves.validate(payload)
                except saves.VersionError as exc:
                    return self._json(409, {"error": str(exc)})
                except (OSError, ValueError) as exc:
                    return self._json(422, {"error": str(exc)})
                match_id = saves.new_id(SAVES, MATCHES)
                MATCHES[match_id] = {"state": state, "events": events, "name": name,
                                     "history": payload.get("history", []),
                                     "checkpoint_skip": payload.get("checkpoint_skip", {})}
                warning = _autosave(match_id)
                return self._json(201, {"match_id": match_id, "warnings": warnings, "save_warning": warning})
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
                    before = session.public_snapshot(match["state"])
                    result = apply_action(match["state"], body)
                    if result["success"]:
                        if not match["state"].web_reaction:
                            result["events"] = session.changes(before, match["state"], body) + result["events"]
                        match["events"].extend(result["events"])
                        session.checkpoint(match)
                        result["save_warning"] = _autosave(match_id)
                    response = {**result, "pending": bool(match["state"].web_reaction),
                                "events": _visible_events(result["events"], body.get("player_id"))}
                    return self._json(200 if result["success"] else 422, response)
                if resource == "system":
                    try:
                        session.restore(match, body.get("operation"))
                    except ValueError as exc:
                        return self._json(422, {"error": str(exc)})
                    warning = _autosave(match_id)
                    return self._json(200, {"success": True, "save_warning": warning})
                if resource == "save":
                    name = body.get("name", "Partida local")
                    if not isinstance(name, str) or not name.strip() or len(name) > 60:
                        return self._json(422, {"error": "Nome do save deve ter de 1 a 60 caracteres."})
                    try:
                        saved_id = Path(_save(match_id, name.strip())).stem
                    except OSError:
                        return self._json(507, {"error": "Não foi possível salvar a cópia. Exporte a partida para preservá-la."})
                    return self._json(200, {"save_id": saved_id, "version": SAVE_VERSION})
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
