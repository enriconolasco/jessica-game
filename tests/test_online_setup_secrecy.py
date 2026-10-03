"""Povos públicos antes de heróis privados; revelação só com partida criada."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.rooms import Registry, Room, RoomError
from jessica.web.room_store import RoomStore, StorageError
from test_variable_players import ROWS, rejects
from test_online_rooms import http, request


def heroes_stage(registry, count=2):
    created = registry.create("J1", count)
    room = registry.get(created["room"]["code"])
    tokens = [created["credential"]]
    for pid in range(2, count + 1):
        tokens.append(room.join(f"J{pid}")["credential"])
    for member, row in zip(room.members, ROWS):
        room.select(member, row["people"])
        room.mark_ready(member, True)
    assert room.setup_phase == "heroes" and room.match is None
    return room, tokens


def test_all_counts_public_peoples_private_heroes_and_automatic_start():
    for count in range(2, 6):
        room, tokens = heroes_stage(Registry(), count)
        assert all(m.people_confirmed for m in room.members)
        rejects(lambda: room.select(room.members[0], people="demonios"), RoomError)
        for i, (member, row) in enumerate(zip(room.members, ROWS)):
            room.select(member, hero_id=row["hero_id"])
            if i < count - 1:
                for viewer in room.members:
                    public = room.public(viewer)
                    assert public["players"][i]["people"] == row["people"]
                    assert public["players"][i]["hero_id"] == (row["hero_id"] if viewer is member else None)
                assert room.match is None
            room.mark_ready(member, True)
            assert bool(room.match) == (i == count - 1)
        for viewer in room.members:
            assert [p["hero_id"] for p in room.public(viewer)["players"]] == [r["hero_id"] for r in ROWS[:count]]
            assert room.public(viewer)["status"] == "playing"


def test_http_early_choices_and_privacy_even_for_host():
    registry = Registry()
    created = registry.create("Host", 2); room = registry.get(created["room"]["code"])
    host = created["credential"]; guest = room.join("Guest")["credential"]
    with http(registry) as base:
        route = f"/rooms/{room.code}"
        before = room.record()
        assert request(base, route + "/select", {"people":"humanos","hero_id":"miyamoto"}, host)[0] == 422
        assert room.record() == before
        for token, people in ((host,"humanos"),(guest,"anoes")):
            assert request(base, route + "/select", {"people":people}, token)[0] == 200
            assert request(base, route + "/ready", {"ready":True}, token)[0] == 200
        assert request(base, route + "/select", {"hero_id":"ori"}, guest)[0] == 200
        assert request(base, route + "/ready", {"ready":True}, guest)[0] == 200
        public = request(base, route, token=host)[1]
        assert public["players"][1]["hero_id"] is None
        assert "ori" not in json.dumps(public)
        assert request(base, route + "/snapshot", token=host)[0] == 409
        assert request(base, route + "/select", {"hero_id":"miyamoto"}, host)[0] == 200
        public = request(base, route + "/ready", {"ready":True}, host)[1]
        assert public["status"] == "playing" and public["players"][1]["hero_id"] == "ori"


def test_restart_preserves_secret_and_failed_final_confirmation_is_atomic():
    with TemporaryDirectory() as directory:
        store = RoomStore(Path(directory) / "rooms.sqlite3")
        try:
            room, tokens = heroes_stage(Registry(store))
            room.select(room.members[0], hero_id="miyamoto")
            room.mark_ready(room.members[0], True)
            restored = Registry(store).get(room.code)
            assert restored.public(restored.authenticate(tokens[1]))["players"][0]["hero_id"] is None
            assert restored.public(restored.authenticate(tokens[0]))["players"][0]["hero_id"] == "miyamoto"
            room.select(room.members[1], hero_id="ori")
            before, disk = room.record(), store.load()
            with patch.object(store, "save", side_effect=StorageError("disk full")):
                rejects(lambda: room.mark_ready(room.members[1], True), RoomError)
            assert room.record() == before and store.load() == disk and room.match is None
            assert room.public(room.members[1])["players"][0]["hero_id"] is None
            room.mark_ready(room.members[1], True)
            assert Registry(store).get(room.code).match is not None
        finally:
            store.close()


def test_legacy_lobby_reconfirms_without_revealing_and_matches_survive():
    room, tokens = heroes_stage(Registry())
    for member, row in zip(room.members, ROWS):
        room.select(member, hero_id=row["hero_id"])
    record = room.record(); record.pop("setup_phase")
    for member in record["members"]:
        member.pop("people_confirmed")
    restored = Room.restore(record, None)
    assert restored.setup_phase == "peoples" and all(not m.hero_id and not m.people_confirmed for m in restored.members)
    for member in room.members:
        room.mark_ready(member, True)
    record = room.record(); record.pop("setup_phase")
    for member in record["members"]:
        member.pop("people_confirmed")
    assert Room.restore(record, None).match is not None


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test(); passed += 1
            except Exception as exc:
                failed += 1; print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(bool(failed))
