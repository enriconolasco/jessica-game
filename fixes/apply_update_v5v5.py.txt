"""apply_update_v5v5: Cabaca roll, roll humanos no log, tropa special no mapa,
   eventos futuros, turno 13+ bloqueia muralha, resumo do local na noite."""
from pathlib import Path
from datetime import datetime
import os
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v5_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. actions.py - Cabaca roll no log (fix do v5v4b)
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    'def _cabaca_cheia(state, player):\n'
    '    r = state.rng.randint(1, 4)\n'
    '    if r == 1:',
    'def _cabaca_cheia(state, player):\n'
    '    r = state.rng.randint(1, 4)\n'
    '    log(state, f"[ROLL] Cabaca Cheia: 1d4 = {r}")\n'
    '    if r == 1:'
))

# =============================================================
# 2. actions.py - turno 13+ bloqueia subir muralha
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    'def raise_city_life(state: GameState, player_id: int, times: int = 1) -> None:\n'
    '    if times < 1:\n'
    '        raise ActionError("Precisa ao menos 1.")\n'
    '    city = get_city(state, player_id)\n'
    '    player = get_player(state, player_id)\n'
    '    if not city.is_alive():\n'
    '        raise ActionError("Cidade destruida.")',
    'def raise_city_life(state: GameState, player_id: int, times: int = 1) -> None:\n'
    '    if times < 1:\n'
    '        raise ActionError("Precisa ao menos 1.")\n'
    '    if state.turn >= 13:\n'
    '        raise ActionError("Turno 13+: nao pode mais subir muralha.")\n'
    '    city = get_city(state, player_id)\n'
    '    player = get_player(state, player_id)\n'
    '    if not city.is_alive():\n'
    '        raise ActionError("Cidade destruida.")'
))

# =============================================================
# 3. peoples.py - Roça grava rolls no action_log (nao so event_log)
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    'def _humans_roca_de_quilombo(state: GameState, player: Player) -> None:\n'
    '    num_penas = sum(1 for a in player.field_artifacts if a.card_id == "PENA")\n'
    '    num_dice = 1 + num_penas\n'
    '    rolls = [state.rng.randint(1, 4) for _ in range(num_dice)]\n'
    '    log(state, f"{player.name} (Humanos): Roca - {num_dice}D4 = {rolls}.")\n'
    '    for r in rolls:\n'
    '        _apply_roca_result(state, player, r)',
    'def _humans_roca_de_quilombo(state: GameState, player: Player) -> None:\n'
    '    from .state import record_action\n'
    '    num_penas = sum(1 for a in player.field_artifacts if a.card_id == "PENA")\n'
    '    num_dice = 1 + num_penas\n'
    '    rolls = [state.rng.randint(1, 4) for _ in range(num_dice)]\n'
    '    record_action(state, player.id, "roll", source="roca_humanos",\n'
    '                  dice=num_dice, results=list(rolls))\n'
    '    log(state, f"{player.name} (Humanos): Roca - {num_dice}D4 = {rolls}.")\n'
    '    for r in rolls:\n'
    '        _apply_roca_result(state, player, r)'
))

# =============================================================
# 4. main.py - show_turn_log inclui rolls do event_log
# =============================================================
EDITS.append((
    "jessica/main.py",
    '    console.print(f"[bold]TURNO {state.turn} - o que aconteceu ate agora[/bold]")\n'
    '    found = False\n'
    '    for label, items in buckets.items():\n'
    '        if not items:\n'
    '            continue\n'
    '        found = True\n'
    '        for item in items:\n'
    '            console.print(f"[dim][{label}][/dim] {item}")\n'
    '    if not found:\n'
    '        console.print("[dim](nada ainda)[/dim]")\n'
    '    console.print()',
    '    # Rolls: filtra event_log do turno por marcador [ROLL]\n'
    '    prefix = f"[T{state.turn} "\n'
    '    rolls = []\n'
    '    for line in state.event_log:\n'
    '        if not line.startswith(prefix):\n'
    '            continue\n'
    '        idx = line.find("[ROLL]")\n'
    '        if idx >= 0:\n'
    '            rolls.append(line[idx:])\n'
    '    # Roll entries do action_log (Roca e outros)\n'
    '    for e in entries:\n'
    '        if e["action"] != "roll":\n'
    '            continue\n'
    '        params = e.get("params", {})\n'
    '        try:\n'
    '            pname = get_player(state, e["player_id"]).name\n'
    '        except Exception:\n'
    '            pname = f"J{e[\'player_id\']}"\n'
    '        src = params.get("source", "?")\n'
    '        results = params.get("results", [])\n'
    '        rolls.append(f"[ROLL] {pname} {src}: {results}")\n'
    '    console.print(f"[bold]TURNO {state.turn} - o que aconteceu ate agora[/bold]")\n'
    '    found = False\n'
    '    for label, items in buckets.items():\n'
    '        if not items:\n'
    '            continue\n'
    '        found = True\n'
    '        for item in items:\n'
    '            console.print(f"[dim][{label}][/dim] {item}")\n'
    '    if rolls:\n'
    '        found = True\n'
    '        for r in rolls:\n'
    '            console.print(f"[dim][ROLL][/dim] {r}")\n'
    '    if not found:\n'
    '        console.print("[dim](nada ainda)[/dim]")\n'
    '    console.print()'
))

# =============================================================
# 5. main.py - _city_cell_lines: mostra TODAS unidades fisicamente la
# =============================================================
EDITS.append((
    "jessica/main.py",
    'def _city_cell_lines(state, pid: int, width: int) -> list[str]:\n'
    '    player = get_player(state, pid)\n'
    '    city = player.city\n'
    '    mark = " *" if state.curuna_id == pid else ""\n'
    '    povo = player.people[:8]\n'
    '    title = f"J{pid} {player.name[:8]}{mark}"\n'
    '    sub = f"({povo})"\n'
    '    vida = f"Cidade {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"\n'
    '    lines = [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width), _pad(vida, width)]\n'
    '    units = []\n'
    '    for u in player.units:\n'
    '        if u.house == f"city_{pid}":\n'
    '            kind = "H" if isinstance(u, Hero) else "T"\n'
    '            units.append(f"{kind}{u.life}")\n'
    '    if units:\n'
    '        for u in units:\n'
    '            lines.append(_pad(u, width))\n'
    '    else:\n'
    '        lines.append(_pad("[dim]-[/dim]", width))\n'
    '    return lines',
    'def _city_cell_lines(state, pid: int, width: int) -> list[str]:\n'
    '    player = get_player(state, pid)\n'
    '    city = player.city\n'
    '    mark = " *" if state.curuna_id == pid else ""\n'
    '    povo = player.people[:8]\n'
    '    title = f"J{pid} {player.name[:8]}{mark}"\n'
    '    sub = f"({povo})"\n'
    '    vida = f"Cidade {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"\n'
    '    lines = [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width), _pad(vida, width)]\n'
    '    house = f"city_{pid}"\n'
    '    units = []\n'
    '    for p in state.players:\n'
    '        for u in p.units:\n'
    '            if u.house == house and u.is_alive():\n'
    '                kind = "H" if isinstance(u, Hero) else "T"\n'
    '                label = f"{kind}{u.life}"\n'
    '                if p.id != pid:\n'
    '                    label = f"J{p.id} {label}"\n'
    '                units.append(label)\n'
    '    if units:\n'
    '        for u in units:\n'
    '            lines.append(_pad(u, width))\n'
    '    else:\n'
    '        lines.append(_pad("[dim]-[/dim]", width))\n'
    '    return lines'
))

# =============================================================
# 6. main.py - _center_cell_lines: idem
# =============================================================
EDITS.append((
    "jessica/main.py",
    'def _center_cell_lines(state, width: int) -> list[str]:\n'
    '    units = []\n'
    '    for p in state.players:\n'
    '        for u in p.units:\n'
    '            if u.house == CENTER:\n'
    '                kind = "H" if isinstance(u, Hero) else "T"\n'
    '                units.append(f"{p.name[:4]}-{kind}{u.life}")\n'
    '    lines = [_pad("[bold]CENTRO[/bold]", width), _pad("", width)]\n'
    '    if units:\n'
    '        for u in units:\n'
    '            lines.append(_pad(u, width))\n'
    '    else:\n'
    '        lines.append(_pad("[dim]-[/dim]", width))\n'
    '    return lines',
    'def _center_cell_lines(state, width: int) -> list[str]:\n'
    '    units = []\n'
    '    for p in state.players:\n'
    '        for u in p.units:\n'
    '            if u.house == CENTER and u.is_alive():\n'
    '                kind = "H" if isinstance(u, Hero) else "T"\n'
    '                units.append(f"J{p.id}-{kind}{u.life}")\n'
    '    lines = [_pad("[bold]CENTRO[/bold]", width), _pad("", width)]\n'
    '    if units:\n'
    '        for u in units:\n'
    '            lines.append(_pad(u, width))\n'
    '    else:\n'
    '        lines.append(_pad("[dim]-[/dim]", width))\n'
    '    return lines'
))

# =============================================================
# 7. main.py - show_eventos_futuros
# =============================================================
EDITS.append((
    "jessica/main.py",
    'def _menu_informacoes(state, pid: int) -> None:',
    'def show_eventos_futuros(state) -> None:\n'
    '    console.print("[bold]Eventos futuros previstos[/bold]")\n'
    '    found = False\n'
    '    for p in state.players:\n'
    '        if p.city.has_monument and p.city.is_alive():\n'
    '            next_mult = ((state.turn // 4) + 1) * 4\n'
    '            console.print(f"  {p.name}: Monumento -> +1 artefato no turno {next_mult}")\n'
    '            found = True\n'
    '    for p in state.players:\n'
    '        if state.turn < p.spell_cooldown_until_turn and p.city.is_alive():\n'
    '            console.print(f"  {p.name}: Feitico disponivel no turno {p.spell_cooldown_until_turn}")\n'
    '            found = True\n'
    '    for e in state.pending_effects:\n'
    '        try:\n'
    '            pname = get_player(state, e["player_id"]).name\n'
    '        except Exception:\n'
    '            pname = f"J{e.get(\'player_id\', \'?\')}"\n'
    '        kind = e.get("kind", "?")\n'
    '        due = e.get("due_turn", "?")\n'
    '        console.print(f"  {pname}: {kind} no turno {due}")\n'
    '        found = True\n'
    '    for p in state.players:\n'
    '        if (p.people == "filhos_floresta" and p.city.is_alive()\n'
    '                and not p.filhos_bonus_recebido and state.turn < 13):\n'
    '            console.print(f"  {p.name} (Filhos): Florescimento Exuberante no turno 13")\n'
    '            found = True\n'
    '    if state.turn >= 13:\n'
    '        console.print("  [red]Turno 13+ ativo: ninguem pode mais subir muralha.[/red]")\n'
    '    else:\n'
    '        console.print(f"  [dim]A partir do turno 13, ninguem podera subir muralha.[/dim]")\n'
    '    if not found:\n'
    '        console.print("  [dim](nada previsto)[/dim]")\n'
    '    console.print()\n'
    '\n'
    '\n'
    'def _menu_informacoes(state, pid: int) -> None:'
))

# =============================================================
# 8. main.py - adiciona Eventos futuros ao submenu Informacoes
# =============================================================
EDITS.append((
    "jessica/main.py",
    'def _menu_informacoes(state, pid: int) -> None:\n'
    '    opts = [\n'
    '        "Loja",\n'
    '        "Inspecionar local / unidade",\n'
    '        "Artefatos em campo (todos)",\n'
    '        "Passivas ativas",\n'
    '        "Unidades empaladas / infectadas",\n'
    '        "Habilidades (povo, feitico, herois)",\n'
    '        "Voltar",\n'
    '    ]\n'
    '    idx = pick_index("Informacoes", opts)\n'
    '    if idx == 0:\n'
    '        show_loja(state)\n'
    '    elif idx == 1:\n'
    '        estudar_campo(state)\n'
    '    elif idx == 2:\n'
    '        show_active_artifacts(state)\n'
    '    elif idx == 3:\n'
    '        show_passivas_ativas(state)\n'
    '    elif idx == 4:\n'
    '        show_empalados_infectados(state)\n'
    '    elif idx == 5:\n'
    '        show_habilidades(state, pid)',
    'def _menu_informacoes(state, pid: int) -> None:\n'
    '    opts = [\n'
    '        "Loja",\n'
    '        "Inspecionar local / unidade",\n'
    '        "Artefatos em campo (todos)",\n'
    '        "Passivas ativas",\n'
    '        "Unidades empaladas / infectadas",\n'
    '        "Eventos futuros",\n'
    '        "Habilidades (povo, feitico, herois)",\n'
    '        "Voltar",\n'
    '    ]\n'
    '    idx = pick_index("Informacoes", opts)\n'
    '    if idx == 0:\n'
    '        show_loja(state)\n'
    '    elif idx == 1:\n'
    '        estudar_campo(state)\n'
    '    elif idx == 2:\n'
    '        show_active_artifacts(state)\n'
    '    elif idx == 3:\n'
    '        show_passivas_ativas(state)\n'
    '    elif idx == 4:\n'
    '        show_empalados_infectados(state)\n'
    '    elif idx == 5:\n'
    '        show_eventos_futuros(state)\n'
    '    elif idx == 6:\n'
    '        show_habilidades(state, pid)'
))

# =============================================================
# 9. main.py - resumo do local antes de cada declaracao na noite
# =============================================================
EDITS.append((
    "jessica/main.py",
    '            if not any(find_targets(state, u) for u in units_here):\n'
    '                continue\n'
    '            console.print(f"[bold]{player.name} declara ataques em {house_short(state, house)}.[/bold]")',
    '            if not any(find_targets(state, u) for u in units_here):\n'
    '                continue\n'
    '            # Resumo do local + mapa antes de declarar\n'
    '            _mostrar_resumo_local(state, house)\n'
    '            console.print(f"[bold]{player.name} declara ataques em {house_short(state, house)}.[/bold]")'
))

# Helper _mostrar_resumo_local
EDITS.append((
    "jessica/main.py",
    'def _ainai_prompt_all(state, all_pids):',
    'def _mostrar_resumo_local(state, house: str) -> None:\n'
    '    console.print(f"\\n[bold cyan]=== {house_short(state, house)} ===[/bold cyan]")\n'
    '    if house.startswith("city_"):\n'
    '        pid = int(house.split("_")[1])\n'
    '        p = get_player(state, pid)\n'
    '        console.print(f"Cidade: {p.city.life}/{p.city.life_max}")\n'
    '    any_unit = False\n'
    '    for p in state.players:\n'
    '        for u in p.units:\n'
    '            if u.house != house or not u.is_alive():\n'
    '                continue\n'
    '            any_unit = True\n'
    '            tipo = (f"Heroi {heroes.hero_name(u.hero_id)}"\n'
    '                    if isinstance(u, Hero) else f"Tropa {u.archetype.value}")\n'
    '            flags = []\n'
    '            if u.double_damage:\n'
    '                flags.append("2xdano")\n'
    '            if u.resistance_stacks:\n'
    '                flags.append(f"resx{u.resistance_stacks}")\n'
    '            if u.statuses.get("invisivel_until_turn", -1) >= state.turn:\n'
    '                flags.append("invisivel")\n'
    '            if u.statuses.get("sono_until_turn", -1) > state.turn:\n'
    '                flags.append("dormindo")\n'
    '            if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn:\n'
    '                flags.append("amaldicoado")\n'
    '            if u.statuses.get("k_s_active"):\n'
    '                flags.append("Ks")\n'
    '            flags_str = f" [{", ".join(flags)}]" if flags else ""\n'
    '            console.print(f"  {p.name}: {u.id} ({tipo}) {u.life}/{u.life_max}{flags_str}")\n'
    '    if not any_unit:\n'
    '        console.print("  [dim](vazio)[/dim]")\n'
    '    show_map(state)\n'
    '    console.print()\n'
    '\n'
    '\n'
    'def _ainai_prompt_all(state, all_pids):'
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