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
