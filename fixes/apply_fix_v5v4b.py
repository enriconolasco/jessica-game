"""apply_fix_v5v4b: log de roll da Cabaca Cheia em actions.py (nao peoples)."""
from pathlib import Path
from datetime import datetime
import os
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v4b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

OLD = '''\
def _cabaca_cheia(state, player):
    r = state.rng.randint(1, 4)
    if r == 1:'''

NEW = '''\
def _cabaca_cheia(state, player):
    r = state.rng.randint(1, 4)
    log(state, f"[ROLL] Cabaca Cheia: 1d4 = {r}")
    if r == 1:'''


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    full = ROOT / "jessica" / "core" / "actions.py"
    if not full.exists():
        print(f"ERRO: {full} nao existe.")
        return
    original = full.read_text(encoding="utf-8")
    if OLD not in original:
        print("AVISO: snippet nao encontrado em actions.py.")
        print("Talvez ja tenha sido corrigido ou o arquivo divergiu.")
        return
    patched = original.replace(OLD, NEW, 1)
    backup_path = BACKUP_DIR / "jessica" / "core" / "actions.py"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(patched, encoding="utf-8")
    print("OK  - jessica/core/actions.py (log de roll do Caroco)")
    print(f"Backup: {BACKUP_DIR}")


if __name__ == "__main__":
    main()