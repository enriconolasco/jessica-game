"""v5v10g — Ainai (sem tocar _try_ainai_teleport) + Luide antes de declarar.

1. Ainai: detecta mudança de house comparando antes/depois de _try_ainai_teleport.
          Se caiu em casa já processada, chama _declarar_casa imediatamente.
2. Luide: chama _luide_janela_noturna ANTES de _declarar_casa (hoje só depois).

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
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
BKP = ROOT / "backups" / f"v5v10g_{TS}"
BKP.mkdir(parents=True, exist_ok=True)
print(f"ROOT: {ROOT}\nBackup: {BKP}\n")

MAIN = ROOT / "jessica" / "main.py"


# =========================================================================
# Ainai: sniff house antes/depois de _try_ainai_teleport
# =========================================================================
def fix_ainai():
    item = "ainai"
    src = MAIN.read_text(encoding="utf-8")
    if "# v5v10g ainai" in src:
        print(f"[skip {item}] já aplicado")
        return

    pat = re.compile(
        r"^([ \t]*)def _ainai_prompt_all\(state, all_pids\)[^:]*:[\s\S]*?"
        r"(?=^\1def |^\1class |\Z)",
        re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] _ainai_prompt_all não casou")
        return

    novo = '''def _ainai_prompt_all(state, all_pids, processed_houses=None):  # v5v10g ainai
    """v5v10g: se Ainai teleporta para casa já processada, reabre e declara."""
    if processed_houses is None:
        processed_houses = set()
    for pid in all_pids:
        player = get_player(state, pid)
        if not player.units:
            continue
        ainai_before = next((u for u in player.units
                             if isinstance(u, Hero) and u.is_alive()
                             and u.hero_id == "ainai"), None)
        house_before = ainai_before.house if ainai_before else None
        try:
            _try_ainai_teleport(state, player)
        except Exception as e:
            console.print(f"[red]Erro Ainai: {e}[/red]")
            continue
        ainai_after = next((u for u in player.units
                            if isinstance(u, Hero) and u.is_alive()
                            and u.hero_id == "ainai"), None)
        if ainai_after is None:
            continue
        house_after = ainai_after.house
        if house_before != house_after and house_after in processed_houses:
            console.print("[cyan]Ainai entrou em casa já processada. "
                          "Declara agora.[/cyan]")
            try:
                _declarar_casa(state, house_after, [pid])
            except Exception as e:
                console.print(f"[red]Erro declaração Ainai: {e}[/red]")
'''
    src = src[:m.start()] + novo + src[m.end():]

    # atualiza apenas as chamadas que vêm depois de _luide_janela_noturna(..., processed_houses)
    src = re.sub(
        r"(_luide_janela_noturna\(state, all_pids, processed_houses\)\n[ \t]+)"
        r"_ainai_prompt_all\(state, all_pids\)",
        r"\1_ainai_prompt_all(state, all_pids, processed_houses)",
        src)

    try:
        ast.parse(src)
    except SyntaxError as ex:
        print(f"[ERRO {item}] quebraria: {ex}")
        return
    shutil.copy2(MAIN, BKP / "main.py.ainai")
    MAIN.write_text(src, encoding="utf-8")
    print(f"[OK   {item}] Ainai reabre casa processada")


# =========================================================================
# Luide: chamar ANTES de _declarar_casa também
# =========================================================================
def fix_luide():
    item = "luide"
    src = MAIN.read_text(encoding="utf-8")
    if "# v5v10g luide" in src:
        print(f"[skip {item}] já aplicado")
        return

    old = (
        "        pids_here = _order_players_for_house(state, pids_here, house)\n"
        "        _declarar_casa(state, house, pids_here)\n"
        "        processed_houses.add(house)\n"
    )
    new = (
        "        pids_here = _order_players_for_house(state, pids_here, house)\n"
        "        # v5v10g luide: antes de qualquer unidade vampira declarar\n"
        "        _luide_janela_noturna(state, all_pids, processed_houses)\n"
        "        _declarar_casa(state, house, pids_here)\n"
        "        processed_houses.add(house)\n"
    )
    if old not in src:
        print(f"[AVISO {item}] bloco alvo não casou — verifique run_night_phase")
        return
    src = src.replace(old, new, 1)

    try:
        ast.parse(src)
    except SyntaxError as ex:
        print(f"[ERRO {item}] quebraria: {ex}")
        return
    shutil.copy2(MAIN, BKP / "main.py.luide")
    MAIN.write_text(src, encoding="utf-8")
    print(f"[OK   {item}] Luide chamado antes de cada casa")


def main():
    try:
        fix_ainai()
    except Exception as ex:
        print(f"[ERRO ainai]: {ex}")
    print()
    try:
        fix_luide()
    except Exception as ex:
        print(f"[ERRO luide]: {ex}")
    print()
    print(f"Backup: {BKP}")
    print("Rode: python tests\\run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())