"""apply_update_v5a: motor dos Filhos da Floresta + Gnomos e Duendes."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5a_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# jessica/core/constants.py
# =============================================================
FILES["jessica/core/constants.py"] = '''\
from enum import Enum

DEFAULT_NUM_PLAYERS = 4
DEFAULT_CITY_LIFE_START = 2
DEFAULT_CITY_LIFE_MAX = 6
DEFAULT_STARTING_GOLD = 0
DEFAULT_STARTING_MAGIC = 0
DEFAULT_STARTING_TROOPS = 0
DEFAULT_STARTING_HERO_ALIVE = False
DEFAULT_STARTING_ARTIFACTS = 0
DEFAULT_SEED = 20260916

RESOURCES_PER_DAY = 2
GOLD_INTEREST_DIVISOR = 5
CITY_LIFE_COST_GOLD = 2
HERO_SUMMON_COST_MAGIC = 3
TROOP_SUMMON_COST_MAGIC = 1
TROOP_MAX_LIFE = {
    "light": 4,
    "medium": 6,
    "heavy": 8,
    "special": 5,
    "extra": 4,
    "ghoul": 1,
    "esqueleto": 1,
}
MONUMENT_COST_GOLD = 1
MONUMENT_BONUS_INTERVAL = 4

ARTIFACT_GOLD_COST = 6
ARTIFACT_MAGIC_COST = 6
ARTIFACT_SELL_GOLD = 7
ARTIFACT_MAX_BUYS_GOLD_PER_DAY = 1
ARTIFACT_MAX_BUYS_MAGIC_PER_DAY = 1
ARTIFACTS_PER_CARD_IN_SHOP = 2

CITY_HOUSES = ("city_1", "city_2", "city_3", "city_4")
CENTER = "center"
ALL_HOUSES = CITY_HOUSES + (CENTER,)

FIRST_TURN = 1
FIRST_CURUNA_ID = 1

# Filhos da Floresta
FILHOS_BONUS_TURN = 13

# Gnomos e Duendes
BET_HEART = "H"      # Muralha (mudar vida da cidade)
BET_CLUB = "C"       # Usar Artefato
BET_DIAMOND = "D"    # Ganhar ou vender Artefato
BET_SPADE = "S"      # Invocar ou matar Tropa/Herói
ALL_BETS = (BET_HEART, BET_CLUB, BET_DIAMOND, BET_SPADE)


class Phase(Enum):
    DAY = "day"
    NIGHT = "night"


class Resource(Enum):
    GOLD = "gold"
    MAGIC = "magic"


class TroopArchetype(Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SPECIAL = "special"
    EXTRA = "extra"
    GHOUL = "ghoul"
    ESQUELETO = "esqueleto"
'''

# =============================================================
# jessica/core/models.py - campos dos novos povos
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
    bloqueado_mover_proximo: bool = False

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

    # Filhos da Floresta
    filhos_bonus_recebido: bool = False
    baoba_pagamentos: int = 0

    # Gnomos e Duendes
    bet_H_target: Optional[int] = None
    bet_C_target: Optional[int] = None
    bet_D_target: Optional[int] = None
    bet_S_target: Optional[int] = None
    correct_bets: int = 0
    zebum_herois: list[str] = field(default_factory=list)
    spell_copia_id: Optional[str] = None
    spell_copia_turn: int = -1
    bets_need_realocacao: bool = False

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
# jessica/core/peoples.py - hooks de apostas + bonus filhos
# =============================================================
FILES["jessica/core/peoples.py"] = '''\
"""Passivas dos povos."""
from __future__ import annotations
from .state import get_player, log
from .models import GameState, Player, Unit, Hero, Troop
from .constants import (
    TroopArchetype, CENTER, CITY_HOUSES,
    BET_HEART, BET_CLUB, BET_DIAMOND, BET_SPADE, ALL_BETS, FILHOS_BONUS_TURN,
)
from . import heroes


PEOPLE_HUMANS = "humanos"
PEOPLE_DWARVES = "anoes"
PEOPLE_ORCS = "orcs"
PEOPLE_FAE = "fadas"
PEOPLE_VAMPIRES = "vampiros"
PEOPLE_LOBISOMENS = "lobisomens"
PEOPLE_GIGANTES = "gigantes"
PEOPLE_MORTOS_VIVOS = "mortos_vivos"
PEOPLE_FILHOS = "filhos_floresta"
PEOPLE_GNOMOS = "gnomos_duendes"


# Mapeia acao -> naipe de aposta que ela satisfaz
ACTION_TO_BET = {
    "raise_city_life": BET_HEART,
    "play_artifact": BET_CLUB,
    "buy_artifact_gold": BET_DIAMOND,
    "buy_artifact_magic": BET_DIAMOND,
    "transmute_artifact_magic": BET_DIAMOND,
    "sell_artifact": BET_DIAMOND,
    "summon_hero": BET_SPADE,
    "summon_troop": BET_SPADE,
    "kill": BET_SPADE,
}


def unit_signature(u: Unit) -> dict:
    if isinstance(u, Hero):
        return {"kind": "hero", "id": u.hero_id}
    return {"kind": "troop", "id": u.archetype.value}


def is_empalado(player: Player, sig: dict) -> bool:
    return sig in player.empalados


# =============================================================
# Hook de acao: chamado por acoes do motor
# =============================================================

def on_action_performed(state: GameState, actor_id: int, action: str) -> None:
    """Verifica se alguma aposta de Gnomos eh cumprida por essa acao."""
    suit = ACTION_TO_BET.get(action)
    if suit is None:
        return
    for gnomo in state.players:
        if gnomo.people != PEOPLE_GNOMOS:
            continue
        if not gnomo.city.is_alive():
            continue
        target = getattr(gnomo, f"bet_{suit}_target", None)
        if target is None:
            continue
        if target != actor_id:
            continue
        # Aposta cumprida
        gnomo.correct_bets += 1
        setattr(gnomo, f"bet_{suit}_target", None)
        actor = get_player(state, actor_id)
        log(state, f"{gnomo.name}: Aposta {suit} cumprida por {actor.name}. "
                   f"(Total: {gnomo.correct_bets} corretas)")


# =============================================================
# Sao Tome: passivas dos alvos das apostas
# =============================================================

def sao_tome_has_aposta_em(player: Player, target_id: int) -> bool:
    """True se Sao Tome tem ao menos 1 aposta pendente nesse alvo."""
    return (
        player.bet_H_target == target_id
        or player.bet_C_target == target_id
        or player.bet_D_target == target_id
        or player.bet_S_target == target_id
    )


def sao_tome_effective_peoples(state: GameState, player: Player) -> set[str]:
    """Retorna o conjunto de povos cujas passivas Sao Tome tem agora."""
    if player.people != PEOPLE_GNOMOS:
        return {player.people}
    # So faz sentido se tiver Sao Tome vivo
    has_sao_tome = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
        for u in player.units
    )
    if not has_sao_tome:
        return {PEOPLE_GNOMOS}
    result = {PEOPLE_GNOMOS}
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        if sao_tome_has_aposta_em(player, other.id):
            result.add(other.people)
    return result


# =============================================================
# Filhos: bonus turno 13
# =============================================================

def apply_filhos_bonus(state: GameState) -> None:
    if state.turn != FILHOS_BONUS_TURN:
        return
    for p in state.players:
        if p.people != PEOPLE_FILHOS:
            continue
        if not p.city.is_alive():
            continue
        if p.filhos_bonus_recebido:
            continue
        # +2 vida respeitando cap
        ganho_vida = min(2, p.city.life_max - p.city.life)
        p.city.life += ganho_vida
        p.city.gold += 2
        p.city.magic += 2
        p.filhos_bonus_recebido = True
        log(state, f"{p.name} (Filhos): Florescimento Exuberante (+{ganho_vida} Vida, +2 Ouro, +2 Magia).")


# =============================================================
# Gnomos: re-alocar apostas + sortear feitico copia
# =============================================================

def reset_gnomos_bets(state: GameState) -> None:
    """No inicio do turno, marca que as apostas precisam ser re-alocadas."""
    for p in state.players:
        if p.people != PEOPLE_GNOMOS:
            continue
        if not p.city.is_alive():
            continue
        p.bet_H_target = None
        p.bet_C_target = None
        p.bet_D_target = None
        p.bet_S_target = None
        p.bets_need_realocacao = True
        log(state, f"{p.name} (Gnomos): apostas serao re-alocadas.")


def draw_spell_copia(state: GameState, player: Player) -> None:
    """Sorteia 1 feitico de povo participante. Nao pode ser o proprio Gnomos."""
    from . import spells as spells_mod
    peoples_participantes = set()
    for p in state.players:
        if p.people and p.people != PEOPLE_GNOMOS:
            peoples_participantes.add(p.people)
    if not peoples_participantes:
        player.spell_copia_id = None
        return
    candidatos = []
    for people in peoples_participantes:
        sp = spells_mod.spell_for_people(people)
        if sp is not None:
            candidatos.append(sp.spell_id)
    if not candidatos:
        player.spell_copia_id = None
        return
    player.spell_copia_id = state.rng.choice(candidatos)
    player.spell_copia_turn = state.turn
    log(state, f"{player.name} (Gnomos): feitico copiado sorteado: {player.spell_copia_id}.")


# =============================================================
# Passivas padrao (morning)
# =============================================================

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
    # Sao Tome: passivas extras dos alvos
    if p == PEOPLE_GNOMOS:
        _sao_tome_extra_passives(state, player)


def _sao_tome_extra_passives(state: GameState, player: Player) -> None:
    """Sao Tome executa as passivas dos alvos das apostas pendentes."""
    has_sao_tome = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
        for u in player.units
    )
    if not has_sao_tome:
        return
    for other in state.players:
        if other.id == player.id:
            continue
        if not other.city.is_alive():
            continue
        if not sao_tome_has_aposta_em(player, other.id):
            continue
        op = other.people
        if op == PEOPLE_DWARVES:
            _dwarves_mineiro_carreiro(state, player)
        elif op == PEOPLE_HUMANS:
            _humans_roca_de_quilombo(state, player)


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
    victim_owner = get_player(state, dead_unit.owner_id)

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

    if killer_player.people == PEOPLE_LOBISOMENS:
        sig = unit_signature(dead_unit)
        if sig not in killer_player.infectados:
            killer_player.infectados.append(sig)
            log(state, f"  {dead_unit.id} infectado pela Maldicao da Lua.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if heroes.has_ability(u.hero_id, "empala_on_kill"):
            sig = unit_signature(dead_unit)
            if sig not in victim_owner.empalados:
                victim_owner.empalados.append(sig)
                log(state, f"  {dead_unit.id} empalado por Dracula (dono {victim_owner.name}).")
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

    # Hooks de aposta: kill
    on_action_performed(state, killer_player_id, "kill")


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


def apply_lua_cheia_effects(state: GameState) -> None:
    for p in state.players:
        if p.people != PEOPLE_LOBISOMENS:
            continue
        if not p.city.is_alive():
            continue
        if not is_lua_cheia(state, p.id):
            continue

        log(state, f"--- LUA CHEIA para {p.name} ---")
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
    if not lobisomem.infectados:
        return
    sigs_hero = {e["id"] for e in lobisomem.infectados if e["kind"] == "hero"}
    sigs_troop = {e["id"] for e in lobisomem.infectados if e["kind"] == "troop"}

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


def apply_cova_rasa(state: GameState) -> None:
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


def apply_presenca_magnetica(state: GameState) -> None:
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
    enemies.sort(key=lambda u: u.life, reverse=True)
    log(state, f"Presenca Magnetica em {home}: {len(enemies)} inimigos forcados.")
    for enemy in enemies:
        if not joao.is_alive():
            log(state, "  Joao morreu — restantes cancelados.")
            break
        if not enemy.is_alive():
            continue
        dmg = enemy.life * 2
        joao.life = max(0, joao.life - dmg)
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
# jessica/core/heroes.py - add filhos + gnomos
# =============================================================
FILES["jessica/core/heroes.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class HeroDefinition:
    hero_id: str
    people: str
    name: str
    life: int
    abilities: tuple[str, ...] = ()


HERO_CATALOG: dict[str, HeroDefinition] = {
    "miyamoto": HeroDefinition("miyamoto", "humanos", "Miyamoto Musashi", 4,
        ("attack_during_day", "gain_max_life_on_kill", "double_attack_if_stronger")),
    "besouro": HeroDefinition("besouro", "humanos", "Besouro Mangangá", 4,
        ("double_damage_and_resist_vs_stronger", "mandinga_artifact_at_night")),
    "iuna": HeroDefinition("iuna", "humanos", "Iúna", 2,
        ("takes_1_damage_when_attacked", "deals_1_to_4_damage", "adds_penas_once")),
    "barbadourada": HeroDefinition("barbadourada", "anoes", "Barbadourada", 6,
        ("magic_per_artifact_morning",)),
    "ori": HeroDefinition("ori", "anoes", "Ori, Velho Mestre Ferreiro", 3,
        ("resistance_aura",)),
    "seven_dwarves": HeroDefinition("seven_dwarves", "anoes", "Os 7 Anoes", 1,
        ("seven_dwarves",)),
    "dain": HeroDefinition("dain", "anoes", "Dain, o Alergico", 1,
        ("kill_attacker_at_night_end",)),
    "buin": HeroDefinition("buin", "anoes", "Buin, o Dengoso", 2,
        ("cannot_be_attacked_by_heroes",)),
    "bein": HeroDefinition("bein", "anoes", "Bein, o Soneca", 3,
        ("sleep_on_attack",)),
    "boin": HeroDefinition("boin", "anoes", "Boin, o Feliz", 4,
        ("see_2_pick_1_artifact",)),
    "tintin": HeroDefinition("tintin", "anoes", "Tin Tin, o Bobao", 5,
        ("can_be_invisible",)),
    "don": HeroDefinition("don", "anoes", "Don, o Zangado", 6,
        ("extra_attacks_per_dwarf",)),
    "din": HeroDefinition("din", "anoes", "Din, o Mestre", 7,
        ("dwarves_can_attack_cities",)),
    "garoche": HeroDefinition("garoche", "orcs", "Ga'Roche, Rei do Sertao", 3,
        ("execute_weak_targets", "grow_per_execute")),
    "arken": HeroDefinition("arken", "orcs", "Arken, Cacador de Uma So Flecha", 4,
        ("espolia_daily",)),
    "vovo_gamba": HeroDefinition("vovo_gamba", "orcs", "Vovo Gamba, Protetora dos Espiritos", 3,
        ("tropa_bonus_damage", "choose_attack_time")),
    "ainai": HeroDefinition("ainai", "fadas", "Ainai, Fada da Vinganca", 5,
        ("move_to_fallen_fae",)),
    "valendar": HeroDefinition("valendar", "fadas", "Valendar, Rainha Maga", 5,
        ("substitutes_spell",)),
    "luna": HeroDefinition("luna", "fadas", "Luna, Sonhadora de Realidades", 2,
        ("spell_multi_artifact", "return_move")),
    "dracula": HeroDefinition("dracula", "vampiros", "Dracula", 7,
        ("empala_on_kill", "reset_spell_on_kill")),
    "dandara": HeroDefinition("dandara", "vampiros", "Dandara, Cacadora de Burgueses", 5,
        ("invisibilidade_grupo",)),
    "luide_vampa": HeroDefinition("luide_vampa", "vampiros", "Luide Vampa, Lider dos Bandidos", 5,
        ("move_aliados_noturno",)),
    "lupa_lider": HeroDefinition("lupa_lider", "lobisomens", "Lupa, Lider da Matilha", 7,
        ("resistencia_lua_cheia",)),
    "cigana": HeroDefinition("cigana", "lobisomens", "Cigana, Caminhante da Nevoa", 2,
        ("veu_da_lua",)),
    "luarado": HeroDefinition("luarado", "lobisomens", "Luarado, Filhote da Mare", 4,
        ("cacada_infecciosa",)),
    "joao_grandao": HeroDefinition("joao_grandao", "gigantes", "Joao Grandao, Protetor do Pe Desenterrado", 10,
        ("presenca_magnetica",)),
    "pe_descalco": HeroDefinition("pe_descalco", "gigantes", "Pe Descalco, Aquela que Treme a Terra", 4,
        ("ataque_extra", "grito_de_guerra")),
    "caroco": HeroDefinition("caroco", "gigantes", "Caroco, o Dende Teimoso", 2,
        ("caroco_geracional", "cabaca_cheia")),
    "cobra": HeroDefinition("cobra", "mortos_vivos", "Cobra, o Paje Caido", 3,
        ("espectro_hook",)),
    "zoia": HeroDefinition("zoia", "mortos_vivos", "Zoia Bulbo Negro, Pressagio da Peste", 2,
        ("tropas_extras",)),
    "cova_rasa": HeroDefinition("cova_rasa", "mortos_vivos", "Cova Rasa da Terra Funda", 1,
        ("amaldicoar_proximos",)),
    "guarari": HeroDefinition("guarari", "filhos_floresta", "Guarari, Centauro Guardiao da Floresta", 5,
        ("transformar_centauro",)),
    "aiquara": HeroDefinition("aiquara", "filhos_floresta", "Aiquara, Ninfa da Baia Doce", 2,
        ("controlar_inimigo",)),
    "baoba_ba": HeroDefinition("baoba_ba", "filhos_floresta", "Baoba-ba, Anciao Milenar", 10,
        ("invocacao_multi_turno",)),
    "bimbo_do_mal": HeroDefinition("bimbo_do_mal", "gnomos_duendes", "Bimbo do Mal", 2,
        ("gastar_aposta",)),
    "sao_tome": HeroDefinition("sao_tome", "gnomos_duendes", "Sao Tome, Morador de Piramide", 4,
        ("passivas_dos_alvos", "duas_determinacoes")),
    "zebum": HeroDefinition("zebum", "gnomos_duendes", "Zebum, o Mistico Viajante", 3,
        ("invocar_heroi_estrangeiro",)),
}

SEVEN_DWARVES_ORDER = ["dain", "buin", "bein", "boin", "tintin", "don", "din"]

LEGACY_NAMES: dict[str, str] = {
    "Miyamoto Musashi": "miyamoto",
    "Besouro Mangangá": "besouro",
    "Iúna": "iuna",
    "Barbadourada": "barbadourada",
    "Ori": "ori",
    "Os 7 Anões": "seven_dwarves",
    "Ga'Roche": "garoche",
    "Arken": "arken",
    "Vovó Gamba": "vovo_gamba",
    "Ainai": "ainai",
    "Valendar": "valendar",
    "Luna": "luna",
    "Dracula": "dracula",
    "Dandara": "dandara",
    "Luide Vampa": "luide_vampa",
    "Lupã": "lupa_lider",
    "Cigana": "cigana",
    "Luarado": "luarado",
    "João Grandão": "joao_grandao",
    "Pé Descalço": "pe_descalco",
    "Caroço": "caroco",
    "Cobra": "cobra",
    "Zoia": "zoia",
    "Zoia Bulbo Negro": "zoia",
    "Cova Rasa": "cova_rasa",
    "Cova Rasa da Terra Funda": "cova_rasa",
    "Guarari": "guarari",
    "Aiquara": "aiquara",
    "Baoba-bá": "baoba_ba",
    "Baoba-ba": "baoba_ba",
    "Bimbo do Mal": "bimbo_do_mal",
    "São Tomé": "sao_tome",
    "Sao Tome": "sao_tome",
    "Zebum": "zebum",
    "Zebum, o Místico Viajante": "zebum",
}


def heroes_for_people(people: str) -> list[HeroDefinition]:
    if people == "anoes":
        return [HERO_CATALOG[h] for h in ("barbadourada", "ori", "seven_dwarves")]
    if people == "mortos_vivos":
        return [HERO_CATALOG[h] for h in ("cobra", "zoia", "cova_rasa")]
    if people == "filhos_floresta":
        return [HERO_CATALOG[h] for h in ("guarari", "aiquara", "baoba_ba")]
    if people == "gnomos_duendes":
        return [HERO_CATALOG[h] for h in ("bimbo_do_mal", "sao_tome", "zebum")]
    return [h for h in HERO_CATALOG.values()
            if h.people == people and h.hero_id not in SEVEN_DWARVES_ORDER]


def resolve_hero_for_people(people: str, raw: str) -> str:
    if raw in HERO_CATALOG:
        return raw
    legacy = LEGACY_NAMES.get(raw)
    if legacy is not None:
        return legacy
    for h in HERO_CATALOG.values():
        if h.people == people and h.name == raw:
            return h.hero_id
    raw_lower = raw.lower()
    matches = [h for h in HERO_CATALOG.values()
               if h.people == people and h.name.lower().startswith(raw_lower)]
    if len(matches) == 1:
        return matches[0].hero_id
    return raw


def normalize_hero_id(raw: str) -> str:
    if raw in HERO_CATALOG:
        return raw
    if raw in LEGACY_NAMES:
        return LEGACY_NAMES[raw]
    for hid, hd in HERO_CATALOG.items():
        if hd.name == raw:
            return hid
    raw_lower = raw.lower()
    matches = [h for h in HERO_CATALOG.values() if h.name.lower().startswith(raw_lower)]
    if len(matches) == 1:
        return matches[0].hero_id
    raise KeyError(f"Heroi desconhecido: {raw}")


def get_hero(hero_id: str) -> HeroDefinition:
    return HERO_CATALOG[normalize_hero_id(hero_id)]


def has_ability(hero_id: str, ability: str) -> bool:
    try:
        h = get_hero(hero_id)
    except KeyError:
        return False
    return ability in h.abilities


def hero_name(hero_id: str) -> str:
    try:
        return get_hero(hero_id).name
    except KeyError:
        return hero_id


def is_seven_dwarf(hero_id: str) -> bool:
    return hero_id in SEVEN_DWARVES_ORDER


def next_dwarf_to_summon(alive_hero_ids: set[str]) -> str | None:
    for hid in SEVEN_DWARVES_ORDER:
        if hid not in alive_hero_ids:
            return hid
    return None


def dwarf_index(hero_id: str) -> int:
    if hero_id not in SEVEN_DWARVES_ORDER:
        return -1
    return SEVEN_DWARVES_ORDER.index(hero_id)
'''

# =============================================================
# jessica/core/spells.py - add decompor + imitacao
# =============================================================
FILES["jessica/core/spells.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SpellDefinition:
    spell_id: str
    people: str
    name: str
    description: str
    implemented: bool = True


SPELL_CATALOG: dict[str, SpellDefinition] = {
    "resistencia": SpellDefinition(
        "resistencia", "humanos", "Resistencia",
        "De Resistencia a um aliado ate o fim do turno.",
    ),
    "armadura_de_ouro": SpellDefinition(
        "armadura_de_ouro", "anoes", "Armadura de Ouro",
        "Pague X Ouro para anular ate X dano por hit.",
    ),
    "espoliar": SpellDefinition(
        "espoliar", "orcs", "Espoliar",
        "+2 Ouro por Cidade inimiga ocupada.",
    ),
    "sonho_lucido": SpellDefinition(
        "sonho_lucido", "fadas", "Sonho Lucido",
        "Troca naipe do proximo artefato.",
    ),
    "transformar_morcego": SpellDefinition(
        "transformar_morcego", "vampiros", "Transformar em Morcego",
        "1 aliado anda 2x ou 1x se recem-invocado.",
    ),
    "licantropo": SpellDefinition(
        "licantropo", "lobisomens", "Licantropo",
        "1 unidade sua vira Lobisomem ate fim do turno.",
    ),
    "linhagem_ancestral": SpellDefinition(
        "linhagem_ancestral", "gigantes", "Linhagem Ancestral",
        "Ativa o feitico de 1 heroi Gigante vivo.",
    ),
    "levantar_mortos": SpellDefinition(
        "levantar_mortos", "mortos_vivos", "Levantar os Mortos",
        "Escolha 2 tropas (mortas ou nao invocadas) e invoque com 1 de vida.",
    ),
    "decompor": SpellDefinition(
        "decompor", "filhos_floresta", "Decompor",
        "Sacrifica um elemento seu por Magia (Heroi +4, Tropa vida+2, Muralha -1 vida +3 Magia).",
    ),
    "imitacao_gnomerica": SpellDefinition(
        "imitacao_gnomerica", "gnomos_duendes", "Imitacao Gnomerica",
        "Copia o feitico de outro povo participante (sorteado por dia).",
    ),
}


def get_spell(spell_id: str) -> SpellDefinition:
    if spell_id not in SPELL_CATALOG:
        raise KeyError(f"Feitico desconhecido: {spell_id}")
    return SPELL_CATALOG[spell_id]


def spell_for_people(people: str) -> SpellDefinition | None:
    for s in SPELL_CATALOG.values():
        if s.people == people:
            return s
    return None
'''

# =============================================================
# jessica/core/turn.py - chamar hooks novos
# =============================================================
FILES["jessica/core/turn.py"] = '''\
from __future__ import annotations
from .constants import Phase, MONUMENT_BONUS_INTERVAL, FILHOS_BONUS_TURN
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
    _process_caroco_turn1(state)
    _process_gigantes_turn(state)
    peoples.apply_lua_cheia_effects(state)
    peoples.apply_filhos_bonus(state)
    _reset_gnomos_bets_e_sorteio(state)
    reset_unit_flags(state)
    return interest


def _reset_gnomos_bets_e_sorteio(state: GameState) -> None:
    peoples.reset_gnomos_bets(state)
    for p in state.players:
        if p.people == peoples.PEOPLE_GNOMOS and p.city.is_alive():
            if p.spell_copia_turn != state.turn:
                peoples.draw_spell_copia(state, p)


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


def _process_caroco_turn1(state: GameState) -> None:
    if state.turn != 1:
        return
    for player in state.players:
        if player.people != peoples.PEOPLE_GIGANTES:
            continue
        if player.chosen_hero_id != "caroco":
            continue
        if not player.city.is_alive():
            continue
        if any(isinstance(u, Hero) and u.hero_id == "caroco" for u in player.units):
            continue
        hero = Hero(id=f"p{player.id}_caroco_free",
                    owner_id=player.id, house=f"city_{player.id}",
                    life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
        player.units.append(hero)
        log(state, f"{player.name}: Caroco invocado gratuitamente (turno 1).")
    # Gnomos: Zebum gratis no turno 1
    for player in state.players:
        if player.people != peoples.PEOPLE_GNOMOS:
            continue
        if player.chosen_hero_id != "zebum":
            continue
        if not player.city.is_alive():
            continue
        if any(isinstance(u, Hero) and u.hero_id == "zebum" for u in player.units):
            continue
        hero = Hero(id=f"p{player.id}_zebum_free",
                    owner_id=player.id, house=f"city_{player.id}",
                    life=3, life_max=3, hero_id="zebum", has_moved_this_turn=True)
        player.units.append(hero)
        log(state, f"{player.name}: Zebum invocado gratuitamente (turno 1).")


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


def _luna_return(state: GameState) -> None:
    for player in state.players:
        for u in player.units:
            if (isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
                    and "luna_origin_house" in u.statuses):
                origin = u.statuses.pop("luna_origin_house")
                if origin != u.house:
                    log(state, f"  Luna retorna de {u.house} para {origin}.")
                    u.house = origin


def end_day(state: GameState) -> None:
    if state.phase != Phase.DAY:
        raise TurnError("Nao esta na fase do Dia.")
    state.deaths_this_night = []
    artifacts_effects.on_night_start(state)
    _luna_return(state)
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
# jessica/core/serialize.py - persistir campos novos
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
         "infectado": u.infectado,
         "bloqueado_mover_proximo": u.bloqueado_mover_proximo}
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
                  infectado=d.get("infectado", False),
                  bloqueado_mover_proximo=d.get("bloqueado_mover_proximo", False))
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
        "filhos_bonus_recebido": p.filhos_bonus_recebido,
        "baoba_pagamentos": p.baoba_pagamentos,
        "bet_H_target": p.bet_H_target,
        "bet_C_target": p.bet_C_target,
        "bet_D_target": p.bet_D_target,
        "bet_S_target": p.bet_S_target,
        "correct_bets": p.correct_bets,
        "zebum_herois": list(p.zebum_herois),
        "spell_copia_id": p.spell_copia_id,
        "spell_copia_turn": p.spell_copia_turn,
        "bets_need_realocacao": p.bets_need_realocacao,
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
        filhos_bonus_recebido=d.get("filhos_bonus_recebido", False),
        baoba_pagamentos=d.get("baoba_pagamentos", 0),
        bet_H_target=d.get("bet_H_target", None),
        bet_C_target=d.get("bet_C_target", None),
        bet_D_target=d.get("bet_D_target", None),
        bet_S_target=d.get("bet_S_target", None),
        correct_bets=d.get("correct_bets", 0),
        zebum_herois=list(d.get("zebum_herois", [])),
        spell_copia_id=d.get("spell_copia_id", None),
        spell_copia_turn=d.get("spell_copia_turn", -1),
        bets_need_realocacao=d.get("bets_need_realocacao", False),
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


if __name__ == "__main__":
    main()