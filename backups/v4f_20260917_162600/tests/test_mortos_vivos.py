"""Testes: Mortos-Vivos."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop, cast_spell
from jessica.core.combat import resolve_attack, Attack
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["mortos_vivos", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "mortos_vivos": [], "humanos": ["miyamoto"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "mortos_vivos", "heroi": ""},
            2: {"povo": "humanos", "heroi": "miyamoto"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_mv_heroi_custa_2_magia():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    summon_hero(state, 1, force_hero_id="cobra")
    assert p.city.magic == 8, f"Esperado 8, veio {p.city.magic}"
    print("OK  - Heroi MV custa 2 Magia")


def test_mv_pode_invocar_tres_diferentes():
    state = make_state()
    p = state.players[0]
    p.city.magic = 30
    summon_hero(state, 1, force_hero_id="cobra")
    summon_hero(state, 1, force_hero_id="zoia")
    summon_hero(state, 1, force_hero_id="cova_rasa")
    assert len([u for u in p.units if isinstance(u, Hero)]) == 3
    print("OK  - MV pode ter 3 herois vivos simultaneamente")


def test_levantar_mortos_invoca_2():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    cast_spell(state, 1, choice={"archetypes": ["light", "medium"]})
    troops = [u for u in p.units if hasattr(u, "archetype")]
    assert len(troops) == 2
    assert all(t.life == 1 for t in troops)
    print("OK  - Levantar os Mortos invocou 2 tropas com 1 vida")


def test_zoia_da_ghoul_e_esqueleto():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    arqs_antes = peoples.available_archetypes(p)
    assert TroopArchetype.GHOUL not in arqs_antes
    summon_hero(state, 1, force_hero_id="zoia")
    arqs_depois = peoples.available_archetypes(p)
    assert TroopArchetype.GHOUL in arqs_depois
    assert TroopArchetype.ESQUELETO in arqs_depois
    print("OK  - Zoia liberou Ghoul e Esqueleto")


def test_cova_rasa_amaldicoa():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    cova = summon_hero(state, 1, force_hero_id="cova_rasa")
    cova.house = CENTER
    # Traz tropa inimiga para o centro
    p2 = state.players[1]
    p2.city.gold = 20
    t2 = summon_troop(state, 2, TroopArchetype.LIGHT, 4)
    t2.house = CENTER
    peoples.apply_cova_rasa(state)
    assert t2.statuses.get("amaldicoado_until_turn") == state.turn
    print("OK  - Cova Rasa amaldicoou inimigo proximo")


def test_amaldicoado_dobra_dano():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.gold = 20
    attacker = summon_troop(state, 1, TroopArchetype.HEAVY, 8)
    attacker.house = CENTER
    p2 = state.players[1]
    p2.city.gold = 20
    target = summon_troop(state, 2, TroopArchetype.HEAVY, 8)
    target.house = CENTER
    target.statuses["amaldicoado_until_turn"] = state.turn
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    # Attacker 8 x2 (amaldicoado) = 16 -> target morre; target (8) retalia 8 -> attacker morre
    assert not target.is_alive()
    print("OK  - Amaldicoado tomou dano dobrado")


def run_all():
    tests = [
        test_mv_heroi_custa_2_magia,
        test_mv_pode_invocar_tres_diferentes,
        test_levantar_mortos_invoca_2,
        test_zoia_da_ghoul_e_esqueleto,
        test_cova_rasa_amaldicoa,
        test_amaldicoado_dobra_dano,
    ]
    print("=== Testes Mortos-Vivos ===\n")
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
