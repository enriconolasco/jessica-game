"""apply_update_v5v10_11: Luide Vampa + Q_D imediato + Sonho Lucido imediato
   + Luna escolha livre + Valendar -> Devaneio Onirico."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v10_11_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. models.py - Player.devaneio_ativo_turn
# =============================================================
EDITS.append((
    "jessica/core/models.py",
    "    miyamoto_life_max_bonus: int = 0\n",
    "    miyamoto_life_max_bonus: int = 0\n"
    "    devaneio_ativo_turn: int = -1\n"
))

# =============================================================
# 2. serialize.py - persistir
# =============================================================
EDITS.append((
    "jessica/core/serialize.py",
    '        "miyamoto_life_max_bonus": p.miyamoto_life_max_bonus,\n',
    '        "miyamoto_life_max_bonus": p.miyamoto_life_max_bonus,\n'
    '        "devaneio_ativo_turn": p.devaneio_ativo_turn,\n'
))
EDITS.append((
    "jessica/core/serialize.py",
    '        miyamoto_life_max_bonus=d.get("miyamoto_life_max_bonus", 0),\n',
    '        miyamoto_life_max_bonus=d.get("miyamoto_life_max_bonus", 0),\n'
    '        devaneio_ativo_turn=d.get("devaneio_ativo_turn", -1),\n'
))

# =============================================================
# 3. actions.py - _apply_valendar_bonus checa devaneio
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '''\
def _apply_valendar_bonus(state, player, card_id):
    if not peoples.valendar_is_alive(player):
        return''',
    '''\
def _apply_valendar_bonus(state, player, card_id):
    if not peoples.valendar_is_alive(player):
        return
    if player.devaneio_ativo_turn != state.turn:
        return'''
))

# =============================================================
# 4. actions.py - remove "Valendar substitui Sonho Lucido" do cast
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '''\
    if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
        raise ActionError("Valendar substitui Sonho Lucido.")

''',
    '''\
'''
))

# =============================================================
# 5. actions.py - cast_spell: Sonho Lucido imediato + Devaneio
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '''\
    elif sp.spell_id == "sonho_lucido":
        player.sonho_lucido_pending_turn = state.turn
        if peoples.luna_is_alive(player):
            player.sonho_lucido_multi_turn = state.turn
        log(state, f"{player.name}: Sonho Lucido ativo.")''',
    '''\
    elif sp.spell_id == "sonho_lucido":
        if peoples.valendar_is_alive(player):
            player.devaneio_ativo_turn = state.turn
            log(state, f"{player.name}: Devaneio Onirico ativo (bonus de naipe no proximo artefato).")
        else:
            cards = choice.get("flip_cards", [])
            if not cards:
                raise ActionError("Sonho Lucido: escolha ao menos 1 artefato.")
            if not peoples.luna_is_alive(player) and len(cards) > 1:
                raise ActionError("Sem Luna, so 1 artefato por Sonho Lucido.")
            for cid in cards:
                if cid not in player.hand:
                    raise ActionError(f"Nao tem {cid} na mao.")
            for cid in list(cards):
                new_card = peoples.sonho_lucido_flip(cid)
                if new_card == cid:
                    log(state, f"Sonho Lucido: {card_display(cid)} nao mudou de naipe.")
                    continue
                player.hand.remove(cid)
                player.hand.append(new_card)
                log(state, f"Sonho Lucido: {card_display(cid)} -> {card_display(new_card)}.")
                try:
                    play_artifact(state, player.id, new_card)
                    log(state, f"  jogado: {card_display(new_card)}.")
                except ActionError as e:
                    player.hand.remove(new_card)
                    player.hand.append(cid)
                    log(state, f"  {card_display(new_card)} nao jogado: {e}")'''
))

# =============================================================
# 6. actions.py - play_artifact: remove auto-flip de sonho lucido
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '''\
    if player.sonho_lucido_pending_turn == state.turn:
        new_card = peoples.sonho_lucido_flip(card_id)
        if new_card != card_id:
            player.hand.remove(card_id)
            player.hand.append(new_card)
            log(state, f"Sonho Lucido: {card_display(card_id)} -> {card_display(new_card)}.")
            card_id = new_card
        player.sonho_lucido_used_turn = state.turn
        if player.sonho_lucido_multi_turn != state.turn:
            player.sonho_lucido_pending_turn = -1
    if not artifacts_effects.is_implemented(card_id):''',
    '''\
    if not artifacts_effects.is_implemented(card_id):'''
))

# =============================================================
# 7. main.py - _declarar_casa + _resolver_qd_pendente (helpers)
# =============================================================
NEW_HELPERS = '''\
def _resolver_qd_pendente(state) -> None:
    """Se algum jogador tem Q_D pendente, resolver agora."""
    for p in state.players:
        pend = p.pending_artifact_choice
        if pend and pend.get("kind") == "Q_D":
            try:
                _resolve_pending_choice_if_any(state, p.id)
            except Exception as e:
                console.print(f"[red]Erro Q_D: {e}[/red]")


def _declarar_casa(state, house: str, pids_declaram: list[int]) -> None:
    for pid in pids_declaram:
        player = get_player(state, pid)
        units_here = [u for u in player.units if u.house == house and u.is_alive()]
        if not units_here:
            continue
        if not any(find_targets(state, u) for u in units_here):
            continue
        _mostrar_resumo_local(state, house)
        console.print(f"[bold]{player.name} declara ataques em {house_short(state, house)}.[/bold]")
        for unit in list(units_here):
            if not unit.is_alive():
                continue
            while True:
                targets = find_targets(state, unit)
                if not targets:
                    break
                if _attacks_used(unit) >= _effective_max_attacks(state, unit):
                    break
                atk = prompt_attack(state, unit, targets)
                if not atk:
                    break
                before = len(state.event_log)
                try:
                    resolve_attack(state, atk)
                except CombatError as e:
                    console.print(f"  [red]Erro: {e}[/red]")
                    break
                for line in state.event_log[before:]:
                    console.print(f"  {line}")
                _resolver_qd_pendente(state)
        console.print()


def _luide_janela_noturna(state, all_pids, processed_houses=None) -> None:
    """Oferece mover/usar feitico para vampiros com Luide vivo.
       processed_houses: casas ja declaradas (para reabrir se vampiro voltar)."""
    if processed_houses is None:
        processed_houses = set()
    for pid in all_pids:
        player = get_player(state, pid)
        if player.people != "vampiros":
            continue
        luide = next((u for u in player.units
                      if isinstance(u, Hero) and u.is_alive()
                      and u.hero_id == "luide_vampa"), None)
        if luide is None:
            continue
        while True:
            disponiveis = [u for u in player.units
                           if u.is_alive() and u.moves_this_turn < u.max_moves_this_turn]
            opts = []
            if disponiveis:
                opts.append("Mover unidade")
            if not player.has_cast_spell_this_turn:
                opts.append("Lancar feitico")
            opts.append("(continuar)")
            if len(opts) == 1:
                break
            idx = pick_index(f"{player.name} (Luide Vampa)", opts)
            escolha = opts[idx]
            if escolha == "(continuar)":
                break
            if escolha == "Mover unidade":
                labels = [f"{u.id} ({house_short(state, u.house)}, {u.life})"
                          for u in disponiveis]
                u = disponiveis[pick_index("Unidade", labels)]
                dests = valid_destinations(state, u)
                if not dests:
                    console.print("[red]Sem destinos.[/red]")
                    continue
                labels2 = [house_short(state, d) for d in dests] + ["Cancelar"]
                idx2 = pick_index("Destino", labels2)
                if idx2 == len(dests):
                    continue
                destino = dests[idx2]
                try:
                    move_unit(state, pid, u.id, destino)
                    console.print("[green]Movido.[/green]")
                except ActionError as e:
                    console.print(f"[red]{e}[/red]")
                    continue
                # Se destino ja foi processado, vampiro declara agora
                if destino in processed_houses:
                    console.print(f"[cyan]{u.id} entrou em casa ja processada. Declara agora.[/cyan]")
                    _declarar_casa(state, destino, [pid])
            elif escolha == "Lancar feitico":
                try:
                    choice_data = {}
                    if not player.units:
                        raise ActionError("Sem unidades.")
                    labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
                    choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
                    cast_spell(state, pid, choice_data)
                    console.print("[green]Feitico lancado.[/green]")
                except (ActionError, ValueError) as e:
                    console.print(f"[red]{e}[/red]")


'''

EDITS.append((
    "jessica/main.py",
    "def _ainai_prompt_all(state, all_pids):",
    NEW_HELPERS + "def _ainai_prompt_all(state, all_pids):"
))

# =============================================================
# 8. main.py - substituir run_night_phase inteiro (regex)
# =============================================================
NEW_RUN_NIGHT = '''\
def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_hud(state)
    show_map(state)
    while True:
        opt = Prompt.ask(
            "Antes das declaracoes: [m]apa / [v] estudar campo / [Enter] continuar",
            default="")
        if opt == "m":
            show_map(state)
        elif opt == "v":
            estudar_campo(state)
        else:
            break
    _ask_vovo_position(state)

    all_pids = list(day_order(state))
    for pid in all_pids:
        player = get_player(state, pid)
        _try_luna_return(state, player)

    _ainai_prompt_all(state, all_pids)
    _luide_janela_noturna(state, all_pids, set())

    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
            _try_besouro_mandinga(state, player)

    day = day_order(state)
    city_order = list(reversed(day))
    house_order = [CENTER] + [f"city_{pid}" for pid in city_order]
    processed_houses = set()

    for house in house_order:
        pids_here = []
        for pid in all_pids:
            player = get_player(state, pid)
            if any(u.house == house and u.is_alive() for u in player.units):
                pids_here.append(pid)
        if not pids_here:
            processed_houses.add(house)
            continue
        pids_here = _order_players_for_house(state, pids_here, house)
        _declarar_casa(state, house, pids_here)
        processed_houses.add(house)
        # Luide entre casas
        _luide_janela_noturna(state, all_pids, processed_houses)
        _ainai_prompt_all(state, all_pids)

    # Janela final
    _luide_janela_noturna(state, all_pids, processed_houses)
    _ainai_prompt_all(state, all_pids)
'''


# =============================================================
# 9. main.py - cast de Sonho Lucido: UI
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
        elif sp.spell_id == "imitacao_gnomerica":
            choice_data = _escolher_imitacao(state, player)
        cast_spell(state, pid, choice_data)''',
    '''\
        elif sp.spell_id == "imitacao_gnomerica":
            choice_data = _escolher_imitacao(state, player)
        elif sp.spell_id == "sonho_lucido":
            if peoples.valendar_is_alive(player):
                pass  # Devaneio Onirico: sem escolha
            elif peoples.luna_is_alive(player):
                cards = []
                hand_disponivel = list(player.hand)
                while hand_disponivel:
                    labels = ["(parar)"] + [card_display(c) for c in hand_disponivel]
                    idx = pick_index("Inverter qual?", labels)
                    if idx == 0:
                        break
                    c = hand_disponivel.pop(idx - 1)
                    cards.append(c)
                if not cards:
                    console.print("[yellow]Sonho Lucido cancelado.[/yellow]")
                    return None
                choice_data["flip_cards"] = cards
            else:
                if not player.hand:
                    raise ActionError("Mao vazia.")
                labels = ["Cancelar"] + [card_display(c) for c in player.hand]
                idx = pick_index("Inverter qual?", labels)
                if idx == 0:
                    console.print("[yellow]Sonho Lucido cancelado.[/yellow]")
                    return None
                choice_data["flip_cards"] = [player.hand[idx - 1]]
        cast_spell(state, pid, choice_data)'''
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

    # Substituir run_night_phase inteiro via regex
    if rel_path == "jessica/main.py":
        pattern = re.compile(
            r"def run_night_phase\(state\) -> None:.*?(?=\n(?:def |class )|\Z)",
            re.DOTALL,
        )
        before = current
        current = pattern.sub(NEW_RUN_NIGHT.rstrip() + "\n", current, count=1)
        if current != before:
            applied += 1
            print("  OK  - run_night_phase substituido via regex")
        else:
            print("  AVISO - regex de run_night_phase nao casou.")

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