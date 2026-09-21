"""Testes: Boin (ve 2, escolhe 1)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, buy_artifact_with_gold, transmute_artifact_with_magic,
    resolve_pending_artifact_choice, summon_troop,
)
from jessica.core.constants import TroopArchetype, CENTER


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["seven_dwarves"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "Os 7 Anões"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def _summon_until_boin(state, pid):
    """Invoca em sequencia ate chegar em Boin (indice 3)."""
    p = state.players[pid - 1]
    p.city.magic = 20
    for _ in range(4):
        summon_hero(state, pid)
    return next(u for u in p.units if u.hero_id == "boin")


def _center_troop(state, pid):
    p = state.players[pid - 1]
    p.city.gold = max(p.city.gold, 10)
    p.city.magic = max(p.city.magic, 5)
    t = summon_troop(state, pid, TroopArchetype.LIGHT, 4)
    t.house = CENTER
    return t


def test_boin_buy_draws_2_picks_1():
    state = make_state()
    _summon_until_boin(state, 2)
    _center_troop(state, 2)
    p = state.players[1]
    p.city.gold = 20
    hand_before = len(p.hand)
    shop_before = state.shop.size()

    result = buy_artifact_with_gold(state, 2)
    assert result is None, "Boin deveria devolver None (pending choice)"
    pending = p.pending_artifact_choice
    assert pending is not None
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    print(f"OK  - Boin: comprou e recebeu 2 cartas para escolher: {pending[\'cards\']}")

    chosen = pending["cards"][0]
    resolve_pending_artifact_choice(state, 2, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1, f"Esperado +1 carta, veio {len(p.hand) - hand_before}"
    # Shop: -2 (draw) +1 (devolveu rejeitada) = -1 liquido
    assert state.shop.size() == shop_before - 1,         f"Loja esperada {shop_before - 1}, veio {state.shop.size()}"
    print(f"OK  - Boin: escolheu {chosen}, outra devolvida a Loja")


def test_boin_transmute_draws_2_picks_1():
    state = make_state()
    _summon_until_boin(state, 2)
    p = state.players[1]
    p.city.magic = 20
    hand_before = len(p.hand)

    result = transmute_artifact_with_magic(state, 2)
    assert result is None
    pending = p.pending_artifact_choice
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    chosen = pending["cards"][1]
    resolve_pending_artifact_choice(state, 2, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1
    print("OK  - Boin transmutou com escolha 2-de-1")


def test_no_boin_buy_direct():
    """Sem Boin vivo, compra direta (1 carta)."""
    state = make_state()
    _center_troop(state, 2)
    p = state.players[1]
    p.city.gold = 20
    result = buy_artifact_with_gold(state, 2)
    assert result is not None, "Sem Boin, compra direta"
    assert result in p.hand
    assert p.pending_artifact_choice is None
    print("OK  - Sem Boin: compra direta (1 carta)")


def run_all():
    tests = [
        test_boin_buy_draws_2_picks_1,
        test_boin_transmute_draws_2_picks_1,
        test_no_boin_buy_direct,
    ]
    print("=== Testes Boin ===\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
