"""Formato e validação dos saves completos do cliente local."""
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import uuid
from copy import deepcopy

from ..core.constants import Phase
from ..core.headless import SAVE_VERSION, EVENT_VERSION
from ..core.serialize import state_from_dict

AUTOSAVE_HISTORY_LIMIT = 5


class VersionError(ValueError):
    pass


def new_id(directory, reserved=()):
    while True:
        candidate = uuid.uuid4().hex[:12]
        if candidate not in reserved and not (directory / f"{candidate}.json").exists():
            return candidate


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
        if not isinstance(state.web_reaction, dict):
            raise ValueError("Reação pendente inválida.")
        if state.web_reaction:
            reaction = state.web_reaction
            request = reaction.get("request", {})
            if (not isinstance(request, dict) or request.get("player_id") not in (1, 2, 3, 4)
                    or type(request.get("max_gold")) is not int or request["max_gold"] < 0
                    or not isinstance(reaction.get("action"), dict)
                    or not isinstance(reaction.get("payments"), list)
                    or any(type(x) is not int or x < 0 for x in reaction["payments"])
                    or "origin_active_player_id" not in reaction):
                raise ValueError("Decisão de Armadura inválida.")
            if (type(request.get("damage")) is not int or request["damage"] < 1
                    or type(request.get("gold_available")) is not int or request["gold_available"] < 1
                    or request["max_gold"] != min(request["damage"], request["gold_available"])):
                raise ValueError("Limite da Armadura inválido.")
            preview = reaction.get("preview")
            if preview is not None:
                if (not isinstance(preview, dict)
                        or set(preview) != {"players", "board", "conditions", "shop", "demon_pacts", "self"}
                        or not isinstance(preview["players"], list) or len(preview["players"]) != 4
                        or {p.get("id") for p in preview["players"] if isinstance(p, dict)} != {1, 2, 3, 4}
                        or not isinstance(preview["board"], dict) or not isinstance(preview["board"].get("units"), list)
                        or not isinstance(preview["self"], dict) or not isinstance(preview["self"].get("hand"), list)
                        or not isinstance(preview["conditions"], list) or not isinstance(preview["shop"], dict)
                        or not isinstance(preview["demon_pacts"], list)):
                    raise ValueError("Prévia da defesa inválida.")
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
        generation = payload.get("recovery_generation", 0)
        if type(generation) is not int or generation < 0:
            raise ValueError("Geração de recuperação inválida.")
        if payload.get("kind") == "recovery" and (
                not isinstance(payload.get("source_match_id"), str)
                or not re.fullmatch(r"[a-f0-9]{12}", payload["source_match_id"])):
            raise ValueError("Origem de recuperação inválida.")
        if (not isinstance(events, list) or not all(isinstance(e, dict) for e in events)
                or any(not isinstance(e.get("visibility", {}), dict) for e in events)
                or not isinstance(name, str) or not name.strip() or len(name) > 60):
            raise ValueError("Histórico ou nome do save inválido.")
        if state.web_night and (type(state.web_night.get("turn")) is not int
                or "queue" not in state.web_night
                or type(state.web_night.get("ready", True)) is not bool
                or type(state.web_night.get("final_ainai_queued", False)) is not bool):
            raise ValueError("Estado da fila noturna inválido.")
        history = payload.get("history", [])
        skip = payload.get("checkpoint_skip", {})
        if (not isinstance(skip, dict) or skip and (set(skip) != {"turn", "player_id"}
                or type(skip["turn"]) is not int or skip["turn"] < 1
                or type(skip["player_id"]) is not int or skip["player_id"] not in ids)):
            raise ValueError("Origem de restauração inválida.")
        if not isinstance(history, list) or len(history) > 4:
            raise ValueError("Histórico de restauração inválido.")
        seen = set()
        for checkpoint in history:
            if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("snapshot"), dict):
                raise ValueError("Ponto de restauração inválido.")
            snapshot = checkpoint["snapshot"]
            if "history" in snapshot:
                raise ValueError("Histórico aninhado inválido.")
            restored, _, _ = validate(snapshot)
            pid = checkpoint.get("player_id")
            if (type(pid) is not int or pid in seen or restored.active_player_id != pid
                    or restored.phase != Phase.DAY or restored.web_reaction
                    or checkpoint.get("turn") != state.turn or restored.turn != state.turn):
                raise ValueError("Ponto de restauração incompatível.")
            seen.add(pid)
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
                        or ("occupied" in entry and type(entry["occupied"]) is not bool)
                        or ("house" in entry and entry["house"] not in {"center", "city_1", "city_2", "city_3", "city_4"})):
                    raise ValueError("Janela noturna inválida.")
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError(f"Save inválido: {exc}") from exc
    return state, events, name


def import_payload(payload):
    if not isinstance(payload, dict) or "version" in payload or "state" in payload:
        validate(payload)
        return deepcopy(payload), []
    converted = {"version": SAVE_VERSION, "state": deepcopy(payload),
                 "events": [], "history": [], "name": "Importação do terminal"}
    state, _, _ = validate(converted)
    if not state.game_over:
        if state.phase == Phase.NIGHT:
            if not state.web_night:
                raise ValueError("Save do terminal durante a Noite não contém a fila de declarações. "
                                 "Importe um save feito durante o Dia; o combate não será reiniciado.")
        elif state.web_reaction:
            raise ValueError("Use a exportação web para retomar uma reação pendente.")
        else:
            candidates = [p.id for p in state.players if p.city.is_alive()
                          and p.morning_done_this_turn and not p.has_played_day_this_turn
                          and p.skip_day_turn != state.turn]
            if len(candidates) != 1 or state.active_player_id not in (None, candidates[0]):
                raise ValueError("Save do terminal sem uma jogada diurna inequívoca. "
                                 "Salve durante a vez de um jogador, após sua manhã.")
            converted["state"]["active_player_id"] = candidates[0]
            converted["checkpoint_skip"] = {"turn": state.turn, "player_id": candidates[0]}
    converted["events"] = [{"version": EVENT_VERSION, "type": "match_imported",
        "turn": state.turn, "phase": state.phase.value, "participants": [],
        "data": {"source": "terminal"}, "visibility": {"kind": "public", "player_ids": []}}]
    validate(converted)
    return converted, ["Save do terminal importado sem reaplicar a manhã ou consumir RNG.",
        "O log antigo fica preservado no save; o histórico web começa nesta importação.",
        "Refazer Dia/Mola só estarão disponíveis para jogadas com início registrado na web."]


def read(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate(payload)
    return payload


def write(path, payload):
    validate(payload)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def write_autosave(path, payload):
    if not re.fullmatch(r"[a-f0-9]{12}", path.stem):
        raise ValueError("Identificador de autosave inválido.")
    previous = read(path) if path.is_file() else None
    generation = previous.get("recovery_generation", 0) if previous else 0
    if previous is not None:
        archive = {**previous, "kind": "recovery", "source_match_id": path.stem,
                   "recovery_generation": generation,
                   "name": ("Recuperação — " + previous.get("name", "Partida local"))[:60]}
        write(path.parent / f"{new_id(path.parent)}.json", archive)
    write(path, {**payload, "recovery_generation": generation + 1})
    recoveries = [entry for entry in list_saved(path.parent)
                  if entry.get("kind") == "recovery" and entry.get("source_match_id") == path.stem]
    recoveries.sort(key=lambda entry: entry["recovery_generation"], reverse=True)
    for entry in recoveries[AUTOSAVE_HISTORY_LIMIT:]:
        save_path(path.parent, entry["save_id"]).unlink()


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
                           "source_match_id": payload.get("source_match_id"),
                           "recovery_generation": payload.get("recovery_generation", 0),
                           "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
        except (OSError, ValueError):
            result.append({"save_id": path.stem, "name": "Save inválido", "invalid": True})
    return sorted(result, key=lambda item: item.get("updated_at", ""), reverse=True)
