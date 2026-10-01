"""Regressão: quatro itens de Rogue liberam a seleção e o ataque a Bases."""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.main import find_targets
from jessica.core import peoples, combat
from jessica.core.setup import run_setup
from jessica.core.models import Hero
from jessica.core.constants import Phase


def fixture(items):
    group = [("demonios", "rogue_devil"), ("humanos", "miyamoto"),
             ("orcs", "arken"), ("fadas", "luna")]
    state, _ = run_setup(all_peoples=[p for p, h in group],
        heroes_by_people={p: [h] for p, h in group},
        choices={pid: {"povo": p, "heroi": h} for pid, (p, h) in enumerate(group, 1)}, seed=909)
    state.phase = Phase.NIGHT
    rogue = Hero(id="rogue", owner_id=1, house="city_2", life=5, life_max=5,
                 hero_id="rogue_devil", statuses={"rogue_items": list(items)})
    state.players[0].units = [rogue]
    return state, rogue


def test_four_items_city_attack_is_selectable_and_resolves():
    state, rogue = fixture(peoples.ROGUE_ITEMS)
    assert any(t[:2] == ("city", "2") for t in find_targets(state, rogue))
    before = state.players[1].city.life
    combat.resolve_attack(state, combat.Attack(rogue.id, "city", "2"))
    assert state.players[1].city.life == before - 1


def test_incomplete_items_do_not_offer_city():
    for missing in peoples.ROGUE_ITEMS:
        state, rogue = fixture([i for i in peoples.ROGUE_ITEMS if i != missing])
        assert not any(t[0] == "city" for t in find_targets(state, rogue))


if __name__ == "__main__":
    passed = failed = 0
    for test in (test_four_items_city_attack_is_selectable_and_resolves,
                 test_incomplete_items_do_not_offer_city):
        try:
            test()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"FALHOU - {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"{passed} passaram, {failed} falharam")
    raise SystemExit(1 if failed else 0)
