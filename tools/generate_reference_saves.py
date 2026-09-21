#!/usr/bin/env python3
"""Gera os saves determinísticos usados como referências da baseline P0."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jessica.core.actions import cast_spell, summon_hero, summon_troop
from jessica.core.constants import CENTER, Phase, TroopArchetype
from jessica.core.serialize import load_from_file, save_to_file
from jessica.core.setup import run_setup
from jessica.core.state import snapshot_turn_start_priority

SEEDS = {
    "regression_suite": 20260916,
    "systems_v5v11": 20260921,
    "reference_saves": 51100,
}


def new_state(peoples: list[str], hero_ids: list[str], seed: int):
    state, _ = run_setup(
        all_peoples=peoples,
        heroes_by_people={p: [h] for p, h in zip(peoples, hero_ids)},
        choices={i + 1: {"povo": p, "heroi": hero_ids[i]}
                 for i, p in enumerate(peoples)},
        seed=seed,
    )
    for player in state.players:
        player.city.gold = 30
        player.city.magic = 30
    return state


def ready(unit, house: str) -> None:
    unit.house = house
    unit.statuses.pop("summoned_turn", None)
    unit.moves_this_turn = 0
    unit.has_moved_this_turn = False


def intermediate():
    state = new_state(
        ["fadas", "lobisomens", "humanos", "vampiros"],
        ["luna", "lupa_lider", "miyamoto", "luide_vampa"],
        SEEDS["reference_saves"],
    )
    state.turn = 6
    state.curuna_id = 2
    state.phase = Phase.DAY
    for pid in range(1, 5):
        hero = summon_hero(state, pid)
        troop = summon_troop(state, pid, TroopArchetype.LIGHT, 4)
        ready(hero, CENTER if pid in (1, 3) else f"city_{pid}")
        ready(troop, CENTER if pid in (2, 4) else f"city_{pid}")
    snapshot_turn_start_priority(state)
    return state


def combat_spell():
    state = new_state(
        ["lobisomens", "anoes", "humanos", "fadas"],
        ["lupa_lider", "ori", "miyamoto", "luna"],
        SEEDS["systems_v5v11"],
    )
    state.turn = 7
    state.curuna_id = 2  # Lua Cheia do jogador 1.
    state.phase = Phase.NIGHT
    for pid in range(1, 5):
        ready(summon_hero(state, pid), CENTER)
        ready(summon_troop(state, pid, TroopArchetype.LIGHT, 4), CENTER)
    wolf_troop = next(u for u in state.players[0].units
                      if getattr(u, "archetype", None) is not None)
    cast_spell(state, 1, {"unit_id": wolf_troop.id})
    snapshot_turn_start_priority(state)
    return state


def near_end():
    state = new_state(
        ["humanos", "orcs", "gigantes", "gnomos_duendes"],
        ["miyamoto", "vovo_gamba", "pe_descalco", "zebum"],
        SEEDS["regression_suite"],
    )
    state.turn = 12
    state.curuna_id = 4
    state.phase = Phase.NIGHT
    state.players[0].city.life = 2
    state.players[1].city.life = 0
    state.players[2].city.life = 0
    state.players[3].city.life = 1
    ready(summon_hero(state, 1), CENTER)
    ready(summon_troop(state, 1, TroopArchetype.HEAVY, 8), "city_4")
    ready(summon_hero(state, 4), "city_4")
    snapshot_turn_start_priority(state)
    return state


def main() -> None:
    seeds_dir = ROOT / "seeds"
    saves_dir = ROOT / "saves" / "reference"
    seeds_dir.mkdir(parents=True, exist_ok=True)
    saves_dir.mkdir(parents=True, exist_ok=True)
    (seeds_dir / "reference_seeds.json").write_text(
        json.dumps(SEEDS, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    scenarios = {
        "turno_06_intermediario.json": intermediate(),
        "combate_lua_cheia_feitico.json": combat_spell(),
        "turno_12_proximo_fim.json": near_end(),
    }
    for filename, state in scenarios.items():
        path = saves_dir / filename
        save_to_file(state, str(path))
        loaded = load_from_file(str(path))
        assert loaded.turn == state.turn
        assert loaded.curuna_id == state.curuna_id
        assert len(loaded.players) == 4
    print(f"Gerados {len(scenarios)} saves e {len(SEEDS)} seeds em {ROOT}")


if __name__ == "__main__":
    main()
