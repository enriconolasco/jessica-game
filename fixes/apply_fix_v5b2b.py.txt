"""apply_fix_v5b2b: limpa k_s_active no fim do turno."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b2b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

OLD = '''\
        for u in player.units:
            u.max_attacks_this_night = 1
            u.hero_can_attack_city = False
            u.max_moves_this_turn = 1
            # Feitico Resistencia (duracao 1 turno): reset
            n = u.statuses.pop("spell_resist", 0)'''

NEW = '''\
        for u in player.units:
            u.max_attacks_this_night = 1
            u.hero_can_attack_city = False
            u.max_moves_this_turn = 1
            # H10: Ks eh 1-turno, limpa o flag
            u.statuses.pop("k_s_active", None)
            # Feitico Resistencia (duracao 1 turno): reset
            n = u.statuses.pop("spell_resist", 0)'''


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    full = ROOT / "jessica" / "core" / "artifacts_effects.py"
    if not full.exists():
        print(f"ERRO: {full} nao existe.")
        return
    original = full.read_text(encoding="utf-8")
    if OLD not in original:
        print("AVISO: snippet nao encontrado em artifacts_effects.py.")
        print("Talvez ja tenha sido corrigido, ou o arquivo foi reescrito.")
        return
    patched = original.replace(OLD, NEW, 1)
    backup_path = BACKUP_DIR / "jessica" / "core" / "artifacts_effects.py"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(patched, encoding="utf-8")
    print("OK  - jessica/core/artifacts_effects.py (k_s_active limpo no fim do turno)")
    print(f"Backup: {BACKUP_DIR}")


if __name__ == "__main__":
    main()