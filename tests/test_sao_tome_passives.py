"""Regressoes das passivas herdadas por Sao Tome."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core import peoples
from jessica.core.actions import cast_spell, summon_hero, spell_imitacao_gnomerica
from jessica.core.models import Hero, Troop
from jessica.core.constants import TroopArchetype
from jessica.core.setup import run_setup
from jessica.core.turn import _process_gigantes_turn


def make_state(target_people="fadas"):
    state, _ = run_setup(
        all_peoples=["gnomos_duendes", target_people, "humanos", "orcs"],
        heroes_by_people={
            "gnomos_duendes": ["sao_tome"], target_people: [],
            "humanos": ["miyamoto"], "orcs": ["arken"]},
        choices={1: {"povo": "gnomos_duendes", "heroi": "sao_tome"},
                 2: {"povo": target_people, "heroi": ""},
                 3: {"povo": "humanos", "heroi": "miyamoto"},
                 4: {"povo": "orcs", "heroi": "arken"}},
        seed=25092026, turn_order=[1, 2, 3, 4])
    p = state.players[0]
    p.city.magic = p.city.gold = 30
    summon_hero(state, 1)
    p.bet_H_target = 2
    return state


def test_fadas_valem_para_qualquer_unidade_e_heroi_gnomico():
    state = make_state("fadas")
    p = state.players[0]
    troop = Troop(id="g", owner_id=1, house="center", life=4, life_max=4,
                  archetype=TroopArchetype.LIGHT)
    p.units.append(troop)
    before = p.city.magic
    peoples.on_unit_moved(state, 1, troop)
    assert p.city.magic == before + 1
    hero = next(u for u in p.units if isinstance(u, Hero))
    dead = Hero(id="dead", owner_id=3, house="center", life=0, life_max=4,
                hero_id="miyamoto")
    hand = len(p.hand)
    peoples.on_unit_killed_by(state, 1, dead, hero)
    assert len(p.hand) == hand + 1


def test_lobisomem_usa_lua_cheia_dos_gnomos_e_infecta():
    state = make_state("lobisomens")
    state.curuna_id = 2  # jogador seguinte aos Gnomos na ordem
    p = state.players[0]
    troop = Troop(id="g", owner_id=1, house="center", life=4, life_max=4,
                  archetype=TroopArchetype.LIGHT)
    p.units.append(troop)
    assert peoples.is_lobisomem_ativo(state, troop)
    dead = Troop(id="dead", owner_id=3, house="center", life=0, life_max=4,
                 archetype=TroopArchetype.LIGHT)
    peoples.on_unit_killed_by(state, 1, dead, troop)
    assert p.infectados


def test_gigantes_dobra_todos_herois_gnomicos_permanentemente():
    state = make_state("gigantes")
    state.turn = 4
    sao = next(u for u in state.players[0].units if isinstance(u, Hero))
    _process_gigantes_turn(state)
    assert sao.life == sao.life_max == 8
    state.turn = 8
    _process_gigantes_turn(state)
    assert sao.life == sao.life_max == 16


def test_mortos_vivos_libera_roster_e_remove_ao_perder_passiva():
    state = make_state("mortos_vivos")
    p = state.players[0]
    zebum = summon_hero(state, 1, "zebum")
    assert zebum.statuses["sao_tome_undead_summon"]
    peoples.on_action_performed(state, 2, "base_life_gained")
    assert not any(u.hero_id == "zebum" for u in p.units if isinstance(u, Hero))
    assert any(u.hero_id == "sao_tome" for u in p.units if isinstance(u, Hero))


def test_dragoes_canastra_retorna_para_mao_ao_perder_passiva():
    state = make_state("dragoes")
    p = state.players[0]
    p.hand.append("Q_H")
    p.spell_copia_id = "ressonancia_magica"
    sao = next(u for u in p.units if isinstance(u, Hero))
    base_life = sao.life_max
    spell_imitacao_gnomerica(state, 1, {"action": "add", "card_id": "Q_H"})
    assert p.canastra == ["Q_H"]
    assert sao.life_max == base_life + 2
    peoples.on_action_performed(state, 2, "base_life_gained")
    assert not p.canastra and "Q_H" in p.hand
    assert sao.life_max == base_life


def test_feitico_copiado_entra_em_recarga_normal():
    state = make_state("humanos")
    p = state.players[0]
    p.spell_copia_id = "resistencia"
    sao = next(u for u in p.units if isinstance(u, Hero))
    cast_spell(state, 1, {"unit_id": sao.id})
    assert p.has_cast_spell_this_turn
    assert p.spell_cooldown_until_turn == state.turn + 2


def test_sacrificio_copiado_pode_escolher_outro_heroi():
    state = make_state("demonios")
    p = state.players[0]
    p.hand.append("K_H")
    other = Hero(id="outro", owner_id=1, house="city_1", life=3, life_max=3,
                 hero_id="zebum")
    p.units.append(other)
    p.spell_copia_id = "sacrificio_de_demonio"
    cast_spell(state, 1, {"hero_id": other.id,
                          "artifacts": [{"zone": "hand", "card_id": "K_H"}]})
    assert not any(u.id == "outro" for u in p.units)
    assert any(u.hero_id == "sao_tome" for u in p.units if isinstance(u, Hero))


def test_sao_tome_rerrola_uma_vez_e_substitui_resultado():
    state = make_state("fadas")
    p = state.players[0]
    p.spell_copia_id = "sonho_lucido"
    p.spell_copia_turn = state.turn
    result = peoples.reroll_spell_copia(state, 1)
    assert result != "sonho_lucido"
    try:
        peoples.reroll_spell_copia(state, 1)
        raise AssertionError("Segunda rerrolagem deveria falhar")
    except ValueError:
        pass


def run_all():
    tests = [test_fadas_valem_para_qualquer_unidade_e_heroi_gnomico,
             test_lobisomem_usa_lua_cheia_dos_gnomos_e_infecta,
             test_gigantes_dobra_todos_herois_gnomicos_permanentemente,
             test_mortos_vivos_libera_roster_e_remove_ao_perder_passiva,
             test_dragoes_canastra_retorna_para_mao_ao_perder_passiva,
             test_feitico_copiado_entra_em_recarga_normal,
             test_sacrificio_copiado_pode_escolher_outro_heroi,
             test_sao_tome_rerrola_uma_vez_e_substitui_resultado]
    passed = failed = 0
    for test in tests:
        try:
            test(); passed += 1
        except Exception as exc:
            failed += 1
            print(f"FALHOU - {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")


if __name__ == "__main__":
    run_all()
