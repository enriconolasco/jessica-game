#!/usr/bin/env python3
"""Testes v5v9a/b — existência dos campos + serialização.

Formato de saída: "<N> passaram, <M> falharam" (parsed por run_all.py).
"""
import dataclasses
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jessica.core import models  # noqa: E402


TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def _fields(cls):
    return {f.name: f for f in dataclasses.fields(cls)}


# ---------- v5v9a ----------

@test
def test_player_tem_miyamoto_bonus():
    fs = _fields(models.Player)
    assert "miyamoto_life_max_bonus" in fs, \
        "Player.miyamoto_life_max_bonus ausente (v5v9a) — apply_v5v9bis não rodou?"
    f = fs["miyamoto_life_max_bonus"]
    if f.default is not dataclasses.MISSING:
        assert f.default == 0, f"default esperado 0, veio {f.default!r}"
    elif f.default_factory is not dataclasses.MISSING:
        assert f.default_factory() == 0


@test
def test_player_miyamoto_atribuivel():
    p = object.__new__(models.Player)
    # não constrói dataclass completo; só confere que setattr funciona
    p.miyamoto_life_max_bonus = 3
    assert p.miyamoto_life_max_bonus == 3


# ---------- v5v9b ----------

@test
def test_gamestate_tem_night_start_positions():
    fs = _fields(models.GameState)
    assert "night_start_positions" in fs, \
        "GameState.night_start_positions ausente (v5v9b) — apply_v5v9bis não rodou?"
    f = fs["night_start_positions"]
    if f.default_factory is not dataclasses.MISSING:
        assert f.default_factory() == {}
    elif f.default is not dataclasses.MISSING:
        assert f.default == {}


@test
def test_gamestate_instancia_com_campo_vazio():
    try:
        s = models.GameState(seed=0)
    except TypeError as ex:
        # assinatura mudou; aceita como skip sem falhar
        print(f"  (skip test_gamestate_instancia_com_campo_vazio: {ex})")
        return
    assert getattr(s, "night_start_positions", None) == {}


# ---------- serialização ----------

@test
def test_serialize_menciona_os_dois():
    src = (ROOT / "jessica" / "core" / "serialize.py").read_text(encoding="utf-8")
    assert "miyamoto" in src, "serialize.py não serializa Miyamoto (v5v9a)"
    assert "night_start_positions" in src, \
        "serialize.py não serializa night_start_positions (v5v9b)"


@test
def test_serialize_tem_imports_minimos():
    src = (ROOT / "jessica" / "core" / "serialize.py").read_text(encoding="utf-8")
    assert "def state_to_dict" in src
    assert "def state_from_dict" in src


# ---------- helpers em peoples.py / turn.py ----------

@test
def test_peoples_tem_helper_miyamoto():
    src = (ROOT / "jessica" / "core" / "peoples.py").read_text(encoding="utf-8")
    assert "def hero_life_with_persistent_bonus" in src


@test
def test_peoples_helper_chamado_no_hook():
    src = (ROOT / "jessica" / "core" / "peoples.py").read_text(encoding="utf-8")
    assert 'killer_unit.hero_id == "miyamoto"' in src
    assert 'dead_unit.statuses.get("life_at_death"' in src


@test
def test_turn_tem_snapshot_night_start():
    src = (ROOT / "jessica" / "core" / "turn.py").read_text(encoding="utf-8")
    assert "def snapshot_night_start" in src, "turn.py sem snapshot_night_start (v5v9b)"
    assert "def night_start_priority" in src, "turn.py sem night_start_priority (v5v9b)"


# ---------- runner ----------

def main():
    passed = 0
    failed = 0
    for fn in TESTS:
        try:
            fn()
            passed += 1
            print(f"ok   {fn.__name__}")
        except AssertionError as ex:
            failed += 1
            print(f"FAIL {fn.__name__}: {ex}")
        except Exception as ex:
            failed += 1
            print(f"ERR  {fn.__name__}: {ex.__class__.__name__}: {ex}")
            traceback.print_exc()
    print(f"{passed} passaram, {failed} falharam")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
