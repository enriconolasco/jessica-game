"""v5v14 — desduplicação de main.py.

Regras:
- Alvos: TODOS_POVOS, _mostrar_povo_completo, _menu_povos, _luide_janela_noturna
- Heurística: mantém a versão que menciona `processed_houses` (caso especial
  do Luide, conforme handoff). Sem essa pista, mantém a ÚLTIMA do arquivo.
- Backup em backups/v5v14_dedup_<timestamp>/main.py
- Aborta se o resultado não compilar.

Uso:
  python fixes/apply_v5v14_dedup.py            # aplica
  python fixes/apply_v5v14_dedup.py --dry-run  # só mostra
"""
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path


TARGETS = ["TODOS_POVOS", "_mostrar_povo_completo", "_menu_povos", "_luide_janela_noturna"]


def find_root() -> Path:
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


def collect(src: str) -> dict[str, list[dict]]:
    tree = ast.parse(src)
    out: dict[str, list[dict]] = {}
    for node in tree.body:
        kind = name = None
        start, end = getattr(node, "lineno", None), getattr(node, "end_lineno", None)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind, name = "def", node.name
            if getattr(node, "decorator_list", None):
                start = min(start, min(d.lineno for d in node.decorator_list))
        elif isinstance(node, ast.ClassDef):
            kind, name = "class", node.name
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(
                        {"kind": "assign", "start": node.lineno, "end": node.end_lineno})
            continue
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.setdefault(node.target.id, []).append(
                {"kind": "annassign", "start": node.lineno, "end": node.end_lineno})
            continue
        else:
            continue
        out.setdefault(name, []).append({"kind": kind, "start": start, "end": end})
    return out


def pick_keeper(name: str, occs: list[dict], lines: list[str]) -> dict:
    if name == "_luide_janela_noturna":
        for o in occs:
            body = "\n".join(lines[o["start"] - 1:o["end"]])
            if "processed_houses" in body:
                return o
    return max(occs, key=lambda o: o["start"])  # último


def main():
    dry = "--dry-run" in sys.argv
    root = find_root()
    print(f"ROOT: {root}  (dry-run={dry})")
    main_path = root / "jessica" / "main.py"
    src = main_path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    entries = collect(src)

    to_remove: list[tuple[int, int, str]] = []
    for name in TARGETS:
        occs = entries.get(name, [])
        if len(occs) < 2:
            print(f"  [skip] {name}: {len(occs)}x")
            continue
        keep = pick_keeper(name, occs, lines)
        print(f"  [{name}] mantém linhas {keep['start']}..{keep['end']} ({keep['kind']})")
        for o in occs:
            if o is keep:
                continue
            s, e = o["start"], o["end"]
            if e < len(lines) and lines[e].strip() == "":
                e += 1  # come a linha em branco seguinte
            to_remove.append((s, e, f"{name} ({o['kind']})"))
            print(f"    remove linhas {s}..{e}")

    if not to_remove:
        print("Nada a fazer.")
        return 0

    remove_set = set()
    for s, e, _ in to_remove:
        remove_set.update(range(s, e + 1))
    new_lines = [ln for i, ln in enumerate(lines, 1) if i not in remove_set]
    new_src = "".join(new_lines)

    try:
        ast.parse(new_src)
    except SyntaxError as ex:
        print(f"[ERRO] resultado não compila: {ex}")
        return 1

    removed = len(lines) - len(new_lines)
    print(f"\nmain.py: {len(lines)} -> {len(new_lines)} linhas ({removed} removidas)")

    if dry:
        print("(dry-run — nada gravado)")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = root / "backups" / f"v5v14_dedup_{ts}"
    bkp.mkdir(parents=True, exist_ok=True)
    shutil.copy2(main_path, bkp / "main.py")
    main_path.write_text(new_src, encoding="utf-8")
    print(f"Backup: {bkp / 'main.py'}")
    print("Feito. Rode: python tests/run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())