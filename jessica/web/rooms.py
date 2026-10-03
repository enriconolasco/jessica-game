"""Salas autenticadas; regras e escolhas continuam na porta comum do motor."""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
import secrets
import threading

from . import server, session, saves
from .room_store import StorageError
from ..core.headless import ACTION_VERSION, EVENT_VERSION, SAVE_VERSION, apply_action, legal_actions, view_for_player
from ..core.serialize import state_to_dict
from ..core.initial_conditions import validate_initial


def validate_config(capacity, configs):
    if type(capacity) is not int or not 2 <= capacity <= 5:
        raise RoomError(422, "Escolha de dois a cinco jogadores.")
    if not isinstance(configs, dict) or set(configs) - {str(pid) for pid in range(1, capacity + 1)}:
        raise RoomError(422, "Jogador inválido na configuração.")
    try:
        checked = {pid: validate_initial(values) for pid, values in configs.items()}
        if sum(values.get("artifacts", 0) for values in checked.values()) > 24:
            raise ValueError("Artefatos iniciais excedem a loja (24 cartas).")
        return checked
    except ValueError as exc:
        raise RoomError(422, str(exc)) from exc


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
    people_confirmed: bool = False

    def public(self, reveal_hero=False):
        result = {k: getattr(self, k) for k in ("player_id", "name", "people", "ready", "people_confirmed")}
        result["hero_id"] = self.hero_id if reveal_hero else None
        return result


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
    store: object = field(default=None, repr=False)
    capacity: int = 4
    initial_conditions: dict = field(default_factory=dict)
    setup_phase: str = "peoples"

    def record(self):
        return {"version": 1, "save_version": SAVE_VERSION, "action_version": ACTION_VERSION,
                "event_version": EVENT_VERSION, "code": self.code, "seed": self.seed,
                "revision": self.revision, "members": [asdict(m) for m in self.members],
                "capacity": self.capacity, "initial_conditions": self.initial_conditions,
                "setup_phase": self.setup_phase,
                "match": None if self.match is None else {
                    "state": state_to_dict(self.match["state"]), "events": self.match["events"]},
                "commands": [{"player_id": pid, "command_id": cid, **entry}
                             for (pid, cid), entry in sorted(self.commands.items())]}

    @classmethod
    def restore(cls, record, store):
        try:
            if (record["version"] != 1 or record["save_version"] != SAVE_VERSION
                    or record["action_version"] != ACTION_VERSION or record["event_version"] != EVENT_VERSION
                    or not re.fullmatch(r"[A-Z2-9]{8}", record["code"])
                    or type(record["seed"]) is not int or not 0 <= record["seed"] < 2**64
                    or type(record["revision"]) is not int or record["revision"] < 1):
                raise ValueError("Formato incompatível")
            members = [Member(**item) for item in record["members"]]
            phase = record.get("setup_phase", "heroes" if record["match"] else "peoples")
            if "setup_phase" not in record:
                for member in members:
                    member.people_confirmed = bool(record["match"])
                    if not record["match"]:
                        member.hero_id, member.ready = "", False
            capacity = record.get("capacity", 4)
            initial = validate_config(capacity, record.get("initial_conditions", {}))
            if (not 1 <= len(members) <= capacity or any(type(m.player_id) is not int for m in members)
                    or [m.player_id for m in members] != list(range(1, len(members) + 1))):
                raise ValueError("Participantes inválidos")
            for member in members:
                name(member.name)
                if (not re.fullmatch(r"[a-f0-9]{64}", member.credential_hash)
                        or type(member.ready) is not bool or type(member.people_confirmed) is not bool
                        or member.people not in (None, *server.PEOPLES)
                        or not isinstance(member.hero_id, str)):
                    raise ValueError("Sessão inválida")
                if member.people is None:
                    if member.hero_id or member.ready or member.people_confirmed:
                        raise ValueError("Escolha incompleta")
                elif member.people == "mortos_vivos":
                    if member.hero_id:
                        raise ValueError("Escolha de mortos-vivos inválida")
                elif (member.hero_id or member.ready) and member.hero_id not in {h.hero_id for h in server.heroes.heroes_for_people(member.people)}:
                    raise ValueError("Herói inválido")
            chosen = [m.people for m in members if m.people]
            if len(set(chosen)) != len(chosen):
                raise ValueError("Povos duplicados")
            if (phase not in ("peoples", "heroes")
                    or phase == "peoples" and any(m.hero_id or m.ready for m in members)
                    or phase == "heroes" and (len(members) != capacity or not all(m.people_confirmed for m in members))):
                raise ValueError("Etapa de preparação inválida")
            room = cls(record["code"], record["seed"], members=members, revision=record["revision"], store=store,
                       capacity=capacity, initial_conditions=initial, setup_phase=phase)
            if record["match"] is not None:
                state, events, _ = saves.validate({"version": SAVE_VERSION, **record["match"], "name": "Sala online"})
                if len(members) != capacity or len(state.players) != capacity or state.seed != room.seed:
                    raise ValueError("Partida incompatível")
                room.match = {"state": state, "events": events}
            for command in record["commands"]:
                pid, cid = command["player_id"], command["command_id"]
                entry = {k: command[k] for k in ("action", "fingerprint", "response")}
                if (type(pid) is not int or pid not in range(1, len(members) + 1)
                        or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cid)
                        or (pid, cid) in room.commands or entry["action"].get("player_id") != pid
                        or entry["fingerprint"] != json.dumps(entry["action"], sort_keys=True, allow_nan=False)
                        or entry["response"].get("success") is not True
                        or type(entry["response"].get("revision")) is not int
                        or not 1 <= entry["response"]["revision"] <= room.revision):
                    raise ValueError("Histórico de comandos inválido")
                room.commands[(pid, cid)] = entry
            return room
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise StorageError("Sala persistida incompatível ou danificada; banco preservado.") from exc

    def _commit(self, *, members=None, match=None, commands=None, initial_conditions=None, setup_phase=None):
        candidate = Room(self.code, self.seed, revision=self.revision + 1,
                         members=self.members if members is None else members,
                         match=self.match if match is None else match,
                         commands=self.commands if commands is None else commands,
                         capacity=self.capacity,
                         initial_conditions=self.initial_conditions if initial_conditions is None else initial_conditions,
                         setup_phase=self.setup_phase if setup_phase is None else setup_phase)
        if self.store:
            try:
                self.store.save(candidate.record(), self.revision)
            except StorageError as exc:
                raise RoomError(503, "Não foi possível salvar. A operação não foi aplicada; verifique o armazenamento do servidor.") from exc
        existing = {m.player_id: m for m in self.members}
        self.members = []
        for member in candidate.members:
            stable = existing.get(member.player_id, member)
            stable.__dict__.update(member.__dict__)
            self.members.append(stable)
        self.match, self.commands, self.revision = candidate.match, candidate.commands, candidate.revision
        self.initial_conditions = candidate.initial_conditions
        self.setup_phase = candidate.setup_phase
        for notify in tuple(self.listeners):
            notify(self.revision)

    def public(self, member):
        return {"version": 1, "code": self.code, "revision": self.revision,
                "status": "playing" if self.match else "lobby", "you": member.player_id,
                "host_id": 1, "players": [m.public(bool(self.match) or m.player_id == member.player_id) for m in self.members],
                "setup_phase": self.setup_phase,
                "capacity": self.capacity, "initial_conditions": deepcopy(self.initial_conditions)}

    def authenticate(self, credential):
        if not isinstance(credential, str) or not credential:
            raise RoomError(401, "Credencial de sessão necessária.")
        digest = hashlib.sha256(credential.encode()).hexdigest()
        member = next((m for m in self.members if secrets.compare_digest(m.credential_hash, digest)), None)
        if member is None:
            raise RoomError(403, "Sessão não pertence a esta sala.")
        return member

    def join(self, player_name):
        if self.match or len(self.members) >= self.capacity:
            raise RoomError(409, "Sala cheia ou partida já iniciada.")
        token = secrets.token_urlsafe(32)
        member = Member(len(self.members) + 1, name(player_name), hashlib.sha256(token.encode()).hexdigest())
        self._commit(members=[*self.members, member])
        return {"room": self.public(member), "credential": token}

    def rotate_credential(self, member, credential):
        if not isinstance(credential, str) or not re.fullmatch(r"[a-f0-9]{64}", credential):
            raise RoomError(422, "Nova credencial precisa conter 256 bits em hexadecimal.")
        digest = hashlib.sha256(credential.encode()).hexdigest()
        if any(m is not member and secrets.compare_digest(m.credential_hash, digest) for m in self.members):
            raise RoomError(422, "Credencial indisponível.")
        if not secrets.compare_digest(member.credential_hash, digest):
            members = deepcopy(self.members)
            members[member.player_id - 1].credential_hash = digest
            self._commit(members=members)
        return self.public(member)

    def select(self, member, people=None, hero_id=None):
        if self.match or member.ready or self.setup_phase == "peoples" and member.people_confirmed:
            raise RoomError(409, "Desmarque a confirmação antes de mudar sua escolha.")
        if self.setup_phase == "peoples":
            if hero_id not in (None, ""):
                raise RoomError(422, "Heróis só são escolhidos depois de todos confirmarem os povos.")
        else:
            if people not in (None, member.people):
                raise RoomError(409, "Os povos já foram confirmados e não podem mudar.")
            people = member.people
        choices = {h.hero_id for h in server.heroes.heroes_for_people(people)} if people in server.PEOPLES else set()
        if people not in server.PEOPLES or (self.setup_phase == "heroes" and people != "mortos_vivos" and hero_id not in choices):
            raise RoomError(422, "Povo ou herói inválido.")
        if people == "mortos_vivos" and hero_id not in (None, ""):
            raise RoomError(422, "Mortos-vivos escolhem heróis durante a partida.")
        if any(m is not member and m.people == people for m in self.members):
            raise RoomError(409, "Povo já escolhido nesta sala.")
        members = deepcopy(self.members)
        members[member.player_id - 1].people, members[member.player_id - 1].hero_id = people, hero_id or ""
        self._commit(members=members)
        return self.public(member)

    def mark_ready(self, member, ready):
        if self.match or type(ready) is not bool or not member.people:
            raise RoomError(422, "Escolha povo/herói antes de marcar pronto.")
        if self.setup_phase == "peoples":
            members = deepcopy(self.members)
            members[member.player_id - 1].people_confirmed = ready
            phase = "heroes" if len(members) == self.capacity and all(m.people_confirmed for m in members) else "peoples"
            if member.people_confirmed != ready:
                self._commit(members=members, setup_phase=phase)
        elif member.ready != ready:
            if ready and member.people != "mortos_vivos" and not member.hero_id:
                raise RoomError(422, "Escolha seu herói antes de confirmá-lo.")
            members = deepcopy(self.members)
            members[member.player_id - 1].ready = ready
            match = self._build_match(members) if all(m.ready for m in members) else None
            self._commit(members=members, match=match)
        return self.public(member)

    def _build_match(self, members):
        rows = [{"name": m.name, "people": m.people, "hero_id": m.hero_id,
                 "initial": self.initial_conditions.get(str(m.player_id), {})} for m in members]
        state = server._new_state(self.seed, rows)
        return {"state": state, "events": session.public_events(state)}

    def start(self, member):
        if member.player_id != 1:
            raise RoomError(403, "Somente o anfitrião inicia a partida.")
        if self.match:
            return self.public(member)
        if self.setup_phase != "heroes" or len(self.members) != self.capacity or not all(m.ready for m in self.members):
            raise RoomError(409, f"São necessários {self.capacity} jogadores prontos.")
        self._commit(match=self._build_match(self.members))
        return self.public(member)

    def configure(self, member, revision, configs):
        if member.player_id != 1:
            raise RoomError(403, "Somente o anfitrião configura a partida.")
        if self.match or type(revision) is not int or revision != self.revision:
            raise RoomError(409, "Sala atualizada ou partida já iniciada.")
        checked = validate_config(self.capacity, configs)
        if checked != self.initial_conditions:
            members = deepcopy(self.members)
            for participant in members:
                participant.ready = False
                if self.setup_phase == "peoples":
                    participant.people_confirmed = False
            self._commit(members=members, initial_conditions=checked)
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
        response = {**result, "revision": self.revision + 1, "pending": bool(state.web_reaction),
                    "events": server._visible_events(result["events"], member.player_id)}
        commands = {**self.commands, key: {"fingerprint": fingerprint, "action": action, "response": deepcopy(response)}}
        self._commit(match={"state": state, "events": self.match["events"] + result["events"]}, commands=commands)
        return response


class Registry:
    def __init__(self, store=None, max_rooms=256):
        self.store = store
        self.max_rooms = max_rooms
        self.rooms = {}
        if store:
            for record in store.load():
                room = Room.restore(record, store)
                self.rooms[room.code] = room
        self.lock = threading.RLock()

    def create(self, player_name, capacity=4):
        player_name = name(player_name)
        validate_config(capacity, {})
        with self.lock:
            if len(self.rooms) >= self.max_rooms:
                raise RoomError(503, "Limite de salas atingido. O operador precisa revisar a capacidade; nenhuma sala foi apagada.")
            while (code := "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))) in self.rooms:
                pass
            room = Room(code, secrets.randbits(64), store=self.store, capacity=capacity)
            result = room.join(player_name)
            self.rooms[code] = room
            return result

    def get(self, code):
        with self.lock:
            room = self.rooms.get(code)
        if room is None:
            raise RoomError(404, "Sala não encontrada.")
        return room
