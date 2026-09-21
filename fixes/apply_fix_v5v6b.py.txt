"""apply_fix_v5v6b: substitui show_turn_log inteiro via regex."""
from pathlib import Path
from datetime import datetime
import os
import re
import shutil

def _find_project_root() -> Path:
    env = os.environ.get("JESSICA_ROOT")
    if env:
        p = Path(env)
        if (p / "jessica" / "main.py").exists():
            return p
    candidates = [
        Path.home() / "Downloads" / "jessica",
        Path.home() / "jessica",
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
    ]
    for c in candidates:
        if (c / "jessica" / "main.py").exists():
            return c
    return Path.home() / "Downloads" / "jessica"

ROOT = _find_project_root()
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v6b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

NEW_LOG = '''\
def show_turn_log(state) -> None:
    entries = [e for e in state.action_log if e["turn"] == state.turn]
    buckets: dict[str, list[str]] = {
        "MOV": [], "SUM": [], "ART": [], "FEIT": [], "COMB": [], "MORTE": [],
    }
    for e in entries:
        a = e["action"]
        params = e.get("params", {})
        pname = _describe_player(state, e.get("player_id"))
        if a == "move_unit":
            uid = params.get("unit_id", "?")
            buckets["MOV"].append(
                f"{pname}: moveu {uid} "
                f"de {params.get('origin')} para {params.get('destination')}"
            )
        elif a == "summon_troop":
            buckets["SUM"].append(
                f"{pname}: invocou Tropa {params.get('archetype')} "
                f"({params.get('life')} vida)"
            )
        elif a == "summon_hero":
            hid = params.get("hero_id")
            buckets["SUM"].append(f"{pname}: invocou Heroi {_describe_hero(hid)}")
        elif a == "play_artifact":
            card = _describe_card(params.get("card"))
            choice = params.get("choice") or {}
            extra = ""
            if choice.get("unit_id"):
                tuid = choice["unit_id"]
                for p in state.players:
                    for u in p.units:
                        if u.id == tuid:
                            tipo = (f"Heroi {_describe_hero(u.hero_id)}"
                                    if isinstance(u, Hero)
                                    else f"Tropa {u.archetype.value}")
                            extra = f" em {tipo} de {p.name}"
                            break
            elif choice.get("target_player_id"):
                extra = f" em {_describe_player(state, choice['target_player_id'])}"
            elif choice.get("hero_id"):
                extra = f" (invocou {_describe_hero(choice['hero_id'])})"
            buckets["ART"].append(f"{pname}: jogou {card}{extra}")
        elif a == "buy_artifact_gold":
            buckets["ART"].append(
                f"{pname}: comprou {_describe_card(params.get('card'))} (Ouro)"
            )
        elif a == "transmute_artifact_magic":
            buckets["ART"].append(
                f"{pname}: transmutou {_describe_card(params.get('card'))} (Magia)"
            )
        elif a == "sell_artifact":
            buckets["ART"].append(
                f"{pname}: vendeu {_describe_card(params.get('card'))}"
            )
        elif a == "cast_spell":
            try:
                sp_nome = spells_mod.get_spell(params.get("spell")).name
            except Exception:
                sp_nome = params.get("spell", "?")
            buckets["FEIT"].append(f"{pname}: lancou {sp_nome}")
        elif a == "attack":
            atk = _describe_unit_kind(params, "attacker")
            tgt = _describe_unit_kind(params, "target")
            tgt_dono = _describe_player(state, params.get("target_owner_id"))
            buckets["COMB"].append(
                f"{pname}: {atk} atacou {tgt} de {tgt_dono} "
                f"(dano {params.get('damage')}, ret {params.get('retaliation')})"
            )
        elif a == "attack_city":
            atk = _describe_unit_kind(params, "attacker")
            tgt_dono = _describe_player(state, params.get("target_player_id"))
            buckets["COMB"].append(
                f"{pname}: {atk} atacou a Cidade de {tgt_dono} "
                f"(dano {params.get('damage')})"
            )
        elif a == "unit_died":
            kind = params.get("kind", "?")
            if kind == "hero":
                desc = f"Heroi {_describe_hero(params.get('hero_id'))}"
            elif kind == "troop":
                desc = f"Tropa {params.get('archetype', '?')}"
            else:
                desc = params.get("unit_id", "?")
            killer = _describe_player(state, params.get("killed_by"))
            if params.get("killed_by"):
                buckets["MORTE"].append(f"{pname}: {desc} morreu (por {killer})")
            else:
                buckets["MORTE"].append(f"{pname}: {desc} morreu")
    # Rolls
    prefix = f"[T{state.turn} "
    rolls = []
    for line in state.event_log:
        if not line.startswith(prefix):
            continue
        idx = line.find("[ROLL]")
        if idx >= 0:
            rolls.append(line[idx:])
    for e in entries:
        if e["action"] != "roll":
            continue
        params = e.get("params", {})
        pname = _describe_player(state, e.get("player_id"))
        src = params.get("source", "?")
        results = params.get("results", [])
        rolls.append(f"[ROLL] {pname} {src}: {results}")
    console.print(f"[bold]TURNO {state.turn} - o que aconteceu ate agora[/bold]")
    found = False
    for label, items in buckets.items():
        if not items:
            continue
        found = True
        for item in items:
            console.print(f"[dim][{label}][/dim] {item}")
    if rolls:
        found = True
        for r in rolls:
            console.print(f"[dim][ROLL][/dim] {r}")
    if not found:
        console.print("[dim](nada ainda)[/dim]")
    console.print()
'''


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    full = ROOT / "jessica" / "main.py"
    if not full.exists():
        print(f"ERRO: {full} nao existe.")
        return
    original = full.read_text(encoding="utf-8")

    # Regex: pega "def show_turn_log" ate o proximo "def " ou "class " no inicio de linha
    pattern = re.compile(
        r"def show_turn_log\(state\) -> None:.*?(?=\n(?:def |class )|\Z)",
        re.DOTALL,
    )
    if not pattern.search(original):
        print("AVISO: nao achei 'def show_turn_log' no main.py.")
        return

    patched = pattern.sub(NEW_LOG.rstrip() + "\n", original, count=1)
    if patched == original:
        print("AVISO: substituicao nao mudou nada.")
        return

    backup_path = BACKUP_DIR / "jessica" / "main.py"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(patched, encoding="utf-8")
    print("OK  - jessica/main.py (show_turn_log substituido via regex)")
    print(f"Backup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")


if __name__ == "__main__":
    main()