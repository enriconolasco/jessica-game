"""Testes: Sonho Lucido."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import cast_spell, play_artifact
from jessica.core import peoples


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


def test_flip_card():
    assert peoples.sonho_lucido_flip("K_H") == "K_D"
    assert peoples.sonho_lucido_flip("K_D") == "K_H"
    assert peoples.sonho_lucido_flip("K_S") == "K_C"
    assert peoples.sonho_lucido_flip("K_C") == "K_S"
    print("OK  - sonho_lucido_flip funciona H<->D e S<->C")


def test_flip_pena_unchanged():
    assert peoples.sonho_lucido_flip("PENA") == "PENA"
    print("OK  - Pena nao muda de naipe")


def test_sonho_lucido_flips_played_artifact():
    state = make_state()
    p = state.players[3]  # Fadas
    p.city.magic = 10
    p.hand.append("K_H")
    cast_spell(state, 4, choice={"flip_cards": ["K_H"]})
    # K_H deve ter sido invertido para K_D E jogado automaticamente
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_D" in field_ids, f"K_H deveria ter virado K_D, campo: {field_ids}"
    print("OK  - Sonho Lucido inverteu e jogou K_D imediatamente")


def test_sonho_lucido_only_that_turn():
    state = make_state()
    p = state.players[3]
    p.city.magic = 10
    p.hand.append("K_H")
    cast_spell(state, 4, choice={"flip_cards": ["K_H"]})
    state.turn += 1
    # Novo K_H no proximo turno deve jogar normal, sem inverter
    p.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_H" in field_ids, f"K_H nao deveria ter virado em outro turno, campo: {field_ids}"
    print("OK  - Sonho Lucido so vale no turno do cast")


def test_copia_gnomica_ativa_imediatamente():
    state = make_state()
    p = state.players[0]
    p.people = "gnomos_duendes"
    p.spell_copia_id = "sonho_lucido"
    p.hand = ["K_H"]
    p.city.magic = 10
    cast_spell(state, p.id, {"flip_cards": ["K_H"], "artifact_choices": [{}]})
    assert not p.hand
    assert any(a.card_id == "K_D" for a in p.field_artifacts)
    assert p.sonho_lucido_pending_turn == -1
    assert p.has_cast_spell_this_turn


def run_all():
    tests = [
        test_flip_card,
        test_copia_gnomica_ativa_imediatamente,
        test_flip_pena_unchanged,
        test_sonho_lucido_flips_played_artifact,
        test_sonho_lucido_only_that_turn,
    ]
    print("=== Testes Sonho Lucido ===\n")
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
