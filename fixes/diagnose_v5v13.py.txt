"""Diagnóstico v5v13 — duplicação em main.py + estado dos testes.
Não modifica nada. Só lê e reporta."""
import ast
import subprocess
import sys
from pathlib import Path


def find_root() -> Path:
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


TARGETS = ["TODOS_POVOS", "_mostrar_povo_completo", "_menu_povos", "_luide_janela_noturna"]


def scan_top_level(src: str):
    tree = ast.parse(src)
    names: dict[str, list[dict]] = {}
    for node in tree.body:
        kind = name = None
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind, name = "def", node.name
            if getattr(node, "decorator_list", None):
                start = min(start, min(d.lineno for d in node.decorator_list))
        elif isinstance(node, ast.ClassDef):
            kind, name = "class", node.name
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.setdefault(t.id, []).append(
                        {"kind": "assign", "line": node.lineno, "end": node.end_lineno})
            continue
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.setdefault(node.target.id, []).append(
                {"kind": "annassign", "line": node.lineno, "end": node.end_lineno})
            continue
        else:
            continue
        names.setdefault(name, []).append({"kind": kind, "line": start, "end": end})
    return names


def main():
    root = find_root()
    print(f"ROOT: {root}")
    main_path = root / "jessica" / "main.py"
    src = main_path.read_text(encoding="utf-8")
    n_lines = src.count("\n") + 1
    names = scan_top_level(src)
    print(f"main.py: {n_lines} linhas, {len(names)} nomes top-level\n")

    dupes = {n: v for n, v in names.items() if len(v) > 1}
    print(f"== Duplicatas top-level: {len(dupes)} ==")
    for name, occs in sorted(dupes.items()):
        print(f"  {name}: {len(occs)}x")
        for o in occs:
            size = o['end'] - o['line'] + 1
            print(f"    - {o['kind']} linhas {o['line']}..{o['end']} ({size} linhas)")

    print("\n== Alvos específicos do handoff ==")
    for t in TARGETS:
        occs = names.get(t, [])
        status = "AUSENTE" if not occs else ("OK (única)" if len(occs) == 1 else f"DUPLICADA {len(occs)}x")
        print(f"  {t}: {status}")
        for o in occs:
            print(f"    - {o['kind']} linhas {o['line']}..{o['end']}")

    # checagem especial p/ luide
    print("\n== Checagem especial: _luide_janela_noturna menciona processed_houses? ==")
    lines = src.splitlines()
    for o in names.get("_luide_janela_noturna", []):
        body = "\n".join(lines[o["line"] - 1:o["end"]])
        flag = "SIM" if "processed_houses" in body else "NÃO"
        print(f"  linhas {o['line']}..{o['end']}: processed_houses = {flag}")

    print("\n== Rodando tests/run_all.py ==")
    rc = subprocess.call([sys.executable, str(root / "tests" / "run_all.py")])
    print(f"exit code: {rc}")


if __name__ == "__main__":
    main()