"""apply_fix_v5c0b: Sao Tome sem custo de magia herdado; teste Pe Descalco."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5c0b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. peoples.py - magic_cost_reduction sem heranca gnomos
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    'def magic_cost_reduction(player: Player, state: GameState | None = None) -> int:\n'
    '    if player.people == PEOPLE_ORCS:\n'
    '        return 1\n'
    '    if player.people == PEOPLE_GNOMOS and state is not None:\n'
    '        if PEOPLE_ORCS in sao_tome_effective_peoples(state, player):\n'
    '            return 1\n'
    '    return 0',
    'def magic_cost_reduction(player: Player, state: GameState | None = None) -> int:\n'
    '    if player.people == PEOPLE_ORCS:\n'
    '        return 1\n'
    '    return 0'
))

# =============================================================
# 2. peoples.py - hero_summon_cost sem heranca gnomos
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    'def hero_summon_cost(player: Player, state: GameState | None = None) -> int:\n'
    '    if player.people == PEOPLE_GIGANTES:\n'
    '        return 4\n'
    '    if player.people == PEOPLE_MORTOS_VIVOS:\n'
    '        return 2\n'
    '    if player.people == PEOPLE_GNOMOS and state is not None:\n'
    '        effective = sao_tome_effective_peoples(state, player)\n'
    '        if PEOPLE_MORTOS_VIVOS in effective:\n'
    '            return 2\n'
    '    return max(0, 3 - magic_cost_reduction(player, state))',
    'def hero_summon_cost(player: Player, state: GameState | None = None) -> int:\n'
    '    if player.people == PEOPLE_GIGANTES:\n'
    '        return 4\n'
    '    if player.people == PEOPLE_MORTOS_VIVOS:\n'
    '        return 2\n'
    '    return max(0, 3 - magic_cost_reduction(player, state))'
))

# =============================================================
# 3. test_gigantes.py - Pe Descalco agora tem 2 ataques base
# =============================================================
EDITS.append((
    "tests/test_gigantes.py",
    '    max_atks = _effective_max_attacks(state, pe)\n'
    '    # Pe Descalco tem +1 ataque sempre\n'
    '    assert max_atks == 1, f"Base deveria ser 1, veio {max_atks} (implementacao de +1 ataque fica na UI/passiva)"\n'
    '    print("OK  - Pe Descalco invocado (bonus +1 ataque na mecanica de combate)")',
    '    max_atks = _effective_max_attacks(state, pe)\n'
    '    # Pe Descalco tem +1 ataque sempre (base 1 + 1 bonus = 2)\n'
    '    assert max_atks == 2, f"Pe Descalco deveria ter 2 ataques (1 base + 1 bonus), veio {max_atks}"\n'
    '    print(f"OK  - Pe Descalco tem {max_atks} ataques (1 base + 1 bonus)")'
))


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

    edited_paths = sorted({e[0] for e in EDITS})
    total = 0
    for rel_path in edited_paths:
        full = ROOT / rel_path
        if _apply_edits(rel_path, full, BACKUP_DIR):
            total += 1

    print(f"\n{total} arquivo(s) modificado(s).")
    print(f"Backup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")


if __name__ == "__main__":
    main()