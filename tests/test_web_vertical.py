"""Contrato HTTP da prova web vertical."""
import json
import os
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.web import server


def _request(base, path, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read())


def _raw(base, path):
    with urllib.request.urlopen(base + path) as response:
        return response.status, response.headers.get_content_type(), response.read()


def test_http_vertical_action_view_events_and_autosave():
    old_saves = server.SAVES
    with tempfile.TemporaryDirectory() as tmp:
        server.SAVES = Path(tmp)
        httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            status, created = _request(base, "/matches", "POST", {"seed": 42})
            assert status == 201
            match_id = created["match_id"]
            _, view = _request(base, f"/matches/{match_id}/view?player_id=1")
            _, actions = _request(base, f"/matches/{match_id}/actions?player_id=1")
            action = next(a for a in actions if a["type"] == "collect_resources")
            _, result = _request(base, f"/matches/{match_id}/actions", "POST", action)
            _, events = _request(base, f"/matches/{match_id}/events")
            assert view["active_player_id"] == 1
            assert result["success"] is True
            assert events[-1]["type"] == "resources_collected"
            assert (Path(tmp) / f"{match_id}.json").is_file()
            status, mime, icon = _raw(base, "/assets/visual-direction-v0.2/icons/people-humanos-32.svg")
            assert status == 200 and mime == "image/svg+xml" and b"<svg" in icon
        finally:
            httpd.shutdown()
            server.SAVES = old_saves


def test_all_people_icons_and_map_template_exist():
    root = Path(__file__).resolve().parents[1] / "assets"
    files = ("humanos", "anoes", "orcs", "fadas", "vampiros", "lobisomens",
             "gigantes", "mortos-vivos", "filhos-floresta", "gnomos-duendes",
             "dragoes", "demonios")
    assert all((root / "visual-direction-v0.2" / "icons" / f"people-{name}-32.svg").is_file()
               for name in files)
    assert (root / "visual-direction-v0.1" / "map" / "minimap-template-cross-v0.1.svg").is_file()


def run_all():
    tests = [test_http_vertical_action_view_events_and_autosave,
             test_all_people_icons_and_map_template_exist]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"FALHOU - {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n=== {passed} passaram, {failed} falharam ===")


if __name__ == "__main__":
    run_all()
