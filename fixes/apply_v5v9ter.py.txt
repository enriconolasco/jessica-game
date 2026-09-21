"""v5v9-ter — injeta snapshot_night_start() no ponto correto de end_day.

Alvo: linha `state.phase = Phase.NIGHT` em end_day.
Posição: imediatamente antes, depois de _luna_return.

Idempotente. Backup em backups/v5v9ter_<ts>/. Aborta se quebrar sintaxe."""
import ast
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


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
    bkp = root / "backups" / f"v5v9ter_{ts}"
    bkp.mkdir(parents=True, exist_ok=True)
    print(f"ROOT: {root}\nBackup: {bkp}")

    tp = core / "turn.py"
    tsrc = tp.read_text(encoding="utf-8")

    if "def snapshot_night_start" not in tsrc:
        print("AVISO: snapshot_night_start não existe em turn.py — rode apply_v5v9bis.py primeiro")
        return 1

    # bloco end_day inteiro
    ed_pat = re.compile(r"def end_day\([^)]*\)[^:]*:[\s\S]*?(?=\ndef |\nclass |\Z)")
    ed = ed_pat.search(tsrc)
    if not ed:
        print("AVISO: end_day não casou")
        return 1

    body = ed.group(0)

    # já injetado?
    if "snapshot_night_start(state)" in body:
        print("[skip] snapshot_night_start(state) já está em end_day")
        return 0

    # alvo: linha com state.phase = Phase.NIGHT, captura indentação
    m = re.search(r"^([ \t]*)state\.phase\s*=\s*Phase\.NIGHT\b", body, re.MULTILINE)
    if not m:
        print("AVISO: não achei `state.phase = Phase.NIGHT` em end_day")
        return 1

    indent = m.group(1)
    inject = f"{indent}snapshot_night_start(state)  # v5v9ter\n"

    new_body = body[:m.start()] + inject + body[m.start():]
    new_src = tsrc[:ed.start()] + new_body + tsrc[ed.end():]

    # validação
    try:
        ast.parse(new_src)
    except SyntaxError as ex:
        print(f"[ERRO] turn.py quebraria: {ex}")
        return 1

    shutil.copy2(tp, bkp / "turn.py")
    tp.write_text(new_src, encoding="utf-8")
    print("OK: snapshot_night_start() injetado em end_day")
    print(f"\nBackup: {bkp / 'turn.py'}")
    print("Rode: python tests\\run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())