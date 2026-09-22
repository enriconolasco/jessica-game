"""Testes: habilidades individuais dos 7 Anoes."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop, tintin_ficar_invisivel, ActionError
from jessica.core.combat import resolve_attack, Attack, CombatError
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["seven_dwarves"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "Os 7 Anões"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def _make_troop(state, pid, archetype=TroopArchetype.LIGHT, life=4, house="center"):
    p = state.players[pid - 1]
    p.city.gold = max(p.city.gold, life + 5)
    p.city.magic = max(p.city.magic, 5)
    t = summon_troop(state, pid, archetype, life)
    t.house = house
    return t


def test_dain_marks_attacker_and_kills_at_end_of_night():
    """Dain: atacante morre no fim da noite."""
    from jessica.core.artifacts_effects import on_end_turn
    state = make_state()
    state.phase = Phase.NIGHT
    p2 = state.players[1]
    p2.city.magic = 10
    summon_hero(state, 2)
    dain = summon_hero(state, 2)
    dain.house = CENTER
    enemy = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    resolve_attack(state, Attack(enemy.id, "unit", dain.id))
    # Dain morre (1 de vida)
    assert not dain.is_alive() or dain.life <= 0
    # Marcou o inimigo pra morrer
    assert len(state.dain_kills) == 1, f"Esperado 1 dain_kill, veio {len(state.dain_kills)}"
    on_end_turn(state)
    # Inimigo morto
    assert not enemy.is_alive(), f"Inimigo deveria ter morrido por Dain"
    print("OK  - Dain: atacante morre no fim da noite")


def test_buin_is_invulnerable_against_hero():
    """Dengoso recebe o ataque, mas não perde vida contra Heróis."""
    state = make_state()
    state.phase = Phase.NIGHT
    p2 = state.players[1]
    p2.city.magic = 20
    summon_hero(state, 2)
    buin = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "buin")
    buin.house = CENTER
    enemy_hero = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    # Faz um herói inimigo atacar buin
    p1 = state.players[0]
    p1.city.magic = 10
    hero_enemy = summon_hero(state, 1)
    hero_enemy.house = CENTER
    before = buin.life
    resolve_attack(state, Attack(hero_enemy.id, "unit", buin.id))
    assert buin.life == before
    print("OK  - Dengoso e invulneravel contra Heroi")


def test_bein_impales_killed_target():
    """Soneca empala temporariamente inimigo morto por ele."""
    state = make_state()
    state.phase = Phase.NIGHT
    p2 = state.players[1]
    p2.city.magic = 20
    for _ in range(3):
        summon_hero(state, 2)
    bein = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "bein")
    bein.house = CENTER
    target = _make_troop(state, 1, life=1, house=CENTER)
    resolve_attack(state, Attack(bein.id, "unit", target.id))
    assert state.players[0].dwarf_empalados
    print("OK  - Soneca empala o inimigo morto")


def test_bein_impale_clears_when_dwarves_are_curuna():
    state = make_state()
    state.phase = Phase.NIGHT
    p2 = state.players[1]
    p2.city.magic = 20
    for _ in range(3):
        summon_hero(state, 2)
    bein = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "bein")
    bein.house = CENTER
    target = _make_troop(state, 1, life=1, house=CENTER)
    resolve_attack(state, Attack(bein.id, "unit", target.id))
    from jessica.core.peoples import clear_dwarf_impales_for_curuna
    state.curuna_id = 2
    clear_dwarf_impales_for_curuna(state)
    assert state.players[0].dwarf_empalados == []
    print("OK  - Empalamento de Soneca expira com Anoes Curuna")


def test_tintin_invisibility():
    """Tin Tin fica invisível; não pode ser atacado; ao atacar, revela."""
    state = make_state()
    p2 = state.players[1]
    p2.city.magic = 20
    for _ in range(5):
        summon_hero(state, 2)
    tintin = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "tintin")
    tintin_ficar_invisivel(state, 2)
    assert tintin.statuses.get("invisivel_until_turn") == state.turn
    # Inimigo tenta atacar: bloqueado
    state.phase = Phase.NIGHT
    tintin.house = CENTER
    enemy = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    try:
        resolve_attack(state, Attack(enemy.id, "unit", tintin.id))
        raise AssertionError("Deveria bloquear ataque em invisivel")
    except CombatError as e:
        print(f"OK  - Tin Tin invisivel nao pode ser atacado: {e}")


def test_tintin_cooldown():
    """Tin Tin tem recarga de 1 turno."""
    state = make_state()
    p2 = state.players[1]
    p2.city.magic = 20
    for _ in range(5):
        summon_hero(state, 2)
    tintin_ficar_invisivel(state, 2)
    try:
        tintin_ficar_invisivel(state, 2)
        raise AssertionError("Deveria bloquear por recarga")
    except ActionError as e:
        print(f"OK  - Tin Tin em recarga: {e}")


def run_all():
    tests = [
        test_dain_marks_attacker_and_kills_at_end_of_night,
        test_buin_is_invulnerable_against_hero,
        test_bein_impales_killed_target,
        test_bein_impale_clears_when_dwarves_are_curuna,
        test_tintin_invisibility,
        test_tintin_cooldown,
    ]
    print("=== Testes 7 Anoes habilidades ===\n")
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
