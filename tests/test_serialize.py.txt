"""Testes de serialização (save/load) e action_log."""
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    collect_resources, summon_troop, summon_hero, buy_artifact_with_gold,
    raise_city_life,
)
from jessica.core.constants import TroopArchetype
from jessica.core.serialize import (
    state_to_dict, state_from_dict, save_to_file, load_from_file,
)


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


def test_roundtrip_basic():
    state = make_state()
    state.players[0].city.gold = 15
    state.players[0].city.magic = 7
    state.players[0].hand.append("K_H")
    state.players[0].name = "Enric"
    state.turn = 3
    state.curuna_id = 2

    data = state_to_dict(state)
    state2 = state_from_dict(data)

    assert state2.players[0].city.gold == 15
    assert state2.players[0].city.magic == 7
    assert state2.players[0].hand == ["K_H"]
    assert state2.players[0].name == "Enric"
    assert state2.turn == 3
    assert state2.curuna_id == 2
    print("OK  - Roundtrip básico preserva estado")


def test_rng_is_serialized():
    state = make_state()
    for _ in range(5):
        state.rng.randint(1, 20)
    snapshot = state.rng.state

    state2 = state_from_dict(state_to_dict(state))
    assert state2.rng.state == snapshot, "Estado do RNG deveria ser igual"

    a = state.rng.randint(1, 100)
    b = state2.rng.randint(1, 100)
    assert a == b, "RNGs devem produzir mesma sequência após roundtrip"
    print("OK  - RNG serializa e continua determinístico")


def test_units_roundtrip():
    state = make_state()
    state.players[0].city.gold = 20
    state.players[0].city.magic = 10
    summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    summon_hero(state, 1)

    state2 = state_from_dict(state_to_dict(state))
    units2 = state2.players[0].units
    types = sorted(type(u).__name__ for u in units2)
    assert types == ["Hero", "Troop"], f"Esperado Hero e Troop, veio {types}"
    print("OK  - Unidades (Hero e Troop) preservadas no roundtrip")


def test_action_log_records():
    state = make_state()
    collect_resources(state, 1, 2, 0)
    assert len(state.action_log) == 1
    rec = state.action_log[0]
    assert rec["action"] == "collect_resources"
    assert rec["player_id"] == 1
    assert rec["params"]["gold"] == 2
    assert rec["turn"] == 1
    print("OK  - action_log registra ações do jogador")


def test_action_log_survives_roundtrip():
    state = make_state()
    collect_resources(state, 1, 2, 0)
    state.players[0].city.gold = 20
    state.players[0].city.magic = 5
    troop = summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    troop.house = "center"
    buy_artifact_with_gold(state, 1)

    state2 = state_from_dict(state_to_dict(state))
    assert len(state2.action_log) == len(state.action_log)
    assert state2.action_log[-1]["action"] == "buy_artifact_gold"
    print("OK  - action_log preservado após roundtrip")


def test_save_load_file():
    state = make_state()
    state.players[0].city.gold = 42
    state.players[0].name = "Alguém"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as f:
        path = f.name
    try:
        save_to_file(state, path)
        state2 = load_from_file(path)
        assert state2.players[0].city.gold == 42
        assert state2.players[0].name == "Alguém"
        print("OK  - save_to_file / load_from_file funcionam")
    finally:
        os.unlink(path)


def test_continue_after_load():
    """Jogo continua igual depois de save/load (mesma sequência)."""
    state = make_state()
    state.players[0].city.gold = 20
    state.players[0].city.magic = 5
    troop = summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    troop.house = "center"

    # Salva antes de comprar
    state2 = state_from_dict(state_to_dict(state))

    # Compra em ambos
    c1 = buy_artifact_with_gold(state, 1)
    c2 = buy_artifact_with_gold(state2, 1)

    assert c1 == c2, f"Cartas diferentes após load: {c1} vs {c2}"
    print(f"OK  - Sequência idêntica após load (carta: {c1})")


def run_all():
    tests = [
        test_roundtrip_basic,
        test_rng_is_serialized,
        test_units_roundtrip,
        test_action_log_records,
        test_action_log_survives_roundtrip,
        test_save_load_file,
        test_continue_after_load,
    ]
    print("=== Rodando testes de serialize.py ===\n")
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