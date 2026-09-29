"""Paridade e atomicidade das escolhas disponíveis no navegador."""
import os
import sys
from copy import deepcopy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.web.server import _new_state
from jessica.core.headless import legal_actions, apply_action, view_for_player, apply_event_to_view
from jessica.core import actions, artifacts_effects
from jessica.core.models import Hero, Troop, ArtifactOnField
from jessica.core.constants import Phase
from jessica.core.serialize import state_to_dict, state_from_dict


def ready():
    state = _new_state(72)
    for p in state.players:
        p.city.gold = p.city.magic = 30
        p.units.append(Troop(id=f"target_{p.id}", owner_id=p.id, house="center", life=2, life_max=4))
    state.players[0].hand = sorted(artifacts_effects.IMPLEMENTED)
    return state


def test_todos_artefatos_tem_paridade_com_core():
    initial = ready()
    candidates = [a for a in legal_actions(initial, 1) if a["type"] == "play_artifact"]
    assert {a["params"]["card_id"] for a in candidates} == artifacts_effects.IMPLEMENTED
    for card in sorted(artifacts_effects.IMPLEMENTED):
        action = next(a for a in candidates if a["params"]["card_id"] == card)
        direct, web = deepcopy(initial), deepcopy(initial)
        actions.play_artifact(direct, 1, **action["params"])
        assert apply_action(web, action)["success"]
        assert state_to_dict(web) == state_to_dict(direct), card


def test_escolha_invalida_nao_altera_estado_ou_rng():
    state = ready()
    before = state_to_dict(state)
    action = next(a for a in legal_actions(state, 1) if a["type"] == "play_artifact")
    action["params"]["choice"] = {"unit_id": "inexistente"}
    action["params"]["card_id"] = "K_C"
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before
    assert legal_actions(state, 2) == []


def test_pendencia_obrigatoria_save_load_e_eventos_privados():
    state = ready()
    p = state.players[0]
    p.pending_artifact_choice = {"kind": "J_D", "cards": ["K_H", "J_S", "Q_D"], "pick": 2,
                                 "card_id": "J_D"}
    p.field_artifacts.append(ArtifactOnField(card_id="J_D", owner_id=1))
    state = state_from_dict(state_to_dict(state))
    choices = legal_actions(state, 1)
    assert len(choices) == 3 and all(a["type"] == "resolve_artifact_choice" for a in choices)
    view = view_for_player(state, 1)
    assert view_for_player(state, 2)["self"]["pending_choice"] is None
    result = apply_action(state, choices[0])
    assert result["success"] and state.players[0].pending_artifact_choice is None
    assert all(event["visibility"]["kind"] == "private" for event in result["events"])
    for event in result["events"]:
        view = apply_event_to_view(view, event)
    view["events"] = []
    assert view == view_for_player(state, 1)


def test_rogue_oferta_obrigatoria_e_recompensas_imediatas():
    setup = [{"name": "D", "people": "demonios", "hero_id": "rogue_devil"},
             {"name": "H", "people": "humanos", "hero_id": "miyamoto"},
             {"name": "O", "people": "orcs", "hero_id": "arken"},
             {"name": "F", "people": "fadas", "hero_id": "ainai"}]
    state = _new_state(4, setup, {"magic": 10})
    summon = next(a for a in legal_actions(state, 1) if a["type"] == "summon_hero")
    assert apply_action(state, summon)["success"]
    offered = legal_actions(state, 1)
    assert offered and all(a["type"] == "demon_pact" for a in offered)
    choice = next(a for a in offered if a["params"]["pact_id"] == "banho_sangue"
                  and a["params"]["item"] == "capa")
    before = len(state.players[0].hand)
    assert apply_action(state, choice)["success"]
    owner = state.players[0]
    assert owner.units[0].life == 1 and owner.rogue_items == ["capa"]
    assert len(owner.hand) == before + 1 and not owner.demon_pact_offers


def test_habilidades_deterministicas_e_fase_validada():
    setup = [{"name": "D", "people": "dragoes", "hero_id": "barba_negra"},
             {"name": "H", "people": "humanos", "hero_id": "miyamoto"},
             {"name": "O", "people": "orcs", "hero_id": "arken"},
             {"name": "F", "people": "fadas", "hero_id": "ainai"}]
    state = _new_state(7, setup)
    before = state_to_dict(state)
    candidates = legal_actions(state, 1)
    assert state_to_dict(state) == before
    action = next(a for a in candidates if a["params"].get("ability") == "barba_flames")
    twin = state_from_dict(before)
    assert apply_action(state, action) == apply_action(twin, deepcopy(action))
    assert state_to_dict(state) == state_to_dict(twin)
    state.phase = Phase.NIGHT
    before = state_to_dict(state)
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before


def test_nove_feiticos_equivalentes_ao_core():
    for people, hero in (("humanos", "miyamoto"), ("anoes", "ori"), ("orcs", "arken"),
                         ("vampiros", "luide_vampa"), ("lobisomens", "cigana"),
                         ("gigantes", "caroco"), ("mortos_vivos", "zoia"),
                         ("filhos_floresta", "guarari"), ("dragoes", "purpura")):
        initial = ready()
        p = initial.players[0]
        p.people, p.chosen_hero_id = people, hero
        p.units.append(Hero(id="spell_hero", owner_id=1, house="center",
                            life=6, life_max=6, hero_id=hero))
        before = state_to_dict(initial)
        choices = [a for a in legal_actions(initial, 1) if a["type"] == "cast_spell"]
        assert choices, people
        assert state_to_dict(initial) == before, people
        direct, web = deepcopy(initial), deepcopy(initial)
        actions.cast_spell(direct, 1, choices[0]["params"]["choice"])
        result = apply_action(web, choices[0])
        assert result["success"], (people, result)
        assert state_to_dict(web) == state_to_dict(direct), people


def test_caroco_web_bloqueia_repeticao_sem_consumir_rng():
    state = ready()
    p = state.players[0]
    p.people = "gigantes"
    p.units = [Hero(id=f"c{i}", owner_id=1, house="center", life=2, life_max=2,
                    hero_id="caroco") for i in range(2)]
    options = [a for a in legal_actions(state, 1) if a["type"] == "cast_spell"]
    assert len(options) == 1
    assert apply_action(state, options[0])["success"]
    assert sum("[ROLL] Cabaca Cheia" in line for line in state.event_log) == 2
    before = state_to_dict(state)
    assert not apply_action(state, options[0])["success"]
    assert state_to_dict(state) == before


def test_sao_tome_rerrolagem_deterministica_uma_vez():
    state = ready()
    p = state.players[0]
    p.people = "gnomos_duendes"
    p.spell_copia_id = "resistencia"
    p.spell_copia_turn = state.turn
    p.units.append(Hero(id="tome", owner_id=1, house="center", life=3, life_max=3,
                        hero_id="sao_tome"))
    before = state_to_dict(state)
    choice = next(a for a in legal_actions(state, 1) if a["type"] == "reroll_spell")
    assert state_to_dict(state) == before
    twin = state_from_dict(before)
    assert apply_action(state, choice) == apply_action(twin, choice)
    assert state_to_dict(state) == state_to_dict(twin)
    assert not any(a["type"] == "reroll_spell" for a in legal_actions(state, 1))


def test_http_artefato_e_historico_sobrevivem_ao_load():
    import tempfile
    import threading
    from pathlib import Path
    from jessica.web import server
    from tests.test_web_vertical import _request
    old_saves = server.SAVES
    with tempfile.TemporaryDirectory() as folder:
        server.SAVES = Path(folder)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            _, created = _request(base, "/matches", "POST", {"seed": 5})
            mid = created["match_id"]
            server.MATCHES[mid]["state"].players[0].hand = ["K_D"]
            _, offered = _request(base, f"/matches/{mid}/actions?player_id=1")
            action = next(a for a in offered if a["type"] == "play_artifact")
            _, result = _request(base, f"/matches/{mid}/actions", "POST", action)
            assert result["success"]
            _, rival_events = _request(base, f"/matches/{mid}/events?player_id=2")
            assert all(e["type"] != "player_view_updated" for e in rival_events)
            _, saved = _request(base, f"/matches/{mid}/save", "POST", {})
            _, loaded = _request(base, "/matches/load", "POST", {"save_id": saved["save_id"]})
            resumed = loaded["match_id"]
            _, view = _request(base, f"/matches/{resumed}/view?player_id=1")
            _, history = _request(base, f"/matches/{resumed}/events?player_id=1")
            assert view["players"][0]["field_artifacts"] == ["K_D"]
            assert history == result["events"]
            assert state_to_dict(server.MATCHES[mid]["state"]) == state_to_dict(server.MATCHES[resumed]["state"])
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join()
            server.SAVES = old_saves


def test_sacrificio_multicartas_paridade_save_e_privacidade():
    for people in ("demonios", "gnomos_duendes"):
        state = ready()
        p = state.players[0]
        p.people = people
        p.spell_copia_id = "sacrificio_de_demonio"
        p.chosen_hero_id = "tuza"
        p.units.append(Hero(id="sacrifice", owner_id=1, house="center",
                            life=6, life_max=6, hero_id="tuza"))
        p.hand = ["K_H", "K_H", "Q_D"]
        p.field_artifacts.append(ArtifactOnField(card_id="K_D", owner_id=1))
        before = state_to_dict(state)
        offer = next(a for a in legal_actions(state, 1) if a["type"] == "sacrifice_spell")
        assert state_to_dict(state) == before
        offer["params"]["artifacts"] = offer["selection"]["options"]
        direct = state_from_dict(before)
        actions.cast_spell(direct, 1, offer["params"])
        result = apply_action(state, offer)
        assert result["success"], result
        assert state_to_dict(state) == state_to_dict(direct)
        assert "artifacts" not in result["events"][0]["data"]
        assert state_to_dict(state_from_dict(state_to_dict(state))) == state_to_dict(state)


def test_sacrificio_rejeita_excesso_e_jogador_errado():
    state = ready()
    p = state.players[0]
    p.people = "demonios"
    p.units.append(Hero(id="sacrifice", owner_id=1, house="center",
                        life=6, life_max=6, hero_id="tuza"))
    offer = next(a for a in legal_actions(state, 1) if a["type"] == "sacrifice_spell")
    before = state_to_dict(state)
    offer["params"]["artifacts"] *= 100
    assert not apply_action(state, offer)["success"]
    assert state_to_dict(state) == before
    offer["player_id"] = 2
    assert not apply_action(state, offer)["success"]
    assert state_to_dict(state) == before


def test_sonho_lucido_web_copia_alvo_paridade_e_rejeicao():
    for people in ("fadas", "gnomos_duendes"):
        state = ready()
        p = state.players[0]
        p.people = people
        p.spell_copia_id = "sonho_lucido"
        p.hand = ["K_S"]
        before = state_to_dict(state)
        offer = next(a for a in legal_actions(state, 1) if a["type"] == "cast_spell")
        assert state_to_dict(state) == before
        assert offer["params"]["choice"]["artifact_choices"][0]["unit_id"]
        direct = state_from_dict(before)
        actions.cast_spell(direct, 1, offer["params"]["choice"])
        assert apply_action(state, offer)["success"]
        assert state_to_dict(state) == state_to_dict(direct)
        assert "K_C" not in state.players[0].hand
        rejected = state_from_dict(before)
        offer["params"]["choice"]["artifact_choices"] = [{"unit_id": "unknown"}]
        assert not apply_action(rejected, offer)["success"]
        assert state_to_dict(rejected) == before


def test_coleta_tres_distribuicoes_uma_vez_por_turno():
    for gold in (0, 1, 2):
        state = ready()
        p = state.players[0]
        before_gold, before_magic = p.city.gold, p.city.magic
        choices = [a for a in legal_actions(state, 1) if a["type"] == "collect_resources"]
        assert len(choices) == 3
        action = next(a for a in choices if a["params"]["gold"] == gold)
        result = apply_action(state, action)
        assert result["success"]
        p = state.players[0]
        assert (p.city.gold, p.city.magic) == (before_gold + gold, before_magic + 2 - gold)
        before = state_to_dict(state)
        assert not apply_action(state, action)["success"]
        assert state_to_dict(state) == before
        assert not any(a["type"] == "collect_resources" for a in legal_actions(state, 1))


def test_aiquara_web_paridade_limite_e_imunidade():
    state = ready()
    p = state.players[0]
    p.units.append(Hero(id="ninfa", owner_id=1, house="center",
                        life=3, life_max=3, hero_id="aiquara"))
    state.players[1].units.append(Hero(id="immune", owner_id=2, house="center",
                                     life=20, life_max=20, hero_id="valtherion"))
    before = state_to_dict(state)
    choices = [a for a in legal_actions(state, 1)
               if a["params"].get("ability") == "aiquara_move"]
    assert choices
    assert not any(a["params"]["args"]["enemy_unit_id"] == "immune" for a in choices)
    assert state_to_dict(state) == before
    action = choices[0]
    direct = state_from_dict(before)
    actions.aiquara_mover(direct, 1, **action["params"]["args"])
    assert apply_action(state, action)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    before = state_to_dict(state)
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before


def test_zebum_web_paridade_reinvocacao_e_restricoes():
    state = ready()
    p = state.players[0]
    p.units.append(Hero(id="zebum", owner_id=1, house="center",
                        life=3, life_max=3, hero_id="zebum"))
    p.correct_bets = 30
    before = state_to_dict(state)
    choices = [a for a in legal_actions(state, 1)
               if a["params"].get("ability") == "zebum_summon"]
    assert choices and state_to_dict(state) == before
    forbidden = {other.chosen_hero_id for other in state.players[1:]}
    assert not any(a["params"]["args"]["hero_id"] in forbidden for a in choices)
    action = next(a for a in choices if a["params"]["args"]["hero_id"] != "seven_dwarves")
    direct = state_from_dict(before)
    actions.zebum_invocar_heroi(direct, 1, **action["params"]["args"])
    assert apply_action(state, action)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    acquired = action["params"]["args"]["hero_id"]
    p = state.players[0]
    next(u for u in p.units if isinstance(u, Hero) and u.hero_id == acquired).life = 0
    choices = legal_actions(state, 1)
    action = next(a for a in choices if a["params"].get("ability") == "zebum_resummon")
    direct = state_from_dict(state_to_dict(state))
    actions.zebum_reinvocar(direct, 1, **action["params"]["args"])
    assert apply_action(state, action)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    state.phase = Phase.NIGHT
    assert not apply_action(state, action)["success"]


def betting_state():
    return _new_state(72, [
        {"name": "H", "people": "humanos", "hero_id": "miyamoto"},
        {"name": "O", "people": "orcs", "hero_id": "arken"},
        {"name": "G", "people": "gnomos_duendes", "hero_id": "sao_tome"},
        {"name": "F", "people": "fadas", "hero_id": "ainai"}])


def test_apostas_antes_curruna_save_e_determinismo():
    state = betting_state()
    assert state.active_player_id == 3
    assert not state.players[0].morning_done_this_turn
    assert legal_actions(state, 1) == []
    before = state_to_dict(state)
    offers = legal_actions(state, 3)
    assert len(offers) == 1 and offers[0]["type"] == "allocate_bets"
    assert state_to_dict(state) == before
    action = offers[0]
    action["params"] = {"bets": {"H": 1, "C": 2, "D": None, "S": 4}}
    twin = state_from_dict(before)
    result = apply_action(state, action)
    assert result["success"]
    assert apply_action(twin, action) == result
    assert state_to_dict(state) == state_to_dict(twin)
    assert state.active_player_id == state.curuna_id
    assert state.players[0].morning_done_this_turn
    assert not state.players[2].bets_need_realocacao
    assert state.players[2].bet_H_target == 1
    assert all(e["visibility"]["kind"] == "private" for e in result["events"])
    before = state_to_dict(state)
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before


def test_apostas_invalidas_atomicas():
    state = betting_state()
    action = legal_actions(state, 3)[0]
    before = state_to_dict(state)
    for value in (True, 3, 99, "1", [], {}):
        action["params"] = {"bets": {"H": value, "C": None, "D": None, "S": None}}
        assert not apply_action(state, action)["success"]
        assert state_to_dict(state) == before
    action["params"] = {"bets": dict.fromkeys("HCDS")}
    assert apply_action(state, action)["success"]


def test_luna_multicartas_paridade_ordem_save_e_atomicidade():
    state = ready()
    p = state.players[0]
    p.people = "fadas"
    p.hand = ["K_H", "K_S"]
    p.units.append(Hero(id="luna", owner_id=1, house="center", life=2, life_max=2, hero_id="luna"))
    before = state_to_dict(state)
    offer = next(a for a in legal_actions(state, 1) if a["type"] == "dream_multi")
    assert state_to_dict(state) == before
    options = offer["selection"]["options"]
    first = next(o["choice"] for o in options if o["choice"]["flip_cards"] == ["K_H"])
    second = next(o["choice"] for o in options if o["choice"]["flip_cards"] == ["K_S"])
    choice = {"flip_cards": first["flip_cards"] + second["flip_cards"],
              "artifact_choices": first["artifact_choices"] + second["artifact_choices"]}
    offer["params"] = {"choice": choice}
    direct = state_from_dict(before)
    actions.cast_spell(direct, 1, choice)
    assert apply_action(state, offer)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    assert state_to_dict(state_from_dict(state_to_dict(state))) == state_to_dict(state)
    for cards, targets in ((["K_H", "K_H"], [{}, {}]), (["K_S"], [{"unit_id": "missing"}]),
                           ([], []), (["K_H"], [])):
        rejected = state_from_dict(before)
        offer["params"] = {"choice": {"flip_cards": cards, "artifact_choices": targets}}
        assert not apply_action(rejected, offer)["success"]
        assert state_to_dict(rejected) == before


def test_luna_preview_invoca_e_oferece_novo_alvo_sem_mutacao():
    from jessica.core.interaction_actions import dream_preview
    state = ready()
    p = state.players[0]
    p.people = "fadas"
    p.chosen_hero_id = "luna"
    p.hand = ["J_D", "K_S"]
    p.units = [Hero(id="luna", owner_id=1, house="center", life=2, life_max=2, hero_id="luna")]
    before = state_to_dict(state)
    prefix = {"flip_cards": ["J_D"], "artifact_choices": [{"hero_id": "ainai"}]}
    preview = dream_preview(state, 1, prefix)
    assert state_to_dict(state) == before
    next_choice = next(o["choice"] for o in preview["options"]
                       if o["choice"]["artifact_choices"] == [{"unit_id": "p1_hero_extra_1"}])
    choice = {"flip_cards": prefix["flip_cards"] + next_choice["flip_cards"],
              "artifact_choices": prefix["artifact_choices"] + next_choice["artifact_choices"]}
    action = next(a for a in legal_actions(state, 1) if a["type"] == "dream_multi")
    action["params"] = {"choice": choice}
    direct = state_from_dict(before)
    restored = state_from_dict(before)
    actions.cast_spell(direct, 1, choice)
    assert apply_action(state, action) == apply_action(restored, action)
    assert state_to_dict(state) == state_to_dict(direct) == state_to_dict(restored)
    hero = next(u for u in state.players[0].units if u.id == "p1_hero_extra_1")
    assert hero.double_damage and hero.resistance_stacks == 1
    assert not apply_action(state, action)["success"]
    rejected = state_from_dict(before)
    action["params"]["choice"]["artifact_choices"][1] = {"unit_id": "missing"}
    assert not apply_action(rejected, action)["success"]
    assert state_to_dict(rejected) == before


def test_luna_jd_nao_precisa_ser_ultima_carta():
    state = ready()
    p = state.players[0]
    p.people = "fadas"
    p.hand = ["J_H", "K_H"]
    p.units.append(Hero(id="luna", owner_id=1, house="center", life=2, life_max=2, hero_id="luna"))
    action = next(a for a in legal_actions(state, 1) if a["type"] == "dream_multi")
    choice = {"flip_cards": ["J_H", "K_H"], "artifact_choices": [{}, {}]}
    action["params"] = {"choice": choice}
    direct = state_from_dict(state_to_dict(state))
    actions.cast_spell(direct, 1, choice)
    assert apply_action(state, action)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    assert any(e["kind"] == "J_D" and e["due_turn"] == state.turn + 3 for e in state.pending_effects)


def test_miyamoto_day_attack_parity_and_shared_night_limit():
    from jessica.core import combat
    from jessica.core.turn import end_day
    state = ready()
    p = state.players[0]
    p.units = [Hero(id="miyamoto", owner_id=1, house="center", life=8, life_max=8, hero_id="miyamoto")]
    state.players[1].units.append(Troop(id="distant", owner_id=2, house="city_2", life=2, life_max=4))
    invisible = state.players[2].units[0]
    invisible.statuses["invisivel_until_turn"] = state.turn
    before = state_to_dict(state)
    offers = [a for a in legal_actions(state, 1) if a["type"] == "day_attack"]
    assert offers and state_to_dict(state) == before
    assert not any(a["params"]["target_id"] in ("distant", invisible.id) for a in offers)
    action = offers[0]
    direct = state_from_dict(before)
    combat.resolve_attack_day(direct, combat.Attack(**action["params"]))
    assert apply_action(state, action)["success"]
    assert state_to_dict(state) == state_to_dict(direct)
    used = state.players[0].units[0].attacks_made_this_day
    assert used == 1
    state = state_from_dict(state_to_dict(state))
    end_day(state)
    assert state.players[0].units[0].attacks_made_this_day == used
    before = state_to_dict(state)
    assert not apply_action(state, action)["success"]
    assert state_to_dict(state) == before


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
