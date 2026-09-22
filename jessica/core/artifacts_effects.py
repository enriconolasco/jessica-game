"""Efeitos de artefatos."""
from __future__ import annotations
from .state import get_player, log, mark_summoned, sync_house_priority
from .models import GameState, ArtifactOnField, Unit, Hero, Troop
from .constants import CENTER, CITY_HOUSES, TroopArchetype
from . import heroes, peoples


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
                dragon_base = peoples.dragon_base(player)
                if dragon_base is not None and dragon_base.life < dragon_base.life_max:
                    dragon_base.life += 1
                    peoples.sync_dragon_base_city(player)
                    peoples.on_base_life_gained(state, player.id, 1)
                    log(state, f"{player.name}: Kh Aquilombar (+1 Vida na Base).")
                    state.morning_gains.append(
                        {"pid": player.id, "kind": "Kh", "life": 1}
                    )
                elif player.city.life < player.city.life_max:
                    player.city.life += 1
                    peoples.on_base_life_gained(state, player.id, 1)
                    log(state, f"{player.name}: Kh Aquilombar (+1 Vida).")
                    state.morning_gains.append(
                        {"pid": player.id, "kind": "Kh", "life": 1}
                    )
            elif artifact.card_id == "K_D":
                player.city.gold += 2
                player.city.magic += 1
                log(state, f"{player.name}: Kd Balanca (+2 Ouro, +1 Magia).")
                state.morning_gains.append(
                    {"pid": player.id, "kind": "Kd", "gold": 2, "magic": 1}
                )


def on_play(state: GameState, player_id: int, card_id: str, choice: dict) -> None:
    player = get_player(state, player_id)
    if card_id == "K_H":
        dragon_base = peoples.dragon_base(player)
        if dragon_base is not None:
            dragon_base.life_max += 1
            peoples.sync_dragon_base_city(player)
        else:
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
        hero_life = peoples.hero_life_with_persistent_bonus(player, hdef, state)
        hero = Hero(id=hero_unit_id, owner_id=player_id,
                    house=f"city_{player_id}",
                    life=hero_life, life_max=hero_life,
                    hero_id=hdef.hero_id, has_moved_this_turn=True,
                    moves_this_turn=1)
        player.units.append(hero)
        mark_summoned(state, player, hero)
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
        mark_summoned(state, player, troop)
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
        if target.original_owner_id is not None:
            raise ValueError("Qc nao sobrepoe outro controle temporario.")
        original_owner.units.remove(target)
        player.units.append(target)
        target.original_owner_id = original_owner.id
        target.owner_id = player_id
        # Movimento/ataques consumidos pertencem a unidade e nao sao reiniciados.
        target.has_moved_this_turn = (
            target.moves_this_turn >= target.max_moves_this_turn
        )
        sync_house_priority(state, target.house)
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
                    u.statuses["k_s_active"] = True
            # Don e calculado dinamicamente em combat._effective_max_attacks.


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
        if player.sonho_lucido_pending_turn == state.turn and                 player.sonho_lucido_multi_turn != state.turn:
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
            # H10: Ks eh 1-turno, limpa o flag
            u.statuses.pop("k_s_active", None)
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
    from .actions import discard_field_artifact
    touched_houses = set()
    for p in state.players:
        for u in list(p.units):
            if u.original_owner_id is not None:
                orig = get_player(state, u.original_owner_id)
                touched_houses.add(u.house)
                p.units.remove(u)
                orig.units.append(u)
                u.owner_id = u.original_owner_id
                u.original_owner_id = None
                log(state, f"  {u.id} voltou ao controle de {orig.name}.")
    if touched_houses:
        sync_house_priority(state, *touched_houses)
    # Q_C (Almas Acorrentadas) expira com o controle
    for p in state.players:
        to_discard = [a.card_id for a in p.field_artifacts if a.card_id == "Q_C"]
        for _ in to_discard:
            try:
                discard_field_artifact(state, p.id, "Q_C")
                log(state, f"  {p.name}: Q_C (Almas Acorrentadas) expirou.")
            except Exception:
                pass


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
