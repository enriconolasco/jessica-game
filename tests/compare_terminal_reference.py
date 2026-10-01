"""Replay contra uma instalação terminal independente, sem escrever nela."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def worker(reference):
    sys.path.insert(0, str(reference))
    from jessica.core import actions, combat, peoples
    from jessica.core.constants import TroopArchetype
    from jessica.core.serialize import state_from_dict, state_to_dict
    results = []
    for record in json.load(sys.stdin):
        state = state_from_dict(record["state"])
        args = record["args"]
        if record["module"] == "terminal":
            from contextlib import ExitStack
            from unittest.mock import Mock, patch
            from jessica import main as terminal
            plan = args["plan"]

            def prompt(current, unit, targets):
                wanted = plan.get(unit.id, [])
                if wanted and any(t[:2] == tuple(wanted[0]) for t in targets):
                    kind, target = wanted.pop(0)
                    return combat.Attack(unit.id, kind, target)
                return None

            with ExitStack() as patches:
                if "armor_gold" in args:
                    patches.enter_context(patch.object(combat, "_armor_choice_fn",
                                                       lambda player, damage: args["armor_gold"]))
                patches.enter_context(patch.object(terminal, "console", Mock()))
                patches.enter_context(patch.object(terminal.Prompt, "ask",
                    lambda prompt, **kwargs: kwargs.get("default", "")))
                for name in ("show_hud", "show_map", "_ask_vovo_position", "_try_luna_return",
                             "_ainai_prompt_all", "_try_besouro_mandinga", "_night_info_prompt",
                             "_mostrar_resumo_local", "_luide_janela_noturna"):
                    patches.enter_context(patch.object(terminal, name, lambda *a, **kw: None))
                patches.enter_context(patch.object(terminal, "prompt_attack", prompt))
                terminal.run_night_phase(state)
            results.append(state_to_dict(state))
            continue
        if "archetype" in args:
            args["archetype"] = TroopArchetype(args["archetype"])
        function = getattr({"actions": actions, "combat": combat, "peoples": peoples}[
            record["module"]], record["function"])
        function(state, record["player_id"], **args)
        results.append(state_to_dict(state))
    json.dump(results, sys.stdout, ensure_ascii=True)


def normalize(state):
    return {k: v for k, v in state.items()
            if k not in ("active_player_id", "web_night", "web_reaction")}


def run(reference):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from copy import deepcopy
    from jessica.core import interaction_actions, peoples
    from jessica.core.headless import apply_action, legal_actions
    from jessica.core.models import Hero
    from jessica.core.serialize import state_to_dict
    from test_interaction_actions import ready
    from test_web_mechanics_combinations import ability_scenarios, mixed_night_case
    from test_night_terminal_parity import compare, troop, belial_night
    from test_night_web import night

    records, expected = [], []

    def add(state, action, function, args):
        web = deepcopy(state)
        result = apply_action(web, action)
        assert result["success"], result
        records.append({"state": state_to_dict(state), "player_id": action["player_id"],
                        "module": "actions", "function": function, "args": deepcopy(args),
                        "label": action.get("description", action["type"])})
        expected.append(state_to_dict(web))

    for ability, state in ability_scenarios():
        for action in legal_actions(state, 1):
            if action["type"] == "hero_ability" and action["params"]["ability"] == ability:
                add(state, action, interaction_actions.ABILITIES[ability][0].__name__, action["params"]["args"])
    state = ready()
    for action in legal_actions(state, 1):
        if action["type"] == "play_artifact":
            add(state, action, "play_artifact", action["params"])
    spells = [("humanos", "miyamoto"), ("anoes", "ori"), ("orcs", "arken"),
              ("fadas", "luna"), ("vampiros", "luide_vampa"), ("lobisomens", "cigana"),
              ("gigantes", "caroco"), ("mortos_vivos", "zoia"),
              ("filhos_floresta", "guarari"), ("dragoes", "purpura"),
              ("demonios", "belial"), ("gnomos_duendes", "sao_tome")]
    for people, hero in spells:
        state = ready()
        player = state.players[0]
        player.people, player.chosen_hero_id = people, hero
        player.bets_need_realocacao = False
        if people == "gnomos_duendes":
            player.spell_copia_id = "sonho_lucido"
        player.units.append(Hero(id="caster", owner_id=1, house="center", life=6,
                                 life_max=6, hero_id=hero))
        choices = [a for a in legal_actions(state, 1) if a["type"] in ("cast_spell", "sacrifice_spell")]
        assert choices, people
        for action in choices:
            args = {"choice": action["params"]["choice"]} if action["type"] == "cast_spell" else {
                "choice": action["params"]}
            add(state, action, "cast_spell", args)

    day_count = len(records)
    groups = [[("humanos", "miyamoto"), ("anoes", "seven_dwarves"),
               ("orcs", "vovo_gamba"), ("fadas", "luna")],
              [("vampiros", "dracula"), ("lobisomens", "cigana"),
               ("gigantes", "caroco"), ("mortos_vivos", "cova_rasa")],
              [("gnomos_duendes", "sao_tome"), ("dragoes", "purpura"),
               ("demonios", "tuza"), ("filhos_floresta", "guarari")]]
    for group in groups:
        for turn in (1, 4):
            state, plan = mixed_night_case(group, turn)
            records.append({"state": state_to_dict(state), "module": "terminal", "args": {"plan": plan},
                            "label": f"Noite T{turn}: {','.join(p for p, _ in group)}"})
            web, _ = compare(state, plan)
            expected.append(state_to_dict(web))

    state = night()
    troop(state, 1, "attacker")
    troop(state, 2, "defender")
    state.players[1].armor_active_until_turn = state.turn
    state.players[1].city.gold = 8
    plan = {"attacker": [("unit", "defender")]}
    records.append({"state": state_to_dict(state), "module": "terminal", "args": {"plan": plan, "armor_gold": 0},
                    "label": "Noite com Armadura, pagamento zero"})
    web, _ = compare(state, plan)
    expected.append(state_to_dict(web))

    for attacker_life, defender_life in ((8, 1), (1, 6)):
        state, plan = belial_night(attacker_life, defender_life)
        records.append({"state": state_to_dict(state), "module": "terminal", "args": {"plan": plan},
                        "label": f"Belial: oferta diferida, vidas {attacker_life}/{defender_life}"})
        web, _ = compare(state, plan)
        expected.append(state_to_dict(web))

    from test_rogue_four_items import fixture
    state, _ = fixture(peoples.ROGUE_ITEMS)
    plan = {"rogue": [("city", "2")]}
    records.append({"state": state_to_dict(state), "module": "terminal", "args": {"plan": plan},
                    "label": "Rogue: quatro itens liberam ataque à Base"})
    web, _ = compare(state, plan)
    expected.append(state_to_dict(web))

    completed = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
                                "--reference", str(reference), "--worker"],
                               input=json.dumps(records), capture_output=True, text=True,
                               encoding="utf-8", timeout=60, cwd=str(reference))
    if completed.returncode:
        raise RuntimeError(completed.stderr)
    actual = json.loads(completed.stdout)
    assert len(actual) == len(expected)
    for record, terminal, web in zip(records, actual, expected):
        terminal, web = normalize(terminal), normalize(web)
        if terminal != web:
            fields = [k for k in terminal.keys() | web.keys() if terminal.get(k) != web.get(k)]
            raise AssertionError(f"{record['label']}: divergência em {fields}")
    print(f"{day_count} ações diurnas e {len(records) - day_count} noites mistas iguais "
          "à instalação terminal independente; estado, logs e RNG.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args()
    if not (options.reference / "jessica/core/actions.py").is_file():
        parser.error("A referência deve conter jessica/core/actions.py.")
    if options.reference.resolve() == Path(__file__).resolve().parents[1]:
        parser.error("A referência precisa ser outra instalação, não o próprio cliente web.")
    if options.worker:
        worker(options.reference.resolve())
    else:
        run(options.reference.resolve())
