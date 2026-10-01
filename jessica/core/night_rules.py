"""Seleção de alvos e prioridade compartilhadas pelo terminal e pela web."""
from .models import Hero
from .state import get_player
from . import peoples
from .state import declaration_order_for_house

def ainai_destinations(state, player):
    hero = next((u for u in player.units if isinstance(u, Hero) and u.is_alive()
                 and u.hero_id == "ainai"), None)
    if hero is None or hero.statuses.get("ainai_used_turn") == state.turn:
        return []
    return sorted({h for pid, h in state.fae_fallen_this_turn
                   if pid == player.id and h != hero.house})


def teleport_ainai(state, player, destination):
    from .state import sync_house_priority, log
    if destination not in ainai_destinations(state, player):
        raise ValueError("Destino de Ainai indisponível.")
    hero = next(u for u in player.units if isinstance(u, Hero) and u.is_alive()
                and u.hero_id == "ainai")
    origin = hero.house
    hero.house = destination
    sync_house_priority(state, origin, destination)
    hero.statuses["ainai_used_turn"] = state.turn
    player.city.magic += 1
    log(state, f"Ainai teleportou para {destination} (+1 Magia).")
    return hero


def return_luna(state, player):
    from .state import sync_house_priority
    luna = next((u for u in player.units if isinstance(u, Hero) and u.is_alive()
                 and u.hero_id == "luna" and "luna_origin_house" in u.statuses), None)
    if luna is None:
        raise ValueError("Luna não pode retornar.")
    origin = luna.statuses.pop("luna_origin_house")
    current = luna.house
    luna.house = origin
    sync_house_priority(state, current, origin)

def find_targets(state, unit):
    # Espoliado nao pode atacar nem declarar em cidade
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        return []
    targets = []
    house = unit.house
    can_attack_city = ((not isinstance(unit, Hero)) or unit.hero_can_attack_city
                       or peoples.rogue_can_attack_base(unit))
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
            if target.city.is_alive() and peoples.dragon_base(target) is None:
                targets.append(("city", str(target_pid),
                                f"Cidade de {target.name} ({target.city.life})"))
    for other in state.players:
        if other.id == unit.owner_id:
            continue
        for u in other.units:
            if u.house == house and u.is_alive():
                if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
                    continue
                from .combat import can_attack_unit
                if not can_attack_unit(state, unit, u):
                    continue
                kind = "Heroi" if isinstance(u, Hero) else "Tropa"
                targets.append(("unit", u.id,
                                f"{kind} {u.id} de {other.name} ({u.life})"))
    return targets

def order_players_for_house(state, pids_here: list[int], house: str) -> list[int]:
    ordered = declaration_order_for_house(state, house, pids_here)
    for pid in ordered:
        p = get_player(state, pid)
        if p.bater_primeiro_turn == state.turn:
            others = [x for x in ordered if x != pid]
            return [pid] + others
    vovo_owner = None
    for pid in ordered:
        p = get_player(state, pid)
        for u in p.units:
            if (isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "vovo_gamba" and u.house == house):
                vovo_owner = pid
                break
        if vovo_owner is not None:
            break
    if vovo_owner is None:
        return ordered
    pos = max(1, min(get_player(state, vovo_owner).vovo_position, len(ordered)))
    result = [pid for pid in ordered if pid != vovo_owner]
    result.insert(pos - 1, vovo_owner)
    return result
