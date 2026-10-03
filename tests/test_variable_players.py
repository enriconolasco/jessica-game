"""Configuração compartilhada, casas dinâmicas, recompensa e recuperação."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from io import StringIO
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jessica.core import combat
from jessica.core.constants import Phase
from jessica.core.models import Troop
from jessica.core.state import create_empty_state, game_houses
from jessica.core.headless import SAVE_VERSION, apply_action, legal_actions, view_for_player
from jessica.core.serialize import state_to_dict
from jessica.web import server, saves
from jessica.web.rooms import Registry, Room, RoomError
from jessica.web.room_store import RoomStore

ROWS = [{"name": f"J{i}", "people": p, "hero_id": h} for i, (p, h) in enumerate([
    ("humanos", "miyamoto"), ("anoes", "ori"), ("orcs", "arken"),
    ("fadas", "ainai"), ("vampiros", "luide_vampa")], 1)]


def rejects(callback, exception=ValueError):
    try:
        callback()
    except exception:
        return
    raise AssertionError("Configuração inválida foi aceita")


def test_setup_individual_seed_save_and_privacy_all_counts():
    for count in range(2, 6):
        rows = deepcopy(ROWS[:count])
        rows[0]["initial"] = {"city_life": 9, "gold": 9, "magic": 7, "artifacts": 2}
        a, b = server._new_state(42, rows), server._new_state(42, rows)
        assert state_to_dict(a) == state_to_dict(b)
        assert len(a.players) == count and len(game_houses(a)) == count + 1
        p = a.players[0]
        assert p.city.life == 9 and p.city.life_max == 9
        assert p.city.magic == 7 and len(p.hand) == 2
        assert a.players[1].city.gold == 0 and not a.players[1].hand
        public = view_for_player(a, 2)
        assert len(public["players"]) == count
        assert all("hand" not in player for player in public["players"])
        restored, _, _ = saves.validate({"version": SAVE_VERSION, "state": state_to_dict(a)})
        assert state_to_dict(restored) == state_to_dict(a)


def test_day_night_and_curuna_rotation_all_counts():
    for count in range(2, 6):
        state = server._new_state(42, ROWS[:count])
        for _ in range(120):
            if state.turn == 3:
                break
            options = legal_actions(state, state.active_player_id)
            action = next((a for kind in ("end_turn", "finish_night", "night_pass", "night_window_done", "night_setup")
                           for a in options if a["type"] == kind), None)
            assert action is not None, options
            result = apply_action(state, action)
            assert result["success"], result
        assert state.turn == 3 and state.curuna_id in range(1, count + 1)


def test_reward_counts_players_before_each_elimination():
    for count in range(2, 6):
        state = create_empty_state(num_players=count, city_life=1)
        state.phase = Phase.NIGHT
        for target in range(count, 1, -1):
            attacker = Troop(id=f"attack{target}", owner_id=1, house=f"city_{target}", life=8, life_max=8)
            state.players[0].units.append(attacker)
            before = len(state.players[0].hand)
            combat.resolve_attack(state, combat.Attack(attacker.id, "city", str(target)))
            assert len(state.players[0].hand) - before == target


def test_dragon_base_initial_override_and_elimination_reward():
    rows = deepcopy(ROWS[:3])
    rows[1] = {"name":"Dragão", "people":"dragoes", "hero_id":"barba_negra", "initial":{"city_life":5}}
    state = server._new_state(42, rows)
    base = state.players[1].units[0]
    assert base.life == base.life_max == state.players[1].city.life == 5
    base.life = 0
    base.killed_by_player_id = 1
    combat._cleanup_dead(state)
    assert len(state.players[0].hand) == 3 and state.players[1].city.life == 0
    combat._cleanup_dead(state)
    assert len(state.players[0].hand) == 3


def test_invalid_configuration_and_missing_cities_rejected():
    for count in (0, 1, 6):
        rejects(lambda: server._new_state(42, ROWS[:count] if count != 6 else ROWS * 2))
    for value in ({"gold":-1}, {"magic":True}, {"artifacts":25}, {"city_life":0}, {"oops":3}):
        rows = deepcopy(ROWS[:2]); rows[0]["initial"] = value
        rejects(lambda: server._new_state(42, rows))
    rejects(lambda: server._new_state(42, ROWS[:5], {"artifacts":5}))
    state = server._new_state(42, ROWS[:2])
    state.players[0].units.append(Troop(id="bad", owner_id=1, house="city_3", life=4, life_max=4))
    rejects(lambda: saves.validate({"version":SAVE_VERSION,"state":state_to_dict(state)}))


def test_rooms_capacity_config_permissions_and_restore_all_counts():
    for count in range(2, 6):
        with TemporaryDirectory() as directory:
            store = RoomStore(Path(directory) / "rooms.sqlite3")
            try:
                registry = Registry(store)
                created = registry.create("J1", count)
                room = registry.get(created["room"]["code"])
                for pid in range(2, count + 1):
                    room.join(f"J{pid}")
                rejects(lambda: room.join("extra"), RoomError)
                for member, row in zip(room.members, ROWS):
                    room.select(member, row["people"])
                    room.mark_ready(member, True)
                before = room.record()
                rejects(lambda: room.configure(room.members[1], room.revision, {}), RoomError)
                rejects(lambda: room.configure(room.members[0], room.revision - 1, {}), RoomError)
                assert room.record() == before
                room.configure(room.members[0], room.revision, {"1":{"magic":8,"artifacts":2}})
                assert not any(m.ready for m in room.members)
                for member, row in zip(room.members, ROWS):
                    room.select(member, hero_id=row["hero_id"])
                    room.mark_ready(member, True)
                room.start(room.members[0])
                assert len(room.match["state"].players) == count
                assert len(room.match["state"].players[0].hand) == 2
                recovered = Registry(store).get(room.code)
                assert recovered.capacity == count and recovered.initial_conditions == room.initial_conditions
                assert state_to_dict(recovered.match["state"]) == state_to_dict(room.match["state"])
                rejects(lambda: room.configure(room.members[0], room.revision, {}), RoomError)
            finally:
                store.close()


def test_old_room_defaults_and_invalid_count():
    registry = Registry(); created = registry.create("J1")
    record = registry.get(created["room"]["code"]).record()
    record.pop("capacity"); record.pop("initial_conditions")
    restored = Room.restore(record, None)
    assert restored.capacity == 4 and restored.initial_conditions == {}
    for count in (1, 6, True, "3"):
        rejects(lambda: registry.create("J1", count), RoomError)


def test_terminal_pregame_and_map_all_counts():
    from rich.console import Console
    from jessica import main
    for count in range(2, 6):
        output = StringIO()
        with patch.object(main, "console", Console(file=output, width=100)), \
                patch.object(main, "_ask_int", side_effect=[42,count,2,6,0,0,1]), \
                patch.object(main, "pick_index", return_value=0), \
                patch.object(main.Prompt, "ask", side_effect=[*(f"Pessoa{i}" for i in range(1,count+1)), *([""] * count),"n"]):
            state = main.setup_ui()
            main.show_map(state)
        assert len(state.players) == count and all(len(p.hand) == 1 for p in state.players)
        assert all(f"Pessoa{i}" in output.getvalue() for i in range(1,count+1))


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
