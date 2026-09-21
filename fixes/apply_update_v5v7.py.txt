"""apply_update_v5v7: cores por povo, nome de heroi no mapa, tropas renomeadas,
   describe de rolls, combate descritivo, Asas Encantadas no action_log,
   Ori aura visivel, relatorios por povo."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v7_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. peoples.py - Asas Encantadas registra action_log
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    '''\
def on_unit_moved(state: GameState, player_id: int, unit: Unit) -> None:
    player = get_player(state, player_id)
    if player.people == PEOPLE_FAE:
        player.city.magic += 1
        log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id}.")
        return
    if (player.people == PEOPLE_GNOMOS
            and isinstance(unit, Hero) and unit.hero_id == "sao_tome"):
        effective = sao_tome_effective_peoples(state, player)
        if PEOPLE_FAE in effective:
            player.city.magic += 1
            log(state, f"{player.name} (Sao Tome herda Fadas): +1 Magia ao mover.")''',
    '''\
def on_unit_moved(state: GameState, player_id: int, unit: Unit) -> None:
    from .state import record_action
    player = get_player(state, player_id)
    if player.people == PEOPLE_FAE:
        player.city.magic += 1
        log(state, f"{player.name} (Fadas): +1 Magia ao mover {unit.id} (Asas Encantadas).")
        record_action(state, player_id, "trigger",
                      source="asas_encantadas", magic=1, unit_id=unit.id)
        return
    if (player.people == PEOPLE_GNOMOS
            and isinstance(unit, Hero) and unit.hero_id == "sao_tome"):
        effective = sao_tome_effective_peoples(state, player)
        if PEOPLE_FAE in effective:
            player.city.magic += 1
            log(state, f"{player.name} (Sao Tome herda Fadas): +1 Magia ao mover (Asas Encantadas).")
            record_action(state, player_id, "trigger",
                          source="asas_encantadas_sao_tome", magic=1, unit_id=unit.id)'''
))

# =============================================================
# 2. main.py - adiciona PEOPLE_COLORS, TROOP_DISPLAY, helpers
#    (inseridos antes de SYMBOL_DESC se existir; senao apos RestartGame)
# =============================================================
COLOR_BLOCK = '''\
PEOPLE_COLORS = {
    "humanos": "bright_blue",
    "anoes": "yellow",
    "orcs": "orange3",
    "fadas": "magenta",
    "vampiros": "red",
    "lobisomens": "dark_blue",
    "gigantes": "dark_orange3",
    "mortos_vivos": "grey50",
    "filhos_floresta": "green",
    "gnomos_duendes": "bright_magenta",
}

TROOP_DISPLAY = {
    "light": "pequena",
    "medium": "media",
    "heavy": "grande",
    "special": "especial",
    "extra": "extra",
    "ghoul": "carnical",
    "esqueleto": "esqueleto",
}

ROCA_EFFECTS = {1: "Magia", 2: "Ouro", 3: "Cura 2 pendente", 4: "Dano 1 na sua Cidade"}
CABACA_EFFECTS = {1: "Invulneravel", 2: "+1 movimento", 3: "+1 Ouro", 4: "+1 Magia"}


def _pcolor(povo: str) -> str:
    return PEOPLE_COLORS.get(povo, "white")


def _pname(state, pid: int) -> str:
    try:
        p = get_player(state, pid)
    except Exception:
        return f"J{pid}"
    c = _pcolor(p.people)
    return f"[{c}]{p.name}[/{c}]"


def _troop_display(arch) -> str:
    if hasattr(arch, "value"):
        arch = arch.value
    return TROOP_DISPLAY.get(arch, str(arch))


def _hero_short(hero_id: str) -> str:
    try:
        n = heroes.hero_name(hero_id)
    except Exception:
        return str(hero_id)
    return n.split(",")[0].strip()


def _describe_roll(source: str, results: list) -> str:
    if source == "roca_humanos":
        effects = ROCA_EFFECTS
    elif source == "cabaca_cheia":
        effects = CABACA_EFFECTS
    else:
        effects = None
    parts = []
    for r in results:
        eff = effects.get(r) if effects else None
        if eff:
            parts.append(f"{r} ({eff})")
        else:
            parts.append(str(r))
    return ", ".join(parts)


'''

# Try to insert before SYMBOL_DESC if present
EDITS.append((
    "jessica/main.py",
    "SYMBOL_DESC = {",
    COLOR_BLOCK + "SYMBOL_DESC = {"
))

# =============================================================
# 3. main.py - _unit_symbols: adiciona A (Ori aura)
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def _unit_symbols(state, u) -> str:
    syms = []
    if u.double_damage:
        syms.append("2x")
    if u.resistance_stacks:
        syms.append(f"R{u.resistance_stacks}")''',
    '''\
def _unit_symbols(state, u) -> str:
    syms = []
    # Ori aura: se ha Ori no local
    try:
        owner = get_player(state, u.owner_id)
        for o in owner.units:
            if isinstance(o, Hero) and o.is_alive() and o.hero_id == "ori" and o.house == u.house:
                if o.id != u.id:
                    syms.append("A")
                    break
    except Exception:
        pass
    if u.double_damage:
        syms.append("2x")
    if u.resistance_stacks:
        syms.append(f"R{u.resistance_stacks}")'''
))

# =============================================================
# 4. main.py - SYMBOL_DESC: adiciona A
# =============================================================
EDITS.append((
    "jessica/main.py",
    'SYMBOL_DESC = {\n    "2x": "Dobro de dano (Kc, Qs, Vovo, etc.)",',
    'SYMBOL_DESC = {\n'
    '    "A": "Sob aura de Ori (dano recebido dividido por 2)",\n'
    '    "2x": "Dobro de dano (Kc, Qs, Vovo, etc.)",'
))

# =============================================================
# 5. main.py - _city_cell_lines: nome de heroi, cor de povo, tropas renomeadas
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def _city_cell_lines(state, pid: int, width: int) -> list[str]:
    player = get_player(state, pid)
    city = player.city
    mark = " *" if state.curuna_id == pid else ""
    povo = player.people[:8]
    title = f"J{pid} {player.name[:8]}{mark}"
    sub = f"({povo})"
    vida = f"Cidade {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"
    lines = [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width), _pad(vida, width)]
    house = f"city_{pid}"
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == house and u.is_alive():
                kind = "H" if isinstance(u, Hero) else "T"
                syms = _unit_symbols(state, u)
                label = f"{kind}{u.life}{syms}"
                if p.id != pid:
                    label = f"J{p.id} {label}"
                units.append(label)
    if units:
        for u in units:
            lines.append(_pad(u, width))
    else:
        lines.append(_pad("[dim]-[/dim]", width))
    return lines''',
    '''\
def _city_cell_lines(state, pid: int, width: int) -> list[str]:
    player = get_player(state, pid)
    city = player.city
    mark = " *" if state.curuna_id == pid else ""
    povo = player.people[:10]
    c = _pcolor(player.people)
    title = f"[{c}]J{pid} {player.name[:8]}{mark}[/{c}]"
    sub = f"[{c}]({povo})[/{c}]"
    vida = f"Cidade {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"
    lines = [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width), _pad(vida, width)]
    house = f"city_{pid}"
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == house and u.is_alive():
                syms = _unit_symbols(state, u)
                if isinstance(u, Hero):
                    label = f"{_hero_short(u.hero_id)} {u.life}{syms}"
                else:
                    label = f"{_troop_display(u.archetype)} {u.life}{syms}"
                if p.id != pid:
                    label = f"J{p.id} {label}"
                units.append(label)
    if units:
        for u in units:
            lines.append(_pad(u, width))
    else:
        lines.append(_pad("[dim]-[/dim]", width))
    return lines'''
))

# =============================================================
# 6. main.py - _center_cell_lines
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def _center_cell_lines(state, width: int) -> list[str]:
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == CENTER and u.is_alive():
                kind = "H" if isinstance(u, Hero) else "T"
                syms = _unit_symbols(state, u)
                units.append(f"J{p.id}-{kind}{u.life}{syms}")''',
    '''\
def _center_cell_lines(state, width: int) -> list[str]:
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == CENTER and u.is_alive():
                syms = _unit_symbols(state, u)
                if isinstance(u, Hero):
                    label = f"J{p.id} {_hero_short(u.hero_id)} {u.life}{syms}"
                else:
                    label = f"J{p.id} {_troop_display(u.archetype)} {u.life}{syms}"
                units.append(label)'''
))

# =============================================================
# 7. main.py - show_turn_log: describe de rolls + combat com buffs
#    (regex: substitui a função inteira)
# =============================================================
NEW_LOG = '''\
def show_turn_log(state) -> None:
    entries = [e for e in state.action_log if e["turn"] == state.turn]
    buckets: dict[str, list[str]] = {
        "MOV": [], "SUM": [], "ART": [], "FEIT": [], "COMB": [], "MORTE": [], "TRG": [],
    }
    for e in entries:
        a = e["action"]
        params = e.get("params", {})
        pname = _pname(state, e.get("player_id"))
        if a == "move_unit":
            uid = params.get("unit_id", "?")
            buckets["MOV"].append(
                f"{pname}: moveu {uid} "
                f"de {params.get('origin')} para {params.get('destination')}"
            )
        elif a == "trigger":
            src = params.get("source", "?")
            if src.startswith("asas_encantadas"):
                pname_of = "Asas Encantadas (Fadas)"
                if src.endswith("sao_tome"):
                    pname_of = "Asas Encantadas (Sao Tome herda)"
                buckets["TRG"].append(
                    f"{pname}: +{params.get('magic', 1)} Magia ({pname_of})"
                )
        elif a == "summon_troop":
            buckets["SUM"].append(
                f"{pname}: invocou Tropa {_troop_display(params.get('archetype'))} "
                f"({params.get('life')} vida)"
            )
        elif a == "summon_hero":
            hid = params.get("hero_id")
            buckets["SUM"].append(f"{pname}: invocou Heroi {_hero_short(hid)}")
        elif a == "play_artifact":
            card = _describe_card(params.get("card"))
            choice = params.get("choice") or {}
            extra = ""
            if choice.get("unit_id"):
                tuid = choice["unit_id"]
                for p in state.players:
                    for u in p.units:
                        if u.id == tuid:
                            tipo = (f"Heroi {_hero_short(u.hero_id)}"
                                    if isinstance(u, Hero)
                                    else f"Tropa {_troop_display(u.archetype)}")
                            extra = f" em {tipo} de {_pname(state, p.id)}"
                            break
            elif choice.get("target_player_id"):
                extra = f" em {_pname(state, choice['target_player_id'])}"
            elif choice.get("hero_id"):
                extra = f" (invocou {_hero_short(choice['hero_id'])})"
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
            tgt_dono = _pname(state, params.get("target_owner_id"))
            buckets["COMB"].append(
                f"{pname}: {atk} atacou {tgt} de {tgt_dono} "
                f"(dano {params.get('damage')}, ret {params.get('retaliation')})"
            )
        elif a == "attack_city":
            atk = _describe_unit_kind(params, "attacker")
            tgt_dono = _pname(state, params.get("target_player_id"))
            buckets["COMB"].append(
                f"{pname}: {atk} atacou a Cidade de {tgt_dono} "
                f"(dano {params.get('damage')})"
            )
        elif a == "unit_died":
            kind = params.get("kind", "?")
            if kind == "hero":
                desc = f"Heroi {_hero_short(params.get('hero_id'))}"
            elif kind == "troop":
                desc = f"Tropa {_troop_display(params.get('archetype', '?'))}"
            else:
                desc = params.get("unit_id", "?")
            if params.get("killed_by"):
                killer = _pname(state, params.get("killed_by"))
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
        pname = _pname(state, e.get("player_id"))
        src = params.get("source", "?")
        results = params.get("results", [])
        desc = _describe_roll(src, results)
        rolls.append(f"{pname} {src}: {desc}")
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

def _subst_turn_log(text):
    pattern = re.compile(
        r"def show_turn_log\(state\) -> None:.*?(?=\n(?:def |class )|\Z)",
        re.DOTALL,
    )
    return pattern.sub(NEW_LOG.rstrip() + "\n", text, count=1)


# =============================================================
# 8. main.py - reports por povo (via regex, sem substituir inteiro)
# =============================================================
def _patch_reports(text: str) -> str:
    # _relatorio_producao
    text = text.replace(
        '        table.add_row(\n'
        '            p.name, p.people,\n'
        '            str(s.get("gold_collected", 0)),',
        '        table.add_row(\n'
        '            f"{p.name} ({_pcolor(p.people)}|{p.people})",\n'
        '            str(s.get("gold_collected", 0)),',
    )
    return text


# =============================================================
# 9. main.py - HUD colorido
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def show_hud(state) -> None:
    curuna = get_player(state, state.curuna_id)
    console.print(
        f"[bold yellow]T{state.turn} · {state.phase.value.upper()} · "
        f"Curuna: {curuna.name} ({curuna.people})[/bold yellow]   "
        f"[dim][m]apa  [B]oard  [l]og[/dim]"
    )
    for p in state.players:
        if not p.city.is_alive():
            console.print(f"[red]{p.name} ({p.people}) - ELIMINADO[/red]")
            continue
        hero_str = "-"
        for u in p.units:
            if isinstance(u, Hero) and u.is_alive():
                hero_str = f"{heroes.hero_name(u.hero_id)} {u.life}/{u.life_max}"
                break
        name_pad = p.name.ljust(10)
        povo_pad = f"({p.people})".ljust(20)
        console.print(
            f"{name_pad} {povo_pad} "
            f"vida {p.city.life}/{p.city.life_max}  "
            f"ouro {p.city.gold}  magia {p.city.magic}  "
            f"mao {len(p.hand)}  heroi {hero_str}"
        )
    console.print()''',
    '''\
def show_hud(state) -> None:
    curuna = get_player(state, state.curuna_id)
    console.print(
        f"[bold yellow]T{state.turn} · {state.phase.value.upper()} · "
        f"Curuna: {curuna.name} ({curuna.people})[/bold yellow]   "
        f"[dim][m]apa  [B]oard  [l]og[/dim]"
    )
    for p in state.players:
        c = _pcolor(p.people)
        if not p.city.is_alive():
            console.print(f"[{c}]{p.name} ({p.people}) - ELIMINADO[/{c}]")
            continue
        hero_str = "-"
        for u in p.units:
            if isinstance(u, Hero) and u.is_alive():
                hero_str = f"{_hero_short(u.hero_id)} {u.life}/{u.life_max}"
                break
        name_pad = p.name.ljust(10)
        povo_pad = f"({p.people})".ljust(20)
        console.print(
            f"[{c}]{name_pad} {povo_pad}[/{c}] "
            f"vida {p.city.life}/{p.city.life_max}  "
            f"ouro {p.city.gold}  magia {p.city.magic}  "
            f"mao {len(p.hand)}  heroi {hero_str}"
        )
    console.print()'''
))


def _apply_edits(rel_path: str, full: Path, backup_dir: Path) -> bool:
    if not full.exists():
        print(f"AVISO - {rel_path} nao existe ({full}).")
        return False
    original = full.read_text(encoding="utf-8")
    current = original
    applied = 0
    for path, old, new in EDITS:
        if path != rel_path:
            continue
        if old not in current:
            print(f"  AVISO - snippet nao encontrado em {rel_path}:")
            print(f"    {old[:90]}...")
            continue
        current = current.replace(old, new, 1)
        applied += 1

    # Aplicar regex pro show_turn_log (independente dos EDITS)
    if rel_path == "jessica/main.py":
        before = current
        current = _subst_turn_log(current)
        if current != before:
            applied += 1
            print(f"  OK  - show_turn_log substituido via regex")
        else:
            print(f"  AVISO - regex do show_turn_log nao casou.")

        before = current
        current = _patch_reports(current)
        if current != before:
            applied += 1
            print(f"  OK  - reports ajustados")

    if current == original:
        print(f"AVISO - nenhuma edicao aplicada em {rel_path}.")
        return False
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(current, encoding="utf-8")
    print(f"OK  - {rel_path} ({applied} edit(s))")
    return True


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    if not (ROOT / "jessica" / "main.py").exists():
        print(f"ERRO: nao achei {ROOT}/jessica/main.py")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    edited_paths = sorted({e[0] for e in EDITS})
    total = 0
    for rel_path in edited_paths:
        full = ROOT / rel_path
        if _apply_edits(rel_path, full, BACKUP_DIR):
            total += 1

    print(f"\n{total} arquivo(s) modificado(s).")
    print(f"Backup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()