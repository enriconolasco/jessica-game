"""v5v9-bis — corrige o que o v5v9a/b original não casou.

Conserta:
  (1) Regex de `def X(...) -> Y:` (agora aceita `-> tipo` antes do `:`)
  (2) Assinatura real de on_unit_killed_by: (state, killer_player_id, dead_unit, killer_unit)
  (3) Serialização de miyamoto_life_max_bonus e night_start_positions
  (4) Reescreve _v5v9a_miyamoto_persist com os parâmetros certos

Backup em backups/v5v9bis_<ts>/. Aborta se quebrar sintaxe."""
import ast
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def find_root() -> Path:
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


# aceita `def nome(...) -> qualquer_coisa:` OU `def nome(...):`
FUNC_HEAD = r"def {name}\([^)]*\)[^:]*:\n"

HELPER_MIYAMOTO = '''
# --- v5v9bis: Miyamoto persistente ------------------------------------------
def _v5v9a_miyamoto_persist(state, killer_player_id, dead_unit, killer_unit=None):
    """Se killer_unit é Miyamoto, +1 vida máx no dono e no herói.

    Assinatura espelha on_unit_killed_by. Não levanta exceção."""
    try:
        if killer_unit is None:
            return
        kname = str(getattr(killer_unit, "name", "") or
                    getattr(killer_unit, "hero_name", "") or "")
        if "Miyamoto" not in kname:
            return
        player = None
        for p in getattr(state, "players", []) or []:
            if getattr(p, "id", None) == killer_player_id:
                player = p
                break
        if player is None:
            return
        cur = int(getattr(player, "miyamoto_life_max_bonus", 0) or 0) + 1
        setattr(player, "miyamoto_life_max_bonus", cur)
        for attr in ("life_max", "life"):
            v = getattr(killer_unit, attr, None)
            if isinstance(v, int):
                setattr(killer_unit, attr, v + 1)
        try:
            state.event_log.append(
                f"[T{state.turn} {state.phase.name}] "
                f"⚔ Miyamoto: +1 vida máxima (bônus acumulado: {cur})")
        except Exception:
            pass
    except Exception:
        pass
# ----------------------------------------------------------------------------
'''


def replace_helper(psrc: str) -> tuple[str, bool]:
    """Substitui _v5v9a_miyamoto_persist inteiro (regex robusta)."""
    pat = re.compile(
        r"def _v5v9a_miyamoto_persist\(.*?\n(?=def |class |# ---|_v5v9a|\Z)",
        re.DOTALL)
    if pat.search(psrc):
        return pat.sub(HELPER_MIYAMOTO.lstrip("\n"), psrc, count=1), True
    # se não existia, apenas apende
    return psrc.rstrip() + "\n" + HELPER_MIYAMOTO, True


def inject_hook(psrc: str) -> tuple[str, bool]:
    """Injeta chamada logo após o docstring/primeira linha de on_unit_killed_by."""
    head = re.compile(FUNC_HEAD.format(name="on_unit_killed_by"))
    m = head.search(psrc)
    if not m:
        return psrc, False
    # remove hook antigo (se houver) entre a assinatura e o fim da função
    tail = re.compile(
        r"(_v5v9a_miyamoto_persist\([^)]*\)[\s\S]*?\n(?:[ \t]*pass[^\n]*\n)?)",
        re.MULTILINE)
    # localiza corpo inteiro da função pra limpá-lo
    fn_end = re.compile(r"\ndef on_unit_killed_by\b.*?\n(?=def |class |\Z)", re.DOTALL)
    fm = fn_end.search(psrc)
    if fm:
        body = fm.group(0)
        body_clean = tail.sub("", body)
        psrc = psrc[:fm.start()] + body_clean + psrc[fm.end():]

    # reinjeta
    head = re.compile(FUNC_HEAD.format(name="on_unit_killed_by"))
    m = head.search(psrc)
    if not m:
        return psrc, False
    call = ("    try:\n"
            "        _v5v9a_miyamoto_persist(state, killer_player_id, dead_unit, killer_unit)\n"
            "    except Exception:\n"
            "        pass  # v5v9bis\n")
    return psrc[:m.end()] + call + psrc[m.end():], True


def patch_serialize(ssrc: str) -> tuple[str, bool]:
    """Adiciona serialização. Regex nova aceita `-> tipo:`."""
    changed = False

    to_payload = (
        "    # v5v9bis\n"
        "    try:\n"
        "        out['miyamoto_bonus'] = {str(p.id): int(getattr(p, 'miyamoto_life_max_bonus', 0) or 0)\n"
        "                                 for p in state.players}\n"
        "    except Exception:\n"
        "        pass\n"
        "    try:\n"
        "        out['night_start_positions'] = dict(getattr(state, 'night_start_positions', {}) or {})\n"
        "    except Exception:\n"
        "        pass\n"
    )
    fr_payload = (
        "    # v5v9bis\n"
        "    try:\n"
        "        _mb = data.get('miyamoto_bonus', {}) or {}\n"
        "        for pid_s, val in _mb.items():\n"
        "            _p = next((p for p in state.players if str(p.id) == str(pid_s)), None)\n"
        "            if _p is not None:\n"
        "                _p.miyamoto_life_max_bonus = int(val)\n"
        "    except Exception:\n"
        "        pass\n"
        "    try:\n"
        "        state.night_start_positions = dict(data.get('night_start_positions', {}) or {})\n"
        "    except Exception:\n"
        "        pass\n"
    )

    # limpa tentativas antigas v5v9a / v5v9b (podem ter sido inseridas em estado corrompido)
    ssrc = re.sub(r"[ \t]*# v5v9a\n(?:\s+try:[\s\S]*?\n\s+pass\n)+", "", ssrc)
    ssrc = re.sub(r"[ \t]*# v5v9b\n(?:\s+try:[\s\S]*?\n\s+pass\n)+", "", ssrc)

    for fn, payload in (("state_to_dict", to_payload), ("state_from_dict", fr_payload)):
        pat = re.compile(FUNC_HEAD.format(name=fn))
        m = pat.search(ssrc)
        if not m:
            print(f"  AVISO: {fn} não casou nem com regex relaxada")
            continue
        ssrc = ssrc[:m.end()] + payload + ssrc[m.end():]
        changed = True
        print(f"  OK: serialização enxertada em {fn}")

    return ssrc, changed


def main():
    root = find_root()
    core = root / "jessica" / "core"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = root / "backups" / f"v5v9bis_{ts}"
    bkp.mkdir(parents=True, exist_ok=True)
    print(f"ROOT: {root}\nBackup: {bkp}")

    # ---------- peoples.py ----------
    pp = core / "peoples.py"
    psrc = pp.read_text(encoding="utf-8")
    shutil.copy2(pp, bkp / "peoples.py")
    psrc, _ = replace_helper(psrc)
    psrc, ok = inject_hook(psrc)
    if not ok:
        print("AVISO: on_unit_killed_by não casou — hook não reinjetado")
    pp.write_text(psrc, encoding="utf-8")
    print("OK: peoples.py (helper + hook)")

    # ---------- turn.py ----------
    tp = core / "turn.py"
    tsrc = tp.read_text(encoding="utf-8")
    shutil.copy2(tp, bkp / "turn.py")
    if "def snapshot_night_start" not in tsrc:
        tsrc = tsrc.rstrip() + "\n\n" + '''
# --- v5v9bis: prioridade de declaração noturna ------------------------------
def snapshot_night_start(state):
    """Guarda {(pid, unit_id): house} de todas unidades no início da noite."""
    snap = {}
    for p in getattr(state, "players", []) or []:
        for u in getattr(p, "units", []) or []:
            uid = getattr(u, "id", None)
            if uid is None:
                uid = id(u)
            house = getattr(u, "house", None) or getattr(u, "location", None) or "?"
            snap[f"{getattr(p, 'id', '?')}:{uid}"] = str(house)
    state.night_start_positions = snap


def night_start_priority(state, pid, uid) -> int:
    """0 = já estava no início da noite, 1 = chegou depois."""
    snap = getattr(state, "night_start_positions", None) or {}
    return 0 if f"{pid}:{uid}" in snap else 1
# ---------------------------------------------------------------------------
'''
    # tenta injetar snapshot_night_start antes do return de end_day
    ed_pat = re.compile(r"def end_day\([^)]*\)[^:]*:\n([\s\S]*?)(?=\ndef |\nclass |\Z)")
    em = ed_pat.search(tsrc)
    if em and "snapshot_night_start(state)" not in em.group(1):
        body = em.group(1)
        rets = list(re.finditer(r"\n([ \t]+)return\b", body))
        if rets:
            last = rets[-1]
            indent = last.group(1)
            insert = f"\n{indent}snapshot_night_start(state)  # v5v9bis"
            new_body = body[:last.start()] + insert + body[last.start():]
            tsrc = tsrc[:em.start(1)] + new_body + tsrc[em.end(1):]
            print("OK: snapshot_night_start() enxertado em end_day")
        else:
            print("AVISO: end_day sem return — helper existe, hook manual")
    tp.write_text(tsrc, encoding="utf-8")
    print("OK: turn.py")

    # ---------- serialize.py ----------
    sp = core / "serialize.py"
    if sp.is_file():
        ssrc = sp.read_text(encoding="utf-8")
        shutil.copy2(sp, bkp / "serialize.py")
        ssrc, _ = patch_serialize(ssrc)
        sp.write_text(ssrc, encoding="utf-8")
        print("OK: serialize.py")
    else:
        print("AVISO: serialize.py não existe")

    # ---------- validação ----------
    for f in (pp, tp, sp):
        if f.is_file():
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as ex:
                print(f"[ERRO] {f.name} quebrou: {ex}")
                return 1
    print("\nTudo aplicado. Rode: python tests\\run_all.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())