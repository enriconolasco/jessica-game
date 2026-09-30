"""Importação do terminal e recuperação, sempre em diretórios temporários."""
import os, sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jessica.web import server, saves, session
from jessica.core.headless import apply_action, legal_actions, SAVE_VERSION
from jessica.core.serialize import state_to_dict
from jessica.core.constants import Phase
from test_web_usability import http
from test_web_vertical import _request, _error_request


def daytime(people="humanos"):
    catalog = {p["id"]: p for p in server._catalog()["peoples"]}
    chosen = [people] + [p for p in server.PEOPLES if p != people][:3]
    players = [{"name": f"J{i+1}", "people": p,
                "hero_id": catalog[p]["heroes"][0]["id"] if catalog[p]["heroes"] else ""}
               for i, p in enumerate(chosen)]
    state = server._new_state(92, players, {"order_mode":"fixed", "gold":8, "magic":10})
    bets = next((a for a in legal_actions(state, state.active_player_id)
                 if a["type"] == "allocate_bets"), None)
    if bets:
        assert apply_action(state, bets)["success"]
    return state


def raw_terminal(state):
    data = state_to_dict(state)
    for key in ("active_player_id", "web_night", "web_reaction"):
        data.pop(key, None)
    return data


def test_terminal_day_import_preserves_all_twelve_peoples_state_and_rng():
    for people in server.PEOPLES:
        original = daytime(people)
        raw = raw_terminal(original); before = deepcopy(raw)
        payload, warnings = saves.import_payload(raw)
        restored, events, _ = saves.validate(payload)
        assert state_to_dict(restored) == state_to_dict(original), people
        assert raw == before and warnings
        assert events[0]["type"] == "match_imported"
        action = next(a for a in legal_actions(original, 1) if a["type"] == "collect_resources")
        assert apply_action(original, action) == apply_action(restored, action)
        assert state_to_dict(original) == state_to_dict(restored), people


def test_terminal_rejects_ambiguous_days_night_without_queue_and_future_versions():
    raw = raw_terminal(daytime())
    raw["players"][1]["morning_done_this_turn"] = True
    try:
        saves.import_payload(raw); raise AssertionError("dia ambíguo aceito")
    except ValueError as exc:
        assert "inequívoca" in str(exc)
    raw = raw_terminal(daytime()); raw["phase"] = "night"
    try:
        saves.import_payload(raw); raise AssertionError("noite sem fila aceita")
    except ValueError as exc:
        assert "fila de declarações" in str(exc)
    try:
        saves.import_payload({"version":"save-future", "state":raw})
        raise AssertionError("versão futura aceita")
    except saves.VersionError:
        pass


def test_imported_day_is_not_a_fake_start_checkpoint_and_survives_save_load():
    payload, _ = saves.import_payload(raw_terminal(daytime()))
    state, events, name = saves.validate(payload)
    match = {"state":state, "events":events, "name":name, "history":[],
             "checkpoint_skip":payload["checkpoint_skip"]}
    action = next(a for a in legal_actions(state, 1) if a["type"] == "collect_resources")
    assert apply_action(state, action)["success"]
    session.checkpoint(match)
    assert not match["history"] and not session.controls(match)["undo"]
    with http() as base:
        _, imported = _request(base, "/matches/import", "POST", payload)
        mid = imported["match_id"]
        _, snapshot = _request(base, f"/matches/{mid}/export")
        _, loaded = _request(base, "/matches/import", "POST", snapshot)
        restored = server.MATCHES[loaded["match_id"]]
        session.checkpoint(restored)
        assert not session.controls(restored)["undo"]
    action = next(a for a in legal_actions(state, 1) if a["type"] == "end_turn")
    assert apply_action(state, action)["success"]
    session.checkpoint(match)
    assert session.controls(match)["undo"] and not session.controls(match)["mola"]
    assert match["history"][0]["player_id"] == 2


def test_import_http_privacy_rejection_and_next_action_parity():
    original = daytime()
    original.players[1].hand = ["PENA"]
    original.event_log.append("Jogador 2 comprou PENA, informação privada")
    raw = raw_terminal(original)
    with http() as base:
        status, imported = _request(base, "/matches/import", "POST", raw)
        assert status == 201 and len(imported["warnings"]) == 3
        mid = imported["match_id"]
        _, view = _request(base, f"/matches/{mid}/view?player_id=1")
        _, events = _request(base, f"/matches/{mid}/events?player_id=1")
        assert "PENA" not in str(view) and "PENA" not in str(events)
        _, snapshot = _request(base, f"/matches/{mid}/export")
        assert "PENA" in str(snapshot) and snapshot["checkpoint_skip"]["player_id"] == 1
        _, actions = _request(base, f"/matches/{mid}/actions?player_id=1")
        action = next(a for a in actions if a["type"] == "collect_resources")
        _request(base, f"/matches/{mid}/actions", "POST", action)
        assert apply_action(original, action)["success"]
        assert state_to_dict(original) == state_to_dict(server.MATCHES[mid]["state"])
        before_files = {p.name: p.read_bytes() for p in server.SAVES.glob("*.json")}
        before_matches = set(server.MATCHES)
        raw["phase"] = "night"
        status, error = _error_request(base, "/matches/import", raw)
        assert status == 422 and "fila" in error["error"]
        assert set(server.MATCHES) == before_matches
        assert {p.name:p.read_bytes() for p in server.SAVES.glob("*.json")} == before_files


def test_rotating_autosaves_preserve_five_previous_rng_states_and_manual_saves():
    state = daytime(); payload = {"version":SAVE_VERSION, "state":state_to_dict(state), "events":[], "name":"Teste"}
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp); current = directory / "abcdef123456.json"
        manual = directory / "aaaaaaaaaaaa.json"
        saves.write(manual, {**payload, "kind":"manual"})
        manual_bytes = manual.read_bytes()
        states = []
        for turn in range(1,10):
            state.turn = turn; state.rng.randint(1,20)
            payload["state"] = state_to_dict(state); states.append(deepcopy(payload["state"]))
            saves.write_autosave(current, {**payload, "kind":"autosave"})
        entries = saves.list_saved(directory)
        recoveries = [e for e in entries if e["kind"] == "recovery"]
        assert len(recoveries) == saves.AUTOSAVE_HISTORY_LIMIT == 5
        assert {e["turn"] for e in recoveries} == {4,5,6,7,8}
        for entry in recoveries:
            restored, _, _ = saves.validate(saves.read(saves.save_path(directory,entry["save_id"])))
            assert state_to_dict(restored) == states[entry["turn"]-1]
        assert saves.read(current)["state"] == states[-1]
        assert manual.read_bytes() == manual_bytes and len(list(directory.glob("*.json"))) == 7


def test_failed_atomic_write_does_not_replace_current_save():
    payload = {"version":SAVE_VERSION,"state":state_to_dict(daytime()),"events":[]}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "abcdef123456.json"; saves.write(path,payload)
        original = path.read_bytes(); changed = deepcopy(payload); changed["state"]["turn"] = 2
        with patch.object(Path,"replace",side_effect=OSError("simulated write failure")):
            try:
                saves.write(path,changed); raise AssertionError("falha ignorada")
            except OSError:
                pass
        assert path.read_bytes() == original
        corrupt = deepcopy(payload); corrupt["state"]["rng"]["state"] = "bad"
        try:
            saves.write(path,corrupt); raise AssertionError("save inválido gravado")
        except ValueError:
            pass
        assert path.read_bytes() == original


def test_http_recovery_load_preserves_history_and_rejected_actions_do_not_rotate():
    with http() as base:
        _, created = _request(base,"/matches","POST",{"seed":92,"config":{"order_mode":"fixed"}})
        mid = created["match_id"]
        _, baseline = _request(base,f"/matches/{mid}/export")
        _, actions = _request(base,f"/matches/{mid}/actions")
        collect = next(a for a in actions if a["type"] == "collect_resources")
        _request(base,f"/matches/{mid}/actions","POST",collect)
        _, entries = _request(base,"/saves")
        recoveries = [e for e in entries if e["kind"] == "recovery"]
        assert len(recoveries) == 1 and "state" not in str(entries) and "events" not in str(entries)
        before = {p.name:p.read_bytes() for p in server.SAVES.glob("*.json")}
        assert _error_request(base,f"/matches/{mid}/actions",collect)[0] == 422
        assert {p.name:p.read_bytes() for p in server.SAVES.glob("*.json")} == before
        _, loaded = _request(base,"/matches/load","POST",{"save_id":recoveries[0]["save_id"]})
        _, restored = _request(base,f"/matches/{loaded['match_id']}/export")
        assert {k:v for k,v in restored.items() if k != "name"} == {k:v for k,v in baseline.items() if k != "name"}
        assert session.controls(server.MATCHES[loaded["match_id"]])["undo"]


def test_disk_failure_warns_without_losing_accepted_action_or_claiming_manual_save():
    with http() as base:
        _, created = _request(base,"/matches","POST",{"seed":92,"config":{"order_mode":"fixed"}})
        mid = created["match_id"]; previous = (server.SAVES / f"{mid}.json").read_bytes()
        _, actions = _request(base,f"/matches/{mid}/actions")
        collect = next(a for a in actions if a["type"] == "collect_resources")
        with patch.object(saves,"write",side_effect=OSError("disk full")):
            status, result = _request(base,f"/matches/{mid}/actions","POST",collect)
            assert status == 200 and result["success"] and "memória" in result["save_warning"]
            assert _error_request(base,f"/matches/{mid}/save",{"name":"Cópia"})[0] == 507
            _, created = _request(base,"/matches","POST",{"seed":93})
            assert created["match_id"] in server.MATCHES and created["save_warning"]
        assert (server.SAVES / f"{mid}.json").read_bytes() == previous
        assert server.MATCHES[mid]["state"].players[0].has_collected_this_turn


def test_generated_ids_do_not_overwrite_existing_files():
    from types import SimpleNamespace
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp); path = directory / "aaaaaaaaaaaa.json"
        path.write_text("manual",encoding="utf-8")
        with patch.object(saves.uuid,"uuid4",side_effect=[SimpleNamespace(hex="a"*32),SimpleNamespace(hex="b"*32)]):
            assert saves.new_id(directory) == "b"*12
        assert path.read_text(encoding="utf-8") == "manual"


def test_rotation_isolated_by_match_even_with_identical_file_timestamps():
    payload = {"version":SAVE_VERSION,"state":state_to_dict(daytime()),"events":[]}
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp); first = directory / "aaaaaaaaaaaa.json"; other = directory / "bbbbbbbbbbbb.json"
        saves.write_autosave(other,payload)
        payload["state"]["turn"] = 2; saves.write_autosave(other,payload)
        protected = {p.name:p.read_bytes() for p in directory.glob("*.json")}
        for turn in range(1,9):
            payload["state"]["turn"] = turn; saves.write_autosave(first,payload)
            for path in directory.glob("*.json"):
                os.utime(path,(1000000000,1000000000))
        recoveries = [e for e in saves.list_saved(directory) if e.get("source_match_id") == first.stem]
        assert {e["turn"] for e in recoveries} == {3,4,5,6,7}
        assert all((directory/name).read_bytes() == data for name,data in protected.items())


if __name__ == "__main__":
    passed = failed = 0
    for name,test in sorted(list(globals().items())):
        if name.startswith("test_") and callable(test):
            try:
                test(); passed += 1
            except Exception as exc:
                failed += 1; print(f"FALHOU - {name}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
