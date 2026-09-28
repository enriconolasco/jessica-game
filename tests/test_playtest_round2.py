"""Regressões do segundo lote de playtest do terminal."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.actions import (ActionError, arken_espolia, cast_spell, move_unit,
                                  summon_hero, summon_troop)
from jessica.core.combat import _apply_defense
from jessica.core.constants import TroopArchetype
from jessica.core.models import Hero
from jessica.core.serialize import state_from_dict, state_to_dict
from jessica.core.setup import run_setup
from jessica.core.turn import start_turn


def make_state(peoples, heroes, choices):
    state, _ = run_setup(peoples, heroes, choices, seed=24092026,
                         turn_order=list(range(1, len(peoples) + 1)))
    return state


def test_log_de_mudancas_no_inicio_do_turno():
    from jessica.main import _log_visible_state_changes, _visible_state_snapshot

    state = make_state(["humanos", "orcs"],
                       {"humanos": ["miyamoto"], "orcs": ["arken"]},
                       {1: {"povo": "humanos", "heroi": "miyamoto"},
                        2: {"povo": "orcs", "heroi": "arken"}})
    before = _visible_state_snapshot(state)
    start_turn(state)
    state.players[0].city.gold += 1
    _log_visible_state_changes(state, before, "início do turno")
    assert any("[STATE] início do turno" in entry and "Ouro" in entry
               for entry in state.event_log)


def test_morcego_reabre_movimento_de_recem_invocado():
    state = make_state(["vampiros", "humanos"],
                       {"vampiros": ["dandara"], "humanos": ["miyamoto"]},
                       {1: {"povo": "vampiros", "heroi": "dandara"},
                        2: {"povo": "humanos", "heroi": "miyamoto"}})
    p = state.players[0]
    p.city.gold = 10
    p.city.magic = 10
    troop = summon_troop(state, 1, TroopArchetype.LIGHT, 1, "city_1")
    cast_spell(state, 1, {"unit_id": troop.id})
    move_unit(state, 1, troop.id, "center")
    assert troop.house == "center"


def test_sonho_lucido_resolve_escolha_imediata():
    state = make_state(["fadas", "humanos"],
                       {"fadas": ["ainai", "luna"], "humanos": ["miyamoto"]},
                       {1: {"povo": "fadas", "heroi": "ainai"},
                        2: {"povo": "humanos", "heroi": "miyamoto"}})
    p = state.players[0]
    p.city.magic = 10
    p.hand.append("J_D")
    cast_spell(state, 1, {"flip_cards": ["J_D"],
                          "artifact_choices": [{"hero_id": "luna"}]})
    assert "J_H" not in p.hand
    assert any(a.card_id == "J_H" for a in p.field_artifacts)
    assert any(isinstance(u, Hero) and u.hero_id == "luna" for u in p.units)


def test_arken_espolia_cura_heroi_e_bloqueia_ataque():
    state = make_state(["orcs", "humanos"],
                       {"orcs": ["arken"], "humanos": ["miyamoto"]},
                       {1: {"povo": "orcs", "heroi": "arken"},
                        2: {"povo": "humanos", "heroi": "miyamoto"}})
    p = state.players[0]
    p.city.magic = 10
    arken = summon_hero(state, 1)
    arken.house = "city_2"
    arken.life -= 1
    arken_espolia(state, 1)
    assert arken.life == arken.life_max
    assert arken.statuses["cannot_attack_on_turn"] == state.turn


def test_resistencia_multipla_arredonda_para_baixo():
    state = make_state(["humanos", "orcs"],
                       {"humanos": ["miyamoto"], "orcs": ["arken"]},
                       {1: {"povo": "humanos", "heroi": "miyamoto"},
                        2: {"povo": "orcs", "heroi": "arken"}})
    defender = Hero(id="d", owner_id=1, house="center", life=4, life_max=4,
                    hero_id="miyamoto", resistance_stacks=1)
    assert _apply_defense(state, defender, 3)[0] == 1


def test_ressonancia_primeiro_uso_livre_e_limite_por_carta():
    state = make_state(["dragoes", "humanos"],
                       {"dragoes": ["purpura"], "humanos": ["miyamoto"]},
                       {1: {"povo": "dragoes", "heroi": "purpura"},
                        2: {"povo": "humanos", "heroi": "miyamoto"}})
    p = state.players[0]
    p.hand.extend(["K_H", "K_D"])
    cast_spell(state, 1, {"action": "add", "card_id": "K_H"})
    assert p.spell_cooldown_until_turn <= state.turn
    cast_spell(state, 1, {"action": "remove", "card_id": "K_H"})
    assert p.spell_cooldown_until_turn == state.turn + 2
    cast_spell(state, 1, {"action": "add", "card_id": "K_D"})
    try:
        cast_spell(state, 1, {"action": "add", "card_id": "K_H"})
        raise AssertionError("Terceiro movimento da mesma carta deveria falhar")
    except ActionError:
        pass


def test_novo_contador_de_ressonancia_persiste_no_save():
    state = make_state(["dragoes", "humanos"],
                       {"dragoes": ["purpura"], "humanos": ["miyamoto"]},
                       {1: {"povo": "dragoes", "heroi": "purpura"},
                        2: {"povo": "humanos", "heroi": "miyamoto"}})
    state.players[0].canastra_resonance_uses = 3
    restored = state_from_dict(state_to_dict(state))
    assert restored.players[0].canastra_resonance_uses == 3


def run_all():
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    passed = failed = 0
    for test in tests:
        try:
            test(); passed += 1
        except Exception as exc:
            failed += 1
            print(f"FALHOU - {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n=== {passed} passaram, {failed} falharam ===")


if __name__ == "__main__":
    run_all()
