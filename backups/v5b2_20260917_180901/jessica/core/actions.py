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
