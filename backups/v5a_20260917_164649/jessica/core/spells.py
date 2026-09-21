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
