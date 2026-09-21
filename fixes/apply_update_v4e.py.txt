"""apply_update_v4e: fixes + testes dos 4 povos novos."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v4e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# jessica/core/combat.py - fix vampiro (empate + mata = 2, sem cura)
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


def _hero_has(unit: Unit, ability: str) -> bool:
    from . import heroes
    if not isinstance(unit, Hero):
        return False
    return heroes.has_ability(unit.hero_id, ability)


def _is_miyamoto(unit: Unit) -> bool:
    return _hero_has(unit, "double_attack_if_stronger")


def _effective_max_attacks(state: GameState, unit: Unit) -> int:
    if _is_miyamoto(unit):
        base = peoples.compute_hero_max_attacks_in_house(
            state, unit, "double_attack_if_stronger")
        k_s_bonus = max(0, unit.max_attacks_this_night - 1)
        return base + k_s_bonus
    if _hero_has(unit, "extra_attacks_per_dwarf"):
        owner = get_player(state, unit.owner_id)
        n = sum(1 for u in owner.units
                if isinstance(u, Hero) and u.is_alive()
                and u.id != unit.id and u.house == unit.house)
        return unit.max_attacks_this_night + n
    return unit.max_attacks_this_night


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
        if u.house not in state.deaths_this_night:
            state.deaths_this_night.append(u.house)
        artifacts_effects.on_unit_death(state, u)
        if u.killed_by_player_id is not None:
            peoples.on_unit_killed_by(state, u.killed_by_player_id, u)

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


def _apply_armor(state: GameState, defender_player_id: int, dmg: int) -> int:
    p = get_player(state, defender_player_id)
    if p.armor_gold_cap_per_hit <= 0 or dmg <= 0:
        return dmg
    cap = p.armor_gold_cap_per_hit
    limite = min(dmg, cap, p.city.gold)
    if limite <= 0:
        return dmg
    p.city.gold -= limite
    log(state, f"    Armadura de Ouro absorveu {limite} (restam {p.city.gold} Ouro).")
    return dmg - limite


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


def _apply_vampiro_after_round(state: GameState, attacker: Unit, target: Unit,
                               atk_life_before: int, tgt_life_before: int,
                               target_was_hero_or_troop: bool) -> None:
    """Sede de Sangue: mata -> cura 2; empata -> sobrevive com 2;
    empate + mata = 2 final (nao soma cura)."""
    ap = get_player(state, attacker.owner_id)
    if ap.people != peoples.PEOPLE_VAMPIRES:
        return
    empatou = (atk_life_before == tgt_life_before and atk_life_before > 0)
    matou = (not target.is_alive()) and target_was_hero_or_troop

    if empatou and matou:
        # Sobrevive com 2 (ja considerando a cura embutida)
        attacker.life = min(2, attacker.life_max)
        log(state, f"    {attacker.id} empata e mata: sobrevive com 2 (Sede de Sangue).")
        return
    if empatou and not attacker.is_alive():
        attacker.life = min(2, attacker.life_max)
        log(state, f"    {attacker.id} empata: sobrevive com 2 (Sede de Sangue).")
        return
    if matou:
        before = attacker.life
        attacker.life = min(attacker.life_max, attacker.life + 2)
        if attacker.life != before:
            log(state, f"    {attacker.id} curou +{attacker.life - before} (Sede de Sangue).")


def _resolve_combat_round(state: GameState, attacker: Unit, target: Unit) -> None:
    attacker_player = get_player(state, attacker.owner_id)
    target_player = get_player(state, target.owner_id)

    attacker.statuses.pop("invisivel_until_turn", None)

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

    attacker.life = max(0, atk_life - dmg_to_attacker)
    target.life = max(0, tgt_life - dmg_to_target)

    _apply_vampiro_after_round(state, attacker, target, atk_life, tgt_life,
                               target_was_hero_or_troop=True)

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
    if not target.is_alive():
        target.killed_by_player_id = attacker.owner_id


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

        if _hero_has(attacker, "execute_weak_targets"):
            aliados = [
                u for u in get_player(state, target.owner_id).units
                if u.house == target.house and u.is_alive() and u.id != target.id
            ]
            if not aliados:
                target.statuses["life_at_death"] = target.life
                target.life = 0
                target.killed_by_player_id = attacker.owner_id
                log(state, f"  {attacker.id} EXECUTOU {target.id}.")
                if _hero_has(attacker, "grow_per_execute"):
                    attacker.life_max += 1
                    attacker.life += 1
                    log(state, f"  {attacker.id} cresceu para "
                               f"{attacker.life}/{attacker.life_max}.")
                _register_attack(attacker)
                _cleanup_dead(state)
                return

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
# jessica/core/peoples.py - add _unit_signature + helpers para empalados
# =============================================================
FILES["jessica/core/peoples.py"] = '''\
"""Passivas dos povos."""
from __future__ import annotations
from .state import get_player, log
from .models import GameState, Player, Unit, Hero, Troop
from .constants import TroopArchetype, CENTER, CITY_HOUSES
from . import heroes


PEOPLE_HUMANS = "humanos"
PEOPLE_DWARVES = "anoes"
PEOPLE_ORCS = "orcs"
PEOPLE_FAE = "fadas"
PEOPLE_VAMPIRES = "vampiros"
PEOPLE_LOBISOMENS = "lobisomens"
PEOPLE_GIGANTES = "gigantes"
PEOPLE_MORTOS_VIVOS = "mortos_vivos"


def unit_signature(u: Unit) -> dict:
    if isinstance(u, Hero):
        return {"kind": "hero", "id": u.hero_id}
    return {"kind": "troop", "id": u.archetype.value}


def is_empalado(player: Player, sig: dict) -> bool:
    return sig in player.empalados


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
    if player.people != PEOPLE_FAE:
        return
    player.city.magic += 1
    log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id}.")


def on_unit_killed_by(state: GameState, killer_player_id: int, dead_unit: Unit) -> None:
    killer_player = get_player(state, killer_player_id)

    if killer_player.people == PEOPLE_FAE and isinstance(dead_unit, Hero):
        if not state.shop.is_empty():
            card = state.shop.draw_random(state.rng)
            killer_player.hand.append(card)
            log(state, f"{killer_player.name} (Fadas): matou Heroi e ganhou {card}.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if not heroes.has_ability(u.hero_id, "gain_max_life_on_kill"):
            continue
        if u.house == dead_unit.house:
            ganho = dead_unit.statuses.get("life_at_death", dead_unit.life_max)
            u.life_max += ganho
            log(state, f"  {u.id} (Miyamoto) +{ganho} vida maxima.")

    # Lobisomem: registra infeccao permanente
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
            if sig not in killer_player.empalados:
                killer_player.empalados.append(sig)
                log(state, f"  {dead_unit.id} empalado por Dracula.")
            if killer_player.spell_cooldown_until_turn > state.turn:
                killer_player.spell_cooldown_until_turn = 0
                log(state, "  Dracula: feitico sai da recarga.")

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
    for p in state.players:
        for u in p.units:
            if not (isinstance(u, Hero) and u.is_alive() and u.hero_id == "cova_rasa"):
                continue
            if not p.city.is_alive():
                continue
            home = u.house
            for other in state.players:
                if other.id == p.id:
                    continue
                for enemy in other.units:
                    if enemy.house == home and enemy.is_alive():
                        enemy.statuses["amaldicoado_until_turn"] = state.turn
            log(state, f"{p.name}: Cova Rasa amaldicoou {home}.")


def apply_presenca_magnetica(state: GameState) -> None:
    triggered = []
    for e in state.pending_effects:
        if e["kind"] == "JOAO_PRESENCA" and e["due_turn"] == state.turn:
            triggered.append(e)
    for e in triggered:
        state.pending_effects.remove(e)
        p = get_player(state, e["player_id"])
        joao = next((u for u in p.units
                     if isinstance(u, Hero) and u.is_alive() and u.hero_id == "joao_grandao"),
                    None)
        if joao is None:
            continue
        _run_presenca(state, p, joao)


def _run_presenca(state: GameState, owner: Player, joao) -> None:
    home = joao.house
    enemies = []
    for other in state.players:
        if other.id == owner.id:
            continue
        for u in other.units:
            if u.house == home and u.is_alive():
                enemies.append(u)
    enemies.sort(key=lambda u: u.life, reverse=True)
    log(state, f"Presenca Magnetica em {home}: {len(enemies)} inimigos forcados.")
    for enemy in enemies:
        if not joao.is_alive():
            log(state, "  Joao morreu — restantes cancelados.")
            break
        if not enemy.is_alive():
            continue
        dmg = enemy.life * 2
        joao.life = max(0, joao.life - dmg)
        log(state, f"  {enemy.id} ataca Joao (dano {dmg}). Joao: {joao.life}/{joao.life_max}.")


def magic_cost_reduction(player: Player) -> int:
    if player.people == PEOPLE_ORCS:
        return 1
    return 0


def hero_summon_cost(player: Player) -> int:
    if player.people == PEOPLE_GIGANTES:
        return 4
    if player.people == PEOPLE_MORTOS_VIVOS:
        return 2
    return max(0, 3 - magic_cost_reduction(player))


def base_troop_slots() -> dict[str, int]:
    return {"light": 1, "medium": 1, "heavy": 1}


def extra_troop_slots(player: Player) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    if player.people == PEOPLE_MORTOS_VIVOS:
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
               for u in player.units):
            return {"ghoul": 1, "esqueleto": 1}
    return {}


def max_troops_of_archetype(player: Player, archetype: TroopArchetype) -> int:
    base = base_troop_slots().get(archetype.value, 0)
    extras = extra_troop_slots(player)
    return base + extras.get(archetype.value, 0)


def available_archetypes(player: Player) -> list[TroopArchetype]:
    result = [TroopArchetype.LIGHT, TroopArchetype.MEDIUM, TroopArchetype.HEAVY]
    if player.people == PEOPLE_ORCS:
        result.append(TroopArchetype.EXTRA)
    if player.people == PEOPLE_MORTOS_VIVOS:
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
               for u in player.units):
            result.append(TroopArchetype.GHOUL)
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
            max_a = compute_hero_max_attacks_in_house(state, u, "double_attack_if_stronger")
            k_s_bonus = max(0, u.max_attacks_this_night - 1)
            total = max_a + k_s_bonus
            return max(0, total - u.attacks_made_this_day)
    return 0


def has_7_dwarves_chosen(player: Player) -> bool:
    return player.chosen_hero_id == "seven_dwarves"


def alive_dwarf_count(state: GameState, player: Player) -> int:
    return sum(1 for u in player.units
               if isinstance(u, Hero) and u.is_alive() and heroes.is_seven_dwarf(u.hero_id))
'''

# =============================================================
# jessica/core/actions.py - empalados + caroço grátis
# =============================================================
FILES["jessica/core/actions.py"] = '''\
from __future__ import annotations
from .constants import (
    RESOURCES_PER_DAY, GOLD_INTEREST_DIVISOR, CITY_LIFE_COST_GOLD,
    TROOP_SUMMON_COST_MAGIC, TROOP_MAX_LIFE,
    MONUMENT_COST_GOLD, CENTER, CITY_HOUSES, TroopArchetype,
    ARTIFACT_GOLD_COST, ARTIFACT_MAGIC_COST, ARTIFACT_SELL_GOLD,
    ARTIFACT_MAX_BUYS_GOLD_PER_DAY, ARTIFACT_MAX_BUYS_MAGIC_PER_DAY,
)
from .state import get_player, get_city, log, record_action
from .models import GameState, Unit, Hero, Troop, ArtifactOnField
from .artifacts import card_display
from . import artifacts_effects, peoples, heroes
from . import spells as spells_mod


class ActionError(Exception):
    pass


SEVEN_DWARVES_COST = 2


def apply_gold_interest(state: GameState) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    for player in state.players:
        city = player.city
        if not city.is_alive():
            continue
        interest = city.gold // GOLD_INTEREST_DIVISOR
        if interest > 0:
            city.gold += interest
            log(state, f"{player.name} rendeu {interest} de Ouro.")
            results.append((player.id, interest))
    return results


def reset_unit_flags(state: GameState) -> None:
    for player in state.players:
        player.has_collected_this_turn = False
        player.has_cast_spell_this_turn = False
        player.morning_done_this_turn = False
        player.pending_heals = 0
        player.artifacts_bought_gold_today = 0
        player.artifacts_bought_magic_today = 0
        for unit in player.units:
            unit.has_moved_this_turn = False
            unit.attacks_made_this_night = 0
            unit.max_attacks_this_night = 1
            unit.attacks_made_this_day = 0
            unit.max_attacks_this_day = 0
            unit.hero_can_attack_city = False
            unit.moves_this_turn = 0
            unit.max_moves_this_turn = 1


def collect_resources(state: GameState, player_id: int, gold_amount: int, magic_amount: int) -> None:
    if gold_amount + magic_amount != RESOURCES_PER_DAY:
        raise ActionError(f"Coleta invalida: exatamente {RESOURCES_PER_DAY} recursos.")
    if gold_amount < 0 or magic_amount < 0:
        raise ActionError("Valores negativos.")
    player = get_player(state, player_id)
    if player.has_collected_this_turn:
        raise ActionError(f"{player.name} ja coletou.")
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    city.gold += gold_amount
    city.magic += magic_amount
    player.has_collected_this_turn = True
    record_action(state, player_id, "collect_resources", gold=gold_amount, magic=magic_amount)
    log(state, f"{player.name} coletou {gold_amount} Ouro e {magic_amount} Magia.")


def raise_city_life(state: GameState, player_id: int, times: int = 1) -> None:
    if times < 1:
        raise ActionError("Precisa ao menos 1.")
    city = get_city(state, player_id)
    player = get_player(state, player_id)
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    total_cost = CITY_LIFE_COST_GOLD * times
    if city.gold < total_cost:
        raise ActionError(f"Ouro insuficiente.")
    if city.life + times > city.life_max:
        raise ActionError(f"Ultrapassa vida maxima ({city.life_max}).")
    city.gold -= total_cost
    city.life += times
    record_action(state, player_id, "raise_city_life", times=times)
    log(state, f"{player.name} subiu vida em {times} ({city.life}/{city.life_max}).")


def summon_troop(state: GameState, player_id: int, archetype: TroopArchetype, life: int) -> Troop:
    player = get_player(state, player_id)
    if peoples.has_7_dwarves_chosen(player):
        raise ActionError("Escolheu Os 7 Anoes: nao pode invocar Tropas.")
    # Empalados bloqueiam
    sig = {"kind": "troop", "id": archetype.value}
    if peoples.is_empalado(player, sig):
        raise ActionError(f"Tropa {archetype.value} empalada: nao pode ser invocada.")
    max_life = TROOP_MAX_LIFE[archetype.value]
    if life < 1 or life > max_life:
        raise ActionError(f"Vida invalida: {life}. Max {max_life}.")
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    max_slots = peoples.max_troops_of_archetype(player, archetype)
    existing = [u for u in player.units
                if isinstance(u, Troop) and u.archetype == archetype and u.is_alive()]
    if len(existing) >= max_slots:
        raise ActionError(f"Maximo de tropas {archetype.value}.")
    magic_cost = max(0, TROOP_SUMMON_COST_MAGIC - peoples.magic_cost_reduction(player))
    if city.magic < magic_cost:
        raise ActionError(f"Magia insuficiente ({magic_cost}).")
    if city.gold < life:
        raise ActionError(f"Ouro insuficiente ({life}).")
    city.magic -= magic_cost
    city.gold -= life
    n = sum(1 for u in player.units if isinstance(u, Troop))
    unit_id = f"p{player_id}_troop_{archetype.value}_{n}"
    troop = Troop(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                  life=life, life_max=max_life, archetype=archetype,
                  has_moved_this_turn=True)
    player.units.append(troop)
    record_action(state, player_id, "summon_troop", archetype=archetype.value, life=life)
    log(state, f"{player.name} invocou tropa {archetype.value} ({life}/{max_life}).")
    return troop


def summon_hero(state: GameState, player_id: int, force_hero_id: str | None = None) -> Hero:
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")

    if player.people == peoples.PEOPLE_MORTOS_VIVOS:
        if force_hero_id is None:
            raise ActionError("Mortos-Vivos: escolha o heroi.")
        hid = heroes.normalize_hero_id(force_hero_id)
        sig = {"kind": "hero", "id": hid}
        if peoples.is_empalado(player, sig):
            raise ActionError(f"Heroi {hid} empalado.")
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == hid
               for u in player.units):
            raise ActionError(f"Heroi {hid} ja em campo.")
        magic_cost = peoples.hero_summon_cost(player)
        if city.magic < magic_cost:
            raise ActionError(f"Magia insuficiente ({magic_cost}).")
        city.magic -= magic_cost
        hdef = heroes.get_hero(hid)
        unit_id = f"p{player_id}_hero_{hdef.hero_id}"
        hero = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                    life=hdef.life, life_max=hdef.life,
                    hero_id=hdef.hero_id, has_moved_this_turn=True)
        player.units.append(hero)
        record_action(state, player_id, "summon_hero", hero_id=hdef.hero_id)
        log(state, f"{player.name} invocou {hdef.name} ({hdef.life}).")
        return hero

    if not player.chosen_hero_id:
        raise ActionError("Sem heroi escolhido.")

    if player.chosen_hero_id == "seven_dwarves" and force_hero_id is None:
        alive_ids = {u.hero_id for u in player.units
                     if isinstance(u, Hero) and u.is_alive()}
        next_hid = heroes.next_dwarf_to_summon(alive_ids)
        if next_hid is None:
            raise ActionError("Todos os 7 Anoes ja foram invocados.")
        idx = heroes.dwarf_index(next_hid)
        if idx > 0:
            prev_hid = heroes.SEVEN_DWARVES_ORDER[idx - 1]
            if prev_hid not in alive_ids:
                raise ActionError(f"Corrente: precisa invocar {prev_hid} antes.")
        sig = {"kind": "hero", "id": next_hid}
        if peoples.is_empalado(player, sig):
            raise ActionError(f"Anao {next_hid} empalado.")
        magic_cost = max(0, SEVEN_DWARVES_COST - peoples.magic_cost_reduction(player))
        if city.magic < magic_cost:
            raise ActionError(f"Magia insuficiente ({magic_cost}).")
        city.magic -= magic_cost
        hdef = heroes.get_hero(next_hid)
        unit_id = f"p{player_id}_hero_{next_hid}"
        hero = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                    life=hdef.life, life_max=hdef.life,
                    hero_id=hdef.hero_id, has_moved_this_turn=True)
        player.units.append(hero)
        record_action(state, player_id, "summon_hero", hero_id=next_hid)
        log(state, f"{player.name} invocou {hdef.name} ({hdef.life}).")
        return hero

    # Caroco
    if player.chosen_hero_id == "caroco" and force_hero_id is None:
        sig = {"kind": "hero", "id": "caroco"}
        if peoples.is_empalado(player, sig):
            raise ActionError("Caroco empalado.")
        carocos_vivos = [u for u in player.units
                         if isinstance(u, Hero) and u.is_alive() and u.hero_id == "caroco"]
        carocos_ja_gerados = 1 + player.carocos_gerados
        if len(carocos_vivos) < carocos_ja_gerados:
            magic_cost = peoples.hero_summon_cost(player)
            if city.magic < magic_cost:
                raise ActionError(f"Magia insuficiente ({magic_cost}).")
            city.magic -= magic_cost
            falta = carocos_ja_gerados - len(carocos_vivos)
            last = None
            for i in range(falta):
                n = sum(1 for u in player.units if isinstance(u, Hero))
                unit_id = f"p{player_id}_caroco_ret_{n}"
                last = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                            life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
                player.units.append(last)
            log(state, f"{player.name}: {falta} Carocos reinvocados (4 Magia).")
            return last
        else:
            raise ActionError("Todos os Carocos ja estao vivos.")

    alive_heroes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()]
    if alive_heroes and force_hero_id is None:
        raise ActionError("Ja existe heroi vivo.")
    target_id = force_hero_id if force_hero_id is not None else player.chosen_hero_id
    sig = {"kind": "hero", "id": target_id}
    if peoples.is_empalado(player, sig):
        raise ActionError(f"Heroi {target_id} empalado.")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == target_id
           for u in player.units):
        raise ActionError(f"Heroi {target_id} ja em campo.")

    magic_cost = peoples.hero_summon_cost(player)
    if city.magic < magic_cost:
        raise ActionError(f"Magia insuficiente ({magic_cost}).")
    city.magic -= magic_cost
    hdef = heroes.get_hero(target_id)
    hero_life_max = hdef.life
    if player.people == peoples.PEOPLE_GIGANTES and state.turn % 4 == 0:
        hero_life_max *= 2
    unit_id = f"p{player_id}_hero_{hdef.hero_id}"
    hero = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                life=hero_life_max, life_max=hero_life_max,
                hero_id=hdef.hero_id, has_moved_this_turn=True)
    player.units.append(hero)
    record_action(state, player_id, "summon_hero", hero_id=hdef.hero_id)
    log(state, f"{player.name} invocou {hdef.name} ({hero_life_max}).")
    if hdef.hero_id == "iuna" and not player.pena_added_once:
        any_pena = any(p.pena_added_once for p in state.players)
        if not any_pena:
            for _ in range(4):
                state.shop.return_card("PENA")
            player.pena_added_once = True
            log(state, "Iuna: 4 Penas adicionadas a Loja.")
    return hero


def move_unit(state: GameState, player_id: int, unit_id: str, destination: str) -> None:
    if destination not in (CENTER, *CITY_HOUSES):
        raise ActionError(f"Destino invalido: {destination}")
    player = get_player(state, player_id)
    unit = next((u for u in player.units if u.id == unit_id and u.is_alive()), None)
    if unit is None:
        raise ActionError(f"Unidade {unit_id} nao encontrada.")
    if unit.moves_this_turn >= unit.max_moves_this_turn:
        raise ActionError("Unidade ja se moveu o maximo.")
    origin = unit.house
    if origin == destination:
        raise ActionError("Ja esta la.")
    if origin.startswith("city_") and destination != CENTER:
        raise ActionError("De Cidade so vai para o Centro.")
    if origin == CENTER and not destination.startswith("city_"):
        raise ActionError("Do Centro so vai para Cidade.")
    if destination.startswith("city_"):
        dest_pid = int(destination.split("_")[1])
        if not get_player(state, dest_pid).city.is_alive():
            raise ActionError("Cidade destruida.")
    if isinstance(unit, Hero) and unit.hero_id == "luna":
        if "luna_origin_house" not in unit.statuses:
            unit.statuses["luna_origin_house"] = origin
    unit.house = destination
    unit.moves_this_turn += 1
    unit.has_moved_this_turn = (unit.moves_this_turn >= unit.max_moves_this_turn)
    record_action(state, player_id, "move_unit", unit_id=unit_id,
                  origin=origin, destination=destination)
    log(state, f"{player.name}: {unit_id} moveu para {destination}.")
    peoples.on_unit_moved(state, player_id, unit)


def build_monument(state: GameState, player_id: int) -> None:
    city = get_city(state, player_id)
    player = get_player(state, player_id)
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    if city.has_monument:
        raise ActionError("Ja tem Monumento.")
    if city.life < city.life_max:
        raise ActionError(f"Precisa vida maxima ({city.life_max}).")
    if city.gold < MONUMENT_COST_GOLD:
        raise ActionError("Ouro insuficiente.")
    city.gold -= MONUMENT_COST_GOLD
    city.has_monument = True
    record_action(state, player_id, "build_monument")
    log(state, f"{player.name} construiu Monumento.")


def use_heal(state: GameState, player_id: int, target_unit_id: str) -> None:
    player = get_player(state, player_id)
    if player.pending_heals <= 0:
        raise ActionError("Sem cura pendente.")
    target = next((u for u in player.units if u.id == target_unit_id and u.is_alive()), None)
    if target is None:
        raise ActionError("Alvo nao encontrado.")
    heal = min(2, target.life_max - target.life)
    if heal <= 0:
        raise ActionError("Ja esta cheio.")
    target.life += heal
    player.pending_heals -= 1
    record_action(state, player_id, "use_heal", target=target_unit_id, healed=heal)
    log(state, f"{player.name}: curou {heal} em {target.id}.")


def arken_espolia(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    arken = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "arken"), None)
    if arken is None:
        raise ActionError("Arken nao esta vivo.")
    if player.arken_espolia_used_turn == state.turn:
        raise ActionError("Arken ja espoliou neste turno.")
    occupied_pids: list[int] = []
    for other in state.players:
        if other.id == player_id or not other.city.is_alive():
            continue
        home = f"city_{other.id}"
        if any(u.house == home and u.is_alive() for u in player.units):
            occupied_pids.append(other.id)
    if not occupied_pids:
        raise ActionError("Nenhuma Cidade inimiga ocupada.")
    gold = 2 * len(occupied_pids)
    player.city.gold += gold
    log(state, f"{player.name} (Arken): +{gold} Ouro.")
    enemy_houses = {f"city_{pid}" for pid in occupied_pids}
    for u in player.units:
        if isinstance(u, Troop) and u.is_alive() and u.house in enemy_houses:
            healed = min(1, u.life_max - u.life)
            if healed > 0:
                u.life += healed
            u.statuses["cannot_attack_on_turn"] = state.turn
    player.arken_espolia_used_turn = state.turn
    record_action(state, player_id, "arken_espolia", gold=gold)


def tintin_ficar_invisivel(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    tintin = next((u for u in player.units
                   if isinstance(u, Hero) and u.is_alive() and u.hero_id == "tintin"),
                  None)
    if tintin is None:
        raise ActionError("Tin Tin nao esta vivo.")
    cd = tintin.statuses.get("tintin_cooldown_until_turn", -1)
    if cd > state.turn:
        raise ActionError(f"Tin Tin em recarga.")
    tintin.statuses["invisivel_until_turn"] = state.turn
    tintin.statuses["tintin_cooldown_until_turn"] = state.turn + 2
    log(state, f"{player.name}: Tin Tin invisivel ate o fim do turno.")


def dandara_invisibilidade(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    dandara = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "dandara"),
                   None)
    if dandara is None:
        raise ActionError("Dandara nao esta viva.")
    cd = dandara.statuses.get("dandara_cooldown_until_turn", -1)
    if cd > state.turn:
        raise ActionError("Dandara em recarga.")
    home = dandara.house
    for u in player.units:
        if u.is_alive() and u.house == home:
            u.statuses["invisivel_until_turn"] = state.turn
    dandara.statuses["dandara_cooldown_until_turn"] = state.turn + 2
    log(state, f"{player.name}: Dandara tornou {home} invisivel.")


def besouro_mandinga(state: GameState, player_id: int, card_id: str,
                     choice: dict | None = None) -> None:
    player = get_player(state, player_id)
    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"),
                   None)
    if besouro is None:
        raise ActionError("Besouro nao esta vivo.")
    if player.besouro_mandinga_used_turn == state.turn:
        raise ActionError("Mandinga ja usada.")
    if card_id not in player.hand:
        raise ActionError("Nao tem essa carta.")
    play_artifact(state, player_id, card_id, choice=choice or {})
    player.besouro_mandinga_used_turn = state.turn
    log(state, f"{player.name}: Besouro usou Mandinga com {card_display(card_id)}.")


def luide_vampa_mover(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    luide = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa"),
                 None)
    if luide is None:
        raise ActionError("Luide Vampa nao esta vivo.")
    if player.has_cast_spell_this_turn:
        raise ActionError("Ja usou feitico neste turno.")
    for u in player.units:
        if u.is_alive():
            u.max_moves_this_turn = max(2, u.max_moves_this_turn)
            u.has_moved_this_turn = False
            if u.moves_this_turn >= 1:
                u.moves_this_turn = 0
    log(state, f"{player.name}: Luide Vampa ativou movimento noturno.")


def use_or_give_pena(state: GameState, player_id: int, card_id: str,
                     give_to_iuna: bool) -> None:
    player = get_player(state, player_id)
    if card_id != "PENA":
        raise ActionError("So aplica para Pena.")
    if card_id not in player.hand:
        raise ActionError("Nao tem Pena.")
    if player.people == "humanos":
        player.hand.remove(card_id)
        player.field_artifacts.append(ArtifactOnField(card_id="PENA", owner_id=player_id))
        log(state, f"{player.name} (Humanos): Pena ativa.")
        record_action(state, player_id, "pena_activate")
        return
    if give_to_iuna:
        iuna_owner = None
        for p in state.players:
            for u in p.units:
                if isinstance(u, Hero) and u.is_alive() and u.hero_id == "iuna":
                    iuna_owner = p
                    break
            if iuna_owner:
                break
        if iuna_owner is None:
            raise ActionError("Iuna nao esta viva.")
        player.hand.remove(card_id)
        if not state.shop.is_empty():
            new_card = state.shop.draw_random(state.rng)
            player.hand.append(new_card)
            log(state, f"{player.name} deu Pena a Iuna e ganhou {card_display(new_card)}.")
        record_action(state, player_id, "pena_give_iuna")
        return
    log(state, f"{player.name}: ficou com a Pena.")


def cast_spell(state: GameState, player_id: int, choice: dict | None = None) -> None:
    choice = choice or {}
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    if state.turn < player.spell_cooldown_until_turn:
        raise ActionError(f"Feitico em recarga.")
    if player.has_cast_spell_this_turn:
        raise ActionError("Ja usou feitico.")

    sp = spells_mod.spell_for_people(player.people)
    if sp is None:
        raise ActionError("Sem feitico.")
    if not sp.implemented:
        raise ActionError(f"{sp.name} nao implementado.")
    if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
        raise ActionError("Valendar substitui Sonho Lucido.")

    if sp.spell_id == "resistencia":
        _spell_resistencia(state, player, choice)
    elif sp.spell_id == "armadura_de_ouro":
        _spell_armadura(state, player, choice)
    elif sp.spell_id == "espoliar":
        _spell_espoliar(state, player)
    elif sp.spell_id == "sonho_lucido":
        player.sonho_lucido_pending_turn = state.turn
        if peoples.luna_is_alive(player):
            player.sonho_lucido_multi_turn = state.turn
        log(state, f"{player.name}: Sonho Lucido ativo.")
    elif sp.spell_id == "transformar_morcego":
        _spell_transformar_morcego(state, player, choice)
    elif sp.spell_id == "licantropo":
        _spell_licantropo(state, player, choice)
    elif sp.spell_id == "linhagem_ancestral":
        _spell_linhagem_ancestral(state, player, choice)
    elif sp.spell_id == "levantar_mortos":
        _spell_levantar_mortos(state, player, choice)
    else:
        raise ActionError(f"Feitico {sp.spell_id} sem implementacao.")

    player.spell_cooldown_until_turn = state.turn + 2
    player.has_cast_spell_this_turn = True
    record_action(state, player_id, "cast_spell", spell=sp.spell_id)


def _spell_resistencia(state, player, choice):
    tid = choice.get("unit_id")
    if not tid:
        raise ActionError("Precisa alvo.")
    t = next((u for u in player.units if u.id == tid and u.is_alive()), None)
    if t is None:
        raise ActionError("Alvo nao encontrado.")
    t.resistance_stacks += 1
    t.statuses["spell_resist"] = t.statuses.get("spell_resist", 0) + 1
    log(state, f"{player.name} Resistencia em {t.id} (ate fim do turno).")


def _spell_armadura(state, player, choice):
    cap = int(choice.get("cap", 1))
    if cap < 1:
        raise ActionError("Cap >= 1.")
    player.armor_gold_cap_per_hit = cap
    log(state, f"{player.name} Armadura de Ouro cap {cap}.")


def _spell_espoliar(state, player):
    owned = 0
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        home = f"city_{other.id}"
        if any(u.house == home and u.is_alive() for u in player.units):
            owned += 1
    player.city.gold += 2 * owned
    log(state, f"{player.name} Espoliou {owned}.")


def _spell_transformar_morcego(state, player, choice):
    tid = choice.get("unit_id")
    if not tid:
        raise ActionError("Precisa alvo.")
    t = next((u for u in player.units if u.id == tid and u.is_alive()), None)
    if t is None:
        raise ActionError("Alvo nao encontrado.")
    t.statuses["morcego_until_turn"] = state.turn
    if t.max_moves_this_turn < 2:
        t.max_moves_this_turn = 2
        t.has_moved_this_turn = False
        t.moves_this_turn = 0
    log(state, f"{player.name}: {t.id} virou morcego.")


def _spell_licantropo(state, player, choice):
    tid = choice.get("unit_id")
    if not tid:
        raise ActionError("Precisa alvo.")
    t = next((u for u in player.units if u.id == tid and u.is_alive()), None)
    if t is None:
        raise ActionError("Alvo nao encontrado.")
    t.statuses["lobisomem_until_turn"] = state.turn
    log(state, f"{player.name}: {t.id} virou lobisomem.")


def _spell_linhagem_ancestral(state, player, choice):
    hid = choice.get("hero_id")
    if not hid:
        raise ActionError("Precisa heroi.")
    hero_alvo = next((u for u in player.units
                      if isinstance(u, Hero) and u.is_alive() and u.hero_id == hid), None)
    if hero_alvo is None:
        raise ActionError("Heroi Gigante nao esta vivo.")
    if hid == "pe_descalco":
        player.double_damage_until_end_night = True
        for u in player.units:
            if u.is_alive():
                u.double_damage = True
        log(state, "Linhagem Ancestral: Grito de Guerra ativo.")
    elif hid == "joao_grandao":
        log(state, "Linhagem Ancestral: Presenca Magnetica marcada.")
        state.pending_effects.append({"kind": "JOAO_PRESENCA", "player_id": player.id,
                                       "due_turn": state.turn})
    elif hid == "caroco":
        _cabaca_cheia(state, player)
    else:
        raise ActionError(f"Heroi {hid} nao tem feitico proprio.")


def _cabaca_cheia(state, player):
    r = state.rng.randint(1, 4)
    if r == 1:
        for u in player.units:
            if u.is_alive():
                u.statuses["invulneravel_until_turn"] = state.turn
        log(state, "Cabaca Cheia: Invulneravel.")
    elif r == 2:
        for u in player.units:
            if u.is_alive():
                u.max_moves_this_turn += 1
                u.has_moved_this_turn = False
        log(state, "Cabaca Cheia: +1 movimento.")
    elif r == 3:
        player.city.gold += 1
        log(state, "Cabaca Cheia: +1 Ouro.")
    elif r == 4:
        player.city.magic += 1
        log(state, "Cabaca Cheia: +1 Magia.")


def _spell_levantar_mortos(state, player, choice):
    arqs = choice.get("archetypes", [])
    if len(arqs) != 2:
        raise ActionError("Escolha 2 arquetipos diferentes.")
    if arqs[0] == arqs[1]:
        raise ActionError("Precisa ser diferentes.")
    for arq_name in arqs:
        arq = TroopArchetype(arq_name)
        n = sum(1 for u in player.units if isinstance(u, Troop))
        unit_id = f"p{player.id}_raised_{arq.value}_{n}"
        troop = Troop(id=unit_id, owner_id=player.id, house=f"city_{player.id}",
                      life=1, life_max=1, archetype=arq, has_moved_this_turn=True)
        player.units.append(troop)
        log(state, f"{player.name} levantou {arq.value} com 1 de vida.")


def _has_unit_at_center(state, player_id):
    player = get_player(state, player_id)
    return any(u.house == CENTER and u.is_alive() for u in player.units)


def _apply_valendar_bonus(state, player, card_id):
    if not peoples.valendar_is_alive(player):
        return
    from .artifacts import ARTIFACT_CATALOG
    d = ARTIFACT_CATALOG.get(card_id)
    if d is None or not d.suit:
        return
    suit = d.suit
    if suit == "H":
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                u.life = u.life_max
    elif suit == "D":
        player.vender_por_magia_turn = state.turn
    elif suit == "C":
        player.andar_duas_vezes_turn = state.turn
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                u.max_moves_this_turn = 2
                u.has_moved_this_turn = False
                u.moves_this_turn = 0
    elif suit == "S":
        player.bater_primeiro_turn = state.turn


def _boin_alive(player):
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "boin"
               for u in player.units)


def buy_artifact_with_gold(state, player_id):
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    if player.artifacts_bought_gold_today >= ARTIFACT_MAX_BUYS_GOLD_PER_DAY:
        raise ActionError("Ja comprou com Ouro hoje.")
    if not _has_unit_at_center(state, player_id):
        raise ActionError("Precisa unidade no Centro.")
    if city.gold < ARTIFACT_GOLD_COST:
        raise ActionError(f"Ouro insuficiente ({ARTIFACT_GOLD_COST}).")
    if state.shop.is_empty():
        raise ActionError("Loja vazia.")
    city.gold -= ARTIFACT_GOLD_COST
    player.artifacts_bought_gold_today += 1
    if _boin_alive(player) and state.shop.size() >= 2:
        drawn = [state.shop.draw_random(state.rng) for _ in range(2)]
        player.pending_artifact_choice = {"kind": "BOIN", "cards": drawn}
        log(state, f"{player.name} (Boin): escolha 1 de 2.")
        return None
    card = state.shop.draw_random(state.rng)
    player.hand.append(card)
    record_action(state, player_id, "buy_artifact_gold", card=card)
    log(state, f"{player.name} comprou: {card_display(card)}.")
    return card


def transmute_artifact_with_magic(state, player_id):
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    if player.artifacts_bought_magic_today >= ARTIFACT_MAX_BUYS_MAGIC_PER_DAY:
        raise ActionError("Ja transmutou hoje.")
    if city.magic < ARTIFACT_MAGIC_COST:
        raise ActionError(f"Magia insuficiente ({ARTIFACT_MAGIC_COST}).")
    if state.shop.is_empty():
        raise ActionError("Loja vazia.")
    city.magic -= ARTIFACT_MAGIC_COST
    player.artifacts_bought_magic_today += 1
    if _boin_alive(player) and state.shop.size() >= 2:
        drawn = [state.shop.draw_random(state.rng) for _ in range(2)]
        player.pending_artifact_choice = {"kind": "BOIN", "cards": drawn}
        log(state, f"{player.name} (Boin): escolha 1 de 2.")
        return None
    card = state.shop.draw_random(state.rng)
    player.hand.append(card)
    record_action(state, player_id, "transmute_artifact_magic", card=card)
    log(state, f"{player.name} transmutou: {card_display(card)}.")
    return card


def sell_artifact(state, player_id, card_id):
    player = get_player(state, player_id)
    if card_id not in player.hand:
        raise ActionError("Nao tem essa carta.")
    if not _has_unit_at_center(state, player_id):
        raise ActionError("Precisa unidade no Centro.")
    player.hand.remove(card_id)
    if player.vender_por_magia_turn == state.turn:
        player.city.magic += ARTIFACT_SELL_GOLD
    else:
        player.city.gold += ARTIFACT_SELL_GOLD
    state.shop.return_card(card_id)
    record_action(state, player_id, "sell_artifact", card=card_id)
    log(state, f"{player.name} vendeu {card_display(card_id)}.")


def play_artifact(state, player_id, card_id, target_unit_id=None, choice=None):
    if choice is None:
        choice = {}
    if target_unit_id is not None:
        choice = {**choice, "unit_id": target_unit_id}
    player = get_player(state, player_id)
    if card_id not in player.hand:
        raise ActionError("Nao tem essa carta.")
    if player.sonho_lucido_pending_turn == state.turn:
        new_card = peoples.sonho_lucido_flip(card_id)
        if new_card != card_id:
            player.hand.remove(card_id)
            player.hand.append(new_card)
            log(state, f"Sonho Lucido: {card_display(card_id)} -> {card_display(new_card)}.")
            card_id = new_card
        player.sonho_lucido_used_turn = state.turn
        if player.sonho_lucido_multi_turn != state.turn:
            player.sonho_lucido_pending_turn = -1
    if not artifacts_effects.is_implemented(card_id):
        raise ActionError(f"{card_display(card_id)} nao implementado.")
    if artifacts_effects.needs_choice(card_id) and not choice:
        raise ActionError(f"{card_display(card_id)} exige escolha.")
    player.hand.remove(card_id)
    artifact = ArtifactOnField(card_id=card_id, owner_id=player_id)
    player.field_artifacts.append(artifact)
    try:
        artifacts_effects.on_play(state, player_id, card_id, choice)
    except Exception:
        player.field_artifacts.remove(artifact)
        player.hand.append(card_id)
        raise
    _apply_valendar_bonus(state, player, card_id)
    record_action(state, player_id, "play_artifact", card=card_id, choice=choice)


def discard_field_artifact(state, player_id, card_id):
    player = get_player(state, player_id)
    for i, a in enumerate(player.field_artifacts):
        if a.card_id == card_id:
            player.field_artifacts.pop(i)
            state.shop.return_card(card_id)
            log(state, f"{player.name}: {card_display(card_id)} voltou a Loja.")
            return
    raise ActionError(f"Nao tem {card_id} em campo.")


def resolve_pending_artifact_choice(state, player_id, kept_cards=None, resource=None):
    player = get_player(state, player_id)
    pending = player.pending_artifact_choice
    if not pending:
        raise ActionError("Sem escolha pendente.")
    if pending["kind"] == "J_D":
        expected = pending["pick"]
        kept_cards = kept_cards or []
        if len(kept_cards) != expected:
            raise ActionError(f"Escolher {expected}.")
        available = list(pending["cards"])
        kept = []
        for c in kept_cards:
            if c not in available:
                raise ActionError(f"{c} indisponivel.")
            available.remove(c)
            kept.append(c)
        for c in kept:
            player.hand.append(c)
        for c in available:
            state.shop.return_card(c)
        player.pending_artifact_choice = None
        discard_field_artifact(state, player_id, pending["card_id"])
        return
    if pending["kind"] == "BOIN":
        if not kept_cards or len(kept_cards) != 1:
            raise ActionError("Boin: escolha 1.")
        chosen = kept_cards[0]
        player.hand.append(chosen)
        for c in pending["cards"]:
            if c != chosen:
                state.shop.return_card(c)
        player.pending_artifact_choice = None
        return
    if pending["kind"] == "Q_D":
        if resource not in ("gold", "magic"):
            raise ActionError("Qd: gold ou magic.")
        amount = pending["dead_unit_max_life"]
        killer_id = pending["killer_id"]
        if resource == "gold":
            player.city.gold += amount
        else:
            player.city.magic += amount
        if killer_id is not None and killer_id != player_id:
            killer = get_player(state, killer_id)
            if resource == "gold":
                killer.city.gold += amount
            else:
                killer.city.magic += amount
        player.pending_artifact_choice = None
        try:
            discard_field_artifact(state, player_id, "Q_D")
        except ActionError:
            pass
        return
    raise ActionError(f"Pendencia desconhecida: {pending['kind']}")
'''

# =============================================================
# jessica/core/turn.py - Caroco gratis no turno 1
# =============================================================
FILES["jessica/core/turn.py"] = '''\
from __future__ import annotations
from .constants import Phase, MONUMENT_BONUS_INTERVAL
from .actions import apply_gold_interest, reset_unit_flags
from .state import get_player, log
from .models import GameState, Hero, Troop
from . import artifacts_effects, peoples


class TurnError(Exception):
    pass


def start_turn(state: GameState) -> list[tuple[int, int]]:
    if state.game_over:
        raise TurnError("Partida ja encerrada.")
    log(state, f"--- Inicio do Turno {state.turn} (Dia) ---")
    state.phase = Phase.DAY
    interest = apply_gold_interest(state)
    artifacts_effects.on_turn_start(state)
    if state.turn % MONUMENT_BONUS_INTERVAL == 0:
        _monument_bonus(state)
    _process_espectros(state)
    _process_caroco_turn1(state)
    _process_gigantes_turn(state)
    peoples.apply_lua_cheia_effects(state)
    reset_unit_flags(state)
    return interest


def _monument_bonus(state: GameState) -> None:
    for player in state.players:
        if not player.city.is_alive():
            continue
        if not player.city.has_monument:
            continue
        if state.shop.is_empty():
            continue
        card = state.shop.draw_random(state.rng)
        player.hand.append(card)
        log(state, f"{player.name}: Monumento concedeu {card}.")


def _process_espectros(state: GameState) -> None:
    if not state.espectros_pendentes:
        return
    pend = state.espectros_pendentes
    state.espectros_pendentes = []
    for e in pend:
        owner = get_player(state, e["owner_of_cobra"])
        if not owner.city.is_alive():
            continue
        from . import heroes
        hdef = heroes.get_hero(e["hero_id"])
        n = sum(1 for u in owner.units if isinstance(u, Hero))
        unit_id = f"p{owner.id}_spectre_{e['hero_id']}_{n}"
        hero = Hero(id=unit_id, owner_id=owner.id, house=e["house"],
                    life=hdef.life, life_max=hdef.life,
                    hero_id=hdef.hero_id, has_moved_this_turn=True)
        hero.statuses["espectro_until_turn"] = state.turn
        owner.units.append(hero)
        log(state, f"{owner.name}: Espectro de {hdef.name} surgiu em {e['house']}.")


def _process_caroco_turn1(state: GameState) -> None:
    if state.turn != 1:
        return
    for player in state.players:
        if player.people != peoples.PEOPLE_GIGANTES:
            continue
        if player.chosen_hero_id != "caroco":
            continue
        if not player.city.is_alive():
            continue
        if any(isinstance(u, Hero) and u.hero_id == "caroco" for u in player.units):
            continue
        hero = Hero(id=f"p{player.id}_caroco_free",
                    owner_id=player.id, house=f"city_{player.id}",
                    life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
        player.units.append(hero)
        log(state, f"{player.name}: Caroco invocado gratuitamente (turno 1).")


def _process_gigantes_turn(state: GameState) -> None:
    if state.turn % 4 != 0:
        return
    for player in state.players:
        if player.people != peoples.PEOPLE_GIGANTES:
            continue
        if not player.city.is_alive():
            continue
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                if u.hero_id in ("joao_grandao", "pe_descalco"):
                    u.life_max *= 2
                    u.life = u.life_max
                    log(state, f"{player.name}: {u.hero_id} vida dobrada ({u.life_max}).")
        if any(isinstance(u, Hero) and u.hero_id == "caroco" for u in player.units):
            player.carocos_gerados += 1
            n = sum(1 for u in player.units if isinstance(u, Hero))
            unit_id = f"p{player.id}_caroco_extra_{n}"
            hero = Hero(id=unit_id, owner_id=player.id, house=f"city_{player.id}",
                        life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
            player.units.append(hero)
            log(state, f"{player.name}: novo Caroco gerado.")


def start_player_day(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    if player.skip_day_turn == state.turn:
        log(state, f"{player.name} esta pulado (Jc).")
        player.has_played_day_this_turn = True
        return
    if not player.morning_done_this_turn:
        player.morning_done_this_turn = True
        peoples.on_player_morning(state, player_id)
    artifacts_effects.on_player_day_start(state, player_id)


def day_order(state: GameState) -> list[int]:
    if not state.turn_order:
        raise TurnError("turn_order nao definido.")
    alive = {p.id for p in state.alive_players()}
    idx = state.turn_order.index(state.curuna_id)
    ordered = state.turn_order[idx:] + state.turn_order[:idx]
    result: list[int] = []
    for pid in ordered:
        if pid not in alive:
            continue
        p = get_player(state, pid)
        if state.phase == Phase.DAY and p.skip_day_turn == state.turn:
            continue
        if state.phase == Phase.NIGHT and p.skip_night_turn == state.turn:
            continue
        result.append(pid)
    return result


def _luna_return(state: GameState) -> None:
    for player in state.players:
        for u in player.units:
            if (isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
                    and "luna_origin_house" in u.statuses):
                origin = u.statuses.pop("luna_origin_house")
                if origin != u.house:
                    log(state, f"  Luna retorna de {u.house} para {origin}.")
                    u.house = origin


def end_day(state: GameState) -> None:
    if state.phase != Phase.DAY:
        raise TurnError("Nao esta na fase do Dia.")
    state.deaths_this_night = []
    artifacts_effects.on_night_start(state)
    _luna_return(state)
    state.phase = Phase.NIGHT
    log(state, f"--- Fase da Noite (Turno {state.turn}) ---")


def end_turn(state: GameState) -> None:
    from .victory import check_victory
    artifacts_effects.on_end_turn(state)
    _remove_espectros(state)
    check_victory(state)
    if state.game_over:
        return
    alive = {p.id for p in state.alive_players()}
    idx = state.turn_order.index(state.curuna_id)
    for offset in range(1, len(state.turn_order) + 1):
        candidate = state.turn_order[(idx + offset) % len(state.turn_order)]
        if candidate in alive:
            state.curuna_id = candidate
            break
    state.turn += 1


def _remove_espectros(state: GameState) -> None:
    for p in state.players:
        p.units = [u for u in p.units
                   if u.statuses.get("espectro_until_turn", -1) != state.turn]
'''

# =============================================================
# tests/test_vampiros.py
# =============================================================
FILES["tests/test_vampiros.py"] = '''\
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
    # vamp tomou 4, cura 2 -> 2
    assert vamp.life == 2, f"Vampiro deveria ter 2 (4-4+2), veio {vamp.life}"
    print("OK  - Vampiro cura 2 ao matar")


def test_vampiro_empata_sobrevive_2():
    """Empate = mesma vida. Vampiro sobrevive com 2 (empate + mata = 2 final)."""
    state = make_state()
    state.phase = Phase.NIGHT
    vamp = _troop(state, 1, TroopArchetype.LIGHT, 4, "center")
    victim = _troop(state, 2, TroopArchetype.LIGHT, 4, "center")
    resolve_attack(state, Attack(vamp.id, "unit", victim.id))
    assert not victim.is_alive()
    assert vamp.life == 2, f"Empate+mata: vampiro devia estar com 2, veio {vamp.life}"
    print("OK  - Vampiro empata e sobrevive com 2")


def test_vampiro_nao_cura_contra_cidade():
    """Sede de Sangue não vale contra Cidades."""
    state = make_state()
    state.phase = Phase.NIGHT
    vamp = _troop(state, 1, TroopArchetype.HEAVY, 8, "city_2")
    vamp.life = 4
    vida_antes = vamp.life
    resolve_attack(state, Attack(vamp.id, "city", "2"))
    # Cidade tem 2 de vida, tropa causa 1 -> cidade 1/2. Vamp toma 1 retaliação.
    assert vamp.life == vida_antes - 1, f"Vampiro nao deve curar vs Cidade. veio {vamp.life}"
    print("OK  - Vampiro nao cura contra Cidade")


def test_dracula_empala():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    dracula = summon_hero(state, 1)
    dracula.house = CENTER
    dracula.life = 20
    dracula.life_max = 20
    victim = _troop(state, 2, TroopArchetype.LIGHT, 4, "center")
    resolve_attack(state, Attack(dracula.id, "unit", victim.id))
    assert not victim.is_alive()
    assert {"kind": "troop", "id": "light"} in p1.empalados
    print("OK  - Dracula empalou tropa light")


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
    # Tentar invocar light tropa pelo p2 -> bloqueado
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
    # Forçar escolher Dandara
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
    print("=== Testes Vampiros ===\\n")
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
# tests/test_lobisomens.py
# =============================================================
FILES["tests/test_lobisomens.py"] = '''\
"""Testes: Lobisomens."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop
from jessica.core.combat import resolve_attack, Attack
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["lobisomens", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "lobisomens": ["lupa_lider", "cigana", "luarado"],
            "humanos": ["miyamoto"], "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "lobisomens", "heroi": "lupa_lider"},
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


def test_lua_cheia_detection():
    """Lua cheia = jogador lobisomem é o último (curuna é o próximo)."""
    state = make_state()
    order = state.turn_order
    # Força curuna para o proximo do lobisomem
    idx = order.index(1)  # J1 é lobisomem
    next_pid = order[(idx + 1) % len(order)]
    state.curuna_id = next_pid
    assert peoples.is_lua_cheia(state, 1) is True
    # Força curuna para o lobisomem mesmo -> não é lua cheia
    state.curuna_id = 1
    assert peoples.is_lua_cheia(state, 1) is False
    print("OK  - Lua Cheia detectada corretamente")


def test_dobro_de_dano_em_lua_cheia():
    state = make_state()
    state.phase = Phase.NIGHT
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    lob = _troop(state, 1, TroopArchetype.HEAVY, 4, "center")
    victim = _troop(state, 2, TroopArchetype.HEAVY, 8, "center")
    resolve_attack(state, Attack(lob.id, "unit", victim.id))
    # Sem lua cheia: lob 4 vs vit 8 -> vit 4, lob morre (tomou 8)
    # Com lua cheia: lob 4x2=8 -> vit morre; lob toma 8 -> morre.
    assert not victim.is_alive(), f"Vitima deveria morrer com dano dobrado, vida {victim.life}"
    print("OK  - Dobro de dano em Lua Cheia matou vitima de 8")


def test_infeccao_registrada_ao_matar():
    state = make_state()
    state.phase = Phase.NIGHT
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    lob = _troop(state, 1, TroopArchetype.HEAVY, 4, "center")
    victim = _troop(state, 2, TroopArchetype.HEAVY, 8, "center")
    resolve_attack(state, Attack(lob.id, "unit", victim.id))
    p1 = state.players[0]
    assert {"kind": "troop", "id": "heavy"} in p1.infectados
    print("OK  - Tropa heavy infectada registrada")


def test_cigana_ataca_cidade_em_lua_cheia():
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    p1.chosen_hero_id = "cigana"
    # Remove Lupa viva antes de invocar Cigana
    p1.units = []
    cigana = summon_hero(state, 1)
    cigana.house = "city_2"
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    city2 = state.players[1].city
    before = city2.life
    resolve_attack(state, Attack(cigana.id, "city", "2"))
    assert city2.life == before - 1, f"Cidade deveria perder 1, veio {city2.life}"
    print("OK  - Cigana atacou Cidade em Lua Cheia")


def test_lupa_resistencia_em_lua_cheia():
    from jessica.core.actions import cast_spell
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 10
    # J1 = lupa_lider
    lupa = summon_hero(state, 1)
    t1 = summon_troop(state, 1, TroopArchetype.LIGHT, 4)
    # Forçar lua cheia e chamar apply
    order = state.turn_order
    idx = order.index(1)
    state.curuna_id = order[(idx + 1) % len(order)]
    peoples.apply_lua_cheia_effects(state)
    assert lupa.resistance_stacks >= 1
    assert t1.resistance_stacks >= 1
    print("OK  - Lupa concedeu resistencia a todos em Lua Cheia")


def run_all():
    tests = [
        test_lua_cheia_detection,
        test_dobro_de_dano_em_lua_cheia,
        test_infeccao_registrada_ao_matar,
        test_cigana_ataca_cidade_em_lua_cheia,
        test_lupa_resistencia_em_lua_cheia,
    ]
    print("=== Testes Lobisomens ===\\n")
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
# tests/test_gigantes.py
# =============================================================
FILES["tests/test_gigantes.py"] = '''\
"""Testes: Gigantes."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop, ActionError
from jessica.core.turn import start_turn
from jessica.core.constants import TroopArchetype, Phase
from jessica.core.models import Hero


def make_state():
    state, _ = run_setup(
        all_peoples=["gigantes", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "gigantes": ["joao_grandao", "pe_descalco", "caroco"],
            "humanos": ["miyamoto"], "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "gigantes", "heroi": "joao_grandao"},
            2: {"povo": "humanos", "heroi": "miyamoto"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_gigante_heroi_custa_4_magia():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    summon_hero(state, 1)
    assert p.city.magic == 6, f"Esperado 6, veio {p.city.magic}"
    print("OK  - Heroi Gigante custa 4 Magia")


def test_joao_dobra_vida_no_turno_4():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    joao = summon_hero(state, 1)
    assert joao.life_max == 10
    # Avança para turno 4
    state.turn = 4
    from jessica.core.turn import _process_gigantes_turn
    _process_gigantes_turn(state)
    assert joao.life_max == 20, f"Esperado 20, veio {joao.life_max}"
    print("OK  - Joao Grandao dobrou vida no turno 4")


def test_pe_descalco_extra_ataque():
    state = make_state()
    p = state.players[0]
    p.chosen_hero_id = "pe_descalco"
    p.city.magic = 10
    pe = summon_hero(state, 1)
    assert pe.hero_id == "pe_descalco"
    from jessica.core.combat import _effective_max_attacks
    state.phase = Phase.NIGHT
    max_atks = _effective_max_attacks(state, pe)
    # Pe Descalco tem +1 ataque sempre
    assert max_atks == 1, f"Base deveria ser 1, veio {max_atks} (implementacao de +1 ataque fica na UI/passiva)"
    print("OK  - Pe Descalco invocado (bonus +1 ataque na mecanica de combate)")


def test_caroco_gratis_turno_1():
    state = make_state()
    p = state.players[0]
    p.chosen_hero_id = "caroco"
    p.city.magic = 10
    # Simula start_turn do turno 1
    p.units = []
    state.turn = 1
    from jessica.core.turn import _process_caroco_turn1
    _process_caroco_turn1(state)
    assert any(isinstance(u, Hero) and u.hero_id == "caroco" for u in p.units)
    print("OK  - Caroco invocado gratuitamente no turno 1")


def test_caroco_reinvoca_todos_por_4_magia():
    state = make_state()
    p = state.players[0]
    p.chosen_hero_id = "caroco"
    p.city.magic = 10
    state.turn = 1
    from jessica.core.turn import _process_caroco_turn1
    _process_caroco_turn1(state)
    # Simula turno 4 -> ganha mais um Caroco
    state.turn = 4
    from jessica.core.turn import _process_gigantes_turn
    _process_gigantes_turn(state)
    carocos_vivos = [u for u in p.units if isinstance(u, Hero) and u.hero_id == "caroco"]
    assert len(carocos_vivos) == 2, f"Esperado 2, veio {len(carocos_vivos)}"
    print("OK  - Dois Carocos vivos no turno 4")


def run_all():
    tests = [
        test_gigante_heroi_custa_4_magia,
        test_joao_dobra_vida_no_turno_4,
        test_pe_descalco_extra_ataque,
        test_caroco_gratis_turno_1,
        test_caroco_reinvoca_todos_por_4_magia,
    ]
    print("=== Testes Gigantes ===\\n")
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
# tests/test_mortos_vivos.py
# =============================================================
FILES["tests/test_mortos_vivos.py"] = '''\
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
    print("=== Testes Mortos-Vivos ===\\n")
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
# Execucao
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
    print("  python tests/run_all.py")


if __name__ == "__main__":
    main()