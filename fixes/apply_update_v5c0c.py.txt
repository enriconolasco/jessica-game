"""apply_update_v5c0c: Gnomos herdam Orcs completo; sem MV/Gigantes; testes finais."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5c0c_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}
EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. peoples.py - re-adiciona Orcs (magia); remove MV em hero
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    'def magic_cost_reduction(player: Player, state: GameState | None = None) -> int:\n'
    '    if player.people == PEOPLE_ORCS:\n'
    '        return 1\n'
    '    return 0',
    'def magic_cost_reduction(player: Player, state: GameState | None = None) -> int:\n'
    '    if player.people == PEOPLE_ORCS:\n'
    '        return 1\n'
    '    if player.people == PEOPLE_GNOMOS and state is not None:\n'
    '        if PEOPLE_ORCS in sao_tome_effective_peoples(state, player):\n'
    '            return 1\n'
    '    return 0'
))

# =============================================================
# 2. peoples.py - extra_troop_slots: so Orc
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    '    if player.people == PEOPLE_GNOMOS and state is not None:\n'
    '        effective = sao_tome_effective_peoples(state, player)\n'
    '        result: dict[str, int] = {}\n'
    '        if PEOPLE_ORCS in effective:\n'
    '            result["extra"] = 1\n'
    '        if PEOPLE_MORTOS_VIVOS in effective:\n'
    '            if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"\n'
    '                   for u in player.units):\n'
    '                result["ghoul"] = 1\n'
    '                result["esqueleto"] = 1\n'
    '        return result\n'
    '    return {}',
    '    if player.people == PEOPLE_GNOMOS and state is not None:\n'
    '        effective = sao_tome_effective_peoples(state, player)\n'
    '        result: dict[str, int] = {}\n'
    '        if PEOPLE_ORCS in effective:\n'
    '            result["extra"] = 1\n'
    '        return result\n'
    '    return {}'
))

# =============================================================
# 3. tests/test_filhos_floresta.py (novo)
# =============================================================
FILES["tests/test_filhos_floresta.py"] = '''\
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
    print("=== Testes Filhos da Floresta ===\\n")
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
# 4. tests/test_gnomos_duendes.py (novo)
# =============================================================
FILES["tests/test_gnomos_duendes.py"] = '''\
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
    print("=== Testes Gnomos e Duendes ===\\n")
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


def _apply_edits(rel_path: str, full: Path, backup_dir: Path) -> bool:
    if not full.exists():
        print(f"AVISO - {rel_path} nao existe.")
        return False
    original = full.read_text(encoding="utf-8")
    current = original
    applied = 0
    for path, old, new in EDITS:
        if path != rel_path:
            continue
        if old not in current:
            print(f"  AVISO - snippet nao encontrado em {rel_path}:")
            print(f"    {old[:90]}...")
            continue
        current = current.replace(old, new, 1)
        applied += 1
    if current == original:
        print(f"AVISO - nenhuma edicao aplicada em {rel_path}.")
        return False
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(current, encoding="utf-8")
    print(f"OK  - {rel_path} ({applied} edit(s))")
    return True


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for rel_path, content in FILES.items():
        full = ROOT / rel_path
        if full.exists():
            backup_path = BACKUP_DIR / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, backup_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        print(f"OK  - {rel_path} (novo/sobrescrito)")
        written += 1

    edited_paths = sorted({e[0] for e in EDITS})
    for rel_path in edited_paths:
        full = ROOT / rel_path
        if _apply_edits(rel_path, full, BACKUP_DIR):
            written += 1

    print(f"\n{written} arquivo(s) modificado(s).")
    print(f"Backup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")


if __name__ == "__main__":
    main()