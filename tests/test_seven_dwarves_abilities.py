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


def test_buin_cannot_be_attacked_by_hero():
    """Buin: não pode ser atacado por Heróis."""
    state = make_state()
    state.phase = Phase.NIGHT
    p2 = state.players[1]
    p2.city.magic = 20
    # Invoca dain + buin
    summon_hero(state, 2)
    summon_hero(state, 2)
    buin = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "buin")
    buin.house = CENTER
    enemy_hero = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    # Faz um herói inimigo atacar buin
    p1 = state.players[0]
    p1.city.magic = 10
    hero_enemy = summon_hero(state, 1)
    hero_enemy.house = CENTER
    try:
        resolve_attack(state, Attack(hero_enemy.id, "unit", buin.id))
        raise AssertionError("Herói deveria ser bloqueado contra Buin")
    except CombatError as e:
        print(f"OK  - Buin nao pode ser atacado por Heroi: {e}")


def test_bein_puts_target_to_sleep():
    """Bein dorme alvo até os Anões serem Curuna."""
    state = make_state()
    state.phase = Phase.NIGHT
    p2 = state.players[1]
    p2.city.magic = 20
    for _ in range(3):
        summon_hero(state, 2)
    bein = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "bein")
    bein.house = CENTER
    target = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    resolve_attack(state, Attack(bein.id, "unit", target.id))
    sono = target.statuses.get("sono_until_turn", -1)
    assert sono > state.turn, f"Alvo deveria dormir, sono_until={sono}"
    print(f"OK  - Bein dorme alvo ate turno {sono}")


def test_bein_target_wakes_if_attacked():
    """Alvo dormindo acorda se for atacado."""
    state = make_state()
    state.phase = Phase.NIGHT
    p2 = state.players[1]
    p2.city.magic = 20
    for _ in range(3):
        summon_hero(state, 2)
    bein = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "bein")
    bein.house = CENTER
    target = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    resolve_attack(state, Attack(bein.id, "unit", target.id))
    assert target.statuses.get("sono_until_turn", -1) > state.turn
    # Dain ataca o alvo dormindo (usa outro anao)
    dain = next(u for u in p2.units if isinstance(u, Hero) and u.hero_id == "dain")
    dain.house = CENTER
    # Reset dain attack counter
    dain.attacks_made_this_night = 0
    resolve_attack(state, Attack(dain.id, "unit", target.id))
    # Alvo acordou (sono removido)
    assert "sono_until_turn" not in target.statuses or         target.statuses.get("sono_until_turn", -1) <= state.turn,         f"Alvo deveria ter acordado, sono={target.statuses.get('sono_until_turn')}"
    print("OK  - Bein: alvo acorda se for atacado")


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
        test_buin_cannot_be_attacked_by_hero,
        test_bein_puts_target_to_sleep,
        test_bein_target_wakes_if_attacked,
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
