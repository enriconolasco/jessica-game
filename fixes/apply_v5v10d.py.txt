"""v5v10d — corrige bug do v5v10c que quebrou cast_spell.

Bug: fix_09 injetou `if ...no_cooldown = True` ANTES do `else:` do if-elif
em cast_spell, quebrando o binding. Todos feitiços fora do chain caíam no
else e explodiam.

Fix:
1. Remove a injeção quebrada.
2. Reinsere no lugar certo (dentro do branch linhagem_ancestral).

Backup. Aborta se quebrar sintaxe."""
import ast
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


def main():
    root = find_root()
    ap = root / "jessica" / "core" / "actions.py"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = root / "backups" / f"v5v10d_{ts}"
    bkp.mkdir(parents=True, exist_ok=True)
    print(f"ROOT: {root}\nBackup: {bkp}\n")

    src = ap.read_text(encoding="utf-8")
    shutil.copy2(ap, bkp / "actions.py")

    # 1. remove a injeção quebrada (do v5v10c fix_09)
    bad = (
        "    # v5v10c #09: Linhagem em Caroço não tem recarga\n"
        "    if sp.spell_id == \"linhagem_ancestral\" and choice.get(\"hero_id\") == \"caroco\":\n"
        "        no_cooldown = True\n"
    )
    if bad in src:
        src = src.replace(bad, "", 1)
        print("OK: injeção quebrada removida")
    else:
        print("AVISO: injeção quebrada não encontrada — verifique se rodou apply_v5v10c")

    # 2. reinjeta no branch correto
    target = (
        "    elif sp.spell_id == \"linhagem_ancestral\":\n"
        "        _spell_linhagem_ancestral(state, player, choice)\n"
    )
    replacement = (
        "    elif sp.spell_id == \"linhagem_ancestral\":\n"
        "        _spell_linhagem_ancestral(state, player, choice)\n"
        "        if choice.get(\"hero_id\") == \"caroco\":\n"
        "            no_cooldown = True  # v5v10d\n"
    )
    if target in src:
        src = src.replace(target, replacement, 1)
        print("OK: no_cooldown do Caroço no branch correto")
    else:
        print("AVISO: branch linhagem_ancestral não casou")

    try:
        ast.parse(src)
    except SyntaxError as ex:
        print(f"[ERRO] actions.py quebraria: {ex}")
        return 1

    ap.write_text(src, encoding="utf-8")
    print("\nFeito. Rode: python tests\\run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())