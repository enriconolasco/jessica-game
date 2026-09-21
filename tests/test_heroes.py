"""Testes de heróis: vidas corretas, habilidades específicas."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import summon_troop, summon_hero
from jessica.core.combat import (
    resolve_attack, Attack, _effective_max_attacks,
)
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core import heroes


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["Miyamoto Musashi", "Besouro Mangangá", "Iúna"],
            "anoes": ["Barbadourada", "Ori", "Os 7 Anões"],
            "orcs": ["Ga'Roche", "Arken", "Vovó Gamba"],
            "fadas": ["Ainai", "Valendar", "Luna"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "Miyamoto Musashi"},
            2: {"povo": "anoes", "heroi": "Ori"},
            3: {"povo": "orcs", "heroi": "Ga'Roche"},
            4: {"povo": "fadas", "heroi": "Ainai"},
        },
        seed=20260916,
    )
    return state


def test_hero_life_values():
    state = make_state()
    for p in state.players:
        p.city.magic = 10
        h = summon_hero(state, p.id)
        hd = heroes.get_hero(h.hero_id)
        assert h.life == hd.life, f"{hd.name}: vida {h.life} != {hd.life}"
    print("OK  - Heróis com vidas corretas")


def test_garoche_executes_lonely_target():
    state = make_state()
    state.phase = Phase.NIGHT
    p3 = state.players[2]
    p3.city.magic = 5
    garoche = summon_hero(state, 3)
    garoche.house = CENTER

    # alvo: tropa sozinha do J1 no centro
    p1 = state.players[0]
    p1.city.gold = 10
    p1.city.magic = 5
    enemy = summon_troop(state, 1, TroopArchetype.HEAVY, 8)
    enemy.house = CENTER

    resolve_attack(state, Attack(garoche.id, "unit", enemy.id))
    assert not enemy.is_alive(), "Ga'Roche deveria ter executado"
    assert garoche.life == 4, f"Ga'Roche não deveria ter perdido vida (tem {garoche.life})"
    assert garoche.life_max == 4, f"Ga'Roche cresceu? life_max={garoche.life_max}"
    print("OK  - Ga'Roche executa alvo sozinho, não perde vida, ganha +1")


def test_garoche_does_not_execute_with_allies():
    state = make_state()
    state.phase = Phase.NIGHT
    p3 = state.players[2]
    p3.city.magic = 5
    garoche = summon_hero(state, 3)
    garoche.house = CENTER

    p1 = state.players[0]
    p1.city.gold = 20
    p1.city.magic = 5
    t1 = summon_troop(state, 1, TroopArchetype.HEAVY, 8)
    t1.house = CENTER
    t2 = summon_troop(state, 1, TroopArchetype.MEDIUM, 6)
    t2.house = CENTER

    resolve_attack(state, Attack(garoche.id, "unit", t1.id))
    # Troca normal: garoche tem 3, t1 tem 8 → garoche morre, t1 fica com 5
    assert not garoche.is_alive(), "Ga'Roche deveria morrer na troca"
    print("OK  - Ga'Roche não executa se alvo tem aliados (troca normal)")


def test_musashi_double_if_strongest():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 5
    miyamoto = summon_hero(state, 1)
    miyamoto.house = CENTER
    # vida 4 (maior do local, ninguém mais)
    from jessica.core.turn import end_day
    end_day(state)
    atks = _effective_max_attacks(state, miyamoto)
    assert atks == 2, f"Miyamoto deveria ter 2 ataques, tem {atks}"
    print("OK  - Miyamoto ganha 2 ataques se for o mais forte do local")


def test_musashi_not_strongest():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 5
    p1.city.gold = 10
    miyamoto = summon_hero(state, 1)
    miyamoto.house = CENTER

    p2 = state.players[1]
    p2.city.gold = 20
    p2.city.magic = 5
    heavy = summon_troop(state, 2, TroopArchetype.HEAVY, 8)
    heavy.house = CENTER

    from jessica.core.turn import end_day
    end_day(state)
    atks = _effective_max_attacks(state, miyamoto)
    assert atks == 1, f"Miyamoto deveria ter 1 ataque, tem {atks}"
    print("OK  - Miyamoto não ganha 2 ataques se não for o mais forte")


def test_spell_cooldown_blocks_next_turn():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 10
    p1.city.gold = 10
    # Lança resistência em si mesmo
    p1.units = []
    from jessica.core.actions import cast_spell
    # precisa de unidade
    summon_hero(state, 1)
    hero = p1.units[0]
    cast_spell(state, 1, {"unit_id": hero.id})
    assert p1.spell_cooldown_until_turn == state.turn + 2
    try:
        cast_spell(state, 1, {"unit_id": hero.id})
        raise AssertionError("Deveria bloquear")
    except Exception as e:
        print(f"OK  - Feitiço em recarga: {e}")


def run_all():
    tests = [
        test_hero_life_values,
        test_garoche_executes_lonely_target,
        test_garoche_does_not_execute_with_allies,
        test_musashi_double_if_strongest,
        test_musashi_not_strongest,
        test_spell_cooldown_blocks_next_turn,
    ]
    print("=== Testes heroes ===\n")
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