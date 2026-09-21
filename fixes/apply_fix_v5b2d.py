"""apply_fix_v5b2d: adapta test_heroes (Miyamoto) e test_valendar_luna (Luna)."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b2d_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # ===========================================================
    # test_heroes.py: usa _effective_max_attacks (Miyamoto on-the-fly)
    # ===========================================================
    th = ROOT / "tests" / "test_heroes.py"
    if th.exists():
        orig = th.read_text(encoding="utf-8")
        cur = orig
        # 1. importar _effective_max_attacks
        old_imp = "from jessica.core.combat import resolve_attack, Attack"
        new_imp = ("from jessica.core.combat import (\n"
                   "    resolve_attack, Attack, _effective_max_attacks,\n"
                   ")")
        if old_imp in cur:
            cur = cur.replace(old_imp, new_imp, 1)
        # 2. test_musashi_double_if_strongest
        old1 = '''\
    from jessica.core.turn import end_day
    end_day(state)
    assert miyamoto.max_attacks_this_night == 2, (
        f"Miyamoto deveria ter 2 ataques, tem {miyamoto.max_attacks_this_night}"
    )'''
        new1 = '''\
    from jessica.core.turn import end_day
    end_day(state)
    atks = _effective_max_attacks(state, miyamoto)
    assert atks == 2, f"Miyamoto deveria ter 2 ataques, tem {atks}"'''
        if old1 in cur:
            cur = cur.replace(old1, new1, 1)
        # 3. test_musashi_not_strongest
        old2 = '''\
    from jessica.core.turn import end_day
    end_day(state)
    assert miyamoto.max_attacks_this_night == 1, (
        f"Miyamoto deveria ter 1 ataque (heavy 8 é mais forte), tem "
        f"{miyamoto.max_attacks_this_night}"
    )'''
        new2 = '''\
    from jessica.core.turn import end_day
    end_day(state)
    atks = _effective_max_attacks(state, miyamoto)
    assert atks == 1, f"Miyamoto deveria ter 1 ataque, tem {atks}"'''
        if old2 in cur:
            cur = cur.replace(old2, new2, 1)
        if cur != orig:
            bkp = BACKUP_DIR / "tests" / "test_heroes.py"
            bkp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(th, bkp)
            th.write_text(cur, encoding="utf-8")
            print("OK  - tests/test_heroes.py")
        else:
            print("AVISO - test_heroes.py nao mudou (snippets nao encontrados).")
    else:
        print("AVISO - test_heroes.py nao existe.")

    # ===========================================================
    # test_valendar_luna.py: Luna precisa reset de movimento antes de move_unit
    # ===========================================================
    tl = ROOT / "tests" / "test_valendar_luna.py"
    if tl.exists():
        orig = tl.read_text(encoding="utf-8")
        cur = orig
        old3 = '''\
    luna = summon_hero(state, 4)
    assert luna.hero_id == "luna"
    assert luna.house == "city_4"
    move_unit(state, 4, luna.id, CENTER)'''
        new3 = '''\
    luna = summon_hero(state, 4)
    assert luna.hero_id == "luna"
    assert luna.house == "city_4"
    # H1: heroi invocado nasce "ja moveu". Reseta para testar Luna.
    luna.has_moved_this_turn = False
    luna.moves_this_turn = 0
    move_unit(state, 4, luna.id, CENTER)'''
        if old3 in cur:
            cur = cur.replace(old3, new3, 1)
        if cur != orig:
            bkp = BACKUP_DIR / "tests" / "test_valendar_luna.py"
            bkp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tl, bkp)
            tl.write_text(cur, encoding="utf-8")
            print("OK  - tests/test_valendar_luna.py")
        else:
            print("AVISO - test_valendar_luna.py nao mudou (snippet nao encontrado).")
    else:
        print("AVISO - test_valendar_luna.py nao existe.")

    print(f"\nBackup: {BACKUP_DIR}")
    print("Rode: python tests\\run_all.py")


if __name__ == "__main__":
    main()