"""apply_update_v5b4c: Sao Tome herda passivas continuas."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b4c_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. peoples.py - helper de dano Lobisomem para Sao Tome
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    'def apply_cova_rasa(state: GameState) -> None:',
    'def sao_tome_dano_lobisomem(state: GameState, attacker) -> bool:\n'
    '    """Sao Tome herda o dobro de dano em Lua Cheia se tem aposta em Lobisomens."""\n'
    '    if not (isinstance(attacker, Hero) and attacker.hero_id == "sao_tome"):\n'
    '        return False\n'
    '    owner = get_player(state, attacker.owner_id)\n'
    '    if owner.people != PEOPLE_GNOMOS:\n'
    '        return False\n'
    '    effective = sao_tome_effective_peoples(state, owner)\n'
    '    if PEOPLE_LOBISOMENS not in effective:\n'
    '        return False\n'
    '    for other in state.players:\n'
    '        if other.id == owner.id:\n'
    '            continue\n'
    '        if not sao_tome_has_aposta_em(owner, other.id):\n'
    '            continue\n'
    '        if other.people != PEOPLE_LOBISOMENS:\n'
    '            continue\n'
    '        if is_lua_cheia(state, other.id):\n'
    '            return True\n'
    '    return False\n'
    '\n'
    '\n'
    'def apply_cova_rasa(state: GameState) -> None:'
))

# =============================================================
# 2. peoples.py - on_unit_moved com Sao Tome
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    'def on_unit_moved(state: GameState, player_id: int, unit: Unit) -> None:\n'
    '    player = get_player(state, player_id)\n'
    '    if player.people != PEOPLE_FAE:\n'
    '        return\n'
    '    player.city.magic += 1\n'
    '    log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id}.")',
    'def on_unit_moved(state: GameState, player_id: int, unit: Unit) -> None:\n'
    '    player = get_player(state, player_id)\n'
    '    if player.people == PEOPLE_FAE:\n'
    '        player.city.magic += 1\n'
    '        log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id}.")\n'
    '        return\n'
    '    if (player.people == PEOPLE_GNOMOS\n'
    '            and isinstance(unit, Hero) and unit.hero_id == "sao_tome"):\n'
    '        effective = sao_tome_effective_peoples(state, player)\n'
    '        if PEOPLE_FAE in effective:\n'
    '            player.city.magic += 1\n'
    '            log(state, f"{player.name} (Sao Tome herda Fadas): +1 Magia ao mover.")'
))

# =============================================================
# 3. peoples.py - on_unit_killed_by com Sao Tome
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    '    on_action_performed(state, killer_player_id, "kill")',
    '    # Sao Tome: herda hooks de kill das apostas\n'
    '    if (isinstance(killer_unit, Hero) and killer_unit.hero_id == "sao_tome"\n'
    '            and killer_player.people == PEOPLE_GNOMOS):\n'
    '        effective = sao_tome_effective_peoples(state, killer_player)\n'
    '        if PEOPLE_VAMPIRES in effective:\n'
    '            before = killer_unit.life\n'
    '            killer_unit.life = min(killer_unit.life_max, killer_unit.life + 2)\n'
    '            if killer_unit.life != before:\n'
    '                log(state, f"  Sao Tome curou +{killer_unit.life - before} (Sede de Sangue).")\n'
    '        if PEOPLE_LOBISOMENS in effective:\n'
    '            sig = unit_signature(dead_unit)\n'
    '            if sig not in killer_player.infectados:\n'
    '                killer_player.infectados.append(sig)\n'
    '                log(state, f"  {dead_unit.id} infectado por Sao Tome (Maldicao da Lua).")\n'
    '\n'
    '    on_action_performed(state, killer_player_id, "kill")'
))

# =============================================================
# 4. combat.py - _attack_multiplier com Lobisomem de Sao Tome
# =============================================================
EDITS.append((
    "jessica/core/combat.py",
    '    if peoples.is_lobisomem_ativo(state, attacker):\n'
    '        mult *= 2\n'
    '    return mult',
    '    if peoples.is_lobisomem_ativo(state, attacker):\n'
    '        mult *= 2\n'
    '    if peoples.sao_tome_dano_lobisomem(state, attacker):\n'
    '        mult *= 2\n'
    '    return mult'
))

# =============================================================
# 5. main.py - mostrar passivas virtuais na tela k
# =============================================================
EDITS.append((
    "jessica/main.py",
    '    console.print("\\n[bold]Herois dos outros (em campo)[/bold]")',
    '    # Sao Tome: passivas virtuais dos alvos das apostas\n'
    '    if player.people == "gnomos_duendes":\n'
    '        sao_tome = next((u for u in player.units\n'
    '                         if isinstance(u, Hero) and u.is_alive()\n'
    '                         and u.hero_id == "sao_tome"), None)\n'
    '        if sao_tome is not None:\n'
    '            effective = peoples.sao_tome_effective_peoples(state, player)\n'
    '            extras = sorted(p for p in effective if p != "gnomos_duendes")\n'
    '            if extras:\n'
    '                console.print("\\n[bold]Passivas virtuais (Sao Tome):[/bold]")\n'
    '                for povo in extras:\n'
    '                    console.print(f"  [cyan]{povo}[/cyan]: {PASSIVA_DESC.get(povo, \'-\')}")\n'
    '\n'
    '    console.print("\\n[bold]Herois dos outros (em campo)[/bold]")'
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
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()