"""Janela de Luide em locais sem alvos, exercitando a UI real do terminal."""
import os
import sys
from contextlib import ExitStack
from unittest.mock import Mock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_vampiros import make_state
from jessica import main as terminal
from jessica.core.combat import Attack
from jessica.core.constants import Phase
from jessica.core.models import Hero, Troop
from jessica.core.serialize import state_to_dict


def scenario():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.chosen_hero_id, p.city.magic = "luide_vampa", 20
    p.units = [Hero(id="luide", owner_id=1, house="center", life=1,
                    life_max=1, hero_id="luide_vampa")]
    return state


def ui(picker, attack=None):
    stack = ExitStack()
    stack.enter_context(patch.object(terminal, "console", Mock()))
    for name in ("_night_info_prompt", "_mostrar_resumo_local", "_resolver_qd_pendente"):
        stack.enter_context(patch.object(terminal, name, lambda *a, **kw: None))
    stack.enter_context(patch.object(terminal, "pick_index", picker))
    stack.enter_context(patch.object(terminal, "prompt_attack", attack or Mock(return_value=None)))
    return stack


def test_luide_alone_in_center_can_pass_without_attack():
    state = scenario()
    seen = []
    attack = Mock(return_value=None)
    before = state_to_dict(state)
    with ui(lambda title, options: seen.append(title) or len(options) - 1, attack):
        terminal._declarar_casa(state, "center", [1])
    assert len(seen) == 1 and "Luide Vampa" in seen[0]
    attack.assert_not_called()
    assert state_to_dict(state) == before


def test_vampire_troop_alone_gets_window_with_luide_elsewhere():
    state = scenario()
    state.players[0].units.append(Troop(id="alone", owner_id=1, house="city_1", life=4, life_max=4))
    seen = []
    with ui(lambda title, options: seen.append(title) or len(options) - 1):
        terminal._declarar_casa(state, "city_1", [1])
    assert len(seen) == 1 and "Luide Vampa" in seen[0]


def test_dead_luide_does_not_open_empty_location():
    state = scenario()
    state.players[0].units[0].life = 0
    state.players[0].units.append(Troop(id="alone", owner_id=1, house="city_1", life=4, life_max=4))
    picker = Mock()
    with ui(picker):
        terminal._declarar_casa(state, "city_1", [1])
    picker.assert_not_called()


def test_luide_dying_after_moving_closes_window_immediately():
    state = scenario()
    luide = state.players[0].units[0]
    luide.house = "city_1"
    state.players[0].units.append(Troop(id="alone", owner_id=1, house="city_1", life=4, life_max=4))
    state.players[1].units = [Troop(id="enemy", owner_id=2, house="center", life=8, life_max=8)]
    seen = []

    def picker(title, options):
        if "Luide Vampa" in title:
            seen.append(title)
            return options.index("Mover unidade") if len(seen) == 1 else len(options) - 1
        return 0

    def attack(current, unit, targets):
        return Attack("luide", "unit", "enemy") if unit.id == "luide" else None

    with ui(picker, attack):
        terminal._declarar_casa(state, "city_1", [1], {"center"})
    assert not luide.is_alive()
    assert len(seen) == 1


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

