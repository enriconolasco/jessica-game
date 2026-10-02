"""Cópias privadas consistentes; falhas não desfazem ações já persistidas."""
import sys
import time
import threading
from .room_store import StorageError


class OnlineBackups:
    def __init__(self, store, interval=3600, clock=time.monotonic):
        self.store = store
        self.interval = interval
        self.clock = clock
        self.next_attempt = 0
        self.saved_generation = None
        self.lock = threading.Lock()

    def checkpoint(self, force=False):
        with self.lock:
            return self._checkpoint(force)

    def _checkpoint(self, force):
        now = self.clock()
        if not force and now < self.next_attempt:
            return None
        self.next_attempt = now + self.interval
        if self.saved_generation == self.store.generation:
            return None
        try:
            path, generation = self.store.backup()
        except StorageError as exc:
            print(f"AVISO: {exc} Verifique espaço/permissões e guarde uma cópia privada.", file=sys.stderr, flush=True)
            return None
        self.saved_generation = generation
        return path
