"""v5v9b — GameState.night_start_positions.

- Adiciona campo {f"{pid}:{uid}": house_str} em GameState
- Popula no início da noite (hook em turn.py)
- Serializa em state_to_dict / state_from_dict
- Helper night_start_priority(state, pid, uid) -> 0 se estava no início, 1 senão

Defensivo: AVISO se snippet não casar."""
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


def add_field(src: str, cls: str, line: str) -> tuple[str, bool]:
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            last_end = None
            for n in node.body:
                if isinstance(n, (ast.AnnAssign, ast.Assign)):
                    last_end = n.end_lineno
            if last_end is None:
                return src, False
            lines = src.splitlines(keepends=True)
            lines.insert(last_end, f"    {line}\n")
            return "".join(lines), True
    return src, False


HELPER = '''

# --- v5v9b: prioridade de declaração noturna --------------------------------
def snapshot_night_start(state):
    """Guarda (pid, uid) -> house de todas unidades no início da noite."""
    snap = {}
    for pid, player in getattr(state, "players", {}).items():
        for u in getattr(player, "units", []) or []:
            hid = id(u) if not hasattr(u, "id") else u.id
            house = getattr(u, "house", None) or getattr(u, "location", None) or "?"
            snap[f"{pid}:{hid}"] = str(house)
    state.night_start_positions = snap


def night_start_priority(state, pid, uid) -> int:
    """0 = já estava no início da noite, 1 = chegou depois (declara por último)."""
    snap = getattr(state, "night_start_positions", None) or {}
    return 0 if f"{pid}:{uid}" in snap else 1
# ----------------------------------------------------------------------------
'''


def main():
    root = find_root()
    core = root / "jessica" / "core"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = root / "backups" / f"v5v9b_night_start_{ts}"
    bkp.mkdir(parents=True, exist_ok=True)

    # --- models.py ---
    mp = core / "models.py"
    msrc = mp.read_text(encoding="utf-8")
    if "night_start_positions" in msrc:
        print("[skip] models.py já tem night_start_positions")
    else:
        if "from dataclasses import" in msrc and "field" not in msrc.split("\n")[0:20].__str__():
            msrc = re.sub(r"from dataclasses import ([^\n]+)",
                          lambda m: f"from dataclasses import {m.group(1)}, field"
                          if "field" not in m.group(1) else m.group(0),
                          msrc, count=1)
        msrc, ok = add_field(msrc, "GameState",
                             "night_start_positions: dict = field(default_factory=dict)  # v5v9b")
        if not ok:
            print("AVISO: class GameState não casou em models.py")
        else:
            shutil.copy2(mp, bkp / "models.py")
            mp.write_text(msrc, encoding="utf-8")
            print("OK: GameState.night_start_positions adicionado")

    # --- turn.py: adiciona helper + hook (se possível) ---
    tp = core / "turn.py"
    tsrc = tp.read_text(encoding="utf-8")
    if "snapshot_night_start" not in tsrc:
        tsrc = tsrc.rstrip() + "\n" + HELPER
        # tenta enxertar chamada em end_day (antes do último return) — conservador
        m = re.search(r"(def end_day\([^)]*\):[\s\S]*?)(\n(?=def |class |\Z))", tsrc)
        if m:
            body = m.group(1)
            # procura último 'return' no corpo
            ret_m = list(re.finditer(r"\n(\s+)return\b", body))
            if ret_m:
                last = ret_m[-1]
                indent = last.group(1)
                insert = f"\n{indent}snapshot_night_start(state)  # v5v9b"
                new_body = body[:last.start()] + insert + body[last.start():]
                tsrc = tsrc[:m.start(1)] + new_body + tsrc[m.end(1):]
                print("OK: snapshot_night_start() chamado em end_day")
            else:
                print("AVISO: end_day sem return — hook não injetado")
        else:
            print("AVISO: end_day não casou — helper adicionado, hook não")
        shutil.copy2(tp, bkp / "turn.py")
        tp.write_text(tsrc, encoding="utf-8")
    else:
        print("[skip] turn.py já tem snapshot_night_start")

    # --- serialize.py ---
    sp = core / "serialize.py"
    if sp.is_file():
        ssrc = sp.read_text(encoding="utf-8")
        if "night_start_positions" in ssrc:
            print("[skip] serialize.py já menciona o campo")
        else:
            to = ("    # v5v9b\n"
                  "    try:\n"
                  "        out['night_start_positions'] = dict(getattr(state, 'night_start_positions', {}) or {})\n"
                  "    except Exception:\n"
                  "        pass\n")
            fr = ("    # v5v9b\n"
                  "    try:\n"
                  "        state.night_start_positions = dict(data.get('night_start_positions', {}) or {})\n"
                  "    except Exception:\n"
                  "        pass\n")
            changed = False
            m = re.search(r"(def state_to_dict\([^)]*\):\n)", ssrc)
            if m:
                ssrc = ssrc[:m.end()] + to + ssrc[m.end():]
                changed = True
            m = re.search(r"(def state_from_dict\([^)]*\):\n)", ssrc)
            if m:
                ssrc = ssrc[:m.end()] + fr + ssrc[m.end():]
                changed = True
            if changed:
                shutil.copy2(sp, bkp / "serialize.py")
                sp.write_text(ssrc, encoding="utf-8")
                print("OK: serialize.py atualizado")
            else:
                print("AVISO: state_to_dict/state_from_dict não casaram")
    else:
        print("AVISO: serialize.py não existe")

    # validação
    for f in (mp, tp, sp):
        if f.is_file():
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as ex:
                print(f"[ERRO] {f.name} quebrou: {ex}")
                return 1
    print(f"Backup: {bkp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())