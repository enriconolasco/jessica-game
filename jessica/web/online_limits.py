"""Limites locais do transporte; não expiram partidas nem alteram regras."""
from collections import OrderedDict
import math
import threading
import time


class RequestLimits:
    def __init__(self, clock=time.monotonic, max_keys=2048):
        self.clock = clock
        self.max_keys = max_keys
        self.buckets = OrderedDict()
        self.lock = threading.Lock()

    def delay(self, address, category="api"):
        capacity, rate = (8, 0.05) if category == "create" else (120, 20)
        now = self.clock()
        key = (address, category)
        with self.lock:
            while self.buckets and next(iter(self.buckets.values()))[1] < now - 600:
                self.buckets.popitem(last=False)
            previous = self.buckets.get(key)
            if previous is None and len(self.buckets) >= self.max_keys:
                return 5
            tokens = capacity if previous is None else min(capacity, previous[0] + max(0, now - previous[1]) * rate)
            wait = 0 if tokens >= 1 else math.ceil((1 - tokens) / rate)
            self.buckets[key] = (tokens - 1 if wait == 0 else tokens, now)
            self.buckets.move_to_end(key)
            return wait
