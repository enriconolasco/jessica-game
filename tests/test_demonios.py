"""Testes das mecanicas centrais dos Demonios."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop, cast_spell, play_artifact
from jessica.core.artifacts_effects import on_night_start
from jessica.core.combat import resolve_attack, Attack, CombatError
from jessica.core.constants import CENTER, Phase, TroopArchetype
from jessica.core.models import Troop
from jessica.core import peoples
from jessica.core.serialize import state_from_dict, state_to_dict


def make_state(hero="belial"):
    state, _ = run_setup(
        all_peoples=["demonios", "humanos", "orcs", "fadas"],
        heroes_by_people={"demonios": [hero], "humanos": ["miyamoto"],
                           "orcs": ["arken"], "fadas": ["ainai"]},
        choices={1: {"povo": "demonios", "heroi": hero},
                 2: {"povo": "humanos", "heroi": "miyamoto"},
                 3: {"povo": "orcs", "heroi": "arken"},
                 4: {"povo": "fadas", "heroi": "ainai"}}, seed=666)
    return state


def test_banco_de_almas_qualquer_morte():
    state = make_state()
    demon = state.players[0]
    demon.city.magic = 0
    victim = Troop(id="sacrificio", owner_id=2, house=CENTER, life=0, life_max=4)
    state.players[1].units.append(victim)
    from jessica.core.combat import _cleanup_dead
    _cleanup_dead(state)
    assert demon.city.magic == 1


def test_pacto_sacrificio_recompensa_unico_e_reversivel():
    state = make_state()
    owner = state.players[1]
    owner.city.life = owner.city.life_max = 8
    before = len(owner.hand)
    peoples.make_demon_pact(state, 1, 2, "sacrifique_futuro")
    assert owner.city.life == owner.city.life_max == 4
    assert len(owner.hand) == before + 1
    try:
        peoples.make_demon_pact(state, 1, 3, "sacrifique_futuro")
        raise AssertionError("Pacto duplicado")
    except ValueError:
        pass
    peoples.release_demon_pacts(state, 1)
    assert owner.city.life_max == 8 and owner.city.life == 4


def test_pactos_militar_e_mente_afetam_combate():
    state = make_state()
    p2 = state.players[1]
    p2.city.gold = p2.city.magic = 20
    troop = summon_troop(state, 2, TroopArchetype.LIGHT, 4)
    troop.house = "city_3"
    peoples.make_demon_pact(state, 1, 2, "sacrifique_militar")
    state.phase = Phase.NIGHT
    try:
        resolve_attack(state, Attack(troop.id, "city", "3"))
        raise AssertionError("Tropa sob pacto atacou Base")
    except CombatError:
        pass
    state2 = make_state()
    p2 = state2.players[1]
    p2.city.gold = p2.city.magic = 20
    p3 = state2.players[2]
    p3.city.gold = p3.city.magic = 20
    atk = summon_troop(state2, 2, TroopArchetype.LIGHT, 1)
    target = summon_troop(state2, 3, TroopArchetype.HEAVY, 8)
    atk.house = target.house = CENTER
    peoples.make_demon_pact(state2, 1, 2, "sacrifique_mente")
    state2.phase = Phase.NIGHT
    before = target.life
    resolve_attack(state2, Attack(atk.id, "unit", target.id))
    assert before - target.life == 2


def test_banho_de_sangue_e_vida_de_lider():
    state = make_state()
    blood = peoples.make_demon_pact(state, 1, 2, "banho_sangue")
    state.phase = Phase.NIGHT
    for i in range(3):
        dead = Troop(id=f"dead{i}", owner_id=3, house=CENTER, life=0, life_max=4,
                     killed_by_player_id=2)
        peoples.on_any_unit_death(state, dead)
    assert blood["completed"] and blood["rewarded"]
    leader = peoples.make_demon_pact(state, 1, 2, "vida_lider")
    peoples.on_city_destroyed_for_pacts(state, 2)
    assert leader["completed"] and leader["rewarded"]


def test_belial_area_and_pact_offer():
    state = make_state()
    demon = state.players[0]
    demon.city.magic = 20
    belial = summon_hero(state, 1)
    belial.house = CENTER
    enemy = state.players[1]
    enemy.city.gold = enemy.city.magic = 20
    hero = summon_hero(state, 2)
    hero.house = CENTER
    on_night_start(state)
    assert hero.life == 3
    hero.life = 1
    on_night_start(state)
    assert demon.city.magic == 18
    assert demon.demon_pact_offers and demon.demon_pact_offers[0]["source"] == "belial"


def test_tuza_e_rogue_ofertas():
    state = make_state("tuza")
    state.players[0].city.magic = 20
    tuza = summon_hero(state, 1)
    assert tuza.resistance_stacks == 1
    state.curuna_id = 1
    assert peoples.can_take_tuza_pact(state, 2) == 1
    rogue_state = make_state("rogue_devil")
    rogue_state.players[0].city.magic = 20
    rogue = summon_hero(rogue_state, 1)
    assert rogue_state.players[0].demon_pact_offers
    peoples.make_demon_pact(rogue_state, 1, 1, "sacrifique_mente", "execucao")
    assert rogue.statuses["demon_execute_weaker"]


def test_sacrificio_remove_efeito_ativo_e_serializa():
    state = make_state()
    player = state.players[0]
    player.city.magic = 20
    summon_hero(state, 1)
    target = state.players[1]
    player.hand = ["J_C", "K_D"]
    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})
    assert target.skip_night_turn == state.turn
    cast_spell(state, 1, {"artifacts": [{"zone": "field", "card_id": "J_C"},
                                         {"zone": "hand", "card_id": "K_D"}]})
    assert target.skip_night_turn is None and target.skip_day_turn is None
    assert len(player.hand) == 2
    restored = state_from_dict(state_to_dict(state))
    assert restored.demon_pacts == state.demon_pacts


def run_all():
    tests = [test_banco_de_almas_qualquer_morte,
             test_pacto_sacrificio_recompensa_unico_e_reversivel,
             test_pactos_militar_e_mente_afetam_combate,
             test_banho_de_sangue_e_vida_de_lider,
             test_belial_area_and_pact_offer, test_tuza_e_rogue_ofertas,
             test_sacrificio_remove_efeito_ativo_e_serializa]
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
