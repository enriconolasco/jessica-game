"""v5v10e — fixes pontuais.

#06 Invulnerável: _apply_defense passa a checar status da unidade (Cabaca Cheia)
                  além do flag de Player.
#17 HUD Gnomos: show_hud mostra correct_bets quando há jogador gnomo.

Backup por arquivo. Aborta se quebrar sintaxe."""
import ast
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def find_root():
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


ROOT = find_root()
CORE = ROOT / "jessica" / "core"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
BKP = ROOT / "backups" / f"v5v10e_{TS}"
BKP.mkdir(parents=True, exist_ok=True)
print(f"ROOT: {ROOT}\nBackup: {BKP}\n")

_touched: set[Path] = set()


def read(fname: str) -> str:
    p = (ROOT / "jessica" / fname) if fname == "main.py" else (CORE / fname)
    return p.read_text(encoding="utf-8")


def write(fname: str, src: str, item: str):
    p = (ROOT / "jessica" / fname) if fname == "main.py" else (CORE / fname)
    dst = BKP / f"{p.name}.{item}"
    if not dst.exists():
        shutil.copy2(p, dst)
    p.write_text(src, encoding="utf-8")
    _touched.add(p)


# =========================================================================
# #06 — invulnerável via status de unidade
# =========================================================================
def fix_06():
    item = "06_invulneravel"
    cp = "combat.py"
    src = read(cp)
    if "# v5v10e #06" in src:
        print(f"[skip {item}] já aplicado")
        return
    old = (
        "    p = get_player(state, defender.owner_id)\n"
        "    if p.invulnerable_until_end_turn:\n"
        "        notes.append(\"invulneravel -> 0\")\n"
        "        return 0, notes\n"
    )
    new = (
        "    p = get_player(state, defender.owner_id)\n"
        "    if p.invulnerable_until_end_turn:\n"
        "        notes.append(\"invulneravel -> 0\")\n"
        "        return 0, notes\n"
        "    # v5v10e #06: Cabaca Cheia marca no status da unidade\n"
        "    if defender.statuses.get(\"invulneravel_until_turn\", -1) >= state.turn:\n"
        "        notes.append(\"invulneravel -> 0\")\n"
        "        return 0, notes\n"
    )
    if old not in src:
        print(f"[AVISO {item}] bloco de invulneravel nao casou em _apply_defense")
        return
    src = src.replace(old, new, 1)
    write(cp, src, item)
    print(f"[OK   {item}] _apply_defense checa status da unidade")


# =========================================================================
# #17 — HUD de Gnomos com correct_bets
# =========================================================================
def fix_17():
    item = "17_hud_gnomos"
    mp = "main.py"
    src = read(mp)
    if "# v5v10e #17" in src:
        print(f"[skip {item}] já aplicado")
        return
    pat = re.compile(r"(def show_hud\([^)]*\)[^:]*:\n)", re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] show_hud nao encontrada")
        return
    inj = (
        "    # v5v10e #17: apostas corretas de Gnomos\n"
        "    for _p in state.players:\n"
        "        if _p.people == \"gnomos_duendes\" and _p.city.is_alive():\n"
        "            console.print(f\"  [cyan]{_p.name}: apostas corretas = {_p.correct_bets}[/cyan]\")\n"
    )
    src = src[:m.end()] + inj + src[m.end():]
    write(mp, src, item)
    print(f"[OK   {item}] correct_bets injetado em show_hud")


STEPS = [fix_06, fix_17]


def main():
    for fn in STEPS:
        try:
            fn()
        except Exception as ex:
            print(f"[ERRO {fn.__name__}]: {ex}")
        print()
    print("=" * 70)
    ok = True
    for p in sorted(_touched):
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print(f"  OK  {p.relative_to(ROOT)}")
        except SyntaxError as ex:
            print(f"  ERRO {p.relative_to(ROOT)}: {ex}")
            ok = False
    if not ok:
        return 1
    print(f"\nBackup: {BKP}\nRode: python tests\\run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())