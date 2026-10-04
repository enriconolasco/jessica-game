import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from copy import deepcopy
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from rich.console import Console

from jessica.core.headless import view_for_player, apply_action, legal_actions
from jessica.core.serialize import state_to_dict, state_from_dict, save_to_file, load_from_file
from jessica.core.turn import start_turn, start_player_day, end_day, end_turn, day_order
from jessica.core.victory import check_victory
from jessica.narrative.engine import (VERSION, TRIGGERS, PROFILES, load_catalog,
    validate_catalog, restore_session, lifecycle_event, observe, replay)
from jessica.narrative.terminal import narrate, write_checkpoint, read_checkpoint
from test_turn import make_state


def emit(state, trigger, session=None, **kwargs):
    view = view_for_player(state, 1)
    event = lifecycle_event(trigger, view, **kwargs)
    return observe(state.seed, {} if session is None else session, event, view)


def mechanical(state):
    data = state_to_dict(state)
    data.pop("narrative", None)
    return data


def test_pilot_complete_and_valid():
    entries, errors = load_catalog()
    assert len(entries) == 30 and not errors
    assert {e["trigger"] for e in entries} == TRIGGERS
    for seed in range(30):
        state = make_state(); state.seed = seed
        session, text = emit(state, "match_started")
        assert text and "{" not in text and session["profile"] in PROFILES


def test_catalog_validation():
    entry = load_catalog()[0][0]
    for changes in ({"id":"bad id"}, {"weight":True}, {"weight":0}, {"trigger":"made_up"},
                    {"text":"{hand}"}, {"text":"{player.__class__}"}, {"text":"{player!r}"},
                    {"text":"{player:>9}"}, {"text":"{"}, {"conditions":{"terrain":"forest"}},
                    {"conditions":{"season":"never"}}, {"trigger":[]}):
        entries, errors = validate_catalog({"version":VERSION,"entries":[{**entry, **changes}]})
        assert not entries and errors, changes
    assert not validate_catalog({"version":VERSION,"entries":[entry,entry]})[0]


def test_determinism_and_no_mechanical_mutation():
    state = make_state(); before = mechanical(state)
    a, text_a = emit(state, "match_started")
    b, text_b = emit(state, "match_started")
    assert a == b and text_a == text_b and mechanical(state) == before
    rng = state.rng.state
    state.narrative = a
    emit(state, "turn_started", a)
    assert state.rng.state == rng and mechanical(state) == before


def test_save_load_sequence_consumption_and_replay():
    state = make_state()
    state.narrative, first = emit(state, "match_started")
    with TemporaryDirectory() as folder:
        path = Path(folder)/"save.json"
        save_to_file(state, str(path)); restored = load_from_file(str(path))
    session, text = emit(restored, "match_started", restored.narrative)
    assert text is None and session == state.narrative
    original_next = emit(state, "turn_started", state.narrative)
    restored_next = emit(restored, "turn_started", restored.narrative)
    assert original_next == restored_next
    assert replay(session)[0]["text"] == first
    assert replay(session)[0]["fields"] == state.narrative["history"][0]["fields"]


def test_private_events_and_context_do_not_leak():
    state = make_state(); view = view_for_player(state, 1)
    view["self"] = {"hand":["SECRET"], "pending_choice":"SECRET"}
    event = lifecycle_event("match_started", view)
    event["data"]["secret"] = "SECRET"
    session, text = observe(state.seed, {}, event, view)
    assert "SECRET" not in str(session) and "SECRET" not in text
    for kind in ("private", "players", "unknown"):
        event["visibility"] = {"kind":kind,"player_ids":[1]}
        assert observe(state.seed, session, event, view) == (session,None)
    before = deepcopy(state_to_dict(state))
    assert before == state_to_dict(state)


def test_anti_repetition_and_stable_profile():
    state = make_state(); session, _ = emit(state, "match_started")
    profile = deepcopy(session["profile"]); choices = []
    for turn in range(1,18):
        state.turn = turn
        session, text = emit(state, "turn_started", session)
        choices.append(session["history"][-1]["entry_id"])
        assert text and session["profile"] == profile
    assert len(set(choices[:8])) == 8
    assert all(a != b for a,b in zip(choices,choices[1:]))


def test_missing_invalid_and_incompatible_content_is_safe():
    state = make_state(); view = view_for_player(state,1)
    event = lifecycle_event("match_started",view)
    assert load_catalog(Path("not-present-999.json"))[0] == []
    assert observe(state.seed,{},event,view,entries=[]) == ({},None)
    assert observe(state.seed,{},event,view,entries=[{"bad":True}]) == ({},None)
    for changes in ({"type":[]}, {"visibility":None}, {"turn":"1"},
                    {"data":None}, {"data":{"player_id":[]}}):
        assert observe(state.seed,{}, {**event,**changes},view) == ({},None)
    assert observe(state.seed,{},event,{}) == ({},None)
    session, _ = emit(state,"match_started")
    corrupt = {**session,"rng":{"state":"broken"}}
    assert restore_session(corrupt) == {}
    assert observe(state.seed,corrupt,event,view) == (corrupt,None)
    old = state_to_dict(state); old.pop("narrative",None)
    assert state_from_dict(old).narrative == {}
    old["narrative"] = corrupt
    assert state_from_dict(old).narrative == {}


def test_incompatible_entries_consume_event_without_fabrication():
    state = make_state(); view = view_for_player(state,1)
    event = lifecycle_event("turn_started",view)
    entries = [e for e in load_catalog()[0] if e["trigger"] == "match_started"]
    session, text = observe(state.seed,{},event,view,entries=entries)
    assert text is None and session["history"][-1]["entry_id"] is None
    assert observe(state.seed,session,event,view)[1] is None


def test_rich_markup_is_literal_and_no_additional_prompt():
    state = make_state(); state.players[0].name = "[bold]Pessoa[/bold]"
    stream = StringIO(); console = Console(file=stream,force_terminal=False,width=200)
    narrate(console,state,"player_turn_ended","breve",1,2)
    assert "[bold]Pessoa[/bold]" in stream.getvalue()
    assert state.narrative
    old = deepcopy(state_to_dict(state))
    narrate(console,state,"turn_started","desligada")
    assert state_to_dict(state) == old


def test_undo_restores_narrative_progress():
    state = make_state(); state.narrative, _ = emit(state,"match_started")
    snapshot = state_to_dict(state)
    first = emit(state,"turn_started",state.narrative)
    state.narrative = first[0]
    restored = state_from_dict(snapshot)
    assert emit(restored,"turn_started",restored.narrative) == first


def test_complete_cycles_equal_with_narrative_on_and_off():
    a = make_state(); b = state_from_dict(state_to_dict(a))
    console = Console(file=StringIO(),width=120)
    narrate(console,a,"match_started","breve")
    for _ in range(3):
        for state in (a,b):
            start_turn(state)
            narrate(console,state,"turn_started","breve" if state is a else "desligada")
            order = day_order(state)
            for index, pid in enumerate(order):
                state.active_player_id = pid
                start_player_day(state,pid)
                action = next(a for a in legal_actions(state,pid) if a["type"] == "collect_resources")
                assert apply_action(state,action)["success"]
                narrate(console,state,"player_turn_ended","breve" if state is a else "desligada",
                        pid,order[index+1] if index+1 < len(order) else None)
            state.active_player_id = None
            end_day(state); end_turn(state)
        assert mechanical(a) == mechanical(b)
    for state in (a,b):
        for player in state.players[1:]: player.city.life = 0
        check_victory(state)
        narrate(console,state,"match_ended","breve" if state is a else "desligada")
    assert a.winner_id == b.winner_id == 1 and mechanical(a) == mechanical(b)
    for player in a.players: player.city.life = 0
    a.game_over = False; check_victory(a)
    a.narrative = {}
    session, text = emit(a,"match_ended")
    assert "empate" in text.lower() or "sem vencedor" in text.lower()
    assert session["history"][-1]["entry_id"].startswith("fim.empate.")


def test_checkpoint_boundary_roundtrip_and_reject_web_save():
    state = make_state(); state.narrative, _ = emit(state,"match_started")
    with TemporaryDirectory() as folder:
        path = Path(folder)/"terminal.json"
        write_checkpoint(state,path); restored = read_checkpoint(path)
        assert state_to_dict(state) == state_to_dict(restored)
        save_to_file(state,str(path))
        try: read_checkpoint(path)
        except ValueError: pass
        else: raise AssertionError("Save intermediário não deve entrar na retomada terminal")


def test_terminal_flow_integrates_lifecycle_and_checkpoint():
    from jessica import main
    state = make_state()
    def finish(state):
        for p in state.players[1:]: p.city.life = 0
        check_victory(state)
    with TemporaryDirectory() as folder, patch.object(main,"console",Console(file=StringIO())), \
            patch.object(main,"setup_ui",return_value=state), \
            patch.object(main,"_gnomos_bets_inicio_turno"), \
            patch.object(main,"run_player_day",return_value=None), \
            patch.object(main,"run_night_phase",side_effect=finish):
        path = Path(folder)/"checkpoint.json"
        main._run_one_game(narrative_mode="breve",checkpoint=path)
        triggers = {r["trigger"] for r in state.narrative["history"]}
        assert triggers == TRIGGERS
        assert read_checkpoint(path).game_over
        old = deepcopy(state.narrative)
        main._run_one_game(state,narrative_mode="breve")
        assert state.narrative == old


if __name__ == "__main__":
    tests = [v for k,v in list(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for test in tests:
        try: test(); passed += 1
        except Exception as error:
            import traceback
            traceback.print_exc()
            print(f"FALHOU {test.__name__}: {error}"); failed += 1
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(bool(failed))
