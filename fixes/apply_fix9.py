"""
apply_fix9
- Organiza pastas (fixes/, backups/) e move apply_*.py e _backup_* antigos
- Corrige use_or_give_pena (Pena voltando à mão)
- Corrige testes: encoding UTF-8, contagem da loja, tropa fake no Boin
- Atualiza run_all.py pra usar backups/
Salve em: Downloads/jessica/fixes/apply_fix9.py
"""
from pathlib import Path
from datetime import datetime
import shutil
import sys

# ROOT fica 2 niveis acima porque este script esta em fixes/
ROOT = Path(__file__).parent.parent.resolve()
FIXES_DIR = ROOT / "fixes"
BACKUPS_DIR = ROOT / "backups"
BACKUP_DIR = BACKUPS_DIR / f"apply_fix9_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def reorganize():
    """Cria fixes/, backups/, move apply_*.py e _backup_* antigos."""
    FIXES_DIR.mkdir(exist_ok=True)
    BACKUPS_DIR.mkdir(exist_ok=True)
    print(f"Organizando em: {ROOT}")
    print(f"  fixes/    -> {FIXES_DIR}")
    print(f"  backups/  -> {BACKUPS_DIR}")

    # Move apply_*.py que estao na raiz para fixes/
    this_script = Path(__file__).resolve()
    moved_scripts = 0
    for p in ROOT.glob("apply_*.py"):
        if p.resolve() == this_script:
            continue
        dest = FIXES_DIR / p.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(p), str(dest))
        print(f"  MOVED  {p.name} -> fixes/")
        moved_scripts += 1

    # Move _backup_* que estao na raiz para backups/
    moved_backups = 0
    for p in ROOT.glob("_backup_*"):
        if not p.is_dir():
            continue
        dest = BACKUPS_DIR / p.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(p), str(dest))
        print(f"  MOVED  {p.name}/ -> backups/")
        moved_backups += 1

    print(f"  {moved_scripts} scripts, {moved_backups} backups movidos.\n")


FILES: dict[str, str] = {}

# =============================================================
# jessica/core/actions.py — fix use_or_give_pena
# =============================================================
FILES["jessica/core/actions.py"] = '''\
from __future__ import annotations
from .constants import (
    RESOURCES_PER_DAY, GOLD_INTEREST_DIVISOR, CITY_LIFE_COST_GOLD,
    HERO_SUMMON_COST_MAGIC, TROOP_SUMMON_COST_MAGIC, TROOP_MAX_LIFE,
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
        raise ActionError(f"Cidade destruida.")
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
        raise ActionError(f"Ouro insuficiente (precisa {total_cost}).")
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

    alive_heroes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()]
    if alive_heroes and force_hero_id is None:
        raise ActionError("Ja existe heroi vivo.")
    target_id = force_hero_id if force_hero_id is not None else player.chosen_hero_id
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == target_id
           for u in player.units):
        raise ActionError(f"Heroi {target_id} ja em campo.")

    magic_cost = max(0, HERO_SUMMON_COST_MAGIC - peoples.magic_cost_reduction(player))
    if city.magic < magic_cost:
        raise ActionError(f"Magia insuficiente ({magic_cost}).")
    city.magic -= magic_cost
    hdef = heroes.get_hero(target_id)
    unit_id = f"p{player_id}_hero_{hdef.hero_id}"
    hero = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                life=hdef.life, life_max=hdef.life,
                hero_id=hdef.hero_id, has_moved_this_turn=True)
    player.units.append(hero)
    record_action(state, player_id, "summon_hero", hero_id=hdef.hero_id)
    log(state, f"{player.name} invocou {hdef.name} ({hdef.life}).")
    if hdef.hero_id == "iuna" and not player.pena_added_once:
        any_pena_added = any(p.pena_added_once for p in state.players)
        if not any_pena_added:
            for _ in range(4):
                state.shop.return_card("PENA")
            player.pena_added_once = True
            log(state, "Iuna: 4 Penas do Manto Sagrado adicionadas a Loja.")
    return hero


def move_unit(state: GameState, player_id: int, unit_id: str, destination: str) -> None:
    if destination not in (CENTER, *CITY_HOUSES):
        raise ActionError(f"Destino invalido: {destination}")
    player = get_player(state, player_id)
    unit = next((u for u in player.units if u.id == unit_id and u.is_alive()), None)
    if unit is None:
        raise ActionError(f"Unidade {unit_id} nao encontrada.")
    if unit.moves_this_turn >= unit.max_moves_this_turn:
        raise ActionError("Unidade ja se moveu o maximo neste turno.")
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
            raise ActionError(f"Cidade destruida.")
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
        raise ActionError(f"Alvo nao encontrado.")
    heal = min(2, target.life_max - target.life)
    if heal <= 0:
        raise ActionError(f"{target.id} ja esta cheio.")
    target.life += heal
    player.pending_heals -= 1
    record_action(state, player_id, "use_heal", target=target_unit_id, healed=heal)
    log(state, f"{player.name}: curou {heal} em {target.id} ({target.life}/{target.life_max}).")


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
    log(state, f"{player.name} (Arken): Espoliou {len(occupied_pids)} Cidade(s) - +{gold} Ouro.")
    enemy_houses = {f"city_{pid}" for pid in occupied_pids}
    for u in player.units:
        if isinstance(u, Troop) and u.is_alive() and u.house in enemy_houses:
            healed = min(1, u.life_max - u.life)
            if healed > 0:
                u.life += healed
            u.statuses["cannot_attack_on_turn"] = state.turn
            log(state, f"  {u.id} curou {healed} e nao atacara esta Noite.")
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
        raise ActionError(f"Tin Tin em recarga (ate turno {cd}).")
    tintin.statuses["invisivel_until_turn"] = state.turn
    tintin.statuses["tintin_cooldown_until_turn"] = state.turn + 2
    log(state, f"{player.name}: Tin Tin ficou invisivel ate o fim do turno.")
    record_action(state, player_id, "tintin_invisivel")


def besouro_mandinga(state: GameState, player_id: int, card_id: str,
                     choice: dict | None = None) -> None:
    player = get_player(state, player_id)
    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"),
                   None)
    if besouro is None:
        raise ActionError("Besouro nao esta vivo.")
    if player.besouro_mandinga_used_turn == state.turn:
        raise ActionError("Mandinga ja usada nesta Noite.")
    if card_id not in player.hand:
        raise ActionError(f"{player.name} nao tem {card_id}.")
    play_artifact(state, player_id, card_id, choice=choice or {})
    player.besouro_mandinga_used_turn = state.turn
    log(state, f"{player.name}: Besouro usou Mandinga com {card_display(card_id)}.")


# -------------------------------------------------------------
# Pena
# -------------------------------------------------------------
def use_or_give_pena(state: GameState, player_id: int, card_id: str,
                     give_to_iuna: bool) -> None:
    """
    Humano: vira artefato de campo (permanente).
    Nao-humano + Iuna viva: da a Pena (some do jogo), ganha 1 artefato da Loja.
    Nao-humano sem Iuna: so pode ficar com a Pena (vendavel depois).
    """
    player = get_player(state, player_id)
    if card_id != "PENA":
        raise ActionError("So aplica para Pena.")
    if card_id not in player.hand:
        raise ActionError(f"{player.name} nao tem Pena.")

    # Humano: ativa em campo
    if player.people == "humanos":
        player.hand.remove(card_id)
        player.field_artifacts.append(ArtifactOnField(card_id="PENA", owner_id=player_id))
        log(state, f"{player.name} (Humanos): Pena ativa. Roca ganha +1 dado.")
        record_action(state, player_id, "pena_activate")
        return

    # Nao-humano: dar a Iuna ou ficar
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
            raise ActionError("Iuna nao esta viva. So pode ficar com a Pena.")

        # Remove a Pena da mao (ela vai para Iuna e some do baralho)
        player.hand.remove(card_id)

        # Sorteia 1 artefato ANTES de devolver Pena a loja (se for devolver)
        # Assim a nova carta nao pode ser a propria Pena.
        if not state.shop.is_empty():
            new_card = state.shop.draw_random(state.rng)
            player.hand.append(new_card)
            log(state, f"{player.name} deu a Pena a Iuna e ganhou {card_display(new_card)}.")
        else:
            log(state, f"{player.name} deu a Pena a Iuna (Loja vazia, sem troca).")

        # NAO devolve a Pena a Loja: ela vai para Iuna.
        record_action(state, player_id, "pena_give_iuna")
        return

    # Ficar com a Pena
    log(state, f"{player.name}: ficou com a Pena (sem efeito).")
    record_action(state, player_id, "pena_keep")


# -------------------------------------------------------------
# Feiticos
# -------------------------------------------------------------
def cast_spell(state: GameState, player_id: int, choice: dict | None = None) -> None:
    choice = choice or {}
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruida.")
    if state.turn < player.spell_cooldown_until_turn:
        restantes = player.spell_cooldown_until_turn - state.turn
        raise ActionError(f"Feitico em recarga ({restantes}).")
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
            log(state, f"{player.name}: Sonho Lucido ATIVO (Luna - multiplos).")
        else:
            log(state, f"{player.name}: Sonho Lucido ativo.")
    else:
        raise ActionError(f"Feitico {sp.spell_id} sem implementacao.")

    player.spell_cooldown_until_turn = state.turn + 2
    player.has_cast_spell_this_turn = True
    record_action(state, player_id, "cast_spell", spell=sp.spell_id)


def _spell_resistencia(state: GameState, player, choice: dict) -> None:
    target_id = choice.get("unit_id")
    if not target_id:
        raise ActionError("Precisa alvo.")
    target = next((u for u in player.units if u.id == target_id and u.is_alive()), None)
    if target is None:
        raise ActionError("Alvo nao encontrado.")
    target.resistance_stacks += 1
    log(state, f"{player.name} lancou Resistencia em {target.id} "
               f"(Resx{target.resistance_stacks}).")


def _spell_armadura(state: GameState, player, choice: dict) -> None:
    cap = int(choice.get("cap", 1))
    if cap < 1:
        raise ActionError("Cap deve ser >= 1.")
    player.armor_gold_cap_per_hit = cap
    log(state, f"{player.name} lancou Armadura de Ouro (cap {cap}/hit).")


def _spell_espoliar(state: GameState, player) -> None:
    owned = 0
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        home = f"city_{other.id}"
        if any(u.house == home and u.is_alive() for u in player.units):
            owned += 1
    gold = 2 * owned
    player.city.gold += gold
    log(state, f"{player.name} Espoliou {owned} Cidade(s) - +{gold} Ouro.")


# -------------------------------------------------------------
# Artefatos
# -------------------------------------------------------------
def _has_unit_at_center(state: GameState, player_id: int) -> bool:
    player = get_player(state, player_id)
    return any(u.house == CENTER and u.is_alive() for u in player.units)


def _apply_valendar_bonus(state: GameState, player, card_id: str) -> None:
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
        log(state, "  Valendar C: herois curados ao maximo.")
    elif suit == "D":
        player.vender_por_magia_turn = state.turn
        log(state, "  Valendar O: herois venderao por 7 Magia neste turno.")
    elif suit == "C":
        player.andar_duas_vezes_turn = state.turn
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                u.max_moves_this_turn = 2
                u.has_moved_this_turn = False
                u.moves_this_turn = 0
        log(state, "  Valendar P: herois andarao duas vezes neste turno.")
    elif suit == "S":
        player.bater_primeiro_turn = state.turn
        log(state, "  Valendar E: herois declaram antes nesta Noite.")


def _boin_alive(player) -> bool:
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "boin"
               for u in player.units)


def buy_artifact_with_gold(state: GameState, player_id: int) -> str | None:
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
        log(state, f"{player.name} (Boin): escolha 1 de 2 artefatos.")
        record_action(state, player_id, "buy_artifact_gold_boin")
        return None

    card = state.shop.draw_random(state.rng)
    player.hand.append(card)
    record_action(state, player_id, "buy_artifact_gold", card=card)
    log(state, f"{player.name} comprou: {card_display(card)}.")
    return card


def transmute_artifact_with_magic(state: GameState, player_id: int) -> str | None:
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
        log(state, f"{player.name} (Boin): escolha 1 de 2 artefatos.")
        record_action(state, player_id, "transmute_artifact_magic_boin")
        return None

    card = state.shop.draw_random(state.rng)
    player.hand.append(card)
    record_action(state, player_id, "transmute_artifact_magic", card=card)
    log(state, f"{player.name} transmutou: {card_display(card)}.")
    return card


def sell_artifact(state: GameState, player_id: int, card_id: str) -> None:
    player = get_player(state, player_id)
    if card_id not in player.hand:
        raise ActionError(f"{player.name} nao tem {card_id}.")
    if not _has_unit_at_center(state, player_id):
        raise ActionError("Precisa unidade no Centro.")
    player.hand.remove(card_id)
    if player.vender_por_magia_turn == state.turn:
        player.city.magic += ARTIFACT_SELL_GOLD
        log(state, f"{player.name} vendeu {card_display(card_id)} por {ARTIFACT_SELL_GOLD} Magia.")
    else:
        player.city.gold += ARTIFACT_SELL_GOLD
        log(state, f"{player.name} vendeu {card_display(card_id)} por {ARTIFACT_SELL_GOLD} Ouro.")
    state.shop.return_card(card_id)
    record_action(state, player_id, "sell_artifact", card=card_id)


def play_artifact(state: GameState, player_id: int, card_id: str,
                  target_unit_id: str | None = None,
                  choice: dict | None = None) -> None:
    if choice is None:
        choice = {}
    if target_unit_id is not None:
        choice = {**choice, "unit_id": target_unit_id}

    player = get_player(state, player_id)
    if card_id not in player.hand:
        raise ActionError(f"{player.name} nao tem {card_id}.")

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


def discard_field_artifact(state: GameState, player_id: int, card_id: str) -> None:
    player = get_player(state, player_id)
    for i, a in enumerate(player.field_artifacts):
        if a.card_id == card_id:
            player.field_artifacts.pop(i)
            state.shop.return_card(card_id)
            log(state, f"{player.name}: {card_display(card_id)} voltou a Loja.")
            return
    raise ActionError(f"{player.name} nao tem {card_id} em campo.")


def resolve_pending_artifact_choice(state: GameState, player_id: int,
                                    kept_cards: list[str] | None = None,
                                    resource: str | None = None) -> None:
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
        kept: list[str] = []
        for c in kept_cards:
            if c not in available:
                raise ActionError(f"{c} indisponivel.")
            available.remove(c)
            kept.append(c)
        for c in kept:
            player.hand.append(c)
        for c in available:
            state.shop.return_card(c)
        log(state, f"{player.name}: Jd - escolheu {', '.join(kept)}.")
        player.pending_artifact_choice = None
        discard_field_artifact(state, player_id, pending["card_id"])
        return
    if pending["kind"] == "BOIN":
        if not kept_cards or len(kept_cards) != 1:
            raise ActionError("Boin: escolha exatamente 1 carta.")
        chosen = kept_cards[0]
        if chosen not in pending["cards"]:
            raise ActionError(f"{chosen} nao esta disponivel.")
        player.hand.append(chosen)
        for c in pending["cards"]:
            if c != chosen:
                state.shop.return_card(c)
        log(state, f"{player.name} (Boin): escolheu {card_display(chosen)}.")
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
        res_pt = "Ouro" if resource == "gold" else "Magia"
        log(state, f"{player.name}: Qd - +{amount} {res_pt}.")
        if killer_id is not None and killer_id != player_id:
            killer = get_player(state, killer_id)
            if resource == "gold":
                killer.city.gold += amount
            else:
                killer.city.magic += amount
            log(state, f"{killer.name} (matador) +{amount} {res_pt}.")
        player.pending_artifact_choice = None
        try:
            discard_field_artifact(state, player_id, "Q_D")
        except ActionError:
            pass
        return
    raise ActionError(f"Pendencia desconhecida: {pending['kind']}")
'''

# =============================================================
# tests/_utf8.py — helper para forçar UTF-8 no stdout
# =============================================================
FILES["tests/_utf8.py"] = '''\
"""Forca UTF-8 no stdout/stderr (Windows cp1252 quebra simbolos de naipe)."""
import sys


def setup():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
'''

# =============================================================
# tests/test_artifacts.py — loja tem 24 (12 x 2, PENA fora)
# =============================================================
FILES["tests/test_artifacts.py"] = '''\
"""Testes de artefatos - loja/compra/transmutacao/venda."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    buy_artifact_with_gold, transmute_artifact_with_magic,
    sell_artifact, summon_troop, ActionError,
)
from jessica.core.constants import (
    TroopArchetype, ARTIFACT_GOLD_COST, ARTIFACT_MAGIC_COST,
    ARTIFACT_SELL_GOLD,
)
from jessica.core.artifacts import ARTIFACT_CATALOG, ARTIFACTS_PER_CARD_IN_SHOP


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


def _setup_center_troop(state, pid=1):
    p = state.players[pid - 1]
    p.city.gold = 10
    p.city.magic = 5
    t = summon_troop(state, pid, TroopArchetype.LIGHT, 4)
    t.house = "center"
    return t


def test_shop_initial_size():
    """12 cartas base x 2 = 24. PENA nao esta na Loja ate Iuna ser invocada."""
    state = make_state()
    # Catalogo tem 13 entradas (12 + PENA), mas PENA nao entra no deck inicial
    base_cards = len([k for k in ARTIFACT_CATALOG if k != "PENA"])
    expected = base_cards * ARTIFACTS_PER_CARD_IN_SHOP
    assert state.shop.size() == expected, (
        f"Esperado {expected} cartas, veio {state.shop.size()}"
    )
    print(f"OK  - Loja inicial: {expected} cartas ({base_cards} x {ARTIFACTS_PER_CARD_IN_SHOP})")


def test_buy_with_gold_requires_unit_at_center():
    state = make_state()
    state.players[0].city.gold = 20
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria exigir unidade no Centro")
    except ActionError as e:
        print(f"OK  - Compra sem unidade bloqueada: {e}")


def test_buy_with_gold():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 20
    before_shop = state.shop.size()
    card = buy_artifact_with_gold(state, 1)
    assert card in ARTIFACT_CATALOG
    assert p.city.gold == 20 - ARTIFACT_GOLD_COST
    assert card in p.hand
    assert state.shop.size() == before_shop - 1
    print(f"OK  - Compra com Ouro (carta: {card})")


def test_buy_with_gold_daily_limit():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 30
    buy_artifact_with_gold(state, 1)
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria bloquear segunda compra")
    except ActionError as e:
        print(f"OK  - Limite diario bloqueado: {e}")


def test_transmute_with_magic():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    before = state.shop.size()
    card = transmute_artifact_with_magic(state, 1)
    assert p.city.magic == 10 - ARTIFACT_MAGIC_COST
    assert card in p.hand
    assert state.shop.size() == before - 1
    print(f"OK  - Transmutacao com Magia (carta: {card})")


def test_transmute_daily_limit():
    state = make_state()
    p = state.players[0]
    p.city.magic = 20
    transmute_artifact_with_magic(state, 1)
    try:
        transmute_artifact_with_magic(state, 1)
        raise AssertionError("Deveria bloquear segunda transmutacao")
    except ActionError as e:
        print(f"OK  - Limite diario bloqueado: {e}")


def test_transmute_requires_no_unit():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    assert p.units == []
    transmute_artifact_with_magic(state, 1)
    print("OK  - Transmutacao sem unidade")


def test_sell_requires_unit_at_center():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    card = transmute_artifact_with_magic(state, 1)
    try:
        sell_artifact(state, 1, card)
        raise AssertionError("Deveria exigir unidade no Centro")
    except ActionError as e:
        print(f"OK  - Venda sem unidade bloqueada: {e}")


def test_sell_returns_card_to_shop():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 20
    before_size = state.shop.size()
    card = buy_artifact_with_gold(state, 1)
    after_buy = state.shop.size()
    assert after_buy == before_size - 1
    gold_before = p.city.gold
    sell_artifact(state, 1, card)
    assert p.city.gold == gold_before + ARTIFACT_SELL_GOLD
    assert card not in p.hand
    assert state.shop.size() == after_buy + 1
    print(f"OK  - Venda devolve carta e +{ARTIFACT_SELL_GOLD} Ouro")


def test_sell_does_not_consume_daily_limit():
    state = make_state()
    p = state.players[0]
    _setup_center_troop(state, 1)
    p.city.gold = 20
    card = buy_artifact_with_gold(state, 1)
    sell_artifact(state, 1, card)
    try:
        buy_artifact_with_gold(state, 1)
        raise AssertionError("Deveria continuar bloqueado")
    except ActionError:
        print("OK  - Venda nao zera limite diario")


def run_all():
    tests = [
        test_shop_initial_size,
        test_buy_with_gold_requires_unit_at_center,
        test_buy_with_gold,
        test_buy_with_gold_daily_limit,
        test_transmute_with_magic,
        test_transmute_daily_limit,
        test_transmute_requires_no_unit,
        test_sell_requires_unit_at_center,
        test_sell_returns_card_to_shop,
        test_sell_does_not_consume_daily_limit,
    ]
    print("=== Testes artifacts ===\\n")
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
# tests/test_artifact_effects.py — loja 24
# =============================================================
FILES["tests/test_artifact_effects.py"] = '''\
"""Testes de K-heart e K-diamonds (on_turn_start)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import play_artifact, discard_field_artifact, ActionError
from jessica.core.turn import start_turn
from jessica.core.serialize import state_to_dict, state_from_dict


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


def test_play_not_in_hand():
    state = make_state()
    try:
        play_artifact(state, 1, "K_H")
        raise AssertionError("Deveria bloquear carta fora da mao")
    except ActionError as e:
        print(f"OK  - Carta fora da mao bloqueada: {e}")


def test_play_k_h_raises_life_max():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    before = p.city.life_max
    play_artifact(state, 1, "K_H")
    assert p.city.life_max == before + 1
    assert p.city.life == 2
    assert "K_H" not in p.hand
    assert any(a.card_id == "K_H" for a in p.field_artifacts)
    print(f"OK  - Kh: life_max {before} -> {p.city.life_max}")


def test_play_k_d():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_D")
    play_artifact(state, 1, "K_D")
    assert "K_D" not in p.hand
    assert any(a.card_id == "K_D" for a in p.field_artifacts)
    print("OK  - Kd jogado para o campo")


def test_morning_k_h_heals():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    state.turn = 2
    start_turn(state)
    assert p.city.life == 3, f"Esperado 3, veio {p.city.life}"
    print("OK  - Kh manha: +1 vida")


def test_morning_k_d_gives_resources():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_D")
    play_artifact(state, 1, "K_D")
    gold_before = p.city.gold
    magic_before = p.city.magic
    state.turn = 2
    start_turn(state)
    assert p.city.gold == gold_before + 2
    assert p.city.magic == magic_before + 1
    print("OK  - Kd manha: +2 Ouro, +1 Magia")


def test_morning_k_h_caps_at_life_max():
    state = make_state()
    p = state.players[0]
    p.city.life = p.city.life_max
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    state.turn = 2
    start_turn(state)
    assert p.city.life == 7
    for t in range(3, 6):
        state.turn = t
        start_turn(state)
    assert p.city.life == 7
    print("OK  - Kh manha estanca em life_max")


def test_field_survives_serialization():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    state2 = state_from_dict(state_to_dict(state))
    p2 = state2.players[0]
    assert p2.city.life_max == p.city.life_max
    assert len(p2.field_artifacts) == 1
    assert p2.field_artifacts[0].card_id == "K_H"
    print("OK  - Campo persiste em roundtrip")


def test_discard_returns_to_shop():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_H")
    play_artifact(state, 1, "K_H")
    shop_before = state.shop.size()
    discard_field_artifact(state, 1, "K_H")
    assert state.shop.size() == shop_before + 1
    assert not p.field_artifacts
    print("OK  - Descarte devolve a Loja")


def run_all():
    tests = [
        test_play_not_in_hand,
        test_play_k_h_raises_life_max,
        test_play_k_d,
        test_morning_k_h_heals,
        test_morning_k_d_gives_resources,
        test_morning_k_h_caps_at_life_max,
        test_field_survives_serialization,
        test_discard_returns_to_shop,
    ]
    print("=== Testes K-heart / K-diamonds ===\\n")
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
# tests/test_artifact_effects_f3b.py — encoding
# =============================================================
FILES["tests/test_artifact_effects_f3b.py"] = '''\
"""Testes F3b: K-spades e K-clubs."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

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
        raise AssertionError("Deveria bloquear")
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
    print("OK  - Ks: tropa longe mantem 1 ataque")


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
    print("OK  - Ks: 2 ataques funcionaram")


def test_k_s_returns_to_shop_at_end_turn():
    state = make_state()
    p = state.players[0]
    p.hand.append("K_S")
    play_artifact(state, 1, "K_S")
    shop_after_play = state.shop.size()
    end_turn(state)
    assert not any(a.card_id == "K_S" for a in p.field_artifacts)
    assert state.shop.size() == shop_after_play + 1
    print("OK  - Ks volta a Loja")


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
    print("OK  - Ks buffs limpam")


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
    print(f"OK  - Resistencia 1 stack: 5 -> 2")


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
# tests/test_artifact_effects_f3c.py — encoding
# =============================================================
FILES["tests/test_artifact_effects_f3c.py"] = '''\
"""Testes F3c: J-heart e J-spades."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import play_artifact, summon_troop, ActionError
from jessica.core.combat import resolve_attack, Attack
from jessica.core.turn import end_turn
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero, Troop


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["Miyamoto Musashi", "Besouro Mangangá", "Iúna"],
            "anoes": ["Barbadourada"], "orcs": ["Arken"], "fadas": ["Ainai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "Miyamoto Musashi"},
            2: {"povo": "anoes", "heroi": "Barbadourada"},
            3: {"povo": "orcs", "heroi": "Arken"},
            4: {"povo": "fadas", "heroi": "Ainai"},
        },
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


def test_j_h_requires_hero_id():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_H")
    try:
        play_artifact(state, 1, "J_H")
        raise AssertionError("Deveria exigir hero_id")
    except (ActionError, ValueError) as e:
        print(f"OK  - Jh sem escolha bloqueado")


def test_j_h_cannot_summon_same_hero_as_setup():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_H")
    try:
        play_artifact(state, 1, "J_H", choice={"hero_id": "miyamoto"})
        raise AssertionError("Deveria bloquear")
    except ValueError as e:
        print(f"OK  - Jh bloqueia heroi do setup")


def test_j_h_summons_extra_hero():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_H")
    play_artifact(state, 1, "J_H", choice={"hero_id": "iuna"})
    extras = [u for u in p.units if isinstance(u, Hero) and u.hero_id == "iuna"]
    assert len(extras) == 1, f"Esperado 1 iuna, veio {len(extras)}"
    assert extras[0].life == 2, f"Iuna tem 2 de vida, veio {extras[0].life}"
    assert extras[0].house == "city_1"
    assert any(a.card_id == "J_H" for a in p.field_artifacts)
    print("OK  - Jh invocou Iuna")


def test_j_h_returns_to_shop_on_hero_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("J_H")
    play_artifact(state, 1, "J_H", choice={"hero_id": "iuna"})
    hero = next(u for u in p.units if isinstance(u, Hero) and u.hero_id == "iuna")
    hero.house = "center"
    hero.life = 1  # forca morte em 1 ataque (Iuna toma 1 fixo)
    enemy = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house="center")
    shop_before = state.shop.size()
    resolve_attack(state, Attack(enemy.id, "unit", hero.id))
    assert not hero.is_alive(), "Iuna deveria ter morrido"
    assert not any(a.card_id == "J_H" for a in p.field_artifacts)
    assert state.shop.size() == shop_before + 1
    print("OK  - Jh volta a Loja")


def test_j_h_allows_principal_hero_to_coexist():
    state = make_state()
    p = state.players[0]
    p.city.magic = 5
    from jessica.core.actions import summon_hero
    summon_hero(state, 1)
    p.hand.append("J_H")
    play_artifact(state, 1, "J_H", choice={"hero_id": "iuna"})
    heroes_ = [u for u in p.units if isinstance(u, Hero)]
    assert len(heroes_) == 2
    print("OK  - Jh coexiste com heroi principal")


def test_j_s_requires_house():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    try:
        play_artifact(state, 1, "J_S")
        raise AssertionError("Deveria exigir casa")
    except (ActionError, ValueError) as e:
        print(f"OK  - Js sem escolha bloqueado")


def test_j_s_summons_special_troop_in_center():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": CENTER})
    specials = [u for u in p.units
                if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL]
    assert len(specials) == 1
    t = specials[0]
    assert t.life == 5
    assert t.house == CENTER
    print("OK  - Js invocou tropa 5 no Centro")


def test_j_s_summons_in_enemy_city():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": "city_2"})
    t = next(u for u in p.units
             if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL)
    assert t.house == "city_2"
    print("OK  - Js invocou tropa na Cidade do J2")


def test_j_s_invalid_house():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    try:
        play_artifact(state, 1, "J_S", choice={"house": "marte"})
        raise AssertionError("Deveria bloquear")
    except ValueError as e:
        print(f"OK  - Js casa invalida bloqueada")


def test_j_s_returns_to_shop_on_troop_death():
    state = make_state()
    state.phase = Phase.NIGHT
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": CENTER})
    t = next(u for u in p.units
             if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL)
    enemy = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=8, house=CENTER)
    shop_before = state.shop.size()
    resolve_attack(state, Attack(enemy.id, "unit", t.id))
    assert not t.is_alive()
    assert not any(a.card_id == "J_S" for a in p.field_artifacts)
    assert state.shop.size() == shop_before + 1
    print("OK  - Js volta a Loja quando tropa morre")


def test_j_s_only_one_special_troop_at_a_time():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_S")
    play_artifact(state, 1, "J_S", choice={"house": CENTER})
    p.hand.append("J_S")
    try:
        play_artifact(state, 1, "J_S", choice={"house": CENTER})
        raise AssertionError("Deveria bloquear segunda tropa")
    except ValueError as e:
        print(f"OK  - Js so 1 tropa special viva")


def run_all():
    tests = [
        test_j_h_requires_hero_id,
        test_j_h_cannot_summon_same_hero_as_setup,
        test_j_h_summons_extra_hero,
        test_j_h_returns_to_shop_on_hero_death,
        test_j_h_allows_principal_hero_to_coexist,
        test_j_s_requires_house,
        test_j_s_summons_special_troop_in_center,
        test_j_s_summons_in_enemy_city,
        test_j_s_invalid_house,
        test_j_s_returns_to_shop_on_troop_death,
        test_j_s_only_one_special_troop_at_a_time,
    ]
    print("=== Testes F3c ===\\n")
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
# tests/test_artifact_effects_f3d.py — encoding
# =============================================================
FILES["tests/test_artifact_effects_f3d.py"] = '''\
"""Testes F3d: J-diamonds e Q-diamonds."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

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
    print(f"OK  - Jd dispara escolha")


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
        print(f"OK  - Jd exige 2")


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
        print(f"OK  - Qd sem escolha bloqueado")


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
    print("OK  - Qd volta a Loja")


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
# tests/test_artifact_effects_f3e.py — encoding
# =============================================================
FILES["tests/test_artifact_effects_f3e.py"] = '''\
"""Testes F3e: J-clubs e Q-clubs."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import play_artifact, summon_troop, ActionError
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
    except ActionError:
        print("OK  - Jc sem alvo bloqueado")


def test_j_c_cannot_target_self():
    state = make_state()
    p = state.players[0]
    p.hand.append("J_C")
    try:
        play_artifact(state, 1, "J_C", choice={"target_player_id": 1})
        raise AssertionError("Deveria bloquear auto-alvo")
    except ValueError:
        print("OK  - Jc nao pode ter voce mesmo")


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
    print(f"OK  - Jc: J2 pula Dia e Noite do turno")


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
    print(f"OK  - Jc: J2 pula Noite atual + Dia seguinte")


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
    print(f"OK  - day_order omite J2: {order}")


def test_q_c_requires_target():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    try:
        play_artifact(state, 1, "Q_C")
        raise AssertionError("Deveria exigir alvo")
    except ActionError:
        print("OK  - Qc sem alvo bloqueado")


def test_q_c_cannot_target_own_unit():
    state = make_state()
    p = state.players[0]
    p.hand.append("Q_C")
    own = _make_troop(state, 1, life=4)
    try:
        play_artifact(state, 1, "Q_C", choice={"unit_id": own.id})
        raise AssertionError("Deveria bloquear unidade propria")
    except ValueError:
        print("OK  - Qc nao pode controlar unidade propria")


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
# tests/test_boin.py — tropa fake no centro
# =============================================================
FILES["tests/test_boin.py"] = '''\
"""Testes: Boin."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, buy_artifact_with_gold, transmute_artifact_with_magic,
    resolve_pending_artifact_choice, summon_troop,
)
from jessica.core.constants import TroopArchetype, CENTER
from jessica.core.models import Troop


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


def _force_boin_player(state, pid):
    """Faz o jogador pid escolher 7 Anões e invoca ate Boin."""
    p = state.players[pid - 1]
    p.people = "anoes"
    p.chosen_hero_id = "seven_dwarves"
    p.city.magic = 30
    for _ in range(4):
        summon_hero(state, pid)
    return next(u for u in p.units if u.hero_id == "boin")


def _fake_center_troop(state, pid):
    """Adiciona uma Tropa fake no Centro para o jogador pid, contornando a
    restricao de '7 Anões nao pode invocar Tropa'."""
    p = state.players[pid - 1]
    t = Troop(
        id=f"p{pid}_fake_center",
        owner_id=pid,
        house=CENTER,
        life=4, life_max=4,
        archetype=TroopArchetype.LIGHT,
    )
    p.units.append(t)
    return t


def test_boin_buy_draws_2_picks_1():
    state = make_state()
    _force_boin_player(state, 3)
    _fake_center_troop(state, 3)
    p = state.players[2]
    p.city.gold = 20
    hand_before = len(p.hand)
    shop_before = state.shop.size()

    result = buy_artifact_with_gold(state, 3)
    assert result is None, "Boin deveria devolver None"
    pending = p.pending_artifact_choice
    assert pending is not None
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    print(f"OK  - Boin: comprou e recebeu 2 cartas")
    chosen = pending["cards"][0]
    resolve_pending_artifact_choice(state, 3, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1
    assert state.shop.size() == shop_before - 1
    print(f"OK  - Boin: escolheu 1")


def test_boin_transmute_draws_2_picks_1():
    state = make_state()
    _force_boin_player(state, 3)
    p = state.players[2]
    p.city.magic = 20
    hand_before = len(p.hand)
    result = transmute_artifact_with_magic(state, 3)
    assert result is None
    pending = p.pending_artifact_choice
    assert pending["kind"] == "BOIN"
    assert len(pending["cards"]) == 2
    chosen = pending["cards"][1]
    resolve_pending_artifact_choice(state, 3, kept_cards=[chosen])
    assert chosen in p.hand
    assert len(p.hand) == hand_before + 1
    print("OK  - Boin transmutou com escolha 2-de-1")


def test_no_boin_buy_direct():
    state = make_state()
    _fake_center_troop(state, 1)
    p = state.players[0]
    p.city.gold = 20
    result = buy_artifact_with_gold(state, 1)
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
# tests/test_pena.py — ja' resolvido o codigo
# =============================================================
FILES["tests/test_pena.py"] = '''\
"""Testes: Pena do Manto Sagrado."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, use_or_give_pena, sell_artifact, summon_troop, ActionError,
)
from jessica.core.constants import CENTER, TroopArchetype
from jessica.core.models import Hero
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["iuna"], "anoes": ["ori"],
            "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "humanos", "heroi": "Iúna"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_humano_pena_activate():
    state = make_state()
    p1 = state.players[0]
    p1.hand.append("PENA")
    use_or_give_pena(state, 1, "PENA", give_to_iuna=False)
    assert any(a.card_id == "PENA" for a in p1.field_artifacts)
    assert "PENA" not in p1.hand
    print("OK  - Humano: Pena ativada em campo")


def test_humano_pena_boosts_roca():
    from jessica.core.models import ArtifactOnField
    state = make_state()
    p1 = state.players[0]
    p1.field_artifacts.append(ArtifactOnField(card_id="PENA", owner_id=1))
    before = len(state.event_log)
    peoples.on_player_morning(state, 1)
    new_lines = state.event_log[before:]
    joined = "\\n".join(new_lines)
    assert "2D4" in joined, f"Esperado 2D4 no log. Log: {joined}"
    print("OK  - Humano com Pena: Roca rola 2D4")


def test_non_humano_give_pena_to_iuna():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 10
    summon_hero(state, 1)  # Iuna
    p2 = state.players[1]
    p2.hand.append("PENA")
    use_or_give_pena(state, 2, "PENA", give_to_iuna=True)
    assert "PENA" not in p2.hand, "Pena deveria ter sido entregue"
    assert len(p2.hand) == 1, f"Esperado 1 carta nova, tem {len(p2.hand)}"
    print("OK  - Nao-humano: deu Pena a Iuna e ganhou outro artefato")


def test_non_humano_keep_pena():
    state = make_state()
    p2 = state.players[1]
    p2.hand.append("PENA")
    use_or_give_pena(state, 2, "PENA", give_to_iuna=False)
    assert "PENA" in p2.hand
    print("OK  - Nao-humano: ficou com a Pena")


def test_non_humano_cannot_give_without_iuna():
    state = make_state()
    p2 = state.players[1]
    p2.hand.append("PENA")
    try:
        use_or_give_pena(state, 2, "PENA", give_to_iuna=True)
        raise AssertionError("Deveria bloquear sem Iuna viva")
    except ActionError:
        print("OK  - Sem Iuna: nao pode dar")


def test_sell_pena():
    state = make_state()
    p2 = state.players[1]
    p2.city.gold = 10
    p2.city.magic = 5
    t = summon_troop(state, 2, TroopArchetype.LIGHT, 4)
    t.house = CENTER
    p2.hand.append("PENA")
    gold_before = p2.city.gold
    sell_artifact(state, 2, "PENA")
    assert p2.city.gold == gold_before + 7
    assert "PENA" not in p2.hand
    print("OK  - Pena vendida por 7 Ouro")


def run_all():
    tests = [
        test_humano_pena_activate,
        test_humano_pena_boosts_roca,
        test_non_humano_give_pena_to_iuna,
        test_non_humano_keep_pena,
        test_non_humano_cannot_give_without_iuna,
        test_sell_pena,
    ]
    print("=== Testes Pena ===\\n")
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
# tests/run_all.py — passa env UTF-8 aos subprocessos
# =============================================================
FILES["tests/run_all.py"] = '''\
"""Roda toda a bateria de testes."""
import subprocess
import sys
import os
import re
from pathlib import Path

HERE = Path(__file__).parent.resolve()
TEST_FILES = sorted(HERE.glob("test_*.py"))


def main():
    print(f"Encontrados {len(TEST_FILES)} arquivos de teste.\\n")
    total_pass = 0
    total_fail = 0
    failed_files = []
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for tf in TEST_FILES:
        result = subprocess.run(
            [sys.executable, str(tf)],
            capture_output=True, text=True, cwd=HERE.parent, env=env,
            encoding="utf-8", errors="replace",
        )
        out = (result.stdout or "") + (result.stderr or "")
        m = re.search(r"(\\d+) passaram, (\\d+) falharam", out)
        if m:
            p, f = int(m.group(1)), int(m.group(2))
            total_pass += p
            total_fail += f
            status = "OK " if f == 0 else "FAIL"
            print(f"[{status}] {tf.name}: {p}/{p+f}")
            if f > 0:
                failed_files.append(tf.name)
                print("  --- output ---")
                for line in out.splitlines():
                    if line.startswith("FALHOU"):
                        print(f"  | {line}")
        else:
            total_fail += 1
            failed_files.append(tf.name)
            print(f"[ERRO] {tf.name}: sem contagem")
            for line in out.splitlines():
                if "Error" in line or "Exception" in line:
                    print(f"  | {line}")
                    break
    print()
    print(f"TOTAL: {total_pass} passaram, {total_fail} falharam")
    if failed_files:
        print(f"Arquivos com falha: {', '.join(failed_files)}")


if __name__ == "__main__":
    main()
'''

# =============================================================
# tests/__init__.py — garante que "tests" e um pacote
# =============================================================
FILES["tests/__init__.py"] = ""


def main() -> None:
    # 1) Organiza pastas
    reorganize()

    # 2) Backup + escrita
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