"""apply_update_v5v2: Ajuda (?), Relatorios (R), timeline de recursos."""
from pathlib import Path
from datetime import datetime
import os
import shutil

# --- Auto-detecta o ROOT do projeto ---
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
        Path(__file__).resolve().parent.parent.parent / "jessica",
    ]
    for c in candidates:
        if (c / "jessica" / "main.py").exists():
            return c
    return Path.home() / "Downloads" / "jessica"

ROOT = _find_project_root()
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. models.py - GameState.timeline
# =============================================================
EDITS.append((
    "jessica/core/models.py",
    "    fae_fallen_this_turn: list[tuple[int, str]] = field(default_factory=list)\n",
    "    fae_fallen_this_turn: list[tuple[int, str]] = field(default_factory=list)\n"
    "    timeline: list[dict] = field(default_factory=list)\n"
))

# =============================================================
# 2. serialize.py - persistir timeline
# =============================================================
EDITS.append((
    "jessica/core/serialize.py",
    '            "fae_fallen_this_turn": [list(t) for t in s.fae_fallen_this_turn]}',
    '            "fae_fallen_this_turn": [list(t) for t in s.fae_fallen_this_turn],\n'
    '            "timeline": [dict(e) for e in s.timeline]}'
))
EDITS.append((
    "jessica/core/serialize.py",
    '    state.fae_fallen_this_turn = [tuple(t) for t in d.get("fae_fallen_this_turn", [])]\n'
    '    return state',
    '    state.fae_fallen_this_turn = [tuple(t) for t in d.get("fae_fallen_this_turn", [])]\n'
    '    state.timeline = [dict(e) for e in d.get("timeline", [])]\n'
    '    return state'
))

# =============================================================
# 3. turn.py - snapshot de recursos no fim do turno
# =============================================================
EDITS.append((
    "jessica/core/turn.py",
    'def end_turn(state: GameState) -> None:\n'
    '    from .victory import check_victory\n'
    '    artifacts_effects.on_end_turn(state)\n'
    '    _remove_espectros(state)\n'
    '    check_victory(state)',
    'def _snapshot_timeline(state: GameState) -> None:\n'
    '    entry = {"turn": state.turn, "resources": {}}\n'
    '    for p in state.players:\n'
    '        entry["resources"][p.id] = {\n'
    '            "gold": p.city.gold,\n'
    '            "magic": p.city.magic,\n'
    '            "life": p.city.life,\n'
    '            "life_max": p.city.life_max,\n'
    '        }\n'
    '    state.timeline.append(entry)\n'
    '\n'
    '\n'
    'def end_turn(state: GameState) -> None:\n'
    '    from .victory import check_victory\n'
    '    artifacts_effects.on_end_turn(state)\n'
    '    _remove_espectros(state)\n'
    '    _snapshot_timeline(state)\n'
    '    check_victory(state)'
))

# =============================================================
# 4. main.py - dicts de referencia (status, tutorial)
# =============================================================
STATUS_DESC = '''\
STATUS_DESC = {
    "invisivel": "Nao pode ser atacado ate o fim do turno. Atacar remove a invisibilidade.",
    "sono": "Nao pode atacar. Acorda se for atacado.",
    "amaldicoado": "Recebe o DOBRO de dano de TODAS as fontes ate o fim do turno (Cova Rasa).",
    "morcego": "Vampiro: pode se mover 2x neste turno (ou 1x se recem-invocado).",
    "lobisomem": "Em Lua Cheia: dobro de dano, infeccao ao causar dano (Luarado) ou ao matar.",
    "Ks (Veu das Cacadoras)": "Aliados perto de Heroi do dono batem 2x. Herois podem atacar Cidades.",
    "Centauro (Guarari)": "Anda 2x. Volta ao normal no fim da Noite.",
    "Resistencia": "Cada stack divide o dano recebido por 2.",
    "Invulneravel": "Nao recebe dano ate o fim do turno (Qh).",
    "Armadura de Ouro": "Pode pagar Ouro para anular dano recebido (reativo, durante a Noite).",
    "Esploiado": "Nao pode atacar no turno (Arken Espoliou a casa).",
    "Empalado": "Unidade destruida por Dracula nao pode ser reinvocada pelo dono.",
    "Envenenado (Infeccao)": "Se o alvo morrer em Lua Cheia do Lobisomem, vira Lobisomem controlado.",
}


TUTORIAL_TXT = """\\
JESSICA - Tutorial rapido

OBJETIVO
  Ultima Cidade viva vence. 4 jogadores, cada um com 1 povo + 1 cidade.

TURNO
  Dia -> Noite -> proximo jogador ate todos jogarem.
  Curuna = quem comeca o Dia. Rotaciona anti-horario.

DIA (voce age)
  1. Coleta 2 recursos (Ouro/Magia, distribuicao livre)
  2. Sobe vida da cidade (2 Ouro por +1, cap = vida maxima)
  3. Invoca tropas (1 Magia + X Ouro) e herois (3 Magia)
  4. Move unidades (Cidade <-> Centro, 1x por turno)
  5. Compra/transmuta/vende artefatos (1 cada por dia)
  6. Lanca feitico (1 por turno, cooldown 2 turnos)

NOITE (combate)
  Ordem de resolucao por casa: Centro -> C4 -> C3 -> C2 -> C1.
  Cada unidade ataca 1x (bonus modificam isso).
  Atacante e alvo se machucam (retaliacao).

REGRAS CHAVE
  - Tropa: 1 Magia + X Ouro (X = vida desejada). 3 tipos: light(4) medium(6) heavy(8).
  - Heroi: 3 Magia. Voce escolhe 1 no setup.
  - Moeda: 1 por turno de juros se tiver Ouro acumulado (Ouro/5 arredondado).
  - Monumento: 1 Ouro. Precisa vida cheia. +1 artefato a cada 4 turnos.
"""

'''

EDITS.append((
    "jessica/main.py",
    "class RestartGame(Exception):\n    pass\n",
    STATUS_DESC + "\nclass RestartGame(Exception):\n    pass\n"
))

# =============================================================
# 5. main.py - funcoes de Ajuda
# =============================================================
AJUDA_FUNCS = '''\
def _ajuda_tutorial() -> None:
    console.print(Panel(TUTORIAL_TXT, border_style="cyan"))


def _ajuda_outros_povos(state, pid: int) -> None:
    for p in state.players:
        if p.id == pid:
            continue
        if not p.city.is_alive():
            continue
        console.print(Panel.fit(
            f"[bold]{p.name}[/bold] - Povo: [cyan]{p.people}[/cyan]",
            border_style="cyan"))
        console.print(f"  Passiva: {PASSIVA_DESC.get(p.people, '-')}")
        sp = spells_mod.spell_for_people(p.people)
        if sp:
            console.print(f"  Feitico: {FEITICO_DESC.get(sp.spell_id, sp.name)}")
        console.print(f"  Herois disponiveis:")
        for hd in heroes.heroes_for_people(p.people):
            desc = HERO_ABILITY_DESC.get(hd.hero_id, "")
            console.print(f"    [cyan]{hd.name}[/cyan] ({hd.life} vida) - {desc}")
        console.print()


def _ajuda_artefatos() -> None:
    table = Table(title="Referencia de Artefatos", box=box.ROUNDED)
    table.add_column("Carta")
    table.add_column("Efeito")
    for cid in sorted(ARTIFACT_CATALOG.keys()):
        d = ARTIFACT_CATALOG[cid]
        table.add_row(card_display(cid), d.description)
    console.print(table)


def _ajuda_statuses() -> None:
    table = Table(title="Referencia de Statuses", box=box.ROUNDED)
    table.add_column("Status")
    table.add_column("Efeito")
    for k, v in STATUS_DESC.items():
        table.add_row(k, v)
    console.print(table)


def _ajuda_atalhos() -> None:
    console.print(Panel.fit(
        "[bold]Atalhos de teclado[/bold]\\n\\n"
        "[cyan]1-6[/cyan]     Acoes do turno (coletar, subir vida, invocar, mover, monumento)\\n"
        "[cyan]7,8,9[/cyan]   Comprar (Ouro), Transmutar (Magia), Vender\\n"
        "[cyan]a[/cyan]       Jogar artefato da mao\\n"
        "[cyan]f[/cyan]       Lancar feitico\\n"
        "[cyan]E[/cyan]       Analisar campo de batalha (submenu)\\n"
        "[cyan]B[/cyan]       Panorama (Board) - tudo de todos\\n"
        "[cyan]m[/cyan]       Mapa\\n"
        "[cyan]l[/cyan]       Log do turno\\n"
        "[cyan]R[/cyan]       Relatorios (producao, combate, artefatos)\\n"
        "[cyan]?[/cyan]       Ajuda (esta tela)\\n"
        "[cyan]M[/cyan]       Menu (colher de cha, mola, recomecar)\\n"
        "[cyan]0[/cyan]       Passar a vez",
        border_style="cyan"))


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
        _ajuda_atalhos()


def _relatorio_producao(state) -> None:
    table = Table(title="Producao acumulada", box=box.ROUNDED)
    table.add_column("Jogador")
    table.add_column("Povo")
    table.add_column("Ouro coletado", justify="right")
    table.add_column("Magia coletada", justify="right")
    table.add_column("Tropas", justify="right")
    table.add_column("Herois", justify="right")
    table.add_column("Feiticos", justify="right")
    for p in state.players:
        s = p.stats or {}
        table.add_row(
            p.name, p.people,
            str(s.get("gold_collected", 0)),
            str(s.get("magic_collected", 0)),
            str(s.get("troops_summoned", 0)),
            str(s.get("heroes_summoned", 0)),
            str(s.get("spells_cast", 0)),
        )
    console.print(table)


def _relatorio_combate(state) -> None:
    table = Table(title="Combate", box=box.ROUNDED)
    table.add_column("Jogador")
    table.add_column("Dano causado", justify="right")
    table.add_column("Dano recebido", justify="right")
    table.add_column("Kills", justify="right")
    table.add_column("Mortes", justify="right")
    for p in state.players:
        s = p.stats or {}
        table.add_row(
            p.name,
            str(s.get("damage_dealt", 0)),
            str(s.get("damage_taken", 0)),
            str(s.get("kills", 0)),
            str(s.get("deaths", 0)),
        )
    console.print(table)


def _relatorio_artefatos(state) -> None:
    table = Table(title="Artefatos", box=box.ROUNDED)
    table.add_column("Jogador")
    table.add_column("Comprados", justify="right")
    table.add_column("Jogados", justify="right")
    table.add_column("Vendidos", justify="right")
    for p in state.players:
        s = p.stats or {}
        table.add_row(
            p.name,
            str(s.get("artifacts_bought", 0)),
            str(s.get("artifacts_played", 0)),
            str(s.get("artifacts_sold", 0)),
        )
    console.print(table)


def _relatorio_economia(state) -> None:
    if not state.timeline:
        console.print("[dim]Nenhum turno completo ainda.[/dim]")
        return
    for label, key in (("Ouro", "gold"), ("Magia", "magic"), ("Vida", "life")):
        table = Table(title=f"{label} ao fim de cada turno", box=box.ROUNDED)
        table.add_column("Turno", justify="right")
        for p in state.players:
            table.add_column(p.name, justify="right")
        for entry in state.timeline:
            row = [str(entry["turn"])]
            for p in state.players:
                val = entry.get("resources", {}).get(p.id, {}).get(key, "-")
                row.append(str(val))
            table.add_row(*row)
        console.print(table)
        console.print()


def _menu_relatorios(state, pid: int) -> None:
    opts = [
        "Producao acumulada",
        "Combate",
        "Artefatos",
        "Economia por turno",
        "Voltar",
    ]
    idx = pick_index("Relatorios", opts)
    if idx == 0:
        _relatorio_producao(state)
    elif idx == 1:
        _relatorio_combate(state)
    elif idx == 2:
        _relatorio_artefatos(state)
    elif idx == 3:
        _relatorio_economia(state)


'''

EDITS.append((
    "jessica/main.py",
    "def _get_actions(state, player) -> list[tuple[str, str, str]]:",
    AJUDA_FUNCS + "def _get_actions(state, player) -> list[tuple[str, str, str]]:"
))

# =============================================================
# 6. main.py - botoes no menu principal
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    r.append(("Analisar", "E", "Analisar campo de batalha"))
    r.append(("Atalhos", "m", "Mapa"))
    r.append(("Atalhos", "B", "Panorama (Board)"))
    r.append(("Atalhos", "l", "Log do turno"))
    r.append(("Menu", "M", "Menu do sistema"))
    return r''',
    '''\
    r.append(("Analisar", "E", "Analisar campo de batalha"))
    r.append(("Atalhos", "m", "Mapa"))
    r.append(("Atalhos", "B", "Panorama (Board)"))
    r.append(("Atalhos", "l", "Log do turno"))
    r.append(("Relatorios", "R", "Relatorios (producao, combate)"))
    r.append(("Ajuda", "?", "Ajuda"))
    r.append(("Menu", "M", "Menu do sistema"))
    return r'''
))

# =============================================================
# 7. main.py - handle_action: adiciona R e ?
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    elif choice == "l":
        show_turn_log(state)
    elif choice == "M":''',
    '''\
    elif choice == "l":
        show_turn_log(state)
    elif choice == "R":
        _menu_relatorios(state, pid)
    elif choice == "?":
        _menu_ajuda(state, pid)
    elif choice == "M":'''
))

# =============================================================
# 8. main.py - imports novos
# =============================================================
EDITS.append((
    "jessica/main.py",
    "from .core.artifacts import card_display, get_definition, ARTIFACT_CATALOG",
    "from .core.artifacts import card_display, get_definition, ARTIFACT_CATALOG"
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
        print("Defina JESSICA_ROOT ou mova o script para perto do projeto.")
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