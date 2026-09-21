"""v5v9a — Miyamoto vida máxima persistente.

- Adiciona Player.miyamoto_life_max_bonus: int = 0
- Adiciona _v5v9a_miyamoto_persist() em peoples.py
- Enxerta chamada no topo de on_unit_killed_by (se existir)
- Serializa em state_to_dict / state_from_dict

Se algum alvo não casar, emite AVISO e continua (padrão do projeto).
"""
import ast
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


FIELD = "miyamoto_life_max_bonus"


def find_root() -> Path:
    for c in [Path.home() / "Downloads" / "jessica", Path.home() / "jessica",
              Path.cwd(), Path(__file__).resolve().parent.parent]:
        if (c / "jessica" / "main.py").is_file():
            return c
    raise SystemExit("ROOT não encontrado")


def add_field_to_dataclass(src: str, cls: str, line: str) -> tuple[str, bool]:
    """Insere `line` após o último campo do dataclass `cls`."""
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            last_field_end = None
            for n in node.body:
                if isinstance(n, (ast.AnnAssign, ast.Assign)):
                    last_field_end = n.end_lineno
            if last_field_end is None:
                return src, False
            lines = src.splitlines(keepends=True)
            indent = "    "
            new_lines = lines[:last_field_end] + [f"{indent}{line}\n"] + lines[last_field_end:]
            return "".join(new_lines), True
    return src, False


def ensure_field_import(src: str) -> tuple[str, bool]:
    if re.search(r"from dataclasses import[^\n]*\bfield\b", src):
        return src, True
    m = re.search(r"from dataclasses import ([^\n]+)", src)
    if m:
        names = m.group(1)
        new = f"from dataclasses import {names}, field"
        return src[:m.start()] + new + src[m.end():], True
    # fallback: adiciona import no topo
    return "from dataclasses import field  # v5v9a\n" + src, True


PERSIST_FN = '''

# --- v5v9a: Miyamoto persistente --------------------------------------------
def _v5v9a_miyamoto_persist(state, killer, victim):
    """Se killer é Miyamoto, acumula +1 vida máxima no dono e no próprio herói."""
    try:
        kname = str(getattr(killer, "name", "") or getattr(killer, "hero_name", "") or "")
        if "Miyamoto" not in kname:
            return
        pid = getattr(killer, "owner", None)
        if pid is None:
            pid = getattr(killer, "owner_id", None)
        if pid is None:
            return
        players = getattr(state, "players", None)
        player = None
        if players is not None:
            try:
                player = players[pid]
            except Exception:
                try:
                    player = players.get(pid)
                except Exception:
                    player = None
        if player is None:
            return
        cur = int(getattr(player, "miyamoto_life_max_bonus", 0) or 0) + 1
        setattr(player, "miyamoto_life_max_bonus", cur)
        for attr in ("life_max", "life"):
            v = getattr(killer, attr, None)
            if isinstance(v, int):
                setattr(killer, attr, v + 1)
        log = getattr(state, "log", None) or getattr(state, "record_action", None)
        if callable(log):
            try:
                log(f"☠ Miyamoto: +1 vida máxima (bônus acumulado: {cur})")
            except Exception:
                pass
    except Exception:
        pass
# ----------------------------------------------------------------------------
'''


def inject_hook(src: str) -> tuple[str, bool]:
    """Adiciona chamada no topo do corpo de on_unit_killed_by."""
    pat = re.compile(r"(def on_unit_killed_by\([^)]*\):\n)((?:\s+[^\n]*\n)+)", re.MULTILINE)
    m = pat.search(src)
    if not m:
        return src, False
    # inserir na primeira linha do corpo
    call = "    try:\n        _v5v9a_miyamoto_persist(state, killer, victim)\n    except Exception:\n        pass  # v5v9a\n"
    # indentação pode variar; detectar do primeiro statement
    first_stmt = m.group(2).splitlines()[0]
    indent = re.match(r"(\s*)", first_stmt).group(1)
    call = call.replace("    ", indent)
    new_body = call + m.group(2)
    return src[:m.start()] + m.group(1) + new_body + src[m.end():], True


def patch_serialize(src: str, field: str, cls_name: str) -> tuple[str, bool]:
    """Adiciona serialização em state_to_dict e state_from_dict se possível."""
    changed = False
    # tenta detectar onde o dict do player é montado
    # Padrão conservador: injeta uma linha após 'for ... in ... players' ou similar.
    # Se não encontrar, apenas avisa.
    if f'"{field}"' in src or f"'{field}'" in src:
        return src, True  # já serializado
    # to_dict: procura "def state_to_dict" e injeta um try que salva os bônus
    return src, changed


def main():
    root = find_root()
    core = root / "jessica" / "core"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = root / "backups" / f"v5v9a_miyamoto_{ts}"
    bkp.mkdir(parents=True, exist_ok=True)

    # --- models.py ---
    mp = core / "models.py"
    msrc = mp.read_text(encoding="utf-8")
    if FIELD in msrc:
        print(f"[skip] models.py já tem {FIELD}")
    else:
        msrc, ok = ensure_field_import(msrc)
        if not ok:
            print("AVISO: não consegui garantir import de field()")
        msrc, ok = add_field_to_dataclass(
            msrc, "Player", f"{FIELD}: int = 0  # v5v9a")
        if not ok:
            print("AVISO: não achei class Player em models.py — snippet não casou")
        else:
            shutil.copy2(mp, bkp / "models.py")
            mp.write_text(msrc, encoding="utf-8")
            print(f"OK: Player.{FIELD} adicionado")

    # --- peoples.py ---
    pp = core / "peoples.py"
    psrc = pp.read_text(encoding="utf-8")
    if "_v5v9a_miyamoto_persist" in psrc:
        print("[skip] peoples.py já tem _v5v9a_miyamoto_persist")
    else:
        psrc = psrc.rstrip() + "\n" + PERSIST_FN
        psrc, ok = inject_hook(psrc)
        if not ok:
            print("AVISO: on_unit_killed_by não casou — hook não injetado (função existe, chamada manual)")
        shutil.copy2(pp, bkp / "peoples.py")
        pp.write_text(psrc, encoding="utf-8")
        print("OK: _v5v9a_miyamoto_persist adicionado em peoples.py")

    # --- serialize.py ---
    sp = core / "serialize.py"
    if sp.is_file():
        ssrc = sp.read_text(encoding="utf-8")
        if FIELD in ssrc:
            print("[skip] serialize.py já menciona o campo")
        else:
            # Injeção mínima: em state_to_dict, adicionar dict de bônus por pid
            new_to = (
                "    # v5v9a\n"
                "    try:\n"
                "        out['miyamoto_bonus'] = {p.id: getattr(p, 'miyamoto_life_max_bonus', 0)\n"
                "                                 for p in state.players.values()}\n"
                "    except Exception:\n"
                "        pass\n"
            )
            new_from = (
                "    # v5v9a\n"
                "    try:\n"
                "        _mb = data.get('miyamoto_bonus', {}) or {}\n"
                "        for pid, val in _mb.items():\n"
                "            _p = state.players.get(int(pid))\n"
                "            if _p is not None:\n"
                "                _p.miyamoto_life_max_bonus = int(val)\n"
                "    except Exception:\n"
                "        pass\n"
            )
            changed = False
            m = re.search(r"(def state_to_dict\([^)]*\):\n)", ssrc)
            if m:
                ssrc = ssrc[:m.end()] + new_to + ssrc[m.end():]
                changed = True
            else:
                print("AVISO: state_to_dict não casou")
            m = re.search(r"(def state_from_dict\([^)]*\):\n)", ssrc)
            if m:
                ssrc = ssrc[:m.end()] + new_from + ssrc[m.end():]
                changed = True
            else:
                print("AVISO: state_from_dict não casou")
            if changed:
                shutil.copy2(sp, bkp / "serialize.py")
                sp.write_text(ssrc, encoding="utf-8")
                print("OK: serialize.py atualizado")
    else:
        print("AVISO: serialize.py não existe")

    # validação de sintaxe
    for f in (mp, pp, sp):
        if f.is_file():
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as ex:
                print(f"[ERRO] {f.name} quebrou: {ex}")
                return 1
    print(f"Backup: {bkp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())