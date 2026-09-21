"""Testes de K-heart e K-diamonds (on_turn_start)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import play_artifact, discard_field_artifact, ActionError
from jessica.core.turn import start_turn
from jessica.core.serialize import state_to_dict, state_from_dict


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_play_not_in_hand():
    state = make_state()
    try:
        play_artifact(state, 1, "K_H")
        raise AssertionError("Deveria bloquear carta fora da mao")
    except ActionError as e:
        print(f"OK  - Carta fora da mao bloqueada: {e}")


def test_play_k_h_raises_life_max():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    before = p.city.life_max
    play_artifact(state, 1, "K_H")
    assert p.city.life_max == before + 1
    assert p.city.life == 2
    assert "K_H" not in p.hand
    assert any(a.card_id == "K_H" for a in p.field_artifacts)
    print(f"OK  - Kh: life_max {before} -> {p.city.life_max}")


def test_play_k_d():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_D")
    play_artifact(state, 1, "K_D")
    assert "K_D" not in p.hand
    assert any(a.card_id == "K_D" for a in p.field_artifacts)
    print("OK  - Kd jogado para o campo")


def test_morning_k_h_heals():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    state.turn = 2
    start_turn(state)
    assert p.city.life == 3, f"Esperado 3, veio {p.city.life}"
    print("OK  - Kh manha: +1 vida")


def test_morning_k_d_gives_resources():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_D")
    play_artifact(state, 1, "K_D")
    gold_before = p.city.gold
    magic_before = p.city.magic
    state.turn = 2
    start_turn(state)
    assert p.city.gold == gold_before + 2
    assert p.city.magic == magic_before + 1
    print("OK  - Kd manha: +2 Ouro, +1 Magia")


def test_morning_k_h_caps_at_life_max():
    state = make_state()
    p = state.players[0]
    p.city.life = p.city.life_max
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    state.turn = 2
    start_turn(state)
    assert p.city.life == 7
    for t in range(3, 6):
        state.turn = t
        start_turn(state)
    assert p.city.life == 7
    print("OK  - Kh manha estanca em life_max")


def test_field_survives_serialization():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    state2 = state_from_dict(state_to_dict(state))
    p2 = state2.players[0]
    assert p2.city.life_max == p.city.life_max
    assert len(p2.field_artifacts) == 1
    assert p2.field_artifacts[0].card_id == "K_H"
    print("OK  - Campo persiste em roundtrip")


def test_discard_returns_to_shop():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    shop_before = state.shop.size()
    discard_field_artifact(state, 1, "K_H")
    assert state.shop.size() == shop_before + 1
    assert not p.field_artifacts
    print("OK  - Descarte devolve a Loja")


def run_all():
    tests = [
        test_play_not_in_hand,
        test_play_k_h_raises_life_max,
        test_play_k_d,
        test_morning_k_h_heals,
        test_morning_k_d_gives_resources,
        test_morning_k_h_caps_at_life_max,
        test_field_survives_serialization,
        test_discard_returns_to_shop,
    ]
    print("=== Testes K-heart / K-diamonds ===\n")
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
