"""apply_update_v5c0: estabilizacao (Ainai, Pe Descalco, Cova Rasa, Presenca
   Magnetica, Luarado, Luide Vampa, aposta H em perda de muralha)."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5c0_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}
EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. combat.py - rewrite (Pe Descalco, Luarado, lose_city_life)
# =============================================================
FILES["jessica/core/combat.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass
from .state import get_player, get_city, log
from .models import GameState, Unit, Hero, Troop
from . import peoples


class CombatError(Exception):
    pass


@dataclass
class Attack:
    attacker_unit_id: str
    target_type: str
    target_id: str


def _find_unit(state: GameState, unit_id: str) -> Unit | None:
    for player in state.players:
        for unit in player.units:
            if unit.id == unit_id and unit.is_alive():
                return unit
    return None


def _find_unit_any(state: GameState, unit_id: str) -> Unit | None:
    for player in state.players:
        for unit in player.units:
            if unit.id == unit_id:
                return unit
    return None


def _hero_has(unit: Unit, ability: str) -> bool:
    from . import heroes
    if not isinstance(unit, Hero):
        return False
    return heroes.has_ability(unit.hero_id, ability)


def _is_miyamoto(unit: Unit) -> bool:
    return _hero_has(unit, "double_attack_if_stronger")


def _effective_max_attacks(state: GameState, unit: Unit) -> int:
    base = unit.max_attacks_this_night
    if _is_miyamoto(unit):
        if peoples.compute_hero_max_attacks_in_house(
                state, unit, "double_attack_if_stronger") >= 2:
            base += 1
    if _hero_has(unit, "extra_attacks_per_dwarf"):
        owner = get_player(state, unit.owner_id)
        n = sum(1 for u in owner.units
                if isinstance(u, Hero) and u.is_alive()
                and u.id != unit.id and u.house == unit.house)
        base += n
    # Pe Descalco: +1 ataque sempre
    if _hero_has(unit, "ataque_extra"):
        base += 1
    if unit.statuses.get("k_s_active"):
        base *= 2
    return base


def _attacks_used(unit: Unit) -> int:
    if _is_miyamoto(unit):
        return unit.attacks_made_this_day
    return unit.attacks_made_this_night


def _register_attack(unit: Unit) -> None:
    if _is_miyamoto(unit):
        unit.attacks_made_this_day += 1
    else:
        unit.attacks_made_this_night += 1


def _award_city_destruction(state: GameState, destroyer_id: int) -> None:
    alive_now = sum(1 for p in state.players if p.city.is_alive())
    reward = {3: 4, 2: 3, 1: 2, 0: 0}.get(alive_now, 0)
    if reward == 0:
        return
    destroyer = get_player(state, destroyer_id)
    for _ in range(reward):
        if state.shop.is_empty():
            break
        destroyer.hand.append(state.shop.draw_random(state.rng))
    log(state, f"  {destroyer.name} destruiu Cidade e ganhou {reward} artefato(s).")


def _cleanup_dead(state: GameState) -> None:
    from . import artifacts_effects

    dead_units: list[Unit] = []
    for player in state.players:
        for u in player.units:
            if not u.is_alive():
                dead_units.append(u)

    for u in dead_units:
        owner = get_player(state, u.owner_id)
        if owner.people == peoples.PEOPLE_FAE:
            state.fae_fallen_this_turn.append((owner.id, u.house))

    for u in dead_units:
        if u.house not in state.deaths_this_night:
            state.deaths_this_night.append(u.house)
        artifacts_effects.on_unit_death(state, u)
        if u.killed_by_player_id is not None:
            killer_unit = None
            if u.killed_by_unit_id is not None:
                killer_unit = _find_unit_any(state, u.killed_by_unit_id)
            peoples.on_unit_killed_by(state, u.killed_by_player_id, u, killer_unit)

    for player in state.players:
        dead = [u for u in player.units if not u.is_alive()]
        for u in dead:
            log(state, f"  {u.id} ({player.name}) morreu.")
        player.units = [u for u in player.units if u.is_alive()]

    artifacts_effects.on_cleanup_after_combat(state)

    for player in state.players:
        if not player.city.is_alive() and player.units:
            log(state, f"  {player.name} eliminado.")
            player.units = []


def _attack_multiplier(state: GameState, attacker: Unit, target: Unit | None = None) -> int:
    mult = 1
    p = get_player(state, attacker.owner_id)
    if p.double_damage_until_end_night:
        mult *= 2
    if attacker.double_damage:
        mult *= 2
    if _hero_has(attacker, "double_damage_and_resist_vs_stronger") and target is not None:
        if target.life >= attacker.life:
            mult *= 2
    if peoples.is_lobisomem_ativo(state, attacker):
        mult *= 2
    if peoples.sao_tome_dano_lobisomem(state, attacker):
        mult *= 2
    return mult


def _compute_attack_damage(state: GameState, attacker: Unit, base: int,
                           target: Unit | None = None) -> int:
    if _hero_has(attacker, "deals_1_to_4_damage") and target is not None:
        base = state.rng.randint(1, 4)
    return base * _attack_multiplier(state, attacker, target)


def _apply_vovo_bonus(state: GameState, attacker: Unit, dmg: int,
                      target: Unit | None) -> int:
    if target is None:
        return dmg
    if peoples.has_vovo_bonus(state, attacker):
        return dmg + 1
    return dmg


def _apply_amaldicoado(state: GameState, defender: Unit, dmg: int) -> int:
    if defender.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
        return dmg * 2
    return dmg


def _apply_defense(state: GameState, defender: Unit, dmg: int,
                   attacker: Unit | None = None,
                   is_city_retaliation: bool = False) -> tuple[int, list[str]]:
    notes: list[str] = []
    p = get_player(state, defender.owner_id)
    if p.invulnerable_until_end_turn:
        notes.append("invulneravel -> 0")
        return 0, notes
    if _hero_has(defender, "takes_1_damage_when_attacked") and not is_city_retaliation:
        if dmg > 0:
            dmg = min(dmg, 1)
    original = dmg
    for _ in range(defender.resistance_stacks):
        dmg = dmg // 2
    if _hero_has(defender, "resistance_aura"):
        dmg = dmg // 2
        notes.append("Ori aura")
    else:
        for u in p.units:
            if isinstance(u, Hero) and u.is_alive() and _hero_has(u, "resistance_aura"):
                if u.house == defender.house:
                    dmg = dmg // 2
                    notes.append("Ori aura (aliado)")
                    break
    if attacker is not None and _hero_has(defender, "double_damage_and_resist_vs_stronger"):
        if attacker.life >= defender.life:
            dmg = dmg // 2
            notes.append("Besouro resistencia")
    if dmg < original:
        notes.append(f"dano {original} -> {dmg}")
    return dmg, notes


_armor_choice_fn = None


def set_armor_choice_fn(fn) -> None:
    global _armor_choice_fn
    _armor_choice_fn = fn


def _apply_armor(state: GameState, defender_player_id: int, dmg: int) -> int:
    p = get_player(state, defender_player_id)
    if p.armor_active_until_turn < state.turn or dmg <= 0:
        return dmg
    if _armor_choice_fn is not None:
        try:
            pay = int(_armor_choice_fn(p, dmg))
        except Exception:
            pay = min(dmg, p.city.gold)
    else:
        pay = min(dmg, p.city.gold)
    pay = max(0, min(pay, dmg, p.city.gold))
    if pay <= 0:
        return dmg
    p.city.gold -= pay
    log(state, f"    Armadura de Ouro absorveu {pay} (restam {p.city.gold} Ouro).")
    return dmg - pay


def _check_can_attack(state: GameState, unit: Unit) -> None:
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        raise CombatError(f"Unidade {unit.id} nao pode atacar (Espoliou).")
    if unit.statuses.get("sono_until_turn", -1) > state.turn:
        raise CombatError(f"Unidade {unit.id} esta dormindo (Bein).")


def _compute_bein_sleep_until(state: GameState, attacker_owner_id: int) -> int:
    order = state.turn_order
    if not order:
        return state.turn + 1
    if attacker_owner_id not in order or state.curuna_id not in order:
        return state.turn + 1
    curuna_idx = order.index(state.curuna_id)
    owner_idx = order.index(attacker_owner_id)
    delta = (owner_idx - curuna_idx) % len(order)
    if delta == 0:
        delta = len(order)
    return state.turn + delta


def _apply_vampiro_after_round(state: GameState, self_unit: Unit, other: Unit,
                               self_life_before: int, other_life_before: int) -> None:
    sp = get_player(state, self_unit.owner_id)
    if sp.people != peoples.PEOPLE_VAMPIRES:
        return
    empatou = (self_life_before == other_life_before and self_life_before > 0)
    matou = not other.is_alive()

    if empatou and matou:
        self_unit.life = min(2, self_unit.life_max)
        log(state, f"    {self_unit.id} empata e mata: sobrevive com 2 (Sede de Sangue).")
        return
    if empatou and not self_unit.is_alive():
        self_unit.life = min(2, self_unit.life_max)
        log(state, f"    {self_unit.id} empata: sobrevive com 2 (Sede de Sangue).")
        return
    if matou:
        before = self_unit.life
        self_unit.life = min(self_unit.life_max, self_unit.life + 2)
        if self_unit.life != before:
            log(state, f"    {self_unit.id} curou +{self_unit.life - before} (Sede de Sangue).")


def _luarado_infecta(state: GameState, attacker: Unit, target: Unit, dmg: int) -> None:
    """Luarado infecta QUALQUER alvo que ele cause dano (heroi ou tropa)."""
    from . import peoples as _p
    if dmg <= 0:
        return
    if not _p.is_lobisomem_ativo(state, attacker):
        return
    owner = get_player(state, attacker.owner_id)
    if not (isinstance(attacker, Hero) and attacker.hero_id == "luarado"):
        return
    sig = _p.unit_signature(target)
    if sig not in owner.infectados:
        owner.infectados.append(sig)
        log(state, f"    {target.id} infectado por Luarado (Maldicao da Lua).")


def _try_execute_hero(state: GameState, executor: Unit, victim: Unit) -> bool:
    if not _hero_has(executor, "execute_weak_targets"):
        return False
    if not victim.is_alive():
        return False
    aliados = [
        u for u in get_player(state, victim.owner_id).units
        if u.house == victim.house and u.is_alive() and u.id != victim.id
    ]
    if aliados:
        return False
    victim.statuses["life_at_death"] = victim.life
    victim.life = 0
    victim.killed_by_player_id = executor.owner_id
    victim.killed_by_unit_id = executor.id
    log(state, f"  {executor.id} EXECUTOU {victim.id}.")
    if _hero_has(executor, "grow_per_execute"):
        executor.life_max += 1
        executor.life += 1
        ep = get_player(state, executor.owner_id)
        ep.garoche_life_max_bonus += 1
        log(state, f"  {executor.id} cresceu para {executor.life}/{executor.life_max} "
                   f"(bonus persistente: {ep.garoche_life_max_bonus}).")
    return True


def _resolve_combat_round(state: GameState, attacker: Unit, target: Unit) -> None:
    attacker_player = get_player(state, attacker.owner_id)
    target_player = get_player(state, target.owner_id)

    attacker.statuses.pop("invisivel_until_turn", None)

    if _try_execute_hero(state, attacker, target):
        return
    if target.is_alive() and _try_execute_hero(state, target, attacker):
        return

    atk_life = attacker.life
    tgt_life = target.life

    raw_atk = _compute_attack_damage(state, attacker, atk_life, target=target)
    raw_atk = _apply_vovo_bonus(state, attacker, raw_atk, target)
    raw_atk = _apply_amaldicoado(state, target, raw_atk)
    raw_tgt = _compute_attack_damage(state, target, tgt_life, target=attacker)
    raw_tgt = _apply_vovo_bonus(state, target, raw_tgt, attacker)
    raw_tgt = _apply_amaldicoado(state, attacker, raw_tgt)

    dmg_to_target, notes_t = _apply_defense(state, target, raw_atk, attacker)
    dmg_to_attacker, notes_a = _apply_defense(state, attacker, raw_tgt, target)

    dmg_to_target = _apply_armor(state, target.owner_id, dmg_to_target)
    dmg_to_attacker = _apply_armor(state, attacker.owner_id, dmg_to_attacker)

    # Luarado: infecta por dano (antes de aplicar morte)
    _luarado_infecta(state, attacker, target, dmg_to_target)

    attacker.life = max(0, atk_life - dmg_to_attacker)
    target.life = max(0, tgt_life - dmg_to_target)

    _apply_vampiro_after_round(state, attacker, target, atk_life, tgt_life)
    _apply_vampiro_after_round(state, target, attacker, tgt_life, atk_life)

    if not attacker.is_alive():
        attacker.statuses["life_at_death"] = atk_life
    if not target.is_alive():
        target.statuses["life_at_death"] = tgt_life

    if not _hero_has(attacker, "sleep_on_attack"):
        if target.statuses.get("sono_until_turn", -1) > state.turn:
            target.statuses.pop("sono_until_turn", None)
            log(state, f"    {target.id} acordou (foi atacado).")

    if _hero_has(attacker, "sleep_on_attack") and target.is_alive():
        sono_until = _compute_bein_sleep_until(state, attacker.owner_id)
        target.statuses["sono_until_turn"] = sono_until
        log(state, f"    {target.id} adormeceu (ate turno {sono_until}).")

    if _hero_has(target, "kill_attacker_at_night_end") and dmg_to_target > 0:
        state.dain_kills.append({"attacker_id": attacker.id, "turn": state.turn})
        log(state, f"    {attacker.id} atacou Dain e morrera no fim da noite.")

    extra = ""
    if notes_t:
        extra += f" [alvo: {'; '.join(notes_t)}]"
    if notes_a:
        extra += f" [atacante: {'; '.join(notes_a)}]"

    log(state, f"  {attacker.id} ({attacker_player.name}) atacou "
               f"{target.id} ({target_player.name}): "
               f"{attacker.id} {atk_life} -> {attacker.life}, "
               f"{target.id} {tgt_life} -> {target.life}{extra}.")

    if not attacker.is_alive():
        attacker.killed_by_player_id = target.owner_id
        attacker.killed_by_unit_id = target.id
    if not target.is_alive():
        target.killed_by_player_id = attacker.owner_id
        target.killed_by_unit_id = attacker.id


def _city_life_lost(state: GameState, target_pid: int, amount: int) -> None:
    """Notifica a perda de vida da cidade para apostas (H - Copas)."""
    if amount <= 0:
        return
    peoples.on_action_performed(state, target_pid, "lose_city_life")


def resolve_attack(state: GameState, attack: Attack) -> None:
    attacker = _find_unit(state, attack.attacker_unit_id)
    if attacker is None:
        raise CombatError(f"Atacante {attack.attacker_unit_id} nao encontrado.")
    _check_can_attack(state, attacker)
    max_atk = _effective_max_attacks(state, attacker)
    if _attacks_used(attacker) >= max_atk:
        raise CombatError(f"Unidade {attacker.id} ja atacou o maximo.")

    attacker_player = get_player(state, attacker.owner_id)
    attacker_name = attacker_player.name

    if attack.target_type == "city" and attacker_player.no_city_attacks_until_end_turn:
        raise CombatError(f"{attacker_name} nao pode atacar Cidades (Qh).")

    if attack.target_type == "city":
        can_hero_attack_city = attacker.hero_can_attack_city
        if isinstance(attacker, Hero) and not can_hero_attack_city:
            if _hero_has(attacker, "dwarves_can_attack_cities"):
                can_hero_attack_city = True
            elif _hero_has(attacker, "veu_da_lua"):
                if peoples.is_lua_cheia(state, attacker.owner_id):
                    can_hero_attack_city = True
            else:
                owner = get_player(state, attacker.owner_id)
                for u in owner.units:
                    if (isinstance(u, Hero) and u.is_alive()
                            and u.hero_id == "din" and u.house == attacker.house):
                        can_hero_attack_city = True
                        break
        if isinstance(attacker, Hero) and not can_hero_attack_city:
            raise CombatError("Heroi nao pode atacar Cidade (CMB-002).")
        if not attack.target_id.isdigit():
            raise CombatError("Alvo de cidade deve ser id.")
        target_pid = int(attack.target_id)
        if target_pid == attacker.owner_id:
            raise CombatError("Nao pode atacar a propria Cidade.")
        target_player = get_player(state, target_pid)
        city = target_player.city
        if not city.is_alive():
            raise CombatError(f"Cidade ja destruida.")

        attacker.statuses.pop("invisivel_until_turn", None)

        dmg_to_city = _compute_attack_damage(state, attacker, 1)
        life_before = city.life
        city.life = max(0, city.life - dmg_to_city)
        _city_life_lost(state, target_pid, life_before - city.life)
        log(state, f"  {attacker.id} ({attacker_name}) atacou Cidade de "
                   f"{target_player.name}: {life_before} -> {city.life}.")
        if life_before > 0 and city.life == 0:
            if city.has_monument:
                log(state, f"  A Cidade de {target_player.name} ruiu - Monumento tambem.")
            else:
                log(state, f"  A Cidade de {target_player.name} ruiu.")
            _award_city_destruction(state, attacker.owner_id)

        raw_ret = 1
        ret, notes = _apply_defense(state, attacker, raw_ret, is_city_retaliation=True)
        if _hero_has(attacker, "takes_1_damage_when_attacked") and raw_ret > 0:
            ret, notes = _apply_defense(state, attacker, 1, is_city_retaliation=True)
        ret = _apply_armor(state, attacker.owner_id, ret)
        if ret == 0 and attacker_player.invulnerable_until_end_turn:
            log(state, f"  Retaliacao ignorada (invulneravel).")
        else:
            before = attacker.life
            attacker.life = max(0, attacker.life - ret)
            note_str = f" [{'; '.join(notes)}]" if notes else ""
            log(state, f"  Retaliacao: {attacker.id} {before} -> {attacker.life}{note_str}.")
            if not attacker.is_alive():
                attacker.statuses["life_at_death"] = before
                attacker.killed_by_player_id = target_pid

    elif attack.target_type == "unit":
        target = _find_unit(state, attack.target_id)
        if target is None:
            raise CombatError(f"Alvo nao encontrado.")
        if target.owner_id == attacker.owner_id:
            raise CombatError("Nao pode atacar aliado.")
        if target.statuses.get("invisivel_until_turn", -1) >= state.turn:
            raise CombatError(f"{target.id} esta invisivel.")
        if _hero_has(target, "cannot_be_attacked_by_heroes") and isinstance(attacker, Hero):
            raise CombatError(f"{target.id} (Buin) nao pode ser atacado por Herois.")

        _resolve_combat_round(state, attacker, target)

    else:
        raise CombatError(f"Tipo invalido: {attack.target_type}")

    _register_attack(attacker)
    _cleanup_dead(state)


def resolve_attack_day(state: GameState, attack: Attack) -> None:
    attacker = _find_unit(state, attack.attacker_unit_id)
    if attacker is None:
        raise CombatError(f"Atacante nao encontrado.")
    max_atk = _effective_max_attacks(state, attacker)
    if _attacks_used(attacker) >= max_atk:
        raise CombatError(f"Unidade {attacker.id} ja atacou o maximo.")
    if attack.target_type != "unit":
        raise CombatError("Ataque diurno so ataca unidades.")
    target = _find_unit(state, attack.target_id)
    if target is None:
        raise CombatError(f"Alvo nao encontrado.")
    if target.owner_id == attacker.owner_id:
        raise CombatError("Nao pode atacar aliado.")
    if target.statuses.get("invisivel_until_turn", -1) >= state.turn:
        raise CombatError(f"{target.id} esta invisivel.")
    _resolve_combat_round(state, attacker, target)
    _register_attack(attacker)
    _cleanup_dead(state)


def resolve_night(state: GameState, attacks: list[Attack]) -> None:
    if not attacks:
        log(state, "Nenhum ataque nesta Noite.")
        return
    order = ["center", "city_4", "city_3", "city_2", "city_1"]
    by_house: dict[str, list[Attack]] = {}
    for a in attacks:
        unit = _find_unit(state, a.attacker_unit_id)
        house = unit.house if unit else "?"
        by_house.setdefault(house, []).append(a)
    for house in order:
        for a in by_house.get(house, []):
            resolve_attack(state, a)
    for house, atks in by_house.items():
        if house in order:
            continue
        for a in atks:
            resolve_attack(state, a)
'''

# =============================================================
# 2. peoples.py - rewrite (Presenca real, Cova Rasa, perda muralha)
# =============================================================
FILES["jessica/core/peoples.py"] = '''\
"""Passivas dos povos."""
from __future__ import annotations
from .state import get_player, log
from .models import GameState, Player, Unit, Hero, Troop
from .constants import (
    TroopArchetype, CENTER, CITY_HOUSES,
    BET_HEART, BET_CLUB, BET_DIAMOND, BET_SPADE, ALL_BETS, FILHOS_BONUS_TURN,
)
from . import heroes


PEOPLE_HUMANS = "humanos"
PEOPLE_DWARVES = "anoes"
PEOPLE_ORCS = "orcs"
PEOPLE_FAE = "fadas"
PEOPLE_VAMPIRES = "vampiros"
PEOPLE_LOBISOMENS = "lobisomens"
PEOPLE_GIGANTES = "gigantes"
PEOPLE_MORTOS_VIVOS = "mortos_vivos"
PEOPLE_FILHOS = "filhos_floresta"
PEOPLE_GNOMOS = "gnomos_duendes"


ACTION_TO_BET = {
    "raise_city_life": BET_HEART,
    "lose_city_life": BET_HEART,
    "play_artifact": BET_CLUB,
    "buy_artifact_gold": BET_DIAMOND,
    "buy_artifact_magic": BET_DIAMOND,
    "transmute_artifact_magic": BET_DIAMOND,
    "sell_artifact": BET_DIAMOND,
    "summon_hero": BET_SPADE,
    "summon_troop": BET_SPADE,
    "kill": BET_SPADE,
}


def unit_signature(u: Unit) -> dict:
    if isinstance(u, Hero):
        return {"kind": "hero", "id": u.hero_id}
    return {"kind": "troop", "id": u.archetype.value}


def is_empalado(player: Player, sig: dict) -> bool:
    return sig in player.empalados


def on_action_performed(state: GameState, actor_id: int, action: str) -> None:
    suit = ACTION_TO_BET.get(action)
    if suit is None:
        return
    for gnomo in state.players:
        if gnomo.people != PEOPLE_GNOMOS:
            continue
        if not gnomo.city.is_alive():
            continue
        target = getattr(gnomo, f"bet_{suit}_target", None)
        if target is None:
            continue
        if target != actor_id:
            continue
        gnomo.correct_bets += 1
        setattr(gnomo, f"bet_{suit}_target", None)
        actor = get_player(state, actor_id)
        log(state, f"{gnomo.name}: Aposta {suit} cumprida por {actor.name}. "
                   f"(Total: {gnomo.correct_bets} corretas)")


def sao_tome_has_aposta_em(player: Player, target_id: int) -> bool:
    return (
        player.bet_H_target == target_id
        or player.bet_C_target == target_id
        or player.bet_D_target == target_id
        or player.bet_S_target == target_id
    )


def sao_tome_effective_peoples(state: GameState, player: Player) -> set[str]:
    if player.people != PEOPLE_GNOMOS:
        return {player.people}
    has_sao_tome = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
        for u in player.units
    )
    if not has_sao_tome:
        return {PEOPLE_GNOMOS}
    result = {PEOPLE_GNOMOS}
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        if sao_tome_has_aposta_em(player, other.id):
            result.add(other.people)
    return result


def sao_tome_dano_lobisomem(state: GameState, attacker) -> bool:
    if not (isinstance(attacker, Hero) and attacker.hero_id == "sao_tome"):
        return False
    owner = get_player(state, attacker.owner_id)
    if owner.people != PEOPLE_GNOMOS:
        return False
    effective = sao_tome_effective_peoples(state, owner)
    if PEOPLE_LOBISOMENS not in effective:
        return False
    for other in state.players:
        if other.id == owner.id:
            continue
        if not sao_tome_has_aposta_em(owner, other.id):
            continue
        if other.people != PEOPLE_LOBISOMENS:
            continue
        if is_lua_cheia(state, other.id):
            return True
    return False


def apply_filhos_bonus(state: GameState) -> None:
    if state.turn != FILHOS_BONUS_TURN:
        return
    for p in state.players:
        if p.people != PEOPLE_FILHOS:
            continue
        if not p.city.is_alive():
            continue
        if p.filhos_bonus_recebido:
            continue
        ganho_vida = min(2, p.city.life_max - p.city.life)
        p.city.life += ganho_vida
        p.city.gold += 2
        p.city.magic += 2
        p.filhos_bonus_recebido = True
        log(state, f"{p.name} (Filhos): Florescimento Exuberante (+{ganho_vida} Vida, +2 Ouro, +2 Magia).")


def reset_gnomos_bets(state: GameState) -> None:
    for p in state.players:
        if p.people != PEOPLE_GNOMOS:
            continue
        if not p.city.is_alive():
            continue
        p.bet_H_target = None
        p.bet_C_target = None
        p.bet_D_target = None
        p.bet_S_target = None
        p.bets_need_realocacao = True
        log(state, f"{p.name} (Gnomos): apostas serao re-alocadas.")


def draw_spell_copia(state: GameState, player: Player) -> None:
    from . import spells as spells_mod
    peoples_participantes = set()
    for p in state.players:
        if p.people and p.people != PEOPLE_GNOMOS:
            peoples_participantes.add(p.people)
    if not peoples_participantes:
        player.spell_copia_id = None
        return
    candidatos = []
    for people in peoples_participantes:
        sp = spells_mod.spell_for_people(people)
        if sp is not None:
            candidatos.append(sp.spell_id)
    if not candidatos:
        player.spell_copia_id = None
        return
    player.spell_copia_id = state.rng.choice(candidatos)
    player.spell_copia_turn = state.turn
    log(state, f"{player.name} (Gnomos): feitico copiado sorteado: {player.spell_copia_id}.")


def on_player_morning(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    p = player.people
    if p == PEOPLE_DWARVES:
        _dwarves_mineiro_carreiro(state, player)
    elif p == PEOPLE_HUMANS:
        _humans_roca_de_quilombo(state, player)
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive() and u.hero_id == "barbadourada":
            n = len(player.hand)
            if n > 0:
                player.city.magic += n
                log(state, f"{player.name}: Barbadourada - +{n} Magia.")
    if p == PEOPLE_GNOMOS:
        _sao_tome_extra_passives(state, player)


def _sao_tome_extra_passives(state: GameState, player: Player) -> None:
    has_sao_tome = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
        for u in player.units
    )
    if not has_sao_tome:
        return
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        if not sao_tome_has_aposta_em(player, other.id):
            continue
        op = other.people
        if op == PEOPLE_DWARVES:
            _dwarves_mineiro_carreiro(state, player)
        elif op == PEOPLE_HUMANS:
            _humans_roca_de_quilombo(state, player)


def _dwarves_mineiro_carreiro(state: GameState, player: Player) -> None:
    count = sum(1 for u in player.units if u.is_alive())
    player.city.gold += count
    log(state, f"{player.name} (Anoes): Mineiro Carreiro - +{count} Ouro.")


def _humans_roca_de_quilombo(state: GameState, player: Player) -> None:
    num_penas = sum(1 for a in player.field_artifacts if a.card_id == "PENA")
    num_dice = 1 + num_penas
    rolls = [state.rng.randint(1, 4) for _ in range(num_dice)]
    log(state, f"{player.name} (Humanos): Roca - {num_dice}D4 = {rolls}.")
    for r in rolls:
        _apply_roca_result(state, player, r)


def _apply_roca_result(state: GameState, player: Player, result: int) -> None:
    if result == 1:
        player.city.magic += 1
        log(state, "  +1 Magia.")
    elif result == 2:
        player.city.gold += 1
        log(state, "  +1 Ouro.")
    elif result == 3:
        player.pending_heals += 1
        log(state, f"  Cura 2 pendente ({player.pending_heals}).")
    elif result == 4:
        _roca_dano(state, player)


def _roca_dano(state: GameState, player: Player) -> None:
    home = f"city_{player.id}"
    enemies = []
    for other in state.players:
        if other.id == player.id:
            continue
        for u in other.units:
            if u.house == home and u.is_alive():
                enemies.append(u)
    if not enemies:
        log(state, "  Dano: sem inimigos na Cidade.")
        return
    for u in enemies:
        u.life = max(0, u.life - 1)
        log(state, f"  1 dano em {u.id}: {u.life}/{u.life_max}.")
    for other in state.players:
        dead = [u for u in other.units if not u.is_alive()]
        for d in dead:
            log(state, f"  {d.id} morreu (Roca).")
        other.units = [u for u in other.units if u.is_alive()]


def on_unit_moved(state: GameState, player_id: int, unit: Unit) -> None:
    player = get_player(state, player_id)
    if player.people == PEOPLE_FAE:
        player.city.magic += 1
        log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id}.")
        return
    if (player.people == PEOPLE_GNOMOS
            and isinstance(unit, Hero) and unit.hero_id == "sao_tome"):
        effective = sao_tome_effective_peoples(state, player)
        if PEOPLE_FAE in effective:
            player.city.magic += 1
            log(state, f"{player.name} (Sao Tome herda Fadas): +1 Magia ao mover.")


def on_unit_killed_by(state: GameState, killer_player_id: int,
                      dead_unit: Unit, killer_unit: Unit | None = None) -> None:
    killer_player = get_player(state, killer_player_id)
    victim_owner = get_player(state, dead_unit.owner_id)

    if killer_player.people == PEOPLE_FAE and isinstance(killer_unit, Hero):
        if not state.shop.is_empty():
            card = state.shop.draw_random(state.rng)
            killer_player.hand.append(card)
            log(state, f"{killer_player.name} (Fadas): {killer_unit.id} matou "
                       f"{dead_unit.id} e ganhou {card}.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if not heroes.has_ability(u.hero_id, "gain_max_life_on_kill"):
            continue
        if u.house == dead_unit.house:
            ganho = dead_unit.statuses.get("life_at_death", dead_unit.life_max)
            u.life_max += ganho
            log(state, f"  {u.id} (Miyamoto) +{ganho} vida maxima.")

    if killer_player.people == PEOPLE_LOBISOMENS:
        sig = unit_signature(dead_unit)
        if sig not in killer_player.infectados:
            killer_player.infectados.append(sig)
            log(state, f"  {dead_unit.id} infectado pela Maldicao da Lua.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if heroes.has_ability(u.hero_id, "empala_on_kill"):
            sig = unit_signature(dead_unit)
            if sig not in victim_owner.empalados:
                victim_owner.empalados.append(sig)
                log(state, f"  {dead_unit.id} empalado por Dracula (dono {victim_owner.name}).")
            if killer_player.spell_cooldown_until_turn > state.turn:
                killer_player.spell_cooldown_until_turn = 0
                log(state, "  Dracula: feitico sai da recarga.")

    if isinstance(dead_unit, Hero) and dead_unit.hero_id == "baoba_ba":
        victim_owner.baoba_pagamentos = 0
        victim_owner.baoba_invocado = False
        log(state, f"  {victim_owner.name}: Baoba-ba morreu. Pagamentos zerados.")

    if isinstance(dead_unit, Hero):
        for p in state.players:
            for u in p.units:
                if (isinstance(u, Hero) and u.is_alive()
                        and u.hero_id == "cobra"):
                    state.espectros_pendentes.append({
                        "hero_id": dead_unit.hero_id,
                        "house": dead_unit.house,
                        "owner_of_cobra": p.id,
                        "original_owner_id": dead_unit.owner_id,
                    })
                    log(state, f"  Espectro agendado: {dead_unit.hero_id} em {dead_unit.house}.")

    if (isinstance(killer_unit, Hero) and killer_unit.hero_id == "sao_tome"
            and killer_player.people == PEOPLE_GNOMOS):
        effective = sao_tome_effective_peoples(state, killer_player)
        if PEOPLE_VAMPIRES in effective:
            before = killer_unit.life
            killer_unit.life = min(killer_unit.life_max, killer_unit.life + 2)
            if killer_unit.life != before:
                log(state, f"  Sao Tome curou +{killer_unit.life - before} (Sede de Sangue).")
        if PEOPLE_LOBISOMENS in effective:
            sig = unit_signature(dead_unit)
            if sig not in killer_player.infectados:
                killer_player.infectados.append(sig)
                log(state, f"  {dead_unit.id} infectado por Sao Tome (Maldicao da Lua).")

    on_action_performed(state, killer_player_id, "kill")


def has_vovo_bonus(state: GameState, attacker: Unit) -> bool:
    if not isinstance(attacker, Troop):
        return False
    owner = get_player(state, attacker.owner_id)
    for u in owner.units:
        if (isinstance(u, Hero) and u.is_alive()
                and u.hero_id == "vovo_gamba"
                and u.house == attacker.house):
            return True
    return False


def valendar_is_alive(player: Player) -> bool:
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "valendar"
               for u in player.units)


def luna_is_alive(player: Player) -> bool:
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
               for u in player.units)


SUIT_FLIP = {"H": "D", "D": "H", "S": "C", "C": "S"}


def sonho_lucido_flip(card_id: str) -> str:
    from . import artifacts
    d = artifacts.ARTIFACT_CATALOG.get(card_id)
    if d is None or not d.suit:
        return card_id
    other_suit = SUIT_FLIP[d.suit]
    new_id = f"{d.rank}_{other_suit}"
    if new_id in artifacts.ARTIFACT_CATALOG:
        return new_id
    return card_id


def is_lua_cheia(state: GameState, lobisomem_player_id: int) -> bool:
    order = state.turn_order
    if not order:
        return False
    if lobisomem_player_id not in order:
        return False
    idx = order.index(lobisomem_player_id)
    next_pid = order[(idx + 1) % len(order)]
    return state.curuna_id == next_pid


def is_lobisomem_ativo(state: GameState, unit: Unit) -> bool:
    if unit.statuses.get("lobisomem_until_turn", -1) >= state.turn:
        return True
    owner = get_player(state, unit.owner_id)
    if owner.people != PEOPLE_LOBISOMENS:
        return False
    return is_lua_cheia(state, owner.id)


def apply_lua_cheia_effects(state: GameState) -> None:
    for p in state.players:
        if p.people != PEOPLE_LOBISOMENS:
            continue
        if not p.city.is_alive():
            continue
        if not is_lua_cheia(state, p.id):
            continue

        log(state, f"--- LUA CHEIA para {p.name} ---")
        _flip_infected(state, p)

        has_lupa = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "lupa_lider"
                       for u in p.units)
        has_cigana = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "cigana"
                         for u in p.units)
        has_luarado = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luarado"
                          for u in p.units)

        for u in p.units:
            if has_lupa:
                if u.statuses.get("lupa_resist_until_turn", -1) < state.turn:
                    u.resistance_stacks += 1
                    u.statuses["lupa_resist_until_turn"] = state.turn
            if has_cigana:
                u.statuses["invisivel_until_turn"] = state.turn
            if has_luarado and isinstance(u, Hero) and u.hero_id == "luarado":
                u.max_moves_this_turn = 2
                u.has_moved_this_turn = False
                u.moves_this_turn = 0


def _flip_infected(state: GameState, lobisomem: Player) -> None:
    if not lobisomem.infectados:
        return
    sigs_hero = {e["id"] for e in lobisomem.infectados if e["kind"] == "hero"}
    sigs_troop = {e["id"] for e in lobisomem.infectados if e["kind"] == "troop"}

    for other in state.players:
        if other.id == lobisomem.id:
            continue
        if not other.city.is_alive():
            continue
        for u in list(other.units):
            if not u.is_alive():
                continue
            if u.original_owner_id is not None:
                continue
            matches = False
            if isinstance(u, Hero) and u.hero_id in sigs_hero:
                matches = True
            elif isinstance(u, Troop) and u.archetype.value in sigs_troop:
                matches = True
            if not matches:
                continue
            other.units.remove(u)
            lobisomem.units.append(u)
            u.original_owner_id = other.id
            u.owner_id = lobisomem.id
            u.statuses["lobisomem_until_turn"] = state.turn
            log(state, f"  {u.id} ({other.name}) virou Lobisomem (controlado por {lobisomem.name}).")


def apply_cova_rasa(state: GameState) -> None:
    """Amaldicoa todas unidades inimigas na mesma casa da Cova Rasa."""
    for p in state.players:
        for u in p.units:
            if not (isinstance(u, Hero) and u.is_alive() and u.hero_id == "cova_rasa"):
                continue
            if not p.city.is_alive():
                continue
            home = u.house
            total = 0
            for other in state.players:
                if other.id == p.id:
                    continue
                for enemy in other.units:
                    if enemy.house == home and enemy.is_alive():
                        enemy.statuses["amaldicoado_until_turn"] = state.turn
                        total += 1
            log(state, f"{p.name}: Cova Rasa amaldicoou {total} inimigo(s) em {home}.")


def apply_presenca_magnetica(state: GameState) -> None:
    """Joao Grandao forca inimigos da casa a ataca-lo (ordem: maior vida -> menor).
    Consome ataques normais. Joao retalia. Se morrer, restantes cancelam."""
    from .combat import resolve_attack, Attack, CombatError, _effective_max_attacks, _attacks_used

    triggered = [e for e in state.pending_effects
                 if e["kind"] == "JOAO_PRESENCA" and e["due_turn"] == state.turn]
    for e in triggered:
        state.pending_effects.remove(e)
        owner = get_player(state, e["player_id"])
        joao = next((u for u in owner.units
                     if isinstance(u, Hero) and u.is_alive() and u.hero_id == "joao_grandao"),
                    None)
        if joao is None:
            continue
        home = joao.house
        enemies = []
        for other in state.players:
            if other.id == owner.id:
                continue
            for u in other.units:
                if u.house == home and u.is_alive():
                    enemies.append(u)
        enemies.sort(key=lambda u: u.life, reverse=True)
        log(state, f"Presenca Magnetica em {home}: {len(enemies)} inimigo(s) forcado(s).")
        for enemy in enemies:
            if not joao.is_alive():
                log(state, "  Joao morreu - restantes cancelados.")
                break
            if not enemy.is_alive():
                continue
            max_atk = _effective_max_attacks(state, enemy)
            while _attacks_used(enemy) < max_atk:
                if not joao.is_alive():
                    break
                try:
                    resolve_attack(state, Attack(enemy.id, "unit", joao.id))
                except CombatError as ex:
                    log(state, f"  {enemy.id} nao pode atacar: {ex}")
                    break


def magic_cost_reduction(player: Player, state: GameState | None = None) -> int:
    if player.people == PEOPLE_ORCS:
        return 1
    if player.people == PEOPLE_GNOMOS and state is not None:
        if PEOPLE_ORCS in sao_tome_effective_peoples(state, player):
            return 1
    return 0


def hero_summon_cost(player: Player, state: GameState | None = None) -> int:
    if player.people == PEOPLE_GIGANTES:
        return 4
    if player.people == PEOPLE_MORTOS_VIVOS:
        return 2
    if player.people == PEOPLE_GNOMOS and state is not None:
        effective = sao_tome_effective_peoples(state, player)
        if PEOPLE_MORTOS_VIVOS in effective:
            return 2
    return max(0, 3 - magic_cost_reduction(player, state))


def base_troop_slots() -> dict[str, int]:
    return {"light": 1, "medium": 1, "heavy": 1}


def extra_troop_slots(player: Player, state: GameState | None = None) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    if player.people == PEOPLE_MORTOS_VIVOS:
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
               for u in player.units):
            return {"ghoul": 1, "esqueleto": 1}
    if player.people == PEOPLE_GNOMOS and state is not None:
        effective = sao_tome_effective_peoples(state, player)
        result: dict[str, int] = {}
        if PEOPLE_ORCS in effective:
            result["extra"] = 1
        if PEOPLE_MORTOS_VIVOS in effective:
            if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
                   for u in player.units):
                result["ghoul"] = 1
                result["esqueleto"] = 1
        return result
    return {}


def max_troops_of_archetype(player: Player, archetype: TroopArchetype,
                            state: GameState | None = None) -> int:
    base = base_troop_slots().get(archetype.value, 0)
    extras = extra_troop_slots(player, state)
    return base + extras.get(archetype.value, 0)


def available_archetypes(player: Player, state: GameState | None = None) -> list[TroopArchetype]:
    result = [TroopArchetype.LIGHT, TroopArchetype.MEDIUM, TroopArchetype.HEAVY]
    extras = extra_troop_slots(player, state)
    if "extra" in extras:
        result.append(TroopArchetype.EXTRA)
    if "ghoul" in extras:
        result.append(TroopArchetype.GHOUL)
    if "esqueleto" in extras:
        result.append(TroopArchetype.ESQUELETO)
    return result


def compute_hero_max_attacks_in_house(state: GameState, unit: Unit, ability: str) -> int:
    if not (isinstance(unit, Hero) and unit.is_alive()):
        return 1
    if not heroes.has_ability(unit.hero_id, ability):
        return 1
    max_life_house = unit.life
    for p in state.players:
        for u in p.units:
            if u.id == unit.id:
                continue
            if u.house == unit.house and u.is_alive():
                if u.life > max_life_house:
                    max_life_house = u.life
    return 2 if unit.life >= max_life_house else 1


def miyamoto_attacks_remaining(state: GameState, player: Player) -> int:
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto":
            from .combat import _effective_max_attacks
            total = _effective_max_attacks(state, u)
            return max(0, total - u.attacks_made_this_day)
    return 0


def has_7_dwarves_chosen(player: Player) -> bool:
    return player.chosen_hero_id == "seven_dwarves"


def alive_dwarf_count(state: GameState, player: Player) -> int:
    return sum(1 for u in player.units
               if isinstance(u, Hero) and u.is_alive() and heroes.is_seven_dwarf(u.hero_id))
'''

# =============================================================
# 3. actions.py - Luide Vampa fix (typo)
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '    for u in player.units:\n'
    '        if u.is_alive():\n'
    '            u.max_moves_this_turn = max(2, u.max_moves_this_turn)\n'
    '            u.has_moved_this_turn = False\n'
    '            if u.moves_this_turn >= 1:\n'
    '                u.moves_turn_turn = 0\n'
    '                u.moves_this_turn = 0\n'
    '    log(state, f"{player.name}: Luide Vampa ativou movimento noturno.")',
    '    log(state, f"{player.name}: Luide Vampa ativo. Vampiros podem mover/usar '
    'feitico durante a Noite (a UI oferece o prompt).")'
))

# =============================================================
# 4. actions.py - Decompor chama perder muralha
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '    elif kind == "city":\n'
    '        if player.city.life <= 1:\n'
    '            raise ActionError("Cidade ja com 1 de vida.")\n'
    '        player.city.life -= 1\n'
    '        player.city.magic += 3\n'
    '        log(state, f"{player.name}: Decompos muralha (-1 Vida, +3 Magia).")',
    '    elif kind == "city":\n'
    '        if player.city.life <= 1:\n'
    '            raise ActionError("Cidade ja com 1 de vida.")\n'
    '        player.city.life -= 1\n'
    '        player.city.magic += 3\n'
    '        peoples.on_action_performed(state, player_id, "lose_city_life")\n'
    '        log(state, f"{player.name}: Decompos muralha (-1 Vida, +3 Magia).")'
))

# =============================================================
# 5. main.py - Ainai usa fae_fallen_this_turn, antes E depois
# =============================================================
EDITS.append((
    "jessica/main.py",
    'def _try_ainai_teleport(state, player) -> bool:\n'
    '    ainai = next((u for u in player.units\n'
    '                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "ainai"), None)\n'
    '    if ainai is None:\n'
    '        return False\n'
    '    if ainai.statuses.get("ainai_used_this_night") == state.turn:\n'
    '        return False\n'
    '    if not state.deaths_this_night:\n'
    '        return False\n'
    '    casas = [h for h in state.deaths_this_night if h != ainai.house]\n'
    '    if not casas:\n'
    '        return False\n'
    '    console.print("[yellow]Ainai pode teletransportar para casa com morte nesta Noite.[/yellow]")\n'
    '    labels = [house_short(state, h) for h in casas]\n'
    '    idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)\n'
    '    if idx == 0:\n'
    '        return False\n'
    '    destino = casas[idx - 1]\n'
    '    ainai.house = destino\n'
    '    ainai.statuses["ainai_used_this_night"] = state.turn\n'
    '    player.city.magic += 1\n'
    '    console.print(f"[green]Ainai teleportou para {house_short(state, destino)} (+1 Magia).[/green]")\n'
    '    return True',
    'def _try_ainai_teleport(state, player) -> bool:\n'
    '    ainai = next((u for u in player.units\n'
    '                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "ainai"), None)\n'
    '    if ainai is None:\n'
    '        return False\n'
    '    if ainai.statuses.get("ainai_used_turn") == state.turn:\n'
    '        return False\n'
    '    # Apenas fadas ALIADAS caidas neste turno (nao necessariamente nesta noite)\n'
    '    casas_alvo = set()\n'
    '    for oid, h in state.fae_fallen_this_turn:\n'
    '        if oid != ainai.owner_id:\n'
    '            continue\n'
    '        if h == ainai.house:\n'
    '            continue\n'
    '        casas_alvo.add(h)\n'
    '    if not casas_alvo:\n'
    '        return False\n'
    '    casas = sorted(casas_alvo)\n'
    '    console.print("[yellow]Ainai pode teletransportar para casa com fada aliada caida neste turno.[/yellow]")\n'
    '    labels = [house_short(state, h) for h in casas]\n'
    '    idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)\n'
    '    if idx == 0:\n'
    '        return False\n'
    '    destino = casas[idx - 1]\n'
    '    ainai.house = destino\n'
    '    ainai.statuses["ainai_used_turn"] = state.turn\n'
    '    player.city.magic += 1\n'
    '    console.print(f"[green]Ainai teleportou para {house_short(state, destino)} (+1 Magia).[/green]")\n'
    '    return True'
))

# =============================================================
# 6. main.py - run_night_phase refeito (Ainai antes/depois, Luide)
# =============================================================
EDITS.append((
    "jessica/main.py",
    'def run_night_phase(state) -> None:\n'
    '    console.rule("[bold]NOITE[/bold]")\n'
    '    show_map(state)\n'
    '    # H8: ver mapa / estudar campo antes das declaracoes\n'
    '    while True:\n'
    '        opt = Prompt.ask(\n'
    '            "Antes das declaracoes: [m]apa / [v] estudar campo / [Enter] continuar",\n'
    '            default="")\n'
    '        if opt == "m":\n'
    '            show_map(state)\n'
    '        elif opt == "v":\n'
    '            estudar_campo(state)\n'
    '        else:\n'
    '            break\n'
    '    _ask_vovo_position(state)\n'
    '\n'
    '    # Luna prompt (antes das declaracoes)\n'
    '    all_pids = list(day_order(state))\n'
    '    for pid in all_pids:\n'
    '        player = get_player(state, pid)\n'
    '        _try_luna_return(state, player)\n'
    '\n'
    '    for pid in all_pids:\n'
    '        player = get_player(state, pid)\n'
    '        if player.units:\n'
    '            _try_ainai_teleport(state, player)\n'
    '            _try_besouro_mandinga(state, player)\n'
    '\n'
    '    house_order = [CENTER, "city_4", "city_3", "city_2", "city_1"]\n'
    '    for house in house_order:\n'
    '        pids_here = []\n'
    '        for pid in all_pids:\n'
    '            player = get_player(state, pid)\n'
    '            if any(u.house == house and u.is_alive() for u in player.units):\n'
    '                pids_here.append(pid)\n'
    '        if not pids_here:\n'
    '            continue\n'
    '        pids_here = _order_players_for_house(state, pids_here, house)\n'
    '        for pid in pids_here:\n'
    '            player = get_player(state, pid)\n'
    '            units_here = [u for u in player.units if u.house == house and u.is_alive()]\n'
    '            if not units_here:\n'
    '                continue\n'
    '            if not any(find_targets(state, u) for u in units_here):\n'
    '                continue\n'
    '            console.print(f"[bold]{player.name} declara ataques em {house_short(state, house)}.[/bold]")\n'
    '            for unit in list(units_here):\n'
    '                if not unit.is_alive():\n'
    '                    continue\n'
    '                while True:\n'
    '                    targets = find_targets(state, unit)\n'
    '                    if not targets:\n'
    '                        break\n'
    '                    if _attacks_used(unit) >= _effective_max_attacks(state, unit):\n'
    '                        break\n'
    '                    atk = prompt_attack(state, unit, targets)\n'
    '                    if not atk:\n'
    '                        break\n'
    '                    before = len(state.event_log)\n'
    '                    try:\n'
    '                        resolve_attack(state, atk)\n'
    '                    except CombatError as e:\n'
    '                        console.print(f"  [red]Erro: {e}[/red]")\n'
    '                        break\n'
    '                    for line in state.event_log[before:]:\n'
    '                        console.print(f"  {line}")\n'
    '            console.print()',
    'def _luide_janela_noturna(state, all_pids):\n'
    '    """Oferece mover/usar feitico para vampiros com Luide vivo."""\n'
    '    for pid in all_pids:\n'
    '        player = get_player(state, pid)\n'
    '        if player.people != "vampiros":\n'
    '            continue\n'
    '        luide = next((u for u in player.units\n'
    '                      if isinstance(u, Hero) and u.is_alive()\n'
    '                      and u.hero_id == "luide_vampa"), None)\n'
    '        if luide is None:\n'
    '            continue\n'
    '        while True:\n'
    '            disponiveis = [u for u in player.units\n'
    '                           if u.is_alive() and u.moves_this_turn < u.max_moves_this_turn]\n'
    '            opts = []\n'
    '            if disponiveis:\n'
    '                opts.append("Mover unidade")\n'
    '            if not player.has_cast_spell_this_turn:\n'
    '                opts.append("Lancar feitico")\n'
    '            opts.append("(continuar)")\n'
    '            if len(opts) == 1:\n'
    '                break\n'
    '            idx = pick_index(f"{player.name} (Luide Vampa)", opts)\n'
    '            escolha = opts[idx]\n'
    '            if escolha == "(continuar)":\n'
    '                break\n'
    '            if escolha == "Mover unidade":\n'
    '                labels = [f"{u.id} ({house_short(state, u.house)}, {u.life})"\n'
    '                          for u in disponiveis]\n'
    '                u = disponiveis[pick_index("Unidade", labels)]\n'
    '                dests = valid_destinations(state, u)\n'
    '                if not dests:\n'
    '                    console.print("[red]Sem destinos.[/red]")\n'
    '                    continue\n'
    '                labels2 = ["Cancelar"] + [house_short(state, d) for d in dests]\n'
    '                idx2 = pick_index("Destino", labels2)\n'
    '                if idx2 == 0:\n'
    '                    continue\n'
    '                try:\n'
    '                    move_unit(state, pid, u.id, dests[idx2 - 1])\n'
    '                    console.print("[green]Movido.[/green]")\n'
    '                except ActionError as e:\n'
    '                    console.print(f"[red]{e}[/red]")\n'
    '            elif escolha == "Lancar feitico":\n'
    '                try:\n'
    '                    choice_data = {}\n'
    '                    if not player.units:\n'
    '                        raise ActionError("Sem unidades.")\n'
    '                    labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]\n'
    '                    choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id\n'
    '                    cast_spell(state, pid, choice_data)\n'
    '                    console.print("[green]Feitico lancado.[/green]")\n'
    '                except (ActionError, ValueError) as e:\n'
    '                    console.print(f"[red]{e}[/red]")\n'
    '\n'
    '\n'
    'def _ainai_prompt_all(state, all_pids):\n'
    '    for pid in all_pids:\n'
    '        player = get_player(state, pid)\n'
    '        if player.units:\n'
    '            _try_ainai_teleport(state, player)\n'
    '\n'
    '\n'
    'def run_night_phase(state) -> None:\n'
    '    console.rule("[bold]NOITE[/bold]")\n'
    '    show_map(state)\n'
    '    while True:\n'
    '        opt = Prompt.ask(\n'
    '            "Antes das declaracoes: [m]apa / [v] estudar campo / [Enter] continuar",\n'
    '            default="")\n'
    '        if opt == "m":\n'
    '            show_map(state)\n'
    '        elif opt == "v":\n'
    '            estudar_campo(state)\n'
    '        else:\n'
    '            break\n'
    '    _ask_vovo_position(state)\n'
    '\n'
    '    all_pids = list(day_order(state))\n'
    '    for pid in all_pids:\n'
    '        player = get_player(state, pid)\n'
    '        _try_luna_return(state, player)\n'
    '\n'
    '    # Ainai: ANTES\n'
    '    _ainai_prompt_all(state, all_pids)\n'
    '    # Luide: janela noturna antes\n'
    '    _luide_janela_noturna(state, all_pids)\n'
    '\n'
    '    for pid in all_pids:\n'
    '        player = get_player(state, pid)\n'
    '        if player.units:\n'
    '            _try_besouro_mandinga(state, player)\n'
    '\n'
    '    house_order = [CENTER, "city_4", "city_3", "city_2", "city_1"]\n'
    '    for house in house_order:\n'
    '        pids_here = []\n'
    '        for pid in all_pids:\n'
    '            player = get_player(state, pid)\n'
    '            if any(u.house == house and u.is_alive() for u in player.units):\n'
    '                pids_here.append(pid)\n'
    '        if not pids_here:\n'
    '            continue\n'
    '        pids_here = _order_players_for_house(state, pids_here, house)\n'
    '        for pid in pids_here:\n'
    '            player = get_player(state, pid)\n'
    '            units_here = [u for u in player.units if u.house == house and u.is_alive()]\n'
    '            if not units_here:\n'
    '                continue\n'
    '            if not any(find_targets(state, u) for u in units_here):\n'
    '                continue\n'
    '            console.print(f"[bold]{player.name} declara ataques em {house_short(state, house)}.[/bold]")\n'
    '            for unit in list(units_here):\n'
    '                if not unit.is_alive():\n'
    '                    continue\n'
    '                while True:\n'
    '                    targets = find_targets(state, unit)\n'
    '                    if not targets:\n'
    '                        break\n'
    '                    if _attacks_used(unit) >= _effective_max_attacks(state, unit):\n'
    '                        break\n'
    '                    atk = prompt_attack(state, unit, targets)\n'
    '                    if not atk:\n'
    '                        break\n'
    '                    before = len(state.event_log)\n'
    '                    try:\n'
    '                        resolve_attack(state, atk)\n'
    '                    except CombatError as e:\n'
    '                        console.print(f"  [red]Erro: {e}[/red]")\n'
    '                        break\n'
    '                    for line in state.event_log[before:]:\n'
    '                        console.print(f"  {line}")\n'
    '            console.print()\n'
    '\n'
    '        # Luide: janela entre casas (apos cada casa)\n'
    '        _luide_janela_noturna(state, all_pids)\n'
    '        # Ainai: nova chance a cada casa\n'
    '        _ainai_prompt_all(state, all_pids)\n'
    '\n'
    '    # Ainai: DEPOIS de tudo\n'
    '    _ainai_prompt_all(state, all_pids)'
))


def _apply_edits(rel_path: str, full: Path, backup_dir: Path) -> bool:
    if not full.exists():
        print(f"AVISO - {rel_path} nao existe.")
        return False
    original = full.read_text(encoding="utf-8")
    current = original
    applied = 0
    for path, old, new in EDITS:
        if path != rel_path:
            continue
        if old not in current:
            print(f"  AVISO - snippet nao encontrado em {rel_path}:")
            print(f"    {old[:90]}...")
            continue
        current = current.replace(old, new, 1)
        applied += 1
    if current == original:
        print(f"AVISO - nenhuma edicao aplicada em {rel_path}.")
        return False
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(current, encoding="utf-8")
    print(f"OK  - {rel_path} ({applied} edit(s))")
    return True


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for rel_path, content in FILES.items():
        full = ROOT / rel_path
        if full.exists():
            backup_path = BACKUP_DIR / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, backup_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        print(f"OK  - {rel_path} (rewrite)")
        written += 1

    edited_paths = sorted({e[0] for e in EDITS})
    for rel_path in edited_paths:
        full = ROOT / rel_path
        if _apply_edits(rel_path, full, BACKUP_DIR):
            written += 1

    print(f"\n{written} arquivo(s) modificado(s).")
    print(f"Backup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()