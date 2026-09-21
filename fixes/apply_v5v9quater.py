"""v5v9-quater v2 — conserta snapshot_night_start.

O v1 tinha bug no verificador (procurava string inexistente).
Este só troca o check. Resto idêntico."""
import ast
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


HELPER_NOVO = '''def snapshot_night_start(state):
    """Guarda {(pid, unit_id): house} de todas unidades no início da noite."""
    snap = {}
    for p in getattr(state, "players", []) or []:
        pid = getattr(p, "id", None)
        for u in getattr(p, "units", []) or []:
            uid = getattr(u, "id", None)
            if uid is None:
                uid = id(u)
            house = getattr(u, "house", None) or getattr(u, "location", None) or "?"
            snap[f"{pid}:{uid}"] = str(house)
    state.night_start_positions = snap
'''


def find_root() -> Path:
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


def main():
    root = find_root()
    core = root / "jessica" / "core"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = root / "backups" / f"v5v9quater_{ts}"
    bkp.mkdir(parents=True, exist_ok=True)
    print(f"ROOT: {root}\nBackup: {bkp}")

    tp = core / "turn.py"
    tsrc = tp.read_text(encoding="utf-8")

    pat = re.compile(
        r"def snapshot_night_start\([^)]*\)[^:]*:[\s\S]*?(?=\ndef |\nclass |\Z)"
    )
    if not pat.search(tsrc):
        print("AVISO: snapshot_night_start não existe em turn.py")
        return 1

    novo = pat.sub(HELPER_NOVO, tsrc, count=1)

    m = re.search(r"def snapshot_night_start[\s\S]*?(?=\ndef |\Z)", novo)
    if not m:
        print("[ERRO] não achei snapshot_night_start depois da substituição")
        return 1
    body = m.group(0)

    if ".items()" in body:
        print("[ERRO] ainda contém .items() — abortando")
        print("Trecho:")
        print(body[:500])
        return 1
    if 'getattr(state, "players", [])' not in body:
        print("[ERRO] não usa lista com getattr(state, \"players\", [])")
        print("Trecho:")
        print(body[:500])
        return 1

    try:
        ast.parse(novo)
    except SyntaxError as ex:
        print(f"[ERRO] turn.py quebraria: {ex}")
        return 1

    shutil.copy2(tp, bkp / "turn.py")
    tp.write_text(novo, encoding="utf-8")
    print("OK: snapshot_night_start substituído (itera list[Player])")
    print(f"\nBackup: {bkp / 'turn.py'}")
    print("Rode: python tests\\run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())