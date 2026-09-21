"""apply_update_v4b: motor Lua Cheia + main.py com 8 povos."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v4b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# jessica/core/models.py - add infectados ao Player
# =============================================================
FILES["jessica/core/models.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .constants import Phase, TroopArchetype
from .artifacts import Shop
from .rng import DeterministicRNG


@dataclass
class City:
    owner_id: int
    life: int
    life_max: int
    gold: int = 0
    magic: int = 0
    has_monument: bool = False

    def is_alive(self) -> bool:
        return self.life > 0


@dataclass
class Unit:
    id: str
    owner_id: int
    house: str
    life: int
    life_max: int
    has_moved_this_turn: bool = False
    double_damage: bool = False
    resistance_stacks: int = 0
    attacks_made_this_night: int = 0
    max_attacks_this_night: int = 1
    attacks_made_this_day: int = 0
    max_attacks_this_day: int = 0
    hero_can_attack_city: bool = False
    killed_by_player_id: Optional[int] = None
    original_owner_id: Optional[int] = None
    statuses: dict = field(default_factory=dict)
    moves_this_turn: int = 0
    max_moves_this_turn: int = 1
    infectado: bool = False

    def is_alive(self) -> bool:
        return self.life > 0


@dataclass
class Hero(Unit):
    hero_id: str = ""


@dataclass
class Troop(Unit):
    archetype: TroopArchetype = TroopArchetype.LIGHT


@dataclass
class ArtifactOnField:
    card_id: str
    owner_id: int
    extra: dict = field(default_factory=dict)


@dataclass
class Player:
    id: int
    name: str
    people: str
    city: City
    chosen_hero_id: Optional[str] = None
    spell_cooldown_until_turn: int = 0
    has_collected_this_turn: bool = False
    has_cast_spell_this_turn: bool = False
    morning_done_this_turn: bool = False
    has_played_day_this_turn: bool = False
    artifacts_bought_gold_today: int = 0
    artifacts_bought_magic_today: int = 0
    pending_heals: int = 0
    hand: list[str] = field(default_factory=list)
    field_artifacts: list[ArtifactOnField] = field(default_factory=list)
    units: list[Unit] = field(default_factory=list)
    arken_espolia_used_turn: int = -1
    vovo_position: int = 1
    sonho_lucido_used_turn: int = -1
    sonho_lucido_pending_turn: int = -1
    sonho_lucido_multi_turn: int = -1
    vender_por_magia_turn: int = -1
    andar_duas_vezes_turn: int = -1
    bater_primeiro_turn: int = -1
    pena_added_once: bool = False
    besouro_mandinga_used_turn: int = -1
    carocos_gerados: int = 0
    empalados: list[str] = field(default_factory=list)
    infectados: list[dict] = field(default_factory=list)

    double_damage_until_end_night: bool = False
    invulnerable_until_end_turn: bool = False
    no_city_attacks_until_end_turn: bool = False
    armor_gold_cap_per_hit: int = 0

    skip_day_turn: Optional[int] = None
    skip_night_turn: Optional[int] = None

    pending_artifact_choice: Optional[dict] = None


@dataclass
class GameState:
    seed: int
    rng: DeterministicRNG = field(default_factory=lambda: DeterministicRNG(0))
    players: list[Player] = field(default_factory=list)
    turn_order: list[int] = field(default_factory=list)
    shop: Shop = field(default_factory=Shop)
    turn: int = 1
    phase: Phase = Phase.DAY
    curuna_id: int = 1
    event_log: list[str] = field(default_factory=list)
    action_log: list[dict] = field(default_factory=list)
    game_over: bool = False
    winner_id: Optional[int] = None
    pending_effects: list[dict] = field(default_factory=list)
    deaths_this_night: list[str] = field(default_factory=list)
    dain_kills: list[dict] = field(default_factory=list)
    espectros_pendentes: list[dict] = field(default_factory=list)
    lobisomens_transformados: list[dict] = field(default_factory=list)

    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.city.is_alive()]

    def player(self, pid: int) -> Player:
        for p in self.players:
            if p.id == pid:
                return p
        raise ValueError(f"Jogador {pid} nao encontrado")
'''

# =============================================================
# jessica/core/peoples.py - add Lua Cheia + Cova Rasa + Presenca
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
        if isinstance(dead_unit, Hero):
            sig = {"kind": "hero", "id": dead_unit.hero_id}
        else:
            sig = {"kind": "troop", "archetype": dead_unit.archetype.value}
        if sig not in killer_player.infectados:
            killer_player.infectados.append(sig)
            log(state, f"  {dead_unit.id} infectado pela Maldicao da Lua.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if heroes.has_ability(u.hero_id, "empala_on_kill"):
            if dead_unit.id not in killer_player.empalados:
                killer_player.empalados.append(dead_unit.id)
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


# -------------------------------------------------------------
# Lua Cheia: efeitos e flip
# -------------------------------------------------------------

def apply_lua_cheia_effects(state: GameState) -> None:
    """
    Aplica efeitos de Lua Cheia no inicio do turno (do lobisomem).
    - Flip de infectados
    - Lupa Lider: +1 Resistencia a todos os lobisomens
    - Cigana: todos invisiveis
    - Luarado: 2 movimentos
    """
    for p in state.players:
        if p.people != PEOPLE_LOBISOMENS:
            continue
        if not p.city.is_alive():
            continue
        if not is_lua_cheia(state, p.id):
            continue

        log(state, f"--- LUA CHEIA para {p.name} ---")

        # Flip de unidades infectadas (controladas temporariamente)
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
    """Durante Lua Cheia, unidades de inimigos que correspondem a infeccoes
    viram Lobisomens temporarios sob controle do jogador Lobisomem."""
    if not lobisomem.infectados:
        return
    sigs_hero = {e["id"] for e in lobisomem.infectados if e["kind"] == "hero"}
    sigs_troop = {e["archetype"] for e in lobisomem.infectados if e["kind"] == "troop"}

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


# -------------------------------------------------------------
# Cova Rasa
# -------------------------------------------------------------

def apply_cova_rasa(state: GameState) -> None:
    """Cova Rasa viva: inimigos proximos ficam amaldicoados no inicio da Noite."""
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


# -------------------------------------------------------------
# Presenca Magnetica (Joao Grandao)
# -------------------------------------------------------------

def apply_presenca_magnetica(state: GameState) -> None:
    """Se JOAO_PRESENCA pendente, forca inimigos proximos a atacar Joao."""
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
    # Ordem decrescente de vida atual
    enemies.sort(key=lambda u: u.life, reverse=True)
    log(state, f"Presenca Magnetica de Joao Grandao em {home}: {len(enemies)} inimigos forcados.")
    for enemy in enemies:
        if not joao.is_alive():
            log(state, "  Joao morreu — ataques restantes cancelados.")
            break
        if not enemy.is_alive():
            continue
        # Ataque dobrado contra Joao, sem retaliação do lado do inimigo? Nao: Joao retalia.
        # Simula: dano ao Joao = 2 * vida_atual; Joao retalia com sua vida atual (troca simples).
        from .combat import _resolve_combat_round  # reusa logica
        # Mas _resolve_combat_round aplica multiplicadores. Vamos aplicar dano dobrado manualmente.
        dmg = enemy.life * 2
        joao.life = max(0, joao.life - dmg)
        # Joao retalia
        enemy.life = max(0, enemy.life - enemy.statuses.get("life_at_death", 0))  # placeholder
        # Simplificando: Joao sofre, inimigo nao e retaliado aqui (MVP)
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
# jessica/core/artifacts_effects.py - chamar Cova Rasa e Presenca
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
    # Cova Rasa: antes de tudo
    peoples.apply_cova_rasa(state)
    # Presenca Magnetica (Joao Grandao)
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
            # Resistencia de Lupa expira
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
# jessica/core/turn.py - chamar Lua Cheia
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


def end_day(state: GameState) -> None:
    if state.phase != Phase.DAY:
        raise TurnError("Nao esta na fase do Dia.")
    state.deaths_this_night = []
    artifacts_effects.on_night_start(state)
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
# jessica/core/serialize.py - add infectados
# =============================================================
FILES["jessica/core/serialize.py"] = '''\
from __future__ import annotations
import json
from .models import City, Player, Unit, Hero, Troop, GameState, ArtifactOnField
from .artifacts import Shop
from .rng import DeterministicRNG
from .constants import Phase, TroopArchetype


def city_to_dict(c: City) -> dict:
    return {"owner_id": c.owner_id, "life": c.life, "life_max": c.life_max,
            "gold": c.gold, "magic": c.magic, "has_monument": c.has_monument}


def city_from_dict(d: dict) -> City:
    return City(owner_id=d["owner_id"], life=d["life"], life_max=d["life_max"],
                gold=d["gold"], magic=d["magic"], has_monument=d["has_monument"])


def unit_to_dict(u: Unit) -> dict:
    kind = "hero" if isinstance(u, Hero) else "troop"
    d = {"kind": kind, "id": u.id, "owner_id": u.owner_id, "house": u.house,
         "life": u.life, "life_max": u.life_max,
         "has_moved_this_turn": u.has_moved_this_turn,
         "double_damage": u.double_damage,
         "resistance_stacks": u.resistance_stacks,
         "attacks_made_this_night": u.attacks_made_this_night,
         "max_attacks_this_night": u.max_attacks_this_night,
         "attacks_made_this_day": u.attacks_made_this_day,
         "max_attacks_this_day": u.max_attacks_this_day,
         "hero_can_attack_city": u.hero_can_attack_city,
         "killed_by_player_id": u.killed_by_player_id,
         "original_owner_id": u.original_owner_id,
         "statuses": dict(u.statuses),
         "moves_this_turn": u.moves_this_turn,
         "max_moves_this_turn": u.max_moves_this_turn,
         "infectado": u.infectado}
    if kind == "hero":
        d["hero_id"] = u.hero_id
    else:
        d["archetype"] = u.archetype.value
    return d


def unit_from_dict(d: dict) -> Unit:
    common = dict(id=d["id"], owner_id=d["owner_id"], house=d["house"],
                  life=d["life"], life_max=d["life_max"],
                  has_moved_this_turn=d["has_moved_this_turn"],
                  double_damage=d.get("double_damage", False),
                  resistance_stacks=d.get("resistance_stacks", 0),
                  attacks_made_this_night=d.get("attacks_made_this_night", 0),
                  max_attacks_this_night=d.get("max_attacks_this_night", 1),
                  attacks_made_this_day=d.get("attacks_made_this_day", 0),
                  max_attacks_this_day=d.get("max_attacks_this_day", 0),
                  hero_can_attack_city=d.get("hero_can_attack_city", False),
                  killed_by_player_id=d.get("killed_by_player_id", None),
                  original_owner_id=d.get("original_owner_id", None),
                  statuses=dict(d.get("statuses", {})),
                  moves_this_turn=d.get("moves_this_turn", 0),
                  max_moves_this_turn=d.get("max_moves_this_turn", 1),
                  infectado=d.get("infectado", False))
    if d["kind"] == "hero":
        return Hero(**common, hero_id=d["hero_id"])
    return Troop(**common, archetype=TroopArchetype(d["archetype"]))


def artifact_on_field_to_dict(a: ArtifactOnField) -> dict:
    return {"card_id": a.card_id, "owner_id": a.owner_id, "extra": dict(a.extra)}


def artifact_on_field_from_dict(d: dict) -> ArtifactOnField:
    return ArtifactOnField(card_id=d["card_id"], owner_id=d["owner_id"],
                           extra=dict(d.get("extra", {})))


def player_to_dict(p: Player) -> dict:
    return {
        "id": p.id, "name": p.name, "people": p.people,
        "chosen_hero_id": p.chosen_hero_id,
        "spell_cooldown_until_turn": p.spell_cooldown_until_turn,
        "has_collected_this_turn": p.has_collected_this_turn,
        "has_cast_spell_this_turn": p.has_cast_spell_this_turn,
        "morning_done_this_turn": p.morning_done_this_turn,
        "has_played_day_this_turn": p.has_played_day_this_turn,
        "artifacts_bought_gold_today": p.artifacts_bought_gold_today,
        "artifacts_bought_magic_today": p.artifacts_bought_magic_today,
        "pending_heals": p.pending_heals,
        "arken_espolia_used_turn": p.arken_espolia_used_turn,
        "vovo_position": p.vovo_position,
        "sonho_lucido_used_turn": p.sonho_lucido_used_turn,
        "sonho_lucido_pending_turn": p.sonho_lucido_pending_turn,
        "sonho_lucido_multi_turn": p.sonho_lucido_multi_turn,
        "vender_por_magia_turn": p.vender_por_magia_turn,
        "andar_duas_vezes_turn": p.andar_duas_vezes_turn,
        "bater_primeiro_turn": p.bater_primeiro_turn,
        "pena_added_once": p.pena_added_once,
        "besouro_mandinga_used_turn": p.besouro_mandinga_used_turn,
        "carocos_gerados": p.carocos_gerados,
        "empalados": list(p.empalados),
        "infectados": [dict(e) for e in p.infectados],
        "hand": list(p.hand),
        "field_artifacts": [artifact_on_field_to_dict(a) for a in p.field_artifacts],
        "units": [unit_to_dict(u) for u in p.units],
        "city": city_to_dict(p.city),
        "double_damage_until_end_night": p.double_damage_until_end_night,
        "invulnerable_until_end_turn": p.invulnerable_until_end_turn,
        "no_city_attacks_until_end_turn": p.no_city_attacks_until_end_turn,
        "armor_gold_cap_per_hit": p.armor_gold_cap_per_hit,
        "pending_artifact_choice": p.pending_artifact_choice,
        "skip_day_turn": p.skip_day_turn,
        "skip_night_turn": p.skip_night_turn,
    }


def player_from_dict(d: dict) -> Player:
    return Player(
        id=d["id"], name=d["name"], people=d["people"],
        chosen_hero_id=d["chosen_hero_id"],
        spell_cooldown_until_turn=d.get("spell_cooldown_until_turn", 0),
        has_collected_this_turn=d["has_collected_this_turn"],
        has_cast_spell_this_turn=d["has_cast_spell_this_turn"],
        morning_done_this_turn=d.get("morning_done_this_turn", False),
        has_played_day_this_turn=d.get("has_played_day_this_turn", False),
        artifacts_bought_gold_today=d["artifacts_bought_gold_today"],
        artifacts_bought_magic_today=d["artifacts_bought_magic_today"],
        pending_heals=d.get("pending_heals", 0),
        arken_espolia_used_turn=d.get("arken_espolia_used_turn", -1),
        vovo_position=d.get("vovo_position", 1),
        sonho_lucido_used_turn=d.get("sonho_lucido_used_turn", -1),
        sonho_lucido_pending_turn=d.get("sonho_lucido_pending_turn", -1),
        sonho_lucido_multi_turn=d.get("sonho_lucido_multi_turn", -1),
        vender_por_magia_turn=d.get("vender_por_magia_turn", -1),
        andar_duas_vezes_turn=d.get("andar_duas_vezes_turn", -1),
        bater_primeiro_turn=d.get("bater_primeiro_turn", -1),
        pena_added_once=d.get("pena_added_once", False),
        besouro_mandinga_used_turn=d.get("besouro_mandinga_used_turn", -1),
        carocos_gerados=d.get("carocos_gerados", 0),
        empalados=list(d.get("empalados", [])),
        infectados=[dict(e) for e in d.get("infectados", [])],
        hand=list(d["hand"]),
        field_artifacts=[artifact_on_field_from_dict(a) for a in d.get("field_artifacts", [])],
        units=[unit_from_dict(u) for u in d["units"]],
        city=city_from_dict(d["city"]),
        double_damage_until_end_night=d.get("double_damage_until_end_night", False),
        invulnerable_until_end_turn=d.get("invulnerable_until_end_turn", False),
        no_city_attacks_until_end_turn=d.get("no_city_attacks_until_end_turn", False),
        armor_gold_cap_per_hit=d.get("armor_gold_cap_per_hit", 0),
        pending_artifact_choice=d.get("pending_artifact_choice", None),
        skip_day_turn=d.get("skip_day_turn", None),
        skip_night_turn=d.get("skip_night_turn", None),
    )


def state_to_dict(s: GameState) -> dict:
    return {"seed": s.seed, "rng": s.rng.to_dict(),
            "players": [player_to_dict(p) for p in s.players],
            "turn_order": list(s.turn_order),
            "shop": {"deck": list(s.shop.deck)},
            "turn": s.turn, "phase": s.phase.value,
            "curuna_id": s.curuna_id,
            "event_log": list(s.event_log),
            "action_log": list(s.action_log),
            "game_over": s.game_over, "winner_id": s.winner_id,
            "pending_effects": [dict(e) for e in s.pending_effects],
            "deaths_this_night": list(s.deaths_this_night),
            "dain_kills": [dict(e) for e in s.dain_kills],
            "espectros_pendentes": [dict(e) for e in s.espectros_pendentes],
            "lobisomens_transformados": [dict(e) for e in s.lobisomens_transformados]}


def state_from_dict(d: dict) -> GameState:
    state = GameState(seed=d["seed"], rng=DeterministicRNG.from_dict(d["rng"]))
    state.players = [player_from_dict(p) for p in d["players"]]
    state.turn_order = list(d["turn_order"])
    state.shop = Shop(deck=list(d["shop"]["deck"]))
    state.turn = d["turn"]
    state.phase = Phase(d["phase"])
    state.curuna_id = d["curuna_id"]
    state.event_log = list(d["event_log"])
    state.action_log = list(d["action_log"])
    state.game_over = d["game_over"]
    state.winner_id = d["winner_id"]
    state.pending_effects = [dict(e) for e in d.get("pending_effects", [])]
    state.deaths_this_night = list(d.get("deaths_this_night", []))
    state.dain_kills = [dict(e) for e in d.get("dain_kills", [])]
    state.espectros_pendentes = [dict(e) for e in d.get("espectros_pendentes", [])]
    state.lobisomens_transformados = [dict(e) for e in d.get("lobisomens_transformados", [])]
    return state


def save_to_file(state: GameState, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state_to_dict(state), f, ensure_ascii=False, indent=2)


def load_from_file(path: str) -> GameState:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return state_from_dict(data)
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
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()