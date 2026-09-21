"""Testes: Boin."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, buy_artifact_with_gold, transmute_artifact_with_magic,
    resolve_pending_artifact_choice, summon_troop,
)
from jessica.core.constants import TroopArchetype, CENTER
from jessica.core.models import Troop


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


def _force_boin_player(state, pid):
    """Faz o jogador pid escolher 7 Anões e invoca ate Boin."""
    p = state.players[pid - 1]
    p.people = "anoes"
    p.chosen_hero_id = "seven_dwarves"
    p.city.magic = 30
    for _ in range(4):
        summon_hero(state, pid)
    return next(u for u in p.units if u.hero_id == "boin")


def _fake_center_troop(state, pid):
    """Adiciona uma Tropa fake no Centro para o jogador pid, contornando a
    restricao de '7 Anões nao pode invocar Tropa'."""
    p = state.players[pid - 1]
    t = Troop(
        id=f"p{pid}_fake_center",
        owner_id=pid,
        house=CENTER,
        life=4, life_max=4,
        archetype=TroopArchetype.LIGHT,
    )
    p.units.append(t)
    return t


def test_boin_buy_draws_2_picks_1():
    state = make_state()
    _force_boin_player(state, 3)
    _fake_center_troop(state, 3)
    p = state.players[2]
    p.city.gold = 20
    hand_before = len(p.hand)
    shop_before = state.shop.size()

    result = buy_artifact_with_gold(state, 3)
    assert result is None, "Boin deveria devolver None"
    pending = p.pending_artifact_choice
    assert pending is not None
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    print(f"OK  - Boin: comprou e recebeu 2 cartas")
    chosen = pending["cards"][0]
    resolve_pending_artifact_choice(state, 3, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1
    assert state.shop.size() == shop_before - 1
    print(f"OK  - Boin: escolheu 1")


def test_boin_transmute_draws_2_picks_1():
    state = make_state()
    _force_boin_player(state, 3)
    p = state.players[2]
    p.city.magic = 20
    hand_before = len(p.hand)
    result = transmute_artifact_with_magic(state, 3)
    assert result is None
    pending = p.pending_artifact_choice
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    chosen = pending["cards"][1]
    resolve_pending_artifact_choice(state, 3, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1
    print("OK  - Boin transmutou com escolha 2-de-1")


def test_no_boin_buy_direct():
    state = make_state()
    _fake_center_troop(state, 1)
    p = state.players[0]
    p.city.gold = 20
    result = buy_artifact_with_gold(state, 1)
    assert result is not None
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
