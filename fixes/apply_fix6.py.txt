"""apply_fix6: run_all.py melhorado + sanity atualizado."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.resolve()
BACKUP_DIR = ROOT / f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# tests/run_all.py — mostra FALHOU lines de cada arquivo
# =============================================================
FILES["tests/run_all.py"] = '''\
"""Roda toda a bateria de testes. Salve em tests/."""
import subprocess
import sys
import re
from pathlib import Path

HERE = Path(__file__).parent.resolve()
TEST_FILES = sorted(HERE.glob("test_*.py"))


def main():
    print(f"Encontrados {len(TEST_FILES)} arquivos de teste.\\n")
    total_pass = 0
    total_fail = 0
    failed_files = []
    for tf in TEST_FILES:
        print(f"--- {tf.name} ---")
        result = subprocess.run(
            [sys.executable, str(tf)],
            capture_output=True, text=True, cwd=HERE.parent,
        )
        out = result.stdout + result.stderr
        m = re.search(r"(\\d+) passaram, (\\d+) falharam", out)
        if m:
            p, f = int(m.group(1)), int(m.group(2))
            total_pass += p
            total_fail += f
            print(f"  {p} passaram, {f} falharam")
            if f > 0:
                failed_files.append(tf.name)
                for line in out.splitlines():
                    if line.startswith("FALHOU"):
                        print(f"    {line}")
        else:
            total_fail += 1
            failed_files.append(tf.name)
            print(f"  ERRO (sem contagem)")
            # Mostra a linha do erro de sintaxe/import
            for line in out.splitlines():
                if "Error" in line or "SyntaxError" in line or "Exception" in line:
                    print(f"    {line}")
                    break
    print()
    print(f"TOTAL: {total_pass} passaram, {total_fail} falharam")
    if failed_files:
        print(f"Arquivos com falha: {', '.join(failed_files)}")


if __name__ == "__main__":
    main()
'''

# =============================================================
# tests/test_sanity.py — catálogo agora tem 19 heróis (12 + 7 anões)
# =============================================================
FILES["tests/test_sanity.py"] = '''\
"""Teste de sanidade."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_imports():
    from jessica.core import (
        constants, models, state, setup, actions, combat,
        turn, victory, serialize, artifacts, artifacts_effects,
        peoples, heroes, spells, rng,
    )
    print("OK  - todos os modulos carregam")


def test_heroes_catalog():
    from jessica.core import heroes
    # 12 base + 7 anoes individuais = 19
    assert len(heroes.HERO_CATALOG) == 19, (
        f"Esperado 19 herois (12 + 7 anoes), tem {len(heroes.HERO_CATALOG)}"
    )
    for people in ("humanos", "orcs", "fadas"):
        hs = heroes.heroes_for_people(people)
        assert len(hs) == 3, f"{people} tem {len(hs)} herois escolhiveis, esperado 3"
    anao = heroes.heroes_for_people("anoes")
    assert len(anao) == 3, f"anoes tem {len(anao)} herois escolhiveis, esperado 3"
    print("OK  - 19 herois no catalogo (3 escolhiveis por povo)")


def test_spells_catalog():
    from jessica.core import spells
    assert len(spells.SPELL_CATALOG) == 4
    for people in ("humanos", "anoes", "orcs", "fadas"):
        sp = spells.spell_for_people(people)
        assert sp is not None, f"{people} sem feitico"
    print("OK  - 4 feiticos, 1 por povo")


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
    print("OK  - Unit tem campos de dia/noite + statuses + moves")


def test_player_has_new_fields():
    from jessica.core.models import Player, City
    c = City(owner_id=1, life=2, life_max=6)
    p = Player(id=1, name="X", people="humanos", city=c)
    assert p.spell_cooldown_until_turn == 0
    assert p.arken_espolia_used_turn == -1
    assert p.besouro_mandinga_used_turn == -1
    assert p.pena_added_once is False
    print("OK  - Player tem campos de feitico/mandinga/pena")


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
# Execução
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