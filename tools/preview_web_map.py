"""Synthetic public PlayerView for visual QA; no match or save is modified.

Run: python tools/preview_web_map.py, then open http://127.0.0.1:8766.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.web.server import Handler, STATIC, ThreadingHTTPServer


def fixture():
    players = [
        {"id": 1, "name": "Ana", "people": "humanos"},
        {"id": 2, "name": "Beto", "people": "dragoes"},
        {"id": 3, "name": "Cris", "people": "fadas"},
        {"id": 4, "name": "Dani", "people": "povo_desconhecido"},
    ]
    units = []
    for index in range(36):
        owner = index % 4 + 1
        hero = index < 4 or index >= 32
        units.append({
            "id": f"qa_{index:02}", "owner_id": owner,
            "house": "center" if index < 28 else f"city_{owner}",
            "kind": "hero" if hero else "troop",
            "hero_id": ["miyamoto", "purpura", "luna", "heroi_desconhecido"][owner - 1] if hero else None,
            "archetype": None if hero else "light", "life": 2, "life_max": 4,
            "statuses": {"invisivel_until_turn": 3} if index == 0 else {},
            "resistance_stacks": 1 if index == 1 else 0, "double_damage": False,
        })
    return {"players": players, "board": {"units": units}}


class PreviewHandler(Handler):
    def do_GET(self):
        if self._parts():
            return super().do_GET()
        script = """
<script>
api('/catalog').then(data => {
  catalog = data;
  $('start').hidden = true;
  $('game').hidden = false;
  $('status').textContent = 'Prévia de teste · 36 unidades sintéticas · nenhum save alterado';
  $('save').hidden = true;
  document.querySelector('#game > .grid').remove();
  renderMap(FIXTURE);
});
</script>
""".replace("FIXTURE", json.dumps(fixture(), ensure_ascii=False))
        body = STATIC.joinpath("index.html").read_text(encoding="utf-8")
        payload = body.replace("</body>", script + "</body>").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    print("Prévia do mapa: http://127.0.0.1:8766", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8766), PreviewHandler).serve_forever()
