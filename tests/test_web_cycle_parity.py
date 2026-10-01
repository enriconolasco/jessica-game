"""Ciclo noturno/diurno e cruzamentos reativos, restaurando cada decisão."""
import os
import sys
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica.core import combat, night_actions
from jessica.core.constants import Phase
from jessica.core.headless import apply_action, legal_actions, view_for_player
from jessica.core.models import Hero, Troop, ArtifactOnField
from jessica.core.serialize import state_to_dict, state_from_dict
from jessica.core.state import log
from jessica.core.turn import day_order, end_day, end_turn, start_turn, start_player_day
from jessica.web import saves, server
from test_night_web import night
from test_night_terminal_parity import mechanics


def step(state, action):
    before = state_to_dict(state)
    restored = state_from_dict(before)
    result = apply_action(state, action)
    assert result["success"], result
    assert result == apply_action(restored, action)
    assert state_to_dict(state) == state_to_dict(restored)
    # Persistência usa a validação real do servidor, inclusive reações pendentes.
    restored, _, _ = saves.validate({"version": "save-v0.1", "state": state_to_dict(state),
                                    "events": result["events"], "history": []})
    snapshot = state_to_dict(restored)
    for player in restored.players:
        legal_actions(restored, player.id)
        view_for_player(restored, player.id)
    assert state_to_dict(restored) == snapshot
    return restored


def finish(state):
    action = next(a for a in legal_actions(state, state.active_player_id or state.curuna_id)
                  if a["type"] == "finish_night")
    return step(state, action)


def terminal_next_turn(state):
    direct = deepcopy(state)
    log(direct, f"--- Fim da Noite (Turno {direct.turn}) ---")
    end_turn(direct)
    if not direct.game_over:
        start_turn(direct)
        order = day_order(direct)
        if order:
            start_player_day(direct, order[0])
        else:
            end_day(direct)
    return direct


def test_next_curuna_skipped_opens_first_eligible_day():
    for skipped in ((2,), (2, 3), (2, 3, 4), (2, 3, 4, 1)):
        state = night()
        for pid in skipped:
            state.players[pid - 1].skip_day_turn = 2
        direct = terminal_next_turn(state)
        final = finish(state)
        assert mechanics(final) == mechanics(direct), skipped
        if len(skipped) < 4:
            assert final.active_player_id == day_order(final)[0]
            assert final.players[1].morning_done_this_turn is False
            assert legal_actions(final, 2) == []
        else:
            assert final.phase == Phase.NIGHT


def test_skipped_gnome_bets_still_precede_first_eligible_day():
    state = night()
    state.players[1].people = "gnomos_duendes"
    state.players[1].skip_day_turn = 2
    state = finish(state)
    assert state.active_player_id == 2
    assert not any(p.morning_done_this_turn for p in state.players)
    choices = legal_actions(state, 2)
    assert [a["type"] for a in choices] == ["allocate_bets"]
    state = step(state, choices[0])
    assert state.active_player_id == 3 and state.players[2].morning_done_this_turn
    assert not state.players[1].morning_done_this_turn and legal_actions(state, 2) == []


def test_stale_active_skipped_player_cannot_take_normal_actions():
    state = server._new_state(7)
    state.players[0].skip_day_turn = state.turn
    before = state_to_dict(state)
    assert legal_actions(state, 1) == []
    action = {"version": "action-v0.1", "type": "collect_resources", "player_id": 1,
              "params": {"gold": 0, "magic": 2}}
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before


def test_next_turn_mornings_interest_and_rng_for_twelve_peoples():
    for people in server.PEOPLES:
        state = night()
        state.players[1].people = people
        for player in state.players:
            player.city.gold = 12
        if people == "gnomos_duendes":
            # Apostas são verificadas no caso separado, não ignoradas pelo comparador.
            direct = deepcopy(state)
            log(direct, f"--- Fim da Noite (Turno {direct.turn}) ---")
            end_turn(direct)
            start_turn(direct)
            state = finish(state)
            assert mechanics(state) == mechanics(direct)
            state = step(state, legal_actions(state, 2)[0])
            direct.players[1].bets_need_realocacao = False
            start_player_day(direct, 2)
        else:
            direct = terminal_next_turn(state)
            state = finish(state)
        assert mechanics(state) == mechanics(direct), people
        assert state.turn == 2 and state.phase == Phase.DAY
        assert state.active_player_id == 2 and state.players[1].morning_done_this_turn


def test_end_night_restores_control_expires_effects_and_cleans_spectres():
    state = night()
    controlled = Troop(id="controlled", owner_id=1, original_owner_id=2,
                       house="center", life=4, life_max=4, double_damage=True)
    state.players[0].units = [controlled, Troop(id="spectre", owner_id=1, house="city_1",
        life=2, life_max=2, statuses={"espectro_until_turn": state.turn})]
    state.players[0].field_artifacts = [ArtifactOnField("Q_C", 1,
        {"target_unit_id": "controlled", "original_owner_id": 2})]
    state.players[0].double_damage_until_end_night = True
    direct = terminal_next_turn(state)
    final = finish(state)
    assert mechanics(final) == mechanics(direct)
    assert not final.players[0].units and not final.players[0].field_artifacts
    assert final.players[1].units[0].id == "controlled"
    assert final.players[1].units[0].owner_id == 2
    assert not final.players[1].units[0].double_damage


def test_delayed_death_and_demon_magic_at_end_night():
    state = night()
    state.players[0].people = "demonios"
    state.players[1].units = [Troop(id="doomed", owner_id=2, house="city_2", life=4, life_max=4)]
    state.dain_kills = [{"turn": state.turn, "attacker_id": "doomed"}]
    magic = state.players[0].city.magic
    direct = terminal_next_turn(state)
    final = finish(state)
    assert mechanics(final) == mechanics(direct)
    assert not final.players[1].units and not final.dain_kills
    assert final.players[0].city.magic == magic + 1


def test_armor_retaliation_kills_luide_and_closes_window():
    state = night()
    state.players[1].people = "vampiros"
    state.players[0].units = [Troop(id="attacker", owner_id=1, house="center", life=4, life_max=4)]
    state.players[1].units = [Hero(id="luide", owner_id=2, house="center", life=1,
                                 life_max=3, hero_id="luide_vampa")]
    state.players[1].armor_active_until_turn = state.turn
    state.players[1].city.gold = 8
    night_actions.prepare(state)
    direct = deepcopy(state)
    attack = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
    state = step(state, attack)
    assert state.active_player_id == 2 and state.web_reaction
    payment = legal_actions(state, 2)[0]
    payment["params"] = {"gold": 0}
    state = step(state, payment)
    with combat.armor_policy(lambda p, damage: 0):
        combat.resolve_attack(direct, combat.Attack(**attack["params"]))
    night_actions.advance(direct)
    assert state_to_dict(state) == state_to_dict(direct)
    assert not state.players[1].units and not state.web_reaction
    assert not any(a["type"].startswith("night_luide") for a in legal_actions(state, 2))


def test_elimination_during_armor_reaction_reaches_victory():
    state = night()
    state.players[2].city.life = state.players[3].city.life = 0
    state.players[1].city.life = 1
    state.players[0].armor_active_until_turn = state.turn
    state.players[0].city.gold = 8
    state.players[0].units = [Troop(id="siege", owner_id=1, house="city_2", life=4, life_max=4)]
    night_actions.prepare(state)
    direct = deepcopy(state)
    attack = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
    state = step(state, attack)
    assert state.web_reaction and not state.game_over
    payment = legal_actions(state, 1)[0]
    payment["params"] = {"gold": 0}
    state = step(state, payment)
    with combat.armor_policy(lambda p, damage: 0):
        combat.resolve_attack(direct, combat.Attack(**attack["params"]))
    night_actions.advance(direct)
    assert state_to_dict(state) == state_to_dict(direct)
    assert state.game_over and state.winner_id == 1
    assert all(legal_actions(state, p.id) == [] for p in state.players)


def test_armor_then_qd_preserves_belial_pact_for_next_day():
    from jessica.core.actions import resolve_pending_artifact_choice
    from jessica.core.interaction_actions import execute
    for accept in (False, True):
        state = night()
        state.players[0].units = [Hero(id="miyamoto", owner_id=1, house="center",
                                      life=6, life_max=6, hero_id="miyamoto")]
        state.players[1].units = [Hero(id="marked", owner_id=2, house="center",
                                      life=1, life_max=4, hero_id="arken")]
        state.players[1].armor_active_until_turn = state.turn
        state.players[1].city.gold = 8
        state.players[2].field_artifacts = [ArtifactOnField("Q_D", 3,
            {"target_unit_id": "marked"})]
        state.players[3].people = "demonios"
        state.players[3].units = [Hero(id="belial", owner_id=4, house="city_4",
                                      life=2, life_max=2, hero_id="belial")]
        night_actions.prepare(state)
        direct = deepcopy(state)
        attack = next(a for a in legal_actions(state, 1) if a["type"] == "night_attack")
        state = step(state, attack)
        assert state.active_player_id == 2 and state.web_reaction
        payment = legal_actions(state, 2)[0]
        payment["params"] = {"gold": 0}
        state = step(state, payment)
        with combat.armor_policy(lambda p, damage: 0):
            combat.resolve_attack(direct, combat.Attack(**attack["params"]))
        night_actions.advance(direct)
        assert state_to_dict(state) == state_to_dict(direct)
        assert state.active_player_id == 3 and not state.web_reaction
        assert legal_actions(state, 1) == []
        choice = next(a for a in legal_actions(state, 3) if a["params"] == {"resource": "magic"})
        state = step(state, choice)
        resolve_pending_artifact_choice(direct, 3, resource="magic")
        night_actions.advance(direct)
        assert state_to_dict(state) == state_to_dict(direct)
        assert state.active_player_id == 1 and state.players[0].demon_pact_offers
        assert not state.players[2].pending_artifact_choice
        assert not state.demon_pacts
        assert not any(a["type"] in ("night_pact", "night_decline_pact")
                       for a in legal_actions(state, 1))
        state = finish(state)
        assert state.turn == 2 and state.active_player_id == 2
        assert state.players[0].demon_pact_offers
        assert not any(a["type"] == "demon_pact" for a in legal_actions(state, 1))
        while state.active_player_id != 1:
            state = step(state, next(a for a in legal_actions(state, state.active_player_id)
                                    if a["type"] == "end_turn"))
        assert state.phase == Phase.DAY
        direct = deepcopy(state)
        if accept:
            action = next(a for a in legal_actions(state, 1)
                          if a["params"].get("pact_id") == "sacrifique_futuro")
        else:
            action = next(a for a in legal_actions(state, 1) if a["type"] == "decline_pact")
        state = step(state, action)
        execute(direct, action)
        assert state_to_dict(state) == state_to_dict(direct)
        assert not state.players[0].demon_pact_offers and not state.players[2].pending_artifact_choice
        assert state.turn == 2 and state.active_player_id == 1


def test_http_skipped_curuna_handoff_save_and_load():
    from test_web_usability import http
    from test_web_vertical import _request, _error_request
    state = night()
    state.players[1].skip_day_turn = 2
    night_actions.prepare(state)
    with http() as base:
        _, created = _request(base, "/matches/import", "POST", {
            "version": "save-v0.1", "state": state_to_dict(state), "events": [], "history": []})
        mid = created["match_id"]
        _, choices = _request(base, f"/matches/{mid}/actions")
        action = next(a for a in choices if a["type"] == "finish_night")
        _, result = _request(base, f"/matches/{mid}/actions", "POST", action)
        assert result["success"]
        _, view = _request(base, f"/matches/{mid}/view")
        assert view["active_player_id"] == 3 and view["curuna_id"] == 2
        assert view["viewer_id"] == 3
        _, choices = _request(base, f"/matches/{mid}/actions?player_id=2")
        assert choices == []
        invalid = {"version": "action-v0.1", "type": "collect_resources", "player_id": 2,
                   "params": {"gold": 0, "magic": 2}}
        assert _error_request(base, f"/matches/{mid}/actions", invalid)[0] == 422
        _, saved = _request(base, f"/matches/{mid}/save", "POST", {"name": "Dia elegível"})
        _, loaded = _request(base, "/matches/load", "POST", {"save_id": saved["save_id"]})
        _, restored = _request(base, f"/matches/{loaded['match_id']}/view")
        assert restored == view
        _, choices = _request(base, f"/matches/{loaded['match_id']}/actions")
        assert choices and all(a["player_id"] == 3 for a in choices)


def test_luna_dream_sequence_new_hero_control_night_and_next_morning():
    from jessica.core.actions import cast_spell
    from jessica.core.interaction_actions import dream_preview
    from test_night_terminal_parity import compare
    state = night()
    state.phase = Phase.DAY
    state.active_player_id = 1
    player = state.players[0]
    player.people = "fadas"
    player.chosen_hero_id = "luna"
    player.city.magic = 20
    player.hand = ["J_D", "K_S", "Q_S"]
    player.units = [Hero(id="luna", owner_id=1, house="city_1", life=2, life_max=2,
                         hero_id="luna", resistance_stacks=2)]
    state.players[1].units = [Troop(id="controlled", owner_id=2, house="center", life=4, life_max=4),
                              Troop(id="old_ally", owner_id=2, house="center", life=2, life_max=4)]
    state.players[2].units = [Troop(id="enemy", owner_id=3, house="city_1", life=2,
                                  life_max=4, resistance_stacks=1)]
    choice = {"flip_cards": ["J_D", "K_S", "Q_S"],
              "artifact_choices": [{"hero_id": "ainai"}, {"unit_id": "p1_hero_extra_1"},
                                   {"unit_id": "controlled"}]}
    before = state_to_dict(state)
    prefix = {key: value[:1] for key, value in choice.items()}
    preview = dream_preview(state, 1, prefix)
    assert any(o["choice"]["artifact_choices"] == [{"unit_id": "p1_hero_extra_1"}]
               for o in preview["options"])
    assert state_to_dict(state) == before
    direct = deepcopy(state)
    cast_spell(direct, 1, choice)
    action = next(a for a in legal_actions(state, 1) if a["type"] == "dream_multi")
    action["params"] = {"choice": choice}
    state = step(state, action)
    assert state_to_dict(state) == state_to_dict(direct)
    end_day(state)
    plan = {"luna": [("unit", "enemy")], "p1_hero_extra_1": [("unit", "enemy")],
            "controlled": [("unit", "old_ally")]}
    state, trace = compare(state, plan, lambda title, labels: 0,
                           real_windows=("_try_luna_return", "_ainai_prompt_all"))
    assert len(trace) == 3
    direct = terminal_next_turn(state)
    state = finish(state)
    assert mechanics(state) == mechanics(direct)
    assert state.players[1].units[0].id == "controlled"
    assert state.players[1].units[0].owner_id == 2
    assert not state.players[0].has_cast_spell_this_turn


def test_ainai_queue_metadata_validation_and_legacy_save():
    state = night()
    for pid in (1, 2):
        state.players[pid - 1].units = [Troop(id=f"u{pid}", owner_id=pid,
            house="center", life=4, life_max=4)]
    night_actions.prepare(state)
    payload = {"version": "save-v0.1", "state": state_to_dict(state), "events": []}
    for key in ("final_ainai_queued", "occupied"):
        invalid = deepcopy(payload)
        queue = invalid["state"]["web_night"]
        if key == "final_ainai_queued":
            queue[key] = "yes"
        else:
            next(e for e in queue["queue"] if e.get("kind") == "end_house")[key] = 1
        try:
            saves.validate(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Metadado inválido aceito: {key}")
    for entry in payload["state"]["web_night"]["queue"]:
        entry.pop("occupied", None)
    restored, _, _ = saves.validate(payload)
    assert "final_ainai_queued" not in restored.web_night
    for pid in (1, 2):
        restored = step(restored, next(a for a in legal_actions(restored, pid)
                                      if a["type"] == "night_pass"))
    assert restored.web_night["final_ainai_queued"] is True
    assert legal_actions(restored, 1)[0]["type"] == "finish_night"


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
