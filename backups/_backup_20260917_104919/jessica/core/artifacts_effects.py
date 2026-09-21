"""
Efeitos de artefatos.
"""
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
                    log(state, f"{player.name}: K♥ Aquilombar (+1 Vida: "
                               f"{player.city.life}/{player.city.life_max}).")
            elif artifact.card_id == "K_D":
                player.city.gold += 2
                player.city.magic += 1
                log(state, f"{player.name}: K♦ Balança (+2 Ouro, +1 Magia).")


def on_play(state: GameState, player_id: int, card_id: str, choice: dict) -> None:
    player = get_player(state, player_id)
    if card_id == "K_H":
        player.city.life_max += 1
        log(state, f"{player.name} jogou K♥ Aquilombar.")
        return
    if card_id == "K_D":
        log(state, f"{player.name} jogou K♦ Balança.")
        return
    if card_id == "Q_H":
        player.invulnerable_until_end_turn = True
        player.no_city_attacks_until_end_turn = True
        log(state, f"{player.name} jogou Q♥.")
        return
    if card_id == "Q_S":
        player.double_damage_until_end_night = True
        log(state, f"{player.name} jogou Q♠.")
        return
    if card_id == "K_S":
        log(state, f"{player.name} jogou K♠.")
        return
    if card_id == "K_C":
        target_unit_id = choice.get("unit_id")
        if not target_unit_id:
            raise ValueError("K♣ requer unit_id.")
        target = next((u for u in player.units if u.id == target_unit_id and u.is_alive()), None)
        if target is None:
            raise ValueError(f"Alvo {target_unit_id} não encontrado.")
        target.double_damage = True
        target.resistance_stacks += 1
        for a in player.field_artifacts:
            if a.card_id == "K_C" and "target_unit_id" not in a.extra:
                a.extra["target_unit_id"] = target_unit_id
                break
        log(state, f"{player.name} jogou K♣ em {target.id}.")
        return
    if card_id == "J_H":
        hero_id = choice.get("hero_id")
        if not hero_id:
            raise ValueError("J♥ requer hero_id.")
        if hero_id == player.chosen_hero_id:
            raise ValueError("J♥ não pode invocar o herói do setup.")
        alive = any(isinstance(u, Hero) and u.hero_id == hero_id and u.is_alive()
                    for u in player.units)
        if alive:
            raise ValueError(f"Herói {hero_id} já em campo.")
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
        log(state, f"{player.name} jogou J♥: invocou {hdef.name}.")
        return
    if card_id == "J_S":
        house = choice.get("house")
        if not house:
            raise ValueError("J♠ requer house.")
        if house not in (CENTER, *CITY_HOUSES):
            raise ValueError(f"Casa inválida: {house}")
        existing = [u for u in player.units
                    if isinstance(u, Troop) and u.archetype == TroopArchetype.SPECIAL
                    and u.is_alive()]
        if existing:
            raise ValueError("Já existe tropa do Chamado da Lua.")
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
        log(state, f"{player.name} jogou J♠: tropa 5 em {house}.")
        return
    if card_id == "J_D":
        state.pending_effects.append({
            "kind": "J_D", "player_id": player_id,
            "due_turn": state.turn + 3, "card_id": "J_D",
        })
        log(state, f"{player.name} jogou J♦.")
        return
    if card_id == "Q_D":
        target_unit_id = choice.get("unit_id")
        if not target_unit_id:
            raise ValueError("Q♦ requer unit_id.")
        target = _find_any_unit(state, target_unit_id)
        if target is None:
            raise ValueError(f"Alvo {target_unit_id} não encontrado.")
        for a in player.field_artifacts:
            if a.card_id == "Q_D" and "target_unit_id" not in a.extra:
                a.extra["target_unit_id"] = target_unit_id
                break
        log(state, f"{player.name} jogou Q♦ em {target.id}.")
        return
    if card_id == "J_C":
        target_id = choice.get("target_player_id")
        if target_id is None:
            raise ValueError("J♣ requer target_player_id.")
        target = get_player(state, target_id)
        if target.id == player_id:
            raise ValueError("J♣ não pode ter você como alvo.")
        if not target.city.is_alive():
            raise ValueError("J♣ não pode ter jogador eliminado.")
        target.skip_night_turn = state.turn
        target.skip_day_turn = state.turn + 1 if target.has_played_day_this_turn else state.turn
        log(state, f"{player.name} jogou J♣ em {target.name}.")
        return
    if card_id == "Q_C":
        target_unit_id = choice.get("unit_id")
        if not target_unit_id:
            raise ValueError("Q♣ requer unit_id.")
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
            raise ValueError(f"Alvo {target_unit_id} não encontrado.")
        if original_owner.id == player_id:
            raise ValueError("Q♣ só controla unidade inimiga.")
        if not original_owner.city.is_alive():
            raise ValueError("Q♣ não controla unidade de jogador eliminado.")
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
        log(state, f"{player.name} jogou Q♣: controla {target.id}.")
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
        if e["player_id"] == player_id and e["due_turn"] == state.turn:
            triggered.append(e)
    for e in triggered:
        state.pending_effects.remove(e)
        if e["kind"] == "J_D":
            _trigger_j_d(state, player_id, e["card_id"])


def _trigger_j_d(state: GameState, player_id: int, card_id: str) -> None:
    player = get_player(state, player_id)
    if state.shop.size() < 3:
        log(state, f"{player.name}: J♦ — Loja insuficiente.")
        _discard_card(state, player_id, card_id)
        return
    drawn = [state.shop.draw_random(state.rng) for _ in range(3)]
    player.pending_artifact_choice = {
        "kind": "J_D", "card_id": card_id, "cards": drawn, "pick": 2,
    }
    log(state, f"{player.name}: J♦ Tabaréu — escolha 2 de 3.")


def on_night_start(state: GameState) -> None:
    """
    K♠ concede +1 ataque a heróis e a aliados próximos a um herói.
    O cálculo especial de Miyamoto é feito on-demand em combat.py.
    """
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
            log(state, f"  Q♦: {owner.name} deve escolher recompensa.")


def on_end_turn(state: GameState) -> None:
    from .actions import discard_field_artifact
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
        if player.skip_day_turn is not None and player.skip_day_turn < state.turn:
            player.skip_day_turn = None
        if player.skip_night_turn is not None and player.skip_night_turn < state.turn:
            player.skip_night_turn = None
        for u in player.units:
            u.max_attacks_this_night = 1
            u.hero_can_attack_city = False


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