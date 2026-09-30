"""Servidor descartável para QA manual: python -B tests/serve_ui_scenarios.py."""
import argparse
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jessica.core import night_actions
from jessica.core.constants import Phase
from jessica.core.headless import SAVE_VERSION, apply_action, legal_actions
from jessica.core.models import ArtifactOnField, Hero, Troop
from jessica.core.serialize import state_to_dict
from jessica.core.turn import end_day
from jessica.web import saves, server


def scenarios():
    sacrifice = server._new_state(72)
    player = sacrifice.players[0]
    player.people, player.chosen_hero_id = "demonios", "tuza"
    player.city.magic = 20
    player.units = [Hero(id="tuza", owner_id=1, house="center", life=6,
                         life_max=6, hero_id="tuza")]
    player.hand = ["K_H", "Q_D"]
    player.field_artifacts = [ArtifactOnField("K_D", 1)]
    assert any(a["type"] == "sacrifice_spell" for a in legal_actions(sacrifice, 1))

    dream = server._new_state(72)
    for p in dream.players:
        p.units = []
    player = dream.players[0]
    player.people, player.chosen_hero_id = "fadas", "luna"
    player.city.magic = 20
    player.hand = ["J_D", "K_S", "Q_S"]
    player.units = [Hero(id="luna", owner_id=1, house="city_1", life=2,
                         life_max=2, hero_id="luna")]
    dream.players[1].units = [Troop(id="target", owner_id=2, house="center", life=4, life_max=4)]
    assert any(a["type"] == "dream_multi" for a in legal_actions(dream, 1))

    armor = server._new_state(72)
    for p in armor.players:
        p.units = []
    end_day(armor)
    for pid in (1, 2):
        player = armor.players[pid - 1]
        player.city.gold = 8
        player.armor_active_until_turn = armor.turn
        player.hand = ["J_H"] if pid == 1 else ["K_H"]
        player.units = [Troop(id=f"t{pid}", owner_id=pid, house="center", life=4, life_max=4)]
    night_actions.prepare(armor)
    attack = next(a for a in legal_actions(armor, armor.active_player_id) if a["type"] == "night_attack")
    assert apply_action(armor, attack)["success"] and armor.web_reaction
    assert armor.phase == Phase.NIGHT
    return (("Sacrifício: mão e campo", sacrifice), ("Luna: escolhas encadeadas", dream),
            ("Armadura: reação e passagem de jogador", armor))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="jessica-web-ui-") as directory:
        server.SAVES = Path(directory)
        for index, (name, state) in enumerate(scenarios(), 1):
            saves.write(server.SAVES / f"{index:012x}.json", {
                "version": SAVE_VERSION, "state": state_to_dict(state), "events": [],
                "history": [], "name": name, "kind": "manual",
            })
        print(f"QA isolado: http://127.0.0.1:{args.port} — saves temporários.", flush=True)
        with server.ThreadingHTTPServer(("127.0.0.1", args.port), server.Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
