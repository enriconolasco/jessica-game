"""Testes: Valendar e Luna."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, play_artifact, cast_spell, move_unit, ActionError,
)
from jessica.core.constants import CENTER
from jessica.core.models import Hero
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["valendar", "luna", "ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "Valendar"}},
        seed=20260916,
    )
    return state


def test_valendar_blocks_sonho_lucido():
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    summon_hero(state, 4)
    try:
        cast_spell(state, 4)
        raise AssertionError("Deveria bloquear Sonho Lucido com Valendar viva")
    except ActionError as e:
        print(f"OK  - Valendar bloqueia Sonho Lucido: {e}")


def test_valendar_heart_heals_heroes():
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    val = summon_hero(state, 4)
    val.life = 1
    p4.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    assert val.life == val.life_max, f"Valendar deveria estar curada (1 -> {val.life})"
    print(f"OK  - Valendar C: heroi curado ao maximo ({val.life}/{val.life_max})")


def test_valendar_diamond_magic_sell():
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    summon_hero(state, 4)
    p4.hand.append("K_D")
    play_artifact(state, 4, "K_D")
    assert p4.vender_por_magia_turn == state.turn
    print("OK  - Valendar O: vender por magia ativo")


def test_valendar_clubs_2_moves():
    """Valendar P: heróis andam 2 vezes neste turno."""
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    val = summon_hero(state, 4)
    p4.hand.append("K_C")
    # K_C exige alvo; usamos o próprio Valendar
    play_artifact(state, 4, "K_C", choice={"unit_id": val.id})
    assert val.max_moves_this_turn == 2, f"Esperado 2, veio {val.max_moves_this_turn}"
    print("OK  - Valendar P: 2 movimentos ativos")


def test_valendar_spades_first():
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    summon_hero(state, 4)
    p4.hand.append("K_S")
    play_artifact(state, 4, "K_S")
    assert p4.bater_primeiro_turn == state.turn
    print("OK  - Valendar E: bater primeiro ativo")


def test_valendar_reverts_when_dead():
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    val = summon_hero(state, 4)
    assert peoples.valendar_is_alive(p4) is True
    val.life = 0
    p4.units = [u for u in p4.units if u.is_alive()]
    assert peoples.valendar_is_alive(p4) is False
    cast_spell(state, 4)
    assert p4.sonho_lucido_pending_turn == state.turn
    print("OK  - Valendar morta: Sonho Lucido volta")


def test_luna_multi_artifact():
    """Luna: Sonho Lucido aplica a N artefatos."""
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 20
    # Força a escolha de Luna antes de invocar
    p4.chosen_hero_id = "luna"
    luna = summon_hero(state, 4)
    assert luna.hero_id == "luna", f"Esperado luna, veio {luna.hero_id}"
    assert peoples.luna_is_alive(p4)
    cast_spell(state, 4)
    assert p4.sonho_lucido_multi_turn == state.turn,         f"Multi nao setado: {p4.sonho_lucido_multi_turn}"
    p4.hand.append("K_H")
    p4.hand.append("K_S")
    play_artifact(state, 4, "K_H")
    play_artifact(state, 4, "K_S")
    field_ids = [a.card_id for a in p4.field_artifacts]
    assert "K_D" in field_ids, f"K_H deveria ter virado K_D. Campo: {field_ids}"
    assert "K_C" in field_ids, f"K_S deveria ter virado K_C. Campo: {field_ids}"
    print("OK  - Luna: Sonho Lucido aplicou a 2 artefatos")


def test_luna_returns_to_origin():
    from jessica.core.turn import end_day
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    p4.chosen_hero_id = "luna"
    luna = summon_hero(state, 4)
    assert luna.hero_id == "luna"
    assert luna.house == "city_4"
    move_unit(state, 4, luna.id, CENTER)
    assert luna.house == CENTER
    assert luna.statuses.get("luna_origin_house") == "city_4"
    end_day(state)
    assert luna.house == "city_4", f"Luna deveria ter voltado pra city_4, esta em {luna.house}"
    print("OK  - Luna voltou ao local de origem no inicio da Noite")


def run_all():
    tests = [
        test_valendar_blocks_sonho_lucido,
        test_valendar_heart_heals_heroes,
        test_valendar_diamond_magic_sell,
        test_valendar_clubs_2_moves,
        test_valendar_spades_first,
        test_valendar_reverts_when_dead,
        test_luna_multi_artifact,
        test_luna_returns_to_origin,
    ]
    print("=== Testes Valendar e Luna ===\n")
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
