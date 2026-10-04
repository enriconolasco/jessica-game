from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import re
from pathlib import Path
from string import Formatter

from ..core.rng import DeterministicRNG

VERSION = "narrative-v0.1"
TRIGGERS = {"match_started", "turn_started", "player_turn_ended", "match_ended"}
FIELDS = {"territory", "season", "atmosphere", "motive", "peoples", "turn",
          "curuna", "player", "next_player", "winner"}
PROFILES = (
    {"territory": "uma serra de pedra e mata", "season": "tempo das chuvas",
     "atmosphere": "névoa entre os morros", "motive": "a disputa pelas passagens"},
    {"territory": "uma várzea de rios largos", "season": "tempo das águas baixas",
     "atmosphere": "vento sobre os remansos", "motive": "a disputa pelas travessias"},
    {"territory": "um chapadão cercado de veredas", "season": "tempo da seca",
     "atmosphere": "poeira nos caminhos", "motive": "a disputa pelos caminhos antigos"},
)
PEOPLES = dict(zip(
    ("humanos", "anoes", "orcs", "fadas", "vampiros", "lobisomens", "gigantes",
     "mortos_vivos", "filhos_floresta", "gnomos_duendes", "dragoes", "demonios"),
    ("Humanos", "Anões", "Orcs", "Fadas", "Vampiros", "Lobisomens", "Gigantes",
     "Mortos-Vivos", "Filhos da Floresta", "Gnomos e Duendes", "Dragões", "Demônios")))
CATALOG = Path(__file__).resolve().parents[2] / "content/narrative/pilot-v0.1.json"


def validate_catalog(payload):
    """Entradas inválidas são omitidas; diagnósticos ficam disponíveis à revisão."""
    if not isinstance(payload, dict) or payload.get("version") != VERSION or not isinstance(payload.get("entries"), list):
        return [], ["Envelope narrativo incompatível"]
    entries, errors = [], []
    ids = Counter(e.get("id") for e in payload["entries"]
                  if isinstance(e, dict) and isinstance(e.get("id"), str))
    for entry in payload["entries"]:
        try:
            if not isinstance(entry, dict) or set(entry) != {"id", "trigger", "conditions", "text", "weight"}:
                raise ValueError("campos inválidos")
            if not isinstance(entry["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,99}", entry["id"]) or ids[entry["id"]] != 1:
                raise ValueError("identificador ausente/duplicado")
            if entry["trigger"] not in TRIGGERS or type(entry["weight"]) is not int or not 1 <= entry["weight"] <= 100:
                raise ValueError("gatilho/peso inválido")
            if not isinstance(entry["conditions"], dict):
                raise ValueError("condições inválidas")
            allowed = {key: {p[key] for p in PROFILES} for key in PROFILES[0]}
            allowed["outcome"] = {"victory", "draw"}
            for key, value in entry["conditions"].items():
                if key not in allowed or not isinstance(value, str) or value not in allowed[key]:
                    raise ValueError("condição desconhecida")
            if not isinstance(entry["text"], str) or not entry["text"].strip() or len(entry["text"]) > 600:
                raise ValueError("texto inválido")
            for _, variable, specification, conversion in Formatter().parse(entry["text"]):
                if variable is not None and (variable not in FIELDS or specification or conversion):
                    raise ValueError("variável/formatação não permitida")
            entries.append(deepcopy(entry))
        except (TypeError, ValueError) as error:
            errors.append(f"{entry.get('id', '?') if isinstance(entry, dict) else '?'}: {error}")
    return entries, errors


def load_catalog(path=CATALOG):
    try:
        return validate_catalog(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return [], ["Catálogo ausente ou ilegível"]


def restore_session(value):
    if not value:
        return {}
    try:
        if (not isinstance(value, dict) or value.get("version") != VERSION
                or value.get("profile") not in PROFILES
                or not isinstance(value.get("rng"), dict)
                or type(value["rng"].get("state")) is not int
                or not 0 <= value["rng"]["state"] < 2**64
                or not isinstance(value.get("history"), list)):
            return {}
        seen = set()
        for record in value["history"]:
            if (not isinstance(record, dict) or record.get("trigger") not in TRIGGERS
                    or not isinstance(record.get("event_id"), str) or not record["event_id"]
                    or record["event_id"] in seen or record.get("visibility") != "public"
                    or record.get("entry_id") is not None and not isinstance(record["entry_id"], str)
                    or not isinstance(record.get("fields"), dict)
                    or set(record["fields"]) - FIELDS
                    or any(not isinstance(v, (str, int)) for v in record["fields"].values())
                    or record.get("text") is not None and not isinstance(record["text"], str)):
                return {}
            seen.add(record["event_id"])
        return deepcopy(value)
    except (TypeError, KeyError):
        return {}


def lifecycle_event(trigger, view, player_id=None, next_player_id=None):
    """Adaptadores chamam nos limites reais do fluxo, nunca por leitura de logs."""
    if trigger not in TRIGGERS:
        raise ValueError("Gatilho desconhecido")
    event_id = {"match_started": "match:start", "turn_started": f"turn:{view['turn']}:start",
                "player_turn_ended": f"turn:{view['turn']}:player:{player_id}:end",
                "match_ended": "match:end"}[trigger]
    return {"version": "event-v0.1", "id": event_id, "type": trigger,
            "turn": view["turn"], "phase": view["phase"],
            "participants": [] if player_id is None else [player_id],
            "visibility": {"kind": "public", "player_ids": []},
            "data": {"player_id": player_id, "next_player_id": next_player_id}}


def observe(seed, session, event, view, mode="breve", entries=None):
    """Só recebe projeção pública. Retorna metadados novos e texto opcional."""
    if (mode != "breve" or not isinstance(event, dict)
            or event.get("version") != "event-v0.1" or not isinstance(event.get("type"), str)
            or event["type"] not in TRIGGERS or not isinstance(event.get("visibility"), dict)
            or event.get("visibility", {}).get("kind") != "public"
            or not isinstance(event.get("id"), str) or not event["id"]
            or type(event.get("turn")) is not int or event["turn"] < 1
            or not isinstance(event.get("data"), dict)):
        return deepcopy(session), None
    if (not isinstance(view, dict) or not isinstance(view.get("players"), list)
            or any(not isinstance(p, dict) or type(p.get("id")) is not int
                   or not isinstance(p.get("name"), str) or not isinstance(p.get("people"), str)
                   for p in view["players"])
            or any(event["data"].get(k) is not None and type(event["data"][k]) is not int
                   for k in ("player_id", "next_player_id"))
            or event["type"] == "match_ended" and not view.get("game_over")):
        return deepcopy(session), None
    restored = restore_session(session)
    if session and not restored:
        return deepcopy(session), None
    if entries is None:
        entries, _ = load_catalog()
    else:
        entries, _ = validate_catalog({"version": VERSION, "entries": entries})
    if not entries:
        return deepcopy(session), None
    if not restored:
        narrative_seed = int.from_bytes(sha256(f"jessica:narrative:v1:{seed}".encode()).digest()[:8], "big")
        rng = DeterministicRNG(narrative_seed)
        restored = {"version": VERSION, "profile": deepcopy(rng.choice(PROFILES)),
                    "rng": rng.to_dict(), "history": []}
    if any(r["event_id"] == event["id"] for r in restored["history"]):
        return restored, None
    names = {p["id"]: p["name"] for p in view["players"]}
    data = event.get("data", {})
    fields = {**restored["profile"], "turn": event["turn"],
              "peoples": ", ".join(PEOPLES.get(p["people"], p["people"]) for p in view["players"]),
              "curuna": names.get(view.get("curuna_id"), "o Curruna"),
              "player": names.get(data.get("player_id"), "o jogador"),
              "next_player": names.get(data.get("next_player_id"), "a noite"),
              "winner": names.get(view.get("winner_id"), "nenhum povo")}
    outcome = "victory" if view.get("winner_id") is not None else "draw"
    context = {**fields, "outcome": outcome}
    pool = [e for e in entries if e["trigger"] == event["type"]
            and all(context.get(k) == v for k, v in e["conditions"].items())]
    selected, text = None, None
    if pool:
        counts = Counter(r["entry_id"] for r in restored["history"])
        least = min(counts[e["id"]] for e in pool)
        pool = [e for e in pool if counts[e["id"]] == least]
        recent = [r["entry_id"] for r in restored["history"] if r["trigger"] == event["type"]][-2:]
        pool = [e for e in pool if e["id"] not in recent] or pool
        rng = DeterministicRNG.from_dict(restored["rng"])
        draw = rng.randrange(sum(e["weight"] for e in pool))
        for entry in pool:
            draw -= entry["weight"]
            if draw < 0:
                selected = entry
                break
        text = selected["text"].format_map(fields)
        restored["rng"] = rng.to_dict()
    restored["history"].append({"event_id": event["id"], "trigger": event["type"],
        "entry_id": selected["id"] if selected else None, "fields": fields,
        "text": text, "visibility": "public"})
    return restored, text


def replay(session):
    return [deepcopy(record) for record in restore_session(session).get("history", [])
            if record["text"] is not None]
