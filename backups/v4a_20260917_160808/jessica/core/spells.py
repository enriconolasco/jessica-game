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
        "resistencia", "humanos", "Resistência",
        "Dê Resistência a um aliado nesta Noite.",
    ),
    "armadura_de_ouro": SpellDefinition(
        "armadura_de_ouro", "anoes", "Armadura de Ouro",
        "Pague X Ouro para anular até X dano por hit.",
    ),
    "espoliar": SpellDefinition(
        "espoliar", "orcs", "Espoliar",
        "+2 Ouro por Cidade inimiga ocupada.",
    ),
    "sonho_lucido": SpellDefinition(
        "sonho_lucido", "fadas", "Sonho Lúcido",
        "Troca o naipe do próximo artefato usado (♥↔♦, ♠↔♣).",
        implemented=True,
    ),
}


def get_spell(spell_id: str) -> SpellDefinition:
    if spell_id not in SPELL_CATALOG:
        raise KeyError(f"Feitiço desconhecido: {spell_id}")
    return SPELL_CATALOG[spell_id]


def spell_for_people(people: str) -> SpellDefinition | None:
    for s in SPELL_CATALOG.values():
        if s.people == people:
            return s
    return None
