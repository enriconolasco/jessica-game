"""apply_update_v5v4: reorganizacao de menus + bugs (empala/espectro/Q_C/MV/ordem/seed)."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v4_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}
EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. setup.py - turn_order fixo [1,2,3,4] (anti-horario no mapa)
# =============================================================
EDITS.append((
    "jessica/core/setup.py",
    '''\
    state.curuna_id = order[0]
    log(state, f"Curuna inicial: J{state.curuna_id}")''',
    '''\
    state.curuna_id = order[0]
    # Ordem de jogo fixa: anti-horario no mapa (baixo -> direita -> cima -> esquerda)
    state.turn_order = [1, 2, 3, 4]
    log(state, f"Ordem de jogo (anti-horaria): {state.turn_order}")
    log(state, f"Curuna inicial: J{state.curuna_id}")'''
))

# =============================================================
# 2. actions.py - Levantar Mortos valida arquetipos
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '''\
def _spell_levantar_mortos(state, player, choice):
    arqs = choice.get("archetypes", [])
    if len(arqs) != 2:
        raise ActionError("Escolha 2 arquetipos diferentes.")
    if arqs[0] == arqs[1]:
        raise ActionError("Precisa ser diferentes.")
    for arq_name in arqs:
        arq = TroopArchetype(arq_name)''',
    '''\
def _spell_levantar_mortos(state, player, choice):
    arqs = choice.get("archetypes", [])
    if len(arqs) != 2:
        raise ActionError("Escolha 2 arquetipos diferentes.")
    if arqs[0] == arqs[1]:
        raise ActionError("Precisa ser diferentes.")
    disponiveis = {a.value for a in peoples.available_archetypes(player, state)}
    for arq_name in arqs:
        if arq_name not in disponiveis:
            raise ActionError(f"Arquetipo {arq_name} nao disponivel (precisa Zoia viva).")
        arq = TroopArchetype(arq_name)'''
))

# =============================================================
# 3. peoples.py - Dracula cura ao empalar; espectro nao gera espectro; log Caroco
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    '''\
    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if heroes.has_ability(u.hero_id, "empala_on_kill"):
            sig = unit_signature(dead_unit)
            if sig not in victim_owner.empalados:
                victim_owner.empalados.append(sig)
                log(state, f"  {dead_unit.id} empalado por Dracula (dono {victim_owner.name}).")
            if killer_player.spell_cooldown_until_turn > state.turn:
                killer_player.spell_cooldown_until_turn = 0
                log(state, "  Dracula: feitico sai da recarga.")''',
    '''\
    for u in killer_player.units:
        if not (isinstance(u, Hero) and u.is_alive()):
            continue
        if heroes.has_ability(u.hero_id, "empala_on_kill"):
            sig = unit_signature(dead_unit)
            if sig not in victim_owner.empalados:
                victim_owner.empalados.append(sig)
                log(state, f"  {dead_unit.id} empalado por Dracula (dono {victim_owner.name}).")
                # Dracula cura 2 ao empalar
                if u.life < u.life_max:
                    before = u.life
                    u.life = min(u.life_max, u.life + 2)
                    log(state, f"  {u.id} curou +{u.life - before} (Empalar).")
            if killer_player.spell_cooldown_until_turn > state.turn:
                killer_player.spell_cooldown_until_turn = 0
                log(state, "  Dracula: feitico sai da recarga.")'''
))

EDITS.append((
    "jessica/core/peoples.py",
    '''\
    if isinstance(dead_unit, Hero):
        for p in state.players:
            for u in p.units:
                if (isinstance(u, Hero) and u.is_alive()
                        and u.hero_id == "cobra"):
                    state.espectros_pendentes.append({
                        "hero_id": dead_unit.hero_id,
                        "house": dead_unit.house,
                        "owner_of_cobra": p.id,
                        "original_owner_id": dead_unit.owner_id,
                    })
                    log(state, f"  Espectro agendado: {dead_unit.hero_id} em {dead_unit.house}.")''',
    '''\
    if isinstance(dead_unit, Hero) and "espectro_until_turn" not in dead_unit.statuses:
        for p in state.players:
            for u in p.units:
                if (isinstance(u, Hero) and u.is_alive()
                        and u.hero_id == "cobra"):
                    state.espectros_pendentes.append({
                        "hero_id": dead_unit.hero_id,
                        "house": dead_unit.house,
                        "owner_of_cobra": p.id,
                        "original_owner_id": dead_unit.owner_id,
                    })
                    log(state, f"  Espectro agendado: {dead_unit.hero_id} em {dead_unit.house}.")'''
))

EDITS.append((
    "jessica/core/peoples.py",
    '''\
def _cabaca_cheia(state, player):
    r = state.rng.randint(1, 4)
    if r == 1:''',
    '''\
def _cabaca_cheia(state, player):
    r = state.rng.randint(1, 4)
    log(state, f"[ROLL] Cabaca Cheia: 1d4 = {r}")
    if r == 1:'''
))

# =============================================================
# 4. combat.py - log de roll da Iuna
# =============================================================
EDITS.append((
    "jessica/core/combat.py",
    '''\
def _compute_attack_damage(state: GameState, attacker: Unit, base: int,
                           target: Unit | None = None) -> int:
    if _hero_has(attacker, "deals_1_to_4_damage") and target is not None:
        base = state.rng.randint(1, 4)
    return base * _attack_multiplier(state, attacker, target)''',
    '''\
def _compute_attack_damage(state: GameState, attacker: Unit, base: int,
                           target: Unit | None = None) -> int:
    if _hero_has(attacker, "deals_1_to_4_damage") and target is not None:
        roll = state.rng.randint(1, 4)
        log(state, f"    [ROLL] Iuna: 1d4 = {roll}")
        base = roll
    return base * _attack_multiplier(state, attacker, target)'''
))

# =============================================================
# 5. artifacts_effects.py - Q_C descartado no fim do turno
# =============================================================
EDITS.append((
    "jessica/core/artifacts_effects.py",
    '''\
def _restore_controlled_units(state: GameState) -> None:
    for p in state.players:
        for u in list(p.units):
            if u.original_owner_id is not None:
                orig = get_player(state, u.original_owner_id)
                p.units.remove(u)
                orig.units.append(u)
                u.owner_id = u.original_owner_id
                u.original_owner_id = None
                log(state, f"  {u.id} voltou ao controle de {orig.name}.")''',
    '''\
def _restore_controlled_units(state: GameState) -> None:
    from .actions import discard_field_artifact
    for p in state.players:
        for u in list(p.units):
            if u.original_owner_id is not None:
                orig = get_player(state, u.original_owner_id)
                p.units.remove(u)
                orig.units.append(u)
                u.owner_id = u.original_owner_id
                u.original_owner_id = None
                log(state, f"  {u.id} voltou ao controle de {orig.name}.")
    # Q_C (Almas Acorrentadas) expira com o controle
    for p in state.players:
        to_discard = [a.card_id for a in p.field_artifacts if a.card_id == "Q_C"]
        for _ in to_discard:
            try:
                discard_field_artifact(state, p.id, "Q_C")
                log(state, f"  {p.name}: Q_C (Almas Acorrentadas) expirou.")
            except Exception:
                pass'''
))

# =============================================================
# 6. main.py - substituicoes cirurgicas
# =============================================================

# 6a. _get_actions: nova versao enxuta
EDITS.append((
    "jessica/main.py",
    '''\
def _get_actions(state, player) -> list[tuple[str, str, str]]:
    sp = spells_mod.spell_for_people(player.people)

    r = []
    r.append(("Turno", "1", "Acoes (coletar, invocar, mover, monumento)"))
    r.append(("Turno", "2", "Artefatos (comprar, transmutar, vender, jogar)"))
    r.append(("Turno", "3", f"Lancar feitico: {sp.name}" if sp else "Lancar feitico"))''',
    '''\
def _get_actions(state, player) -> list[tuple[str, str, str]]:
    sp = spells_mod.spell_for_people(player.people)

    r = []
    r.append(("Turno", "1", "Acoes (coletar, invocar, mover, monumento)"))
    r.append(("Turno", "2", "Artefatos (comprar, transmutar, vender, jogar)"))
    r.append(("Turno", "3", f"Lancar feitico: {sp.name}" if sp else "Lancar feitico"))
    r.append(("Turno", "4", "Especiais (herois, habilidades)"))'''
))

EDITS.append((
    "jessica/main.py",
    '''\
    r.append(("Analisar", "E", "Analisar campo de batalha"))
    r.append(("Atalhos", "m", "Mapa"))
    r.append(("Atalhos", "B", "Panorama (Board)"))
    r.append(("Atalhos", "l", "Log do turno"))
    r.append(("Relatorios", "R", "Relatorios (producao, combate)"))
    r.append(("Ajuda", "?", "Ajuda"))
    r.append(("Menu", "M", "Menu do sistema"))
    return r''',
    '''\
    r.append(("Info", "i", "Informacoes"))
    r.append(("Info", "m", "Mapa"))
    r.append(("Info", "p", "Panorama (Board)"))
    r.append(("Info", "l", "Log do turno"))
    r.append(("Info", "r", "Relatorios"))
    r.append(("Info", "?", "Ajuda"))
    r.append(("Info", "x", "Menu do sistema"))
    return r'''
))

# 6b. Trocar _menu_analisar por _menu_informacoes + _menu_especiais
EDITS.append((
    "jessica/main.py",
    '''\
def _menu_analisar(state, pid: int) -> None:
    opts = [
        "Mapa",
        "Panorama (Board)",
        "Loja",
        "Inspecionar local / unidade",
        "Artefatos em campo (todos)",
        "Passivas ativas",
        "Habilidades (povo, feitico, herois)",
        "Voltar",
    ]
    idx = pick_index("Analisar campo de batalha", opts)
    if idx == 0:
        show_map(state)
    elif idx == 1:
        show_board(state)
    elif idx == 2:
        show_loja(state)
    elif idx == 3:
        estudar_campo(state)
    elif idx == 4:
        show_active_artifacts(state)
    elif idx == 5:
        show_passivas_ativas(state)
    elif idx == 6:
        show_habilidades(state, pid)''',
    '''\
def _menu_informacoes(state, pid: int) -> None:
    opts = [
        "Loja",
        "Inspecionar local / unidade",
        "Artefatos em campo (todos)",
        "Passivas ativas",
        "Unidades empaladas / infectadas",
        "Habilidades (povo, feitico, herois)",
        "Voltar",
    ]
    idx = pick_index("Informacoes", opts)
    if idx == 0:
        show_loja(state)
    elif idx == 1:
        estudar_campo(state)
    elif idx == 2:
        show_active_artifacts(state)
    elif idx == 3:
        show_passivas_ativas(state)
    elif idx == 4:
        show_empalados_infectados(state)
    elif idx == 5:
        show_habilidades(state, pid)


def show_empalados_infectados(state) -> None:
    console.print("[bold]Empalados (nao podem ser reinvocados)[/bold]")
    found = False
    for p in state.players:
        if p.empalados:
            found = True
            for sig in p.empalados:
                console.print(f"  {p.name}: {sig['kind']} {sig['id']}")
    if not found:
        console.print("  [dim](nenhum)[/dim]")
    console.print()
    console.print("[bold]Infectados (viram Lobisomem em Lua Cheia)[/bold]")
    found = False
    for p in state.players:
        if p.infectados:
            found = True
            for sig in p.infectados:
                console.print(f"  {p.name}: {sig['kind']} {sig['id']}")
    if not found:
        console.print("  [dim](nenhum)[/dim]")
    console.print()


def _menu_especiais(state, pid: int) -> str | None:
    player = get_player(state, pid)
    opts = []
    keys = []
    if player.people == "gnomos_duendes" and player.bets_need_realocacao:
        opts.append("Alocar apostas do turno")
        keys.append("A")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto" for u in player.units):
        opts.append("Miyamoto: atacar de Dia")
        keys.append("d")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "arken" for u in player.units) \\
            and player.arken_espolia_used_turn != state.turn:
        opts.append("Arken: Espoliar")
        keys.append("e")
    tintin = next((u for u in player.units
                   if isinstance(u, Hero) and u.is_alive() and u.hero_id == "tintin"), None)
    if tintin is not None and tintin.statuses.get("tintin_cooldown_until_turn", -1) <= state.turn:
        opts.append("Tin Tin: ficar invisivel")
        keys.append("t")
    dandara = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "dandara"), None)
    if dandara is not None and dandara.statuses.get("dandara_cooldown_until_turn", -1) <= state.turn:
        opts.append("Dandara: invisibilidade de grupo")
        keys.append("y")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa" for u in player.units) \\
            and not player.has_cast_spell_this_turn:
        opts.append("Luide Vampa: movimento noturno")
        keys.append("z")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "guarari" for u in player.units):
        opts.append("Guarari: transformar tropa em Centauro (2 Magia)")
        keys.append("q")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "aiquara" for u in player.units):
        opts.append("Aiquara: controlar inimigo")
        keys.append("i")
    if (player.people == "filhos_floresta"
            and not any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "baoba_ba"
                        for u in player.units)):
        opts.append(f"Baoba-ba: pagar Magia ({player.baoba_pagamentos}/3)")
        keys.append("b")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "bimbo_do_mal" for u in player.units):
        opts.append(f"Bimbo ({player.correct_bets} apostas corretas)")
        keys.append("p")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zebum" for u in player.units):
        opts.append("Zebum: invocar/reinvocar heroi")
        keys.append("g")
    if player.pending_heals > 0:
        opts.append(f"Usar cura pendente ({player.pending_heals})")
        keys.append("h")
    if not opts:
        console.print("[dim]Sem acoes especiais disponiveis.[/dim]")
        return None
    opts.append("Voltar")
    idx = pick_index("Especiais", opts)
    if idx == len(opts) - 1:
        return None
    return _do_action(state, pid, keys[idx])'''
))

# 6c. handle_action: router trata 4, i, p, x
EDITS.append((
    "jessica/main.py",
    '''\
def handle_action(state, pid: int, choice: str) -> str | None:
    """Router: submenus para [1]/[2]/[3]; resto vai direto pro _do_action."""
    if choice == "1":
        return _menu_acoes_turno(state, pid)
    if choice == "2":
        return _menu_artefatos(state, pid)
    if choice == "3":
        return _do_action(state, pid, "f")
    return _do_action(state, pid, choice)''',
    '''\
def handle_action(state, pid: int, choice: str) -> str | None:
    if choice == "1":
        return _menu_acoes_turno(state, pid)
    if choice == "2":
        return _menu_artefatos(state, pid)
    if choice == "3":
        return _do_action(state, pid, "f")
    if choice == "4":
        return _menu_especiais(state, pid)
    if choice == "i":
        _menu_informacoes(state, pid)
        return None
    if choice == "m":
        show_map(state)
        return None
    if choice == "p":
        show_board(state)
        return None
    if choice == "l":
        show_turn_log(state)
        return None
    if choice == "r":
        _menu_relatorios(state, pid)
        return None
    if choice == "?":
        _menu_ajuda(state, pid)
        return None
    if choice == "x":
        return _menu_sistema(state, pid)
    return _do_action(state, pid, choice)'''
))

# 6d. _do_action: remove branches antigos (E, B, M, R, ?) porque o router trata
EDITS.append((
    "jessica/main.py",
    '''\
    elif choice == "E":
        _menu_analisar(state, pid)
    elif choice == "m":
        show_map(state)
    elif choice == "B":
        show_board(state)
    elif choice == "l":
        show_turn_log(state)
    elif choice == "R":
        _menu_relatorios(state, pid)
    elif choice == "?":
        _menu_ajuda(state, pid)
    elif choice == "M":
        result = _menu_sistema(state, pid)
        if result:
            return result''',
    '''\
'''
))

# 6e. _city_cell_lines: uma unidade por linha (expande verticalmente)
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
    units = []
    for u in player.units:
        if u.house == f"city_{pid}":
            kind = "H" if isinstance(u, Hero) else "T"
            units.append(f"{kind}{u.life}")
    units_str = ", ".join(units) if units else "[dim]-[/dim]"
    return [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width),
            _pad(vida, width), _pad(units_str, width)]''',
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
    units = []
    for u in player.units:
        if u.house == f"city_{pid}":
            kind = "H" if isinstance(u, Hero) else "T"
            units.append(f"{kind}{u.life}")
    if units:
        for u in units:
            lines.append(_pad(u, width))
    else:
        lines.append(_pad("[dim]-[/dim]", width))
    return lines'''
))

# 6f. setup_ui: seed aleatorio
EDITS.append((
    "jessica/main.py",
    '''\
    console.print()
    seed = DEFAULT_SEED
    console.print(f"[dim]Seed: {seed}[/dim]\\n")''',
    '''\
    console.print()
    import random as _rnd
    default_seed = _rnd.randint(1, 999999999)
    seed = _ask_int(f"Seed (mesma seed = mesma partida) [{default_seed}]",
                    default=default_seed, min_val=1, max_val=999999999)
    console.print(f"[dim]Seed: {seed}[/dim]\\n")'''
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