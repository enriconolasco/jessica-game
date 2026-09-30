"""Formato e validação dos saves completos do cliente local."""
import json
from datetime import datetime, timezone
from pathlib import Path
import re

from ..core.constants import Phase
from ..core.headless import SAVE_VERSION
from ..core.serialize import state_from_dict


class VersionError(ValueError):
    pass


def save_path(directory, save_id):
    if not isinstance(save_id, str) or not re.fullmatch(r"[a-f0-9]{12}(?:\.json)?", save_id):
        raise ValueError("Identificador de save inválido.")
    return directory / f"{Path(save_id).stem}.json"


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("O arquivo deve conter um save completo de Jéssica.")
    if payload.get("version") != SAVE_VERSION:
        raise VersionError("Versão de save incompatível. Use um arquivo exportado pelo cliente web atual.")
    try:
        json.dumps(payload, allow_nan=False)
        data = payload["state"]
        if (type(data["turn"]) is not int or data["turn"] < 1
                or type(data["rng"]["state"]) is not int
                or not 0 <= data["rng"]["state"] < 2**64
                or type(data["game_over"]) is not bool):
            raise ValueError("Estado ou RNG inválido.")
        state = state_from_dict(data)
        ids = {p.id for p in state.players}
        if (len(state.players) != 4 or ids != {1, 2, 3, 4}
                or len(state.turn_order) != 4 or set(state.turn_order) != ids
                or state.curuna_id not in ids or state.active_player_id not in ids | {None}
                or state.phase not in (Phase.DAY, Phase.NIGHT)
                or not isinstance(state.web_night, dict)):
            raise ValueError("Estrutura da partida inválida.")
        for p in state.players:
            if (not isinstance(p.hand, list) or not all(isinstance(c, str) for c in p.hand)
                    or not isinstance(p.name, str) or p.city.owner_id != p.id
                    or any(type(v) is not int for v in (p.city.life, p.city.life_max, p.city.gold, p.city.magic))):
                raise ValueError("Dados do jogador inválidos.")
            for u in p.units:
                if (u.owner_id != p.id or not isinstance(u.id, str)
                        or u.house not in {"center", "city_1", "city_2", "city_3", "city_4"}
                        or type(u.life) is not int or type(u.life_max) is not int):
                    raise ValueError("Dados de unidade inválidos.")
        events = payload.get("events", [])
        name = payload.get("name", "Partida local")
        if (not isinstance(events, list) or not all(isinstance(e, dict) for e in events)
                or any(not isinstance(e.get("visibility", {}), dict) for e in events)
                or not isinstance(name, str) or not name.strip() or len(name) > 60):
            raise ValueError("Histórico ou nome do save inválido.")
        if state.web_night and (type(state.web_night.get("turn")) is not int
                or "queue" not in state.web_night
                or type(state.web_night.get("ready", True)) is not bool):
            raise ValueError("Estado da fila noturna inválido.")
        for key in ("queue", "setup"):
            entries = state.web_night.get(key, [])
            if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
                raise ValueError("Fila noturna inválida.")
            for entry in entries:
                kind = entry.get("kind")
                if (kind not in (None, "house", "end_house", "ainai", "luide",
                        "flames", "vovo", "aiquara", "luna", "besouro")
                        or ("player_id" in entry and entry["player_id"] not in ids)
                        or (kind not in ("flames", "house", "end_house") and "player_id" not in entry)
                        or (kind in (None, "house", "end_house", "luide") and "house" not in entry)
                        or (kind is None and not isinstance(entry.get("unit_id"), str))
                        or ("house" in entry and entry["house"] not in {"center", "city_1", "city_2", "city_3", "city_4"})):
                    raise ValueError("Janela noturna inválida.")
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError(f"Save inválido: {exc}") from exc
    return state, events, name


def read(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate(payload)
    return payload


def write(path, payload):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def list_saved(directory):
    result = []
    for path in directory.glob("*.json"):
        if not re.fullmatch(r"[a-f0-9]{12}", path.stem):
            continue
        try:
            payload = read(path)
            state = payload["state"]
            result.append({"save_id": path.stem, "name": payload.get("name", "Partida local"),
                           "turn": state["turn"], "phase": state["phase"],
                           "kind": payload.get("kind", "autosave"),
                           "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
        except (OSError, ValueError):
            result.append({"save_id": path.stem, "name": "Save inválido", "invalid": True})
    return sorted(result, key=lambda item: item.get("updated_at", ""), reverse=True)
