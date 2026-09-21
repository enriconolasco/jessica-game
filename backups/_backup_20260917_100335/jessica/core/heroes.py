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
}


def heroes_for_people(people: str) -> list[HeroDefinition]:
    return [h for h in HERO_CATALOG.values() if h.people == people]


def resolve_hero_for_people(people: str, raw: str) -> str:
    """
    Normaliza qualquer string (nome completo, apelido, letra) para o hero_id
    canônico do povo. Se não achar, devolve raw (vai falhar com erro claro depois).
    """
    candidates = heroes_for_people(people)

    # 1) hero_id canônico direto
    for h in candidates:
        if h.hero_id == raw:
            return h.hero_id

    # 2) nome exato
    for h in candidates:
        if h.name == raw:
            return h.hero_id

    # 3) LEGACY_NAMES (contextualizado ao povo)
    legacy = LEGACY_NAMES.get(raw)
    if legacy is not None:
        for h in candidates:
            if h.hero_id == legacy:
                return legacy

    # 4) prefixo case-insensitive
    raw_lower = raw.lower()
    matches = [h for h in candidates if h.name.lower().startswith(raw_lower)]
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
    # prefixo
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