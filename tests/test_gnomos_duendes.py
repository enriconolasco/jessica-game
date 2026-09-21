"""Testes: Gnomos e Duendes."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()

from jessica.core.setup import run_setup
from jessica.core.actions import (
    summon_hero, summon_troop, play_artifact, raise_city_life, ActionError,
    gnomo_alocar_aposta, bimbo_invisibilidade, bimbo_gastar_5,
    zebum_invocar_heroi,
)
from jessica.core.combat import resolve_attack, Attack
from jessica.core.constants import TroopArchetype, Phase, CENTER
from jessica.core.models import Hero, Troop
from jessica.core import peoples


def make_state():
    state, _ = run_setup(
        all_peoples=["gnomos_duendes", "humanos", "orcs", "fadas"],
        heroes_by_people={
            "gnomos_duendes": ["Bimbo do Mal", "São Tomé", "Zebum"],
            "humanos": ["miyamoto"], "orcs": ["arken"], "fadas": ["ainai"]},
        choices={
            1: {"povo": "gnomos_duendes", "heroi": "Zebum"},
            2: {"povo": "humanos", "heroi": "miyamoto"},
            3: {"povo": "orcs", "heroi": "arken"},
            4: {"povo": "fadas", "heroi": "ainai"}},
        seed=20260916,
    )
    return state


def test_alocar_aposta():
    state = make_state()
    p1 = state.players[0]
    gnomo_alocar_aposta(state, 1, "H", 2)
    gnomo_alocar_aposta(state, 1, "S", 3)
    assert p1.bet_H_target == 2
    assert p1.bet_S_target == 3
    print("OK  - Apostas alocadas H->J2, S->J3")


def test_aposta_nao_pode_ser_em_si():
    state = make_state()
    try:
        gnomo_alocar_aposta(state, 1, "H", 1)
        raise AssertionError("Deveria bloquear")
    except ActionError as e:
        print(f"OK  - Aposta em si bloqueada: {e}")


def test_aposta_cumprida_em_raise_city_life():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p2.city.gold = 10
    gnomo_alocar_aposta(state, 1, "H", 2)
    raise_city_life(state, 2)
    assert p1.correct_bets == 1
    assert p1.bet_H_target is None
    print("OK  - Aposta H cumprida em raise_city_life")


def test_aposta_cumprida_em_summon_troop():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p2.city.gold = 20
    p2.city.magic = 5
    gnomo_alocar_aposta(state, 1, "S", 2)
    summon_troop(state, 2, TroopArchetype.LIGHT, 4)
    assert p1.correct_bets == 1
    assert p1.bet_S_target is None
    print("OK  - Aposta S cumprida em summon_troop")


def test_aposta_cumprida_em_play_artifact():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    gnomo_alocar_aposta(state, 1, "C", 2)
    p2.hand.append("K_H")
    play_artifact(state, 2, "K_H")
    assert p1.correct_bets == 1
    print("OK  - Aposta C cumprida em play_artifact")


def test_aposta_cumprida_em_kill():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p3 = state.players[2]
    p2.city.gold = 20
    p2.city.magic = 10
    p3.city.gold = 20
    p3.city.magic = 10
    atk = summon_troop(state, 2, TroopArchetype.HEAVY, 8)
    atk.house = CENTER
    vit = summon_troop(state, 3, TroopArchetype.LIGHT, 4)
    vit.house = CENTER
    gnomo_alocar_aposta(state, 1, "S", 2)
    state.phase = Phase.NIGHT
    resolve_attack(state, Attack(atk.id, "unit", vit.id))
    assert p1.correct_bets == 1
    print("OK  - Aposta S cumprida em kill")


def test_aposta_acumula_entre_turnos():
    state = make_state()
    p1 = state.players[0]
    p2 = state.players[1]
    p2.city.gold = 20
    gnomo_alocar_aposta(state, 1, "H", 2)
    raise_city_life(state, 2)
    assert p1.correct_bets == 1
    peoples.reset_gnomos_bets(state)
    assert p1.correct_bets == 1, "Apostas corretas nao devem zerar"
    assert p1.bets_need_realocacao is True
    print("OK  - Apostas corretas acumulam entre turnos")


def test_bimbo_invisibilidade():
    state = make_state()
    p1 = state.players[0]
    p1.correct_bets = 3
    p1.city.magic = 10
    p1.chosen_hero_id = "bimbo_do_mal"
    bimbo = summon_hero(state, 1, force_hero_id="bimbo_do_mal")
    bimbo_invisibilidade(state, 1)
    assert p1.correct_bets == 2
    assert bimbo.statuses.get("invisivel_until_turn") == state.turn
    print("OK  - Bimbo invisivel (custo 1 aposta)")


def test_bimbo_gastar_5():
    state = make_state()
    p1 = state.players[0]
    p1.correct_bets = 6
    p1.city.magic = 10
    p1.chosen_hero_id = "bimbo_do_mal"
    summon_hero(state, 1, force_hero_id="bimbo_do_mal")
    hand_antes = len(p1.hand)
    bimbo_gastar_5(state, 1)
    assert p1.correct_bets == 1
    assert len(p1.hand) == hand_antes + 1
    print("OK  - Bimbo gastou 5 apostas por artefato")


def test_zebum_invoca_heroi_estrangeiro():
    state = make_state()
    p1 = state.players[0]
    p1.correct_bets = 10
    p1.city.magic = 10
    p1.chosen_hero_id = "zebum"
    summon_hero(state, 1)
    zebum_invocar_heroi(state, 1, "iuna")
    assert "iuna" in p1.zebum_herois
    assert any(isinstance(u, Hero) and u.hero_id == "iuna" for u in p1.units)
    assert p1.correct_bets == 6
    print("OK  - Zebum invocou Iuna por 4 apostas")


def test_zebum_custo_crescente():
    state = make_state()
    p1 = state.players[0]
    p1.correct_bets = 100
    p1.city.magic = 10
    p1.chosen_hero_id = "zebum"
    summon_hero(state, 1)
    zebum_invocar_heroi(state, 1, "iuna")
    zebum_invocar_heroi(state, 1, "besouro")
    assert p1.correct_bets == 100 - 10, f"Esperado 90, veio {p1.correct_bets}"
    print("OK  - Custo crescente: 4 + 6 = 10 apostas")


def test_zebum_nao_invoca_heroi_principal_alheio():
    state = make_state()
    p1 = state.players[0]
    p1.correct_bets = 100
    p1.city.magic = 10
    p1.chosen_hero_id = "zebum"
    summon_hero(state, 1)
    try:
        zebum_invocar_heroi(state, 1, "miyamoto")
        raise AssertionError("Deveria bloquear heroi principal alheio")
    except ActionError as e:
        print(f"OK  - Nao invoca heroi principal alheio: {e}")


def test_gnomos_herdam_orcs_completo():
    state = make_state()
    p1 = state.players[0]
    p1.correct_bets = 10
    p1.city.magic = 10
    p1.chosen_hero_id = "sao_tome"
    summon_hero(state, 1, force_hero_id="sao_tome")
    gnomo_alocar_aposta(state, 1, "H", 3)  # J3 = orcs
    red = peoples.magic_cost_reduction(p1, state)
    assert red == 1, f"magic_cost_reduction esperado 1, veio {red}"
    custo_hero = peoples.hero_summon_cost(p1, state)
    assert custo_hero == 2, f"hero_summon_cost esperado 2, veio {custo_hero}"
    arqs = peoples.available_archetypes(p1, state)
    assert TroopArchetype.EXTRA in arqs, f"Sem EXTRA: {arqs}"
    print("OK  - Gnomos herdam Orc completo (magia + slot extra)")


def test_gnomos_nao_herdam_mv():
    state = make_state()
    p1 = state.players[0]
    p1.correct_bets = 10
    p1.city.magic = 10
    p1.chosen_hero_id = "sao_tome"
    summon_hero(state, 1, force_hero_id="sao_tome")
    # Setup nao tem MV; so confirma que nada de MV vaza
    effective = peoples.sao_tome_effective_peoples(state, p1)
    assert "mortos_vivos" not in effective
    arqs = peoples.available_archetypes(p1, state)
    assert TroopArchetype.GHOUL not in arqs
    assert TroopArchetype.ESQUELETO not in arqs
    print("OK  - Gnomos nao herdam MV (slots nem custo)")


def run_all():
    tests = [
        test_alocar_aposta,
        test_aposta_nao_pode_ser_em_si,
        test_aposta_cumprida_em_raise_city_life,
        test_aposta_cumprida_em_summon_troop,
        test_aposta_cumprida_em_play_artifact,
        test_aposta_cumprida_em_kill,
        test_aposta_acumula_entre_turnos,
        test_bimbo_invisibilidade,
        test_bimbo_gastar_5,
        test_zebum_invoca_heroi_estrangeiro,
        test_zebum_custo_crescente,
        test_zebum_nao_invoca_heroi_principal_alheio,
        test_gnomos_herdam_orcs_completo,
        test_gnomos_nao_herdam_mv,
    ]
    print("=== Testes Gnomos e Duendes ===\n")
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
