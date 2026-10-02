"""Snapshots online transacionais, privados e exclusivos de um servidor."""
import json
import os
from pathlib import Path
import sqlite3
import threading
import tempfile
from datetime import datetime, timezone
from contextlib import closing


class StorageError(OSError):
    pass


class RoomStore:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.connection = None
        self.owner = None
        self.lock = threading.RLock()
        self.generation = 0
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.owner = self.path.with_suffix(self.path.suffix + ".lock").open("a+b")
            self.owner.seek(0, os.SEEK_END)
            if not self.owner.tell():
                self.owner.write(b"1")
                self.owner.flush()
            self.owner.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.connection = sqlite3.connect(self.path, check_same_thread=False)
            self.connection.execute("PRAGMA synchronous=FULL")
            version = self.connection.execute("PRAGMA user_version").fetchone()[0]
            tables = self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version not in (0, 1) or version == 0 and tables or version == 1 and tables != [("rooms",)]:
                raise StorageError("Banco online incompatível; arquivo preservado.")
            if version == 0:
                with self.connection:
                    self.connection.execute("CREATE TABLE rooms (code TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL)")
                    self.connection.execute("PRAGMA user_version=1")
        except (OSError, sqlite3.Error) as exc:
            self.close()
            raise StorageError("Armazenamento online indisponível, ocupado ou incompatível; nenhum arquivo foi descartado.") from exc

    def load(self):
        try:
            with self.lock:
                rows = self.connection.execute("SELECT code, revision, payload FROM rooms ORDER BY code").fetchall()
            result = []
            for code, revision, raw in rows:
                payload = json.loads(raw)
                if not isinstance(payload, dict) or payload.get("code") != code or payload.get("revision") != revision:
                    raise ValueError("Registro inconsistente")
                result.append(payload)
            return result
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise StorageError("Não foi possível recuperar as salas; banco preservado.") from exc

    def save(self, payload, previous_revision):
        try:
            raw = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            with self.lock:
                with self.connection:
                    if previous_revision == 0:
                        self.connection.execute("INSERT INTO rooms VALUES (?, ?, ?)", (payload["code"], payload["revision"], raw))
                    else:
                        changed = self.connection.execute("UPDATE rooms SET revision=?, payload=? WHERE code=? AND revision=?",
                            (payload["revision"], raw, payload["code"], previous_revision)).rowcount
                        if changed != 1:
                            raise StorageError("Revisão persistida divergente; atualização não gravada.")
                self.generation += 1
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise StorageError("Não foi possível gravar a sala.") from exc

    def backup(self):
        temporary = None
        try:
            folder = self.path.parent / "backups"
            folder.mkdir(parents=True, exist_ok=True)
            descriptor, filename = tempfile.mkstemp(prefix=f".{self.path.name}-", suffix=".tmp", dir=folder)
            os.close(descriptor)
            temporary = Path(filename)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            target = folder / f"{self.path.name}-{stamp}-{temporary.stem.rsplit('-', 1)[-1]}.sqlite3"
            with self.lock:
                generation = self.generation
                with closing(sqlite3.connect(temporary)) as destination:
                    self.connection.backup(destination)
                    if destination.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                        raise StorageError("Verificação do backup falhou.")
                with temporary.open("r+b") as snapshot:
                    os.fsync(snapshot.fileno())
                os.replace(temporary, target)
            return target, generation
        except (OSError, sqlite3.Error) as exc:
            raise StorageError("Backup online não gravado; banco principal preservado.") from exc
        finally:
            if temporary is not None and temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.owner:
            self.owner.close()
            self.owner = None
