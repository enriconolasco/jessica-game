"""apply_fix5: corrige sintaxe f3d/boin + reescreve f3a/f3b/f3e."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.resolve()
BACKUP_DIR = ROOT / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# tests/test_artifact_effects_f3a.py — Q♥ e Q♠
# =============================================================
FILES["tests/test_artifact_effects_f3a.py"] = '''\
"""Testes F3a: Q-heart e Q-spades."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import play_artifact, summon_troop
from jessica.core.combat import resolve_attack, Attack, CombatError
from jessica.core.turn import end_turn
from jessica.core.constants import TroopArchetype, Phase


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
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
    t.has_moved_this_turn = False
    return t


def test_q_h_invulnerable_vs_unit():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    t1 = _make_troop(state, 1, house="center", life=4)
    t2 = _make_troop(state, 2, house="center", life=4)
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert t1.life == 4, f"t1 deveria continuar com 4, veio {t1.life}"
    assert not t2.is_alive(), "t2 deveria ter morrido"
    print("OK  - Qh: invulnerabilidade bloqueia dano recebido")


def test_q_h_blocks_city_attack():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    t1 = _make_troop(state, 1, house="city_2", life=4)
    try:
        resolve_attack(state, Attack(t1.id, "city", "2"))
        raise AssertionError("Deveria ter bloqueado ataque a Cidade")
    except CombatError as e:
        print(f"OK  - Qh: ataque a Cidade bloqueado: {e}")


def test_q_h_blocks_retaliation():
    state = make_state()
    state.phase = Phase.NIGHT
    t1 = _make_troop(state, 1, house="city_2", life=4)
    before = t1.life
    resolve_attack(state, Attack(t1.id, "city", "2"))
    assert t1.life == before - 1, f"Deveria perder 1, veio {before} -> {t1.life}"
    print("OK  - Sem Qh: retaliacao normal (1 de dano)")


def test_q_s_doubles_damage_unit_vs_unit():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_S")
    play_artifact(state, 1, "Q_S")
    t1 = _make_troop(state, 1, archetype=TroopArchetype.LIGHT, life=4, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t1.is_alive(), f"t1 deveria morrer (tomou 6), veio {t1.life}"
    assert not t2.is_alive(), f"t2 deveria morrer (tomou 8), veio {t2.life}"
    print("OK  - Qs: dobro de dano (t1 4x2=8 mata t2 com 6)")


def test_no_q_s_does_not_kill():
    state = make_state()
    state.phase = Phase.NIGHT
    t1 = _make_troop(state, 1, archetype=TroopArchetype.LIGHT, life=4, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t1.is_alive(), f"t1 deveria morrer, veio {t1.life}"
    assert t2.is_alive(), "t2 deveria sobreviver sem Qs"
    assert t2.life == 2, f"t2 deveria ficar com 2, veio {t2.life}"
    print("OK  - Sem Qs: mesmo ataque nao mata t2 (fica com 2)")


def test_q_s_doubles_damage_to_city():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_S")
    play_artifact(state, 1, "Q_S")
    t1 = _make_troop(state, 1, house="city_2", life=4)
    city2 = state.players[1].city
    life_before = city2.life
    resolve_attack(state, Attack(t1.id, "city", "2"))
    assert city2.life == life_before - 2, f"Esperado {life_before - 2}, veio {city2.life}"
    print(f"OK  - Qs: dobro contra Cidade ({life_before} -> {city2.life})")


def test_q_h_and_q_s_return_to_shop_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    shop_after_play = state.shop.size()
    end_turn(state)
    assert not any(a.card_id == "Q_H" for a in p1.field_artifacts)
    assert state.shop.size() == shop_after_play + 1
    print("OK  - Qh volta a Loja ao fim do turno")


def test_q_s_flag_clears_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("Q_S")
    play_artifact(state, 1, "Q_S")
    assert p1.double_damage_until_end_night is True
    end_turn(state)
    assert p1.double_damage_until_end_night is False
    print("OK  - Qs flag limpa ao fim do turno")


def test_q_h_flags_clear_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("Q_H")
    play_artifact(state, 1, "Q_H")
    assert p1.invulnerable_until_end_turn is True
    end_turn(state)
    assert p1.invulnerable_until_end_turn is False
    print("OK  - Qh flags limpam ao fim do turno")


def run_all():
    tests = [
        test_q_h_invulnerable_vs_unit,
        test_q_h_blocks_city_attack,
        test_q_h_blocks_retaliation,
        test_q_s_doubles_damage_unit_vs_unit,
        test_no_q_s_does_not_kill,
        test_q_s_doubles_damage_to_city,
        test_q_h_and_q_s_return_to_shop_at_end_turn,
        test_q_s_flag_clears_at_end_turn,
        test_q_h_flags_clear_at_end_turn,
    ]
    print("=== Testes F3a ===\\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
'''

# =============================================================
# tests/test_artifact_effects_f3b.py — K♠ e K♣
# =============================================================
FILES["tests/test_artifact_effects_f3b.py"] = '''\
"""Testes F3b: K-spades e K-clubs."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, summon_troop, summon_hero, ActionError,
)
from jessica.core.combat import resolve_attack, Attack, CombatError
from jessica.core.turn import end_day, end_turn
from jessica.core.constants import TroopArchetype, Phase


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
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
    t.has_moved_this_turn = False
    return t


def _make_hero(state, pid, house="center"):
    p = state.players[pid - 1]
    p.city.magic = max(p.city.magic, 10)
    h = summon_hero(state, pid)
    h.house = house
    h.has_moved_this_turn = False
    return h


def test_k_s_requires_no_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    assert any(a.card_id == "K_S" for a in p.field_artifacts)
    print("OK  - Ks jogado sem alvo")


def test_k_s_lets_hero_attack_city():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    hero = _make_hero(state, 1, house="city_2")
    end_day(state)
    city2 = state.players[1].city
    life_before = city2.life
    resolve_attack(state, Attack(hero.id, "city", "2"))
    assert city2.life == life_before - 1
    print(f"OK  - Ks: Heroi atacou Cidade ({life_before} -> {city2.life})")


def test_without_k_s_hero_cannot_attack_city():
    state = make_state()
    hero = _make_hero(state, 1, house="city_2")
    end_day(state)
    try:
        resolve_attack(state, Attack(hero.id, "city", "2"))
        raise AssertionError("Deveria bloquear Heroi atacando Cidade sem Ks")
    except CombatError as e:
        print(f"OK  - Sem Ks: Heroi vs Cidade bloqueado: {e}")


def test_k_s_allows_two_attacks_for_nearby_troop():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)
    assert troop.max_attacks_this_night == 2, f"Esperado 2, veio {troop.max_attacks_this_night}"
    print("OK  - Ks: tropa perto de Heroi ganha 2 ataques")


def test_k_s_troop_without_hero_nearby_has_one_attack():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="city_1")
    end_day(state)
    assert troop.max_attacks_this_night == 1
    print("OK  - Ks: tropa longe de Heroi mantem 1 ataque")


def test_two_attacks_actually_happen():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)
    troop.house = "city_2"
    city2 = state.players[1].city
    life_before = city2.life
    resolve_attack(state, Attack(troop.id, "city", "2"))
    assert troop.attacks_made_this_night == 1
    resolve_attack(state, Attack(troop.id, "city", "2"))
    assert troop.attacks_made_this_night == 2
    assert city2.life == life_before - 2
    print("OK  - Ks: 2 ataques funcionaram (2 dano a Cidade)")


def test_k_s_returns_to_shop_at_end_turn():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    shop_after_play = state.shop.size()
    end_turn(state)
    assert not any(a.card_id == "K_S" for a in p.field_artifacts)
    assert state.shop.size() == shop_after_play + 1
    print("OK  - Ks volta a Loja ao fim do turno")


def test_k_s_buffs_clear_at_end_turn():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    hero = _make_hero(state, 1, house="center")
    troop = _make_troop(state, 1, life=4, house="center")
    end_day(state)
    assert hero.hero_can_attack_city is True
    assert troop.max_attacks_this_night == 2
    end_turn(state)
    assert hero.hero_can_attack_city is False
    assert troop.max_attacks_this_night == 1
    print("OK  - Ks buffs limpam no fim do turno")


def test_k_c_requires_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_C")
    try:
        play_artifact(state, 1, "K_C")
        raise AssertionError("Deveria exigir alvo")
    except (ActionError, ValueError) as e:
        print(f"OK  - Kc sem alvo bloqueado: {e}")


def test_k_c_applies_buffs():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_C")
    troop = _make_troop(state, 1, life=4)
    play_artifact(state, 1, "K_C", choice={"unit_id": troop.id})
    assert troop.double_damage is True
    assert troop.resistance_stacks == 1
    print("OK  - Kc: alvo ganhou dobro e resistencia")


def test_k_c_doubles_damage():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("K_C")
    t1 = _make_troop(state, 1, life=4, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "K_C", choice={"unit_id": t1.id})
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t2.is_alive()
    assert t1.life == 1, f"t1 deveria ficar com 1, veio {t1.life}"
    print(f"OK  - Kc: dobro + resistencia (t1 com {t1.life})")


def test_k_c_returns_to_shop_on_target_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("K_C")
    t1 = _make_troop(state, 1, life=2, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    play_artifact(state, 1, "K_C", choice={"unit_id": t1.id})
    shop_before = state.shop.size()
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert not t1.is_alive()
    assert not any(a.card_id == "K_C" for a in p.field_artifacts)
    assert state.shop.size() == shop_before + 1
    print("OK  - Kc: volta a Loja quando alvo morre")


def test_resistance_divides_damage():
    state = make_state()
    state.phase = Phase.NIGHT
    t1 = _make_troop(state, 1, archetype=TroopArchetype.HEAVY, life=5, house="center")
    t2 = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=5, house="center")
    t2.resistance_stacks = 1
    resolve_attack(state, Attack(t1.id, "unit", t2.id))
    assert t2.life == 3, f"t2 deveria ficar com 3, veio {t2.life}"
    print(f"OK  - Resistencia 1 stack: 5 -> 2 (t2 com {t2.life})")


def run_all():
    tests = [
        test_k_s_requires_no_target,
        test_k_s_lets_hero_attack_city,
        test_without_k_s_hero_cannot_attack_city,
        test_k_s_allows_two_attacks_for_nearby_troop,
        test_k_s_troop_without_hero_nearby_has_one_attack,
        test_two_attacks_actually_happen,
        test_k_s_returns_to_shop_at_end_turn,
        test_k_s_buffs_clear_at_end_turn,
        test_k_c_requires_target,
        test_k_c_applies_buffs,
        test_k_c_doubles_damage,
        test_k_c_returns_to_shop_on_target_death,
        test_resistance_divides_damage,
    ]
    print("=== Testes F3b ===\\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
'''

# =============================================================
# tests/test_artifact_effects_f3d.py — J♦ e Q♦ (sintaxe corrigida)
# =============================================================
FILES["tests/test_artifact_effects_f3d.py"] = '''\
"""Testes F3d: J-diamonds e Q-diamonds."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, summon_troop, resolve_pending_artifact_choice, ActionError,
)
from jessica.core.combat import resolve_attack, Attack
from jessica.core.turn import start_player_day
from jessica.core.constants import TroopArchetype, Phase, CENTER


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
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


def test_j_d_schedules_effect():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    assert len(state.pending_effects) == 1
    e = state.pending_effects[0]
    assert e["kind"] == "J_D"
    assert e["player_id"] == 1
    assert e["due_turn"] == state.turn + 3
    due = e["due_turn"]
    print(f"OK  - Jd agendado para turno {due}")


def test_j_d_triggers_pending_choice():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    state.turn = 4
    start_player_day(state, 1)
    assert p.pending_artifact_choice is not None
    assert p.pending_artifact_choice["kind"] == "J_D"
    assert len(p.pending_artifact_choice["cards"]) == 3
    cards = p.pending_artifact_choice["cards"]
    print(f"OK  - Jd dispara escolha: {cards}")


def test_j_d_resolution_keeps_2_of_3():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    state.turn = 4
    start_player_day(state, 1)
    cards = p.pending_artifact_choice["cards"]
    kept = cards[:2]
    shop_before = state.shop.size()
    resolve_pending_artifact_choice(state, 1, kept_cards=kept)
    assert p.pending_artifact_choice is None
    for c in kept:
        assert c in p.hand
    assert state.shop.size() == shop_before + 2
    assert not any(a.card_id == "J_D" for a in p.field_artifacts)
    print("OK  - Jd resolveu: 2 pra mao, 1 + Jd pra Loja")


def test_j_d_resolution_requires_pick_2():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    state.turn = 4
    start_player_day(state, 1)
    cards = p.pending_artifact_choice["cards"]
    try:
        resolve_pending_artifact_choice(state, 1, kept_cards=cards[:1])
        raise AssertionError("Deveria exigir 2")
    except ActionError as e:
        print(f"OK  - Jd exige 2: {e}")


def test_j_d_persists_in_pending_effects():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_D")
    play_artifact(state, 1, "J_D")
    from jessica.core.serialize import state_to_dict, state_from_dict
    s2 = state_from_dict(state_to_dict(state))
    assert len(s2.pending_effects) == 1
    print("OK  - Jd pendente sobrevive a serializacao")


def test_q_d_requires_unit():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_D")
    try:
        play_artifact(state, 1, "Q_D")
        raise AssertionError("Deveria exigir unit_id")
    except ActionError as e:
        print(f"OK  - Qd sem escolha bloqueado: {e}")


def test_q_d_marks_target_only():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6)
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    qd = next(a for a in p.field_artifacts if a.card_id == "Q_D")
    assert qd.extra["target_unit_id"] == target.id
    assert "resource" not in qd.extra
    print("OK  - Qd marcou alvo (sem recurso)")


def test_q_d_creates_pending_choice_on_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    assert not target.is_alive()
    assert p1.pending_artifact_choice is not None
    assert p1.pending_artifact_choice["kind"] == "Q_D"
    assert p1.pending_artifact_choice["dead_unit_max_life"] == 6
    assert p1.pending_artifact_choice["killer_id"] == 3
    print("OK  - Qd gera escolha pendente na morte")


def test_q_d_gold_reward_to_owner_and_killer():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    gold1_before = state.players[0].city.gold
    gold3_before = state.players[2].city.gold
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="gold")
    assert state.players[0].city.gold == gold1_before + 6
    assert state.players[2].city.gold == gold3_before + 6
    print("OK  - Qd: +6 Ouro pro dono e matador")


def test_q_d_magic_reward():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    m1_before = state.players[0].city.magic
    m3_before = state.players[2].city.magic
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="magic")
    assert state.players[0].city.magic == m1_before + 6
    assert state.players[2].city.magic == m3_before + 6
    print("OK  - Qd: +6 Magia pro dono e matador")


def test_q_d_no_double_when_owner_is_killer():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 1, archetype=TroopArchetype.LIGHT, life=4, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    gold1_before = state.players[0].city.gold
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="gold")
    assert state.players[0].city.gold == gold1_before + 4
    print("OK  - Qd: owner ganha 1 vez")


def test_q_d_returns_to_shop_after_resolution():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.HEAVY, life=8, house="center")
    shop_before = state.shop.size()
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    resolve_pending_artifact_choice(state, 1, resource="gold")
    assert not any(a.card_id == "Q_D" for a in p1.field_artifacts)
    assert state.shop.size() == shop_before + 1
    print("OK  - Qd volta a Loja apos resolucao")


def test_q_d_no_reward_if_target_survives():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_D")
    target = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    play_artifact(state, 1, "Q_D", choice={"unit_id": target.id})
    attacker = _make_troop(state, 3, archetype=TroopArchetype.LIGHT, life=2, house="center")
    gold1_before = state.players[0].city.gold
    resolve_attack(state, Attack(attacker.id, "unit", target.id))
    assert target.is_alive()
    assert p1.pending_artifact_choice is None
    assert state.players[0].city.gold == gold1_before
    assert any(a.card_id == "Q_D" for a in p1.field_artifacts)
    print("OK  - Qd sem recompensa se alvo sobrevive")


def run_all():
    tests = [
        test_j_d_schedules_effect,
        test_j_d_triggers_pending_choice,
        test_j_d_resolution_keeps_2_of_3,
        test_j_d_resolution_requires_pick_2,
        test_j_d_persists_in_pending_effects,
        test_q_d_requires_unit,
        test_q_d_marks_target_only,
        test_q_d_creates_pending_choice_on_death,
        test_q_d_gold_reward_to_owner_and_killer,
        test_q_d_magic_reward,
        test_q_d_no_double_when_owner_is_killer,
        test_q_d_returns_to_shop_after_resolution,
        test_q_d_no_reward_if_target_survives,
    ]
    print("=== Testes F3d ===\\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
'''

# =============================================================
# tests/test_artifact_effects_f3e.py — J♣ e Q♣ (reescrito)
# =============================================================
FILES["tests/test_artifact_effects_f3e.py"] = '''\
"""Testes F3e: J-clubs e Q-clubs."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    play_artifact, summon_troop, ActionError,
)
from jessica.core.combat import resolve_attack, Attack
from jessica.core.turn import day_order, end_turn
from jessica.core.constants import TroopArchetype, Phase, CENTER


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
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


def test_j_c_requires_target_player():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_C")
    try:
        play_artifact(state, 1, "J_C")
        raise AssertionError("Deveria exigir alvo")
    except ActionError as e:
        print(f"OK  - Jc sem alvo bloqueado: {e}")


def test_j_c_cannot_target_self():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_C")
    try:
        play_artifact(state, 1, "J_C", choice={"target_player_id": 1})
        raise AssertionError("Deveria bloquear auto-alvo")
    except ValueError as e:
        print(f"OK  - Jc nao pode ter voce mesmo: {e}")


def test_j_c_marks_skip_for_target_who_has_not_played():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")
    p1.has_played_day_this_turn = True
    p2.has_played_day_this_turn = False
    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})
    assert p2.skip_day_turn == state.turn
    assert p2.skip_night_turn == state.turn
    print(f"OK  - Jc: J2 (nao jogou) pula Dia e Noite do turno {state.turn}")


def test_j_c_marks_skip_for_target_who_has_played():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")
    p1.has_played_day_this_turn = True
    p2.has_played_day_this_turn = True
    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})
    assert p2.skip_night_turn == state.turn
    assert p2.skip_day_turn == state.turn + 1
    print(f"OK  - Jc: J2 (ja jogou) pula Noite atual + Dia {state.turn + 1}")


def test_j_c_day_order_skips_target():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("J_C")
    p2.has_played_day_this_turn = False
    p1.has_played_day_this_turn = True
    play_artifact(state, 1, "J_C", choice={"target_player_id": 2})
    order = day_order(state)
    assert 2 not in order, f"J2 deveria estar pulado: {order}"
    print(f"OK  - day_order omite J2 (pulado): {order}")


def test_q_c_requires_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    try:
        play_artifact(state, 1, "Q_C")
        raise AssertionError("Deveria exigir alvo")
    except ActionError as e:
        print(f"OK  - Qc sem alvo bloqueado: {e}")


def test_q_c_cannot_target_own_unit():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    own = _make_troop(state, 1, life=4)
    try:
        play_artifact(state, 1, "Q_C", choice={"unit_id": own.id})
        raise AssertionError("Deveria bloquear unidade propria")
    except ValueError as e:
        print(f"OK  - Qc nao pode controlar unidade propria: {e}")


def test_q_c_takes_control():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=4)
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    p1_ids = {u.id for u in p1.units}
    p2_ids = {u.id for u in p2.units}
    assert enemy.id in p1_ids
    assert enemy.id not in p2_ids
    assert enemy.original_owner_id == 2
    assert enemy.owner_id == 1
    print(f"OK  - Qc: {enemy.id} passou para J1")


def test_q_c_returns_control_at_end_turn():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=4)
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    end_turn(state)
    p1_ids = {u.id for u in p1.units}
    p2_ids = {u.id for u in p2.units}
    assert enemy.id not in p1_ids
    assert enemy.id in p2_ids
    assert enemy.owner_id == 2
    print("OK  - Qc: unidade volta ao dono no fim do turno")


def test_q_c_can_attack_original_owner():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=4, house="center")
    own = _make_troop(state, 2, archetype=TroopArchetype.MEDIUM, life=6, house="center")
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    resolve_attack(state, Attack(enemy.id, "unit", own.id))
    assert not enemy.is_alive()
    print("OK  - Qc: controlada pode atacar unidade do dono original")


def test_q_c_controlled_dies_permanently():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p2 = state.players[1]
    p1.hand.append("Q_C")
    enemy = _make_troop(state, 2, life=2, house="center")
    own = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    play_artifact(state, 1, "Q_C", choice={"unit_id": enemy.id})
    resolve_attack(state, Attack(enemy.id, "unit", own.id))
    p1_ids = {u.id for u in p1.units}
    p2_ids = {u.id for u in p2.units}
    assert enemy.id not in p1_ids
    assert enemy.id not in p2_ids
    print("OK  - Qc: se controlada morre, morre")


def run_all():
    tests = [
        test_j_c_requires_target_player,
        test_j_c_cannot_target_self,
        test_j_c_marks_skip_for_target_who_has_not_played,
        test_j_c_marks_skip_for_target_who_has_played,
        test_j_c_day_order_skips_target,
        test_q_c_requires_target,
        test_q_c_cannot_target_own_unit,
        test_q_c_takes_control,
        test_q_c_returns_control_at_end_turn,
        test_q_c_can_attack_original_owner,
        test_q_c_controlled_dies_permanently,
    ]
    print("=== Testes F3e ===\\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
'''

# =============================================================
# tests/test_boin.py — corrigido (sintaxe)
# =============================================================
FILES["tests/test_boin.py"] = '''\
"""Testes: Boin."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, buy_artifact_with_gold, transmute_artifact_with_magic,
    resolve_pending_artifact_choice, summon_troop,
)
from jessica.core.constants import TroopArchetype, CENTER


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


def _summon_until_boin(state, pid):
    p = state.players[pid - 1]
    p.city.magic = 20
    for _ in range(4):
        summon_hero(state, pid)
    return next(u for u in p.units if u.hero_id == "boin")


def _center_troop(state, pid):
    p = state.players[pid - 1]
    p.city.gold = max(p.city.gold, 10)
    p.city.magic = max(p.city.magic, 5)
    t = summon_troop(state, pid, TroopArchetype.LIGHT, 4)
    t.house = CENTER
    return t


def test_boin_buy_draws_2_picks_1():
    state = make_state()
    _summon_until_boin(state, 2)
    _center_troop(state, 2)
    p = state.players[1]
    p.city.gold = 20
    hand_before = len(p.hand)
    shop_before = state.shop.size()

    result = buy_artifact_with_gold(state, 2)
    assert result is None, "Boin deveria devolver None (pending choice)"
    pending = p.pending_artifact_choice
    assert pending is not None
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    cards = pending["cards"]
    print(f"OK  - Boin: comprou e recebeu 2 cartas: {cards}")

    chosen = pending["cards"][0]
    resolve_pending_artifact_choice(state, 2, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1
    assert state.shop.size() == shop_before - 1
    print(f"OK  - Boin: escolheu {chosen}, outra devolvida")


def test_boin_transmute_draws_2_picks_1():
    state = make_state()
    _summon_until_boin(state, 2)
    p = state.players[1]
    p.city.magic = 20
    hand_before = len(p.hand)

    result = transmute_artifact_with_magic(state, 2)
    assert result is None
    pending = p.pending_artifact_choice
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    chosen = pending["cards"][1]
    resolve_pending_artifact_choice(state, 2, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1
    print("OK  - Boin transmutou com escolha 2-de-1")


def test_no_boin_buy_direct():
    state = make_state()
    _center_troop(state, 2)
    p = state.players[1]
    p.city.gold = 20
    result = buy_artifact_with_gold(state, 2)
    assert result is not None
    assert result in p.hand
    assert p.pending_artifact_choice is None
    print("OK  - Sem Boin: compra direta (1 carta)")


def run_all():
    tests = [
        test_boin_buy_draws_2_picks_1,
        test_boin_transmute_draws_2_picks_1,
        test_no_boin_buy_direct,
    ]
    print("=== Testes Boin ===\\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
'''

# =============================================================
# Execução
# =============================================================
def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for rel_path, content in FILES.items():
        full = ROOT / rel_path
        if full.exists():
            backup_path = BACKUP_DIR / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, backup_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        print(f"OK  - {rel_path}")
    print(f"\\n{len(FILES)} arquivos escritos.")
    print(f"Backup: {BACKUP_DIR}")
    print("\\nRode:")
    print("  python tests/test_artifact_effects_f3a.py")
    print("  python tests/test_artifact_effects_f3b.py")
    print("  python tests/test_artifact_effects_f3d.py")
    print("  python tests/test_artifact_effects_f3e.py")
    print("  python tests/test_boin.py")
    print("  python tests/run_all.py")


if __name__ == "__main__":
    main()