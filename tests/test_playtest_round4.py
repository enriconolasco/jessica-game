"""Regressões de Resistência em área e do modo Base de Barba Negra."""
import os
import sys
from copy import deepcopy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica.core.setup import run_setup
from jessica.core import actions, combat, peoples
from jessica.core.constants import Phase
from jessica.core.models import Hero, Troop
from jessica.core.serialize import state_to_dict


def make_state(people="dragoes", hero="barba_negra"):
    state, _ = run_setup(
        [people, "humanos", "anoes", "fadas"],
        {people: [hero], "humanos": ["miyamoto"], "anoes": ["ori"], "fadas": ["ainai"]},
        {1: {"povo": people, "heroi": hero}, 2: {"povo": "humanos", "heroi": "miyamoto"},
         3: {"povo": "anoes", "heroi": "ori"}, 4: {"povo": "fadas", "heroi": "ainai"}},
        seed=730)
    for p in state.players:
        p.city.magic = 20
    return state


def test_resistencia_anula_area_de_ambas_fontes_sem_morte():
    for people, hid in (("dragoes", "barba_negra"), ("demonios", "belial")):
        state = make_state(people, hid)
        source = peoples.dragon_base(state.players[0]) if hid == "barba_negra" else actions.summon_hero(state, 1)
        source.house = "center"
        resistant = Troop(id="resistente", owner_id=2, house="center", life=1, life_max=4, resistance_stacks=1)
        exposed = Troop(id="exposto", owner_id=2, house="center", life=2, life_max=4)
        aura_ally = Troop(id="aura_aliado", owner_id=3, house="center", life=1, life_max=4)
        ori = Hero(id="ori", owner_id=3, house="center", life=4, life_max=4, hero_id="ori")
        state.players[1].units = [resistant, exposed]
        state.players[2].units = [ori, aura_ally]
        if hid == "barba_negra":
            actions.barba_mar_de_chamas(state, 1)
        state.phase = Phase.NIGHT
        magic = state.players[0].city.magic
        if hid == "barba_negra":
            actions.barba_resolver_mar_de_chamas(state)
        else:
            peoples.apply_belial_night_start(state)
        assert resistant.life == aura_ally.life == 1 and ori.life == 4
        assert exposed.life == 1
        assert resistant.killed_by_unit_id is None
        assert state.players[0].city.magic == magic
        assert any("resistente: 1 -> 1" in line for line in state.event_log)


def test_barba_alvo_heroico_depende_do_modo_dia_e_noite():
    initial = make_state()
    barba = peoples.dragon_base(initial.players[0])
    barba.house = "center"
    initial.players[1].units = [Hero(id="enemy", owner_id=2, house="center", life=4, life_max=4, hero_id="miyamoto")]
    for resolver in (combat.resolve_attack, combat.resolve_attack_day):
        state = deepcopy(initial)
        before = state_to_dict(state)
        try:
            resolver(state, combat.Attack("enemy", "unit", barba.id))
        except combat.CombatError as exc:
            assert "Base" in str(exc)
        else:
            raise AssertionError("Heroi atacou Barba Negra em modo Base")
        assert state_to_dict(state) == before
        actions.barba_combater_como_heroi(state, 1)
        resolver(state, combat.Attack("enemy", "unit", barba.id))
        assert not any(u.id == barba.id and u.is_alive() for u in state.players[0].units)


def test_tropa_ainda_ataca_barba_base_com_dano_fixo():
    state = make_state()
    barba = peoples.dragon_base(state.players[0])
    barba.house = "center"
    troop = Troop(id="troop", owner_id=2, house="center", life=4, life_max=4)
    state.players[1].units = [troop]
    combat.resolve_attack(state, combat.Attack(troop.id, "unit", barba.id))
    assert barba.life == 2 and troop.life == 3


if __name__ == "__main__":
    passed = failed = 0
    for name, test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test()
                passed += 1
            except Exception as exc:
                failed += 1
                print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")

