"""v5v10f — fecha o bloco.

1. test_valendar_luna: test_luna_returns_to_origin reescrito (retorno é via prompt
   na UI, não mais automático em end_day — você pediu).
2. Ainai: se teleporta pra casa já processada, declara imediatamente.

Backup. Aborta se quebrar sintaxe."""
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
BKP = ROOT / "backups" / f"v5v10f_{TS}"
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
# test_valendar_luna.py — test_luna_returns_to_origin
# =========================================================================
def fix_test_luna():
    item = "test_luna"
    tp = ROOT / "tests" / "test_valendar_luna.py"
    if not tp.is_file():
        print(f"[AVISO {item}] arquivo nao existe")
        return
    shutil.copy2(tp, BKP / tp.name)
    src = tp.read_text(encoding="utf-8")

    pat = re.compile(
        r"def test_luna_returns_to_origin\(\):[\s\S]*?(?=\ndef |\Z)",
        re.MULTILINE)
    if not pat.search(src):
        print(f"[AVISO {item}] test_luna_returns_to_origin nao casou")
        return

    novo = '''def test_luna_returns_to_origin():
    """Luna: guarda origem ao mover; retorno é via prompt na UI (v5v10f).

    O retorno automático em end_day foi removido por design. A UI
    (main.py:_try_luna_return) é quem pergunta ao jogador no início da Noite.
    """
    state = make_state()
    p4 = state.players[3]
    p4.city.magic = 10
    p4.chosen_hero_id = "luna"
    luna = summon_hero(state, 4)
    assert luna.hero_id == "luna"
    assert luna.house == "city_4"
    luna.has_moved_this_turn = False
    luna.moves_this_turn = 0
    move_unit(state, 4, luna.id, CENTER)
    assert luna.house == CENTER
    assert luna.statuses.get("luna_origin_house") == "city_4", (
        "Luna deveria ter guardado origem city_4"
    )
    print("OK  - Luna guardou origem (retorno via prompt na UI)")
'''
    src = pat.sub(novo, src, count=1)
    try:
        ast.parse(src)
    except SyntaxError as ex:
        print(f"[ERRO {item}] quebraria: {ex}")
        return
    tp.write_text(src, encoding="utf-8")
    _touched.add(tp)
    print(f"[OK   {item}] test_luna_returns_to_origin reescrito")


# =========================================================================
# Ainai: reabrir casa processada após teleporte
# =========================================================================
def fix_ainai():
    item = "ainai"
    mp = "main.py"
    src = read(mp)
    if "# v5v10f ainai" in src:
        print(f"[skip {item}] já aplicado")
        return

    # 1. _try_ainai_teleport retorna destino (str) ou None
    pat = re.compile(
        r"^([ \t]*)def _try_ainai_teleport\(state, player\)[^:]*:[\s\S]*?"
        r"(?=^\1def |^\1class |\Z)",
        re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] _try_ainai_teleport nao casou")
        return
    old_body = m.group(0)
    # adiciona return destino nos pontos de sucesso
    new_body = old_body
    # return None nos caminhos iniciais de falha (se ainda não tem)
    new_body = new_body.replace(
        "if ainai is None:\n        return",
        "if ainai is None:\n        return None")
    new_body = new_body.replace(
        'if ainai.statuses.get("ainai_used_turn") == state.turn:\n        return',
        'if ainai.statuses.get("ainai_used_turn") == state.turn:\n        return None')
    # o return final (depois de mover)
    new_body = new_body.replace(
        'console.print(f"[green]Ainai teleportou para {house_short(state, destino)} (+1 Magia).[/green]")',
        'console.print(f"[green]Ainai teleportou para {house_short(state, destino)} (+1 Magia).[/green]")\n'
        '    return destino  # v5v10f ainai')
    # caso não teleporte
    new_body = new_body.replace(
        'idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)\n    if idx == 0:\n        return',
        'idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)\n    if idx == 0:\n        return None')
    if new_body == old_body:
        print(f"[AVISO {item}] nenhuma substituicao efetiva em _try_ainai_teleport")
        return
    src = src[:m.start()] + new_body + src[m.end():]

    # 2. _ainai_prompt_all aceita processed_houses e reabre se necessario
    pat2 = re.compile(
        r"^([ \t]*)def _ainai_prompt_all\(state, all_pids\)[^:]*:[\s\S]*?"
        r"(?=^\1def |^\1class |\Z)",
        re.MULTILINE)
    m2 = pat2.search(src)
    if not m2:
        print(f"[AVISO {item}] _ainai_prompt_all nao casou")
        return
    novo_prompt = '''def _ainai_prompt_all(state, all_pids, processed_houses=None):  # v5v10f ainai
    if processed_houses is None:
        processed_houses = set()
    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
            destino = _try_ainai_teleport(state, player)
            if destino and destino in processed_houses:
                console.print(
                    f"[cyan]Ainai entrou em casa ja processada. "
                    f"Declara agora.[/cyan]")
                try:
                    _declarar_casa(state, destino, [pid])
                except Exception as e:
                    console.print(f"[red]Erro declaracao Ainai: {e}[/red]")
'''
    src = src[:m2.start()] + novo_prompt + src[m2.end():]

    # 3. atualizar chamadas (2 pontos no loop + 1 antes + 1 depois)
    # A chamada dentro do loop passa processed_houses
    src = re.sub(
        r"(_declarar_casa\(state, house, pids_here\)\n\s*processed_houses\.add\(house\)\n\s*# Luide entre casas\n\s*_luide_janela_noturna\(state, all_pids, processed_houses\)\n\s*)_ainai_prompt_all\(state, all_pids\)",
        r"\1_ainai_prompt_all(state, all_pids, processed_houses)",
        src, count=1)
    # A janela final
    src = re.sub(
        r"(_luide_janela_noturna\(state, all_pids, processed_houses\)\n\s*)_ainai_prompt_all\(state, all_pids\)\n\ndef show_victory",
        r"\1_ainai_prompt_all(state, all_pids, processed_houses)\n\ndef show_victory",
        src, count=1)

    try:
        ast.parse(src)
    except SyntaxError as ex:
        print(f"[ERRO {item}] quebraria: {ex}")
        return
    write(mp, src, item)
    print(f"[OK   {item}] Ainai reabre casa processada")


# =========================================================================
# runner
# =========================================================================
def main():
    try:
        fix_test_luna()
    except Exception as ex:
        print(f"[ERRO test_luna]: {ex}")
    print()
    try:
        fix_ainai()
    except Exception as ex:
        print(f"[ERRO ainai]: {ex}")
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