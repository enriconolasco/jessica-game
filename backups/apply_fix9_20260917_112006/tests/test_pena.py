"""Testes: Pena do Manto Sagrado."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, use_or_give_pena, sell_artifact, summon_troop, ActionError,
)
from jessica.core.constants import CENTER, TroopArchetype
from jessica.core.models import Hero
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["iuna"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "Iúna"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_humano_pena_activate():
    """Humano: Pena vira artefato em campo (permanente)."""
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("PENA")
    use_or_give_pena(state, 1, "PENA", give_to_iuna=False)
    assert any(a.card_id == "PENA" for a in p1.field_artifacts),         "Pena deveria estar no campo"
    assert "PENA" not in p1.hand, "Pena nao deveria estar na mao"
    print("OK  - Humano: Pena ativada em campo")


def test_humano_pena_boosts_roca():
    """Humano com Pena ativa: Roca rola 2D4."""
    state = make_state()
    p1 = state.players[0]
    p1.field_artifacts.append(
        type(p1.field_artifacts[0])(card_id="PENA", owner_id=1)
        if p1.field_artifacts else __import__("jessica.core.models", fromlist=["ArtifactOnField"]).ArtifactOnField(card_id="PENA", owner_id=1)
    )
    # Log capturado para ver se apareceu 2D4
    before = len(state.event_log)
    peoples.on_player_morning(state, 1)
    new_lines = state.event_log[before:]
    joined = "\n".join(new_lines)
    assert "2D4" in joined, f"Esperado 2D4 no log. Log: {joined}"
    print("OK  - Humano com Pena: Roca rola 2D4")


def test_non_humano_give_pena_to_iuna():
    """Nao-humano com Iuna viva: dar a Pena e ganhar outro artefato."""
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 10
    summon_hero(state, 1)  # Iuna
    p2 = state.players[1]
    p2.hand.append("PENA")
    hand_before = len(p2.hand)
    use_or_give_pena(state, 2, "PENA", give_to_iuna=True)
    assert "PENA" not in p2.hand, "Pena deveria ter sido entregue"
    assert len(p2.hand) == hand_before, f"Deveria ter 1 carta nova (era {hand_before}, tem {len(p2.hand)})"
    print("OK  - Nao-humano: deu Pena a Iuna e ganhou outro artefato")


def test_non_humano_keep_pena():
    """Nao-humano: pode ficar com a Pena (sem efeito)."""
    state = make_state()
    p2 = state.players[1]
    p2.hand.append("PENA")
    use_or_give_pena(state, 2, "PENA", give_to_iuna=False)
    assert "PENA" in p2.hand, "Pena deveria ter ficado na mao"
    print("OK  - Nao-humano: ficou com a Pena")


def test_non_humano_cannot_give_without_iuna():
    state = make_state()
    p2 = state.players[1]
    p2.hand.append("PENA")
    try:
        use_or_give_pena(state, 2, "PENA", give_to_iuna=True)
        raise AssertionError("Deveria bloquear sem Iuna viva")
    except ActionError as e:
        print(f"OK  - Sem Iuna: nao pode dar: {e}")


def test_sell_pena():
    """Nao-humano pode vender Pena por 7 Ouro."""
    state = make_state()
    p2 = state.players[1]
    p2.city.gold = 10
    p2.city.magic = 5
    # Tropa no Centro
    t = summon_troop(state, 2, TroopArchetype.LIGHT, 4)
    t.house = CENTER
    p2.hand.append("PENA")
    gold_before = p2.city.gold
    sell_artifact(state, 2, "PENA")
    assert p2.city.gold == gold_before + 7, f"Esperado +7, veio +{p2.city.gold - gold_before}"
    assert "PENA" not in p2.hand
    print("OK  - Pena vendida por 7 Ouro")


def run_all():
    tests = [
        test_humano_pena_activate,
        test_humano_pena_boosts_roca,
        test_non_humano_give_pena_to_iuna,
        test_non_humano_keep_pena,
        test_non_humano_cannot_give_without_iuna,
        test_sell_pena,
    ]
    print("=== Testes Pena ===\n")
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
