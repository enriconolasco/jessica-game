"""
apply_update.py (batch 2026-09-17 v2)
Implementa: 7 Anões, Iúna, Sonho Lúcido, Mandinga do Besouro, Pena.
"""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.resolve()
BACKUP_DIR = ROOT / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

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
    "seven_dwarves": HeroDefinition("seven_dwarves", "anoes", "Os 7 Anões", 1,
        ("seven_dwarves",)),
    # 7 anões individuais
    "dain": HeroDefinition("dain", "anoes", "Dain, o Alérgico", 1,
        ("kill_attacker_at_night_end",)),
    "buin": HeroDefinition("buin", "anoes", "Buin, o Dengoso", 2,
        ("cannot_be_attacked_by_heroes",)),
    "bein": HeroDefinition("bein", "anoes", "Bein, o Soneca", 3,
        ("sleep_on_attack",)),
    "boin": HeroDefinition("boin", "anoes", "Boin, o Feliz", 4,
        ("see_2_pick_1_artifact",)),
    "tintin": HeroDefinition("tintin", "anoes", "Tin Tin, o Bobão", 5,
        ("can_be_invisible",)),
    "don": HeroDefinition("don", "anoes", "Don, o Zangado", 6,
        ("extra_attacks_per_dwarf",)),
    "din": HeroDefinition("din", "anoes", "Din, o Mestre", 7,
        ("dwarves_can_attack_cities",)),
    "garoche": HeroDefinition("garoche", "orcs", "Ga'Roche, Rei do Sertão", 3,
        ("execute_weak_targets", "grow_per_execute")),
    "arken": HeroDefinition("arken", "orcs", "Arken, Caçador de Uma Só Flecha", 4,
        ("espolia_daily",)),
    "vovo_gamba": HeroDefinition("vovo_gamba", "orcs", "Vovó Gamba, Protetora dos Espíritos", 3,
        ("tropa_bonus_damage", "choose_attack_time")),
    "ainai": HeroDefinition("ainai", "fadas", "Ainai, Fada da Vingança", 5,
        ("move_to_fallen_fae",)),
    "valendar": HeroDefinition("valendar", "fadas", "Valendar, Rainha Maga", 5,
        ("substitutes_spell",)),
    "luna": HeroDefinition("luna", "fadas", "Luna, Sonhadora de Realidades", 2,
        ("spell_multi_artifact", "return_move")),
}

SEVEN_DWARVES_ORDER = ["dain", "buin", "bein", "boin", "tintin", "don", "din"]


LEGACY_NAMES: dict[str, str] = {
    "Miyamoto Musashi": "miyamoto",
    "Besouro Mangangá": "besouro",
    "Iúna": "iuna",
    "Barbadourada": "barbadourada",
    "Ori": "ori",
    "Ori, Velho Mestre Ferreiro": "ori",
    "Os 7 Anões": "seven_dwarves",
    "Ga'Roche": "garoche",
    "Ga'Roche, Rei do Sertão": "garoche",
    "Arken": "arken",
    "Arken, Caçador de Uma Só Flecha": "arken",
    "Vovó Gamba": "vovo_gamba",
    "Vovó Gamba, Protetora dos Espíritos": "vovo_gamba",
    "Ainai": "ainai",
    "Ainai, Fada da Vingança": "ainai",
    "Valendar": "valendar",
    "Valendar, Rainha Maga": "valendar",
    "Luna": "luna",
    "Luna, Sonhadora de Realidades": "luna",
    "Dain": "dain",
    "Buin": "buin",
    "Bein": "bein",
    "Boin": "boin",
    "Tin Tin": "tintin",
    "Don": "don",
    "Din": "din",
}


def heroes_for_people(people: str) -> list[HeroDefinition]:
    # Para o setup, expor apenas os 3 heróis "escolhíveis"
    if people == "anoes":
        return [HERO_CATALOG[h] for h in ("barbadourada", "ori", "seven_dwarves")]
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
    raise KeyError(f"Herói desconhecido: {raw}")


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
    """Devolve o próximo anão (menor vida) que ainda não está vivo."""
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
# jessica/core/artifacts.py
# =============================================================
FILES["jessica/core/artifacts.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass, field
from .constants import ARTIFACTS_PER_CARD_IN_SHOP
from .rng import DeterministicRNG


@dataclass(frozen=True)
class ArtifactDefinition:
    card_id: str
    rank: str
    suit: str
    name: str
    description: str


ARTIFACT_CATALOG: dict[str, ArtifactDefinition] = {
    "J_H": ArtifactDefinition("J_H", "J", "H", "Memórias Ancestrais",
        "Invoque outro Herói do seu povo."),
    "Q_H": ArtifactDefinition("Q_H", "Q", "H", "Bênção da Natureza",
        "Aliados e Cidade invulneráveis neste turno; sem ataques a Cidades."),
    "K_H": ArtifactDefinition("K_H", "K", "H", "Aquilombar",
        "+1 Vida e +1 Vida máxima toda manhã."),
    "J_D": ArtifactDefinition("J_D", "J", "D", "Tabaréu que Vem do Sertão",
        "Daqui a 3 Dias, veja 3 e escolha 2."),
    "Q_D": ArtifactDefinition("Q_D", "Q", "D", "Mel de Ouro Encantado",
        "Escolha unidade. Você e o matador ganham vida máx. dela em Ouro/Magia."),
    "K_D": ArtifactDefinition("K_D", "K", "D", "Balança que Pesa Ouro",
        "+2 Ouro e +1 Magia toda manhã até o fim do jogo."),
    "J_S": ArtifactDefinition("J_S", "J", "S", "Chamado da Lua",
        "Invoque Tropa de 5 em qualquer lugar."),
    "Q_S": ArtifactDefinition("Q_S", "Q", "S", "Chama Eterna da Revolução",
        "Aliados dão o dobro de dano à Noite."),
    "K_S": ArtifactDefinition("K_S", "K", "S", "Véu das Caçadoras",
        "Heróis atacam Cidades. Aliados próximos a Herói batem 2 vezes."),
    "J_C": ArtifactDefinition("J_C", "J", "C", "Travessura Gnômica",
        "Pule o próximo Dia e Noite de um jogador."),
    "Q_C": ArtifactDefinition("Q_C", "Q", "C", "Maldição das Almas Acorrentadas",
        "Controle um Inimigo neste turno."),
    "K_C": ArtifactDefinition("K_C", "K", "C", "Pacto de Salomão",
        "Um aliado: dobro de dano e Resistência até morrer."),
    "PENA": ArtifactDefinition("PENA", "", "", "Pena do Manto Sagrado",
        "Humano: +1 dado na Roça permanentemente. Não-humano: dê à Iúna para ganhar outro artefato."),
}


SUIT_SYMBOL = {"H": "♥", "D": "♦", "S": "♠", "C": "♣"}


def card_display(card_id: str) -> str:
    d = ARTIFACT_CATALOG[card_id]
    if d.suit:
        return f"{d.rank}{SUIT_SYMBOL[d.suit]} {d.name}"
    return d.name


def get_definition(card_id: str) -> ArtifactDefinition:
    if card_id not in ARTIFACT_CATALOG:
        raise KeyError(f"Carta desconhecida: {card_id}")
    return ARTIFACT_CATALOG[card_id]


def make_full_deck() -> list[str]:
    deck: list[str] = []
    for card_id in ARTIFACT_CATALOG:
        if card_id == "PENA":
            continue  # Pena só entra via Iúna
        deck.extend([card_id] * ARTIFACTS_PER_CARD_IN_SHOP)
    return deck


@dataclass
class Shop:
    deck: list[str] = field(default_factory=make_full_deck)

    def is_empty(self) -> bool:
        return not self.deck

    def size(self) -> int:
        return len(self.deck)

    def draw_random(self, rng: DeterministicRNG) -> str:
        if not self.deck:
            raise ValueError("Loja vazia.")
        idx = rng.randrange(len(self.deck))
        return self.deck.pop(idx)

    def return_card(self, card_id: str) -> None:
        self.deck.append(card_id)

    def copies_of(self, card_id: str) -> int:
        return self.deck.count(card_id)
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

    # Sonho Lúcido / Valendar
    sonho_lucido_used_turn: int = -1
    sonho_lucido_pending_turn: int = -1
    vender_por_magia_turn: int = -1
    andar_duas_vezes_turn: int = -1
    bater_primeiro_turn: int = -1

    # Iúna / Pena
    pena_added_once: bool = False
    besouro_mandinga_used_turn: int = -1

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

    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.city.is_alive()]

    def player(self, pid: int) -> Player:
        for p in self.players:
            if p.id == pid:
                return p
        raise ValueError(f"Jogador {pid} não encontrado")
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
                log(state, f"{player.name}: Barbadourada — +{n} Magia.")


def _dwarves_mineiro_carreiro(state: GameState, player: Player) -> None:
    count = sum(1 for u in player.units if u.is_alive())
    player.city.gold += count
    log(state, f"{player.name} (Anões): Mineiro Carreiro — +{count} Ouro.")


def _humans_roca_de_quilombo(state: GameState, player: Player) -> None:
    # +1 dado por Pena ATIVA em campo (Pena em campo, não na mão)
    num_penas = sum(1 for a in player.field_artifacts if a.card_id == "PENA")
    num_dice = 1 + num_penas
    rolls = [state.rng.randint(1, 4) for _ in range(num_dice)]
    log(state, f"{player.name} (Humanos): Roça — {num_dice}D4 = {rolls}.")
    for r in rolls:
        _apply_roca_result(state, player, r)


def _apply_roca_result(state: GameState, player: Player, result: int) -> None:
    if result == 1:
        player.city.magic += 1
        log(state, "  → +1 Magia.")
    elif result == 2:
        player.city.gold += 1
        log(state, "  → +1 Ouro.")
    elif result == 3:
        player.pending_heals += 1
        log(state, f"  → Cura 2 pendente ({player.pending_heals}).")
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
        log(state, "  → Dano: sem inimigos na Cidade.")
        return
    for u in enemies:
        u.life = max(0, u.life - 1)
        log(state, f"  → 1 dano em {u.id}: {u.life}/{u.life_max}.")
    for other in state.players:
        dead = [u for u in other.units if not u.is_alive()]
        for d in dead:
            log(state, f"  {d.id} morreu (Roça).")
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
            log(state, f"{killer_player.name} (Fadas): matou Herói e ganhou {card}.")

    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if not heroes.has_ability(u.hero_id, "gain_max_life_on_kill"):
            continue
        if u.house == dead_unit.house:
            ganho = dead_unit.statuses.get("life_at_death", dead_unit.life_max)
            u.life_max += ganho
            log(state, f"  {u.id} (Miyamoto) +{ganho} vida máxima.")


# ---------- Vovó Gamba ----------

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


# ---------- Valendar / Sonho Lúcido ----------

def valendar_is_alive(player: Player) -> bool:
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "valendar"
               for u in player.units)


def luna_is_alive(player: Player) -> bool:
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
               for u in player.units)


SUIT_FLIP = {"H": "D", "D": "H", "S": "C", "C": "S"}


def sonho_lucido_flip(card_id: str) -> str:
    """Troca o naipe para o outro da mesma cor (H<->D, S<->C). Mantém rank."""
    from . import artifacts
    d = artifacts.ARTIFACT_CATALOG.get(card_id)
    if d is None or not d.suit:
        return card_id
    other_suit = SUIT_FLIP[d.suit]
    new_id = f"{d.rank}_{other_suit}"
    if new_id in artifacts.ARTIFACT_CATALOG:
        return new_id
    return card_id


# ---------- Modificadores ----------

def magic_cost_reduction(player: Player) -> int:
    if player.people == PEOPLE_ORCS:
        return 1
    return 0


def base_troop_slots() -> dict[str, int]:
    return {"light": 1, "medium": 1, "heavy": 1}


def extra_troop_slots(player: Player) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    return {}


def max_troops_of_archetype(player: Player, archetype: TroopArchetype) -> int:
    base = base_troop_slots().get(archetype.value, 0)
    extras = extra_troop_slots(player)
    return base + extras.get(archetype.value, 0)


def available_archetypes(player: Player) -> list[TroopArchetype]:
    result = [TroopArchetype.LIGHT, TroopArchetype.MEDIUM, TroopArchetype.HEAVY]
    if player.people == PEOPLE_ORCS:
        result.append(TroopArchetype.EXTRA)
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
# jessica/core/actions.py
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


SEVEN_DWARVES_COST = 2  # magia por anão


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
    player = get_player(state, player_id)
    if peoples.has_7_dwarves_chosen(player):
        raise ActionError("Escolheu Os 7 Anões: não pode invocar Tropas.")
    max_life = TROOP_MAX_LIFE[archetype.value]
    if life < 1 or life > max_life:
        raise ActionError(f"Vida inválida: {life}. Máx {max_life}.")
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


def summon_hero(state: GameState, player_id: int, force_hero_id: str | None = None) -> Hero:
    """
    Invoca herói. Se o escolhido for seven_dwarves, invoca o próximo anão
    da corrente. Se force_hero_id for passado (J♥), invoca aquele herói específico.
    """
    player = get_player(state, player_id)
    city = player.city
    if not city.is_alive():
        raise ActionError("Cidade destruída.")
    if not player.chosen_hero_id:
        raise ActionError("Sem herói escolhido.")

    # Caso especial: seven_dwarves
    if player.chosen_hero_id == "seven_dwarves" and force_hero_id is None:
        alive_ids = {u.hero_id for u in player.units
                     if isinstance(u, Hero) and u.is_alive()}
        next_hid = heroes.next_dwarf_to_summon(alive_ids)
        if next_hid is None:
            raise ActionError("Todos os 7 Anões já foram invocados.")
        # Corrente: anão N só pode ser invocado se N-1 vivo (ou se for o primeiro)
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

    # Caso geral
    alive_heroes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()]
    if alive_heroes and force_hero_id is None:
        raise ActionError("Já existe herói vivo.")
    # Se forçar um herói específico, checa se já existe
    target_id = force_hero_id if force_hero_id is not None else player.chosen_hero_id
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == target_id
           for u in player.units):
        raise ActionError(f"Herói {target_id} já em campo.")

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
    # Iúna: adiciona 4 Penas (uma vez por partida)
    if hdef.hero_id == "iuna" and not player.pena_added_once:
        # Marca como já adicionada (por partida, qualquer jogador)
        any_pena_added = any(p.pena_added_once for p in state.players)
        if not any_pena_added:
            for _ in range(4):
                state.shop.return_card("PENA")
            player.pena_added_once = True
            log(state, "Iúna: 4 Penas do Manto Sagrado adicionadas à Loja.")
    return hero


def move_unit(state: GameState, player_id: int, unit_id: str, destination: str) -> None:
    if destination not in (CENTER, *CITY_HOUSES):
        raise ActionError(f"Destino inválido: {destination}")
    player = get_player(state, player_id)
    unit = next((u for u in player.units if u.id == unit_id and u.is_alive()), None)
    if unit is None:
        raise ActionError(f"Unidade {unit_id} não encontrada.")
    if unit.moves_this_turn >= unit.max_moves_this_turn:
        raise ActionError("Unidade já se moveu o máximo neste turno.")
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


def arken_espolia(state: GameState, player_id: int) -> None:
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
    log(state, f"{player.name} (Arken): Espoliou {len(occupied_pids)} Cidade(s) — +{gold} Ouro.")
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


# ---------- Mandinga do Besouro ----------

def besouro_mandinga(state: GameState, player_id: int, card_id: str,
                     choice: dict | None = None) -> None:
    """Besouro: jogar 1 artefato da mão no início da Noite, 1× por Noite."""
    player = get_player(state, player_id)
    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"),
                   None)
    if besouro is None:
        raise ActionError("Besouro não está vivo.")
    if player.besouro_mandinga_used_turn == state.turn:
        raise ActionError("Mandinga já usada nesta Noite.")
    if card_id not in player.hand:
        raise ActionError(f"{player.name} não tem {card_id}.")
    # Reusa play_artifact (que trata needs_choice)
    play_artifact(state, player_id, card_id, choice=choice or {})
    player.besouro_mandinga_used_turn = state.turn
    log(state, f"{player.name}: Besouro usou Mandinga com {card_display(card_id)}.")


# ---------- Pena ----------

def use_or_give_pena(state: GameState, player_id: int, card_id: str,
                     give_to_iuna: bool) -> None:
    """
    Se jogador é Humano: a Pena vira buff permanente (fica em campo).
    Se não é Humano:
      - give_to_iuna=True: entrega à Iúna (dono), ganha 1 artefato aleatório da Loja.
      - give_to_iuna=False: fica com a Pena (pode vender por 7 Ouro depois).
    """
    player = get_player(state, player_id)
    if card_id != "PENA":
        raise ActionError("Só aplica para Pena.")
    if card_id not in player.hand:
        raise ActionError(f"{player.name} não tem Pena.")

    if player.people == "humanos":
        # Vira artefato de campo permanente
        player.hand.remove(card_id)
        player.field_artifacts.append(ArtifactOnField(card_id="PENA", owner_id=player_id))
        log(state, f"{player.name} (Humanos): Pena ativa. Roça ganha +1 dado.")
        record_action(state, player_id, "pena_activate")
        return

    if give_to_iuna:
        # Procura quem tem Iúna
        iuna_owner = None
        for p in state.players:
            for u in p.units:
                if isinstance(u, Hero) and u.is_alive() and u.hero_id == "iuna":
                    iuna_owner = p
                    break
            if iuna_owner:
                break
        if iuna_owner is None:
            raise ActionError("Iúna não está viva. Só pode ficar com a Pena.")
        player.hand.remove(card_id)
        # Iúna ganha a Pena (a Pena é devolvida à Loja, o comprador ganha nova)
        state.shop.return_card(card_id)
        # Comprador ganha 1 artefato aleatório
        if not state.shop.is_empty():
            new_card = state.shop.draw_random(state.rng)
            player.hand.append(new_card)
            log(state, f"{player.name} deu a Pena à Iúna e ganhou {card_display(new_card)}.")
        else:
            log(state, f"{player.name} deu a Pena à Iúna (Loja vazia, sem troca).")
        record_action(state, player_id, "pena_give_iuna")
        return

    # Fica com a Pena (sem efeito até segunda ordem)
    log(state, f"{player.name}: ficou com a Pena (sem efeito).")
    record_action(state, player_id, "pena_keep")


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
    elif sp.spell_id == "sonho_lucido":
        # Apenas marca que Sonho Lúcido está ativo neste turno
        player.sonho_lucido_pending_turn = state.turn
        log(state, f"{player.name}: Sonho Lúcido ativo — próximos artefatos jogados trocarão de naipe.")
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
        raise ActionError("Alvo não encontrado.")
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


def _apply_valendar_bonus(state: GameState, player, card_id: str) -> None:
    """
    Aplica bônus de naipe de Valendar se ativa, ao jogar um artefato.
      ♥ Cura todos os heróis ao máximo
      ♦ Vender artefatos por 7 Magia neste turno
      ♣ Heróis andam duas vezes neste turno
      ♠ Bate primeiro (declara antes na Noite)
    """
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
        log(state, f"  Valendar ♥: heróis curados ao máximo.")
    elif suit == "D":
        player.vender_por_magia_turn = state.turn
        log(state, f"  Valendar ♦: heróis venderão por 7 Magia neste turno.")
    elif suit == "C":
        player.andar_duas_vezes_turn = state.turn
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                u.max_moves_this_turn = 2
                u.has_moved_this_turn = False
        log(state, f"  Valendar ♣: heróis andarão duas vezes neste turno.")
    elif suit == "S":
        player.bater_primeiro_turn = state.turn
        log(state, f"  Valendar ♠: heróis declararão antes nesta Noite.")


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

    # Valendar ♦: vende por Magia (7)
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
        raise ActionError(f"{player.name} não tem {card_id}.")

    # Sonho Lúcido: se ativo, troca naipe automaticamente (antes de checar is_implemented)
    if player.sonho_lucido_pending_turn == state.turn:
        new_card = peoples.sonho_lucido_flip(card_id)
        if new_card != card_id:
            player.hand.remove(card_id)
            player.hand.append(new_card)
            log(state, f"Sonho Lúcido: {card_display(card_id)} → {card_display(new_card)}.")
            card_id = new_card
            player.sonho_lucido_used_turn = state.turn

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
    # Valendar aplica bônus por naipe
    _apply_valendar_bonus(state, player, card_id)
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
'''

# =============================================================
# jessica/core/combat.py
# =============================================================
FILES["jessica/core/combat.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass
from .state import get_player, get_city, log
from .models import GameState, Unit, Hero, Troop


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
        from . import peoples
        base = peoples.compute_hero_max_attacks_in_house(
            state, unit, "double_attack_if_stronger")
        k_s_bonus = max(0, unit.max_attacks_this_night - 1)
        return base + k_s_bonus
    # Don: +1 ataque por anão próximo
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
    from . import artifacts_effects, peoples

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
    return mult


def _compute_attack_damage(state: GameState, attacker: Unit, base: int,
                           target: Unit | None = None) -> int:
    # Iúna: 1-4 de dano aleatório
    if _hero_has(attacker, "deals_1_to_4_damage") and target is not None:
        base = state.rng.randint(1, 4)
    return base * _attack_multiplier(state, attacker, target)


def _apply_vovo_bonus(state: GameState, attacker: Unit, dmg: int,
                      target: Unit | None) -> int:
    if target is None:
        return dmg
    from . import peoples
    if peoples.has_vovo_bonus(state, attacker):
        return dmg + 1
    return dmg


def _apply_defense(state: GameState, defender: Unit, dmg: int,
                   attacker: Unit | None = None,
                   is_city_retaliation: bool = False) -> tuple[int, list[str]]:
    notes: list[str] = []
    p = get_player(state, defender.owner_id)
    if p.invulnerable_until_end_turn:
        notes.append("invulnerável → 0")
        return 0, notes

    # Iúna: recebe exatamente 1 de dano (depois de aplicar dobro/valores)
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
            notes.append("Besouro resistência")
    if dmg < original:
        notes.append(f"dano {original} → {dmg}")
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
        raise CombatError(f"Unidade {unit.id} não pode atacar (Espoliou com Arken).")
    if unit.statuses.get("sono_until_turn", -1) > state.turn:
        raise CombatError(f"Unidade {unit.id} está dormindo.")


def _resolve_combat_round(state: GameState, attacker: Unit, target: Unit) -> None:
    attacker_player = get_player(state, attacker.owner_id)
    target_player = get_player(state, target.owner_id)

    atk_life = attacker.life
    tgt_life = target.life

    raw_atk = _compute_attack_damage(state, attacker, atk_life, target=target)
    raw_atk = _apply_vovo_bonus(state, attacker, raw_atk, target)
    raw_tgt = _compute_attack_damage(state, target, tgt_life, target=attacker)
    raw_tgt = _apply_vovo_bonus(state, target, raw_tgt, attacker)

    dmg_to_target, notes_t = _apply_defense(state, target, raw_atk, attacker)
    dmg_to_attacker, notes_a = _apply_defense(state, attacker, raw_tgt, target)

    dmg_to_target = _apply_armor(state, target.owner_id, dmg_to_target)
    dmg_to_attacker = _apply_armor(state, attacker.owner_id, dmg_to_attacker)

    attacker.life = max(0, atk_life - dmg_to_attacker)
    target.life = max(0, tgt_life - dmg_to_target)

    if not attacker.is_alive():
        attacker.statuses["life_at_death"] = atk_life
    if not target.is_alive():
        target.statuses["life_at_death"] = tgt_life

    # Dain: quem ataca Dain morre no fim da noite
    if _hero_has(target, "kill_attacker_at_night_end") and dmg_to_target > 0:
        target.statuses["_dain_killer"] = attacker.id

    # Bein: dorme quem for atacado
    if _hero_has(attacker, "sleep_on_attack") and target.is_alive():
        target.statuses["sono_until_turn"] = state.turn + 1
        log(state, f"    {target.id} adormeceu (Bein).")

    extra = ""
    if notes_t:
        extra += f" [alvo: {'; '.join(notes_t)}]"
    if notes_a:
        extra += f" [atacante: {'; '.join(notes_a)}]"

    log(state, f"  {attacker.id} ({attacker_player.name}) atacou "
               f"{target.id} ({target_player.name}): "
               f"{attacker.id} {atk_life} → {attacker.life}, "
               f"{target.id} {tgt_life} → {target.life}{extra}.")

    if not attacker.is_alive():
        attacker.killed_by_player_id = target.owner_id
    if not target.is_alive():
        target.killed_by_player_id = attacker.owner_id


def resolve_attack(state: GameState, attack: Attack) -> None:
    attacker = _find_unit(state, attack.attacker_unit_id)
    if attacker is None:
        raise CombatError(f"Atacante {attack.attacker_unit_id} não encontrado.")
    _check_can_attack(state, attacker)
    max_atk = _effective_max_attacks(state, attacker)
    if _attacks_used(attacker) >= max_atk:
        raise CombatError(f"Unidade {attacker.id} já atacou o máximo permitido "
                          f"nesta Noite ({_attacks_used(attacker)}/{max_atk}).")

    attacker_player = get_player(state, attacker.owner_id)
    attacker_name = attacker_player.name

    if attack.target_type == "city" and attacker_player.no_city_attacks_until_end_turn:
        raise CombatError(f"{attacker_name} não pode atacar Cidades (Q♥).")

    if attack.target_type == "city":
        # Herói ataca Cidade só se K♠ ativo ou se for anão perto de Din
        can_hero_attack_city = attacker.hero_can_attack_city
        if isinstance(attacker, Hero) and not can_hero_attack_city:
            if _hero_has(attacker, "dwarves_can_attack_cities"):
                can_hero_attack_city = True  # o próprio Din
            else:
                # Se há um Din vivo do mesmo dono na mesma casa
                owner = get_player(state, attacker.owner_id)
                for u in owner.units:
                    if (isinstance(u, Hero) and u.is_alive()
                            and u.hero_id == "din" and u.house == attacker.house):
                        can_hero_attack_city = True
                        break
        if isinstance(attacker, Hero) and not can_hero_attack_city:
            raise CombatError("Herói não pode atacar Cidade (CMB-002).")
        if not attack.target_id.isdigit():
            raise CombatError("Alvo de cidade deve ser id.")
        target_pid = int(attack.target_id)
        if target_pid == attacker.owner_id:
            raise CombatError("Não pode atacar a própria Cidade.")
        target_player = get_player(state, target_pid)
        city = target_player.city
        if not city.is_alive():
            raise CombatError(f"Cidade já destruída.")

        dmg_to_city = _compute_attack_damage(state, attacker, 1)
        life_before = city.life
        city.life = max(0, city.life - dmg_to_city)
        log(state, f"  {attacker.id} ({attacker_name}) atacou Cidade de "
                   f"{target_player.name}: {life_before} → {city.life}.")
        if life_before > 0 and city.life == 0:
            if city.has_monument:
                log(state, f"  A Cidade de {target_player.name} ruiu — Monumento também.")
            else:
                log(state, f"  A Cidade de {target_player.name} ruiu.")
            _award_city_destruction(state, attacker.owner_id)

        raw_ret = 1
        ret, notes = _apply_defense(state, attacker, raw_ret, is_city_retaliation=True)
        if _hero_has(attacker, "takes_1_damage_when_attacked") and raw_ret > 0:
            ret = min(raw_ret, 1)
            ret, notes = _apply_defense(state, attacker, ret, is_city_retaliation=True)
        ret = _apply_armor(state, attacker.owner_id, ret)
        if ret == 0 and attacker_player.invulnerable_until_end_turn:
            log(state, f"  Retaliação ignorada (invulnerável).")
        else:
            before = attacker.life
            attacker.life = max(0, attacker.life - ret)
            note_str = f" [{'; '.join(notes)}]" if notes else ""
            log(state, f"  Retaliação: {attacker.id} {before} → {attacker.life}{note_str}.")
            if not attacker.is_alive():
                attacker.statuses["life_at_death"] = before
                attacker.killed_by_player_id = target_pid

    elif attack.target_type == "unit":
        target = _find_unit(state, attack.target_id)
        if target is None:
            raise CombatError(f"Alvo não encontrado.")
        if target.owner_id == attacker.owner_id:
            raise CombatError("Não pode atacar aliado.")

        # Buin: não pode ser atacado por Heróis
        if _hero_has(target, "cannot_be_attacked_by_heroes") and isinstance(attacker, Hero):
            raise CombatError(f"{target.id} (Buin) não pode ser atacado por Heróis.")

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
        raise CombatError(f"Tipo inválido: {attack.target_type}")

    _register_attack(attacker)
    _cleanup_dead(state)


def resolve_attack_day(state: GameState, attack: Attack) -> None:
    attacker = _find_unit(state, attack.attacker_unit_id)
    if attacker is None:
        raise CombatError(f"Atacante não encontrado.")
    max_atk = _effective_max_attacks(state, attacker)
    if _attacks_used(attacker) >= max_atk:
        raise CombatError(f"Unidade {attacker.id} já atacou o máximo permitido "
                          f"neste turno ({_attacks_used(attacker)}/{max_atk}).")

    if attack.target_type != "unit":
        raise CombatError("Ataque diurno só ataca unidades.")

    target = _find_unit(state, attack.target_id)
    if target is None:
        raise CombatError(f"Alvo não encontrado.")
    if target.owner_id == attacker.owner_id:
        raise CombatError("Não pode atacar aliado.")

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
         "max_moves_this_turn": u.max_moves_this_turn}
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
                  max_moves_this_turn=d.get("max_moves_this_turn", 1))
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
        "vender_por_magia_turn": p.vender_por_magia_turn,
        "andar_duas_vezes_turn": p.andar_duas_vezes_turn,
        "bater_primeiro_turn": p.bater_primeiro_turn,
        "pena_added_once": p.pena_added_once,
        "besouro_mandinga_used_turn": p.besouro_mandinga_used_turn,
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
        vender_por_magia_turn=d.get("vender_por_magia_turn", -1),
        andar_duas_vezes_turn=d.get("andar_duas_vezes_turn", -1),
        bater_primeiro_turn=d.get("bater_primeiro_turn", -1),
        pena_added_once=d.get("pena_added_once", False),
        besouro_mandinga_used_turn=d.get("besouro_mandinga_used_turn", -1),
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
            "deaths_this_night": list(s.deaths_this_night)}


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
# jessica/main.py
# =============================================================
FILES["jessica/main.py"] = '''\
"""Jéssica - Protótipo v0.2."""
from __future__ import annotations
import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box

from .core.setup import run_setup, roll_d20_order
from .core.state import make_rng, get_player
from .core.actions import (
    collect_resources, raise_city_life, summon_troop, summon_hero,
    move_unit, build_monument, buy_artifact_with_gold,
    transmute_artifact_with_magic, sell_artifact, play_artifact,
    resolve_pending_artifact_choice, use_heal, cast_spell, arken_espolia,
    besouro_mandinga, use_or_give_pena, ActionError,
)
from .core.combat import (
    resolve_attack, resolve_attack_day, Attack, CombatError,
    _effective_max_attacks, _attacks_used,
)
from .core.turn import start_turn, start_player_day, day_order, end_day, end_turn
from .core.constants import (
    CITY_HOUSES, CENTER, TroopArchetype, Phase, DEFAULT_SEED,
    TROOP_MAX_LIFE, RESOURCES_PER_DAY, CITY_LIFE_COST_GOLD,
    HERO_SUMMON_COST_MAGIC, TROOP_SUMMON_COST_MAGIC, MONUMENT_COST_GOLD,
    ARTIFACT_GOLD_COST, ARTIFACT_MAGIC_COST, ARTIFACT_SELL_GOLD,
    DEFAULT_CITY_LIFE_START, DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC,
)
from .core.models import Hero, Troop
from .core.artifacts import card_display, get_definition, ARTIFACT_CATALOG
from .core.serialize import state_to_dict, state_from_dict
from .core import artifacts_effects, peoples, heroes, spells as spells_mod


console = Console()

PEOPLES = ["humanos", "anoes", "orcs", "fadas"]

HEROES_BY_PEOPLE = {
    "humanos": ["Miyamoto Musashi", "Besouro Mangangá", "Iúna"],
    "anoes": ["Barbadourada", "Ori", "Os 7 Anões"],
    "orcs": ["Ga'Roche", "Arken", "Vovó Gamba"],
    "fadas": ["Ainai", "Valendar", "Luna"],
}

PASSIVA_DESC = {
    "humanos": "Roça de Quilombo: rola 1D4 (+1 dado por Pena ativa) toda manhã.",
    "anoes": "Mineiro Carreiro: +1 Ouro por unidade anã viva, toda manhã.",
    "orcs": "Berço de Guerreiros: -1 Magia em invocações. Tem arquétipo extra de tropa (4 vida).",
    "fadas": "Asas Encantadas: +1 Magia quando unidade anda. Heróis ganham 1 artefato ao matar Herói inimigo.",
}

FEITICO_DESC = {
    "resistencia": "Resistência (Humanos): dê Resistência a um aliado nesta Noite.",
    "armadura_de_ouro": "Armadura de Ouro (Anões): cap X por hit.",
    "espoliar": "Espoliar (Orcs): +2 Ouro por Cidade inimiga ocupada.",
    "sonho_lucido": "Sonho Lúcido (Fadas): troca o naipe do próximo artefato automaticamente (♥↔♦, ♠↔♣).",
}

HERO_ABILITY_DESC = {
    "miyamoto": "Invencível sob o Sol: ataca de Dia. +vida máx. ao matar. 2 ataques se for o mais forte.",
    "besouro": "o Maioral: dobro + resistência vs. ≥. Mandinga: 1 artefato da mão no início da Noite.",
    "iuna": "Águia Negra: recebe exatamente 1 de dano. Dá 1D4 aleatório. Adiciona 4 Penas ao ser invocada.",
    "barbadourada": "Filho das Cachoeiras: +1 Magia por artefato na mão, toda manhã.",
    "ori": "Velho Mestre Ferreiro: ele + aliados na mesma casa ganham Resistência.",
    "seven_dwarves": "Os 7 Anões: invoque cada um com 2 Magia, em corrente. Sem Tropas.",
    "dain": "Alérgico (1 vida): quem ataca Dain morre no fim da Noite.",
    "buin": "Dengoso (2): não pode ser atacado por Heróis.",
    "bein": "Soneca (3): quem for atacado dorme (não age) até os Anões serem Curuna.",
    "boin": "Feliz (4): ao receber artefato, vê 2 e escolhe 1.",
    "tintin": "Bobão (5): pode ficar Invisível no Dia (com recarga).",
    "don": "Zangado (6): 1 ataque extra por Anão próximo.",
    "din": "Mestre (7): Anões próximos podem atacar Bases inimigas.",
    "garoche": "Rei do Sertão: executa sem aliados próximos. +1 vida ao executar.",
    "arken": "Caçador: pode Espoliar todo Dia.",
    "vovo_gamba": "Protetora: tropas na casa dela dão +1 dano. Escolhe posição no local.",
    "ainai": "Fada da Vingança: teleporta para onde morreu unidade Fada/Elfo na Noite. +1 Magia.",
    "valendar": "Rainha Maga: substitui Sonho Lúcido por bônus de naipe ao jogar artefatos (♥ cura, ♦ magia, ♣ 2 movimentos, ♠ primeiro).",
    "luna": "Sonhadora: aplica Sonho Lúcido a N artefatos. Retorna ao local de origem se andou.",
}


class RestartGame(Exception):
    pass


def house_display(state, house: str) -> str:
    if house == CENTER:
        return "Centro"
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        return f"Cidade {get_player(state, pid).name}"
    return house


def get_actions_menu(state, player) -> list[tuple[str, str]]:
    magic_reduction = peoples.magic_cost_reduction(player)
    troop_cost = max(0, TROOP_SUMMON_COST_MAGIC - magic_reduction)
    hero_cost = max(0, HERO_SUMMON_COST_MAGIC - magic_reduction)
    sp = spells_mod.spell_for_people(player.people)

    actions = [
        ("1", "Coletar recursos (2)"),
        ("2", f"Subir vida da Cidade ({CITY_LIFE_COST_GOLD} Ouro por +1)"),
    ]
    if not peoples.has_7_dwarves_chosen(player):
        actions.append(("3", f"Invocar Tropa ({troop_cost} Magia + X Ouro)"))
    else:
        actions.append(("3", "[bloqueado] Sem tropas (7 Anões)"))
    if player.chosen_hero_id == "seven_dwarves":
        alive_ids = {u.hero_id for u in player.units if isinstance(u, Hero) and u.is_alive()}
        nxt = heroes.next_dwarf_to_summon(alive_ids)
        label = f"Invocar Herói (próximo: {heroes.hero_name(nxt) if nxt else 'nenhum'})"
        actions.append(("4", label))
    else:
        actions.append(("4", f"Invocar Herói ({hero_cost} Magia)"))
    actions += [
        ("5", "Mover unidade"),
        ("6", f"Construir Monumento ({MONUMENT_COST_GOLD} Ouro)"),
        ("7", f"Comprar Artefato com Ouro ({ARTIFACT_GOLD_COST}, no Centro)"),
        ("8", f"Transmutar Artefato com Magia ({ARTIFACT_MAGIC_COST}, na Cidade)"),
        ("9", f"Vender Artefato ({ARTIFACT_SELL_GOLD} Ouro, no Centro)"),
        ("10", "Jogar Artefato"),
        ("11", "Resumo"),
        ("12", "Mapa"),
        ("13", "Loja"),
        ("14", "Artefatos ativos"),
        ("g", "Habilidades"),
    ]
    miyamoto_atks = peoples.miyamoto_attacks_remaining(state, player)
    if miyamoto_atks > 0:
        actions.append(("d", f"Miyamoto: atacar de Dia ({miyamoto_atks})"))
    arken = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "arken"), None)
    if arken is not None and player.arken_espolia_used_turn != state.turn:
        actions.append(("e", "Arken: Espoliar"))
    if sp:
        cd_str = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd_str = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        actions.append(("f", f"Lançar feitiço: {sp.name}{cd_str}"))
    if player.pending_heals > 0:
        actions.append(("h", f"Usar cura pendente ({player.pending_heals})"))
    actions.append(("u", "Colher de chá (refazer meu dia)"))
    actions.append(("m", "Mola (jogador anterior)"))
    actions.append(("r", "Reiniciar partida"))
    actions.append(("0", "Passar a vez"))
    return actions


def pick_index(prompt: str, options: list[str]) -> int:
    table = Table(box=box.SIMPLE)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Opção")
    for i, opt in enumerate(options, 1):
        table.add_row(str(i), opt)
    console.print(table)
    while True:
        try:
            n = IntPrompt.ask(prompt, default=1)
            if 1 <= n <= len(options):
                return n - 1
        except Exception:
            pass
        console.print(f"[red]Escolha entre 1 e {len(options)}[/red]")


def valid_destinations(state, unit) -> list[str]:
    if unit.house.startswith("city_"):
        return [CENTER]
    if unit.house == CENTER:
        return [h for h in CITY_HOUSES
                if get_player(state, int(h.split("_")[1])).city.is_alive()]
    return []


def _ask_int(prompt: str, default: int, min_val: int = 0, max_val: int = 999) -> int:
    while True:
        try:
            v = IntPrompt.ask(prompt, default=default)
            if min_val <= v <= max_val:
                return v
        except Exception:
            pass
        console.print(f"[red]Valor entre {min_val} e {max_val}.[/red]")


def setup_ui():
    console.print(Panel.fit(
        "[bold cyan]JÉSSICA[/bold cyan]\\n"
        "[italic]Protótipo v0.2[/italic]",
        border_style="cyan",
    ))
    console.print()
    seed = DEFAULT_SEED
    console.print(f"[dim]Seed: {seed}[/dim]\\n")

    console.print("[bold]Configuração da partida[/bold]\\n")
    city_life = _ask_int(f"Vida inicial da Cidade [{DEFAULT_CITY_LIFE_START}]",
                         default=DEFAULT_CITY_LIFE_START, min_val=1, max_val=100)
    city_life_max = _ask_int(f"Vida máxima da Cidade [{DEFAULT_CITY_LIFE_MAX}]",
                             default=DEFAULT_CITY_LIFE_MAX, min_val=city_life, max_val=100)
    gold_start = _ask_int(f"Ouro inicial [{DEFAULT_STARTING_GOLD}]",
                          default=DEFAULT_STARTING_GOLD, min_val=0, max_val=999)
    magic_start = _ask_int(f"Magia inicial [{DEFAULT_STARTING_MAGIC}]",
                           default=DEFAULT_STARTING_MAGIC, min_val=0, max_val=999)
    console.print()

    rng = make_rng(seed)
    order = roll_d20_order(rng, 4)

    table = Table(title="Ordem de turno", box=box.SIMPLE)
    table.add_column("Posição", justify="right")
    table.add_column("Jogador", justify="right")
    for i, pid in enumerate(order, 1):
        table.add_row(str(i), f"Jogador {pid}")
    console.print(table)
    console.print()

    console.print("[bold]Nomes dos jogadores[/bold]\\n")
    names: dict[int, str] = {}
    for pid in range(1, 5):
        names[pid] = Prompt.ask(f"Nome do Jogador {pid}", default=f"Jogador {pid}")
    console.print()

    choices: dict[int, dict] = {}
    console.print("[bold]Escolha de povos[/bold]\\n")
    available_peoples = list(PEOPLES)
    for pid in order:
        console.print(f"Vez de [bold]{names[pid]}[/bold] (Jogador {pid}).")
        idx = pick_index("Povo", available_peoples)
        chosen = available_peoples[idx]
        available_peoples.remove(chosen)
        choices[pid] = {"povo": chosen}
        console.print(f"[green]{names[pid]} escolheu: {chosen}[/green]\\n")

    console.print("[bold]Escolha de heróis[/bold]\\n")
    for pid in order:
        povo = choices[pid]["povo"]
        herois = HEROES_BY_PEOPLE[povo]
        console.print(f"Vez de [bold]{names[pid]}[/bold] ({povo}).")
        idx = pick_index("Herói", herois)
        choices[pid]["heroi"] = herois[idx]
        console.print(f"[green]{names[pid]} escolheu: {herois[idx]}[/green]\\n")

    state, _ = run_setup(
        all_peoples=PEOPLES, heroes_by_people=HEROES_BY_PEOPLE,
        choices=choices, seed=seed, turn_order=order,
        city_life=city_life, city_life_max=city_life_max,
        gold_start=gold_start, magic_start=magic_start,
    )
    for p in state.players:
        p.name = names[p.id]
    return state


def show_state_for_player(state, pid: int) -> None:
    player = get_player(state, pid)
    city = player.city
    mark = " [bold yellow]<- CURUNA[/bold yellow]" if state.curuna_id == pid else ""
    hero_display = "-"
    if player.chosen_hero_id:
        try:
            hd = heroes.get_hero(player.chosen_hero_id)
            hero_display = f"{hd.name} ({hd.life})"
        except KeyError:
            hero_display = player.chosen_hero_id
    sp = spells_mod.spell_for_people(player.people)
    sp_str = ""
    if sp:
        cd = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        sp_str = f" | Feitico: {sp.name}{cd}"

    console.print(f"[bold]{player.name}[/bold]{mark} - Povo: {player.people} - Heroi: {hero_display}{sp_str}")
    console.print(f"Cidade: vida {city.life}/{city.life_max} | Ouro: {city.gold} | Magia: {city.magic} | Mon: {'sim' if city.has_monument else 'nao'}")
    if player.pending_heals > 0:
        console.print(f"[green]Curas pendentes: {player.pending_heals}[/green]")
    if player.armor_gold_cap_per_hit > 0:
        console.print(f"[cyan]Armadura de Ouro - cap {player.armor_gold_cap_per_hit}/hit[/cyan]")
    if player.sonho_lucido_pending_turn == state.turn:
        console.print(f"[magenta]Sonho Lúcido ATIVO neste turno[/magenta]")

    if player.hand:
        table = Table(title="Mao", box=box.SIMPLE)
        table.add_column("Carta")
        for c in player.hand:
            table.add_row(card_display(c))
        console.print(table)
    else:
        console.print("[dim]Mao vazia.[/dim]")

    if player.field_artifacts:
        table = Table(title="Campo", box=box.SIMPLE)
        table.add_column("Carta")
        for a in player.field_artifacts:
            table.add_row(card_display(a.card_id))
        console.print(table)
    else:
        console.print("[dim]Campo vazio.[/dim]")

    if player.units:
        table = Table(title="Suas unidades", box=box.SIMPLE)
        table.add_column("ID")
        table.add_column("Tipo")
        table.add_column("Local")
        table.add_column("Vida", justify="right")
        table.add_column("Flags", justify="left")
        for u in player.units:
            if isinstance(u, Hero):
                kind = f"Heroi {heroes.hero_name(u.hero_id)}"
            else:
                kind = f"Tropa {u.archetype.value}"
            flags = []
            if u.double_damage: flags.append("2xdano")
            if u.resistance_stacks: flags.append(f"Resx{u.resistance_stacks}")
            if u.original_owner_id is not None: flags.append("Qc")
            if u.statuses.get("cannot_attack_on_turn") == state.turn: flags.append("sem ataque")
            if u.statuses.get("sono_until_turn", -1) > state.turn: flags.append("dormindo")
            if u.statuses.get("invisivel"): flags.append("invisivel")
            flags_str = ", ".join(flags) if flags else "-"
            table.add_row(u.id, kind, house_display(state, u.house),
                          f"{u.life}/{u.life_max}", flags_str)
        console.print(table)
    else:
        console.print("[dim]Sem unidades.[/dim]")
    console.print()


def _strip_markup(s: str) -> str:
    return re.sub(r"\\[/?[^\\]]*\\]", "", s)


def _pad(text: str, width: int) -> str:
    plain_len = len(_strip_markup(text))
    pad = max(0, width - plain_len)
    left = pad // 2
    right = pad - left
    return " " * left + text + " " * right


def _city_cell_lines(state, pid: int, width: int) -> list[str]:
    player = get_player(state, pid)
    city = player.city
    mark = " *" if state.curuna_id == pid else ""
    povo = player.people[:8]
    title = f"J{pid} {player.name[:8]}{mark}"
    sub = f"({povo})"
    vida = f"Vida {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"
    units = []
    for u in player.units:
        if u.house == f"city_{pid}":
            kind = "H" if isinstance(u, Hero) else "T"
            units.append(f"{kind}{u.life}")
    units_str = ", ".join(units) if units else "[dim]-[/dim]"
    return [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width),
            _pad(vida, width), _pad(units_str, width)]


def _center_cell_lines(state, width: int) -> list[str]:
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == CENTER:
                kind = "H" if isinstance(u, Hero) else "T"
                units.append(f"{p.name[:4]}-{kind}{u.life}")
    lines = [_pad("[bold]CENTRO[/bold]", width), _pad("", width)]
    if units:
        for u in units:
            lines.append(_pad(u, width))
    else:
        lines.append(_pad("[dim]-[/dim]", width))
    return lines


def _pad_to_height(lines: list[str], height: int, width: int) -> list[str]:
    while len(lines) < height:
        lines.append(" " * width)
    return lines[:height]


def show_map(state) -> None:
    w = 22
    j1 = _city_cell_lines(state, 1, w); j2 = _city_cell_lines(state, 2, w)
    j3 = _city_cell_lines(state, 3, w); j4 = _city_cell_lines(state, 4, w)
    center = _center_cell_lines(state, w)
    height = max(len(j1), len(j2), len(j3), len(j4), len(center), 3)
    j1 = _pad_to_height(j1, height, w); j2 = _pad_to_height(j2, height, w)
    j3 = _pad_to_height(j3, height, w); j4 = _pad_to_height(j4, height, w)
    center = _pad_to_height(center, height, w)
    empty = [" " * w for _ in range(height)]
    sep = " | "
    line_sep = "-" * (w * 3 + 6)
    for i in range(height):
        console.print(empty[i] + sep + j3[i] + sep + empty[i], highlight=False)
    console.print(line_sep, highlight=False)
    for i in range(height):
        console.print(j4[i] + sep + center[i] + sep + j2[i], highlight=False)
    console.print(line_sep, highlight=False)
    for i in range(height):
        console.print(empty[i] + sep + j1[i] + sep + empty[i], highlight=False)
    curuna = get_player(state, state.curuna_id)
    console.print()
    console.print(f"[bold yellow]* Curuna: {curuna.name}[/bold yellow]")
    console.print(f"[dim]Loja: {state.shop.size()} cartas[/dim]\\n")


def show_resumo(state) -> None:
    table = Table(title=f"Resumo - Turno {state.turn} ({state.phase.value})", box=box.ROUNDED)
    table.add_column("Jogador"); table.add_column("Povo")
    table.add_column("Vida", justify="right"); table.add_column("Ouro", justify="right")
    table.add_column("Magia", justify="right"); table.add_column("Mao", justify="right")
    table.add_column("Campo", justify="right"); table.add_column("Mon.", justify="center")
    for p in state.players:
        mark = " *" if state.curuna_id == p.id else ""
        alive = p.city.is_alive()
        table.add_row(
            f"{p.name}{mark}" if alive else f"[red]{p.name} (morto)[/red]",
            p.people or "-",
            f"{p.city.life}/{p.city.life_max}" if alive else "-",
            str(p.city.gold) if alive else "-",
            str(p.city.magic) if alive else "-",
            str(len(p.hand)), str(len(p.field_artifacts)),
            "sim" if p.city.has_monument else "-")
    console.print(table)


def show_loja(state) -> None:
    from collections import Counter
    counts = Counter(state.shop.deck)
    table = Table(title=f"Loja - {state.shop.size()} cartas", box=box.ROUNDED)
    table.add_column("Carta"); table.add_column("Qtd", justify="right")
    for cid in sorted(ARTIFACT_CATALOG.keys()):
        table.add_row(card_display(cid), str(counts.get(cid, 0)))
    console.print(table)


def show_active_artifacts(state) -> None:
    table = Table(title="Artefatos ativos", box=box.ROUNDED)
    table.add_column("Jogador"); table.add_column("Carta"); table.add_column("Detalhes")
    found = False
    for p in state.players:
        for a in p.field_artifacts:
            found = True
            extra = ", ".join(f"{k}={v}" for k, v in a.extra.items()) if a.extra else "-"
            table.add_row(p.name, card_display(a.card_id), extra)
    if not found:
        console.print("[dim]Nenhum artefato ativo.[/dim]")
    else:
        console.print(table)


def show_habilidades(state, pid: int) -> None:
    player = get_player(state, pid)
    console.print(Panel.fit(
        f"[bold]{player.name}[/bold] - Povo: [cyan]{player.people}[/cyan]",
        border_style="cyan"))
    console.print("[bold]Passiva do povo[/bold]")
    console.print(PASSIVA_DESC.get(player.people, "-"))
    sp = spells_mod.spell_for_people(player.people)
    console.print("\\n[bold]Feitico[/bold]")
    if sp is None:
        console.print("-")
    else:
        desc = FEITICO_DESC.get(sp.spell_id, sp.description)
        if peoples.valendar_is_alive(player) and sp.spell_id == "sonho_lucido":
            desc += " [Valendar ativa: Sonho Lúcido desativado, bônus por naipe ativo]"
        console.print(desc)
        if state.turn < player.spell_cooldown_until_turn:
            console.print(f"[yellow]Recarga: {player.spell_cooldown_until_turn - state.turn} turno(s)[/yellow]")

    console.print("\\n[bold]Herois do jogador[/bold]")
    has_any = False
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive():
            has_any = True
            hd = heroes.get_hero(u.hero_id)
            console.print(f"  [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_display(state, u.house)}")
            console.print(f"    {HERO_ABILITY_DESC.get(u.hero_id, hd.name)}")
    if not has_any:
        console.print("  [dim](nenhum heroi vivo)[/dim]")

    console.print("\\n[bold]Herois dos outros (em campo)[/bold]")
    has_other = False
    for other in state.players:
        if other.id == pid:
            continue
        for u in other.units:
            if isinstance(u, Hero) and u.is_alive():
                has_other = True
                hd = heroes.get_hero(u.hero_id)
                console.print(f"  {other.name}: [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_display(state, u.house)}")
    if not has_other:
        console.print("  [dim](nenhum)[/dim]")


def menu_player_actions(state, player) -> str:
    actions = get_actions_menu(state, player)
    table = Table(box=box.SIMPLE)
    table.add_column("Opcao", style="cyan"); table.add_column("Acao")
    for key, label in actions:
        table.add_row(key, label)
    console.print(table)
    return Prompt.ask("Acao", choices=[k for k, _ in actions], default="0")


def _ask_choice_for_artifact(state, pid: int, card_id: str) -> dict:
    player = get_player(state, pid)
    ctype = artifacts_effects.choice_type(card_id)
    if ctype == "own_unit":
        if not player.units:
            raise ActionError(f"{card_display(card_id)} precisa de alvo.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        return {"unit_id": player.units[pick_index("Alvo", labels)].id}
    if ctype == "any_unit":
        all_units, labels = [], []
        for other in state.players:
            if not other.city.is_alive():
                continue
            for u in other.units:
                all_units.append(u)
                labels.append(f"{u.id} de {other.name} ({u.life}/{u.life_max}, {house_display(state, u.house)})")
        if not all_units:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        return {"unit_id": all_units[pick_index("Alvo", labels)].id}
    if ctype == "any_player":
        others = [p for p in state.players if p.id != pid and p.city.is_alive()]
        if not others:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        labels = [f"{p.name} (J{p.id})" for p in others]
        return {"target_player_id": others[pick_index("Alvo", labels)].id}
    if ctype == "any_enemy_unit":
        all_units, labels = [], []
        for other in state.players:
            if other.id == pid or not other.city.is_alive():
                continue
            for u in other.units:
                all_units.append(u)
                labels.append(f"{u.id} de {other.name} ({u.life}/{u.life_max})")
        if not all_units:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        return {"unit_id": all_units[pick_index("Alvo", labels)].id}
    if ctype == "people_hero":
        herois = HEROES_BY_PEOPLE.get(player.people, [])
        disponiveis = []
        for h in herois:
            hid = heroes.resolve_hero_for_people(player.people, h)
            if hid == player.chosen_hero_id:
                continue
            if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == hid
                   for u in player.units):
                continue
            disponiveis.append(h)
        # 7 Anões não entram em J♥
        if player.chosen_hero_id == "seven_dwarves":
            disponiveis = []
        if not disponiveis:
            raise ActionError("Todos os outros herois usados.")
        return {"hero_id": disponiveis[pick_index("Heroi", disponiveis)]}
    if ctype == "house":
        options = [h for h in CITY_HOUSES
                   if get_player(state, int(h.split("_")[1])).city.is_alive()]
        options.append(CENTER)
        labels = [house_display(state, h) for h in options]
        return {"house": options[pick_index("Casa", labels)]}
    return {}


def _resolve_pending_choice_if_any(state, pid: int) -> None:
    player = get_player(state, pid)
    pending = player.pending_artifact_choice
    if not pending:
        return
    if pending["kind"] == "J_D":
        console.print(f"[yellow]{player.name}: Jd Tabareu - escolha 2 de 3.[/yellow]")
        cards = list(pending["cards"])
        table = Table(box=box.SIMPLE)
        table.add_column("#", justify="right"); table.add_column("Carta")
        for i, c in enumerate(cards, 1):
            table.add_row(str(i), card_display(c))
        console.print(table)
        kept: list[str] = []
        while len(kept) < pending["pick"]:
            n = IntPrompt.ask(f"Escolha {len(kept)+1}a", default=1)
            if 1 <= n <= len(cards):
                c = cards[n - 1]
                if c not in kept:
                    kept.append(c)
        resolve_pending_artifact_choice(state, pid, kept_cards=kept)
        return
    if pending["kind"] == "Q_D":
        amount = pending["dead_unit_max_life"]
        console.print(f"[yellow]{player.name}: Qd - alvo morreu. Recompensa ({amount}):[/yellow]")
        idx = pick_index("Recurso", ["Ouro", "Magia"])
        resolve_pending_artifact_choice(state, pid, resource="gold" if idx == 0 else "magic")
        return


def _pick_target_for_day_attack(state, attacker, player):
    targets = []
    for other in state.players:
        if other.id == player.id or not other.city.is_alive():
            continue
        for u in other.units:
            if u.house == attacker.house and u.is_alive():
                targets.append(u)
    if not targets:
        raise ActionError("Sem alvos no local.")
    labels = [f"{u.id} de {get_player(state, u.owner_id).name} ({u.life}/{u.life_max})" for u in targets]
    return targets[pick_index("Alvo do ataque diurno", labels)]


def _handle_pena(state, pid: int, card_id: str) -> None:
    """Decide o que fazer com uma Pena recém-comprada/transmutada."""
    player = get_player(state, pid)
    console.print("[yellow]Você recebeu uma Pena do Manto Sagrado.[/yellow]")
    if player.people == "humanos":
        use_or_give_pena(state, pid, card_id, give_to_iuna=False)
        return
    # Não-humano: opção de dar à Iúna (se viva) ou ficar
    iuna_alive = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "iuna"
        for p in state.players for u in p.units
    )
    opts = ["Ficar com a Pena (vendável por 7 Ouro)"]
    if iuna_alive:
        opts.append("Dar à Iúna e ganhar outro artefato")
    idx = pick_index("Pena:", opts)
    use_or_give_pena(state, pid, card_id, give_to_iuna=(idx == 1))


def handle_action(state, pid: int, choice: str) -> str | None:
    player = get_player(state, pid)
    if choice == "1":
        gold = IntPrompt.ask(f"Ouro (0 a {RESOURCES_PER_DAY})", default=RESOURCES_PER_DAY)
        if gold < 0 or gold > RESOURCES_PER_DAY:
            raise ActionError("Fora do intervalo.")
        collect_resources(state, pid, gold, RESOURCES_PER_DAY - gold)
        console.print("[green]Coleta ok.[/green]")
    elif choice == "2":
        raise_city_life(state, pid, IntPrompt.ask("Vezes", default=1))
        console.print("[green]Vida ok.[/green]")
    elif choice == "3":
        if peoples.has_7_dwarves_chosen(player):
            raise ActionError("Sem Tropas (7 Anões).")
        archetypes = peoples.available_archetypes(player)
        labels = [f"{a.value} (max {TROOP_MAX_LIFE[a.value]})" for a in archetypes]
        archetype = archetypes[pick_index("Arquetipo", labels)]
        max_life = TROOP_MAX_LIFE[archetype.value]
        life = IntPrompt.ask(f"Vida (1 a {max_life})", default=max_life)
        summon_troop(state, pid, archetype, life)
        console.print("[green]Tropa ok.[/green]")
    elif choice == "4":
        summon_hero(state, pid)
        console.print("[green]Heroi ok.[/green]")
    elif choice == "5":
        units = [u for u in player.units if u.moves_this_turn < u.max_moves_this_turn]
        if not units:
            raise ActionError("Sem unidades.")
        idx = pick_index("Unidade", [f"{u.id} ({house_display(state, u.house)}, {u.life})" for u in units])
        unit = units[idx]
        dests = valid_destinations(state, unit)
        if not dests:
            raise ActionError("Sem destinos.")
        idx2 = pick_index("Destino", [house_display(state, d) for d in dests])
        move_unit(state, pid, unit.id, dests[idx2])
        console.print("[green]Movimento ok.[/green]")
    elif choice == "6":
        build_monument(state, pid)
        console.print("[green]Monumento ok.[/green]")
    elif choice == "7":
        card = buy_artifact_with_gold(state, pid)
        console.print(f"[green]Comprou: {card_display(card)}[/green]")
        if card == "PENA":
            _handle_pena(state, pid, card)
    elif choice == "8":
        card = transmute_artifact_with_magic(state, pid)
        console.print(f"[green]Transmutou: {card_display(card)}[/green]")
        if card == "PENA":
            _handle_pena(state, pid, card)
    elif choice == "9":
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = [card_display(c) for c in player.hand]
        card = player.hand[pick_index("Vender", labels)]
        sell_artifact(state, pid, card)
        console.print(f"[green]Vendeu: {card_display(card)}[/green]")
    elif choice == "10":
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = [card_display(c) for c in player.hand]
        card = player.hand[pick_index("Jogar", labels)]
        # Se for Pena, rota especial
        if card == "PENA":
            _handle_pena(state, pid, card)
            return None
        choice_data = _ask_choice_for_artifact(state, pid, card)
        play_artifact(state, pid, card, choice=choice_data)
        console.print(f"[green]Jogou: {card_display(card)}[/green]")
    elif choice == "11":
        show_resumo(state)
    elif choice == "12":
        show_map(state)
    elif choice == "13":
        show_loja(state)
    elif choice == "14":
        show_active_artifacts(state)
    elif choice == "g":
        show_habilidades(state, pid)
    elif choice == "d":
        miyamoto = next((u for u in player.units
                         if isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto"), None)
        if miyamoto is None:
            raise ActionError("Miyamoto nao esta vivo.")
        atks_restantes = peoples.miyamoto_attacks_remaining(state, player)
        if atks_restantes <= 0:
            raise ActionError("Miyamoto ja atacou o maximo.")
        target = _pick_target_for_day_attack(state, miyamoto, player)
        resolve_attack_day(state, Attack(miyamoto.id, "unit", target.id))
        console.print("[green]Ataque diurno executado.[/green]")
    elif choice == "e":
        arken_espolia(state, pid)
        console.print("[green]Arken espoliou.[/green]")
    elif choice == "f":
        sp = spells_mod.spell_for_people(player.people)
        if sp is None:
            raise ActionError("Sem feitico.")
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            raise ActionError("Valendar substitui Sonho Lúcido.")
        choice_data: dict = {}
        if sp.spell_id == "resistencia":
            if not player.units:
                raise ActionError("Sem unidades.")
            labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
            choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
        elif sp.spell_id == "armadura_de_ouro":
            choice_data["cap"] = _ask_int("Cap por hit", default=2, min_val=1, max_val=10)
        cast_spell(state, pid, choice_data)
        console.print(f"[green]{sp.name} lancado.[/green]")
    elif choice == "h":
        if not player.units:
            raise ActionError("Sem unidades.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        idx = pick_index("Alvo", labels)
        use_heal(state, pid, player.units[idx].id)
        console.print("[green]Cura ok.[/green]")
    elif choice == "u":
        return "undo"
    elif choice == "m":
        return "mola"
    elif choice == "r":
        return "restart"
    return None


def run_player_day(state, pid: int) -> str | None:
    player = get_player(state, pid)
    try:
        _resolve_pending_choice_if_any(state, pid)
    except (ActionError, ValueError) as e:
        console.print(f"[red]Erro pendente: {e}[/red]")
    while True:
        show_state_for_player(state, pid)
        choice = menu_player_actions(state, player)
        if choice == "0":
            player.has_played_day_this_turn = True
            return None
        try:
            result = handle_action(state, pid, choice)
            if result is not None:
                return result
        except (ActionError, CombatError, ValueError) as e:
            console.print(f"[red]Erro: {e}[/red]")
        console.print()


def find_targets(state, unit):
    targets = []
    house = unit.house
    can_attack_city = (not isinstance(unit, Hero)) or unit.hero_can_attack_city
    if isinstance(unit, Hero) and not can_attack_city:
        # Din na mesma casa permite anões atacar cidade
        owner = get_player(state, unit.owner_id)
        for u in owner.units:
            if (isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "din" and u.house == house):
                can_attack_city = True
                break
    if can_attack_city and house.startswith("city_"):
        target_pid = int(house.split("_")[1])
        if target_pid != unit.owner_id:
            target = get_player(state, target_pid)
            if target.city.is_alive():
                targets.append(("city", str(target_pid),
                                f"Cidade de {target.name} ({target.city.life})"))
    for other in state.players:
        if other.id == unit.owner_id:
            continue
        for u in other.units:
            if u.house == house and u.is_alive():
                kind = "Heroi" if isinstance(u, Hero) else "Tropa"
                targets.append(("unit", u.id,
                                f"{kind} {u.id} de {other.name} ({u.life})"))
    return targets


def prompt_attack(state, unit, targets) -> Attack | None:
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_display(state, unit.house)}")
    options = ["Nao atacar"] + [t[2] for t in targets]
    idx = pick_index("Acao", options)
    if idx == 0:
        return None
    return Attack(unit.id, targets[idx - 1][0], targets[idx - 1][1])


def _try_ainai_teleport(state, player) -> bool:
    ainai = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "ainai"), None)
    if ainai is None:
        return False
    if ainai.statuses.get("ainai_used_this_night") == state.turn:
        return False
    if not state.deaths_this_night:
        return False
    casas = [h for h in state.deaths_this_night if h != ainai.house]
    if not casas:
        return False
    console.print("[yellow]Ainai pode teletransportar para uma casa com morte nesta Noite.[/yellow]")
    labels = [house_display(state, h) for h in casas]
    idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)
    if idx == 0:
        return False
    destino = casas[idx - 1]
    ainai.house = destino
    ainai.statuses["ainai_used_this_night"] = state.turn
    player.city.magic += 1
    console.print(f"[green]Ainai teleportou para {house_display(state, destino)} (+1 Magia).[/green]")
    return True


def _try_besouro_mandinga(state, player) -> bool:
    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"), None)
    if besouro is None:
        return False
    if player.besouro_mandinga_used_turn == state.turn:
        return False
    if not player.hand:
        return False
    console.print(f"[yellow]{player.name}: Besouro pode usar Mandinga (1 artefato da mão).[/yellow]")
    opts = ["Nao usar"] + [card_display(c) for c in player.hand]
    idx = pick_index("Mandinga:", opts)
    if idx == 0:
        return False
    card = player.hand[idx - 1]
    choice_data = _ask_choice_for_artifact(state, player.id, card)
    besouro_mandinga(state, player.id, card, choice=choice_data)
    console.print(f"[green]Mandinga: {card_display(card)} jogado.[/green]")
    return True


def _ask_vovo_position(state) -> None:
    for p in state.players:
        vovo = next((u for u in p.units
                     if isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba"), None)
        if vovo is None:
            continue
        console.print(f"[yellow]{p.name}: Vovo - escolha posicao no local ({house_display(state, vovo.house)}).[/yellow]")
        pos = _ask_int("Posicao (1=primeiro, 4=ultimo)", default=1, min_val=1, max_val=4)
        p.vovo_position = pos


def _order_players_for_house(state, pids_here: list[int], house: str) -> list[int]:
    # Valendar ♠: se algum jogador ativou, ele vem primeiro
    for pid in pids_here:
        p = get_player(state, pid)
        if p.bater_primeiro_turn == state.turn:
            others = [x for x in pids_here if x != pid]
            return [pid] + others
    # Vovó
    vovo_owner = None
    for pid in pids_here:
        p = get_player(state, pid)
        for u in p.units:
            if (isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "vovo_gamba" and u.house == house):
                vovo_owner = pid
                break
        if vovo_owner is not None:
            break
    if vovo_owner is None:
        return pids_here
    pos = max(1, min(get_player(state, vovo_owner).vovo_position, len(pids_here)))
    ordered = [pid for pid in pids_here if pid != vovo_owner]
    ordered.insert(pos - 1, vovo_owner)
    return ordered


def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_map(state)
    _ask_vovo_position(state)
    all_pids = list(day_order(state))
    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
            _try_ainai_teleport(state, player)
            _try_besouro_mandinga(state, player)
    house_order = [CENTER, "city_4", "city_3", "city_2", "city_1"]
    for house in house_order:
        pids_here = []
        for pid in all_pids:
            player = get_player(state, pid)
            if any(u.house == house and u.is_alive() for u in player.units):
                pids_here.append(pid)
        if not pids_here:
            continue
        pids_here = _order_players_for_house(state, pids_here, house)
        for pid in pids_here:
            player = get_player(state, pid)
            units_here = [u for u in player.units if u.house == house and u.is_alive()]
            if not units_here:
                continue
            if not any(find_targets(state, u) for u in units_here):
                continue
            console.print(f"[bold]{player.name} declara ataques em {house_display(state, house)}.[/bold]")
            for unit in list(units_here):
                if not unit.is_alive():
                    continue
                while True:
                    targets = find_targets(state, unit)
                    if not targets:
                        break
                    if _attacks_used(unit) >= _effective_max_attacks(state, unit):
                        break
                    atk = prompt_attack(state, unit, targets)
                    if not atk:
                        break
                    before = len(state.event_log)
                    try:
                        resolve_attack(state, atk)
                    except CombatError as e:
                        console.print(f"  [red]Erro: {e}[/red]")
                        break
                    for line in state.event_log[before:]:
                        console.print(f"  {line}")
            console.print()


def show_victory(state) -> None:
    if state.winner_id:
        player = get_player(state, state.winner_id)
        console.print()
        console.print(Panel.fit(
            f"[bold green]VITORIA![/bold green]\\n\\n{player.name} ({player.people}) venceu!",
            border_style="green"))
    else:
        console.print(Panel.fit("[bold red]Empate![/bold red]", border_style="red"))


def _run_one_game() -> None:
    console.clear()
    state = setup_ui()
    while not state.game_over:
        interest = start_turn(state)
        console.rule(f"[bold yellow]TURNO {state.turn} - DIA[/bold yellow]")
        curuna = get_player(state, state.curuna_id)
        console.print(f"[bold yellow]* Curuna: {curuna.name}[/bold yellow]\\n")
        if interest:
            pros = ", ".join(f"{get_player(state, pid).name} (+{g})" for pid, g in interest)
            console.print(f"[yellow]Prosperidade:[/yellow] {pros}\\n")
        skipped = [p.name for p in state.players
                   if p.city.is_alive() and p.skip_day_turn == state.turn]
        if skipped:
            console.print(f"[yellow]Pulados: {', '.join(skipped)}[/yellow]\\n")
        show_map(state)
        console.print()
        day_players = day_order(state)
        snapshots: dict[int, dict] = {}
        i = 0
        while i < len(day_players):
            pid = day_players[i]
            player = get_player(state, pid)
            snapshots[pid] = state_to_dict(state)
            console.rule(f"[bold]Vez de {player.name}[/bold]")
            before = len(state.event_log)
            start_player_day(state, pid)
            for line in state.event_log[before:]:
                console.print(f"  [cyan]{line}[/cyan]")
            if player.skip_day_turn == state.turn:
                player.has_played_day_this_turn = True
                console.print(f"[yellow]{player.name} pulou.[/yellow]")
                i += 1
                continue
            result = run_player_day(state, pid)
            if result == "restart":
                raise RestartGame()
            if result == "undo":
                state = state_from_dict(snapshots[pid])
                console.print("[yellow]Colher de cha: refaz.[/yellow]")
                continue
            if result == "mola":
                if i > 0:
                    i -= 1
                prev = day_players[i]
                state = state_from_dict(snapshots[prev])
                console.print(f"[yellow]Mola: {get_player(state, prev).name} refaz.[/yellow]")
                continue
            i += 1
        end_day(state)
        night_skipped = [p.name for p in state.players
                         if p.city.is_alive() and p.skip_night_turn == state.turn]
        if night_skipped:
            console.print(f"[yellow]Pulados na Noite: {', '.join(night_skipped)}[/yellow]\\n")
        run_night_phase(state)
        if state.game_over:
            break
        end_turn(state)
        if not state.game_over:
            console.input("\\n[dim]Enter...[/dim] ")
            console.clear()
    show_victory(state)


def main() -> None:
    while True:
        try:
            _run_one_game()
        except RestartGame:
            console.print("[yellow]Reiniciando...[/yellow]\\n")
            continue
        except KeyboardInterrupt:
            console.print("\\n[yellow]Interrompido.[/yellow]")
            return
        try:
            again = Prompt.ask("Jogar outra?", choices=["s", "n"], default="n")
        except KeyboardInterrupt:
            return
        if again != "s":
            return
        console.print()


if __name__ == "__main__":
    main()
'''

# =============================================================
# tests/test_7_dwarves.py
# =============================================================
FILES["tests/test_7_dwarves.py"] = '''\
"""Testes: Os 7 Anões."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, summon_troop, ActionError, SEVEN_DWARVES_COST,
)
from jessica.core.constants import TroopArchetype
from jessica.core.models import Hero
from jessica.core import heroes


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


def test_dwarves_block_troops():
    state = make_state()
    p = state.players[1]
    p.city.gold = 20
    p.city.magic = 10
    try:
        summon_troop(state, 2, TroopArchetype.LIGHT, 4)
        raise AssertionError("Deveria bloquear tropas")
    except ActionError as e:
        print(f"OK  - 7 Anoes bloqueiam tropas: {e}")


def test_summon_first_dwarf():
    state = make_state()
    p = state.players[1]
    p.city.magic = 10
    h = summon_hero(state, 2)
    assert h.hero_id == "dain"
    assert h.life == 1
    print("OK  - 1o anao (dain) invocado")


def test_summon_chain_in_order():
    state = make_state()
    p = state.players[1]
    p.city.magic = 20
    for expected in ["dain", "buin", "bein", "boin", "tintin", "don", "din"]:
        h = summon_hero(state, 2)
        assert h.hero_id == expected, f"Esperado {expected}, veio {h.hero_id}"
    print("OK  - Corrente completa dos 7 anoes invocada em ordem")


def test_chain_requires_prev_alive():
    state = make_state()
    p = state.players[1]
    p.city.magic = 20
    summon_hero(state, 2)  # dain
    # Mata dain
    dain = next(u for u in p.units if isinstance(u, Hero) and u.hero_id == "dain")
    dain.life = 0
    p.units = [u for u in p.units if u.is_alive()]
    # Tenta invocar buin: deveria falhar
    try:
        summon_hero(state, 2)
        raise AssertionError("Deveria bloquear sem dain vivo")
    except ActionError as e:
        print(f"OK  - Corrente bloqueia sem anao anterior: {e}")


def test_cost_is_2_magic():
    state = make_state()
    p = state.players[1]
    p.city.magic = 5
    summon_hero(state, 2)  # anões são -0 (não é orc)
    assert p.city.magic == 3
    print("OK  - Cada anao custa 2 magia")


def run_all():
    tests = [
        test_dwarves_block_troops,
        test_summon_first_dwarf,
        test_summon_chain_in_order,
        test_chain_requires_prev_alive,
        test_cost_is_2_magic,
    ]
    print("=== Testes 7 Anoes ===\\n")
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
# tests/test_iuna.py
# =============================================================
FILES["tests/test_iuna.py"] = '''\
"""Testes: Iúna."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import summon_hero, summon_troop
from jessica.core.combat import resolve_attack, Attack
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero


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


def _make_troop(state, pid, archetype=TroopArchetype.LIGHT, life=4, house="center"):
    p = state.players[pid - 1]
    p.city.gold = max(p.city.gold, life + 5)
    p.city.magic = max(p.city.magic, 5)
    t = summon_troop(state, pid, archetype, life)
    t.house = house
    return t


def test_iuna_adds_penas_to_shop():
    state = make_state()
    p = state.players[0]
    p.city.magic = 10
    before = state.shop.copies_of("PENA")
    assert before == 0, f"Penas já existem antes? {before}"
    summon_hero(state, 1)
    after = state.shop.copies_of("PENA")
    assert after == 4, f"Esperado 4 Penas, veio {after}"
    print("OK  - Iuna adicionou 4 Penas a Loja")


def test_iuna_takes_exactly_1_damage():
    """Iúna recebe exatamente 1 de dano, mesmo contra ataque de 10."""
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    iuna = summon_hero(state, 1)
    iuna.house = CENTER
    enemy = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=10, house=CENTER)
    life_before = iuna.life
    resolve_attack(state, Attack(enemy.id, "unit", iuna.id))
    assert iuna.life == life_before - 1, f"Iuna deveria perder exatamente 1, caiu {life_before - iuna.life}"
    print(f"OK  - Iuna recebe exatamente 1 de dano (vida {iuna.life})")


def test_iuna_takes_1_from_small_attacker_too():
    """Mesmo atacante pequeno: ela recebe 1."""
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    iuna = summon_hero(state, 1)
    iuna.house = CENTER
    enemy = _make_troop(state, 2, archetype=TroopArchetype.LIGHT, life=2, house=CENTER)
    life_before = iuna.life
    resolve_attack(state, Attack(enemy.id, "unit", iuna.id))
    assert iuna.life == life_before - 1, f"Esperado -1, caiu {life_before - iuna.life}"
    print(f"OK  - Iuna recebe 1 de dano de atacante pequeno")


def test_iuna_deals_1_to_4_damage():
    """Iúna dá 1D4 de dano ao atacar (não usa vida atual)."""
    state = make_state()
    state.phase = Phase.NIGHT
    p1 = state.players[0]
    p1.city.magic = 10
    iuna = summon_hero(state, 1)
    iuna.house = CENTER
    target = _make_troop(state, 2, archetype=TroopArchetype.HEAVY, life=10, house=CENTER)
    life_before = target.life
    resolve_attack(state, Attack(iuna.id, "unit", target.id))
    dmg = life_before - target.life
    assert 1 <= dmg <= 4, f"Dano fora do range 1-4: {dmg}"
    print(f"OK  - Iuna deu {dmg} de dano (1-4)")


def run_all():
    tests = [
        test_iuna_adds_penas_to_shop,
        test_iuna_takes_exactly_1_damage,
        test_iuna_takes_1_from_small_attacker_too,
        test_iuna_deals_1_to_4_damage,
    ]
    print("=== Testes Iuna ===\\n")
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
# tests/test_sonho_lucido.py
# =============================================================
FILES["tests/test_sonho_lucido.py"] = '''\
"""Testes: Sonho Lucido."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from jessica.core.setup import run_setup
from jessica.core.actions import cast_spell, play_artifact
from jessica.core import peoples


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


def test_flip_card():
    assert peoples.sonho_lucido_flip("K_H") == "K_D"
    assert peoples.sonho_lucido_flip("K_D") == "K_H"
    assert peoples.sonho_lucido_flip("K_S") == "K_C"
    assert peoples.sonho_lucido_flip("K_C") == "K_S"
    print("OK  - sonho_lucido_flip funciona H<->D e S<->C")


def test_flip_pena_unchanged():
    assert peoples.sonho_lucido_flip("PENA") == "PENA"
    print("OK  - Pena nao muda de naipe")


def test_sonho_lucido_flips_played_artifact():
    state = make_state()
    p = state.players[3]  # Fadas
    p.city.magic = 10
    cast_spell(state, 4)
    assert p.sonho_lucido_pending_turn == state.turn
    # Coloca um K_H na mão e joga
    p.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    # Deve ter virado K_D no campo
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_D" in field_ids, f"K_H deveria ter virado K_D, campo: {field_ids}"
    print("OK  - Sonho Lucido trocou K_H para K_D ao jogar")


def test_sonho_lucido_only_that_turn():
    state = make_state()
    p = state.players[3]
    p.city.magic = 10
    cast_spell(state, 4)
    # "Avança" turno manualmente
    state.turn += 1
    p.hand.append("K_H")
    play_artifact(state, 4, "K_H")
    field_ids = [a.card_id for a in p.field_artifacts]
    assert "K_H" in field_ids, f"K_H nao deveria ter virado em outro turno, campo: {field_ids}"
    print("OK  - Sonho Lucido so vale naquele turno")


def run_all():
    tests = [
        test_flip_card,
        test_flip_pena_unchanged,
        test_sonho_lucido_flips_played_artifact,
        test_sonho_lucido_only_that_turn,
    ]
    print("=== Testes Sonho Lucido ===\\n")
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
# Execução
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
    print("  python tests/test_7_dwarves.py")
    print("  python tests/test_iuna.py")
    print("  python tests/test_sonho_lucido.py")
    print("  python tests/test_peoples_f4a.py")
    print("  python tests/test_artifact_effects_f3c.py")
    print("  python tests/test_artifact_effects_f3d.py")
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()