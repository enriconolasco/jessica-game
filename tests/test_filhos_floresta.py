"""Testes: Filhos da Floresta."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, summon_troop, cast_spell, baoba_pagar_magia, ActionError,
)
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero, Troop
from jessica.core.combat import _cleanup_dead
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["filhos_floresta", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "filhos_floresta": ["Guarari", "Aiquara", "Baoba-bá"],
            "humanos": ["miyamoto"], "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "filhos_floresta", "heroi": "Guarari"},
            2: {"povo": "humanos", "heroi": "miyamoto"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_filhos_comeca_com_1_vida():
    state = make_state()
    p1 = state.players[0]
    assert p1.city.life == 1, f"Filhos deveria comecar com 1, veio {p1.city.life}"
    print(f"OK  - Filhos: cidade comeca com {p1.city.life} de vida")


def test_bonus_turno_13():
    state = make_state()
    p1 = state.players[0]
    state.turn = 13
    peoples.apply_filhos_bonus(state)
    assert p1.city.life == 3, f"Esperado vida 3, veio {p1.city.life}"
    assert p1.city.gold == 2
    assert p1.city.magic == 2
    assert p1.filhos_bonus_recebido is True
    peoples.apply_filhos_bonus(state)
    assert p1.city.life == 3
    print("OK  - Bonus turno 13: +2 Vida, +2 Ouro, +2 Magia (uma vez)")


def test_bonus_turno_13_respeita_cap():
    state = make_state()
    p1 = state.players[0]
    p1.city.life = p1.city.life_max
    state.turn = 13
    peoples.apply_filhos_bonus(state)
    assert p1.city.life == p1.city.life_max
    print("OK  - Bonus turno 13 respeita vida maxima")


def test_decompor_heroi():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 5
    guarari = summon_hero(state, 1)
    assert guarari.is_alive()
    magia_antes = p1.city.magic
    cast_spell(state, 1, choice={"kind": "hero", "unit_id": guarari.id})
    assert guarari not in p1.units
    assert p1.city.magic == magia_antes + 4, (
        f"Esperado +4, veio {p1.city.magic - magia_antes}"
    )
    print("OK  - Decompor heroi: +4 Magia")


def test_decompor_tropa():
    state = make_state()
    p1 = state.players[0]
    p1.city.gold = 20
    p1.city.magic = 1
    t = summon_troop(state, 1, TroopArchetype.HEAVY, 8)
    magia_antes = p1.city.magic
    cast_spell(state, 1, choice={"kind": "troop", "unit_id": t.id})
    assert p1.city.magic == magia_antes + 10, (
        f"Tropa 8/8 deveria dar +10, veio {p1.city.magic - magia_antes}"
    )
    print("OK  - Decompor tropa 8/8: +10 Magia (vida + 2)")


def test_decompor_muralha():
    state = make_state()
    p1 = state.players[0]
    p1.city.life = 4
    p1.city.magic = 0
    cast_spell(state, 1, choice={"kind": "city"})
    assert p1.city.life == 3, f"Esperado vida 3, veio {p1.city.life}"
    assert p1.city.magic == 3, f"Esperado magia 3, veio {p1.city.magic}"
    print("OK  - Decompor muralha: -1 Vida, +3 Magia")


def test_baoba_pagamentos_invocam():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 5
    baoba_pagar_magia(state, 1)
    assert p1.baoba_pagamentos == 1
    baoba_pagar_magia(state, 1)
    assert p1.baoba_pagamentos == 2
    baoba_pagar_magia(state, 1)
    assert p1.baoba_pagamentos == 0
    assert p1.baoba_invocado is True
    assert any(isinstance(u, Hero) and u.hero_id == "baoba_ba" for u in p1.units)
    print("OK  - Baoba-ba: 3 pagamentos invocam")


def test_baoba_bloqueia_pagar_se_vivo():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 5
    for _ in range(3):
        baoba_pagar_magia(state, 1)
    try:
        baoba_pagar_magia(state, 1)
        raise AssertionError("Deveria bloquear pagamento com Baoba vivo")
    except ActionError as e:
        print(f"OK  - Nao pode pagar com Baoba vivo: {e}")


def test_baoba_invocado_na_cidade():
    state = make_state()
    p1 = state.players[0]
    p1.city.magic = 5
    for _ in range(3):
        baoba_pagar_magia(state, 1)
    baoba = next(u for u in p1.units
                 if isinstance(u, Hero) and u.hero_id == "baoba_ba")
    assert baoba.house == "city_1", f"Esperado city_1, veio {baoba.house}"
    print(f"OK  - Baoba-ba invocado em {baoba.house}")


def test_baoba_morte_zera_pagamentos():
    state = make_state()
    p1 = state.players[0]
    p1.baoba_pagamentos = 2
    p1.baoba_invocado = True
    b = Hero(id="p1_baoba_teste", owner_id=1, house="center",
             life=0, life_max=10, hero_id="baoba_ba",
             killed_by_player_id=2)
    p1.units.append(b)
    _cleanup_dead(state)
    assert p1.baoba_pagamentos == 0
    assert p1.baoba_invocado is False
    print("OK  - Morte do Baoba-ba zera pagamentos")


def run_all():
    tests = [
        test_filhos_comeca_com_1_vida,
        test_bonus_turno_13,
        test_bonus_turno_13_respeita_cap,
        test_decompor_heroi,
        test_decompor_tropa,
        test_decompor_muralha,
        test_baoba_pagamentos_invocam,
        test_baoba_bloqueia_pagar_se_vivo,
        test_baoba_invocado_na_cidade,
        test_baoba_morte_zera_pagamentos,
    ]
    print("=== Testes Filhos da Floresta ===\n")
    p, f = 0, 0
    for t in tests:
        try:
            t()
            p += 1
        except Exception as e:
            f += 1
            print(f"FALHOU - {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n=== {p} passaram, {f} falharam ===")


if __name__ == "__main__":
    run_all()
