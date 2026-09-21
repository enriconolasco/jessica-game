"""apply_update_v5v13: fix Luna Sonho + ficha contextual + empalados no Board
   + cancelar por ultimo em prompts de alvo + night_start_positions check."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v13_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


# =============================================================
# 1. Fix Luna Sonho (bloco inteiro via regex)
# =============================================================
NEW_SONHO_BLOCK = '''\
        elif sp.spell_id == "sonho_lucido":
            if peoples.valendar_is_alive(player):
                pass  # Devaneio Onirico: sem escolha
            elif peoples.luna_is_alive(player):
                cards = []
                hand_disponivel = list(player.hand)
                while hand_disponivel:
                    labels = [card_display(c) for c in hand_disponivel] + ["(parar)"]
                    idx = pick_index("Inverter qual?", labels)
                    if idx == len(hand_disponivel):
                        break
                    c = hand_disponivel.pop(idx)
                    cards.append(c)
                if not cards:
                    console.print("[yellow]Sonho Lucido cancelado.[/yellow]")
                    return None
                choice_data["flip_cards"] = cards
            else:
                if not player.hand:
                    raise ActionError("Mao vazia.")
                labels = [card_display(c) for c in player.hand] + ["Cancelar"]
                idx = pick_index("Inverter qual?", labels)
                if idx == len(player.hand):
                    console.print("[yellow]Sonho Lucido cancelado.[/yellow]")
                    return None
                choice_data["flip_cards"] = [player.hand[idx]]'''


def _patch_luna_sonho() -> bool:
    full = ROOT / "jessica" / "main.py"
    if not full.exists():
        print("AVISO - main.py nao existe.")
        return False
    txt = full.read_text(encoding="utf-8")
    if 'choice_data["flip_cards"] = cards' in txt and '(parar)"' in txt and 'labels = [card_display(c) for c in hand_disponivel] + ["(parar)"]' in txt:
        print("OK  - Luna Sonho ja esta no formato novo")
        return True
    pattern = re.compile(
        r'        elif sp\.spell_id == "sonho_lucido":.*?choice_data\["flip_cards"\] = \[player\.hand\[idx - 1\]\]',
        re.DOTALL,
    )
    if not pattern.search(txt):
        # Tenta capturar ate "cast_spell(state, pid, choice_data)"
        pattern = re.compile(
            r'        elif sp\.spell_id == "sonho_lucido":.*?(?=\n        cast_spell\(state, pid, choice_data\))',
            re.DOTALL,
        )
        if not pattern.search(txt):
            print("AVISO - bloco sonho_lucido nao encontrado no main.py.")
            return False
    new_txt = pattern.sub(NEW_SONHO_BLOCK, txt, count=1)
    if new_txt == txt:
        print("AVISO - substituicao do sonho lucido nao mudou nada.")
        return False
    backup = BACKUP_DIR / "jessica" / "main.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(new_txt, encoding="utf-8")
    print("OK  - Sonho Lucido reescrito (Cancelar/(parar) no fim)")
    return True


# =============================================================
# 2. Cancelar por ultimo em prompts de alvo de feitico
# =============================================================
def _patch_prompts_alvo() -> bool:
    full = ROOT / "jessica" / "main.py"
    if not full.exists():
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt
    changes = 0

    # 2a. resistencia / transformar_morcego / licantropo (mesma linha em 3 branches)
    old_a = 'choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id'
    if old_a in txt:
        new_a = '''\
        _units_labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units] + ["Cancelar"]
        _idx_u = pick_index("Alvo", _units_labels)
        if _idx_u == len(player.units):
            console.print("[yellow]Cancelado.[/yellow]")
            return None
        choice_data["unit_id"] = player.units[_idx_u].id'''
        # Nao posso simplesmente substituir porque perde indentacao dos 3 lugares
        # Vou trocar por um helper global primeiro
        pass

    # Melhor: criar helper _pick_unit_or_cancel e substituir as 3 chamadas
    helper = '''\
def _pick_unit_or_cancel(player, prompt="Alvo"):
    """Retorna unit_id ou None se cancelar. Cancelar no fim da lista."""
    if not player.units:
        raise ActionError("Sem unidades.")
    labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units] + ["Cancelar"]
    idx = pick_index(prompt, labels)
    if idx == len(player.units):
        return None
    return player.units[idx].id


'''
    if "_pick_unit_or_cancel" not in txt:
        txt = txt.replace(
            "def _get_actions(state, player) -> list[tuple[str, str, str]]:",
            helper + "def _get_actions(state, player) -> list[tuple[str, str, str]]:",
            1,
        )
        changes += 1
        print("  OK  - helper _pick_unit_or_cancel adicionado")

    # Substituir 3 chamadas: cada uma tem "labels" definidas antes
    # Padrao: labels = [...]; choice_data["unit_id"] = player.units[pick_index(...)].id
    patterns = [
        # resistencia
        (re.compile(
            r'        if sp\.spell_id == "resistencia":\n'
            r'            if not player\.units:\n'
            r'                raise ActionError\("Sem unidades\."\)\n'
            r'            labels = \[f"\{u\.id\} \(\{u\.life\}/\{u\.life_max\}\)" for u in player\.units\]\n'
            r'            choice_data\["unit_id"\] = player\.units\[pick_index\("Alvo", labels\)\]\.id',
            re.DOTALL),
         '''\
        if sp.spell_id == "resistencia":
            _uid = _pick_unit_or_cancel(player, "Alvo")
            if _uid is None:
                console.print("[yellow]Cancelado.[/yellow]")
                return None
            choice_data["unit_id"] = _uid'''),
        # transformar_morcego
        (re.compile(
            r'        elif sp\.spell_id == "transformar_morcego":\n'
            r'            if not player\.units:\n'
            r'                raise ActionError\("Sem unidades\."\)\n'
            r'            labels = \[f"\{u\.id\} \(\{u\.life\}/\{u\.life_max\}\)" for u in player\.units\]\n'
            r'            choice_data\["unit_id"\] = player\.units\[pick_index\("Alvo", labels\)\]\.id',
            re.DOTALL),
         '''\
        elif sp.spell_id == "transformar_morcego":
            _uid = _pick_unit_or_cancel(player, "Alvo")
            if _uid is None:
                console.print("[yellow]Cancelado.[/yellow]")
                return None
            choice_data["unit_id"] = _uid'''),
        # licantropo
        (re.compile(
            r'        elif sp\.spell_id == "licantropo":\n'
            r'            if not player\.units:\n'
            r'                raise ActionError\("Sem unidades\."\)\n'
            r'            labels = \[f"\{u\.id\} \(\{u\.life\}/\{u\.life_max\}\)" for u in player\.units\]\n'
            r'            choice_data\["unit_id"\] = player\.units\[pick_index\("Alvo", labels\)\]\.id',
            re.DOTALL),
         '''\
        elif sp.spell_id == "licantropo":
            _uid = _pick_unit_or_cancel(player, "Alvo")
            if _uid is None:
                console.print("[yellow]Cancelado.[/yellow]")
                return None
            choice_data["unit_id"] = _uid'''),
    ]
    for pat, repl in patterns:
        if pat.search(txt):
            txt = pat.sub(repl, txt, count=1)
            changes += 1
            print("  OK  - prompt de feitico adaptado")
        else:
            print("  AVISO - um prompt de feitico nao casou (regex).")

    if txt == original:
        print("AVISO - nenhuma mudanca em prompts de feitico.")
        return False
    backup = BACKUP_DIR / "jessica" / "main.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print(f"OK  - main.py: {changes} mudanca(s) em prompts")
    return True


# =============================================================
# 3. Ficha contextual de unidade (drill-down)
# =============================================================
FICHA_FUNC = '''\
def _ficha_unidade(state, uid: str) -> None:
    """Mostra ficha completa de uma unidade."""
    u = None
    dono = None
    for p in state.players:
        for x in p.units:
            if x.id == uid:
                u, dono = x, p
                break
        if u:
            break
    if u is None:
        console.print(f"[red]Unidade {uid} nao encontrada.[/red]")
        return
    c = _pcolor(dono.people)
    tipo = (f"Heroi {heroes.hero_name(u.hero_id)}" if isinstance(u, Hero)
            else f"Tropa {_troop_display(u.archetype)}")
    console.print(Panel.fit(
        f"[bold {c}]{u.id}[/bold {c}] - {tipo}",
        border_style=c))
    console.print(f"Dono: {_pname(state, dono.id)} ({dono.people})")
    console.print(f"Local: {house_short(state, u.house)}")
    console.print(f"Vida: {u.life}/{u.life_max}")
    console.print(f"Movimentos: {u.moves_this_turn}/{u.max_moves_this_turn}")
    console.print(f"Ataques (noite): {u.attacks_made_this_night}/"
                  f"{_effective_max_attacks(state, u)}")
    if isinstance(u, Hero):
        hd = heroes.get_hero(u.hero_id)
        console.print(f"Habilidades: {', '.join(hd.abilities) if hd.abilities else '-'}")
    syms = _unit_symbols(state, u)
    console.print(f"Status: {syms if syms else '(nenhum)'}")
    console.print("[bold]Detalhamento:[/bold]")
    if u.double_damage:
        console.print("  - Dobro de dano ativo")
    if u.resistance_stacks:
        console.print(f"  - {u.resistance_stacks} stacks de Resistencia (divide dano por "
                      f"{2 ** u.resistance_stacks})")
    if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
        console.print(f"  - Invisivel ate o fim do turno {state.turn}")
    if u.statuses.get("sono_until_turn", -1) > state.turn:
        console.print(f"  - Dormindo ate turno {u.statuses['sono_until_turn']}")
    if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
        console.print(f"  - Amaldicoado (dano dobrado)")
    if u.statuses.get("k_s_active"):
        console.print("  - Ks ativo (dobra ataques)")
    if u.statuses.get("morcego_until_turn", -1) >= state.turn:
        console.print("  - Morcego (+1 movimento)")
    if u.statuses.get("lobisomem_until_turn", -1) >= state.turn:
        console.print("  - Lobisomem (dobro de dano)")
    if u.statuses.get("cannot_attack_on_turn") == state.turn:
        console.print("  - Espoliado (nao ataca neste turno)")
    if u.statuses.get("centauro_until_turn", -1) == state.turn:
        console.print("  - Centauro (2 movimentos)")
    if u.statuses.get("invulneravel_until_turn", -1) >= state.turn:
        console.print("  - Invulneravel")
    if u.original_owner_id is not None:
        console.print(f"  - Controlado temporariamente (dono real: "
                      f"{_pname(state, u.original_owner_id)})")
    console.print()


def _inspecionar_unidade(state, pid: int) -> None:
    """Lista todas as unidades vivas do jogo; usuario escolhe uma pra ver ficha."""
    todas = []
    labels = []
    for p in state.players:
        if not p.city.is_alive():
            continue
        for u in p.units:
            if not u.is_alive():
                continue
            todas.append(u.id)
            tipo = (f"Heroi {_hero_short(u.hero_id)}" if isinstance(u, Hero)
                    else f"Tropa {_troop_display(u.archetype)}")
            labels.append(f"{u.id} ({tipo}) - {_pname(state, p.id)} "
                          f"em {house_short(state, u.house)}")
    if not todas:
        console.print("[dim]Sem unidades.[/dim]")
        return
    labels.append("Voltar")
    idx = pick_index("Inspecionar unidade", labels)
    if idx == len(todas):
        return
    _ficha_unidade(state, todas[idx])


'''

# =============================================================
# 4. Empalados / Infectados no Board
# =============================================================
def _patch_board_empalados() -> bool:
    full = ROOT / "jessica" / "main.py"
    if not full.exists():
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt

    # Adicionar bloco no fim de show_board (antes do proximo "def ")
    anchor = "def show_turn_log(state) -> None:"
    if anchor not in txt:
        print("AVISO - show_turn_log nao achado pra ancorar Board.")
        return False
    bloco = '''\
def _board_empalados_infectados(state) -> None:
    empal = []
    for p in state.players:
        for sig in p.empalados:
            empal.append(f"  {_pname(state, p.id)}: {sig['kind']} {sig['id']}")
    infect = []
    for p in state.players:
        for sig in p.infectados:
            infect.append(f"  {_pname(state, p.id)}: {sig['kind']} {sig['id']}")
    if empal or infect:
        console.print()
        if empal:
            console.print("[bold]Empalados (nao reinvocaveis)[/bold]")
            for ln in empal:
                console.print(ln)
        if infect:
            console.print("[bold]Infectados (viram Lobisomem em Lua Cheia)[/bold]")
            for ln in infect:
                console.print(ln)


'''
    if "_board_empalados_infectados" not in txt:
        txt = txt.replace(anchor, bloco + anchor, 1)
        print("  OK  - _board_empalados_infectados adicionado")

    # Chamar no fim de show_board: procurar o final de show_board
    # Ultima linha do show_board costuma ser "console.print()" ou "show_board(state)"
    # Vou procurar por "def show_board" e achar o proximo "def " e inserir chamada
    pattern = re.compile(
        r"(def show_board\(state\) -> None:.*?)(\n(?:def |class )|\Z)",
        re.DOTALL,
    )
    m = pattern.search(txt)
    if not m:
        print("AVISO - show_board nao encontrado.")
        return False
    body = m.group(1)
    if "_board_empalados_infectados(state)" in body:
        print("OK  - Board ja chama _board_empalados_infectados")
    else:
        new_body = body.rstrip() + "\n    _board_empalados_infectados(state)\n"
        txt = txt[:m.start(1)] + new_body + txt[m.end(1):]
        print("  OK  - Board agora lista empalados/infectados")

    if txt == original:
        print("AVISO - Board nao mudou.")
        return False
    backup = BACKUP_DIR / "jessica" / "main.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - Board atualizado")
    return True


# =============================================================
# 5. Adicionar opcoes no menu Informacoes
# =============================================================
def _patch_menu_info() -> bool:
    full = ROOT / "jessica" / "main.py"
    if not full.exists():
        return False
    txt = full.read_text(encoding="utf-8")
    original = txt
    old = '''\
def _menu_informacoes(state, pid: int) -> None:
    opts = [
        "Loja",
        "Inspecionar local / unidade",
        "Artefatos em campo (todos)",
        "Passivas ativas",
        "Unidades empaladas / infectadas",
        "Eventos futuros",
        "Ver povo (todos os 10)",
        "Habilidades do meu povo",
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
        show_eventos_futuros(state)
    elif idx == 6:
        _menu_povos(state, pid)
    elif idx == 7:
        show_habilidades(state, pid)'''
    new = '''\
def _menu_informacoes(state, pid: int) -> None:
    opts = [
        "Loja",
        "Inspecionar local",
        "Inspecionar unidade (ficha completa)",
        "Artefatos em campo (todos)",
        "Passivas ativas",
        "Unidades empaladas / infectadas",
        "Eventos futuros",
        "Ver povo (todos os 10)",
        "Habilidades do meu povo",
        "Voltar",
    ]
    idx = pick_index("Informacoes", opts)
    if idx == 0:
        show_loja(state)
    elif idx == 1:
        estudar_campo(state)
    elif idx == 2:
        _inspecionar_unidade(state, pid)
    elif idx == 3:
        show_active_artifacts(state)
    elif idx == 4:
        show_passivas_ativas(state)
    elif idx == 5:
        show_empalados_infectados(state)
    elif idx == 6:
        show_eventos_futuros(state)
    elif idx == 7:
        _menu_povos(state, pid)
    elif idx == 8:
        show_habilidades(state, pid)'''
    if old in txt:
        txt = txt.replace(old, new, 1)
    elif "Inspecionar unidade (ficha completa)" in txt:
        print("OK  - _menu_informacoes ja tem ficha de unidade")
        return True
    else:
        print("AVISO - _menu_informacoes nao casou (texto divergiu).")
        return False

    # Inserir _ficha_unidade/_inspecionar_unidade antes de _menu_informacoes
    if "_ficha_unidade" not in txt:
        txt = txt.replace(
            "def _menu_informacoes(state, pid: int) -> None:",
            FICHA_FUNC + "def _menu_informacoes(state, pid: int) -> None:",
            1,
        )
        print("  OK  - _ficha_unidade / _inspecionar_unidade adicionadas")

    backup = BACKUP_DIR / "jessica" / "main.py"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup)
    full.write_text(txt, encoding="utf-8")
    print("OK  - _menu_informacoes atualizado")
    return True


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    _patch_luna_sonho()
    _patch_prompts_alvo()
    _patch_board_empalados()
    _patch_menu_info()

    print(f"\nBackup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()