"""apply_update_v4d: setup 8 povos + 8 feedbacks + UI feiticos novos."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v4d_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# jessica/core/actions.py - fix spell resistencia source
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

    # Gigantes: Caroco tem logica especial
    if player.chosen_hero_id == "caroco" and force_hero_id is None:
        # Se ja tem um Caroco vivo, o normal é bloquear. O "invocar de novo" e via Magia paga.
        # Regra: 4 Magia -> todos os Carocos mortos voltam ao mesmo tempo.
        carocos_vivos = [u for u in player.units
                         if isinstance(u, Hero) and u.is_alive() and u.hero_id == "caroco"]
        carocos_ja_gerados = player.carocos_gerados + 1  # 1 principal + N gerados
        if len(carocos_vivos) < carocos_ja_gerados:
            magic_cost = peoples.hero_summon_cost(player)
            if city.magic < magic_cost:
                raise ActionError(f"Magia insuficiente ({magic_cost}).")
            city.magic -= magic_cost
            falta = carocos_ja_gerados - len(carocos_vivos)
            for i in range(falta):
                n = sum(1 for u in player.units if isinstance(u, Hero))
                unit_id = f"p{player_id}_caroco_ret_{n}"
                hero = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                            life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
                player.units.append(hero)
            log(state, f"{player.name}: {falta} Carocos reinvocados (4 Magia).")
            return player.units[-1]
        else:
            raise ActionError("Todos os Carocos ja estao vivos.")

    alive_heroes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()]
    if alive_heroes and force_hero_id is None:
        raise ActionError("Ja existe heroi vivo.")
    target_id = force_hero_id if force_hero_id is not None else player.chosen_hero_id
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
    """Luide Vampa: ativa feitico + permite mover aliados na Noite."""
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
# jessica/core/artifacts_effects.py - reset spell_resist no end_turn
# =============================================================
FILES["jessica/core/artifacts_effects.py"] = '''\
"""Efeitos de artefatos."""
from __future__ import annotations
from .state import get_player, log
from .models import GameState, ArtifactOnField, Unit, Hero, Troop
from .constants import CENTER, CITY_HOUSES, TroopArchetype
from . import heroes


IMPLEMENTED: set[str] = {
    "K_H", "K_D", "Q_H", "Q_S", "K_S", "K_C",
    "J_H", "J_S", "J_D", "Q_D", "J_C", "Q_C",
}
ONE_TURN_CARDS: set[str] = {"Q_H", "Q_S", "K_S"}
CHOICE_TYPE: dict[str, str] = {
    "K_C": "own_unit", "J_H": "people_hero", "J_S": "house",
    "Q_D": "any_unit", "J_C": "any_player", "Q_C": "any_enemy_unit",
}


def is_implemented(card_id: str) -> bool:
    return card_id in IMPLEMENTED


def needs_choice(card_id: str) -> bool:
    return card_id in CHOICE_TYPE


def choice_type(card_id: str) -> str | None:
    return CHOICE_TYPE.get(card_id)


def on_turn_start(state: GameState) -> None:
    for player in state.players:
        if not player.city.is_alive():
            continue
        for artifact in player.field_artifacts:
            if artifact.card_id == "K_H":
                if player.city.life < player.city.life_max:
                    player.city.life += 1
                    log(state, f"{player.name}: Kh Aquilombar (+1 Vida).")
            elif artifact.card_id == "K_D":
                player.city.gold += 2
                player.city.magic += 1
                log(state, f"{player.name}: Kd Balanca (+2 Ouro, +1 Magia).")


def on_play(state: GameState, player_id: int, card_id: str, choice: dict) -> None:
    player = get_player(state, player_id)
    if card_id == "K_H":
        player.city.life_max += 1
        log(state, f"{player.name} jogou Kh Aquilombar.")
        return
    if card_id == "K_D":
        log(state, f"{player.name} jogou Kd Balanca.")
        return
    if card_id == "Q_H":
        player.invulnerable_until_end_turn = True
        player.no_city_attacks_until_end_turn = True
        log(state, f"{player.name} jogou Qh.")
        return
    if card_id == "Q_S":
        player.double_damage_until_end_night = True
        log(state, f"{player.name} jogou Qs.")
        return
    if card_id == "K_S":
        log(state, f"{player.name} jogou Ks.")
        return
    if card_id == "K_C":
        target_unit_id = choice.get("unit_id")
        if not target_unit_id:
            raise ValueError("Kc requer unit_id.")
        target = next((u for u in player.units if u.id == target_unit_id and u.is_alive()), None)
        if target is None:
            raise ValueError(f"Alvo {target_unit_id} nao encontrado.")
        target.double_damage = True
        target.resistance_stacks += 1
        for a in player.field_artifacts:
            if a.card_id == "K_C" and "target_unit_id" not in a.extra:
                a.extra["target_unit_id"] = target_unit_id
                break
        log(state, f"{player.name} jogou Kc em {target.id}.")
        return
    if card_id == "J_H":
        hero_id = choice.get("hero_id")
        if not hero_id:
            raise ValueError("Jh requer hero_id.")
        hero_id = heroes.resolve_hero_for_people(player.people, hero_id)
        if hero_id == player.chosen_hero_id:
            raise ValueError("Jh nao pode invocar o heroi do setup.")
        alive = any(isinstance(u, Hero) and u.hero_id == hero_id and u.is_alive()
                    for u in player.units)
        if alive:
            raise ValueError(f"Heroi {hero_id} ja em campo.")
        n = sum(1 for u in player.units if isinstance(u, Hero))
        hero_unit_id = f"p{player_id}_hero_extra_{n}"
        hdef = heroes.get_hero(hero_id)
        hero = Hero(id=hero_unit_id, owner_id=player_id,
                    house=f"city_{player_id}",
                    life=hdef.life, life_max=hdef.life,
                    hero_id=hdef.hero_id, has_moved_this_turn=True)
        player.units.append(hero)
        for a in player.field_artifacts:
            if a.card_id == "J_H" and "hero_unit_id" not in a.extra:
                a.extra["hero_unit_id"] = hero_unit_id
                break
        log(state, f"{player.name} jogou Jh: invocou {hdef.name}.")
        return
    if card_id == "J_S":
        house = choice.get("house")
        if not house:
            raise ValueError("Js requer house.")
        if house not in (CENTER, *CITY_HOUSES):
            raise ValueError(f"Casa invalida: {house}")
        existing = [u for u in player.units
                    if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL
                    and u.is_alive()]
        if existing:
            raise ValueError("Ja existe tropa do Chamado da Lua.")
        n = sum(1 for u in player.units if isinstance(u, Troop))
        troop_unit_id = f"p{player_id}_moon_troop_{n}"
        troop = Troop(id=troop_unit_id, owner_id=player_id, house=house,
                      life=5, life_max=5, archetype=TroopArchetype.SPECIAL,
                      has_moved_this_turn=True)
        player.units.append(troop)
        for a in player.field_artifacts:
            if a.card_id == "J_S" and "troop_unit_id" not in a.extra:
                a.extra["troop_unit_id"] = troop_unit_id
                break
        log(state, f"{player.name} jogou Js: tropa 5 em {house}.")
        return
    if card_id == "J_D":
        state.pending_effects.append({
            "kind": "J_D", "player_id": player_id,
            "due_turn": state.turn + 3, "card_id": "J_D",
        })
        log(state, f"{player.name} jogou Jd.")
        return
    if card_id == "Q_D":
        target_unit_id = choice.get("unit_id")
        if not target_unit_id:
            raise ValueError("Qd requer unit_id.")
        target = _find_any_unit(state, target_unit_id)
        if target is None:
            raise ValueError(f"Alvo {target_unit_id} nao encontrado.")
        for a in player.field_artifacts:
            if a.card_id == "Q_D" and "target_unit_id" not in a.extra:
                a.extra["target_unit_id"] = target_unit_id
                break
        log(state, f"{player.name} jogou Qd em {target.id}.")
        return
    if card_id == "J_C":
        target_id = choice.get("target_player_id")
        if target_id is None:
            raise ValueError("Jc requer target_player_id.")
        target = get_player(state, target_id)
        if target.id == player_id:
            raise ValueError("Jc nao pode ter voce como alvo.")
        if not target.city.is_alive():
            raise ValueError("Jc nao pode ter jogador eliminado.")
        target.skip_night_turn = state.turn
        target.skip_day_turn = state.turn + 1 if target.has_played_day_this_turn else state.turn
        log(state, f"{player.name} jogou Jc em {target.name}.")
        return
    if card_id == "Q_C":
        target_unit_id = choice.get("unit_id")
        if not target_unit_id:
            raise ValueError("Qc requer unit_id.")
        target = None
        original_owner = None
        for p in state.players:
            for u in p.units:
                if u.id == target_unit_id and u.is_alive():
                    target, original_owner = u, p
                    break
            if target:
                break
        if target is None:
            raise ValueError(f"Alvo {target_unit_id} nao encontrado.")
        if original_owner.id == player_id:
            raise ValueError("Qc so controla unidade inimiga.")
        if not original_owner.city.is_alive():
            raise ValueError("Qc nao controla unidade de jogador eliminado.")
        original_owner.units.remove(target)
        player.units.append(target)
        target.original_owner_id = original_owner.id
        target.owner_id = player_id
        target.has_moved_this_turn = False
        for a in player.field_artifacts:
            if a.card_id == "Q_C" and "target_unit_id" not in a.extra:
                a.extra["target_unit_id"] = target_unit_id
                a.extra["original_owner_id"] = original_owner.id
                break
        log(state, f"{player.name} jogou Qc: controla {target.id}.")
        return


def _find_any_unit(state: GameState, unit_id: str) -> Unit | None:
    for p in state.players:
        for u in p.units:
            if u.id == unit_id and u.is_alive():
                return u
    return None


def on_player_day_start(state: GameState, player_id: int) -> None:
    triggered = []
    for e in state.pending_effects:
        if e["player_id"] == player_id and e["due_turn"] == state.turn and e["kind"] == "J_D":
            triggered.append(e)
    for e in triggered:
        state.pending_effects.remove(e)
        _trigger_j_d(state, player_id, e["card_id"])


def _trigger_j_d(state: GameState, player_id: int, card_id: str) -> None:
    player = get_player(state, player_id)
    if state.shop.size() < 3:
        log(state, f"{player.name}: Jd - Loja insuficiente.")
        _discard_card(state, player_id, card_id)
        return
    drawn = [state.shop.draw_random(state.rng) for _ in range(3)]
    player.pending_artifact_choice = {
        "kind": "J_D", "card_id": card_id, "cards": drawn, "pick": 2,
    }
    log(state, f"{player.name}: Jd Tabareu - escolha 2 de 3.")


def on_night_start(state: GameState) -> None:
    from . import peoples
    peoples.apply_cova_rasa(state)
    peoples.apply_presenca_magnetica(state)

    by_house_max: dict[str, int] = {}
    for p in state.players:
        for u in p.units:
            if u.is_alive():
                by_house_max[u.house] = max(by_house_max.get(u.house, 0), u.life)

    for player in state.players:
        has_k_s = any(a.card_id == "K_S" for a in player.field_artifacts)
        hero_houses = {u.house for u in player.units
                       if isinstance(u, Hero) and u.is_alive()}
        for u in player.units:
            u.max_attacks_this_night = 1
            u.hero_can_attack_city = False
            if has_k_s:
                if isinstance(u, Hero):
                    u.hero_can_attack_city = True
                if u.house in hero_houses:
                    u.max_attacks_this_night = 2
            if isinstance(u, Hero) and heroes.has_ability(u.hero_id, "double_attack_if_stronger"):
                if u.life >= by_house_max.get(u.house, 0):
                    u.max_attacks_this_night = max(u.max_attacks_this_night, 2)
            if isinstance(u, Hero) and heroes.has_ability(u.hero_id, "extra_attacks_per_dwarf"):
                n = sum(1 for u2 in player.units
                        if isinstance(u2, Hero) and u2.is_alive()
                        and u2.id != u.id and u2.house == u.house)
                u.max_attacks_this_night += n


def on_unit_death(state: GameState, dead_unit: Unit) -> None:
    for owner in state.players:
        for a in list(owner.field_artifacts):
            if a.card_id != "Q_D":
                continue
            if a.extra.get("target_unit_id") != dead_unit.id:
                continue
            if "pending_choice_created" in a.extra:
                continue
            a.extra["pending_choice_created"] = True
            owner.pending_artifact_choice = {
                "kind": "Q_D", "card_id": "Q_D",
                "dead_unit_id": dead_unit.id,
                "dead_unit_max_life": dead_unit.life_max,
                "killer_id": dead_unit.killed_by_player_id,
            }
            log(state, f"  Qd: {owner.name} deve escolher recompensa.")


def on_end_turn(state: GameState) -> None:
    from .actions import discard_field_artifact

    _process_dain_kills(state)

    _restore_controlled_units(state)
    for player in state.players:
        for card_id in ONE_TURN_CARDS:
            if any(a.card_id == card_id for a in player.field_artifacts):
                discard_field_artifact(state, player.id, card_id)
    _cleanup_j_c(state)
    for player in state.players:
        player.double_damage_until_end_night = False
        player.invulnerable_until_end_turn = False
        player.no_city_attacks_until_end_turn = False
        player.armor_gold_cap_per_hit = 0
        player.has_played_day_this_turn = False
        if player.sonho_lucido_pending_turn == state.turn and \
                player.sonho_lucido_multi_turn != state.turn:
            player.sonho_lucido_pending_turn = -1
        if player.sonho_lucido_multi_turn == state.turn:
            player.sonho_lucido_pending_turn = -1
        if player.vender_por_magia_turn == state.turn:
            player.vender_por_magia_turn = -1
        if player.andar_duas_vezes_turn == state.turn:
            player.andar_duas_vezes_turn = -1
        if player.bater_primeiro_turn == state.turn:
            player.bater_primeiro_turn = -1
        if player.skip_day_turn is not None and player.skip_day_turn < state.turn:
            player.skip_day_turn = None
        if player.skip_night_turn is not None and player.skip_night_turn < state.turn:
            player.skip_night_turn = None
        for u in player.units:
            u.max_attacks_this_night = 1
            u.hero_can_attack_city = False
            u.max_moves_this_turn = 1
            # Feitico Resistencia (duracao 1 turno): reset
            n = u.statuses.pop("spell_resist", 0)
            if n > 0:
                u.resistance_stacks = max(0, u.resistance_stacks - n)
            # Lupa Lider: tira resistencia temporaria
            if u.statuses.get("lupa_resist_until_turn", -1) == state.turn:
                u.statuses.pop("lupa_resist_until_turn", None)
                u.resistance_stacks = max(0, u.resistance_stacks - 1)


def _process_dain_kills(state: GameState) -> None:
    remaining = []
    for entry in state.dain_kills:
        if entry["turn"] != state.turn:
            remaining.append(entry)
            continue
        atk_id = entry["attacker_id"]
        found = None
        for p in state.players:
            for u in p.units:
                if u.id == atk_id and u.is_alive():
                    found = u
                    break
            if found:
                break
        if found is not None:
            found.statuses["life_at_death"] = found.life
            found.life = 0
            log(state, f"  {found.id} morreu por atacar Dain (fim da noite).")
    state.dain_kills = remaining
    for p in state.players:
        p.units = [u for u in p.units if u.is_alive()]


def _restore_controlled_units(state: GameState) -> None:
    for p in state.players:
        for u in list(p.units):
            if u.original_owner_id is not None:
                orig = get_player(state, u.original_owner_id)
                p.units.remove(u)
                orig.units.append(u)
                u.owner_id = u.original_owner_id
                u.original_owner_id = None
                log(state, f"  {u.id} voltou ao controle de {orig.name}.")


def _cleanup_j_c(state: GameState) -> None:
    from .actions import discard_field_artifact
    for player in state.players:
        to_discard = []
        for a in player.field_artifacts:
            if a.card_id != "J_C":
                continue
            tgt_id = a.extra.get("target_player_id")
            if tgt_id is None:
                continue
            tgt = get_player(state, tgt_id)
            if tgt.skip_day_turn is None and tgt.skip_night_turn is None:
                to_discard.append(a.card_id)
        for c in to_discard:
            discard_field_artifact(state, player.id, c)


def on_cleanup_after_combat(state: GameState) -> None:
    from .actions import discard_field_artifact
    all_surviving_ids: set[str] = set()
    for p in state.players:
        all_surviving_ids.update(u.id for u in p.units)
    for player in state.players:
        to_discard: list[str] = []
        for a in player.field_artifacts:
            if a.card_id == "K_C":
                tgt = a.extra.get("target_unit_id")
                if tgt and tgt not in all_surviving_ids:
                    to_discard.append(a.card_id)
            elif a.card_id == "J_H":
                tgt = a.extra.get("hero_unit_id")
                if tgt and tgt not in all_surviving_ids:
                    to_discard.append(a.card_id)
            elif a.card_id == "J_S":
                tgt = a.extra.get("troop_unit_id")
                if tgt and tgt not in all_surviving_ids:
                    to_discard.append(a.card_id)
            elif a.card_id == "Q_C":
                tgt = a.extra.get("target_unit_id")
                if tgt and tgt not in all_surviving_ids:
                    to_discard.append(a.card_id)
        for c in to_discard:
            discard_field_artifact(state, player.id, c)


def _discard_card(state: GameState, player_id: int, card_id: str) -> None:
    from .actions import discard_field_artifact
    try:
        discard_field_artifact(state, player_id, card_id)
    except Exception:
        pass
'''

# =============================================================
# jessica/core/setup.py - horario povo selection
# =============================================================
FILES["jessica/core/setup.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass
from .constants import (
    DEFAULT_CITY_LIFE_START, DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC,
)
from .state import make_rng, create_empty_state, get_player, log
from .models import GameState
from .rng import DeterministicRNG
from . import heroes


@dataclass
class SetupResult:
    turn_order: list[int]
    banned_peoples: list[str]
    chosen_peoples: dict[int, str]
    chosen_heroes: dict[int, str]


def roll_d20_order(rng: DeterministicRNG, num_players: int) -> list[int]:
    rolls: dict[int, int] = {i + 1: rng.randint(1, 20) for i in range(num_players)}
    while True:
        by_value: dict[int, list[int]] = {}
        for pid, val in rolls.items():
            by_value.setdefault(val, []).append(pid)
        tied_groups = [pids for pids in by_value.values() if len(pids) > 1]
        if not tied_groups:
            break
        for group in tied_groups:
            for pid in group:
                rolls[pid] = rng.randint(1, 20)
    ordered = sorted(rolls.items(), key=lambda kv: kv[1], reverse=True)
    return [pid for pid, _ in ordered]


def horario_from(order: list[int]) -> list[int]:
    """Retorna a lista em sentido horario a partir do primeiro."""
    if not order:
        return []
    return [order[0]] + list(reversed(order[1:]))


def run_setup(
    all_peoples: list[str],
    heroes_by_people: dict[str, list[str]],
    choices: dict[int, dict],
    seed: int,
    num_players: int = 4,
    turn_order: list[int] | None = None,
    city_life: int = DEFAULT_CITY_LIFE_START,
    city_life_max: int = DEFAULT_CITY_LIFE_MAX,
    gold_start: int = DEFAULT_STARTING_GOLD,
    magic_start: int = DEFAULT_STARTING_MAGIC,
) -> tuple[GameState, SetupResult]:
    rng = make_rng(seed)
    state = create_empty_state(
        num_players=num_players,
        city_life=city_life,
        city_life_max=city_life_max,
        seed=seed,
        gold_start=gold_start,
        magic_start=magic_start,
    )
    if turn_order is None:
        order = roll_d20_order(rng, num_players)
    else:
        order = list(turn_order)
    state.turn_order = order
    log(state, f"Ordem de turno (anti-horario): {order}")
    povo_order = horario_from(order)
    log(state, f"Ordem de povo (horario): {povo_order}")

    banned: list[str] = []
    reversed_order = list(reversed(order))
    for pid in reversed_order[:2]:
        if "ban" in choices[pid] and choices[pid]["ban"]:
            povo = choices[pid]["ban"]
            banned.append(povo)
            log(state, f"Jogador {pid} banou: {povo}")
    if banned:
        log(state, f"Povos disponiveis: {[p for p in all_peoples if p not in banned]}")
    else:
        log(state, "Nenhum povo banido.")

    chosen_peoples: dict[int, str] = {}
    for pid in povo_order:
        povo = choices[pid]["povo"]
        chosen_peoples[pid] = povo
        get_player(state, pid).people = povo
        log(state, f"Jogador {pid} escolheu: {povo}")

    chosen_heroes: dict[int, str] = {}
    for pid in povo_order:
        povo = choices[pid]["povo"]
        if povo == "mortos_vivos":
            chosen_heroes[pid] = ""
            get_player(state, pid).chosen_hero_id = None
            log(state, f"Jogador {pid} (Mortos-Vivos): escolha de heroi pulada.")
            continue
        raw_hero = choices[pid]["heroi"]
        canonical = heroes.resolve_hero_for_people(povo, raw_hero)
        chosen_heroes[pid] = canonical
        get_player(state, pid).chosen_hero_id = canonical
        log(state, f"Jogador {pid} escolheu heroi: {canonical}")

    state.curuna_id = order[0]
    log(state, f"Curuna inicial: J{state.curuna_id}")

    return state, SetupResult(
        turn_order=order,
        banned_peoples=banned,
        chosen_peoples=chosen_peoples,
        chosen_heroes=chosen_heroes,
    )
'''

# =============================================================
# jessica/main.py - setup 8 povos + 8 feedbacks + UI novas
# =============================================================
FILES["jessica/main.py"] = '''\
"""Jessica - Prototipo v0.4."""
from __future__ import annotations
import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box

from .core.setup import run_setup, roll_d20_order, horario_from
from .core.state import make_rng, get_player
from .core.actions import (
    collect_resources, raise_city_life, summon_troop, summon_hero,
    move_unit, build_monument, buy_artifact_with_gold,
    transmute_artifact_with_magic, sell_artifact, play_artifact,
    resolve_pending_artifact_choice, use_heal, cast_spell, arken_espolia,
    besouro_mandinga, use_or_give_pena, tintin_ficar_invisivel,
    dandara_invisibilidade, luide_vampa_mover, ActionError,
)
from .core.combat import (
    resolve_attack, resolve_attack_day, Attack, CombatError,
    _effective_max_attacks, _attacks_used,
)
from .core.turn import start_turn, start_player_day, day_order, end_day, end_turn
from .core.constants import (
    CITY_HOUSES, CENTER, TroopArchetype, Phase, DEFAULT_SEED,
    TROOP_MAX_LIFE, RESOURCES_PER_DAY, CITY_LIFE_COST_GOLD,
    MONUMENT_COST_GOLD,
    ARTIFACT_GOLD_COST, ARTIFACT_MAGIC_COST, ARTIFACT_SELL_GOLD,
    DEFAULT_CITY_LIFE_START, DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC,
)
from .core.models import Hero, Troop
from .core.artifacts import card_display, get_definition, ARTIFACT_CATALOG
from .core.serialize import state_to_dict, state_from_dict
from .core import artifacts_effects, peoples, heroes, spells as spells_mod


console = Console()

PEOPLES = ["humanos", "anoes", "orcs", "fadas",
           "vampiros", "lobisomens", "gigantes", "mortos_vivos"]

HEROES_BY_PEOPLE = {
    "humanos": ["Miyamoto Musashi", "Besouro Mangangá", "Iúna"],
    "anoes": ["Barbadourada", "Ori", "Os 7 Anões"],
    "orcs": ["Ga'Roche", "Arken", "Vovó Gamba"],
    "fadas": ["Ainai", "Valendar", "Luna"],
    "vampiros": ["Dracula", "Dandara", "Luide Vampa"],
    "lobisomens": ["Lupã", "Cigana", "Luarado"],
    "gigantes": ["João Grandão", "Pé Descalço", "Caroço"],
    "mortos_vivos": [],
}

PASSIVA_DESC = {
    "humanos": "Roca de Quilombo: rola 1D4 (+1 por Pena ativa) toda manha.",
    "anoes": "Mineiro Carreiro: +1 Ouro por unidade ana viva, toda manha.",
    "orcs": "Berco de Guerreiros: -1 Magia em invocacoes. Arquetipo extra.",
    "fadas": "Asas Encantadas: +1 Magia ao mover. Herois ganham artefato ao matar Heroi.",
    "vampiros": "Sede de Sangue: mata -> cura 2. Empata -> sobrevive com 2. Nao vale contra Cidades.",
    "lobisomens": "Maldicao da Lua: em Lua Cheia, dobro de dano. Unidades mortas ficam infectadas.",
    "gigantes": "Estatura Colossal: herois custam 4 Magia. Turnos x4 dobram vida de Joao e Pe.",
    "mortos_vivos": "Heróis custam 2 Magia, sem escolha no setup. Os 3 disponiveis na partida.",
}

FEITICO_DESC = {
    "resistencia": "Resistencia: de Resistencia a um aliado ate o fim do turno.",
    "armadura_de_ouro": "Armadura de Ouro: cap X de ouro por hit.",
    "espoliar": "Espoliar: +2 Ouro por Cidade inimiga ocupada.",
    "sonho_lucido": "Sonho Lucido: troca naipe do proximo artefato.",
    "transformar_morcego": "Transformar em Morcego: 1 aliado anda 2x (ou 1x se recem-invocado).",
    "licantropo": "Licantropo: 1 unidade sua vira Lobisomem ate fim do turno.",
    "linhagem_ancestral": "Linhagem Ancestral: ativa o feitico de 1 heroi Gigante vivo.",
    "levantar_mortos": "Levantar os Mortos: escolha 2 tropas e invoque com 1 de vida.",
}

HERO_ABILITY_DESC = {
    "miyamoto": "Invencivel sob o Sol: ataca de Dia. +vida max ao matar. 2 ataques se for o mais forte.",
    "besouro": "o Maioral: dobro + resistencia vs >=. Mandinga: artefato na Noite.",
    "iuna": "Aguia Negra: 1 de dano fixo recebido. 1D4 ao atacar. Adiciona 4 Penas.",
    "barbadourada": "Filho das Cachoeiras: +1 Magia por artefato na mao.",
    "ori": "Velho Mestre Ferreiro: ele + aliados na casa ganham Resistencia.",
    "seven_dwarves": "Os 7 Anoes: 7 herois em corrente. Sem Tropas.",
    "dain": "Alergico: atacante morre no fim da Noite.",
    "buin": "Dengoso: nao pode ser atacado por Herois.",
    "bein": "Soneca: quem for atacado dorme ate os Anoes serem Curuna.",
    "boin": "Feliz: ve 2, escolhe 1 ao comprar/transmutar.",
    "tintin": "Bobao: fica Invisivel (recarga 1 turno).",
    "don": "Zangado: 1 ataque extra por Anao proximo.",
    "din": "Mestre: Anoes proximos atacam Cidades.",
    "garoche": "Rei do Sertao: executa sem aliados proximos. +1 vida por execucao.",
    "arken": "Cacador: Espoliar todo Dia.",
    "vovo_gamba": "Protetora: tropas na casa dela +1 dano. Escolhe posicao no local.",
    "ainai": "Fada da Vinganca: teleporta para onde Fada/Elfo morreu. +1 Magia.",
    "valendar": "Rainha Maga: substitui Sonho Lucido por bonus de naipe.",
    "luna": "Sonhadora: Sonho Lucido multi. Retorna ao local de origem.",
    "dracula": "Dracula: mata -> empala. Mata -> feitico sai da recarga.",
    "dandara": "Dandara: torna ela + aliados da casa invisiveis.",
    "luide_vampa": "Luide Vampa: ativa movimento noturno para aliados.",
    "lupa_lider": "Lupa Lider: em Lua Cheia, +Resistencia a todos os Lobisomens.",
    "cigana": "Cigana: em Lua Cheia, ataca Cidades e torna todos invisiveis.",
    "luarado": "Luarado: em Lua Cheia/transformado, anda 2x e infecta por dano.",
    "joao_grandao": "Joao Grandao: Presenca Magnetica forca ataques inimigos.",
    "pe_descalco": "Pe Descalco: +1 ataque sempre. Grito de Guerra: aliados x2 dano.",
    "caroco": "Caroco: gratis no turno 1. Multiplos Carocos gerados. Cabaca Cheia.",
    "cobra": "Cobra: herois mortos retornam como Espectros por 1 turno.",
    "zoia": "Zoia: 2 tropas extras (Ghoul e Esqueleto com 1 vida).",
    "cova_rasa": "Cova Rasa: amaldicoa inimigos proximos no inicio da Noite.",
}


class RestartGame(Exception):
    pass


def house_display(state, house: str) -> str:
    if house == CENTER:
        return "Centro"
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        return f"Cidade {get_player(state, pid).name}"
    return house


def house_short(state, house: str) -> str:
    if house == CENTER:
        return "Centro"
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        p = get_player(state, pid)
        return f"Cidade J{pid} - {p.name} ({p.people})"
    return house


def _get_actions(state, player) -> list[tuple[str, str, str]]:
    magic_reduction = peoples.magic_cost_reduction(player)
    troop_cost = max(0, 1 - magic_reduction)
    hero_cost = peoples.hero_summon_cost(player)
    sp = spells_mod.spell_for_people(player.people)

    r = []
    r.append(("Acoes", "1", "Coletar recursos (2)"))
    r.append(("Acoes", "2", f"Subir vida da Cidade ({CITY_LIFE_COST_GOLD} Ouro/+1)"))
    if not peoples.has_7_dwarves_chosen(player):
        r.append(("Acoes", "3", f"Invocar Tropa ({troop_cost} Magia + X Ouro)"))
    else:
        r.append(("Acoes", "3", "[bloqueado] Sem tropas (7 Anoes)"))
    if player.people == "mortos_vivos":
        r.append(("Acoes", "4", f"Invocar Heroi ({hero_cost} Magia, escolher agora)"))
    elif player.chosen_hero_id == "seven_dwarves":
        alive_ids = {u.hero_id for u in player.units if isinstance(u, Hero) and u.is_alive()}
        nxt = heroes.next_dwarf_to_summon(alive_ids)
        label = f"Invocar Heroi (proximo: {heroes.hero_name(nxt) if nxt else 'nenhum'})"
        r.append(("Acoes", "4", label))
    elif player.chosen_hero_id == "caroco":
        r.append(("Acoes", "4", "Invocar Caroco (4 Magia se algum morreu)"))
    else:
        r.append(("Acoes", "4", f"Invocar Heroi ({hero_cost} Magia)"))
    r.append(("Acoes", "5", "Mover unidade"))
    r.append(("Acoes", "6", f"Construir Monumento ({MONUMENT_COST_GOLD} Ouro)"))

    r.append(("Artefatos", "7", f"Comprar com Ouro ({ARTIFACT_GOLD_COST})"))
    r.append(("Artefatos", "8", f"Transmutar com Magia ({ARTIFACT_MAGIC_COST})"))
    r.append(("Artefatos", "9", f"Vender ({ARTIFACT_SELL_GOLD} Ouro)"))
    r.append(("Artefatos", "a", "Jogar artefato da mao"))

    if sp:
        cd_str = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd_str = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        label = f"Lancar feitico: {sp.name}{cd_str}"
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            label += " (bloqueado)"
        r.append(("Especiais", "f", label))

    miyamoto_atks = peoples.miyamoto_attacks_remaining(state, player)
    if miyamoto_atks > 0:
        r.append(("Especiais", "d", f"Miyamoto: atacar de Dia ({miyamoto_atks})"))

    arken = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "arken"), None)
    if arken is not None and player.arken_espolia_used_turn != state.turn:
        r.append(("Especiais", "e", "Arken: Espoliar"))

    tintin = next((u for u in player.units
                   if isinstance(u, Hero) and u.is_alive() and u.hero_id == "tintin"), None)
    if tintin is not None:
        cd = tintin.statuses.get("tintin_cooldown_until_turn", -1)
        if cd <= state.turn:
            r.append(("Especiais", "t", "Tin Tin: ficar Invisivel"))

    dandara = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "dandara"), None)
    if dandara is not None:
        cd = dandara.statuses.get("dandara_cooldown_until_turn", -1)
        if cd <= state.turn:
            r.append(("Especiais", "y", "Dandara: invisibilidade do grupo"))

    luide = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa"), None)
    if luide is not None and not player.has_cast_spell_this_turn:
        r.append(("Especiais", "z", "Luide Vampa: ativar movimento noturno"))

    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"), None)
    if besouro is not None and player.besouro_mandinga_used_turn != state.turn and player.hand:
        # Mandinga e na Noite, mas por simplicidade deixamos como opcao no Dia tambem.
        pass

    if player.pending_heals > 0:
        r.append(("Especiais", "h", f"Usar cura pendente ({player.pending_heals})"))

    r.append(("Info", "r", f"Resumo"))
    r.append(("Info", "m", "Mapa"))
    r.append(("Info", "l", "Loja"))
    r.append(("Info", "k", "Habilidades"))
    r.append(("Info", "v", "Estudar campo de batalha"))
    r.append(("Info", "j", "Historico de acoes"))
    r.append(("Info", "n", "Artefatos ativos"))

    r.append(("Sistema", "u", "Colher de cha (refazer meu dia)"))
    r.append(("Sistema", "w", "Mola (jogador anterior)"))
    r.append(("Sistema", "x", "Reiniciar partida"))
    return r


def pick_index(prompt: str, options: list[str]) -> int:
    table = Table(box=box.SIMPLE)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Opcao")
    for i, opt in enumerate(options, 1):
        table.add_row(str(i), opt)
    console.print(table)
    while True:
        try:
            n = IntPrompt.ask(prompt, default=1)
            if 1 <= n <= len(options):
                return n - 1
        except Exception:
            pass
        console.print(f"[red]Escolha entre 1 e {len(options)}[/red]")


def valid_destinations(state, unit) -> list[str]:
    if unit.house.startswith("city_"):
        return [CENTER]
    if unit.house == CENTER:
        return [h for h in CITY_HOUSES
                if get_player(state, int(h.split("_")[1])).city.is_alive()]
    return []


def _ask_int(prompt: str, default: int, min_val: int = 0, max_val: int = 999) -> int:
    while True:
        try:
            v = IntPrompt.ask(prompt, default=default)
            if min_val <= v <= max_val:
                return v
        except Exception:
            pass
        console.print(f"[red]Valor entre {min_val} e {max_val}.[/red]")


def setup_ui():
    console.print(Panel.fit(
        "[bold cyan]JESSICA[/bold cyan]\\n"
        "[italic]Prototipo v0.4 - 8 povos[/italic]",
        border_style="cyan"))
    console.print()
    seed = DEFAULT_SEED
    console.print(f"[dim]Seed: {seed}[/dim]\\n")
    console.print("[bold]Configuracao da partida[/bold]\\n")
    city_life = _ask_int(f"Vida inicial da Cidade [{DEFAULT_CITY_LIFE_START}]",
                         default=DEFAULT_CITY_LIFE_START, min_val=1, max_val=100)
    city_life_max = _ask_int(f"Vida maxima da Cidade [{DEFAULT_CITY_LIFE_MAX}]",
                             default=DEFAULT_CITY_LIFE_MAX, min_val=city_life, max_val=100)
    gold_start = _ask_int(f"Ouro inicial [{DEFAULT_STARTING_GOLD}]",
                          default=DEFAULT_STARTING_GOLD, min_val=0, max_val=999)
    magic_start = _ask_int(f"Magia inicial [{DEFAULT_STARTING_MAGIC}]",
                           default=DEFAULT_STARTING_MAGIC, min_val=0, max_val=999)
    console.print()
    rng = make_rng(seed)
    order = roll_d20_order(rng, 4)
    povo_order = horario_from(order)
    table = Table(title="Ordem do D20 (anti-horario - ordem de JOGO)", box=box.SIMPLE)
    table.add_column("Posicao", justify="right")
    table.add_column("Jogador", justify="right")
    for i, pid in enumerate(order, 1):
        table.add_row(str(i), f"Jogador {pid}")
    console.print(table)
    table2 = Table(title="Ordem de ESCOLHA DE POVO (horario)", box=box.SIMPLE)
    table2.add_column("Posicao", justify="right")
    table2.add_column("Jogador", justify="right")
    for i, pid in enumerate(povo_order, 1):
        table2.add_row(str(i), f"Jogador {pid}")
    console.print(table2)
    console.print()
    console.print("[bold]Nomes dos jogadores[/bold]\\n")
    names: dict[int, str] = {}
    for pid in range(1, 5):
        names[pid] = Prompt.ask(f"Nome do Jogador {pid}", default=f"Jogador {pid}")
    console.print()
    choices: dict[int, dict] = {}
    console.print("[bold]Escolha de povos (sentido horario)[/bold]\\n")
    available_peoples = list(PEOPLES)
    for pid in povo_order:
        console.print(f"Vez de [bold]{names[pid]}[/bold] (Jogador {pid}).")
        idx = pick_index("Povo", available_peoples)
        chosen = available_peoples[idx]
        available_peoples.remove(chosen)
        choices[pid] = {"povo": chosen}
        console.print(f"[green]{names[pid]} escolheu: {chosen}[/green]\\n")
    console.print("[bold]Escolha de herois[/bold]\\n")
    for pid in povo_order:
        povo = choices[pid]["povo"]
        if povo == "mortos_vivos":
            console.print(f"[bold]{names[pid]}[/bold] (Mortos-Vivos): sem escolha de heroi.\\n")
            choices[pid]["heroi"] = ""
            continue
        herois = HEROES_BY_PEOPLE[povo]
        console.print(f"Vez de [bold]{names[pid]}[/bold] ({povo}).")
        idx = pick_index("Heroi", herois)
        choices[pid]["heroi"] = herois[idx]
        console.print(f"[green]{names[pid]} escolheu: {herois[idx]}[/green]\\n")
    state, _ = run_setup(
        all_peoples=PEOPLES, heroes_by_people=HEROES_BY_PEOPLE,
        choices=choices, seed=seed, turn_order=order,
        city_life=city_life, city_life_max=city_life_max,
        gold_start=gold_start, magic_start=magic_start,
    )
    for p in state.players:
        p.name = names[p.id]
    return state


def show_state_for_player(state, pid: int) -> None:
    player = get_player(state, pid)
    city = player.city
    mark = " [bold yellow]<- CURUNA[/bold yellow]" if state.curuna_id == pid else ""
    hero_display = "-"
    if player.chosen_hero_id:
        try:
            hd = heroes.get_hero(player.chosen_hero_id)
            hero_display = f"{hd.name} ({hd.life})"
        except KeyError:
            hero_display = player.chosen_hero_id
    elif player.people == "mortos_vivos":
        hero_display = "(livre - escolhe na invocacao)"
    sp = spells_mod.spell_for_people(player.people)
    sp_str = ""
    if sp:
        cd = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        sp_str = f" | Feitico: {sp.name}{cd}"

    console.print(f"[bold]{player.name}[/bold]{mark} - Povo: {player.people} - Heroi: {hero_display}{sp_str}")
    console.print(f"Cidade: vida {city.life}/{city.life_max} | Ouro: {city.gold} | Magia: {city.magic} | Mon: {'sim' if city.has_monument else 'nao'}")

    if player.units:
        table = Table(title="Suas unidades", box=box.SIMPLE)
        table.add_column("ID"); table.add_column("Tipo"); table.add_column("Local")
        table.add_column("Vida", justify="right"); table.add_column("Flags", justify="left")
        for u in player.units:
            if isinstance(u, Hero):
                kind = f"Heroi {heroes.hero_name(u.hero_id)}"
            else:
                kind = f"Tropa {u.archetype.value}"
            flags = []
            if u.double_damage: flags.append("2xdano")
            if u.resistance_stacks: flags.append(f"Resx{u.resistance_stacks}")
            if u.original_owner_id is not None: flags.append("ctrl")
            if u.statuses.get("cannot_attack_on_turn") == state.turn: flags.append("sem ataque")
            if u.statuses.get("sono_until_turn", -1) > state.turn: flags.append("dormindo")
            if u.statuses.get("invisivel_until_turn", -1) >= state.turn: flags.append("invisivel")
            if u.statuses.get("lobisomem_until_turn", -1) >= state.turn: flags.append("lobisomem")
            if u.statuses.get("morcego_until_turn", -1) >= state.turn: flags.append("morcego")
            if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn: flags.append("amaldicoado")
            flags_str = ", ".join(flags) if flags else "-"
            table.add_row(u.id, kind, house_short(state, u.house),
                          f"{u.life}/{u.life_max}", flags_str)
        console.print(table)
    else:
        console.print("[dim]Sem unidades.[/dim]")
    console.print()


def _strip_markup(s: str) -> str:
    return re.sub(r"\\[/?[^\\]]*\\]", "", s)


def _pad(text: str, width: int) -> str:
    plain_len = len(_strip_markup(text))
    pad = max(0, width - plain_len)
    left = pad // 2
    right = pad - left
    return " " * left + text + " " * right


def _city_cell_lines(state, pid: int, width: int) -> list[str]:
    player = get_player(state, pid)
    city = player.city
    mark = " *" if state.curuna_id == pid else ""
    povo = player.people[:8]
    title = f"J{pid} {player.name[:8]}{mark}"
    sub = f"({povo})"
    vida = f"Cidade {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"
    units = []
    for u in player.units:
        if u.house == f"city_{pid}":
            kind = "H" if isinstance(u, Hero) else "T"
            units.append(f"{kind}{u.life}")
    units_str = ", ".join(units) if units else "[dim]-[/dim]"
    return [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width),
            _pad(vida, width), _pad(units_str, width)]


def _center_cell_lines(state, width: int) -> list[str]:
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == CENTER:
                kind = "H" if isinstance(u, Hero) else "T"
                units.append(f"{p.name[:4]}-{kind}{u.life}")
    lines = [_pad("[bold]CENTRO[/bold]", width), _pad("", width)]
    if units:
        for u in units:
            lines.append(_pad(u, width))
    else:
        lines.append(_pad("[dim]-[/dim]", width))
    return lines


def _pad_to_height(lines: list[str], height: int, width: int) -> list[str]:
    while len(lines) < height:
        lines.append(" " * width)
    return lines[:height]


def show_map(state) -> None:
    w = 22
    j1 = _city_cell_lines(state, 1, w); j2 = _city_cell_lines(state, 2, w)
    j3 = _city_cell_lines(state, 3, w); j4 = _city_cell_lines(state, 4, w)
    center = _center_cell_lines(state, w)
    height = max(len(j1), len(j2), len(j3), len(j4), len(center), 3)
    j1 = _pad_to_height(j1, height, w); j2 = _pad_to_height(j2, height, w)
    j3 = _pad_to_height(j3, height, w); j4 = _pad_to_height(j4, height, w)
    center = _pad_to_height(center, height, w)
    empty = [" " * w for _ in range(height)]
    sep = " | "
    line_sep = "-" * (w * 3 + 6)
    for i in range(height):
        console.print(empty[i] + sep + j3[i] + sep + empty[i], highlight=False)
    console.print(line_sep, highlight=False)
    for i in range(height):
        console.print(j4[i] + sep + center[i] + sep + j2[i], highlight=False)
    console.print(line_sep, highlight=False)
    for i in range(height):
        console.print(empty[i] + sep + j1[i] + sep + empty[i], highlight=False)
    curuna = get_player(state, state.curuna_id)
    console.print()
    console.print(f"[bold yellow]* Curuna: {curuna.name}[/bold yellow]")
    console.print(f"[dim]Loja: {state.shop.size()} cartas[/dim]\\n")


def show_resumo(state) -> None:
    table = Table(title=f"Resumo - Turno {state.turn} ({state.phase.value})", box=box.ROUNDED)
    table.add_column("Jogador")
    table.add_column("Povo")
    table.add_column("Heroi")
    table.add_column("Vida", justify="right")
    table.add_column("Ouro", justify="right")
    table.add_column("Magia", justify="right")
    table.add_column("Mao", justify="right")
    table.add_column("Mon.", justify="center")
    for p in state.players:
        mark = " *" if state.curuna_id == p.id else ""
        alive = p.city.is_alive()
        heroi = "-"
        if p.people == "mortos_vivos":
            vivos = [u for u in p.units if isinstance(u, Hero) and u.is_alive()]
            if vivos:
                heroi = ", ".join(heroes.hero_name(u.hero_id) for u in vivos)
            else:
                heroi = "(livre)"
        elif p.chosen_hero_id:
            try:
                heroi = heroes.hero_name(p.chosen_hero_id)
            except KeyError:
                heroi = p.chosen_hero_id
        table.add_row(
            f"{p.name}{mark}" if alive else f"[red]{p.name} (morto)[/red]",
            p.people or "-",
            heroi,
            f"{p.city.life}/{p.city.life_max}" if alive else "-",
            str(p.city.gold) if alive else "-",
            str(p.city.magic) if alive else "-",
            str(len(p.hand)),
            "sim" if p.city.has_monument else "-")
    console.print(table)


def show_loja(state) -> None:
    from collections import Counter
    counts = Counter(state.shop.deck)
    table = Table(title=f"Loja - {state.shop.size()} cartas", box=box.ROUNDED)
    table.add_column("Carta"); table.add_column("Qtd", justify="right")
    for cid in sorted(ARTIFACT_CATALOG.keys()):
        table.add_row(card_display(cid), str(counts.get(cid, 0)))
    console.print(table)


def show_active_artifacts(state) -> None:
    table = Table(title="Artefatos ativos", box=box.ROUNDED)
    table.add_column("Jogador"); table.add_column("Carta"); table.add_column("Detalhes")
    found = False
    for p in state.players:
        for a in p.field_artifacts:
            found = True
            extra = ", ".join(f"{k}={v}" for k, v in a.extra.items()) if a.extra else "-"
            table.add_row(p.name, card_display(a.card_id), extra)
    if not found:
        console.print("[dim]Nenhum artefato ativo.[/dim]")
    else:
        console.print(table)


def show_habilidades(state, pid: int) -> None:
    player = get_player(state, pid)
    console.print(Panel.fit(
        f"[bold]{player.name}[/bold] - Povo: [cyan]{player.people}[/cyan]",
        border_style="cyan"))
    console.print("[bold]Passiva do povo[/bold]")
    console.print(PASSIVA_DESC.get(player.people, "-"))
    sp = spells_mod.spell_for_people(player.people)
    console.print("\\n[bold]Feitico[/bold]")
    if sp is None:
        console.print("-")
    else:
        desc = FEITICO_DESC.get(sp.spell_id, sp.description)
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            desc += " [Valendar ativa - bloqueado]"
        console.print(desc)
        if state.turn < player.spell_cooldown_until_turn:
            console.print(f"[yellow]Recarga: {player.spell_cooldown_until_turn - state.turn} turno(s)[/yellow]")
    console.print("\\n[bold]Herois do jogador[/bold]")
    has_any = False
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive():
            has_any = True
            hd = heroes.get_hero(u.hero_id)
            console.print(f"  [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_short(state, u.house)}")
            console.print(f"    {HERO_ABILITY_DESC.get(u.hero_id, hd.name)}")
    if not has_any:
        console.print("  [dim](nenhum)[/dim]")
    console.print("\\n[bold]Herois dos outros (em campo)[/bold]")
    has_other = False
    for other in state.players:
        if other.id == pid:
            continue
        for u in other.units:
            if isinstance(u, Hero) and u.is_alive():
                has_other = True
                hd = heroes.get_hero(u.hero_id)
                console.print(f"  {other.name}: [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_short(state, u.house)}")
    if not has_other:
        console.print("  [dim](nenhum)[/dim]")


def _inspecionar_local(state, house: str) -> None:
    """Mostra tudo que esta no local."""
    console.print(Panel.fit(f"[bold]Local: {house_short(state, house)}[/bold]",
                            border_style="cyan"))
    # Cidade
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        p = get_player(state, pid)
        console.print(f"Cidade: vida {p.city.life}/{p.city.life_max}")
    # Unidades
    any_unit = False
    for p in state.players:
        for u in p.units:
            if u.house != house or not u.is_alive():
                continue
            any_unit = True
            if isinstance(u, Hero):
                tipo = f"Heroi {heroes.hero_name(u.hero_id)}"
            else:
                tipo = f"Tropa {u.archetype.value}"
            flags = []
            if u.double_damage: flags.append("2xdano")
            if u.resistance_stacks: flags.append(f"Resx{u.resistance_stacks}")
            if u.original_owner_id is not None: flags.append("ctrl")
            if u.statuses.get("sono_until_turn", -1) > state.turn: flags.append("dormindo")
            if u.statuses.get("invisivel_until_turn", -1) >= state.turn: flags.append("invisivel")
            if u.statuses.get("lobisomem_until_turn", -1) >= state.turn: flags.append("lobisomem")
            if u.statuses.get("morcego_until_turn", -1) >= state.turn: flags.append("morcego")
            if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn: flags.append("amaldicoado")
            flags_str = ", ".join(flags) if flags else "-"
            console.print(f"  {p.name} | {u.id} ({tipo}) | vida {u.life}/{u.life_max} | {flags_str}")
    if not any_unit:
        console.print("  [dim](vazio)[/dim]")


def estudar_campo(state) -> None:
    options = []
    labels = []
    for h in CITY_HOUSES:
        pid = int(h.split("_")[1])
        p = get_player(state, pid)
        labels.append(f"Cidade J{pid} - {p.name} ({p.people})")
        options.append(h)
    labels.append("Centro do mapa")
    options.append(CENTER)
    idx = pick_index("Local", labels)
    _inspecionar_local(state, options[idx])


def historico(state) -> None:
    log_lines = state.event_log
    if not log_lines:
        console.print("[dim]Nenhum evento registrado.[/dim]")
        return
    N = 20
    while True:
        chunk = log_lines[-N:] if len(log_lines) > N else log_lines
        table = Table(title=f"Historico (ultimas {len(chunk)} de {len(log_lines)})", box=box.SIMPLE)
        table.add_column("Linha")
        for line in chunk:
            table.add_row(line)
        console.print(table)
        if len(log_lines) <= N:
            break
        ans = Prompt.ask("Mostrar mais 20? (s/n)", choices=["s", "n"], default="n")
        if ans != "s":
            break
        N += 20


def menu_player_actions(state, player) -> str:
    actions = _get_actions(state, player)
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Secao", style="dim")
    table.add_column("Tecla", style="cyan", justify="center")
    table.add_column("Acao")
    current = None
    for section, key, label in actions:
        if section != current:
            table.add_section()
            current = section
        table.add_row(section, key, label)
    console.print(table)
    valid_keys = [k for _, k, _ in actions] + ["0"]
    return Prompt.ask("Acao (0 = Passar a vez)", choices=valid_keys, default="0")


def _ask_choice_for_artifact(state, pid: int, card_id: str) -> dict:
    player = get_player(state, pid)
    ctype = artifacts_effects.choice_type(card_id)
    if ctype == "own_unit":
        if not player.units:
            raise ActionError(f"{card_display(card_id)} precisa de alvo.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        return {"unit_id": player.units[pick_index("Alvo", labels)].id}
    if ctype == "any_unit":
        all_units, labels = [], []
        for other in state.players:
            if not other.city.is_alive():
                continue
            for u in other.units:
                all_units.append(u)
                labels.append(f"{u.id} de {other.name} ({u.life}/{u.life_max}, {house_short(state, u.house)})")
        if not all_units:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        return {"unit_id": all_units[pick_index("Alvo", labels)].id}
    if ctype == "any_player":
        others = [p for p in state.players if p.id != pid and p.city.is_alive()]
        if not others:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        labels = [f"{p.name} (J{p.id})" for p in others]
        return {"target_player_id": others[pick_index("Alvo", labels)].id}
    if ctype == "any_enemy_unit":
        all_units, labels = [], []
        for other in state.players:
            if other.id == pid or not other.city.is_alive():
                continue
            for u in other.units:
                all_units.append(u)
                labels.append(f"{u.id} de {other.name} ({u.life}/{u.life_max})")
        if not all_units:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        return {"unit_id": all_units[pick_index("Alvo", labels)].id}
    if ctype == "people_hero":
        herois = HEROES_BY_PEOPLE.get(player.people, [])
        disponiveis = []
        for h in herois:
            hid = heroes.resolve_hero_for_people(player.people, h)
            if hid == player.chosen_hero_id:
                continue
            if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == hid
                   for u in player.units):
                continue
            disponiveis.append(h)
        if player.chosen_hero_id == "seven_dwarves":
            disponiveis = []
        if not disponiveis:
            raise ActionError("Todos os outros herois usados.")
        return {"hero_id": disponiveis[pick_index("Heroi", disponiveis)]}
    if ctype == "house":
        options = [h for h in CITY_HOUSES
                   if get_player(state, int(h.split("_")[1])).city.is_alive()]
        options.append(CENTER)
        labels = [house_short(state, h) for h in options]
        return {"house": options[pick_index("Casa", labels)]}
    return {}


def _resolve_pending_choice_if_any(state, pid: int) -> None:
    player = get_player(state, pid)
    pending = player.pending_artifact_choice
    if not pending:
        return
    if pending["kind"] == "J_D":
        console.print(f"[yellow]{player.name}: Jd - escolha 2 de 3.[/yellow]")
        cards = list(pending["cards"])
        table = Table(box=box.SIMPLE)
        table.add_column("#", justify="right"); table.add_column("Carta")
        for i, c in enumerate(cards, 1):
            table.add_row(str(i), card_display(c))
        console.print(table)
        kept: list[str] = []
        while len(kept) < pending["pick"]:
            n = IntPrompt.ask(f"Escolha {len(kept)+1}a", default=1)
            if 1 <= n <= len(cards):
                c = cards[n - 1]
                if c not in kept:
                    kept.append(c)
        resolve_pending_artifact_choice(state, pid, kept_cards=kept)
        return
    if pending["kind"] == "BOIN":
        console.print(f"[yellow]{player.name}: Boin - escolha 1 de 2.[/yellow]")
        cards = list(pending["cards"])
        table = Table(box=box.SIMPLE)
        table.add_column("#", justify="right"); table.add_column("Carta")
        for i, c in enumerate(cards, 1):
            table.add_row(str(i), card_display(c))
        console.print(table)
        idx = IntPrompt.ask("Escolha", default=1)
        if not (1 <= idx <= len(cards)):
            idx = 1
        resolve_pending_artifact_choice(state, pid, kept_cards=[cards[idx - 1]])
        return
    if pending["kind"] == "Q_D":
        amount = pending["dead_unit_max_life"]
        console.print(f"[yellow]{player.name}: Qd - alvo morreu. Recompensa ({amount}):[/yellow]")
        idx = pick_index("Recurso", ["Ouro", "Magia"])
        resolve_pending_artifact_choice(state, pid, resource="gold" if idx == 0 else "magic")
        return


def _pick_target_for_day_attack(state, attacker, player):
    targets = []
    for other in state.players:
        if other.id == player.id or not other.city.is_alive():
            continue
        for u in other.units:
            if u.house == attacker.house and u.is_alive():
                targets.append(u)
    if not targets:
        raise ActionError("Sem alvos no local.")
    labels = [f"{u.id} de {get_player(state, u.owner_id).name} ({u.life}/{u.life_max})" for u in targets]
    return targets[pick_index("Alvo", labels)]


def _handle_pena(state, pid: int, card_id: str) -> None:
    player = get_player(state, pid)
    console.print("[yellow]Voce recebeu uma Pena do Manto Sagrado.[/yellow]")
    if player.people == "humanos":
        use_or_give_pena(state, pid, card_id, give_to_iuna=False)
        return
    iuna_alive = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "iuna"
        for p in state.players for u in p.units
    )
    opts = ["Ficar com a Pena (vendavel por 7 Ouro)"]
    if iuna_alive:
        opts.append("Dar a Iuna e ganhar outro artefato")
    idx = pick_index("Pena:", opts)
    use_or_give_pena(state, pid, card_id, give_to_iuna=(idx == 1))


def _escolher_heroi_mv() -> str:
    opts = ["Cobra, o Paje Caido (3 vida)",
            "Zoia Bulbo Negro (2 vida)",
            "Cova Rasa da Terra Funda (1 vida)"]
    idx = pick_index("Escolher heroi Mortos-Vivos", opts)
    return ["cobra", "zoia", "cova_rasa"][idx]


def handle_action(state, pid: int, choice: str) -> str | None:
    player = get_player(state, pid)
    if choice == "1":
        gold = IntPrompt.ask(f"Ouro (0 a {RESOURCES_PER_DAY})", default=RESOURCES_PER_DAY)
        if gold < 0 or gold > RESOURCES_PER_DAY:
            raise ActionError("Fora do intervalo.")
        collect_resources(state, pid, gold, RESOURCES_PER_DAY - gold)
        console.print("[green]Coleta ok.[/green]")
    elif choice == "2":
        raise_city_life(state, pid, IntPrompt.ask("Vezes", default=1))
        console.print("[green]Vida ok.[/green]")
    elif choice == "3":
        if peoples.has_7_dwarves_chosen(player):
            raise ActionError("Sem Tropas (7 Anoes).")
        archetypes = peoples.available_archetypes(player)
        labels = [f"{a.value} (max {TROOP_MAX_LIFE[a.value]})" for a in archetypes]
        archetype = archetypes[pick_index("Arquetipo", labels)]
        max_life = TROOP_MAX_LIFE[archetype.value]
        life = IntPrompt.ask(f"Vida (1 a {max_life})", default=max_life)
        summon_troop(state, pid, archetype, life)
        console.print("[green]Tropa ok.[/green]")
    elif choice == "4":
        if player.people == "mortos_vivos":
            hid = _escolher_heroi_mv()
            summon_hero(state, pid, force_hero_id=hid)
        else:
            summon_hero(state, pid)
        console.print("[green]Heroi ok.[/green]")
    elif choice == "5":
        units = [u for u in player.units if u.moves_this_turn < u.max_moves_this_turn]
        if not units:
            raise ActionError("Sem unidades.")
        idx = pick_index("Unidade", [f"{u.id} ({house_short(state, u.house)}, {u.life})" for u in units])
        unit = units[idx]
        dests = valid_destinations(state, unit)
        if not dests:
            raise ActionError("Sem destinos.")
        labels = ["Cancelar"] + [house_short(state, d) for d in dests]
        idx2 = pick_index("Destino", labels)
        if idx2 == 0:
            console.print("[yellow]Movimento cancelado.[/yellow]")
            return None
        move_unit(state, pid, unit.id, dests[idx2 - 1])
        console.print("[green]Movimento ok.[/green]")
    elif choice == "6":
        build_monument(state, pid)
        console.print("[green]Monumento ok.[/green]")
    elif choice == "7":
        card = buy_artifact_with_gold(state, pid)
        if card is None:
            _resolve_pending_choice_if_any(state, pid)
            return None
        console.print(f"[green]Comprou: {card_display(card)}[/green]")
        if card == "PENA":
            _handle_pena(state, pid, card)
    elif choice == "8":
        card = transmute_artifact_with_magic(state, pid)
        if card is None:
            _resolve_pending_choice_if_any(state, pid)
            return None
        console.print(f"[green]Transmutou: {card_display(card)}[/green]")
        if card == "PENA":
            _handle_pena(state, pid, card)
    elif choice == "9":
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = [card_display(c) for c in player.hand]
        card = player.hand[pick_index("Vender", labels)]
        sell_artifact(state, pid, card)
        console.print(f"[green]Vendeu: {card_display(card)}[/green]")
    elif choice == "a":
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = [card_display(c) for c in player.hand]
        card = player.hand[pick_index("Jogar", labels)]
        if card == "PENA":
            _handle_pena(state, pid, card)
            return None
        choice_data = _ask_choice_for_artifact(state, pid, card)
        play_artifact(state, pid, card, choice=choice_data)
        console.print(f"[green]Jogou: {card_display(card)}[/green]")
    elif choice == "r":
        show_resumo(state)
    elif choice == "m":
        show_map(state)
    elif choice == "l":
        show_loja(state)
    elif choice == "k":
        show_habilidades(state, pid)
    elif choice == "v":
        estudar_campo(state)
    elif choice == "j":
        historico(state)
    elif choice == "n":
        show_active_artifacts(state)
    elif choice == "d":
        miyamoto = next((u for u in player.units
                         if isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto"), None)
        if miyamoto is None:
            raise ActionError("Miyamoto nao esta vivo.")
        atks = peoples.miyamoto_attacks_remaining(state, player)
        if atks <= 0:
            raise ActionError("Miyamoto ja atacou o maximo.")
        target = _pick_target_for_day_attack(state, miyamoto, player)
        resolve_attack_day(state, Attack(miyamoto.id, "unit", target.id))
        console.print("[green]Ataque diurno executado.[/green]")
    elif choice == "e":
        arken_espolia(state, pid)
        console.print("[green]Arken espoliou.[/green]")
    elif choice == "t":
        tintin_ficar_invisivel(state, pid)
        console.print("[green]Tin Tin invisivel.[/green]")
    elif choice == "y":
        dandara_invisibilidade(state, pid)
        console.print("[green]Dandara invisivel.[/green]")
    elif choice == "z":
        luide_vampa_mover(state, pid)
        console.print("[green]Luide Vampa: movimento noturno ativo.[/green]")
    elif choice == "f":
        sp = spells_mod.spell_for_people(player.people)
        if sp is None:
            raise ActionError("Sem feitico.")
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            raise ActionError("Valendar substitui Sonho Lucido.")
        choice_data: dict = {}
        if sp.spell_id == "resistencia":
            if not player.units:
                raise ActionError("Sem unidades.")
            labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
            choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
        elif sp.spell_id == "armadura_de_ouro":
            choice_data["cap"] = _ask_int("Cap por hit", default=2, min_val=1, max_val=10)
        elif sp.spell_id == "transformar_morcego":
            if not player.units:
                raise ActionError("Sem unidades.")
            labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
            choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
        elif sp.spell_id == "licantropo":
            if not player.units:
                raise ActionError("Sem unidades.")
            labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
            choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
        elif sp.spell_id == "linhagem_ancestral":
            gigantes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()
                        and u.hero_id in ("joao_grandao", "pe_descalco", "caroco")]
            if not gigantes:
                raise ActionError("Sem herois Gigantes vivos.")
            labels = [heroes.hero_name(u.hero_id) for u in gigantes]
            choice_data["hero_id"] = gigantes[pick_index("Heroi", labels)].hero_id
        elif sp.spell_id == "levantar_mortos":
            labels = ["light", "medium", "heavy", "extra", "ghoul", "esqueleto"]
            i1 = pick_index("Arquetipo 1", labels)
            i2 = pick_index("Arquetipo 2", labels)
            choice_data["archetypes"] = [labels[i1], labels[i2]]
        cast_spell(state, pid, choice_data)
        console.print(f"[green]{sp.name} lancado.[/green]")
    elif choice == "h":
        if not player.units:
            raise ActionError("Sem unidades.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        idx = pick_index("Alvo", labels)
        use_heal(state, pid, player.units[idx].id)
        console.print("[green]Cura ok.[/green]")
    elif choice == "u":
        return "undo"
    elif choice == "w":
        return "mola"
    elif choice == "x":
        return "restart"
    return None


def run_player_day(state, pid: int) -> str | None:
    player = get_player(state, pid)
    try:
        _resolve_pending_choice_if_any(state, pid)
    except (ActionError, ValueError) as e:
        console.print(f"[red]Erro pendente: {e}[/red]")
    while True:
        show_state_for_player(state, pid)
        choice = menu_player_actions(state, player)
        if choice == "0":
            player.has_played_day_this_turn = True
            return None
        try:
            result = handle_action(state, pid, choice)
            if result is not None:
                return result
        except (ActionError, CombatError, ValueError) as e:
            console.print(f"[red]Erro: {e}[/red]")
        console.print()


def find_targets(state, unit):
    targets = []
    house = unit.house
    can_attack_city = (not isinstance(unit, Hero)) or unit.hero_can_attack_city
    if isinstance(unit, Hero) and not can_attack_city:
        owner = get_player(state, unit.owner_id)
        for u in owner.units:
            if (isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "din" and u.house == house):
                can_attack_city = True
                break
        if (not can_attack_city and peoples.is_lua_cheia(state, owner.id)
                and owner.people == peoples.PEOPLE_LOBISOMENS):
            for u in owner.units:
                if isinstance(u, Hero) and u.is_alive() and u.hero_id == "cigana" and u.house == house:
                    can_attack_city = True
                    break
    if can_attack_city and house.startswith("city_"):
        target_pid = int(house.split("_")[1])
        if target_pid != unit.owner_id:
            target = get_player(state, target_pid)
            if target.city.is_alive():
                targets.append(("city", str(target_pid),
                                f"Cidade de {target.name} ({target.city.life})"))
    for other in state.players:
        if other.id == unit.owner_id:
            continue
        for u in other.units:
            if u.house == house and u.is_alive():
                if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
                    continue
                kind = "Heroi" if isinstance(u, Hero) else "Tropa"
                targets.append(("unit", u.id,
                                f"{kind} {u.id} de {other.name} ({u.life})"))
    return targets


def prompt_attack(state, unit, targets) -> Attack | None:
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_short(state, unit.house)}")
    options = ["Nao atacar"] + [t[2] for t in targets]
    idx = pick_index("Acao", options)
    if idx == 0:
        return None
    return Attack(unit.id, targets[idx - 1][0], targets[idx - 1][1])


def _try_ainai_teleport(state, player) -> bool:
    ainai = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "ainai"), None)
    if ainai is None:
        return False
    if ainai.statuses.get("ainai_used_this_night") == state.turn:
        return False
    if not state.deaths_this_night:
        return False
    casas = [h for h in state.deaths_this_night if h != ainai.house]
    if not casas:
        return False
    console.print("[yellow]Ainai pode teletransportar para casa com morte nesta Noite.[/yellow]")
    labels = [house_short(state, h) for h in casas]
    idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)
    if idx == 0:
        return False
    destino = casas[idx - 1]
    ainai.house = destino
    ainai.statuses["ainai_used_this_night"] = state.turn
    player.city.magic += 1
    console.print(f"[green]Ainai teleportou para {house_short(state, destino)} (+1 Magia).[/green]")
    return True


def _try_besouro_mandinga(state, player) -> bool:
    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"), None)
    if besouro is None:
        return False
    if player.besouro_mandinga_used_turn == state.turn:
        return False
    if not player.hand:
        return False
    console.print(f"[yellow]{player.name}: Besouro pode usar Mandinga.[/yellow]")
    opts = ["Nao usar"] + [card_display(c) for c in player.hand]
    idx = pick_index("Mandinga:", opts)
    if idx == 0:
        return False
    card = player.hand[idx - 1]
    if card == "PENA":
        console.print("[red]Pena nao pode ser usada via Mandinga.[/red]")
        return False
    choice_data = _ask_choice_for_artifact(state, player.id, card)
    besouro_mandinga(state, player.id, card, choice=choice_data)
    console.print(f"[green]Mandinga: {card_display(card)} jogado.[/green]")
    return True


def _try_luna_return(state, player) -> None:
    luna = next((u for u in player.units
                 if isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"), None)
    if luna is None:
        return
    if "luna_origin_house" not in luna.statuses:
        console.print(f"[dim]{player.name}: Luna nao moveu este turno, nao pode teletransportar.[/dim]")
        return
    origin = luna.statuses["luna_origin_house"]
    console.print(f"[yellow]{player.name}: Luna andou neste turno. Teletransportar de volta para {house_short(state, origin)}?[/yellow]")
    opts = ["Sim", "Nao"]
    idx = pick_index("Luna:", opts)
    if idx == 0:
        luna.house = origin
        luna.statuses.pop("luna_origin_house", None)
        console.print(f"[green]Luna retornou para {house_short(state, origin)}.[/green]")


def _ask_vovo_position(state) -> None:
    for p in state.players:
        vovo = next((u for u in p.units
                     if isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba"), None)
        if vovo is None:
            continue
        console.print(f"[yellow]{p.name}: Vovo - posicao no local ({house_short(state, vovo.house)}).[/yellow]")
        pos = _ask_int("Posicao (1=primeiro, 4=ultimo)", default=1, min_val=1, max_val=4)
        p.vovo_position = pos


def _order_players_for_house(state, pids_here: list[int], house: str) -> list[int]:
    for pid in pids_here:
        p = get_player(state, pid)
        if p.bater_primeiro_turn == state.turn:
            others = [x for x in pids_here if x != pid]
            return [pid] + others
    vovo_owner = None
    for pid in pids_here:
        p = get_player(state, pid)
        for u in p.units:
            if (isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "vovo_gamba" and u.house == house):
                vovo_owner = pid
                break
        if vovo_owner is not None:
            break
    if vovo_owner is None:
        return pids_here
    pos = max(1, min(get_player(state, vovo_owner).vovo_position, len(pids_here)))
    ordered = [pid for pid in pids_here if pid != vovo_owner]
    ordered.insert(pos - 1, vovo_owner)
    return ordered


def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_map(state)
    _ask_vovo_position(state)

    # Luna prompt (antes das declaracoes)
    all_pids = list(day_order(state))
    for pid in all_pids:
        player = get_player(state, pid)
        _try_luna_return(state, player)

    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
            _try_ainai_teleport(state, player)
            _try_besouro_mandinga(state, player)

    house_order = [CENTER, "city_4", "city_3", "city_2", "city_1"]
    for house in house_order:
        pids_here = []
        for pid in all_pids:
            player = get_player(state, pid)
            if any(u.house == house and u.is_alive() for u in player.units):
                pids_here.append(pid)
        if not pids_here:
            continue
        pids_here = _order_players_for_house(state, pids_here, house)
        for pid in pids_here:
            player = get_player(state, pid)
            units_here = [u for u in player.units if u.house == house and u.is_alive()]
            if not units_here:
                continue
            if not any(find_targets(state, u) for u in units_here):
                continue
            console.print(f"[bold]{player.name} declara ataques em {house_short(state, house)}.[/bold]")
            for unit in list(units_here):
                if not unit.is_alive():
                    continue
                while True:
                    targets = find_targets(state, unit)
                    if not targets:
                        break
                    if _attacks_used(unit) >= _effective_max_attacks(state, unit):
                        break
                    atk = prompt_attack(state, unit, targets)
                    if not atk:
                        break
                    before = len(state.event_log)
                    try:
                        resolve_attack(state, atk)
                    except CombatError as e:
                        console.print(f"  [red]Erro: {e}[/red]")
                        break
                    for line in state.event_log[before:]:
                        console.print(f"  {line}")
            console.print()


def show_victory(state) -> None:
    if state.winner_id:
        player = get_player(state, state.winner_id)
        console.print()
        console.print(Panel.fit(
            f"[bold green]VITORIA![/bold green]\\n\\n{player.name} ({player.people}) venceu!",
            border_style="green"))
    else:
        console.print(Panel.fit("[bold red]Empate![/bold red]", border_style="red"))


def _run_one_game() -> None:
    console.clear()
    state = setup_ui()
    while not state.game_over:
        interest = start_turn(state)
        console.rule(f"[bold yellow]TURNO {state.turn} - DIA[/bold yellow]")
        curuna = get_player(state, state.curuna_id)
        console.print(f"[bold yellow]* Curuna: {curuna.name}[/bold yellow]\\n")
        if interest:
            pros = ", ".join(f"{get_player(state, pid).name} (+{g})" for pid, g in interest)
            console.print(f"[yellow]Prosperidade:[/yellow] {pros}\\n")
        skipped = [p.name for p in state.players
                   if p.city.is_alive() and p.skip_day_turn == state.turn]
        if skipped:
            console.print(f"[yellow]Pulados: {', '.join(skipped)}[/yellow]\\n")
        show_map(state)
        console.print()
        day_players = day_order(state)
        snapshots: dict[int, dict] = {}
        i = 0
        while i < len(day_players):
            pid = day_players[i]
            player = get_player(state, pid)
            snapshots[pid] = state_to_dict(state)
            console.rule(f"[bold]Vez de {player.name}[/bold]")
            before = len(state.event_log)
            start_player_day(state, pid)
            for line in state.event_log[before:]:
                console.print(f"  [cyan]{line}[/cyan]")
            if player.skip_day_turn == state.turn:
                player.has_played_day_this_turn = True
                console.print(f"[yellow]{player.name} pulou.[/yellow]")
                i += 1
                continue
            result = run_player_day(state, pid)
            if result == "restart":
                raise RestartGame()
            if result == "undo":
                state = state_from_dict(snapshots[pid])
                console.print("[yellow]Colher de cha: refaz.[/yellow]")
                continue
            if result == "mola":
                if i > 0:
                    i -= 1
                prev = day_players[i]
                state = state_from_dict(snapshots[prev])
                console.print(f"[yellow]Mola: {get_player(state, prev).name} refaz.[/yellow]")
                continue
            i += 1
        end_day(state)
        night_skipped = [p.name for p in state.players
                         if p.city.is_alive() and p.skip_night_turn == state.turn]
        if night_skipped:
            console.print(f"[yellow]Pulados na Noite: {', '.join(night_skipped)}[/yellow]\\n")
        run_night_phase(state)
        if state.game_over:
            break
        end_turn(state)
        if not state.game_over:
            console.input("\\n[dim]Enter...[/dim] ")
            console.clear()
    show_victory(state)


def main() -> None:
    while True:
        try:
            _run_one_game()
        except RestartGame:
            console.print("[yellow]Reiniciando...[/yellow]\\n")
            continue
        except KeyboardInterrupt:
            console.print("\\n[yellow]Interrompido.[/yellow]")
            return
        try:
            again = Prompt.ask("Jogar outra?", choices=["s", "n"], default="n")
        except KeyboardInterrupt:
            return
        if again != "s":
            return
        console.print()


if __name__ == "__main__":
    main()
'''

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
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()