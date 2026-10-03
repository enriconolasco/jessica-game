"""Condições iniciais explícitas; compartilhadas entre os três clientes."""
from .state import get_player, log

FIELDS = {"city_life", "city_life_max", "gold", "magic", "artifacts"}


def validate_initial(value):
    if not isinstance(value, dict) or set(value) - FIELDS:
        raise ValueError("Configuração individual inválida.")
    result = {}
    for key, number in value.items():
        minimum, maximum = (1, 100) if key.startswith("city_life") else (0, 24) if key == "artifacts" else (0, 999)
        if type(number) is not int or not minimum <= number <= maximum:
            raise ValueError(f"Valor inicial inválido: {key} ({minimum}–{maximum}).")
        result[key] = number
    if result.get("city_life", 1) > result.get("city_life_max", 100):
        raise ValueError("Vida inicial maior que a máxima.")
    return result


def apply_initial_conditions(state, configs):
    if not isinstance(configs, dict) or set(configs) - {p.id for p in state.players}:
        raise ValueError("Jogador inválido nas condições iniciais.")
    checked = {pid: validate_initial(values) for pid, values in configs.items()}
    if sum(values.get("artifacts", 0) for values in checked.values()) > state.shop.size():
        raise ValueError("Artefatos iniciais excedem as cartas disponíveis na loja.")
    for pid, values in checked.items():
        p = get_player(state, pid)
        life = values.get("city_life", p.city.life)
        maximum = values.get("city_life_max", max(p.city.life_max, life))
        if life > maximum:
            raise ValueError("Vida inicial maior que a máxima da base.")
    for p in state.players:
        values = checked.get(p.id, {})
        p.city.life = values.get("city_life", p.city.life)
        p.city.life_max = values.get("city_life_max", max(p.city.life_max, p.city.life))
        p.city.gold = values.get("gold", p.city.gold)
        p.city.magic = values.get("magic", p.city.magic)
        for unit in p.units:
            if unit.statuses.get("dragon_base"):
                unit.life, unit.life_max = p.city.life, p.city.life_max
        for _ in range(values.get("artifacts", 0)):
            p.hand.append(state.shop.draw_random(state.rng))
        if values:
            log(state, f"{p.name}: condições iniciais — Base {p.city.life}/{p.city.life_max}, "
                       f"{p.city.gold} Ouro, {p.city.magic} Magia, {len(p.hand)} artefato(s) na mão.")
