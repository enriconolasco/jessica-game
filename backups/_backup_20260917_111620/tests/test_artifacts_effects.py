"""Testes de efeitos de artefatos — Fase 2 (play + K_H + K_D)."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, discard_field_artifact, ActionError,
)
from jessica.core.turn import start_player_day
from jessica.core import artifacts_effects
from jessica.core.serialize import state_to_dict, state_from_dict


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["m"], "anoes": ["b"], "orcs": ["g"], "fadas": ["ai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "m"},
            2: {"povo": "anoes", "heroi": "b"},
            3: {"povo": "orcs", "heroi": "g"},
            4: {"povo": "fadas", "heroi": "ai"},
        },
        seed=20260916,
    )
    return state


def test_play_unimplemented_card_blocked():
    state = make_state()
    state.players[0].hand.append("Q_H")
    try:
        play_artifact(state, 1, "Q_H")
        raise AssertionError("Deveria bloquear carta não implementada")
    except ActionError as e:
        print(f"OK  - Carta não implementada bloqueada: {e}")


def test_play_not_in_hand():
    state = make_state()
    try:
        play_artifact(state, 1, "K_H")
        raise AssertionError("Deveria bloquear carta fora da mão")
    except ActionError as e:
        print(f"OK  - Carta fora da mão bloqueada: {e}")


def test_play_k_h_raises_life_max():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    before = p.city.life_max
    play_artifact(state, 1, "K_H")

    assert p.city.life_max == before + 1, (
        f"life_max esperado {before + 1}, veio {p.city.life_max}"
    )
    assert p.city.life == 2, f"Vida não deveria ter mudado ainda, veio {p.city.life}"
    assert "K_H" not in p.hand, "Carta deveria sair da mão"
    assert any(a.card_id == "K_H" for a in p.field_artifacts), "Carta deveria estar no campo"
    print(f"OK  - K♥ Aquilombar: life_max {before} → {p.city.life_max}, vida ainda 2")


def test_play_k_d():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_D")
    play_artifact(state, 1, "K_D")

    assert "K_D" not in p.hand
    assert any(a.card_id == "K_D" for a in p.field_artifacts)
    print("OK  - K♦ Balança jogado para o campo")


def test_morning_k_h_heals():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")

    p.morning_done_this_turn = False
    start_player_day(state, 1)
    assert p.city.life == 3, f"Esperado 3 após manhã, veio {p.city.life}"

    start_player_day(state, 1)
    assert p.city.life == 3, "Manhã não deveria disparar duas vezes no mesmo turno"
    print("OK  - K♥ manhã: +1 vida (2 → 3) e não duplica")


def test_morning_k_d_gives_resources():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_D")
    play_artifact(state, 1, "K_D")
    p.morning_done_this_turn = False
    gold_before = p.city.gold
    magic_before = p.city.magic
    start_player_day(state, 1)
    assert p.city.gold == gold_before + 2, f"Esperado +2 ouro, veio {p.city.gold - gold_before}"
    assert p.city.magic == magic_before + 1, f"Esperado +1 magia, veio {p.city.magic - magic_before}"
    print(f"OK  - K♦ manhã: +2 Ouro, +1 Magia (agora {p.city.gold}/{p.city.magic})")


def test_morning_k_h_caps_at_life_max():
    state = make_state()
    p = state.players[0]
    p.city.life = p.city.life_max
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")

    p.morning_done_this_turn = False
    start_player_day(state, 1)
    assert p.city.life == 7, f"Esperado 7, veio {p.city.life}"

    for _ in range(3):
        p.morning_done_this_turn = False
        start_player_day(state, 1)
    assert p.city.life == 7, f"Deveria estagnar em 7, veio {p.city.life}"
    print("OK  - K♥ manhã estanca em life_max")


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
    print("OK  - Campo persiste em roundtrip de serialização")


def test_discard_returns_to_shop():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    shop_before = state.shop.size()
    discard_field_artifact(state, 1, "K_H")
    assert state.shop.size() == shop_before + 1
    assert not p.field_artifacts
    print("OK  - Descarte de artefato devolve à Loja")


def run_all():
    tests = [
        test_play_unimplemented_card_blocked,
        test_play_not_in_hand,
        test_play_k_h_raises_life_max,
        test_play_k_d,
        test_morning_k_h_heals,
        test_morning_k_d_gives_resources,
        test_morning_k_h_caps_at_life_max,
        test_field_survives_serialization,
        test_discard_returns_to_shop,
    ]
    print("=== Rodando testes de artifact_effects (Fase 2) ===\n")
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== Resultado: {passed} passaram, {failed} falharam ===")


if __name__ == "__main__":
    run_all()