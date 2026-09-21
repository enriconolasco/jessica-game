"""apply_update_v4a: Vampiros, Lobisomens, Gigantes, Mortos-Vivos (motor)."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v4a_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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

PRIORITY_HERO_ABILITY = 0
PRIORITY_SPELL = 1
PRIORITY_PEOPLE_PASSIVE = 2
PRIORITY_ARTIFACT_EFFECT = 3


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
# jessica/core/models.py
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
# jessica/core/heroes.py
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
}


def heroes_for_people(people: str) -> list[HeroDefinition]:
    if people == "anoes":
        return [HERO_CATALOG[h] for h in ("barbadourada", "ori", "seven_dwarves")]
    if people == "mortos_vivos":
        return [HERO_CATALOG[h] for h in ("cobra", "zoia", "cova_rasa")]
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
# jessica/core/spells.py
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
        "De Resistencia a um aliado nesta Noite.",
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
        "Troca o naipe do proximo artefato usado.",
    ),
    "transformar_morcego": SpellDefinition(
        "transformar_morcego", "vampiros", "Transformar em Morcego",
        "1 aliado: pode andar 2x (ou 1x se recem-invocado). Ate o fim do turno.",
    ),
    "licantropo": SpellDefinition(
        "licantropo", "lobisomens", "Licantropo",
        "1 unidade original sua vira Lobisomem (efeito de Lua Cheia) ate o fim do turno.",
    ),
    "linhagem_ancestral": SpellDefinition(
        "linhagem_ancestral", "gigantes", "Linhagem Ancestral",
        "Ativa o feitico de um dos seus herois Gigantes vivos.",
    ),
    "levantar_mortos": SpellDefinition(
        "levantar_mortos", "mortos_vivos", "Levantar os Mortos",
        "Escolha 2 tropas suas (mortas ou nao invocadas) e invoque-as com 1 de vida.",
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
# jessica/core/peoples.py
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

    if killer_player.people == PEOPLE_LOBISOMENS and not dead_unit.infectado:
        dead_unit.infectado = True
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
# jessica/core/combat.py
# =============================================================
FILES["jessica/core/combat.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass
from .state import get_player, get_city, log
from .models import GameState, Unit, Hero, Troop
from . import peoples


class CombatError(Exception):
    pass


@dataclass
class Attack:
    attacker_unit_id: str
    target_type: str
    target_id: str


def _find_unit(state: GameState, unit_id: str) -> Unit | None:
    for player in state.players:
        for unit in player.units:
            if unit.id == unit_id and unit.is_alive():
                return unit
    return None


def _hero_has(unit: Unit, ability: str) -> bool:
    from . import heroes
    if not isinstance(unit, Hero):
        return False
    return heroes.has_ability(unit.hero_id, ability)


def _is_miyamoto(unit: Unit) -> bool:
    return _hero_has(unit, "double_attack_if_stronger")


def _effective_max_attacks(state: GameState, unit: Unit) -> int:
    if _is_miyamoto(unit):
        base = peoples.compute_hero_max_attacks_in_house(
            state, unit, "double_attack_if_stronger")
        k_s_bonus = max(0, unit.max_attacks_this_night - 1)
        return base + k_s_bonus
    if _hero_has(unit, "extra_attacks_per_dwarf"):
        owner = get_player(state, unit.owner_id)
        n = sum(1 for u in owner.units
                if isinstance(u, Hero) and u.is_alive()
                and u.id != unit.id and u.house == unit.house)
        return unit.max_attacks_this_night + n
    return unit.max_attacks_this_night


def _attacks_used(unit: Unit) -> int:
    if _is_miyamoto(unit):
        return unit.attacks_made_this_day
    return unit.attacks_made_this_night


def _register_attack(unit: Unit) -> None:
    if _is_miyamoto(unit):
        unit.attacks_made_this_day += 1
    else:
        unit.attacks_made_this_night += 1


def _award_city_destruction(state: GameState, destroyer_id: int) -> None:
    alive_now = sum(1 for p in state.players if p.city.is_alive())
    reward = {3: 4, 2: 3, 1: 2, 0: 0}.get(alive_now, 0)
    if reward == 0:
        return
    destroyer = get_player(state, destroyer_id)
    for _ in range(reward):
        if state.shop.is_empty():
            break
        destroyer.hand.append(state.shop.draw_random(state.rng))
    log(state, f"  {destroyer.name} destruiu Cidade e ganhou {reward} artefato(s).")


def _cleanup_dead(state: GameState) -> None:
    from . import artifacts_effects

    dead_units: list[Unit] = []
    for player in state.players:
        for u in player.units:
            if not u.is_alive():
                dead_units.append(u)

    for u in dead_units:
        if u.house not in state.deaths_this_night:
            state.deaths_this_night.append(u.house)
        artifacts_effects.on_unit_death(state, u)
        if u.killed_by_player_id is not None:
            peoples.on_unit_killed_by(state, u.killed_by_player_id, u)

    for player in state.players:
        dead = [u for u in player.units if not u.is_alive()]
        for u in dead:
            log(state, f"  {u.id} ({player.name}) morreu.")
        player.units = [u for u in player.units if u.is_alive()]

    artifacts_effects.on_cleanup_after_combat(state)

    for player in state.players:
        if not player.city.is_alive() and player.units:
            log(state, f"  {player.name} eliminado.")
            player.units = []


def _attack_multiplier(state: GameState, attacker: Unit, target: Unit | None = None) -> int:
    mult = 1
    p = get_player(state, attacker.owner_id)
    if p.double_damage_until_end_night:
        mult *= 2
    if attacker.double_damage:
        mult *= 2
    if _hero_has(attacker, "double_damage_and_resist_vs_stronger") and target is not None:
        if target.life >= attacker.life:
            mult *= 2
    if peoples.is_lobisomem_ativo(state, attacker):
        mult *= 2
    return mult


def _compute_attack_damage(state: GameState, attacker: Unit, base: int,
                           target: Unit | None = None) -> int:
    if _hero_has(attacker, "deals_1_to_4_damage") and target is not None:
        base = state.rng.randint(1, 4)
    return base * _attack_multiplier(state, attacker, target)


def _apply_vovo_bonus(state: GameState, attacker: Unit, dmg: int,
                      target: Unit | None) -> int:
    if target is None:
        return dmg
    if peoples.has_vovo_bonus(state, attacker):
        return dmg + 1
    return dmg


def _apply_amaldicoado(state: GameState, defender: Unit, dmg: int) -> int:
    if defender.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
        return dmg * 2
    return dmg


def _apply_defense(state: GameState, defender: Unit, dmg: int,
                   attacker: Unit | None = None,
                   is_city_retaliation: bool = False) -> tuple[int, list[str]]:
    notes: list[str] = []
    p = get_player(state, defender.owner_id)
    if p.invulnerable_until_end_turn:
        notes.append("invulneravel -> 0")
        return 0, notes
    if _hero_has(defender, "takes_1_damage_when_attacked") and not is_city_retaliation:
        if dmg > 0:
            dmg = min(dmg, 1)
    original = dmg
    for _ in range(defender.resistance_stacks):
        dmg = dmg // 2
    if _hero_has(defender, "resistance_aura"):
        dmg = dmg // 2
        notes.append("Ori aura")
    else:
        for u in p.units:
            if isinstance(u, Hero) and u.is_alive() and _hero_has(u, "resistance_aura"):
                if u.house == defender.house:
                    dmg = dmg // 2
                    notes.append("Ori aura (aliado)")
                    break
    if attacker is not None and _hero_has(defender, "double_damage_and_resist_vs_stronger"):
        if attacker.life >= defender.life:
            dmg = dmg // 2
            notes.append("Besouro resistencia")
    if dmg < original:
        notes.append(f"dano {original} -> {dmg}")
    return dmg, notes


def _apply_armor(state: GameState, defender_player_id: int, dmg: int) -> int:
    p = get_player(state, defender_player_id)
    if p.armor_gold_cap_per_hit <= 0 or dmg <= 0:
        return dmg
    cap = p.armor_gold_cap_per_hit
    limite = min(dmg, cap, p.city.gold)
    if limite <= 0:
        return dmg
    p.city.gold -= limite
    log(state, f"    Armadura de Ouro absorveu {limite} (restam {p.city.gold} Ouro).")
    return dmg - limite


def _check_can_attack(state: GameState, unit: Unit) -> None:
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        raise CombatError(f"Unidade {unit.id} nao pode atacar (Espoliou).")
    if unit.statuses.get("sono_until_turn", -1) > state.turn:
        raise CombatError(f"Unidade {unit.id} esta dormindo (Bein).")


def _compute_bein_sleep_until(state: GameState, attacker_owner_id: int) -> int:
    order = state.turn_order
    if not order:
        return state.turn + 1
    if attacker_owner_id not in order or state.curuna_id not in order:
        return state.turn + 1
    curuna_idx = order.index(state.curuna_id)
    owner_idx = order.index(attacker_owner_id)
    delta = (owner_idx - curuna_idx) % len(order)
    if delta == 0:
        delta = len(order)
    return state.turn + delta


def _apply_vampiro_after_round(state: GameState, attacker: Unit, target: Unit,
                               atk_life_before: int, tgt_life_before: int,
                               target_was_hero_or_troop: bool) -> None:
    ap = get_player(state, attacker.owner_id)
    if ap.people != peoples.PEOPLE_VAMPIRES:
        return
    if atk_life_before == tgt_life_before and atk_life_before > 0:
        if not attacker.is_alive():
            attacker.life = 2
            log(state, f"    {attacker.id} sobreviveu com 2 (Sede de Sangue).")
    if not target.is_alive() and target_was_hero_or_troop:
        before = attacker.life
        attacker.life = min(attacker.life_max, attacker.life + 2)
        if attacker.life != before:
            log(state, f"    {attacker.id} curou +{attacker.life - before} (Sede de Sangue).")


def _resolve_combat_round(state: GameState, attacker: Unit, target: Unit) -> None:
    attacker_player = get_player(state, attacker.owner_id)
    target_player = get_player(state, target.owner_id)

    attacker.statuses.pop("invisivel_until_turn", None)

    atk_life = attacker.life
    tgt_life = target.life

    raw_atk = _compute_attack_damage(state, attacker, atk_life, target=target)
    raw_atk = _apply_vovo_bonus(state, attacker, raw_atk, target)
    raw_atk = _apply_amaldicoado(state, target, raw_atk)
    raw_tgt = _compute_attack_damage(state, target, tgt_life, target=attacker)
    raw_tgt = _apply_vovo_bonus(state, target, raw_tgt, attacker)
    raw_tgt = _apply_amaldicoado(state, attacker, raw_tgt)

    dmg_to_target, notes_t = _apply_defense(state, target, raw_atk, attacker)
    dmg_to_attacker, notes_a = _apply_defense(state, attacker, raw_tgt, target)

    dmg_to_target = _apply_armor(state, target.owner_id, dmg_to_target)
    dmg_to_attacker = _apply_armor(state, attacker.owner_id, dmg_to_attacker)

    attacker.life = max(0, atk_life - dmg_to_attacker)
    target.life = max(0, tgt_life - dmg_to_target)

    _apply_vampiro_after_round(state, attacker, target, atk_life, tgt_life,
                               target_was_hero_or_troop=True)

    if not attacker.is_alive():
        attacker.statuses["life_at_death"] = atk_life
    if not target.is_alive():
        target.statuses["life_at_death"] = tgt_life

    if not _hero_has(attacker, "sleep_on_attack"):
        if target.statuses.get("sono_until_turn", -1) > state.turn:
            target.statuses.pop("sono_until_turn", None)
            log(state, f"    {target.id} acordou (foi atacado).")

    if _hero_has(attacker, "sleep_on_attack") and target.is_alive():
        sono_until = _compute_bein_sleep_until(state, attacker.owner_id)
        target.statuses["sono_until_turn"] = sono_until
        log(state, f"    {target.id} adormeceu (ate turno {sono_until}).")

    if _hero_has(target, "kill_attacker_at_night_end") and dmg_to_target > 0:
        state.dain_kills.append({"attacker_id": attacker.id, "turn": state.turn})
        log(state, f"    {attacker.id} atacou Dain e morrera no fim da noite.")

    extra = ""
    if notes_t:
        extra += f" [alvo: {'; '.join(notes_t)}]"
    if notes_a:
        extra += f" [atacante: {'; '.join(notes_a)}]"

    log(state, f"  {attacker.id} ({attacker_player.name}) atacou "
               f"{target.id} ({target_player.name}): "
               f"{attacker.id} {atk_life} -> {attacker.life}, "
               f"{target.id} {tgt_life} -> {target.life}{extra}.")

    if not attacker.is_alive():
        attacker.killed_by_player_id = target.owner_id
    if not target.is_alive():
        target.killed_by_player_id = attacker.owner_id


def resolve_attack(state: GameState, attack: Attack) -> None:
    attacker = _find_unit(state, attack.attacker_unit_id)
    if attacker is None:
        raise CombatError(f"Atacante {attack.attacker_unit_id} nao encontrado.")
    _check_can_attack(state, attacker)
    max_atk = _effective_max_attacks(state, attacker)
    if _attacks_used(attacker) >= max_atk:
        raise CombatError(f"Unidade {attacker.id} ja atacou o maximo.")

    attacker_player = get_player(state, attacker.owner_id)
    attacker_name = attacker_player.name

    if attack.target_type == "city" and attacker_player.no_city_attacks_until_end_turn:
        raise CombatError(f"{attacker_name} nao pode atacar Cidades (Qh).")

    if attack.target_type == "city":
        can_hero_attack_city = attacker.hero_can_attack_city
        if isinstance(attacker, Hero) and not can_hero_attack_city:
            if _hero_has(attacker, "dwarves_can_attack_cities"):
                can_hero_attack_city = True
            elif _hero_has(attacker, "veu_da_lua"):
                if peoples.is_lua_cheia(state, attacker.owner_id):
                    can_hero_attack_city = True
            else:
                owner = get_player(state, attacker.owner_id)
                for u in owner.units:
                    if (isinstance(u, Hero) and u.is_alive()
                            and u.hero_id == "din" and u.house == attacker.house):
                        can_hero_attack_city = True
                        break
        if isinstance(attacker, Hero) and not can_hero_attack_city:
            raise CombatError("Heroi nao pode atacar Cidade (CMB-002).")
        if not attack.target_id.isdigit():
            raise CombatError("Alvo de cidade deve ser id.")
        target_pid = int(attack.target_id)
        if target_pid == attacker.owner_id:
            raise CombatError("Nao pode atacar a propria Cidade.")
        target_player = get_player(state, target_pid)
        city = target_player.city
        if not city.is_alive():
            raise CombatError(f"Cidade ja destruida.")

        attacker.statuses.pop("invisivel_until_turn", None)

        dmg_to_city = _compute_attack_damage(state, attacker, 1)
        life_before = city.life
        city.life = max(0, city.life - dmg_to_city)
        log(state, f"  {attacker.id} ({attacker_name}) atacou Cidade de "
                   f"{target_player.name}: {life_before} -> {city.life}.")
        if life_before > 0 and city.life == 0:
            if city.has_monument:
                log(state, f"  A Cidade de {target_player.name} ruiu - Monumento tambem.")
            else:
                log(state, f"  A Cidade de {target_player.name} ruiu.")
            _award_city_destruction(state, attacker.owner_id)

        raw_ret = 1
        ret, notes = _apply_defense(state, attacker, raw_ret, is_city_retaliation=True)
        if _hero_has(attacker, "takes_1_damage_when_attacked") and raw_ret > 0:
            ret, notes = _apply_defense(state, attacker, 1, is_city_retaliation=True)
        ret = _apply_armor(state, attacker.owner_id, ret)
        if ret == 0 and attacker_player.invulnerable_until_end_turn:
            log(state, f"  Retaliacao ignorada (invulneravel).")
        else:
            before = attacker.life
            attacker.life = max(0, attacker.life - ret)
            note_str = f" [{'; '.join(notes)}]" if notes else ""
            log(state, f"  Retaliacao: {attacker.id} {before} -> {attacker.life}{note_str}.")
            if not attacker.is_alive():
                attacker.statuses["life_at_death"] = before
                attacker.killed_by_player_id = target_pid

    elif attack.target_type == "unit":
        target = _find_unit(state, attack.target_id)
        if target is None:
            raise CombatError(f"Alvo nao encontrado.")
        if target.owner_id == attacker.owner_id:
            raise CombatError("Nao pode atacar aliado.")
        if target.statuses.get("invisivel_until_turn", -1) >= state.turn:
            raise CombatError(f"{target.id} esta invisivel.")
        if _hero_has(target, "cannot_be_attacked_by_heroes") and isinstance(attacker, Hero):
            raise CombatError(f"{target.id} (Buin) nao pode ser atacado por Herois.")

        if _hero_has(attacker, "execute_weak_targets"):
            aliados = [
                u for u in get_player(state, target.owner_id).units
                if u.house == target.house and u.is_alive() and u.id != target.id
            ]
            if not aliados:
                target.statuses["life_at_death"] = target.life
                target.life = 0
                target.killed_by_player_id = attacker.owner_id
                log(state, f"  {attacker.id} EXECUTOU {target.id}.")
                if _hero_has(attacker, "grow_per_execute"):
                    attacker.life_max += 1
                    attacker.life += 1
                    log(state, f"  {attacker.id} cresceu para "
                               f"{attacker.life}/{attacker.life_max}.")
                _register_attack(attacker)
                _cleanup_dead(state)
                return

        _resolve_combat_round(state, attacker, target)

    else:
        raise CombatError(f"Tipo invalido: {attack.target_type}")

    _register_attack(attacker)
    _cleanup_dead(state)


def resolve_attack_day(state: GameState, attack: Attack) -> None:
    attacker = _find_unit(state, attack.attacker_unit_id)
    if attacker is None:
        raise CombatError(f"Atacante nao encontrado.")
    max_atk = _effective_max_attacks(state, attacker)
    if _attacks_used(attacker) >= max_atk:
        raise CombatError(f"Unidade {attacker.id} ja atacou o maximo.")
    if attack.target_type != "unit":
        raise CombatError("Ataque diurno so ataca unidades.")
    target = _find_unit(state, attack.target_id)
    if target is None:
        raise CombatError(f"Alvo nao encontrado.")
    if target.owner_id == attacker.owner_id:
        raise CombatError("Nao pode atacar aliado.")
    if target.statuses.get("invisivel_until_turn", -1) >= state.turn:
        raise CombatError(f"{target.id} esta invisivel.")
    _resolve_combat_round(state, attacker, target)
    _register_attack(attacker)
    _cleanup_dead(state)


def resolve_night(state: GameState, attacks: list[Attack]) -> None:
    if not attacks:
        log(state, "Nenhum ataque nesta Noite.")
        return
    order = ["center", "city_4", "city_3", "city_2", "city_1"]
    by_house: dict[str, list[Attack]] = {}
    for a in attacks:
        unit = _find_unit(state, a.attacker_unit_id)
        house = unit.house if unit else "?"
        by_house.setdefault(house, []).append(a)
    for house in order:
        for a in by_house.get(house, []):
            resolve_attack(state, a)
    for house, atks in by_house.items():
        if house in order:
            continue
        for a in atks:
            resolve_attack(state, a)
'''

# =============================================================
# jessica/core/artifacts_effects.py
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
        if e["player_id"] == player_id and e["due_turn"] == state.turn:
            triggered.append(e)
    for e in triggered:
        state.pending_effects.remove(e)
        if e["kind"] == "J_D":
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
# jessica/core/actions.py
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
            raise ActionError("Mortos-Vivos: escolha o heroi no momento de invocar.")
        hid = heroes.normalize_hero_id(force_hero_id)
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == hid
               for u in player.units):
            raise ActionError(f"Heroi {hid} ja em campo.")
        magic_cost = peoples.hero_summon_cost(player)
        if city.magic < magic_cost:
            raise ActionError(f"Magia insuficiente ({magic_cost}).")
        city.magic -= magic_cost
        hdef = heroes.get_hero(hid)
        hero_life_max = hdef.life
        unit_id = f"p{player_id}_hero_{hdef.hero_id}"
        hero = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",
                    life=hero_life_max, life_max=hero_life_max,
                    hero_id=hdef.hero_id, has_moved_this_turn=True)
        player.units.append(hero)
        record_action(state, player_id, "summon_hero", hero_id=hdef.hero_id)
        log(state, f"{player.name} invocou {hdef.name} ({hero_life_max}).")
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
    log(state, f"{player.name} Resistencia em {t.id}.")


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
    t.max_moves_this_turn = max(2, t.max_moves_this_turn)
    if t.moves_this_turn == 0 and t.has_moved_this_turn:
        t.has_moved_this_turn = False
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
# jessica/core/turn.py
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
    """Cobra: reencarna herois mortos como Espectros."""
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
    """Caroço: a cada 4 turnos, ganha +1 Caroço. Gigantes: vida dobra."""
    if state.turn % 4 != 0:
        return
    for player in state.players:
        if player.people != peoples.PEOPLE_GIGANTES:
            continue
        if not player.city.is_alive():
            continue
        # Dobra vida de Joao Grandao e Pe Descalco
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                if u.hero_id in ("joao_grandao", "pe_descalco"):
                    u.life_max *= 2
                    u.life = u.life_max
                    log(state, f"{player.name}: {u.hero_id} vida dobrada ({u.life_max}).")
        # Adiciona Caroco se tiver
        if any(isinstance(u, Hero) and u.hero_id == "caroco" for u in player.units):
            player.carocos_gerados += 1
            n = sum(1 for u in player.units if isinstance(u, Hero))
            unit_id = f"p{player.id}_caroco_extra_{n}"
            from .models import Hero as H
            hero = H(id=unit_id, owner_id=player.id, house=f"city_{player.id}",
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
    _luna_return_prompt_placeholder(state)
    state.phase = Phase.NIGHT
    log(state, f"--- Fase da Noite (Turno {state.turn}) ---")


def _luna_return_prompt_placeholder(state: GameState) -> None:
    """Placeholder — a confirmacao real fica na UI (fix posterior)."""
    pass


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
# jessica/core/serialize.py
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
# jessica/core/setup.py
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
    log(state, f"Ordem de turno: {order}")

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
    for pid in order:
        povo = choices[pid]["povo"]
        chosen_peoples[pid] = povo
        get_player(state, pid).people = povo
        log(state, f"Jogador {pid} escolheu: {povo}")

    chosen_heroes: dict[int, str] = {}
    for pid in order:
        povo = choices[pid]["povo"]
        if povo == "mortos_vivos":
            # Sem escolha no setup
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


if __name__ == "__main__":
    main()