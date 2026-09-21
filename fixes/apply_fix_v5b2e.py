"""apply_fix_v5b2e: test_artifact_effects_f3b - adapta ao novo contrato do Ks."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS = [
    (
        'from jessica.core.combat import resolve_attack, Attack, CombatError',
        'from jessica.core.combat import (\n'
        '    resolve_attack, Attack, CombatError, _effective_max_attacks,\n'
        ')'
    ),
    (
        '    end_day(state)\n'
        '    assert troop.max_attacks_this_night == 2, f"Esperado 2, veio {troop.max_attacks_this_night}"\n'
        '    print("OK  - Ks: tropa perto de Heroi ganha 2 ataques")',
        '    end_day(state)\n'
        '    efetivo = _effective_max_attacks(state, troop)\n'
        '    assert efetivo == 2, f"Esperado 2, veio {efetivo}"\n'
        '    print("OK  - Ks: tropa perto de Heroi ganha 2 ataques")'
    ),
    (
        '    end_day(state)\n'
        '    assert hero.hero_can_attack_city is True\n'
        '    assert troop.max_attacks_this_night == 2\n'
        '    end_turn(state)\n'
        '    assert hero.hero_can_attack_city is False\n'
        '    assert troop.max_attacks_this_night == 1\n'
        '    print("OK  - Ks buffs limpam")',
        '    end_day(state)\n'
        '    assert hero.hero_can_attack_city is True\n'
        '    assert _effective_max_attacks(state, troop) == 2\n'
        '    assert troop.statuses.get("k_s_active") is True\n'
        '    end_turn(state)\n'
        '    assert hero.hero_can_attack_city is False\n'
        '    assert _effective_max_attacks(state, troop) == 1\n'
        '    assert troop.statuses.get("k_s_active") is None\n'
        '    print("OK  - Ks buffs limpam")'
    ),
]


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    full = ROOT / "tests" / "test_artifact_effects_f3b.py"
    if not full.exists():
        print(f"ERRO: {full} nao existe.")
        return

    original = full.read_text(encoding="utf-8")
    current = original
    applied = 0
    for old, new in EDITS:
        if old not in current:
            print(f"AVISO - snippet nao encontrado:")
            print(f"  {old[:80]}...")
            continue
        current = current.replace(old, new, 1)
        applied += 1

    if current == original:
        print("Nenhuma edicao aplicada.")
        return

    backup = BACKUP_DIR / "tests" / "test_artifact_effects_f3b.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(current, encoding="utf-8")
    print(f"OK  - tests/test_artifact_effects_f3b.py ({applied}/{len(EDITS)} edits)")
    print(f"Backup: {BACKUP_DIR}")


if __name__ == "__main__":
    main()