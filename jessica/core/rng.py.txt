from __future__ import annotations

MASK64 = 0xFFFFFFFFFFFFFFFF


class DeterministicRNG:
    """
    SplitMix64. Estado é apenas um inteiro — serializável em JSON.
    Interface compatível com o subconjunto de random.Random que usamos.
    """

    def __init__(self, seed: int):
        self.state = seed & MASK64

    def _next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return (z ^ (z >> 31)) & MASK64

    def randint(self, a: int, b: int) -> int:
        """Inclusivo em ambos os lados (igual random.Random.randint)."""
        span = b - a + 1
        return a + (self._next_u64() % span)

    def randrange(self, n: int) -> int:
        if n <= 0:
            raise ValueError("randrange: n deve ser > 0")
        return self._next_u64() % n

    def choice(self, seq):
        if not seq:
            raise IndexError("choice: sequência vazia")
        return seq[self.randrange(len(seq))]

    def shuffle(self, seq) -> None:
        for i in range(len(seq) - 1, 0, -1):
            j = self.randrange(i + 1)
            seq[i], seq[j] = seq[j], seq[i]

    def to_dict(self) -> dict:
        return {"state": self.state}

    @classmethod
    def from_dict(cls, data: dict) -> "DeterministicRNG":
        rng = cls(0)
        rng.state = data["state"]
        return rng