"""apply_update_v5v6: prosperidade detalhada, logs descritivos, simbolos no mapa."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v6_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. models.py - GameState.morning_gains
# =============================================================
EDITS.append((
    "jessica/core/models.py",
    "    timeline: list[dict] = field(default_factory=list)\n",
    "    timeline: list[dict] = field(default_factory=list)\n"
    "    morning_gains: list[dict] = field(default_factory=list)\n"
))

# =============================================================
# 2. serialize.py - persistir morning_gains
# =============================================================
EDITS.append((
    "jessica/core/serialize.py",
    '            "timeline": [dict(e) for e in s.timeline]}',
    '            "timeline": [dict(e) for e in s.timeline],\n'
    '            "morning_gains": [dict(e) for e in s.morning_gains]}'
))
EDITS.append((
    "jessica/core/serialize.py",
    '    state.timeline = [dict(e) for e in d.get("timeline", [])]\n'
    '    return state',
    '    state.timeline = [dict(e) for e in d.get("timeline", [])]\n'
    '    state.morning_gains = [dict(e) for e in d.get("morning_gains", [])]\n'
    '    return state'
))

# =============================================================
# 3. actions.py - apply_gold_interest popula morning_gains
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '''\
def apply_gold_interest(state: GameState) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    for player in state.players:
        city = player.city
        if not city.is_alive():
            continue
        interest = city.gold // GOLD_INTEREST_DIVISOR
        if interest > 0:
            city.gold += interest
            log(state, f"{player.name} rendeu {interest} de Ouro.")
            results.append((player.id, interest))
    return results''',
    '''\
def apply_gold_interest(state: GameState) -> list[tuple[int, int]]:
    results: list[tuple[int, int]] = []
    for player in state.players:
        city = player.city
        if not city.is_alive():
            continue
        interest = city.gold // GOLD_INTEREST_DIVISOR
        if interest > 0:
            city.gold += interest
            log(state, f"{player.name} rendeu {interest} de Ouro.")
            results.append((player.id, interest))
            state.morning_gains.append(
                {"pid": player.id, "kind": "juros", "gold": interest}
            )
    return results'''
))

# =============================================================
# 4. artifacts_effects.py - on_turn_start popula morning_gains
# =============================================================
EDITS.append((
    "jessica/core/artifacts_effects.py",
    '''\
def on_turn_start(state: GameState) -> None:
    for player in state.players:
        if not player.city.is_alive():
            continue
        for artifact in player.field_artifacts:
            if artifact.card_id == "K_H":
                if player.city.life < player.city.life_max:
                    player.city.life += 1
                    log(state, f"{player.name}: Kh Aquilombar (+1 Vida).")
            elif artifact.card_id == "K_D":
                player.city.gold += 2
                player.city.magic += 1
                log(state, f"{player.name}: Kd Balanca (+2 Ouro, +1 Magia).")''',
    '''\
def on_turn_start(state: GameState) -> None:
    for player in state.players:
        if not player.city.is_alive():
            continue
        for artifact in player.field_artifacts:
            if artifact.card_id == "K_H":
                if player.city.life < player.city.life_max:
                    player.city.life += 1
                    log(state, f"{player.name}: Kh Aquilombar (+1 Vida).")
                    state.morning_gains.append(
                        {"pid": player.id, "kind": "Kh", "life": 1}
                    )
            elif artifact.card_id == "K_D":
                player.city.gold += 2
                player.city.magic += 1
                log(state, f"{player.name}: Kd Balanca (+2 Ouro, +1 Magia).")
                state.morning_gains.append(
                    {"pid": player.id, "kind": "Kd", "gold": 2, "magic": 1}
                )'''
))

# =============================================================
# 5. turn.py - start_turn limpa morning_gains
# =============================================================
EDITS.append((
    "jessica/core/turn.py",
    '''\
    log(state, f"--- Inicio do Turno {state.turn} (Dia) ---")
    state.phase = Phase.DAY
    interest = apply_gold_interest(state)''',
    '''\
    log(state, f"--- Inicio do Turno {state.turn} (Dia) ---")
    state.phase = Phase.DAY
    state.morning_gains = []
    interest = apply_gold_interest(state)'''
))

# =============================================================
# 6. combat.py - record_action com contexto rico
# =============================================================
EDITS.append((
    "jessica/core/combat.py",
    '''\
    bump_stat(state, attacker.owner_id, "damage_dealt", dmg_to_target)
    bump_stat(state, target.owner_id, "damage_taken", dmg_to_target)
    bump_stat(state, target.owner_id, "damage_dealt", dmg_to_attacker)
    bump_stat(state, attacker.owner_id, "damage_taken", dmg_to_attacker)
    record_action(state, attacker.owner_id, "attack",
                  target_id=target.id, damage=dmg_to_target,
                  retaliation=dmg_to_attacker)''',
    '''\
    bump_stat(state, attacker.owner_id, "damage_dealt", dmg_to_target)
    bump_stat(state, target.owner_id, "damage_taken", dmg_to_target)
    bump_stat(state, target.owner_id, "damage_dealt", dmg_to_attacker)
    bump_stat(state, attacker.owner_id, "damage_taken", dmg_to_attacker)
    record_action(state, attacker.owner_id, "attack",
                  attacker_id=attacker.id,
                  attacker_kind="hero" if isinstance(attacker, Hero) else "troop",
                  attacker_hero_id=attacker.hero_id if isinstance(attacker, Hero) else None,
                  attacker_archetype=attacker.archetype.value if isinstance(attacker, Troop) else None,
                  target_id=target.id,
                  target_owner_id=target.owner_id,
                  target_kind="hero" if isinstance(target, Hero) else "troop",
                  target_hero_id=target.hero_id if isinstance(target, Hero) else None,
                  target_archetype=target.archetype.value if isinstance(target, Troop) else None,
                  damage=dmg_to_target,
                  retaliation=dmg_to_attacker)'''
))

EDITS.append((
    "jessica/core/combat.py",
    '''\
        bump_stat(state, attacker.owner_id, "damage_dealt", dmg_to_city)
        bump_stat(state, target_pid, "damage_taken", dmg_to_city)
        record_action(state, attacker.owner_id, "attack_city",
                      target_player_id=target_pid, damage=dmg_to_city)''',
    '''\
        bump_stat(state, attacker.owner_id, "damage_dealt", dmg_to_city)
        bump_stat(state, target_pid, "damage_taken", dmg_to_city)
        record_action(state, attacker.owner_id, "attack_city",
                      attacker_id=attacker.id,
                      attacker_kind="hero" if isinstance(attacker, Hero) else "troop",
                      attacker_hero_id=attacker.hero_id if isinstance(attacker, Hero) else None,
                      attacker_archetype=attacker.archetype.value if isinstance(attacker, Troop) else None,
                      target_player_id=target_pid,
                      damage=dmg_to_city)'''
))

EDITS.append((
    "jessica/core/combat.py",
    '''\
    for player in state.players:
        dead = [u for u in player.units if not u.is_alive()]
        for u in dead:
            bump_stat(state, player.id, "deaths")
            record_action(state, player.id, "unit_died",
                          unit_id=u.id, house=u.house,
                          killed_by=u.killed_by_player_id)
            log(state, f"  {u.id} ({player.name}) morreu.")
        player.units = [u for u in player.units if u.is_alive()]''',
    '''\
    for player in state.players:
        dead = [u for u in player.units if not u.is_alive()]
        for u in dead:
            bump_stat(state, player.id, "deaths")
            record_action(state, player.id, "unit_died",
                          unit_id=u.id, house=u.house,
                          kind="hero" if isinstance(u, Hero) else "troop",
                          hero_id=u.hero_id if isinstance(u, Hero) else None,
                          archetype=u.archetype.value if isinstance(u, Troop) else None,
                          killed_by=u.killed_by_player_id)
            log(state, f"  {u.id} ({player.name}) morreu.")
        player.units = [u for u in player.units if u.is_alive()]'''
))

# =============================================================
# 7. main.py - SYMBOL_DESC + _unit_symbols + _describe_* helpers
# =============================================================
SYMBOLS_BLOCK = '''\
SYMBOL_DESC = {
    "2x": "Dobro de dano (Kc, Qs, Vovo, etc.)",
    "R": "Resistencia (R1 = 1 stack, R2 = 2 stacks - divide dano por 2 cada)",
    "~": "Invisivel (nao pode ser atacado ate o fim do turno)",
    "z": "Dormindo (nao pode atacar; acorda se for atacado)",
    "\\u2620": "Amaldicoado (recebe o dobro de dano de TODAS as fontes)",
    "\\u00d7": "Ks ativo (dobra o numero de ataques)",
    "B": "Morcego (vampiro com 2 movimentos neste turno)",
    "W": "Lobisomem (em Lua Cheia: dobro de dano)",
    "E": "Esploiado (nao pode atacar neste turno)",
    "C": "Centauro (2 movimentos ate o fim da Noite)",
    "\\u2605": "Invulneravel (nao recebe dano neste turno)",
}


def _unit_symbols(state, u) -> str:
    syms = []
    if u.double_damage:
        syms.append("2x")
    if u.resistance_stacks:
        syms.append(f"R{u.resistance_stacks}")
    if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
        syms.append("~")
    if u.statuses.get("sono_until_turn", -1) > state.turn:
        syms.append("z")
    if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
        syms.append("\\u2620")
    if u.statuses.get("k_s_active"):
        syms.append("\\u00d7")
    if u.statuses.get("morcego_until_turn", -1) >= state.turn:
        syms.append("B")
    if u.statuses.get("lobisomem_until_turn", -1) >= state.turn:
        syms.append("W")
    if u.statuses.get("cannot_attack_on_turn") == state.turn:
        syms.append("E")
    if u.statuses.get("centauro_until_turn", -1) == state.turn:
        syms.append("C")
    if u.statuses.get("invulneravel_until_turn", -1) >= state.turn:
        syms.append("\\u2605")
    return "".join(syms)


def _describe_card(card_id) -> str:
    if not card_id:
        return "?"
    try:
        return card_display(card_id)
    except Exception:
        return str(card_id)


def _describe_hero(hero_id) -> str:
    if not hero_id:
        return "?"
    try:
        return heroes.hero_name(hero_id)
    except Exception:
        return str(hero_id)


def _describe_player(state, pid) -> str:
    if pid is None:
        return "?"
    try:
        return get_player(state, pid).name
    except Exception:
        return f"J{pid}"


def _describe_unit_kind(params, prefix="target") -> str:
    kind = params.get(f"{prefix}_kind")
    if kind == "hero":
        return f"Heroi {_describe_hero(params.get(f'{prefix}_hero_id'))}"
    if kind == "troop":
        arch = params.get(f"{prefix}_archetype", "?")
        return f"Tropa {arch}"
    return params.get(f"{prefix}_id", "?")


'''

EDITS.append((
    "jessica/main.py",
    "SYMBOL_DESC = {",  # shouldn't exist yet, but guard
    "SYMBOL_DESC = {"
))

# Actually insert block after RestartGame class
EDITS.append((
    "jessica/main.py",
    "class RestartGame(Exception):\n    pass\n",
    "class RestartGame(Exception):\n    pass\n\n\n" + SYMBOLS_BLOCK
))

# =============================================================
# 8. main.py - _city_cell_lines com simbolos
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    for p in state.players:
        for u in p.units:
            if u.house == house and u.is_alive():
                kind = "H" if isinstance(u, Hero) else "T"
                label = f"{kind}{u.life}"
                if p.id != pid:
                    label = f"J{p.id} {label}"
                units.append(label)''',
    '''\
    for p in state.players:
        for u in p.units:
            if u.house == house and u.is_alive():
                kind = "H" if isinstance(u, Hero) else "T"
                syms = _unit_symbols(state, u)
                label = f"{kind}{u.life}{syms}"
                if p.id != pid:
                    label = f"J{p.id} {label}"
                units.append(label)'''
))

# =============================================================
# 9. main.py - _center_cell_lines com simbolos
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    for p in state.players:
        for u in p.units:
            if u.house == CENTER and u.is_alive():
                kind = "H" if isinstance(u, Hero) else "T"
                units.append(f"J{p.id}-{kind}{u.life}")''',
    '''\
    for p in state.players:
        for u in p.units:
            if u.house == CENTER and u.is_alive():
                kind = "H" if isinstance(u, Hero) else "T"
                syms = _unit_symbols(state, u)
                units.append(f"J{p.id}-{kind}{u.life}{syms}")'''
))

# =============================================================
# 10. main.py - _mostrar_resumo_local usa simbolos
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
            tipo = (f"Heroi {heroes.hero_name(u.hero_id)}"
                    if isinstance(u, Hero) else f"Tropa {u.archetype.value}")
            flags = []
            if u.double_damage:
                flags.append("2xdano")
            if u.resistance_stacks:
                flags.append(f"resx{u.resistance_stacks}")
            if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
                flags.append("invisivel")
            if u.statuses.get("sono_until_turn", -1) > state.turn:
                flags.append("dormindo")
            if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
                flags.append("amaldicoado")
            if u.statuses.get("k_s_active"):
                flags.append("Ks")
            flags_str = f" [{", ".join(flags)}]" if flags else ""
            console.print(f"  {p.name}: {u.id} ({tipo}) {u.life}/{u.life_max}{flags_str}")''',
    '''\
            tipo = (f"Heroi {heroes.hero_name(u.hero_id)}"
                    if isinstance(u, Hero) else f"Tropa {u.archetype.value}")
            syms = _unit_symbols(state, u)
            syms_str = f" {syms}" if syms else ""
            console.print(f"  {p.name}: {u.id} ({tipo}) {u.life}/{u.life_max}{syms_str}")'''
))

# =============================================================
# 11. main.py - Prosperidade detalhada (run_one_game)
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
        if interest:
            pros = ", ".join(f"{get_player(state, pid).name} (+{g})" for pid, g in interest)
            console.print(f"[yellow]Prosperidade:[/yellow] {pros}\\n")''',
    '''\
        if interest or state.morning_gains:
            by_pid: dict[int, list[dict]] = {}
            for g in state.morning_gains:
                by_pid.setdefault(g["pid"], []).append(g)
            console.print("[yellow]Prosperidade:[/yellow]")
            for p in state.players:
                if p.id not in by_pid:
                    continue
                parts = []
                for g in by_pid[p.id]:
                    kind = g.get("kind", "?")
                    bits = []
                    if g.get("gold"):
                        bits.append(f"+{g['gold']} Ouro")
                    if g.get("magic"):
                        bits.append(f"+{g['magic']} Magia")
                    if g.get("life"):
                        bits.append(f"+{g['life']} Vida")
                    if bits:
                        parts.append(f"{' '.join(bits)} ({kind})")
                if parts:
                    console.print(f"  {p.name}: {'; '.join(parts)}")
            console.print()'''
))

# =============================================================
# 12. main.py - show_turn_log descritivo
# =============================================================
OLD_LOG = '''\
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
    console.print()'''

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
    console.print()'''

EDITS.append((
    "jessica/main.py",
    OLD_LOG,
    NEW_LOG
))

# =============================================================
# 13. main.py - Ajuda: secao "Simbolos no mapa"
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def _menu_ajuda(state, pid: int) -> None:
    opts = [
        "Tutorial rapido",
        "Meu povo (passiva, feitico, herois)",
        "Outros povos em jogo",
        "Referencia de artefatos",
        "Referencia de statuses",
        "Atalhos de teclado",
        "Voltar",
    ]
    idx = pick_index("Ajuda", opts)
    if idx == 0:
        _ajuda_tutorial()
    elif idx == 1:
        show_habilidades(state, pid)
    elif idx == 2:
        _ajuda_outros_povos(state, pid)
    elif idx == 3:
        _ajuda_artefatos()
    elif idx == 4:
        _ajuda_statuses()
    elif idx == 5:
        _ajuda_atalhos()''',
    '''\
def _ajuda_simbolos() -> None:
    table = Table(title="Simbolos no mapa", box=box.ROUNDED)
    table.add_column("Simbolo")
    table.add_column("Efeito")
    for k, v in SYMBOL_DESC.items():
        table.add_row(k, v)
    console.print(table)


def _menu_ajuda(state, pid: int) -> None:
    opts = [
        "Tutorial rapido",
        "Meu povo (passiva, feitico, herois)",
        "Outros povos em jogo",
        "Referencia de artefatos",
        "Referencia de statuses",
        "Referencia de simbolos (mapa)",
        "Atalhos de teclado",
        "Voltar",
    ]
    idx = pick_index("Ajuda", opts)
    if idx == 0:
        _ajuda_tutorial()
    elif idx == 1:
        show_habilidades(state, pid)
    elif idx == 2:
        _ajuda_outros_povos(state, pid)
    elif idx == 3:
        _ajuda_artefatos()
    elif idx == 4:
        _ajuda_statuses()
    elif idx == 5:
        _ajuda_simbolos()
    elif idx == 6:
        _ajuda_atalhos()'''
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