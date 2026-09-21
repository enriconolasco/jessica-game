"""v5v10c — segunda leva de fixes.

Cobre:
  #03 Licantropo: aplica resist da Lupã e invis da Cigana
  #09 Cabaca Cheia: rola por Caroço, log descritivo, sem recarga
  #11 Remover 'extra' do levantamento MV (2 pontos em main.py)
  #15 Sonho Lúcido: detecta cartas que precisam escolha (não joga silenciosamente)
  #16 HUD Lua Cheia: injeta em show_hud
  #20 Renomear tropas: 'Tropa pequena/média/grande'

Backup por arquivo, por item. Aborta se quebrar sintaxe."""
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
BKP = ROOT / "backups" / f"v5v10c_{TS}"
BKP.mkdir(parents=True, exist_ok=True)
print(f"ROOT: {ROOT}\nBackup: {BKP}\n")

_touched: set[Path] = set()


def _path(fname: str) -> Path:
    return (ROOT / "jessica" / fname) if fname == "main.py" else (CORE / fname)


def read(fname: str) -> str:
    return _path(fname).read_text(encoding="utf-8")


def write(fname: str, src: str, item: str):
    p = _path(fname)
    dst = BKP / f"{p.name}.{item}"
    if not dst.exists():
        shutil.copy2(p, dst)
    p.write_text(src, encoding="utf-8")
    _touched.add(p)


def func_pat(name: str):
    return re.compile(
        rf"^([ \t]*)def {re.escape(name)}\([^)]*\)[^:]*:[\s\S]*?(?=^\1def |^\1class |\Z)",
        re.MULTILINE)


def replace_func(src: str, name: str, new_body: str) -> tuple[str, bool]:
    pat = func_pat(name)
    if not pat.search(src):
        return src, False
    return pat.sub(new_body.rstrip() + "\n", src, count=1), True


# =========================================================================
# #03 Licantropo — aplica buffs de Lupã / Cigana ao transformado
# =========================================================================
def fix_03():
    item = "03_licantropo"
    ap = "actions.py"
    src = read(ap)
    novo = '''def _spell_licantropo(state, player, choice):
    tid = choice.get("unit_id")
    if not tid:
        raise ActionError("Precisa alvo.")
    t = next((u for u in player.units if u.id == tid and u.is_alive()), None)
    if t is None:
        raise ActionError("Alvo nao encontrado.")
    t.statuses["lobisomem_until_turn"] = state.turn
    # Buffs derivados dos herois Lobisomens vivos (v5v10c)
    has_lupa = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "lupa_lider"
                   for u in player.units)
    has_cigana = any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "cigana"
                     for u in player.units)
    if has_lupa:
        t.resistance_stacks += 1
        t.statuses["lupa_resist_until_turn"] = state.turn
    if has_cigana:
        t.statuses["invisivel_until_turn"] = state.turn
    log(state, f"{player.name}: {t.id} virou lobisomem (dobro de dano).")
    if has_lupa:
        log(state, f"  +1 Resistencia (Lupa).")
    if has_cigana:
        log(state, f"  Invisivel (Cigana).")
'''
    src, ok = replace_func(src, "_spell_licantropo", novo)
    if ok:
        write(ap, src, item)
        print(f"[OK   {item}] _spell_licantropo reescrito")
    else:
        print(f"[AVISO {item}] _spell_licantropo não casou")


# =========================================================================
# #09 Cabaca Cheia — rola por Caroço, log descritivo, sem recarga
# =========================================================================
def fix_09():
    item = "09_cabaca"
    ap = "actions.py"
    src = read(ap)

    nova_cabaca = '''def _cabaca_cheia(state, player):
    carocos = [u for u in player.units
               if isinstance(u, Hero) and u.is_alive() and u.hero_id == "caroco"]
    alvos = carocos if carocos else [None]
    nomes = {1: "Invulneravel (★)", 2: "+1 movimento", 3: "+1 Ouro", 4: "+1 Magia"}
    for c in alvos:
        r = state.rng.randint(1, 4)
        rotulo = f" (Caroço {c.id})" if c is not None else ""
        log(state, f"[ROLL] Cabaca Cheia{rotulo}: 1d4 = {r} -> {nomes[r]}")
        if r == 1:
            for u in player.units:
                if u.is_alive():
                    u.statuses["invulneravel_until_turn"] = state.turn
        elif r == 2:
            for u in player.units:
                if u.is_alive():
                    u.max_moves_this_turn += 1
                    u.has_moved_this_turn = False
        elif r == 3:
            player.city.gold += 1
        elif r == 4:
            player.city.magic += 1
'''
    src, ok = replace_func(src, "_cabaca_cheia", nova_cabaca)
    if not ok:
        print(f"[AVISO {item}] _cabaca_cheia não casou")
        return

    # sem recarga: adiciona flag no cast_spell quando Linhagem Ancestral -> caroco
    anchor = "    else:\n        raise ActionError(f\"Feitico {sp.spell_id} sem implementacao.\")"
    if anchor in src and "# v5v10c #09" not in src:
        inject = (
            "    # v5v10c #09: Linhagem em Caroço não tem recarga\n"
            "    if sp.spell_id == \"linhagem_ancestral\" and choice.get(\"hero_id\") == \"caroco\":\n"
            "        no_cooldown = True\n"
        )
        src = src.replace(anchor, inject + anchor, 1)
        print(f"[OK   {item}] _cabaca_cheia reescrito + no_cooldown")
    else:
        print(f"[OK   {item}] _cabaca_cheia reescrito (no_cooldown: âncora não casou, aplique manual)")

    write(ap, src, item)


# =========================================================================
# #11 Remover 'extra' do levantamento MV (2 pontos em main.py)
# =========================================================================
def fix_11():
    item = "11_mv_sem_extra"
    mp = "main.py"
    src = read(mp)
    old = 'labels = ["light", "medium", "heavy", "extra", "ghoul", "esqueleto"]'
    new = 'labels = ["light", "medium", "heavy", "ghoul", "esqueleto"]  # v5v10c #11'
    n = src.count(old)
    if n == 0:
        print(f"[skip {item}] já aplicado ou padrão ausente")
        return
    src = src.replace(old, new)
    write(mp, src, item)
    print(f"[OK   {item}] {n} ocorrência(s) alterada(s)")


# =========================================================================
# #15 Sonho Lúcido — detecta cartas que precisam escolha
# =========================================================================
def fix_15():
    item = "15_sonho_lucido"
    ap = "actions.py"
    src = read(ap)
    if "# v5v10c #15" in src:
        print(f"[skip {item}] já aplicado")
        return
    old = (
        "            for cid in list(cards):\n"
        "                new_card = peoples.sonho_lucido_flip(cid)\n"
        "                if new_card == cid:\n"
        "                    log(state, f\"Sonho Lucido: {card_display(cid)} nao mudou de naipe.\")\n"
        "                    continue\n"
        "                player.hand.remove(cid)\n"
        "                player.hand.append(new_card)\n"
        "                log(state, f\"Sonho Lucido: {card_display(cid)} -> {card_display(new_card)}.\")\n"
        "                try:\n"
        "                    play_artifact(state, player.id, new_card)\n"
        "                    log(state, f\"  jogado: {card_display(new_card)}.\")\n"
        "                except ActionError as e:\n"
        "                    player.hand.remove(new_card)\n"
        "                    player.hand.append(cid)\n"
        "                    log(state, f\"  {card_display(new_card)} nao jogado: {e}\")"
    )
    new = (
        "            from . import artifacts_effects as _ae  # v5v10c #15\n"
        "            for cid in list(cards):\n"
        "                new_card = peoples.sonho_lucido_flip(cid)\n"
        "                if new_card == cid:\n"
        "                    log(state, f\"Sonho Lucido: {card_display(cid)} nao mudou de naipe.\")\n"
        "                    continue\n"
        "                player.hand.remove(cid)\n"
        "                player.hand.append(new_card)\n"
        "                log(state, f\"Sonho Lucido: {card_display(cid)} -> {card_display(new_card)}.\")\n"
        "                if _ae.needs_choice(new_card):\n"
        "                    log(state, f\"  {card_display(new_card)} precisa de escolha: ficou na mao.\")\n"
        "                    continue\n"
        "                try:\n"
        "                    play_artifact(state, player.id, new_card)\n"
        "                    log(state, f\"  jogado: {card_display(new_card)}.\")\n"
        "                except ActionError as e:\n"
        "                    player.hand.remove(new_card)\n"
        "                    player.hand.append(cid)\n"
        "                    log(state, f\"  {card_display(new_card)} nao jogado: {e}\")"
    )
    if old not in src:
        print(f"[AVISO {item}] bloco original não casou — snippet mudou")
        return
    src = src.replace(old, new, 1)
    write(ap, src, item)
    print(f"[OK   {item}] needs_choice checado antes de play_artifact")


# =========================================================================
# #16 HUD avisa Lua Cheia (função correta: show_hud)
# =========================================================================
def fix_16():
    item = "16_hud_lua_cheia"
    mp = "main.py"
    src = read(mp)
    if "# v5v10c #16" in src:
        print(f"[skip {item}] já aplicado")
        return
    pat = re.compile(r"(def show_hud\([^)]*\)[^:]*:\n)", re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] show_hud não encontrada")
        return
    inj = (
        "    # v5v10c #16: aviso de Lua Cheia (só se houver lobisomem no jogo)\n"
        "    try:\n"
        "        _tem_lobo = any(p.people == \"lobisomens\" and p.city.is_alive()\n"
        "                        for p in state.players)\n"
        "        if _tem_lobo:\n"
        "            from .core import peoples as _ppl\n"
        "            for _p in state.players:\n"
        "                if _p.people == \"lobisomens\" and _ppl.is_lua_cheia(state, _p.id):\n"
        "                    console.print(\"[bold yellow]*** LUA CHEIA ***[/bold yellow]\")\n"
        "                    break\n"
        "    except Exception:\n"
        "        pass\n"
    )
    src = src[:m.end()] + inj + src[m.end():]
    write(mp, src, item)
    print(f"[OK   {item}] aviso de Lua Cheia injetado em show_hud")


# =========================================================================
# #20 Renomear tropas: 'Tropa pequena/média/grande'
# =========================================================================
def fix_20():
    item = "20_tropa_rename"
    mp = "main.py"
    src = read(mp)
    # bloco dict de nomes
    old = (
        '    "light": "pequena",\n'
        '    "medium": "media",\n'
        '    "heavy": "grande",'
    )
    new = (
        '    "light": "Tropa pequena",   # v5v10c #20\n'
        '    "medium": "Tropa média",\n'
        '    "heavy": "Tropa grande",'
    )
    if old in src:
        src = src.replace(old, new, 1)
        write(mp, src, item)
        print(f"[OK   {item}] dict de nomes renomeado")
    else:
        # tenta variante sem vírgula no último
        old2 = (
            '    "light": "pequena",\n'
            '    "medium": "media",\n'
            '    "heavy": "grande",\n'
        )
        new2 = (
            '    "light": "Tropa pequena",   # v5v10c #20\n'
            '    "medium": "Tropa média",\n'
            '    "heavy": "Tropa grande",\n'
        )
        if old2 in src:
            src = src.replace(old2, new2, 1)
            write(mp, src, item)
            print(f"[OK   {item}] dict de nomes renomeado (variante 2)")
        else:
            print(f"[AVISO {item}] dict de nomes não casou — verifique main.py:197-199")


# =========================================================================
# runner
# =========================================================================
STEPS = [fix_03, fix_09, fix_11, fix_15, fix_16, fix_20]


def main():
    for fn in STEPS:
        try:
            fn()
        except Exception as ex:
            print(f"[ERRO {fn.__name__}]: {ex}")
        print()

    print("=" * 70)
    print("Validação de sintaxe:")
    ok = True
    for p in sorted(_touched):
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print(f"  OK  {p.relative_to(ROOT)}")
        except SyntaxError as ex:
            print(f"  ERRO {p.relative_to(ROOT)}: {ex}")
            ok = False
    if not ok:
        print("\n>>> Algum arquivo quebrou. Restaure do backup antes de rodar testes.")
        return 1
    print(f"\nArquivos alterados: {len(_touched)}")
    print(f"Backup: {BKP}")
    print("Rode: python tests\\run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())