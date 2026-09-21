"""Diagnóstico v5v9 — alvos de Miyamoto persistente e night_start_positions.
Só inspeciona; não modifica."""
import re
from pathlib import Path


def find_root() -> Path:
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


CHECKS = [
    ("models.py",   "class Player",              "dataclass do jogador"),
    ("models.py",   "class GameState",           "dataclass do estado"),
    ("models.py",   "miyamoto_life_max_bonus",   "campo v5v9a (deve estar ausente)"),
    ("models.py",   "night_start_positions",     "campo v5v9b (deve estar ausente)"),
    ("models.py",   "from dataclasses import",   "import de field()"),
    ("heroes.py",   "Miyamoto",                  "definição do herói"),
    ("peoples.py",  "def on_unit_killed_by",     "hook de morte"),
    ("peoples.py",  "Miyamoto",                  "referências"),
    ("combat.py",   "Miyamoto",                  "referências"),
    ("combat.py",   "night_start",               "referências"),
    ("turn.py",     "def start_turn",            "início de turno"),
    ("turn.py",     "def end_day",               "fim do dia"),
    ("turn.py",     "def end_turn",              "fim de turno"),
    ("turn.py",     "night",                     "menções à noite"),
    ("serialize.py","def state_to_dict",         "save"),
    ("serialize.py","def state_from_dict",       "load"),
    ("serialize.py","miyamoto",                  "persistência (deve estar ausente)"),
    ("serialize.py","night_start",               "persistência (deve estar ausente)"),
]


def dump_class(src: str, cls: str, max_chars: int = 3000):
    m = re.search(rf"class {cls}\b[\s\S]*?(?=\nclass |\Z)", src)
    if m:
        print(m.group(0)[:max_chars])
        if len(m.group(0)) > max_chars:
            print(f"  ... ({len(m.group(0)) - max_chars} chars cortados)")


def main():
    root = find_root()
    print(f"ROOT: {root}")
    core = root / "jessica" / "core"

    print("\n== Presença dos alvos ==")
    for fname, needle, desc in CHECKS:
        p = core / fname
        if not p.is_file():
            print(f"  [FALTA] {fname}")
            continue
        text = p.read_text(encoding="utf-8")
        c = text.count(needle)
        flag = "OK " if c else "—  "
        print(f"  [{flag}] {fname}: {needle!r} x{c}  ({desc})")

    mp = (core / "models.py").read_text(encoding="utf-8")
    print("\n== class Player ==")
    dump_class(mp, "Player")
    print("\n== class GameState ==")
    dump_class(mp, "GameState")

    pp = (core / "peoples.py").read_text(encoding="utf-8")
    print("\n== assinatura de on_unit_killed_by ==")
    m = re.search(r"def on_unit_killed_by\([^)]*\)[\s\S]{0,400}", pp)
    print(m.group(0) if m else "  (não achei)")

    print("\n== turn.py: onde aparece 'night' ==")
    tp = (core / "turn.py").read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(tp, 1):
        if "night" in ln.lower():
            print(f"  {i:4}: {ln.rstrip()}")


if __name__ == "__main__":
    main()