"""apply_update_v5v1: HUD, Board, Log do turno, submenus Analisar/Menu, tracking."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5v1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. models.py - Player.stats
# =============================================================
EDITS.append((
    "jessica/core/models.py",
    "    garoche_life_max_bonus: int = 0\n",
    "    garoche_life_max_bonus: int = 0\n\n"
    "    # Estatisticas acumuladas da partida\n"
    "    stats: dict = field(default_factory=dict)\n"
))

# =============================================================
# 2. serialize.py - persistir stats
# =============================================================
EDITS.append((
    "jessica/core/serialize.py",
    '        "garoche_life_max_bonus": p.garoche_life_max_bonus,\n',
    '        "garoche_life_max_bonus": p.garoche_life_max_bonus,\n'
    '        "stats": dict(p.stats),\n'
))
EDITS.append((
    "jessica/core/serialize.py",
    '        garoche_life_max_bonus=d.get("garoche_life_max_bonus", 0),\n',
    '        garoche_life_max_bonus=d.get("garoche_life_max_bonus", 0),\n'
    '        stats=dict(d.get("stats", {})),\n'
))

# =============================================================
# 3. state.py - helper bump_stat
# =============================================================
EDITS.append((
    "jessica/core/state.py",
    '''\
def record_action(state: GameState, player_id: int, action: str, **params) -> None:''',
    '''\
def bump_stat(state: GameState, player_id: int, key: str, amount: int = 1) -> None:
    player = get_player(state, player_id)
    player.stats[key] = player.stats.get(key, 0) + amount


def record_action(state: GameState, player_id: int, action: str, **params) -> None:'''
))

# =============================================================
# 4. actions.py - hooks de stats + importar bump_stat
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    "from .state import get_player, get_city, log, record_action",
    "from .state import get_player, get_city, log, record_action, bump_stat"
))

EDITS.append((
    "jessica/core/actions.py",
    '    city.gold += gold_amount\n'
    '    city.magic += magic_amount\n'
    '    player.has_collected_this_turn = True\n'
    '    record_action(state, player_id, "collect_resources", gold=gold_amount, magic=magic_amount)',
    '    city.gold += gold_amount\n'
    '    city.magic += magic_amount\n'
    '    player.has_collected_this_turn = True\n'
    '    bump_stat(state, player_id, "gold_collected", gold_amount)\n'
    '    bump_stat(state, player_id, "magic_collected", magic_amount)\n'
    '    record_action(state, player_id, "collect_resources", gold=gold_amount, magic=magic_amount)'
))

EDITS.append((
    "jessica/core/actions.py",
    '    city.gold -= total_cost\n'
    '    city.life += times\n'
    '    record_action(state, player_id, "raise_city_life", times=times)',
    '    city.gold -= total_cost\n'
    '    city.life += times\n'
    '    bump_stat(state, player_id, "city_life_raised", times)\n'
    '    record_action(state, player_id, "raise_city_life", times=times)'
))

EDITS.append((
    "jessica/core/actions.py",
    '    record_action(state, player_id, "summon_troop", archetype=archetype.value, life=life)\n'
    '    log(state, f"{player.name} invocou tropa {archetype.value} ({life}/{max_life}) em {target_house}.")',
    '    bump_stat(state, player_id, "troops_summoned")\n'
    '    record_action(state, player_id, "summon_troop", archetype=archetype.value, life=life)\n'
    '    log(state, f"{player.name} invocou tropa {archetype.value} ({life}/{max_life}) em {target_house}.")'
))

EDITS.append((
    "jessica/core/actions.py",
    '    player.units.append(hero)\n'
    '    record_action(state, player_id, "summon_hero", hero_id=hdef.hero_id)\n'
    '    log(state, f"{player.name} invocou {hdef.name} ({hero_life_max}).")',
    '    player.units.append(hero)\n'
    '    bump_stat(state, player_id, "heroes_summoned")\n'
    '    record_action(state, player_id, "summon_hero", hero_id=hdef.hero_id)\n'
    '    log(state, f"{player.name} invocou {hdef.name} ({hero_life_max}).")'
))

EDITS.append((
    "jessica/core/actions.py",
    '    card = state.shop.draw_random(state.rng)\n'
    '    player.hand.append(card)\n'
    '    record_action(state, player_id, "buy_artifact_gold", card=card)\n'
    '    log(state, f"{player.name} comprou: {card_display(card)}.")\n'
    '    peoples.on_action_performed(state, player_id, "buy_artifact_gold")',
    '    card = state.shop.draw_random(state.rng)\n'
    '    player.hand.append(card)\n'
    '    bump_stat(state, player_id, "artifacts_bought")\n'
    '    record_action(state, player_id, "buy_artifact_gold", card=card)\n'
    '    log(state, f"{player.name} comprou: {card_display(card)}.")\n'
    '    peoples.on_action_performed(state, player_id, "buy_artifact_gold")'
))

EDITS.append((
    "jessica/core/actions.py",
    '    card = state.shop.draw_random(state.rng)\n'
    '    player.hand.append(card)\n'
    '    record_action(state, player_id, "transmute_artifact_magic", card=card)\n'
    '    log(state, f"{player.name} transmutou: {card_display(card)}.")\n'
    '    peoples.on_action_performed(state, player_id, "transmute_artifact_magic")',
    '    card = state.shop.draw_random(state.rng)\n'
    '    player.hand.append(card)\n'
    '    bump_stat(state, player_id, "artifacts_bought")\n'
    '    record_action(state, player_id, "transmute_artifact_magic", card=card)\n'
    '    log(state, f"{player.name} transmutou: {card_display(card)}.")\n'
    '    peoples.on_action_performed(state, player_id, "transmute_artifact_magic")'
))

EDITS.append((
    "jessica/core/actions.py",
    '    state.shop.return_card(card_id)\n'
    '    record_action(state, player_id, "sell_artifact", card=card_id)\n'
    '    log(state, f"{player.name} vendeu {card_display(card_id)}.")',
    '    state.shop.return_card(card_id)\n'
    '    bump_stat(state, player_id, "artifacts_sold")\n'
    '    record_action(state, player_id, "sell_artifact", card=card_id)\n'
    '    log(state, f"{player.name} vendeu {card_display(card_id)}.")'
))

EDITS.append((
    "jessica/core/actions.py",
    '    _apply_valendar_bonus(state, player, card_id)\n'
    '    record_action(state, player_id, "play_artifact", card=card_id, choice=choice)',
    '    _apply_valendar_bonus(state, player, card_id)\n'
    '    bump_stat(state, player_id, "artifacts_played")\n'
    '    record_action(state, player_id, "play_artifact", card=card_id, choice=choice)'
))

EDITS.append((
    "jessica/core/actions.py",
    '    player.has_cast_spell_this_turn = True\n'
    '    if not no_cooldown:\n'
    '        player.spell_cooldown_until_turn = state.turn + 2\n'
    '    record_action(state, player_id, "cast_spell", spell=sp.spell_id)',
    '    player.has_cast_spell_this_turn = True\n'
    '    if not no_cooldown:\n'
    '        player.spell_cooldown_until_turn = state.turn + 2\n'
    '    bump_stat(state, player_id, "spells_cast")\n'
    '    record_action(state, player_id, "cast_spell", spell=sp.spell_id)'
))

# =============================================================
# 5. combat.py - hooks de stats (dano/kills/deaths) + record_action
# =============================================================
EDITS.append((
    "jessica/core/combat.py",
    "from .state import get_player, get_city, log",
    "from .state import get_player, get_city, log, record_action, bump_stat"
))

EDITS.append((
    "jessica/core/combat.py",
    '    log(state, f"  {attacker.id} ({attacker_player.name}) atacou "\n'
    '               f"{target.id} ({target_player.name}): "\n'
    '               f"{attacker.id} {atk_life} -> {attacker.life}, "\n'
    '               f"{target.id} {tgt_life} -> {target.life}{extra}.")',
    '    bump_stat(state, attacker.owner_id, "damage_dealt", dmg_to_target)\n'
    '    bump_stat(state, target.owner_id, "damage_taken", dmg_to_target)\n'
    '    bump_stat(state, target.owner_id, "damage_dealt", dmg_to_attacker)\n'
    '    bump_stat(state, attacker.owner_id, "damage_taken", dmg_to_attacker)\n'
    '    record_action(state, attacker.owner_id, "attack",\n'
    '                  target_id=target.id, damage=dmg_to_target,\n'
    '                  retaliation=dmg_to_attacker)\n'
    '    log(state, f"  {attacker.id} ({attacker_player.name}) atacou "\n'
    '               f"{target.id} ({target_player.name}): "\n'
    '               f"{attacker.id} {atk_life} -> {attacker.life}, "\n'
    '               f"{target.id} {tgt_life} -> {target.life}{extra}.")'
))

EDITS.append((
    "jessica/core/combat.py",
    '        log(state, f"  {attacker.id} ({attacker_name}) atacou Cidade de "\n'
    '                   f"{target_player.name}: {life_before} -> {city.life}.")',
    '        bump_stat(state, attacker.owner_id, "damage_dealt", dmg_to_city)\n'
    '        bump_stat(state, target_pid, "damage_taken", dmg_to_city)\n'
    '        record_action(state, attacker.owner_id, "attack_city",\n'
    '                      target_player_id=target_pid, damage=dmg_to_city)\n'
    '        log(state, f"  {attacker.id} ({attacker_name}) atacou Cidade de "\n'
    '                   f"{target_player.name}: {life_before} -> {city.life}.")'
))

EDITS.append((
    "jessica/core/combat.py",
    '    for player in state.players:\n'
    '        dead = [u for u in player.units if not u.is_alive()]\n'
    '        for u in dead:\n'
    '            log(state, f"  {u.id} ({player.name}) morreu.")\n'
    '        player.units = [u for u in player.units if u.is_alive()]',
    '    for player in state.players:\n'
    '        dead = [u for u in player.units if not u.is_alive()]\n'
    '        for u in dead:\n'
    '            bump_stat(state, player.id, "deaths")\n'
    '            record_action(state, player.id, "unit_died",\n'
    '                          unit_id=u.id, house=u.house,\n'
    '                          killed_by=u.killed_by_player_id)\n'
    '            log(state, f"  {u.id} ({player.name}) morreu.")\n'
    '        player.units = [u for u in player.units if u.is_alive()]'
))

# =============================================================
# 6. peoples.py - kills por matador
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    "from .state import get_player, log",
    "from .state import get_player, log, bump_stat"
))

EDITS.append((
    "jessica/core/peoples.py",
    '    on_action_performed(state, killer_player_id, "kill")',
    '    bump_stat(state, killer_player_id, "kills")\n'
    '    on_action_performed(state, killer_player_id, "kill")'
))

# =============================================================
# 7. main.py - helpers novos (HUD, Board, Log, submenus)
# =============================================================
NEW_HELPERS = '''\
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
    console.print()


def show_board(state) -> None:
    show_map(state)
    console.print()
    console.print("[bold]UNIDADES VIVAS POR CASA[/bold]")
    houses = [CENTER] + [f"city_{p.id}" for p in state.players]
    for house in houses:
        lines = []
        for p in state.players:
            for u in p.units:
                if u.house != house or not u.is_alive():
                    continue
                if isinstance(u, Hero):
                    kind = heroes.hero_name(u.hero_id)
                else:
                    kind = f"Tropa {u.archetype.value}"
                flags = []
                if u.double_damage:
                    flags.append("2xdano")
                if u.resistance_stacks:
                    flags.append(f"resx{u.resistance_stacks}")
                if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
                    flags.append("invis")
                if u.statuses.get("sono_until_turn", -1) > state.turn:
                    flags.append("dormindo")
                if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
                    flags.append("amaldicoado")
                if u.statuses.get("k_s_active"):
                    flags.append("Ks")
                if u.statuses.get("morcego_until_turn", -1) >= state.turn:
                    flags.append("morcego")
                if u.statuses.get("lobisomem_until_turn", -1) >= state.turn:
                    flags.append("lobisomem")
                flags_str = f" [{', '.join(flags)}]" if flags else ""
                lines.append(f"    {p.name[:6]} · {u.id} ({kind}) {u.life}/{u.life_max}{flags_str}")
        label = house_short(state, house)
        if lines:
            console.print(f"  [bold]{label}:[/bold]")
            for ln in lines:
                console.print(ln)
        else:
            console.print(f"  [dim]{label}: (vazio)[/dim]")


def show_turn_log(state) -> None:
    entries = [e for e in state.action_log if e["turn"] == state.turn]
    buckets: dict[str, list[str]] = {
        "MOV": [], "SUM": [], "ART": [], "FEIT": [], "COMB": [], "MORTE": [],
    }
    for e in entries:
        a = e["action"]
        params = e.get("params", {})
        try:
            pname = get_player(state, e["player_id"]).name
        except Exception:
            pname = f"J{e['player_id']}"
        if a == "move_unit":
            buckets["MOV"].append(
                f"{pname}: {params.get('unit_id')} "
                f"{params.get('origin')} -> {params.get('destination')}"
            )
        elif a == "summon_troop":
            buckets["SUM"].append(
                f"{pname}: tropa {params.get('archetype')} "
                f"({params.get('life')} vida)"
            )
        elif a == "summon_hero":
            buckets["SUM"].append(f"{pname}: heroi {params.get('hero_id')}")
        elif a == "play_artifact":
            buckets["ART"].append(f"{pname}: jogou {params.get('card')}")
        elif a == "buy_artifact_gold":
            buckets["ART"].append(f"{pname}: comprou {params.get('card')} (ouro)")
        elif a == "transmute_artifact_magic":
            buckets["ART"].append(f"{pname}: transmutou {params.get('card')}")
        elif a == "sell_artifact":
            buckets["ART"].append(f"{pname}: vendeu {params.get('card')}")
        elif a == "cast_spell":
            buckets["FEIT"].append(f"{pname}: {params.get('spell')}")
        elif a == "attack":
            buckets["COMB"].append(
                f"{pname}: atacou {params.get('target_id')} "
                f"(dano {params.get('damage')}, ret {params.get('retaliation')})"
            )
        elif a == "attack_city":
            buckets["COMB"].append(
                f"{pname}: atacou cidade J{params.get('target_player_id')} "
                f"(dano {params.get('damage')})"
            )
        elif a == "unit_died":
            buckets["MORTE"].append(
                f"{pname}: {params.get('unit_id')} morreu em {params.get('house')}"
            )
    console.print(f"[bold]TURNO {state.turn} - o que aconteceu ate agora[/bold]")
    found = False
    for label, items in buckets.items():
        if not items:
            continue
        found = True
        for item in items:
            console.print(f"[dim][{label}][/dim] {item}")
    if not found:
        console.print("[dim](nada ainda)[/dim]")
    console.print()


def show_passivas_ativas(state) -> None:
    console.print("[bold]STATUSES / PASSIVAS ATIVAS[/bold]")
    found = False
    for p in state.players:
        if p.double_damage_until_end_night:
            console.print(f"  {p.name}: dobro de dano (Qs)")
            found = True
        if p.invulnerable_until_end_turn:
            console.print(f"  {p.name}: invulneravel (Qh)")
            found = True
        if p.armor_active_until_turn >= state.turn:
            console.print(f"  {p.name}: Armadura de Ouro ativa")
            found = True
        for u in p.units:
            if u.statuses.get("k_s_active"):
                console.print(f"  {p.name} {u.id}: Ks (dobro de ataques)")
                found = True
    if not found:
        console.print("  [dim](nenhum)[/dim]")
    console.print()


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
        show_habilidades(state, pid)


def _menu_sistema(state, pid: int) -> str | None:
    opts = [
        "Colher de cha (refazer meu turno)",
        "Mola (voltar ao jogador anterior)",
        "Recomecar jogo",
        "Voltar",
    ]
    idx = pick_index("Menu", opts)
    if idx == 0:
        return "undo"
    if idx == 1:
        return "mola"
    if idx == 2:
        return "restart"
    return None


'''

EDITS.append((
    "jessica/main.py",
    "class RestartGame(Exception):\n    pass\n",
    "class RestartGame(Exception):\n    pass\n\n\n" + NEW_HELPERS
))

# =============================================================
# 8. main.py - _get_actions: substitui Info/Sistema por Analisar/Menu/Atalhos
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    r.append(("Info", "r", f"Resumo"))
    r.append(("Info", "m", "Mapa"))
    r.append(("Info", "l", "Loja"))
    r.append(("Info", "k", "Habilidades"))
    r.append(("Info", "v", "Estudar campo de batalha"))
    r.append(("Info", "j", "Historico de acoes"))
    r.append(("Info", "n", "Artefatos ativos"))

    r.append(("Sistema", "u", "Colher de cha (refazer meu dia)"))
    r.append(("Sistema", "w", "Mola (jogador anterior)"))
    r.append(("Sistema", "x", "Reiniciar partida"))
    return r''',
    '''\
    r.append(("Analisar", "E", "Analisar campo de batalha"))
    r.append(("Atalhos", "m", "Mapa"))
    r.append(("Atalhos", "B", "Panorama (Board)"))
    r.append(("Atalhos", "l", "Log do turno"))
    r.append(("Menu", "M", "Menu do sistema"))
    return r'''
))

# =============================================================
# 9. main.py - handle_action: remove branches antigas, adiciona novas
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    elif choice == "r":
        show_resumo(state)
    elif choice == "m":
        show_map(state)
    elif choice == "l":
        show_loja(state)
    elif choice == "k":
        show_habilidades(state, pid)
    elif choice == "v":
        estudar_campo(state)
    elif choice == "j":
        historico(state)
    elif choice == "n":
        show_active_artifacts(state)''',
    '''\
    elif choice == "E":
        _menu_analisar(state, pid)
    elif choice == "m":
        show_map(state)
    elif choice == "B":
        show_board(state)
    elif choice == "l":
        show_turn_log(state)
    elif choice == "M":
        result = _menu_sistema(state, pid)
        if result:
            return result'''
))

EDITS.append((
    "jessica/main.py",
    '''\
    elif choice == "u":
        return "undo"
    elif choice == "w":
        return "mola"
    elif choice == "x":
        return "restart"
    return None''',
    '''\
    return None'''
))

# =============================================================
# 10. main.py - run_player_day chama HUD no topo
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    while True:
        show_state_for_player(state, pid)
        choice = menu_player_actions(state, player)''',
    '''\
    while True:
        show_hud(state)
        show_state_for_player(state, pid)
        choice = menu_player_actions(state, player)'''
))

# =============================================================
# 11. main.py - run_night_phase chama HUD uma vez
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_map(state)''',
    '''\
def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_hud(state)
    show_map(state)'''
))


def _apply_edits(rel_path: str, full: Path, backup_dir: Path) -> bool:
    if not full.exists():
        print(f"AVISO - {rel_path} nao existe.")
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