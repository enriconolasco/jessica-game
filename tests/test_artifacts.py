"""Testes de artefatos - loja/compra/transmutacao/venda."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    buy_artifact_with_gold, transmute_artifact_with_magic,
    sell_artifact, summon_troop, ActionError,
)
from jessica.core.constants import (
    TroopArchetype, ARTIFACT_GOLD_COST, ARTIFACT_MAGIC_COST,
    ARTIFACT_SELL_GOLD,
)
from jessica.core.artifacts import ARTIFACT_CATALOG, ARTIFACTS_PER_CARD_IN_SHOP


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


def _setup_center_troop(state, pid=1):
    p = state.players[pid - 1]
    p.city.gold = 10
    p.city.magic = 5
    t = summon_troop(state, pid, TroopArchetype.LIGHT, 4)
    t.house = "center"
    return t


def test_shop_initial_size():
    """12 cartas base x 2 = 24. PENA nao esta na Loja ate Iuna ser invocada."""
    state = make_state()
    # Catalogo tem 13 entradas (12 + PENA), mas PENA nao entra no deck inicial
    base_cards = len([k for k in ARTIFACT_CATALOG if k != "PENA"])
    expected = base_cards * ARTIFACTS_PER_CARD_IN_SHOP
    assert state.shop.size() == expected, (
        f"Esperado {expected} cartas, veio {state.shop.size()}"
    )
    print(f"OK  - Loja inicial: {expected} cartas ({base_cards} x {ARTIFACTS_PER_CARD_IN_SHOP})")


def test_buy_with_gold_requires_unit_at_center():
    state = make_state()
    state.players[0].city.gold = 20
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria exigir unidade no Centro")
    except ActionError as e:
        print(f"OK  - Compra sem unidade bloqueada: {e}")


def test_buy_with_gold():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 20
    before_shop = state.shop.size()
    card = buy_artifact_with_gold(state, 1)
    assert card in ARTIFACT_CATALOG
    assert p.city.gold == 20 - ARTIFACT_GOLD_COST
    assert card in p.hand
    assert state.shop.size() == before_shop - 1
    print(f"OK  - Compra com Ouro (carta: {card})")


def test_buy_with_gold_daily_limit():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 30
    buy_artifact_with_gold(state, 1)
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria bloquear segunda compra")
    except ActionError as e:
        print(f"OK  - Limite diario bloqueado: {e}")


def test_transmute_with_magic():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    before = state.shop.size()
    card = transmute_artifact_with_magic(state, 1)
    assert p.city.magic == 10 - ARTIFACT_MAGIC_COST
    assert card in p.hand
    assert state.shop.size() == before - 1
    print(f"OK  - Transmutacao com Magia (carta: {card})")


def test_transmute_daily_limit():
    state = make_state()
    p = state.players[0]
    p.city.magic = 20
    transmute_artifact_with_magic(state, 1)
    try:
        transmute_artifact_with_magic(state, 1)
        raise AssertionError("Deveria bloquear segunda transmutacao")
    except ActionError as e:
        print(f"OK  - Limite diario bloqueado: {e}")


def test_transmute_requires_no_unit():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    assert p.units == []
    transmute_artifact_with_magic(state, 1)
    print("OK  - Transmutacao sem unidade")


def test_sell_requires_unit_at_center():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    card = transmute_artifact_with_magic(state, 1)
    try:
        sell_artifact(state, 1, card)
        raise AssertionError("Deveria exigir unidade no Centro")
    except ActionError as e:
        print(f"OK  - Venda sem unidade bloqueada: {e}")


def test_sell_returns_card_to_shop():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 20
    before_size = state.shop.size()
    card = buy_artifact_with_gold(state, 1)
    after_buy = state.shop.size()
    assert after_buy == before_size - 1
    gold_before = p.city.gold
    sell_artifact(state, 1, card)
    assert p.city.gold == gold_before + ARTIFACT_SELL_GOLD
    assert card not in p.hand
    assert state.shop.size() == after_buy + 1
    print(f"OK  - Venda devolve carta e +{ARTIFACT_SELL_GOLD} Ouro")


def test_sell_does_not_consume_daily_limit():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 20
    card = buy_artifact_with_gold(state, 1)
    sell_artifact(state, 1, card)
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria continuar bloqueado")
    except ActionError:
        print("OK  - Venda nao zera limite diario")


def run_all():
    tests = [
        test_shop_initial_size,
        test_buy_with_gold_requires_unit_at_center,
        test_buy_with_gold,
        test_buy_with_gold_daily_limit,
        test_transmute_with_magic,
        test_transmute_daily_limit,
        test_transmute_requires_no_unit,
        test_sell_requires_unit_at_center,
        test_sell_returns_card_to_shop,
        test_sell_does_not_consume_daily_limit,
    ]
    print("=== Testes artifacts ===\n")
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
