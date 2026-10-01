"""Escolhas combinadas, disponibilidade dinâmica e paridade das habilidades."""
import json
import os
import sys
from copy import deepcopy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.web.server import _new_state
from jessica.core import actions, interaction_actions, night_actions, peoples
from jessica.core.constants import Phase
from jessica.core.headless import apply_action, legal_actions, view_for_player
from jessica.core.models import Hero, Troop
from jessica.core.serialize import state_from_dict, state_to_dict
from jessica.core.turn import end_day, _process_gigantes_turn
from jessica.core.state import snapshot_turn_start_priority
from test_night_terminal_parity import compare


def ready(people="demonios", hero="belial"):
    state = _new_state(72)
    for player in state.players:
        player.units = []
        player.hand = []
        player.city.gold = player.city.magic = 30
    player = state.players[0]
    player.people, player.chosen_hero_id = people, hero
    player.bets_need_realocacao = False
    player.hand = ["J_H", "K_S"]
    return state


def raise_rogue(state):
    actions.play_artifact(state, 1, "J_H", choice={"hero_id": "rogue_devil"})
    assert state.players[0].demon_pact_offers


def take_all_pacts(state):
    for pact in list(peoples.available_demon_pacts(state)):
        peoples.make_demon_pact(state, 1, 2, pact)


def test_rogue_por_valete_sem_pactos_nao_bloqueia_dia():
    state = ready()
    take_all_pacts(state)
    direct = deepcopy(state)
    actions.play_artifact(direct, 1, "J_H", choice={"hero_id": "rogue_devil"})
    card = next(a for a in legal_actions(state, 1) if a["type"] == "play_artifact"
                and a["params"] == {"card_id": "J_H", "choice": {"hero_id": "rogue_devil"}})
    assert apply_action(state, card)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    before = state_to_dict(state)
    offered = legal_actions(state, 1)
    assert {"collect_resources", "end_turn"} <= {a["type"] for a in offered}
    assert not any(a["type"] == "demon_pact" for a in offered)
    assert state_to_dict(state) == before
    assert state.players[0].rogue_life_bonus == 0


def test_rogue_sem_pactos_nao_bloqueia_noite_apos_save():
    state = ready()
    take_all_pacts(state)
    raise_rogue(state)
    end_day(state)
    state = state_from_dict(state_to_dict(state))
    before = state_to_dict(state)
    offered = legal_actions(state, 1)
    assert [a["type"] for a in offered] == ["finish_night"]
    assert state_to_dict(state) == before
    assert apply_action(state, offered[0])["success"]
    assert state.phase == Phase.DAY and state.turn == 2


def test_perder_passiva_demonios_nao_prende_gnomos():
    state = ready()
    raise_rogue(state)
    state.players[0].people = "gnomos_duendes"
    state.players[0].chosen_hero_id = "sao_tome"
    before = state_to_dict(state)
    offered = legal_actions(state, 1)
    assert any(a["type"] == "end_turn" for a in offered)
    assert not any(a["type"] == "demon_pact" for a in offered)
    assert state_to_dict(state) == before
    end_day(state)
    assert night_actions.pending_owner(state) is None
    assert any(a["type"] == "finish_night" for a in legal_actions(state, 1))


def test_oferta_invalida_nao_oculta_rogue_valido():
    state = ready()
    raise_rogue(state)
    player = state.players[0]
    player.demon_pact_offers.insert(0, {"source": "rogue_devil", "demon_player_id": 2})
    before = state_to_dict(state)
    offered = legal_actions(state, 1)
    assert offered and all(a["type"] == "demon_pact" and a["params"]["offer_index"] == 1
                           for a in offered)
    assert state_to_dict(state) == before
    invalid = deepcopy(offered[0])
    invalid["params"]["offer_index"] = 0
    assert not apply_action(state, invalid)["success"]
    assert state_to_dict(state) == before
    assert apply_action(state, offered[0])["success"]


def test_oferta_rogue_sem_heroi_nao_bloqueia_dia():
    state = ready()
    raise_rogue(state)
    state.players[0].units = []
    assert any(a["type"] == "end_turn" for a in legal_actions(state, 1))
    assert night_actions.pending_owner(state) is None


def test_oferta_de_eliminado_nao_toma_controle_da_noite():
    state = ready()
    state.players[0].city.life = 0
    state.players[0].demon_pact_offers = [{"source": "belial", "demon_player_id": 1}]
    end_day(state)
    assert night_actions.pending_owner(state) is None
    assert any(a["type"] == "finish_night" for a in legal_actions(state, 2))


def test_recusa_opcional_continua_disponivel_com_loja_de_pactos_esgotada():
    state = ready()
    take_all_pacts(state)
    state.players[0].demon_pact_offers = [{"source": "belial", "demon_player_id": 1}]
    end_day(state)
    choices = legal_actions(state, 1)
    assert [a["type"] for a in choices] == ["night_decline_pact"]
    assert apply_action(state, choices[0])["success"]
    assert any(a["type"] == "finish_night" for a in legal_actions(state, 1))


def ability_scenarios():
    cases = [("orcs", "arken", "arken"), ("anoes", "tintin", "tintin"),
             ("vampiros", "dandara", "dandara"), ("dragoes", "purpura", "purpura"),
             ("dragoes", "barba_negra", "barba_flames"),
             ("dragoes", "barba_negra", "barba_combat"),
             ("filhos_floresta", "baoba_ba", "baoba"),
             ("gnomos_duendes", "bimbo_do_mal", "bimbo_hide"),
             ("gnomos_duendes", "bimbo_do_mal", "bimbo_artifact"),
             ("filhos_floresta", "guarari", "guarari"),
             ("dragoes", "valtherion", "valtherion")]
    for people, hero, ability in cases:
        state = ready(people, hero)
        player = state.players[0]
        player.correct_bets = 6
        if ability != "baoba":
            player.units = [Hero(id="hero", owner_id=1, hero_id=hero,
                                 house="city_2" if ability == "arken" else "center",
                                 life=3, life_max=4)]
        player.units.append(Troop(id="ally", owner_id=1, house="center", life=2, life_max=4))
        state = state_from_dict(state_to_dict(state))
        yield ability, state


def test_habilidades_de_dia_paridade_save_rng_e_parametros_invalidos():
    for ability, state in ability_scenarios():
        before = state_to_dict(state)
        choices = [a for a in legal_actions(state, 1) if a["type"] == "hero_ability"
                   and a["params"]["ability"] == ability]
        assert choices and state_to_dict(state) == before, ability
        for candidate in choices:
            action = json.loads(json.dumps(candidate))
            direct, web = state_from_dict(before), state_from_dict(before)
            interaction_actions.execute(direct, action)
            assert apply_action(web, action)["success"], ability
            assert state_to_dict(web) == state_to_dict(direct), ability
            twin = state_from_dict(before)
            assert apply_action(twin, action)["success"]
            assert state_to_dict(twin) == state_to_dict(web), ability
        bad = deepcopy(choices[0])
        bad["params"]["args"]["unrecognized_parameter"] = True
        assert not apply_action(state, bad)["success"], ability
        assert state_to_dict(state) == before, ability


def test_janela_luide_vazia_mostra_local_atual_nao_combate_futuro():
    state = ready("vampiros", "luide_vampa")
    player = state.players[0]
    player.units = [Hero(id="luide", owner_id=1, hero_id="luide_vampa",
                         house="center", life=6, life_max=6, max_moves_this_turn=2)]
    state.players[1].units = [Troop(id="enemy", owner_id=2, house="city_2", life=4, life_max=4)]
    end_day(state)
    move = next(a for a in legal_actions(state, 1) if a["type"] == "night_luide_move"
                and a["params"]["destination"] == "city_2")
    assert apply_action(state, move)["success"]
    before = state_to_dict(state)
    window = view_for_player(state, 1)["night_window"]
    assert window == {"kind": "luide", "house": "center", "unit_id": None,
                      "player_id": 1, "declaration_order": [1]}
    assert state_to_dict(state) == before


def test_janela_de_preparacao_nao_rotula_combate_ainda_nao_iniciado():
    state = ready("orcs", "vovo_gamba")
    state.players[0].units = [Hero(id="vovo", owner_id=1, hero_id="vovo_gamba",
                                 house="center", life=4, life_max=4)]
    end_day(state)
    window = view_for_player(state, 1)["night_window"]
    assert window["kind"] == "vovo" and window["house"] is None
    assert window["unit_id"] is None and window["player_id"] == 1


def mixed_night_case(group, turn):
    setup = [{"name": f"J{pid}", "people": people, "hero_id": hero}
             for pid, (people, hero) in enumerate(group, 1)]
    state = _new_state(810 + turn, setup, {"magic": 30, "gold": 30, "order_mode": "fixed"})
    state.turn, state.curuna_id = turn, 3
    _process_gigantes_turn(state)
    for player in state.players:
        player.bets_need_realocacao = False
        if not any(isinstance(u, Hero) and u.is_alive() for u in player.units):
            actions.summon_hero(state, player.id,
                                force_hero_id=group[player.id - 1][1] if player.people == "mortos_vivos" else None)
        for unit in player.units:
            unit.house = "center"
        player.units.append(Troop(id=f"troop{player.id}", owner_id=player.id,
                                  house="center", life=3, life_max=4))
    if group[0][0] == "gnomos_duendes":
        gnomo = state.players[0]
        gnomo.bet_H_target = 2
        gnomo.spell_copia_id = "ressonancia_magica"
        gnomo.hand.append("J_H")
        actions.cast_spell(state, 1, {"action": "add", "card_id": "J_H"})
        dragon = state.players[1]
        dragon.hand.append("Q_C")
        actions.cast_spell(state, 2, {"action": "add", "card_id": "Q_C"})
    snapshot_turn_start_priority(state)
    end_day(state)
    plan = {}
    for player in state.players:
        enemy = state.players[player.id % 4]
        own_hero = next(u for u in player.units if isinstance(u, Hero))
        enemy_hero = next(u for u in enemy.units if isinstance(u, Hero))
        plan[own_hero.id] = [("unit", f"troop{enemy.id}")]
        plan[f"troop{player.id}"] = [("unit", enemy_hero.id)]
    return state, plan


def mixed_night(group, turn):
    state, plan = mixed_night_case(group, turn)
    state, trace = compare(state, plan)
    assert trace and state.phase == Phase.NIGHT


def test_cruzamento_humanos_anoes_orcs_fadas_igual_terminal():
    for turn in (1, 4):
        mixed_night([("humanos", "miyamoto"), ("anoes", "seven_dwarves"),
                     ("orcs", "vovo_gamba"), ("fadas", "luna")], turn)


def test_cruzamento_vampiros_lobisomens_gigantes_mortos_vivos_igual_terminal():
    for turn in (1, 4):
        mixed_night([("vampiros", "dracula"), ("lobisomens", "cigana"),
                     ("gigantes", "caroco"), ("mortos_vivos", "cova_rasa")], turn)


def test_cruzamento_sao_tome_canastra_demonios_filhos_igual_terminal():
    for turn in (1, 4):
        mixed_night([("gnomos_duendes", "sao_tome"), ("dragoes", "purpura"),
                     ("demonios", "tuza"), ("filhos_floresta", "guarari")], turn)


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
