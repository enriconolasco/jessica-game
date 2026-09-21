"""apply_fix_v5v12: fix run_all test_valendar, Fadas so heroi mata heroi,
   cancelar por ultimo em sonho lucido/luna/jogar artefato."""
from pathlib import Path
from datetime import datetime
import os
import re
import shutil

def _find_project_root() -> Path:
    env = os.environ.get("JESSICA_ROOT")
    if env:
        p = Path(env)
        if (p / "jessica" / "main.py").exists():
            return p
    candidates = [
        Path.home() / "Downloads" / "jessica",
        Path.home() / "jessica",
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
    ]
    for c in candidates:
        if (c / "jessica" / "main.py").exists():
            return c
    return Path.home() / "Downloads" / "jessica"

ROOT = _find_project_root()
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v12_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _patch_test_runall() -> bool:
    """Corrige run_all() em test_valendar_luna.py (funcao renomeada)."""
    full = ROOT / "tests" / "test_valendar_luna.py"
    if not full.exists():
        print("AVISO - test_valendar_luna.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt
    txt = txt.replace(
        "        test_valendar_blocks_sonho_lucido,",
        "        test_valendar_usa_devaneio,"
    )
    if txt == original:
        print("AVISO - run_all() do test_valendar_luna.py nao mudou.")
        return False
    backup = BACKUP_DIR / "tests" / "test_valendar_luna.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - test_valendar_luna.py: run_all() atualizado")
    return True


def _patch_fadas_heroi_mata_heroi() -> bool:
    """Fadas so ganham artefato se heroi fada mata HEROI (nao tropa)."""
    full = ROOT / "jessica" / "core" / "peoples.py"
    if not full.exists():
        print("AVISO - peoples.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt
    txt = txt.replace(
        '''\
    if killer_player.people == PEOPLE_FAE and isinstance(killer_unit, Hero):
        if not state.shop.is_empty():
            card = state.shop.draw_random(state.rng)
            killer_player.hand.append(card)
            log(state, f"{killer_player.name} (Fadas): {killer_unit.id} matou "
                       f"{dead_unit.id} e ganhou {card}.")''',
        '''\
    if (killer_player.people == PEOPLE_FAE
            and isinstance(killer_unit, Hero)
            and isinstance(dead_unit, Hero)):
        if not state.shop.is_empty():
            card = state.shop.draw_random(state.rng)
            killer_player.hand.append(card)
            log(state, f"{killer_player.name} (Fadas): {killer_unit.id} matou "
                       f"Heroi {dead_unit.id} e ganhou {card}.")'''
    )
    if txt == original:
        print("AVISO - bloco Fadas nao casou em peoples.py.")
        return False
    backup = BACKUP_DIR / "jessica" / "core" / "peoples.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - peoples.py: Fadas so heroi-mata-heroi")
    return True


def _patch_cancelar_ultimo() -> bool:
    """Move 'Cancelar' para o fim em 3 lugares do main.py."""
    full = ROOT / "jessica" / "main.py"
    if not full.exists():
        print("AVISO - main.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt
    changes = 0

    # 1. Sonho Lucido (sem Luna): "Cancelar" primeiro
    old1 = '''\
                labels = ["Cancelar"] + [card_display(c) for c in player.hand]
                idx = pick_index("Inverter qual?", labels)
                if idx == 0:
                    console.print("[yellow]Sonho Lucido cancelado.[/yellow]")
                    return None
                choice_data["flip_cards"] = [player.hand[idx - 1]]'''
    new1 = '''\
                labels = [card_display(c) for c in player.hand] + ["Cancelar"]
                idx = pick_index("Inverter qual?", labels)
                if idx == len(player.hand):
                    console.print("[yellow]Sonho Lucido cancelado.[/yellow]")
                    return None
                choice_data["flip_cards"] = [player.hand[idx]]'''
    if old1 in txt:
        txt = txt.replace(old1, new1, 1)
        changes += 1
        print("  OK  - Sonho Lucido: Cancelar movido pro fim")
    else:
        print("  AVISO - snippet Sonho Lucido nao casou")

    # 2. Luna Sonho Lucido: "(parar)" primeiro
    old2 = '''\
                labels = ["(parar)"] + [card_display(c) for c in hand_disponivel]
                idx = pick_index("Inverter qual?", labels)
                if idx == 0:
                    break
                c = hand_disponivel.pop(idx - 1)
                cards.append(c)'''
    new2 = '''\
                labels = [card_display(c) for c in hand_disponivel] + ["(parar)"]
                idx = pick_index("Inverter qual?", labels)
                if idx == len(hand_disponivel):
                    break
                c = hand_disponivel.pop(idx)
                cards.append(c)'''
    if old2 in txt:
        txt = txt.replace(old2, new2, 1)
        changes += 1
        print("  OK  - Luna Sonho Lucido: (parar) movido pro fim")
    else:
        print("  AVISO - snippet Luna Sonho nao casou")

    # 3. Jogar artefato (branch "a")
    # Buscar tanto a versao com "Cancelar" no inicio quanto nao
    if 'labels = ["Cancelar"] + [card_display(c) for c in player.hand]\n        idx = pick_index("Jogar", labels)\n        if idx == 0:' in txt:
        old3 = '''\
        labels = ["Cancelar"] + [card_display(c) for c in player.hand]
        idx = pick_index("Jogar", labels)
        if idx == 0:
            console.print("[yellow]Cancelado.[/yellow]")
            return None
        card = player.hand[idx - 1]'''
        new3 = '''\
        labels = [card_display(c) for c in player.hand] + ["Cancelar"]
        idx = pick_index("Jogar", labels)
        if idx == len(player.hand):
            console.print("[yellow]Cancelado.[/yellow]")
            return None
        card = player.hand[idx]'''
        if old3 in txt:
            txt = txt.replace(old3, new3, 1)
            changes += 1
            print("  OK  - Jogar artefato: Cancelar movido pro fim")
        else:
            print("  AVISO - snippet Jogar artefato nao casou")

    if changes == 0:
        print("AVISO - nenhuma mudanca de 'cancelar por ultimo' aplicada.")
        return False
    backup = BACKUP_DIR / "jessica" / "main.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print(f"OK  - main.py: {changes} menu(s) ajustado(s)")
    return True


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    _patch_test_runall()
    _patch_fadas_heroi_mata_heroi()
    _patch_cancelar_ultimo()

    print(f"\nBackup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")


if __name__ == "__main__":
    main()