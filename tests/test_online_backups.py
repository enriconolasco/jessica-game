from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import json
import sys
import subprocess
import threading
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.online_backups import OnlineBackups
from jessica.web.rooms import Registry
from jessica.web.room_store import StorageError
from test_online_persistence import store_at, process_server, free_port_pair
from test_online_rooms import http, started, request, envelope


def test_consistent_backup_restores_state_rng_private_views_and_deduplication():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with store_at(path) as store, http(Registry(store)) as base:
            code, tokens, room = started(base)
            command = envelope(base, code, tokens[0])
            result = request(base, f"/rooms/{code}/actions", command, tokens[0])
            assert result[0] == 200
            before = room.record()
            views = [room.snapshot(room.authenticate(token)) for token in tokens]
            backup, generation = store.backup()
            assert generation == store.generation
            assert room.record() == before and backup.parent == store.path.parent / "backups"
            with store_at(backup) as restored_store:
                restored = Registry(restored_store).get(code)
                assert restored.record() == before
                assert [restored.snapshot(restored.authenticate(token)) for token in tokens] == views
                assert restored.apply(restored.authenticate(tokens[0]), command) == result[1]
                assert all(token not in json.dumps(restored_store.load()) for token in tokens)


def test_hourly_schedule_shutdown_and_no_overwrite_or_duplicate_idle_backup():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store:
        now = [0]
        scheduler = OnlineBackups(store, clock=lambda: now[0])
        initial = scheduler.checkpoint()
        original = initial.read_bytes()
        registry = Registry(store)
        registry.create("Ana")
        now[0] = 3599
        assert scheduler.checkpoint() is None
        now[0] = 3600
        hourly = scheduler.checkpoint()
        assert hourly != initial and initial.read_bytes() == original
        now[0] = 7200
        assert scheduler.checkpoint() is None
        registry.create("Beto")
        final = scheduler.checkpoint(force=True)
        assert final not in (initial, hourly)
        assert scheduler.checkpoint(force=True) is None
        assert len(list(initial.parent.glob("*.sqlite3"))) == 3


def test_backup_failure_warns_does_not_undo_action_and_retries():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store:
        registry = Registry(store)
        created = registry.create("Ana")
        before = store.load()
        now = [0]
        scheduler = OnlineBackups(store, clock=lambda: now[0])
        warning = StringIO()
        with patch.object(store, "backup", side_effect=StorageError("Falha simulada")), redirect_stderr(warning):
            assert scheduler.checkpoint() is None
        assert "AVISO" in warning.getvalue()
        assert created["credential"] not in warning.getvalue() and store.load() == before
        now[0] = 3600
        assert scheduler.checkpoint().exists()
        assert store.load() == before


def test_failed_publication_preserves_previous_copy_and_cleans_temporary_file():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store:
        Registry(store).create("Ana")
        previous, _ = store.backup()
        contents = previous.read_bytes()
        with patch("jessica.web.room_store.os.replace", side_effect=OSError("Falha simulada")):
            try:
                store.backup()
                raise AssertionError("Falha ignorada")
            except StorageError:
                pass
        assert previous.read_bytes() == contents
        assert list(previous.parent.iterdir()) == [previous]
        assert store.load()[0]["members"][0]["name"] == "Ana"


def test_concurrent_backups_and_commits_are_complete_valid_snapshots():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store:
        registry = Registry(store)
        created = registry.create("Ana")
        room = registry.get(created["room"]["code"])

        def work(index):
            if index % 2:
                with room.lock:
                    room._commit()
                return None
            return store.backup()[0]

        with ThreadPoolExecutor(max_workers=4) as pool:
            snapshots = [path for path in pool.map(work, range(12)) if path]
        assert len(set(snapshots)) == 6 and room.revision == 7
        for snapshot in snapshots:
            with store_at(snapshot) as restored_store:
                restored = Registry(restored_store).get(room.code)
                assert 1 <= restored.revision <= room.revision
                assert restored.authenticate(created["credential"]).player_id == 1


def test_rejected_save_does_not_trigger_new_backup_or_expose_files():
    with TemporaryDirectory() as folder, store_at(Path(folder) / "rooms.sqlite3") as store:
        registry = Registry(store)
        created = registry.create("Ana")
        scheduler = OnlineBackups(store)
        snapshot = scheduler.checkpoint()
        generation = store.generation
        record = store.load()[0]
        try:
            store.save(record, 99)
            raise AssertionError("Revisão inválida aceita")
        except StorageError:
            pass
        assert store.generation == generation and scheduler.checkpoint(force=True) is None
        with http(registry) as base:
            for route in (f"/saves/online/backups/{snapshot.name}", f"/static/../../saves/online/backups/{snapshot.name}"):
                assert request(base, route, token=created["credential"])[0] >= 400


def test_real_server_creates_private_startup_backup():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        with process_server(path, free_port_pair()) as base:
            copies = list((path.parent / "backups").glob("*.sqlite3"))
            assert len(copies) == 1
            with store_at(copies[0]) as copy:
                assert Registry(copy).rooms == {}
            assert request(base, "/rooms", {"name":"Ana"})[0] == 201


def test_normal_shutdown_backs_up_changes_before_closing_database():
    wrapper = """
import asyncio, _thread, sys, threading
from contextlib import asynccontextmanager
from jessica.web import notifications, online_server
original = notifications.serve_notifications
@asynccontextmanager
async def controlled(*args, **kwargs):
    async with original(*args, **kwargs):
        loop = asyncio.get_running_loop()
        def stop():
            sys.stdin.readline()
            loop.call_soon_threadsafe(_thread.interrupt_main)
        threading.Thread(target=stop, daemon=True).start()
        yield
notifications.serve_notifications = controlled
online_server.main()
"""
    with TemporaryDirectory() as folder:
        path = Path(folder) / "rooms.sqlite3"
        port = free_port_pair()
        process = subprocess.Popen([sys.executable, "-u", "-B", "-c", wrapper, "--storage", str(path), "--port", str(port)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8")
        ready, lines = threading.Event(), []
        def read():
            for line in process.stdout:
                lines.append(line)
                if "WebSocket" in line:
                    ready.set()
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            assert ready.wait(10) and process.poll() is None, "Servidor não iniciou"
            status, created = request(f"http://127.0.0.1:{port}", "/rooms", {"name":"Ana"})
            assert status == 201
            process.stdin.write("\n"); process.stdin.flush()
            assert process.wait(timeout=15) == 0, "".join(lines)
            reader.join(timeout=5)
            copies = list((path.parent / "backups").glob("*.sqlite3"))
            assert len(copies) == 2
            restored = []
            for snapshot in copies:
                with store_at(snapshot) as copy:
                    restored.extend(Registry(copy).rooms.values())
            assert len(restored) == 1
            assert restored[0].authenticate(created["credential"]).name == "Ana"
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            reader.join(timeout=5)
            process.stdin.close(); process.stdout.close()


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
