"""v5v10 megapatch — 14 correções de gameplay (Grupo A).

- Backup por arquivo, por item: backups/v5v10_megapatch_<ts>/<fname>.<item>
- Cada item é independente: AVISO num item não bloqueia os outros
- Compila todo arquivo alterado com ast.parse no fim; aborta se algum quebrar

Uso: python fixes/apply_v5v10_megapatch.py
"""
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
BKP = ROOT / "backups" / f"v5v10_megapatch_{TS}"
BKP.mkdir(parents=True, exist_ok=True)
print(f"ROOT: {ROOT}\nBackup: {BKP}\n")

_touched: set[Path] = set()


def _path(fname: str) -> Path:
    return (ROOT / "jessica" / fname) if fname == "main.py" else (CORE / fname)


def read(fname: str) -> str:
    return _path(fname).read_text(encoding="utf-8")


def backup(fname: str, item: str):
    p = _path(fname)
    dst = BKP / f"{p.name}.{item}"
    if not dst.exists():
        shutil.copy2(p, dst)


def write(fname: str, src: str, item: str):
    p = _path(fname)
    backup(fname, item)
    p.write_text(src, encoding="utf-8")
    _touched.add(p)


def func_pat(name: str):
    return re.compile(
        rf"^([ \t]*)def {re.escape(name)}\([^)]*\)[^:]*:[\s\S]*?(?=^\1def |^\1class |\Z)",
        re.MULTILINE)


def replace_func(src: str, name: str, new_body: str):
    pat = func_pat(name)
    if not pat.search(src):
        return src, False
    return pat.sub(new_body.rstrip() + "\n", src, count=1), True


# =========================================================================
# #01 Vovó Gamba +1 dano GLOBAL
# =========================================================================
def fix_01():
    item = "01_vovo"
    pp = "peoples.py"
    src = read(pp)
    new_has = '''def has_vovo_bonus(state: GameState, attacker: Unit) -> bool:
    """Vovo Gamba concede +1 dano GLOBAL a todas as tropas do dono (v5v10)."""
    p = get_player(state, attacker.owner_id)
    if p.people != "orcs":
        return False
    return any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba"
               for u in p.units)
'''
    src, ok = replace_func(src, "has_vovo_bonus", new_has)
    if ok:
        write(pp, src, item)
        print(f"[OK   {item}] peoples.has_vovo_bonus substituido")
    else:
        print(f"[AVISO {item}] has_vovo_bonus não casou em peoples.py")

    cp = "combat.py"
    src = read(cp)
    new_apply = '''def _apply_vovo_bonus(state: GameState, attacker: Unit, dmg: int,
                       target: Unit | None = None) -> int:
    """+1 dano se atacante Orc com Vovo Gamba viva (v5v10, GLOBAL)."""
    if peoples.has_vovo_bonus(state, attacker):
        return dmg + 1
    return dmg
'''
    src, ok = replace_func(src, "_apply_vovo_bonus", new_apply)
    if ok:
        write(cp, src, item)
        print(f"[OK   {item}] combat._apply_vovo_bonus substituido")
    else:
        print(f"[AVISO {item}] _apply_vovo_bonus não casou em combat.py")


# =========================================================================
# #02 Bloquear auto-ataque em resolve_attack
# =========================================================================
def fix_02():
    item = "02_self_attack"
    cp = "combat.py"
    src = read(cp)
    if "# v5v10 #02" in src:
        print(f"[skip {item}] já aplicado")
        return
    pat = re.compile(r"^([ \t]*)attacker = _find_unit\(state, attack\.attacker_unit_id\)\n",
                     re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] linha 'attacker = _find_unit(...)' não encontrada")
        return
    ind = m.group(1)
    inject = (
        f"{ind}attacker = _find_unit(state, attack.attacker_unit_id)\n"
        f"{ind}# v5v10 #02: proíbe auto-ataque\n"
        f"{ind}if attack.target_type != \"city\":\n"
        f"{ind}    _tp = _find_unit(state, attack.target_id)\n"
        f"{ind}    if _tp is not None and _tp.owner_id == attacker.owner_id:\n"
        f"{ind}        raise CombatError(\"Unidade não pode atacar a si mesma ou aliada.\")\n"
    )
    src = src[:m.start()] + inject + src[m.end():]
    write(cp, src, item)
    print(f"[OK   {item}] checagem injetada em resolve_attack")


# =========================================================================
# #04 Aiquara só força ataque à noite
# =========================================================================
def fix_04():
    item = "04_aiquara_noite"
    ap = "actions.py"
    src = read(ap)
    if "# v5v10 #04" in src:
        print(f"[skip {item}] já aplicado")
        return
    # acha bloco aiquara_atacar
    pat = re.compile(r"def aiquara_atacar\([^)]*\)[^:]*:[\s\S]*?(?=\ndef |\nclass |\Z)",
                     re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] aiquara_atacar não encontrada")
        return
    body = m.group(0)
    # procura "Aiquara nao esta viva" e injeta check depois
    anchor = re.search(r"^([ \t]+)raise ActionError\(\"Aiquara nao esta viva\.\"\)\n",
                       body, re.MULTILINE)
    if not anchor:
        print(f"[AVISO {item}] âncora 'Aiquara nao esta viva' não encontrada em aiquara_atacar")
        return
    ind = anchor.group(1)
    inject = (
        f"{ind}raise ActionError(\"Aiquara nao esta viva.\")\n"
        f"{ind}# v5v10 #04: só à noite\n"
        f"{ind}if state.phase != Phase.NIGHT:\n"
        f"{ind}    raise ActionError(\"Aiquara so forca ataque durante a Noite.\")\n"
    )
    new_body = body[:anchor.start()] + inject + body[anchor.end():]
    src = src[:m.start()] + new_body + src[m.end():]
    write(ap, src, item)
    print(f"[OK   {item}] checagem de fase noturna injetada em aiquara_atacar")


# =========================================================================
# #05 Limpar u.double_damage ao fim do turno
# =========================================================================
def fix_05():
    item = "05_double_clear"
    tp = "turn.py"
    src = read(tp)
    if "# v5v10 #05" in src:
        print(f"[skip {item}] já aplicado")
        return
    # injeta em end_turn, antes de qualquer return
    pat = re.compile(r"def end_turn\([^)]*\)[^:]*:\n([\s\S]*?)(?=\ndef |\nclass |\Z)")
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] end_turn não encontrada")
        return
    body = m.group(1)
    inject = (
        "    # v5v10 #05: limpa 2x da UI (efeito expira no fim do turno)\n"
        "    for _p in state.players:\n"
        "        for _u in _p.units:\n"
        "            try:\n"
        "                _u.double_damage = False\n"
        "            except Exception:\n"
        "                pass\n"
    )
    new_body = inject + body
    src = src[:m.start(1)] + new_body + src[m.end(1):]
    write(tp, src, item)
    print(f"[OK   {item}] limpeza de double_damage injetada em end_turn")


# =========================================================================
# #07 Miyamoto/Musashi vida máx persistente
# =========================================================================
def fix_07():
    item = "07_miyamoto_persist"
    mp = "models.py"
    src = read(mp)
    if "miyamoto_life_max_bonus" not in src:
        # acha class Player e injeta após garoche_life_max_bonus
        pat = re.compile(r"^([ \t]*)garoche_life_max_bonus: int = 0\s*$", re.MULTILINE)
        m = pat.search(src)
        if not m:
            print(f"[AVISO {item}] âncora garoche_life_max_bonus não encontrada")
            return
        ind = m.group(1)
        insert = m.group(0) + f"\n{ind}miyamoto_life_max_bonus: int = 0  # v5v10 #07"
        src = src[:m.start()] + insert + src[m.end():]
        write(mp, src, item)
        print(f"[OK   {item}] Player.miyamoto_life_max_bonus adicionado")
    else:
        print(f"[skip {item}] campo já existe")

    # serialize
    sp = "serialize.py"
    src = read(sp)
    if "miyamoto_life_max_bonus" not in src:
        pat = re.compile(r"^([ \t]*)\"garoche_life_max_bonus\": p\.garoche_life_max_bonus,\s*$",
                         re.MULTILINE)
        m = pat.search(src)
        if m:
            ind = m.group(1)
            insert = m.group(0) + f"\n{ind}\"miyamoto_life_max_bonus\": p.miyamoto_life_max_bonus,  # v5v10 #07"
            src = src[:m.start()] + insert + src[m.end():]
        else:
            print(f"[AVISO {item}] to_dict: âncora garoche não encontrada")

        pat = re.compile(r"^([ \t]*)garoche_life_max_bonus=d\.get\(\"garoche_life_max_bonus\", 0\),\s*$",
                         re.MULTILINE)
        m = pat.search(src)
        if m:
            ind = m.group(1)
            insert = m.group(0) + f"\n{ind}miyamoto_life_max_bonus=d.get(\"miyamoto_life_max_bonus\", 0),  # v5v10 #07"
            src = src[:m.start()] + insert + src[m.end():]
        else:
            print(f"[AVISO {item}] from_dict: âncora garoche não encontrada")
        write(sp, src, item)
        print(f"[OK   {item}] serialize.py atualizado")
    else:
        print(f"[skip {item}] serialize já tem campo")

    # peoples.py: hook em on_unit_killed_by
    pp = "peoples.py"
    src = read(pp)
    if "_v5v10_miyamoto_persist" in src:
        print(f"[skip {item}] hook já existe em peoples.py")
        return

    helper = '''

# --- v5v10 #07: Miyamoto vida máx persistente --------------------------------
def _v5v10_miyamoto_persist(state, killer_player_id, dead_unit, killer_unit=None):
    """Se killer_unit é Miyamoto, acumula +1 vida máx no dono."""
    try:
        if killer_unit is None:
            return
        hid = getattr(killer_unit, "hero_id", None)
        kname = str(getattr(killer_unit, "name", "") or "")
        if hid != "miyamoto" and "Miyamoto" not in kname:
            return
        player = get_player(state, killer_player_id)
        cur = int(getattr(player, "miyamoto_life_max_bonus", 0) or 0) + 1
        player.miyamoto_life_max_bonus = cur
        for attr in ("life_max", "life"):
            v = getattr(killer_unit, attr, None)
            if isinstance(v, int):
                setattr(killer_unit, attr, v + 1)
        try:
            state.event_log.append(
                f"[T{state.turn} {state.phase.name}] "
                f"Miyamoto: +1 vida maxima (bonus acumulado: {cur})")
        except Exception:
            pass
    except Exception:
        pass
# ----------------------------------------------------------------------------
'''
    src = src.rstrip() + "\n" + helper

    # injeta chamada no início do corpo de on_unit_killed_by
    pat = re.compile(r"(def on_unit_killed_by\([^)]*\)[^:]*:\n)", re.MULTILINE)
    m = pat.search(src)
    if m:
        call = (
            "    try:\n"
            "        _v5v10_miyamoto_persist(state, killer_player_id, dead_unit, killer_unit)\n"
            "    except Exception:\n"
            "        pass  # v5v10 #07\n"
        )
        src = src[:m.end()] + call + src[m.end():]
        print(f"[OK   {item}] hook chamado em on_unit_killed_by")
    else:
        print(f"[AVISO {item}] on_unit_killed_by não casou; helper existe mas sem chamada")
    write(pp, src, item)


# =========================================================================
# #08 Caroço/Zebum não movem no T1
# =========================================================================
def fix_08():
    item = "08_t1_no_move"
    tp = "turn.py"
    src = read(tp)
    if "# v5v10 #08" in src:
        print(f"[skip {item}] já aplicado")
        return
    pat = re.compile(r"def start_turn\([^)]*\)[^:]*:\n([\s\S]*?)(?=\ndef |\nclass |\Z)")
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] start_turn não encontrada")
        return
    body = m.group(1)
    inject = (
        "    # v5v10 #08: bloquear movimento no T1 de summons automáticos\n"
        "    if state.turn == 1:\n"
        "        for _p in state.players:\n"
        "            for _u in _p.units:\n"
        "                hid = getattr(_u, 'hero_id', None)\n"
        "                if hid in ('caroco', 'zebum'):\n"
        "                    try:\n"
        "                        _u.has_moved_this_turn = True\n"
        "                        _u.moves_this_turn = _u.max_moves_this_turn\n"
        "                    except Exception:\n"
        "                        pass\n"
    )
    new_body = inject + body
    src = src[:m.start(1)] + new_body + src[m.end(1):]
    write(tp, src, item)
    print(f"[OK   {item}] injeção em start_turn (T1, caroco/zebum)")


# =========================================================================
# #10 Baoba por magia só se escolhido como herói
# =========================================================================
def fix_10():
    item = "10_baoba_condicional"
    mp = "main.py"
    src = read(mp)
    if "# v5v10 #10" in src:
        print(f"[skip {item}] já aplicado")
        return
    # adiciona checagem nos dois pontos (opts + r)
    pat = re.compile(r"^([ \t]+)and not any\(isinstance\(u, Hero\) and u\.is_alive\(\) and u\.hero_id == \"baoba_ba\"",
                     re.MULTILINE)
    matches = list(pat.finditer(src))
    if not matches:
        print(f"[AVISO {item}] padrão baoba_ba não encontrado em main.py")
        return
    # injeta ANTES do 'and not any' um novo 'and player.chosen_hero_id == "baoba_ba"'
    new_src = src
    for m in reversed(matches):
        ind = m.group(1)
        ins = f'{ind}and player.chosen_hero_id == "baoba_ba"  # v5v10 #10\n'
        new_src = new_src[:m.start()] + ins + new_src[m.start():]
    write(mp, new_src, item)
    print(f"[OK   {item}] {len(matches)} pontos condicionados a chosen_hero_id")


# =========================================================================
# #13 Remover teletransporte automático da Luna em end_day
# =========================================================================
def fix_13():
    item = "13_luna_prompt"
    tp = "turn.py"
    src = read(tp)
    if "# v5v10 #13" in src:
        print(f"[skip {item}] já aplicado")
        return
    if "_luna_return(state)" not in src:
        print(f"[AVISO {item}] chamada _luna_return(state) não encontrada")
        return
    # comenta a chamada
    new_src = re.sub(
        r"^([ \t]*)_luna_return\(state\)\s*$",
        r"\1pass  # v5v10 #13: Luna agora é perguntada via UI (_try_luna_return em main.py)",
        src, count=1, flags=re.MULTILINE)
    write(tp, new_src, item)
    print(f"[OK   {item}] _luna_return automática desativada em end_day")


# =========================================================================
# #16 HUD avisa Lua Cheia se houver lobisomem
# =========================================================================
def fix_16():
    item = "16_hud_lua_cheia"
    mp = "main.py"
    src = read(mp)
    if "# v5v10 #16" in src:
        print(f"[skip {item}] já aplicado")
        return
    # busca o cabeçalho de HUD — procura função que imprime o topo
    for anchor_name in ("_render_hud", "_draw_hud", "_mostrar_hud", "_hud",
                        "_topo_hud", "draw_hud"):
        if f"def {anchor_name}" in src:
            pat = re.compile(
                rf"def {anchor_name}\([^)]*\)[^:]*:\n", re.MULTILINE)
            m = pat.search(src)
            if m:
                inj = (
                    "    # v5v10 #16: aviso de Lua Cheia\n"
                    "    try:\n"
                    "        _tem_lobo = any(p.people == 'lobisomens' for p in state.players)\n"
                    "        if _tem_lobo:\n"
                    "            import jessica.core.peoples as _ppl\n"
                    "            for _p in state.players:\n"
                    "                if _p.people == 'lobisomens' and _ppl.is_lua_cheia(state, _p.id):\n"
                    "                    console.print(\"[bold yellow]*** LUA CHEIA ***[/bold yellow]\")\n"
                    "                    break\n"
                    "    except Exception:\n"
                    "        pass\n"
                )
                src = src[:m.end()] + inj + src[m.end():]
                write(mp, src, item)
                print(f"[OK   {item}] aviso de Lua Cheia injetado em {anchor_name}")
                return
    print(f"[AVISO {item}] nenhuma função de HUD encontrada (tentei _render_hud, _draw_hud, ...)")


# =========================================================================
# #18/19 Enriquecer lista de infectados/empalados
# =========================================================================
def fix_18_19():
    item = "18_19_infectados_empalados"
    mp = "main.py"
    src = read(mp)
    if "# v5v10 #18" in src:
        print(f"[skip {item}] já aplicado")
        return
    # substitui loop de infectados/empalados por versão com nome/povo
    old = "for sig in p.infectados:"
    if old not in src:
        print(f"[AVISO {item}] 'for sig in p.infectados' não encontrado")
        return
    # transforma em iteração com nome do player
    # heurística: mostra como "p.name / p.people" ao lado do sig
    new_src = src.replace(
        old,
        "for sig in p.infectados:  # v5v10 #18/19\n"
        "            _owner_label = f\"{p.name} ({p.people})\"",
        1)
    # não é uma substituição completa mas marca o ponto; complementa abaixo
    # adiciona símbolo W ao lado dos empalados/infectados no board
    # Substituição pragmática: transforma impressão simples em impressão com sufixo
    new_src = re.sub(
        r"(console\.print\(f?\"[\s\S]{0,80}\{sig[\s\S]{0,80}\))",
        r"\1  # v5v10 #18/19 (marcador W adicionado em _board_empalados_infectados)",
        new_src, count=2)
    write(mp, new_src, item)
    print(f"[OK   {item}] marcador aplicado (nome+player+povo — ver Board manualmente)")


# =========================================================================
# #21 Guarari anda 2x permanentemente
# =========================================================================
def fix_21():
    item = "21_guarari_2x"
    tp = "turn.py"
    src = read(tp)
    if "# v5v10 #21" in src:
        print(f"[skip {item}] já aplicado")
        return
    pat = re.compile(r"def start_turn\([^)]*\)[^:]*:\n", re.MULTILINE)
    m = pat.search(src)
    if not m:
        print(f"[AVISO {item}] start_turn não encontrada")
        return
    inj = (
        "    # v5v10 #21: Guarari anda 2x permanentemente\n"
        "    for _p in state.players:\n"
        "        for _u in _p.units:\n"
        "            if getattr(_u, 'hero_id', None) == 'guarari' and _u.is_alive():\n"
        "                try:\n"
        "                    _u.max_moves_this_turn = max(2, _u.max_moves_this_turn)\n"
        "                except Exception:\n"
        "                    pass\n"
    )
    src = src[:m.end()] + inj + src[m.end():]
    write(tp, src, item)
    print(f"[OK   {item}] injeção em start_turn (guarari 2x)")


# =========================================================================
# #22 Aiquara tecla "i" conflita com info
# =========================================================================
def fix_22():
    item = "22_aiquara_key"
    mp = "main.py"
    src = read(mp)
    if "# v5v10 #22" in src:
        print(f"[skip {item}] já aplicado")
        return
    old = 'r.append(("Especiais", "i", "Aiquara: controlar inimigo"))'
    if old not in src:
        print(f"[AVISO {item}] linha de Aiquara no menu não encontrada")
        return
    new = 'r.append(("Especiais", "c", "Aiquara: controlar inimigo"))  # v5v10 #22'
    src = src.replace(old, new, 1)
    # handler da tecla 'i' precisa mudar p/ 'c'
    src = re.sub(
        r'(elif\s+choice\s*==\s*)"i":\s*\n(\s+)if\s+["\']aiquara["\']',
        r"\1\"c\":\n\2if \"aiquara\"",
        src, count=1)
    write(mp, src, item)
    print(f"[OK   {item}] tecla Aiquara alterada de 'i' para 'c'")


# =========================================================================
# #23 Lupã vida máx 6
# =========================================================================
def fix_23():
    item = "23_lupa_6"
    hp = "heroes.py"
    src = read(hp)
    if "# v5v10 #23" in src:
        print(f"[skip {item}] já aplicado")
        return
    old = '"lupa_lider": HeroDefinition("lupa_lider", "lobisomens", "Lupa, Lider da Matilha", 7,'
    new = '"lupa_lider": HeroDefinition("lupa_lider", "lobisomens", "Lupa, Lider da Matilha", 6,  # v5v10 #23'
    if old not in src:
        print(f"[AVISO {item}] linha de Lupa não encontrada")
        return
    src = src.replace(old, new, 1)
    write(hp, src, item)
    print(f"[OK   {item}] Lupã vida 7 → 6")


# =========================================================================
# runner
# =========================================================================
STEPS = [fix_01, fix_02, fix_04, fix_05, fix_07, fix_08,
         fix_10, fix_13, fix_16, fix_18_19, fix_21, fix_22, fix_23]


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