"""Seleção de alvos e prioridade compartilhadas pelo terminal e pela web."""
from .models import Hero
from .state import get_player
from . import peoples
from .state import declaration_order_for_house


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
