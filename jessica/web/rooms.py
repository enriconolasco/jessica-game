"""Salas autenticadas; regras e escolhas continuam na porta comum do motor."""
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import re
import secrets
import threading

from . import server, session
from ..core.headless import apply_action, legal_actions, view_for_player


class RoomError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def name(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 40:
        raise RoomError(422, "Nome deve ter de 1 a 40 caracteres.")
    if any(ord(c) < 32 for c in value):
        raise RoomError(422, "Nome contém caracteres inválidos.")
    return value.strip()


@dataclass
class Member:
    player_id: int
    name: str
    credential_hash: str = field(repr=False)
    people: str | None = None
    hero_id: str = ""
    ready: bool = False

    def public(self):
        return {k: getattr(self, k) for k in ("player_id", "name", "people", "hero_id", "ready")}


@dataclass
class Room:
    code: str
    seed: int
    members: list[Member] = field(default_factory=list)
    revision: int = 0
    match: dict | None = field(default=None, repr=False)
    commands: dict = field(default_factory=dict, repr=False)
    lock: object = field(default_factory=threading.RLock, repr=False)
    listeners: set = field(default_factory=set, repr=False)

    def _changed(self):
        self.revision += 1
        for notify in tuple(self.listeners):
            notify(self.revision)

    def public(self, member):
        return {"version": 1, "code": self.code, "revision": self.revision,
                "status": "playing" if self.match else "lobby", "you": member.player_id,
                "host_id": 1, "players": [m.public() for m in self.members]}

    def authenticate(self, credential):
        if not isinstance(credential, str) or not credential:
            raise RoomError(401, "Credencial de sessão necessária.")
        digest = hashlib.sha256(credential.encode()).hexdigest()
        member = next((m for m in self.members if secrets.compare_digest(m.credential_hash, digest)), None)
        if member is None:
            raise RoomError(403, "Sessão não pertence a esta sala.")
        return member

    def join(self, player_name):
        if self.match or len(self.members) >= 4:
            raise RoomError(409, "Sala cheia ou partida já iniciada.")
        token = secrets.token_urlsafe(32)
        member = Member(len(self.members) + 1, name(player_name), hashlib.sha256(token.encode()).hexdigest())
        self.members.append(member)
        self._changed()
        return {"room": self.public(member), "credential": token}

    def select(self, member, people, hero_id):
        if self.match or member.ready:
            raise RoomError(409, "Desmarque pronto antes de mudar sua escolha.")
        choices = {h.hero_id for h in server.heroes.heroes_for_people(people)} if people in server.PEOPLES else set()
        if people not in server.PEOPLES or (people != "mortos_vivos" and hero_id not in choices):
            raise RoomError(422, "Povo ou herói inválido.")
        if people == "mortos_vivos" and hero_id != "":
            raise RoomError(422, "Mortos-vivos escolhem heróis durante a partida.")
        if any(m is not member and m.people == people for m in self.members):
            raise RoomError(409, "Povo já escolhido nesta sala.")
        member.people, member.hero_id = people, hero_id
        self._changed()
        return self.public(member)

    def mark_ready(self, member, ready):
        if self.match or type(ready) is not bool or not member.people:
            raise RoomError(422, "Escolha povo/herói antes de marcar pronto.")
        if member.ready != ready:
            member.ready = ready
            self._changed()
        return self.public(member)

    def start(self, member):
        if member.player_id != 1:
            raise RoomError(403, "Somente o anfitrião inicia a partida.")
        if self.match or len(self.members) != 4 or not all(m.ready for m in self.members):
            raise RoomError(409, "São necessários quatro jogadores prontos.")
        rows = [{"name": m.name, "people": m.people, "hero_id": m.hero_id} for m in self.members]
        state = server._new_state(self.seed, rows)
        self.match = {"state": state, "events": session.public_events(state)}
        self._changed()
        return self.public(member)

    def snapshot(self, member):
        if not self.match:
            raise RoomError(409, "Partida não iniciada.")
        state = self.match["state"]
        return {"version": 1, "revision": self.revision, "player_id": member.player_id,
                "view": view_for_player(state, member.player_id),
                "actions": legal_actions(state, member.player_id),
                "events": server._visible_events(self.match["events"], member.player_id)}

    def apply(self, member, envelope):
        if not self.match:
            raise RoomError(409, "Partida não iniciada.")
        if set(envelope) != {"command_id", "revision", "action"}:
            raise RoomError(422, "Comando precisa de command_id, revision e action.")
        command_id, revision, action = (envelope[k] for k in ("command_id", "revision", "action"))
        if not isinstance(command_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", command_id):
            raise RoomError(422, "Identificador de comando inválido.")
        if type(revision) is not int or revision < 0 or not isinstance(action, dict):
            raise RoomError(422, "Revisão ou ação inválida.")
        action = deepcopy(action)
        if "player_id" in action and (type(action["player_id"]) is not int or action["player_id"] != member.player_id):
            raise RoomError(403, "Não é permitido agir por outro jogador.")
        action["player_id"] = member.player_id
        fingerprint = json.dumps(action, sort_keys=True, allow_nan=False)
        key = (member.player_id, command_id)
        previous = self.commands.get(key)
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise RoomError(409, "Identificador já usado para outro comando.")
            return deepcopy(previous["response"])
        if revision != self.revision:
            raise RoomError(409, "Partida atualizada. Receba uma nova visão antes de agir.")
        state = deepcopy(self.match["state"])
        before = session.public_snapshot(state)
        result = apply_action(state, action)
        if not result["success"]:
            return {**result, "revision": self.revision}
        if not state.web_reaction:
            result["events"] = session.changes(before, state, action) + result["events"]
        self.match["state"] = state
        self.match["events"].extend(result["events"])
        self._changed()
        response = {**result, "revision": self.revision, "pending": bool(state.web_reaction),
                    "events": server._visible_events(result["events"], member.player_id)}
        self.commands[key] = {"fingerprint": fingerprint, "action": action, "response": deepcopy(response)}
        return response


class Registry:
    def __init__(self):
        self.rooms = {}
        self.lock = threading.RLock()

    def create(self, player_name):
        player_name = name(player_name)
        with self.lock:
            while (code := "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))) in self.rooms:
                pass
            room = Room(code, secrets.randbits(64))
            result = room.join(player_name)
            self.rooms[code] = room
            return result

    def get(self, code):
        with self.lock:
            room = self.rooms.get(code)
        if room is None:
            raise RoomError(404, "Sala não encontrada.")
        return room
