"""Testes: Vampiros."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop, summon_hero as sh, ActionError
from jessica.core.combat import resolve_attack, Attack
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero


def make_state():
    state, _ = run_setup(
        all_peoples=["vampiros", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "vampiros": ["dracula", "dandara", "luide_vampa"],
            "humanos": ["miyamoto"], "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "vampiros", "heroi": "dracula"},
            2: {"povo": "humanos", "heroi": "miyamoto"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def _troop(state, pid, arche, life=4, house="center"):
    p = state.players[pid-1]
    p.city.gold = 20
    p.city.magic = 10
    t = summon_troop(state, pid, arche, life)
    t.house = house
    return t


def test_vampiro_cura_ao_matar():
    state = make_state()
    state.phase = Phase.NIGHT
    vamp = _troop(state, 1, TroopArchetype.HEAVY, 8, "center")
    vamp.life = 4
    victim = _troop(state, 2, TroopArchetype.LIGHT, 4, "center")
    resolve_attack(state, Attack(vamp.id, "unit", victim.id))
    assert not victim.is_alive()
    assert vamp.life == 2, f"Vampiro deveria ter 2, veio {vamp.life}"
    print("OK  - Vampiro cura 2 ao matar")


def test_vampiro_empata_sobrevive_2():
    state = make_state()
    state.phase = Phase.NIGHT
    vamp = _troop(state, 1, TroopArchetype.LIGHT, 4, "center")
    victim = _troop(state, 2, TroopArchetype.LIGHT, 4, "center")
    resolve_attack(state, Attack(vamp.id, "unit", victim.id))
    assert not victim.is_alive()
    assert vamp.life == 2, f"Empate+mata: vampiro devia estar com 2, veio {vamp.life}"
    print("OK  - Vampiro empata e sobrevive com 2")


def test_vampiro_nao_cura_contra_cidade():
    state = make_state()
    state.phase = Phase.NIGHT
    vamp = _troop(state, 1, TroopArchetype.HEAVY, 8, "city_2")
    vamp.life = 4
    vida_antes = vamp.life
    resolve_attack(state, Attack(vamp.id, "city", "2"))
    assert vamp.life == vida_antes - 1, f"Vampiro nao deve curar vs Cidade. veio {vamp.life}"
    print("OK  - Vampiro nao cura contra Cidade")


def test_dracula_empala():
    """Empalados vao para o DONO da unidade morta, nao para Dracula."""
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p2 = state.players[1]
    p1.city.magic = 10
    dracula = summon_hero(state, 1)
    dracula.house = CENTER
    dracula.life = 20
    dracula.life_max = 20
    victim = _troop(state, 2, TroopArchetype.LIGHT, 4, "center")
    resolve_attack(state, Attack(dracula.id, "unit", victim.id))
    assert not victim.is_alive()
    assert {"kind": "troop", "id": "light"} in p2.empalados, (
        f"Empalado deveria estar no P2, empalados P2={p2.empalados}"
    )
    print("OK  - Dracula empalou tropa light (bloqueio no dono P2)")


def test_dracula_empala_bloqueia_reinvocacao():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    p1.city.gold = 10
    dracula = summon_hero(state, 1)
    dracula.house = CENTER
    dracula.life = 20
    dracula.life_max = 20
    victim = _troop(state, 2, TroopArchetype.LIGHT, 4, "center")
    resolve_attack(state, Attack(dracula.id, "unit", victim.id))
    # P2 tenta reinvocar light -> bloqueado
    p2 = state.players[1]
    p2.city.gold = 20
    try:
        summon_troop(state, 2, TroopArchetype.LIGHT, 4)
        raise AssertionError("Deveria estar empalado")
    except ActionError as e:
        print(f"OK  - Tropa empalada nao pode reinvocar: {e}")


def test_dandara_invisibilidade():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 10
    p1.city.gold = 20
    p1.chosen_hero_id = "dandara"
    dandara = summon_hero(state, 1)
    t1 = summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    from jessica.core.actions import dandara_invisibilidade
    dandara_invisibilidade(state, 1)
    assert dandara.statuses.get("invisivel_until_turn") == state.turn
    assert t1.statuses.get("invisivel_until_turn") == state.turn
    print("OK  - Dandara tornou grupo invisivel")


def run_all():
    tests = [
        test_vampiro_cura_ao_matar,
        test_vampiro_empata_sobrevive_2,
        test_vampiro_nao_cura_contra_cidade,
        test_dracula_empala,
        test_dracula_empala_bloqueia_reinvocacao,
        test_dandara_invisibilidade,
    ]
    print("=== Testes Vampiros ===\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
