"""Escolhas concretas para feitiços sem seleção composta de cartas."""
from itertools import combinations

from . import heroes, peoples, spells
from .artifacts import card_display
from .models import Hero


def effective_spell(player):
    spell = spells.spell_for_people(player.people)
    if spell and spell.spell_id == "imitacao_gnomerica":
        return spells.SPELL_CATALOG.get(player.spell_copia_id)
    return spell


def choices(state, player):
    spell = effective_spell(player)
    if spell is None:
        return
    sid = spell.spell_id
    living = [u for u in player.units if u.is_alive()]
    if sid in ("resistencia", "transformar_morcego", "licantropo"):
        for unit in living:
            name = heroes.hero_name(unit.hero_id) if isinstance(unit, Hero) else unit.id
            yield {"unit_id": unit.id}, name
    elif sid in ("armadura_de_ouro", "espoliar"):
        yield {}, ""
    elif sid == "linhagem_ancestral":
        for hid in dict.fromkeys(u.hero_id for u in living if isinstance(u, Hero)):
            yield {"hero_id": hid}, heroes.hero_name(hid)
    elif sid == "levantar_mortos":
        available = [a.value for a in peoples.available_archetypes(player, state)]
        for pair in combinations(available, 2):
            yield {"archetypes": list(pair)}, " + ".join(pair)
    elif sid == "decompor":
        yield {"kind": "city"}, "Muralha: −1 vida, +3 Magia"
        for unit in living:
            yield {"kind": "hero" if isinstance(unit, Hero) else "troop", "unit_id": unit.id}, unit.id
    elif sid == "ressonancia_magica":
        for card in dict.fromkeys(player.hand):
            yield {"action": "add", "card_id": card}, f"Incorporar {card_display(card)}"
        for old in player.canastra:
            yield {"action": "remove", "card_id": old}, f"Retirar {card_display(old)}"
            for new in dict.fromkeys(player.hand):
                if old.rsplit("_", 1)[-1] == new.rsplit("_", 1)[-1]:
                    yield {"action": "swap", "old_card_id": old, "new_card_id": new}, (
                        f"Trocar {card_display(old)} por {card_display(new)}")
