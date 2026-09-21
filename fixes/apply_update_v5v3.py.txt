"""apply_update_v5v3a: reorganiza Acoes e Artefatos em submenus."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v3a_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. main.py - submenus novos antes de _get_actions
# =============================================================
SUBMENUS = '''\
def _menu_acoes_turno(state, pid: int):
    """Submenu de acoes do turno (numeros 1-6 antigos)."""
    player = get_player(state, pid)
    options = [
        ("1", "Coletar recursos (2)"),
        ("2", f"Subir vida da Cidade ({CITY_LIFE_COST_GOLD} Ouro/+1)"),
        ("3", "Invocar Tropa"),
        ("4", "Invocar Heroi"),
        ("5", "Mover unidade"),
        ("6", f"Construir Monumento ({MONUMENT_COST_GOLD} Ouro)"),
    ]
    labels = []
    for key, label in options:
        if key == "3" and peoples.has_7_dwarves_chosen(player):
            labels.append(f"[dim]({label} - bloqueado: 7 Anoes)[/dim]")
        else:
            labels.append(label)
    labels.append("Voltar")
    idx = pick_index("Acoes do turno", labels)
    if idx == len(options):
        return None
    return _do_action(state, pid, options[idx][0])


def _menu_artefatos(state, pid: int):
    """Submenu de artefatos."""
    options = [
        ("7", f"Comprar com Ouro ({ARTIFACT_GOLD_COST})"),
        ("8", f"Transmutar com Magia ({ARTIFACT_MAGIC_COST})"),
        ("9", f"Vender ({ARTIFACT_SELL_GOLD} Ouro)"),
        ("a", "Jogar artefato da mao"),
    ]
    labels = [label for _, label in options] + ["Voltar"]
    idx = pick_index("Artefatos", labels)
    if idx == len(options):
        return None
    return _do_action(state, pid, options[idx][0])


'''

EDITS.append((
    "jessica/main.py",
    "def _get_actions(state, player) -> list[tuple[str, str, str]]:",
    SUBMENUS + "def _get_actions(state, player) -> list[tuple[str, str, str]]:"
))

# =============================================================
# 2. main.py - _get_actions: vira menu top-level enxuto
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def _get_actions(state, player) -> list[tuple[str, str, str]]:
    magic_reduction = peoples.magic_cost_reduction(player)
    troop_cost = max(0, 1 - magic_reduction)
    hero_cost = peoples.hero_summon_cost(player)
    sp = spells_mod.spell_for_people(player.people)

    r = []
    r.append(("Acoes", "1", "Coletar recursos (2)"))
    r.append(("Acoes", "2", f"Subir vida da Cidade ({CITY_LIFE_COST_GOLD} Ouro/+1)"))
    if not peoples.has_7_dwarves_chosen(player):
        r.append(("Acoes", "3", f"Invocar Tropa ({troop_cost} Magia + X Ouro)"))
    else:
        r.append(("Acoes", "3", "[bloqueado] Sem tropas (7 Anoes)"))
    if player.people == "mortos_vivos":
        r.append(("Acoes", "4", f"Invocar Heroi ({hero_cost} Magia, escolher agora)"))
    elif player.chosen_hero_id == "seven_dwarves":
        alive_ids = {u.hero_id for u in player.units if isinstance(u, Hero) and u.is_alive()}
        nxt = heroes.next_dwarf_to_summon(alive_ids)
        label = f"Invocar Heroi (proximo: {heroes.hero_name(nxt) if nxt else 'nenhum'})"
        r.append(("Acoes", "4", label))
    elif player.chosen_hero_id == "caroco":
        r.append(("Acoes", "4", "Invocar Caroco (4 Magia se algum morreu)"))
    else:
        r.append(("Acoes", "4", f"Invocar Heroi ({hero_cost} Magia)"))
    r.append(("Acoes", "5", "Mover unidade"))
    r.append(("Acoes", "6", f"Construir Monumento ({MONUMENT_COST_GOLD} Ouro)"))

    r.append(("Artefatos", "7", f"Comprar com Ouro ({ARTIFACT_GOLD_COST})"))
    r.append(("Artefatos", "8", f"Transmutar com Magia ({ARTIFACT_MAGIC_COST})"))
    r.append(("Artefatos", "9", f"Vender ({ARTIFACT_SELL_GOLD} Ouro)"))
    r.append(("Artefatos", "a", "Jogar artefato da mao"))''',
    '''\
def _get_actions(state, player) -> list[tuple[str, str, str]]:
    sp = spells_mod.spell_for_people(player.people)

    r = []
    r.append(("Turno", "1", "Acoes (coletar, invocar, mover, monumento)"))
    r.append(("Turno", "2", "Artefatos (comprar, transmutar, vender, jogar)"))
    r.append(("Turno", "3", f"Lancar feitico: {sp.name}" if sp else "Lancar feitico"))'''
))

# =============================================================
# 3. main.py - remove a linha "r.append(('Especiais', 'f', ...))"
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
    if sp:
        cd_str = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd_str = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        label = f"Lancar feitico: {sp.name}{cd_str}"
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            label += " (bloqueado)"
        r.append(("Especiais", "f", label))
''',
    '''\
'''
))

# =============================================================
# 4. main.py - renomeia handle_action -> _do_action
# =============================================================
EDITS.append((
    "jessica/main.py",
    "def handle_action(state, pid: int, choice: str) -> str | None:",
    "def _do_action(state, pid: int, choice: str) -> str | None:"
))

# =============================================================
# 5. main.py - novo handle_action (router)
# =============================================================
# Insere antes de "def run_player_day"
ROUTER = '''\
def handle_action(state, pid: int, choice: str) -> str | None:
    """Router: submenus para [1]/[2]/[3]; resto vai direto pro _do_action."""
    if choice == "1":
        return _menu_acoes_turno(state, pid)
    if choice == "2":
        return _menu_artefatos(state, pid)
    if choice == "3":
        return _do_action(state, pid, "f")
    return _do_action(state, pid, choice)


'''

EDITS.append((
    "jessica/main.py",
    "def run_player_day(state, pid: int) -> str | None:",
    ROUTER + "def run_player_day(state, pid: int) -> str | None:"
))

# =============================================================
# 6. main.py - atualiza _do_action: keys antigas continuam funcionando
# =============================================================
# Os branches internos em _do_action ainda recebem keys "1".."6", "7".."9", "a", "f", etc.
# Como handle_action agora trata "1" e "2" como submenu, e "3" como feitico,
# _do_action NUNCA vai receber esses keys do top-level. Mas o submenu chama
# _do_action com eles. OK.
#
# Problema: o branch "elif choice == 'f'" continua valido. OK.
# Problema: handle_action agora trata "3" como feitico. Mas "3" na _do_action
# era "Invocar Tropa". Como handle_action nunca passa "3" pro _do_action (ele
# redireciona pra "f"), OK. O submenu de Acoes chama _do_action(state, pid, "3")
# que continua invocando tropa. OK.
#
# Nenhuma edicao precisa aqui. Pulando.

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
        print("Defina JESSICA_ROOT ou rode da pasta correta.")
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