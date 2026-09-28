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
