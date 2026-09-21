"""Diagnóstico consolidado — 23 itens do bloco v5v10.

Uso:
  python fixes/diagnose_all.py > diag_all.txt
  type diag_all.txt

Só lê. Não modifica. Imprime por item:
  - arquivos onde aparece
  - assinatura + primeiras linhas da função relevante
  - greps de termos-chave
"""
import re
import sys
from pathlib import Path


# --------------------------------------------------------------------------- #
# infra
# --------------------------------------------------------------------------- #

def find_root() -> Path:
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


ROOT = find_root()
CORE = ROOT / "jessica" / "core"


def load(fname: str) -> str:
    p = (ROOT / "jessica" / fname) if fname == "main.py" else (CORE / fname)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


def has(src: str, needle: str) -> bool:
    return needle in src


def dump_fn(src: str, name: str, max_lines: int = 40, label: str | None = None):
    if not src:
        print(f"    [{name}] arquivo vazio")
        return
    pat = re.compile(
        rf"^([ \t]*)def {re.escape(name)}\([^)]*\)[^:]*:[\s\S]*?(?=^\1def |^\1class |\Z)",
        re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"    [{name}] NÃO ENCONTRADA")
        return
    body = m.group(0).splitlines()
    head = label or name
    print(f"    -- {head} ({len(body)} linhas) --")
    for ln in body[:max_lines]:
        print(f"      {ln}")
    if len(body) > max_lines:
        print(f"      ... (+{len(body) - max_lines} linhas)")


def grep(src: str, needles: list[str], label: str, limit: int = 30):
    if not src:
        return
    lines = src.splitlines()
    hits = []
    for i, ln in enumerate(lines, 1):
        low = ln.lower()
        if any(n.lower() in low for n in needles):
            hits.append((i, ln.rstrip()))
    print(f"    grep {label}: {len(hits)} hit(s)")
    for i, ln in hits[:limit]:
        print(f"      {i:5}: {ln}")
    if len(hits) > limit:
        print(f"      ... (+{len(hits) - limit})")


def header(n: str, title: str):
    print()
    print("=" * 74)
    print(f"# {n} — {title}")
    print("=" * 74)


# --------------------------------------------------------------------------- #
# cache dos arquivos
# --------------------------------------------------------------------------- #

SRC = {
    "main":       load("main.py"),
    "combat":     load("combat.py"),
    "peoples":    load("peoples.py"),
    "heroes":     load("heroes.py"),
    "spells":     load("spells.py"),
    "actions":    load("actions.py"),
    "turn":       load("turn.py"),
    "models":     load("models.py"),
    "artifacts":  load("artifacts.py"),
    "artifacts_effects": load("artifacts_effects.py"),
    "serialize":  load("serialize.py"),
    "constants":  load("constants.py"),
    "setup":      load("setup.py"),
    "rng":        load("rng.py"),
    "victory":    load("victory.py"),
    "state":      load("state.py"),
}


# --------------------------------------------------------------------------- #
# itens
# --------------------------------------------------------------------------- #

def item_00():
    header("00", "snapshot_night_start (fechado) — sanity")
    dump_fn(SRC["turn"], "snapshot_night_start", max_lines=20)
    print("    esperado: iterar list, sem .items()")
    ok = ".items()" not in (SRC["turn"].split("def snapshot_night_start")[1].split("\ndef ")[0]
                            if "def snapshot_night_start" in SRC["turn"] else "")
    print(f"    status: {'OK' if ok else 'AINDA COM BUG'}")


def item_01():
    header("01", "Vovó Gamba +1 dano GLOBAL (Orc)")
    for fname in ("peoples", "combat", "heroes", "actions", "turn"):
        grep(SRC[fname], ["vovo", "gamba"], f"{fname}.py")
    print()
    for name in ("apply_vovo_gamba", "vovo_gamba", "vovo_bonus",
                 "get_vovo_bonus", "_vovo_damage"):
        if f"def {name}" in SRC["peoples"]:
            dump_fn(SRC["peoples"], name, label=f"peoples.{name}")
    # onde attack/dano é calculado
    print()
    for name in ("resolve_attack", "_resolve_combat_round",
                 "compute_damage", "_compute_attack", "roll_damage"):
        if f"def {name}" in SRC["combat"]:
            dump_fn(SRC["combat"], name, max_lines=30, label=f"combat.{name}")


def item_02():
    header("02", "Auto-ataque proibido (espectro / tropa controlada / lobisomem)")
    grep(SRC["combat"], ["self", "auto", "mesmo", "atacante == alvo",
                         "attacker == target", "killer == victim"], "combat")
    grep(SRC["actions"], ["self", "auto", "mesmo alvo"], "actions")
    grep(SRC["peoples"], ["espectro", "espectros_pendentes", "almas",
                          "acorrentadas", "control"], "peoples")
    print()
    for name in ("resolve_attack", "_resolve_combat_round"):
        if f"def {name}" in SRC["combat"]:
            dump_fn(SRC["combat"], name, max_lines=35, label=f"combat.{name}")


def item_03():
    header("03", "Feitiço Lobisomem (Licantropo)")
    grep(SRC["spells"], ["licantropo", "lobisomem", "lobisomens"],
         "spells.py")
    grep(SRC["peoples"], ["licantropo", "lobisomem", "lupã", "lupa",
                          "cigana", "infectad"], "peoples.py")
    print()
    for name in ("cast_licantropo", "apply_licantropo", "licantropo"):
        if f"def {name}" in SRC["spells"]:
            dump_fn(SRC["spells"], name, label=f"spells.{name}")
        if f"def {name}" in SRC["peoples"]:
            dump_fn(SRC["peoples"], name, label=f"peoples.{name}")
    grep(SRC["combat"], ["lobisomem", "licantropo", "infectad"], "combat.py")
    print("    (esperado: transforma aliado; aplica dobro dano passiva; "
          "Lupã → resistência; Cigana → invisibilidade)")


def item_04():
    header("04", "Aiquara só à noite + #22 menu do especial")
    grep(SRC["heroes"], ["aiquara"], "heroes.py")
    grep(SRC["actions"], ["aiquara"], "actions.py")
    grep(SRC["peoples"], ["aiquara"], "peoples.py")
    grep(SRC["main"], ["aiquara"], "main.py")
    print()
    for name in ("aiquara_move_enemy", "aiquara_force_attack", "aiquara",
                 "_aiquara_dia", "_aiquara_noite"):
        if f"def {name}" in SRC["peoples"]:
            dump_fn(SRC["peoples"], name, label=f"peoples.{name}")
        if f"def {name}" in SRC["actions"]:
            dump_fn(SRC["actions"], name, label=f"actions.{name}")
        if f"def {name}" in SRC["main"]:
            dump_fn(SRC["main"], name, label=f"main.{name}")


def item_05():
    header("05", "UI 2x Pé Descalço persiste após expirar")
    grep(SRC["main"], ["pé descalço", "pe_descalco", "pes_descalco", "2x"],
         "main.py")
    grep(SRC["peoples"], ["descalço", "descalco", "pe_descalco",
                          "double_damage"], "peoples.py")
    grep(SRC["combat"], ["double_damage", "2x", "dobro"], "combat.py")
    grep(SRC["models"], ["double_damage"], "models.py")


def item_06():
    header("06", "Invulnerável (Q♥ Bênção) — flag + UI ★")
    grep(SRC["models"], ["invulnerav"], "models.py")
    grep(SRC["combat"], ["invulnerav"], "combat.py")
    grep(SRC["artifacts_effects"], ["invulnerav", "bencao", "bênção", "Q_H"],
         "artifacts_effects.py")
    grep(SRC["main"], ["invulnerav", "★"], "main.py")
    print()
    for name in ("on_play_Q_H", "play_Q_H", "bencao_natureza",
                 "aplicar_bencao", "apply_bencao"):
        if f"def {name}" in SRC["artifacts_effects"]:
            dump_fn(SRC["artifacts_effects"], name, label=f"artefato.{name}")


def item_07():
    header("07", "Musashi vida máxima persistente")
    grep(SRC["heroes"], ["musashi"], "heroes.py")
    grep(SRC["peoples"], ["musashi"], "peoples.py")
    grep(SRC["models"], ["musashi", "garoche_life_max_bonus"],
         "models.py (referência p/ paralelo)")
    grep(SRC["serialize"], ["musashi", "garoche"], "serialize.py")
    print()
    for name in ("on_musashi_kill", "apply_musashi", "musashi_bonus"):
        if f"def {name}" in SRC["peoples"]:
            dump_fn(SRC["peoples"], name, label=f"peoples.{name}")


def item_08():
    header("08", "Caroço/Zebum não andam no T1 (summon auto)")
    grep(SRC["peoples"], ["caroco", "caroço", "zebum"], "peoples.py")
    grep(SRC["actions"], ["caroco", "caroço", "zebum"], "actions.py")
    grep(SRC["main"], ["caroco", "caroço", "zebum"], "main.py")
    grep(SRC["models"], ["summon_turn", "invocado_turn", "caroco", "zebum"],
         "models.py")


def item_09():
    header("09", "Caroço — feitiço Cabaca Cheia (sem recarga, todos, log)")
    grep(SRC["spells"], ["cabaca", "cabaça", "caroco", "caroço"], "spells.py")
    grep(SRC["peoples"], ["cabaca", "cabaça", "caroco", "caroço"], "peoples.py")
    for name in ("cast_cabaca_cheia", "cabaça_cheia", "cabaca_cheia",
                 "caroco_cabaca", "efeito_cabaca"):
        if f"def {name}" in SRC["spells"]:
            dump_fn(SRC["spells"], name, label=f"spells.{name}")
        if f"def {name}" in SRC["peoples"]:
            dump_fn(SRC["peoples"], name, label=f"peoples.{name}")
        if f"def {name}" in SRC["main"]:
            dump_fn(SRC["main"], name, label=f"main.{name}")


def item_10():
    header("10", "Baoba-bá — invocar por magia só se foi escolhido")
    grep(SRC["peoples"], ["baoba", "baobá"], "peoples.py")
    grep(SRC["actions"], ["baoba", "baobá"], "actions.py")
    grep(SRC["main"], ["baoba", "baobá"], "main.py")
    grep(SRC["models"], ["baoba"], "models.py")


def item_11():
    header("11", "Mortos-Vivos — remover 'extra' do feitiço")
    grep(SRC["spells"], ["extra", "levantar", "mortos"], "spells.py")
    grep(SRC["main"], ["extra", "levantar"], "main.py")
    grep(SRC["peoples"], ["extra"], "peoples.py")


def item_12():
    header("12", "Luide Vampa — janela noturna (opções)")
    grep(SRC["main"], ["luide"], "main.py")
    grep(SRC["peoples"], ["luide"], "peoples.py")
    grep(SRC["turn"], ["luide"], "turn.py")
    print()
    if "def _luide_janela_noturna" in SRC["main"]:
        dump_fn(SRC["main"], "_luide_janela_noturna", max_lines=80)


def item_13():
    header("13", "Luna — prompt sim/não no início da noite")
    dump_fn(SRC["turn"], "_luna_return", max_lines=60)
    grep(SRC["turn"], ["luna"], "turn.py")
    grep(SRC["peoples"], ["luna"], "peoples.py")
    grep(SRC["main"], ["luna"], "main.py")


def item_14():
    header("14", "Ainai — entra na fila de ataque após teleporte")
    grep(SRC["turn"], ["ainai", "teleport"], "turn.py")
    grep(SRC["peoples"], ["ainai", "teleport"], "peoples.py")
    grep(SRC["main"], ["ainai"], "main.py")


def item_15():
    header("15", "Sonho Lúcido + Luna — aplicar artefatos múltiplos")
    grep(SRC["spells"], ["sonho", "lucido", "lúcido"], "spells.py")
    grep(SRC["main"], ["sonho", "lucido", "lúcido"], "main.py")
    grep(SRC["artifacts_effects"], ["sonho"], "artifacts_effects.py")
    print()
    for name in ("cast_sonho_lucido", "sonho_lucido", "_sonho_lucido"):
        if f"def {name}" in SRC["spells"]:
            dump_fn(SRC["spells"], name, max_lines=50, label=f"spells.{name}")
        if f"def {name}" in SRC["main"]:
            dump_fn(SRC["main"], name, max_lines=50, label=f"main.{name}")


def item_16():
    header("16", "HUD — avisar Lua Cheia se houver lobisomem")
    grep(SRC["main"], ["lua cheia", "lua_cheia", "luacheia"], "main.py")
    grep(SRC["peoples"], ["lua cheia", "lua_cheia", "apply_lua_cheia"],
         "peoples.py")
    grep(SRC["state"], ["lua"], "state.py")


def item_17():
    header("17", "Gnomos — apostas no início do TURNO + HUD corretas")
    grep(SRC["turn"], ["aposta", "bet", "realoc"], "turn.py")
    grep(SRC["peoples"], ["aposta", "bet", "realoc"], "peoples.py")
    grep(SRC["main"], ["aposta", "bet", "correct_bet"], "main.py")
    grep(SRC["models"], ["bet_", "correct_bets"], "models.py")


def item_18():
    header("18", "Caractere ao lado do nome de infectado (lobisomem)")
    grep(SRC["main"], ["infectad", "infectado"], "main.py")
    grep(SRC["models"], ["infectad"], "models.py")
    grep(SRC["peoples"], ["infectad"], "peoples.py")


def item_19():
    header("19", "Empalados/infectados — nome + jogador + povo")
    grep(SRC["main"], ["empalad", "infectad"], "main.py")
    grep(SRC["models"], ["empalados", "infectados"], "models.py")
    print()
    # procura função que renderiza o painel
    for name in ("_mostrar_empalados", "_mostrar_infectados",
                 "_painel_empalados", "_painel_infectados",
                 "_board_empalados"):
        if f"def {name}" in SRC["main"]:
            dump_fn(SRC["main"], name, max_lines=30)


def item_20():
    header("20", "Renomear tropas padrão: pequena/média/grande (todos povos)")
    grep(SRC["main"], ["pequena", "média", "media", "grande", "light",
                       "medium", "heavy"], "main.py")
    grep(SRC["constants"], ["TROOP", "LIGHT", "MEDIUM", "HEAVY", "pequena",
                            "media", "grande"], "constants.py")


def item_21():
    header("21", "Guarari — andar 2x permanentemente")
    grep(SRC["peoples"], ["guarari"], "peoples.py")
    grep(SRC["heroes"], ["guarari"], "heroes.py")
    grep(SRC["main"], ["guarari"], "main.py")
    grep(SRC["models"], ["guarari", "andar_duas_vezes"], "models.py")


def item_22():
    header("22", "Aiquara — especial no menu 4 (não no i)")
    grep(SRC["main"], ["aiquara"], "main.py")
    # mapeamento de teclas
    grep(SRC["main"], ["tecla", "key_", "ações", "especiais", "menu 4",
                       "'4'", '"4"'], "main.py")


def item_23():
    header("23", "Lupã vida máxima 6 (era 7)")
    grep(SRC["heroes"], ["lupã", "lupa"], "heroes.py")
    # mostra bloco do catálogo
    m = re.search(r"(Lup[aã][\s\S]{0,400})", SRC["heroes"], re.IGNORECASE)
    if m:
        print(m.group(0)[:600])


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

ITEMS = [
    item_00, item_01, item_02, item_03, item_04, item_05, item_06,
    item_07, item_08, item_09, item_10, item_11, item_12, item_13,
    item_14, item_15, item_16, item_17, item_18, item_19, item_20,
    item_21, item_22, item_23,
]


def main():
    print(f"ROOT: {ROOT}")
    for fn in ITEMS:
        try:
            fn()
        except Exception as ex:
            print(f"  [ERRO no bloco {fn.__name__}]: {ex}")
    print("\n=== FIM DO DIAGNÓSTICO ===")


if __name__ == "__main__":
    main()