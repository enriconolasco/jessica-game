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


def collect_resources(state: GameState, player_id: int, gold_amount: int, magic_amount: int) -> None:
    if gold_amount + magic_amount != RESOURCES_PER_DAY:
        raise ActionError(f"Coleta inválida: exatamente {RESOURCES_PER_DAY} recursos.")
    if gold_amount < 0 or magic_amount < 0:
        raise ActionError("Valores negativos.")
    player = get_player(state, player_id)
    if player.has_collected_this_turn:
        raise ActionError(f"{player.name} já coletou.")
    city = player.city
    if not city.is_alive():
        raise ActionError(f"Cidade destruída.")
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
        raise ActionError("Cidade destruída.")
    total_cost = CITY_LIFE_COST_GOLD * times
    if city.gold < total_cost:
        raise ActionError(f"Ouro insuficiente (precisa {total_cost}).")
    if city.life + times > city.life_max:
        raise ActionError(f"Ultrapassa vida máxima ({city.life_max}).")
    city.gold -= total_cost
    city.life += times
    record_action(state, player_id, "raise_city_life", times=times)
    log(state, f"{player.name} subiu vida em {times} ({city.life}/{city.life_max}).")


def summon_troop(state: GameState, player_id: int, archetype: TroopArchetype, life: int) -> Troop:
    max_life = TROOP_MAX_LIFE[archetype.value]
    if life < 1 or life > max_life:
        raise ActionError(f"Vida inválida: {life}. Máx {max_life}.")
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    max_slots = peoples.max_troops_of_archetype(player, archetype)
    existing = [u for u in player.units
                if isinstance(u, Troop) and u.archetype == archetype and u.is_alive()]
    if len(existing) >= max_slots:
        raise ActionError(f"Máximo de tropas {archetype.value}.")
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


def summon_hero(state: GameState, player_id: int) -> Hero:
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    if not player.chosen_hero_id:
        raise ActionError("Sem herói escolhido.")
    alive_heroes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()]
    if alive_heroes:
        raise ActionError("Já existe herói vivo.")
    magic_cost = max(0, HERO_SUMMON_COST_MAGIC - peoples.magic_cost_reduction(player))
    if city.magic < magic_cost:
        raise ActionError(f"Magia insuficiente ({magic_cost}).")
    city.magic -= magic_cost
    hdef = heroes.get_hero(player.chosen_hero_id)
    hero_life_max = hdef.life
    unit_id = f"p{player_id}_hero"
    hero = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                life=hero_life_max, life_max=hero_life_max,
                hero_id=hdef.hero_id, has_moved_this_turn=True)
    player.units.append(hero)
    record_action(state, player_id, "summon_hero", hero_id=hdef.hero_id)
    log(state, f"{player.name} invocou {hdef.name} ({hero_life_max}).")
    return hero


def move_unit(state: GameState, player_id: int, unit_id: str, destination: str) -> None:
    if destination not in (CENTER, *CITY_HOUSES):
        raise ActionError(f"Destino inválido: {destination}")
    player = get_player(state, player_id)
    unit = next((u for u in player.units if u.id == unit_id and u.is_alive()), None)
    if unit is None:
        raise ActionError(f"Unidade {unit_id} não encontrada.")
    if unit.has_moved_this_turn:
        raise ActionError("Já se moveu.")
    origin = unit.house
    if origin == destination:
        raise ActionError("Já está lá.")
    if origin.startswith("city_") and destination != CENTER:
        raise ActionError("De Cidade só vai para o Centro.")
    if origin == CENTER and not destination.startswith("city_"):
        raise ActionError("Do Centro só vai para Cidade.")
    if destination.startswith("city_"):
        dest_pid = int(destination.split("_")[1])
        if not get_player(state, dest_pid).city.is_alive():
            raise ActionError(f"Cidade destruída.")
    unit.house = destination
    unit.has_moved_this_turn = True
    record_action(state, player_id, "move_unit", unit_id=unit_id,
                  origin=origin, destination=destination)
    log(state, f"{player.name}: {unit_id} moveu para {destination}.")
    peoples.on_unit_moved(state, player_id, unit)


def build_monument(state: GameState, player_id: int) -> None:
    city = get_city(state, player_id)
    player = get_player(state, player_id)
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    if city.has_monument:
        raise ActionError("Já tem Monumento.")
    if city.life < city.life_max:
        raise ActionError(f"Precisa vida máxima ({city.life_max}).")
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
        raise ActionError(f"Alvo não encontrado.")
    heal = min(2, target.life_max - target.life)
    if heal <= 0:
        raise ActionError(f"{target.id} já está cheio.")
    target.life += heal
    player.pending_heals -= 1
    record_action(state, player_id, "use_heal", target=target_unit_id, healed=heal)
    log(state, f"{player.name}: curou {heal} em {target.id} ({target.life}/{target.life_max}).")


# ---------- Arken: Espoliar ----------

def arken_espolia(state: GameState, player_id: int) -> None:
    """
    Arken: Espoliar (ação diária, uma vez por turno).
      - Ganha +2 Ouro por Cidade inimiga ocupada.
      - Tropas em Cidades inimigas curam +1 e não atacam esta Noite.
    """
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    arken = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "arken"),
                 None)
    if arken is None:
        raise ActionError("Arken não está vivo.")
    if player.arken_espolia_used_turn == state.turn:
        raise ActionError("Arken já espoliou neste turno.")

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
    log(state, f"{player.name} (Arken): Espoliou {len(occupied_pids)} Cidade(s) "
               f"— +{gold} Ouro.")

    enemy_houses = {f"city_{pid}" for pid in occupied_pids}
    for u in player.units:
        if isinstance(u, Troop) and u.is_alive() and u.house in enemy_houses:
            healed = min(1, u.life_max - u.life)
            if healed > 0:
                u.life += healed
            u.statuses["cannot_attack_on_turn"] = state.turn
            log(state, f"  {u.id} curou {healed} e não atacará esta Noite.")

    player.arken_espolia_used_turn = state.turn
    record_action(state, player_id, "arken_espolia", gold=gold)


# ---------- Feitiços ----------

def cast_spell(state: GameState, player_id: int, choice: dict | None = None) -> None:
    choice = choice or {}
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    if state.turn < player.spell_cooldown_until_turn:
        restantes = player.spell_cooldown_until_turn - state.turn
        raise ActionError(f"Feitiço em recarga ({restantes}).")
    if player.has_cast_spell_this_turn:
        raise ActionError("Já usou feitiço.")

    sp = spells_mod.spell_for_people(player.people)
    if sp is None:
        raise ActionError("Sem feitiço.")
    if not sp.implemented:
        raise ActionError(f"{sp.name} não implementado.")

    if sp.spell_id == "resistencia":
        _spell_resistencia(state, player, choice)
    elif sp.spell_id == "armadura_de_ouro":
        _spell_armadura(state, player, choice)
    elif sp.spell_id == "espoliar":
        _spell_espoliar(state, player)
    else:
        raise ActionError(f"Feitiço {sp.spell_id} sem implementação.")

    player.spell_cooldown_until_turn = state.turn + 2
    player.has_cast_spell_this_turn = True
    record_action(state, player_id, "cast_spell", spell=sp.spell_id)


def _spell_resistencia(state: GameState, player, choice: dict) -> None:
    target_id = choice.get("unit_id")
    if not target_id:
        raise ActionError("Precisa alvo.")
    target = next((u for u in player.units if u.id == target_id and u.is_alive()), None)
    if target is None:
        raise ActionError(f"Alvo não encontrado.")
    target.resistance_stacks += 1
    log(state, f"{player.name} lançou Resistência em {target.id} "
               f"(Res×{target.resistance_stacks}).")


def _spell_armadura(state: GameState, player, choice: dict) -> None:
    cap = int(choice.get("cap", 1))
    if cap < 1:
        raise ActionError("Cap deve ser >= 1.")
    player.armor_gold_cap_per_hit = cap
    log(state, f"{player.name} lançou Armadura de Ouro (cap {cap}/hit).")


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
    log(state, f"{player.name} Espoliou {owned} Cidade(s) — +{gold} Ouro.")


# ---------- Artefatos ----------

def _has_unit_at_center(state: GameState, player_id: int) -> bool:
    player = get_player(state, player_id)
    return any(u.house == CENTER and u.is_alive() for u in player.units)


def buy_artifact_with_gold(state: GameState, player_id: int) -> str:
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    if player.artifacts_bought_gold_today >= ARTIFACT_MAX_BUYS_GOLD_PER_DAY:
        raise ActionError("Já comprou com Ouro hoje.")
    if not _has_unit_at_center(state, player_id):
        raise ActionError("Precisa unidade no Centro.")
    if city.gold < ARTIFACT_GOLD_COST:
        raise ActionError(f"Ouro insuficiente ({ARTIFACT_GOLD_COST}).")
    if state.shop.is_empty():
        raise ActionError("Loja vazia.")
    card = state.shop.draw_random(state.rng)
    city.gold -= ARTIFACT_GOLD_COST
    player.hand.append(card)
    player.artifacts_bought_gold_today += 1
    record_action(state, player_id, "buy_artifact_gold", card=card)
    log(state, f"{player.name} comprou: {card_display(card)}.")
    return card


def transmute_artifact_with_magic(state: GameState, player_id: int) -> str:
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    if player.artifacts_bought_magic_today >= ARTIFACT_MAX_BUYS_MAGIC_PER_DAY:
        raise ActionError("Já transmutou hoje.")
    if city.magic < ARTIFACT_MAGIC_COST:
        raise ActionError(f"Magia insuficiente ({ARTIFACT_MAGIC_COST}).")
    if state.shop.is_empty():
        raise ActionError("Loja vazia.")
    card = state.shop.draw_random(state.rng)
    city.magic -= ARTIFACT_MAGIC_COST
    player.hand.append(card)
    player.artifacts_bought_magic_today += 1
    record_action(state, player_id, "transmute_artifact_magic", card=card)
    log(state, f"{player.name} transmutou: {card_display(card)}.")
    return card


def sell_artifact(state: GameState, player_id: int, card_id: str) -> None:
    player = get_player(state, player_id)
    if card_id not in player.hand:
        raise ActionError(f"{player.name} não tem {card_id}.")
    if not _has_unit_at_center(state, player_id):
        raise ActionError("Precisa unidade no Centro.")
    player.hand.remove(card_id)
    city = player.city
    city.gold += ARTIFACT_SELL_GOLD
    state.shop.return_card(card_id)
    record_action(state, player_id, "sell_artifact", card=card_id)
    log(state, f"{player.name} vendeu {card_display(card_id)} ({ARTIFACT_SELL_GOLD}).")


def play_artifact(state: GameState, player_id: int, card_id: str,
                  target_unit_id: str | None = None,
                  choice: dict | None = None) -> None:
    if choice is None:
        choice = {}
    if target_unit_id is not None:
        choice = {**choice, "unit_id": target_unit_id}
    player = get_player(state, player_id)
    if card_id not in player.hand:
        raise ActionError(f"{player.name} não tem {card_id}.")
    if not artifacts_effects.is_implemented(card_id):
        raise ActionError(f"{card_display(card_id)} não implementado.")
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
    record_action(state, player_id, "play_artifact", card=card_id, choice=choice)


def discard_field_artifact(state: GameState, player_id: int, card_id: str) -> None:
    player = get_player(state, player_id)
    for i, a in enumerate(player.field_artifacts):
        if a.card_id == card_id:
            player.field_artifacts.pop(i)
            state.shop.return_card(card_id)
            log(state, f"{player.name}: {card_display(card_id)} voltou à Loja.")
            return
    raise ActionError(f"{player.name} não tem {card_id} em campo.")


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
                raise ActionError(f"{c} indisponível.")
            available.remove(c)
            kept.append(c)
        for c in kept:
            player.hand.append(c)
        for c in available:
            state.shop.return_card(c)
        log(state, f"{player.name}: J♦ — escolheu {', '.join(kept)}.")
        player.pending_artifact_choice = None
        discard_field_artifact(state, player_id, pending["card_id"])
        return
    if pending["kind"] == "Q_D":
        if resource not in ("gold", "magic"):
            raise ActionError("Q♦: gold ou magic.")
        amount = pending["dead_unit_max_life"]
        killer_id = pending["killer_id"]
        if resource == "gold":
            player.city.gold += amount
        else:
            player.city.magic += amount
        res_pt = "Ouro" if resource == "gold" else "Magia"
        log(state, f"{player.name}: Q♦ — +{amount} {res_pt}.")
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
    raise ActionError(f"Pendência desconhecida: {pending['kind']}")