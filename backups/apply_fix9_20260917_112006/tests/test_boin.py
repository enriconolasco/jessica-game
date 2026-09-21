"""Testes: Boin."""
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
    """Invoca em sequencia ate chegar em Boin. So funciona se pid escolheu Os 7 Anoes."""
    p = state.players[pid - 1]
    p.city.magic = 20
    for _ in range(4):
        summon_hero(state, pid)
    return next(u for u in p.units if u.hero_id == "boin")


def _center_troop(state, pid):
    """Tropa no Centro (funciona se povo nao for 7 Anoes)."""
    p = state.players[pid - 1]
    p.city.gold = max(p.city.gold, 10)
    p.city.magic = max(p.city.magic, 5)
    t = summon_troop(state, pid, TroopArchetype.LIGHT, 4)
    t.house = CENTER
    return t


def _setup_boin_on_j1(state):
    """Boin no jogador 1 (Humanos): muda chosen_hero_id pra seven_dwarves."""
    p1 = state.players[0]
    p1.people = "anoes"
    p1.chosen_hero_id = "seven_dwarves"
    p1.city.magic = 20
    for _ in range(4):
        summon_hero(state, 1)
    return next(u for u in p1.units if u.hero_id == "boin")


def test_boin_buy_draws_2_picks_1():
    state = make_state()
    # Usa J3 (Orcs) - sem restricao de tropa
    # Mas Boin pertence a anoes. Faz J3 ser anoes com 7 anoes.
    p3 = state.players[2]
    p3.people = "anoes"
    p3.chosen_hero_id = "seven_dwarves"
    p3.city.magic = 20
    for _ in range(4):
        summon_hero(state, 3)
    # Tropa pelo J1 (nao-anao)
    _center_troop(state, 1)
    p3.city.gold = 20
    hand_before = len(p3.hand)
    shop_before = state.shop.size()

    result = buy_artifact_with_gold(state, 3)
    assert result is None, "Boin deveria devolver None"
    pending = p3.pending_artifact_choice
    assert pending is not None
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    cards = pending["cards"]
    print(f"OK  - Boin: comprou e recebeu 2 cartas: {cards}")
    chosen = pending["cards"][0]
    resolve_pending_artifact_choice(state, 3, kept_cards=[chosen])
    assert chosen in p3.hand
    assert len(p3.hand) == hand_before + 1
    assert state.shop.size() == shop_before - 1
    print(f"OK  - Boin: escolheu {chosen}")


def test_boin_transmute_draws_2_picks_1():
    state = make_state()
    p3 = state.players[2]
    p3.people = "anoes"
    p3.chosen_hero_id = "seven_dwarves"
    p3.city.magic = 20
    for _ in range(4):
        summon_hero(state, 3)
    p3.city.magic = 20
    hand_before = len(p3.hand)
    result = transmute_artifact_with_magic(state, 3)
    assert result is None
    pending = p3.pending_artifact_choice
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    chosen = pending["cards"][1]
    resolve_pending_artifact_choice(state, 3, kept_cards=[chosen])
    assert chosen in p3.hand
    assert len(p3.hand) == hand_before + 1
    print("OK  - Boin transmutou com escolha 2-de-1")


def test_no_boin_buy_direct():
    state = make_state()
    _center_troop(state, 1)
    p1 = state.players[0]
    p1.city.gold = 20
    result = buy_artifact_with_gold(state, 1)
    assert result is not None
    assert result in p1.hand
    assert p1.pending_artifact_choice is None
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
