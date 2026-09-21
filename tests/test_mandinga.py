"""Testes: Besouro Mandinga."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, besouro_mandinga, ActionError,
)
from jessica.core.constants import Phase, CENTER
from jessica.core.models import Hero


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["besouro"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "Besouro Mangangá"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_mandinga_requires_besouro_alive():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    try:
        besouro_mandinga(state, 1, "K_H")
        raise AssertionError("Deveria bloquear sem Besouro")
    except ActionError as e:
        print(f"OK  - Mandinga exige Besouro vivo: {e}")


def test_mandinga_plays_artifact_once_per_night():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    summon_hero(state, 1)  # Besouro
    p.hand.append("K_H")
    besouro_mandinga(state, 1, "K_H")
    assert p.besouro_mandinga_used_turn == state.turn
    assert any(a.card_id == "K_H" for a in p.field_artifacts), "K_H deveria estar no campo"
    print("OK  - Mandinga: K_H jogado via Besouro")


def test_mandinga_blocks_second_use():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    summon_hero(state, 1)
    p.hand.append("K_H")
    p.hand.append("K_D")
    besouro_mandinga(state, 1, "K_H")
    try:
        besouro_mandinga(state, 1, "K_D")
        raise AssertionError("Deveria bloquear segunda Mandinga na mesma noite")
    except ActionError as e:
        print(f"OK  - Mandinga bloqueia segunda use: {e}")


def test_mandinga_only_hand():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    summon_hero(state, 1)
    # Coloca um artefato no campo e tenta usar
    try:
        besouro_mandinga(state, 1, "K_H")
        raise AssertionError("Deveria bloquear carta fora da mao")
    except ActionError as e:
        print(f"OK  - Mandinga exige carta na mao: {e}")


def run_all():
    tests = [
        test_mandinga_requires_besouro_alive,
        test_mandinga_plays_artifact_once_per_night,
        test_mandinga_blocks_second_use,
        test_mandinga_only_hand,
    ]
    print("=== Testes Mandinga ===\n")
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
