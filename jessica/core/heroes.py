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
    "lupa_lider": HeroDefinition("lupa_lider", "lobisomens", "Lupa, Lider da Matilha", 6,  # v5v10 #23
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
