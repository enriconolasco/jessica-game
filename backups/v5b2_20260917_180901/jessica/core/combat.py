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
