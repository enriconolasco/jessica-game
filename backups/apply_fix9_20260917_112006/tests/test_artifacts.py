"""Testes de artefatos — Fase 1 (loja, mão, compra, transmutação, venda)."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    buy_artifact_with_gold,
    transmute_artifact_with_magic,
    sell_artifact,
    summon_troop,
    ActionError,
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


def _setup_center_troop(state, pid=1):
    """Invocação de tropa custa ouro. Depois movemos para o Centro.
    Devolve a tropa criada."""
    p = state.players[pid - 1]
    # Garante recursos para invocar (a tropa custa 4 de ouro se vida=4)
    p.city.gold = 10
    p.city.magic = 5
    troop = summon_troop(state, pid, TroopArchetype.LIGHT, 4)
    troop.house = "center"
    return troop


def test_shop_initial_size():
    state = make_state()
    expected = len(ARTIFACT_CATALOG) * ARTIFACTS_PER_CARD_IN_SHOP
    assert state.shop.size() == expected, (
        f"Esperado {expected} cartas, veio {state.shop.size()}"
    )
    print(f"OK  - Loja inicia com {expected} cartas ({len(ARTIFACT_CATALOG)} × {ARTIFACTS_PER_CARD_IN_SHOP})")


def test_buy_with_gold_requires_unit_at_center():
    state = make_state()
    state.players[0].city.gold = 20
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria exigir unidade no Centro")
    except ActionError as e:
        print(f"OK  - Compra sem unidade no Centro bloqueada: {e}")


def test_buy_with_gold():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)  # invoca tropa e move para o Centro
    # Agora zera ouro do jogador para um teste limpo
    p.city.gold = 20
    before_shop = state.shop.size()

    card = buy_artifact_with_gold(state, 1)

    assert card in ARTIFACT_CATALOG, f"Carta desconhecida: {card}"
    assert p.city.gold == 20 - ARTIFACT_GOLD_COST, (
        f"Ouro esperado {20 - ARTIFACT_GOLD_COST}, veio {p.city.gold}"
    )
    assert card in p.hand, "Carta deveria estar na mão"
    assert state.shop.size() == before_shop - 1, "Loja deveria ter 1 carta a menos"
    print(f"OK  - Compra com Ouro (carta: {card})")


def test_buy_with_gold_daily_limit():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 30

    buy_artifact_with_gold(state, 1)
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria bloquear segunda compra no mesmo dia")
    except ActionError as e:
        print(f"OK  - Limite diário de compra com Ouro bloqueado: {e}")


def test_transmute_with_magic():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10

    before = state.shop.size()
    card = transmute_artifact_with_magic(state, 1)

    assert p.city.magic == 10 - ARTIFACT_MAGIC_COST, (
        f"Magia esperada {10 - ARTIFACT_MAGIC_COST}, veio {p.city.magic}"
    )
    assert card in p.hand, "Carta deveria estar na mão"
    assert state.shop.size() == before - 1
    print(f"OK  - Transmutação com Magia (carta: {card})")


def test_transmute_daily_limit():
    state = make_state()
    p = state.players[0]
    p.city.magic = 20

    transmute_artifact_with_magic(state, 1)
    try:
        transmute_artifact_with_magic(state, 1)
        raise AssertionError("Deveria bloquear segunda transmutação no mesmo dia")
    except ActionError as e:
        print(f"OK  - Limite diário de transmutação bloqueado: {e}")


def test_transmute_requires_no_unit():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    assert p.units == []
    transmute_artifact_with_magic(state, 1)
    print("OK  - Transmutação funciona sem unidade (na Cidade)")


def test_sell_requires_unit_at_center():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    card = transmute_artifact_with_magic(state, 1)
    try:
        sell_artifact(state, 1, card)
        raise AssertionError("Deveria exigir unidade no Centro para vender")
    except ActionError as e:
        print(f"OK  - Venda sem unidade no Centro bloqueada: {e}")


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

    assert p.city.gold == gold_before + ARTIFACT_SELL_GOLD, (
        f"Ouro esperado {gold_before + ARTIFACT_SELL_GOLD}, veio {p.city.gold}"
    )
    assert card not in p.hand, "Carta deveria sair da mão"
    assert state.shop.size() == after_buy + 1, "Carta deveria voltar à Loja"
    print(f"OK  - Venda devolve carta à Loja e dá +{ARTIFACT_SELL_GOLD} Ouro")


def test_sell_does_not_consume_daily_limit():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 20

    card = buy_artifact_with_gold(state, 1)
    sell_artifact(state, 1, card)

    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria continuar bloqueado (limite diário)")
    except ActionError:
        print("OK  - Venda não zera o limite diário de compra")


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
    print("=== Rodando testes de artifacts (Fase 1) ===\n")
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