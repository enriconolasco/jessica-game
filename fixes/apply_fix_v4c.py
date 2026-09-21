"""apply_fix_v4c: Luna return + testes de catalogo atualizados."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v4c_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# jessica/core/turn.py — reativa Luna return
# =============================================================
FILES["jessica/core/turn.py"] = '''\
from __future__ import annotations
from .constants import Phase, MONUMENT_BONUS_INTERVAL
from .actions import apply_gold_interest, reset_unit_flags
from .state import get_player, log
from .models import GameState, Hero, Troop
from . import artifacts_effects, peoples


class TurnError(Exception):
    pass


def start_turn(state: GameState) -> list[tuple[int, int]]:
    if state.game_over:
        raise TurnError("Partida ja encerrada.")
    log(state, f"--- Inicio do Turno {state.turn} (Dia) ---")
    state.phase = Phase.DAY
    interest = apply_gold_interest(state)
    artifacts_effects.on_turn_start(state)
    if state.turn % MONUMENT_BONUS_INTERVAL == 0:
        _monument_bonus(state)
    _process_espectros(state)
    _process_gigantes_turn(state)
    peoples.apply_lua_cheia_effects(state)
    reset_unit_flags(state)
    return interest


def _monument_bonus(state: GameState) -> None:
    for player in state.players:
        if not player.city.is_alive():
            continue
        if not player.city.has_monument:
            continue
        if state.shop.is_empty():
            continue
        card = state.shop.draw_random(state.rng)
        player.hand.append(card)
        log(state, f"{player.name}: Monumento concedeu {card}.")


def _process_espectros(state: GameState) -> None:
    if not state.espectros_pendentes:
        return
    pend = state.espectros_pendentes
    state.espectros_pendentes = []
    for e in pend:
        owner = get_player(state, e["owner_of_cobra"])
        if not owner.city.is_alive():
            continue
        from . import heroes
        hdef = heroes.get_hero(e["hero_id"])
        n = sum(1 for u in owner.units if isinstance(u, Hero))
        unit_id = f"p{owner.id}_spectre_{e['hero_id']}_{n}"
        hero = Hero(id=unit_id, owner_id=owner.id, house=e["house"],
                    life=hdef.life, life_max=hdef.life,
                    hero_id=hdef.hero_id, has_moved_this_turn=True)
        hero.statuses["espectro_until_turn"] = state.turn
        owner.units.append(hero)
        log(state, f"{owner.name}: Espectro de {hdef.name} surgiu em {e['house']}.")


def _process_gigantes_turn(state: GameState) -> None:
    if state.turn % 4 != 0:
        return
    for player in state.players:
        if player.people != peoples.PEOPLE_GIGANTES:
            continue
        if not player.city.is_alive():
            continue
        for u in player.units:
            if isinstance(u, Hero) and u.is_alive():
                if u.hero_id in ("joao_grandao", "pe_descalco"):
                    u.life_max *= 2
                    u.life = u.life_max
                    log(state, f"{player.name}: {u.hero_id} vida dobrada ({u.life_max}).")
        if any(isinstance(u, Hero) and u.hero_id == "caroco" for u in player.units):
            player.carocos_gerados += 1
            n = sum(1 for u in player.units if isinstance(u, Hero))
            unit_id = f"p{player.id}_caroco_extra_{n}"
            hero = Hero(id=unit_id, owner_id=player.id, house=f"city_{player.id}",
                        life=2, life_max=2, hero_id="caroco", has_moved_this_turn=True)
            player.units.append(hero)
            log(state, f"{player.name}: novo Caroco gerado.")


def start_player_day(state: GameState, player_id: int) -> None:
    player = get_player(state, player_id)
    if player.skip_day_turn == state.turn:
        log(state, f"{player.name} esta pulado (Jc).")
        player.has_played_day_this_turn = True
        return
    if not player.morning_done_this_turn:
        player.morning_done_this_turn = True
        peoples.on_player_morning(state, player_id)
    artifacts_effects.on_player_day_start(state, player_id)


def day_order(state: GameState) -> list[int]:
    if not state.turn_order:
        raise TurnError("turn_order nao definido.")
    alive = {p.id for p in state.alive_players()}
    idx = state.turn_order.index(state.curuna_id)
    ordered = state.turn_order[idx:] + state.turn_order[:idx]
    result: list[int] = []
    for pid in ordered:
        if pid not in alive:
            continue
        p = get_player(state, pid)
        if state.phase == Phase.DAY and p.skip_day_turn == state.turn:
            continue
        if state.phase == Phase.NIGHT and p.skip_night_turn == state.turn:
            continue
        result.append(pid)
    return result


def _luna_return(state: GameState) -> None:
    """Luna, se andou no Dia, retorna ao local de origem no inicio da Noite.
    TODO: v4c real deve perguntar ao jogador. Por enquanto, retorna automatico."""
    for player in state.players:
        for u in player.units:
            if (isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"
                    and "luna_origin_house" in u.statuses):
                origin = u.statuses.pop("luna_origin_house")
                if origin != u.house:
                    log(state, f"  Luna retorna de {u.house} para {origin}.")
                    u.house = origin


def end_day(state: GameState) -> None:
    if state.phase != Phase.DAY:
        raise TurnError("Nao esta na fase do Dia.")
    state.deaths_this_night = []
    artifacts_effects.on_night_start(state)
    _luna_return(state)
    state.phase = Phase.NIGHT
    log(state, f"--- Fase da Noite (Turno {state.turn}) ---")


def end_turn(state: GameState) -> None:
    from .victory import check_victory
    artifacts_effects.on_end_turn(state)
    _remove_espectros(state)
    check_victory(state)
    if state.game_over:
        return
    alive = {p.id for p in state.alive_players()}
    idx = state.turn_order.index(state.curuna_id)
    for offset in range(1, len(state.turn_order) + 1):
        candidate = state.turn_order[(idx + offset) % len(state.turn_order)]
        if candidate in alive:
            state.curuna_id = candidate
            break
    state.turn += 1


def _remove_espectros(state: GameState) -> None:
    for p in state.players:
        p.units = [u for u in p.units
                   if u.statuses.get("espectro_until_turn", -1) != state.turn]
'''

# =============================================================
# tests/test_sanity.py — 31 herois, 8 feiticos
# =============================================================
FILES["tests/test_sanity.py"] = '''\
"""Teste de sanidade."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests import _utf8
_utf8.setup()


def test_imports():
    from jessica.core import (
        constants, models, state, setup, actions, combat,
        turn, victory, serialize, artifacts, artifacts_effects,
        peoples, heroes, spells, rng,
    )
    print("OK  - todos os modulos carregam")


def test_heroes_catalog():
    from jessica.core import heroes
    # 12 base + 7 anoes individuais + 12 novos (vampiros/lobisomens/gigantes/mv)
    assert len(heroes.HERO_CATALOG) == 31, (
        f"Esperado 31 herois, tem {len(heroes.HERO_CATALOG)}"
    )
    for people in ("humanos", "orcs", "fadas", "vampiros", "lobisomens",
                   "gigantes", "mortos_vivos"):
        hs = heroes.heroes_for_people(people)
        assert len(hs) == 3, f"{people} tem {len(hs)} herois escolhiveis, esperado 3"
    anao = heroes.heroes_for_people("anoes")
    assert len(anao) == 3, f"anoes tem {len(anao)} herois escolhiveis, esperado 3"
    print("OK  - 31 herois no catalogo (3 escolhiveis por povo)")


def test_spells_catalog():
    from jessica.core import spells
    assert len(spells.SPELL_CATALOG) == 8, (
        f"Esperado 8 feiticos, tem {len(spells.SPELL_CATALOG)}"
    )
    for people in ("humanos", "anoes", "orcs", "fadas",
                   "vampiros", "lobisomens", "gigantes", "mortos_vivos"):
        sp = spells.spell_for_people(people)
        assert sp is not None, f"{people} sem feitico"
    print("OK  - 8 feiticos, 1 por povo")


def test_setup_runs():
    from jessica.core.setup import run_setup
    state, _ = run_setup(
        all_peoples=["humanos", "anoes", "orcs", "fadas"],
        heroes_by_people={
            "humanos": ["miyamoto"], "anoes": ["ori"],
            "orcs": ["garoche"], "fadas": ["ainai"],
        },
        choices={
            1: {"povo": "humanos", "heroi": "miyamoto"},
            2: {"povo": "anoes", "heroi": "ori"},
            3: {"povo": "orcs", "heroi": "garoche"},
            4: {"povo": "fadas", "heroi": "ainai"},
        },
        seed=20260916,
    )
    assert len(state.players) == 4
    print("OK  - setup roda")


def test_unit_has_new_fields():
    from jessica.core.models import Unit
    u = Unit(id="x", owner_id=1, house="center", life=4, life_max=4)
    assert u.attacks_made_this_day == 0
    assert u.statuses == {}
    assert u.moves_this_turn == 0
    assert u.infectado is False
    print("OK  - Unit tem campos novos")


def test_player_has_new_fields():
    from jessica.core.models import Player, City
    c = City(owner_id=1, life=2, life_max=6)
    p = Player(id=1, name="X", people="humanos", city=c)
    assert p.spell_cooldown_until_turn == 0
    assert p.arken_espolia_used_turn == -1
    assert p.besouro_mandinga_used_turn == -1
    assert p.pena_added_once is False
    assert p.carocos_gerados == 0
    assert p.empalados == []
    assert p.infectados == []
    print("OK  - Player tem campos novos")


def run_all():
    tests = [
        test_imports,
        test_heroes_catalog,
        test_spells_catalog,
        test_setup_runs,
        test_unit_has_new_fields,
        test_player_has_new_fields,
    ]
    print("=== Sanidade ===\\n")
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
# Execucao
# =============================================================
def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for rel_path, content in FILES.items():
        full = ROOT / rel_path
        if full.exists():
            backup_path = BACKUP_DIR / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, backup_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        print(f"OK  - {rel_path}")
    print(f"\\n{len(FILES)} arquivos escritos.")
    print(f"Backup: {BACKUP_DIR}")
    print("\\nRode:")
    print("  python tests/run_all.py")


if __name__ == "__main__":
    main()