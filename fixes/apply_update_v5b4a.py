"""apply_update_v5b4a: UI infra + 2 povos novos + H6 + H8 + H11."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b4a_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. Povos novos em PEOPLES
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
PEOPLES = ["humanos", "anoes", "orcs", "fadas",
           "vampiros", "lobisomens", "gigantes", "mortos_vivos"]''',
    '''\
PEOPLES = ["humanos", "anoes", "orcs", "fadas",
           "vampiros", "lobisomens", "gigantes", "mortos_vivos",
           "filhos_floresta", "gnomos_duendes"]'''
))

# =============================================================
# 2. HEROES_BY_PEOPLE
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    "mortos_vivos": [],
}''',
    '''\
    "mortos_vivos": [],
    "filhos_floresta": ["Guarari", "Aiquara", "Baoba-bá"],
    "gnomos_duendes": ["Bimbo do Mal", "São Tomé", "Zebum"],
}'''
))

# =============================================================
# 3. PASSIVA_DESC
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    "mortos_vivos": "Heróis custam 2 Magia, sem escolha no setup. Os 3 disponiveis na partida.",
}''',
    '''\
    "mortos_vivos": "Heróis custam 2 Magia, sem escolha no setup. Os 3 disponiveis na partida.",
    "filhos_floresta": "Florescimento Exuberante: Cidade comeca com 1 vida; no turno 13 recebe +2 Vida, +2 Ouro, +2 Magia.",
    "gnomos_duendes": "Continue Apostando: 4 apostas (H/C/D/S) alocadas em outros jogadores no inicio do turno.",
}'''
))

# =============================================================
# 4. FEITICO_DESC
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    "levantar_mortos": "Levantar os Mortos: escolha 2 tropas e invoque com 1 de vida.",
}''',
    '''\
    "levantar_mortos": "Levantar os Mortos: escolha 2 tropas e invoque com 1 de vida.",
    "decompor": "Decompor: sacrifica um elemento seu por Magia (Heroi +4 / Tropa vida+2 / Muralha -1vida +3).",
    "imitacao_gnomerica": "Imitacao Gnomerica: copia o feitico sorteado do dia.",
}'''
))

# =============================================================
# 5. H6: Cancelar ao jogar artefato
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    elif choice == "a":
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = [card_display(c) for c in player.hand]
        card = player.hand[pick_index("Jogar", labels)]
        if card == "PENA":
            _handle_pena(state, pid, card)
            return None
        choice_data = _ask_choice_for_artifact(state, pid, card)
        play_artifact(state, pid, card, choice=choice_data)
        console.print(f"[green]Jogou: {card_display(card)}[/green]")''',
    '''\
    elif choice == "a":
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = ["Cancelar"] + [card_display(c) for c in player.hand]
        idx = pick_index("Jogar", labels)
        if idx == 0:
            console.print("[yellow]Cancelado.[/yellow]")
            return None
        card = player.hand[idx - 1]
        if card == "PENA":
            _handle_pena(state, pid, card)
            return None
        choice_data = _ask_choice_for_artifact(state, pid, card)
        play_artifact(state, pid, card, choice=choice_data)
        console.print(f"[green]Jogou: {card_display(card)}[/green]")'''
))

# =============================================================
# 6. H2: Mostrar mao e artefatos em campo no show_state_for_player
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    else:
        console.print("[dim]Sem unidades.[/dim]")
    console.print()''',
    '''\
    else:
        console.print("[dim]Sem unidades.[/dim]")

    # H2: mao + artefatos em campo
    if player.hand:
        mao = ", ".join(card_display(c) for c in player.hand)
        console.print(f"[bold]Mao ({len(player.hand)}):[/bold] {mao}")
    if player.field_artifacts:
        campo = ", ".join(card_display(a.card_id) for a in player.field_artifacts)
        console.print(f"[bold]Artefatos ativos:[/bold] {campo}")
    console.print()'''
))

# =============================================================
# 7. H11: Armadura reativa - callback
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
from .core.combat import (
    resolve_attack, resolve_attack_day, Attack, CombatError,
    _effective_max_attacks, _attacks_used,
)''',
    '''\
from .core.combat import (
    resolve_attack, resolve_attack_day, Attack, CombatError,
    _effective_max_attacks, _attacks_used,
)
from .core import combat as _combat_mod'''
))

EDITS.append((
    "jessica/main.py",
    '''\
class RestartGame(Exception):
    pass''',
    '''\
class RestartGame(Exception):
    pass


def _armor_choice_prompt(player, dmg):
    cap = min(dmg, player.city.gold)
    console.print(f"[yellow]{player.name}: Armadura de Ouro ativa. "
                  f"Dano {dmg}, Ouro {player.city.gold}, cap {cap}.[/yellow]")
    v = IntPrompt.ask(f"Quanto Ouro pagar (0 a {cap})", default=cap)
    v = max(0, min(v, cap))
    return v'''
))

# =============================================================
# 8. H8: Registrar callback de armadura em main()
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def main() -> None:
    while True:''',
    '''\
def main() -> None:
    _combat_mod.set_armor_choice_fn(_armor_choice_prompt)
    while True:'''
))

# =============================================================
# 9. H8: Mapa/estudar durante a Noite
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_map(state)
    _ask_vovo_position(state)''',
    '''\
def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_map(state)
    # H8: ver mapa / estudar campo antes das declaracoes
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
    _ask_vovo_position(state)'''
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