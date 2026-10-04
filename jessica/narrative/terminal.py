import json
import os
from pathlib import Path
import tempfile

from rich.text import Text

from ..core.headless import view_for_player
from ..core.serialize import state_to_dict, state_from_dict
from .engine import lifecycle_event, observe


def narrate(console, state, trigger, mode, player_id=None, next_player_id=None):
    if mode != "breve":
        return
    view = view_for_player(state, state.players[0].id)
    event = lifecycle_event(trigger, view, player_id, next_player_id)
    session, text = observe(state.seed, state.narrative, event, view, mode)
    state.narrative = session
    if text:
        console.print(Text(text, style="dim italic"), highlight=False)


def write_checkpoint(state, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "kind": "terminal-turn-boundary", "state": state_to_dict(state)}
    fd, temporary = tempfile.mkstemp(prefix=".jessica-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_checkpoint(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if (not isinstance(payload, dict) or payload.get("version") != 1
            or payload.get("kind") != "terminal-turn-boundary"):
        raise ValueError("Use um checkpoint entre turnos gerado pelo terminal atual, não um save intermediário web.")
    try:
        state = state_from_dict(payload["state"])
        if not 2 <= len(state.players) <= 5 or type(state.turn) is not int or state.turn < 1:
            raise ValueError("Checkpoint inválido")
        return state
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Checkpoint inválido") from error
