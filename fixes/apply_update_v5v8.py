"""apply_update_v5v8: info->povos, morcego +1 move, vovo gamba global,
   espoliado sem opcao de ataque."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v8_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. actions.py - Transformar em Morcego: +1 movimento sem resetar
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '''\
def _spell_transformar_morcego(state, player, choice):
    tid = choice.get("unit_id")
    if not tid:
        raise ActionError("Precisa alvo.")
    t = next((u for u in player.units if u.id == tid and u.is_alive()), None)
    if t is None:
        raise ActionError("Alvo nao encontrado.")
    t.statuses["morcego_until_turn"] = state.turn
    if t.max_moves_this_turn < 2:
        t.max_moves_this_turn = 2
        t.has_moved_this_turn = False
        t.moves_this_turn = 0
    log(state, f"{player.name}: {t.id} virou morcego.")''',
    '''\
def _spell_transformar_morcego(state, player, choice):
    tid = choice.get("unit_id")
    if not tid:
        raise ActionError("Precisa alvo.")
    t = next((u for u in player.units if u.id == tid and u.is_alive()), None)
    if t is None:
        raise ActionError("Alvo nao encontrado.")
    t.statuses["morcego_until_turn"] = state.turn
    # +1 movimento (nao reabre movimentos ja usados)
    if t.max_moves_this_turn < 2:
        t.max_moves_this_turn = 2
        t.has_moved_this_turn = t.moves_this_turn >= t.max_moves_this_turn
    log(state, f"{player.name}: {t.id} virou morcego (+1 movimento).")'''
))

# =============================================================
# 2. peoples.py - Vovo Gamba global
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    '''\
def has_vovo_bonus(state: GameState, attacker: Unit) -> bool:
    if not isinstance(attacker, Troop):
        return False
    owner = get_player(state, attacker.owner_id)
    for u in owner.units:
        if (isinstance(u, Hero) and u.is_alive()
                and u.hero_id == "vovo_gamba"
                and u.house == attacker.house):
            return True
    return False''',
    '''\
def has_vovo_bonus(state: GameState, attacker: Unit) -> bool:
    """Vovo Gamba concede +1 dano GLOBAL a todas as tropas do dono."""
    if not isinstance(attacker, Troop):
        return False
    owner = get_player(state, attacker.owner_id)
    for u in owner.units:
        if isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba":
            return True
    return False'''
))

# =============================================================
# 3. peoples.py - check defensivo de MV sem "extra"
# =============================================================
EDITS.append((
    "jessica/core/peoples.py",
    '''\
def extra_troop_slots(player: Player, state: GameState | None = None) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    if player.people == PEOPLE_MORTOS_VIVOS:
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
               for u in player.units):
            return {"ghoul": 1, "esqueleto": 1}''',
    '''\
def extra_troop_slots(player: Player, state: GameState | None = None) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    if player.people == PEOPLE_MORTOS_VIVOS:
        # MV: 3 tropas base + 2 (ghoul/esqueleto) SO com Zoia viva. Sem "extra".
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
               for u in player.units):
            return {"ghoul": 1, "esqueleto": 1}'''
))

# =============================================================
# 4. main.py - mostra povo completo (todos os povos disponiveis)
# =============================================================
POVO_FUNCS = '''\
TODOS_POVOS = [
    "humanos", "anoes", "orcs", "fadas", "vampiros",
    "lobisomens", "gigantes", "mortos_vivos",
    "filhos_floresta", "gnomos_duendes",
]


def _mostrar_povo_completo(povo: str) -> None:
    c = _pcolor(povo)
    console.print(Panel.fit(
        f"[bold {c}]{povo.upper()}[/bold {c}]",
        border_style=c))
    console.print(f"[bold]Passiva:[/bold] {PASSIVA_DESC.get(povo, '-')}")
    sp = spells_mod.spell_for_people(povo)
    if sp:
        console.print(f"[bold]Feitico:[/bold] {sp.name} - "
                      f"{FEITICO_DESC.get(sp.spell_id, sp.description)}")
    console.print("[bold]Herois:[/bold]")
    for hd in heroes.heroes_for_people(povo):
        console.print(f"  [cyan]{hd.name}[/cyan] ({hd.life} vida)")
        desc = HERO_ABILITY_DESC.get(hd.hero_id, "-")
        console.print(f"    {desc}")
    console.print()


def _menu_povos(state, pid: int) -> None:
    em_jogo = {p.people for p in state.players if p.people}
    labels = []
    for pv in TODOS_POVOS:
        tag = " [em jogo]" if pv in em_jogo else ""
        labels.append(f"{pv}{tag}")
    labels.append("Voltar")
    idx = pick_index("Ver povo", labels)
    if idx == len(TODOS_POVOS):
        return
    _mostrar_povo_completo(TODOS_POVOS[idx])


'''

EDITS.append((
    "jessica/main.py",
    "def show_habilidades(state, pid: int) -> None:",
    POVO_FUNCS + "def show_habilidades(state, pid: int) -> None:"
))

# =============================================================
# 5. main.py - adiciona "Ver povo" no submenu de Informacoes
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def _menu_informacoes(state, pid: int) -> None:
    opts = [
        "Loja",
        "Inspecionar local / unidade",
        "Artefatos em campo (todos)",
        "Passivas ativas",
        "Unidades empaladas / infectadas",
        "Eventos futuros",
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
        show_eventos_futuros(state)
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
))

# =============================================================
# 6. main.py - find_targets: filtra espoliado + explica
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def find_targets(state, unit):
    targets = []
    house = unit.house
    can_attack_city = (not isinstance(unit, Hero)) or unit.hero_can_attack_city''',
    '''\
def find_targets(state, unit):
    # Espoliado nao pode atacar nem declarar em cidade
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        return []
    targets = []
    house = unit.house
    can_attack_city = (not isinstance(unit, Hero)) or unit.hero_can_attack_city'''
))

# =============================================================
# 7. main.py - prompt_attack: mostra razao se nao ha alvos
# =============================================================
EDITS.append((
    "jessica/main.py",
    '''\
def prompt_attack(state, unit, targets) -> Attack | None:
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_short(state, unit.house)}")
    options = ["Nao atacar"] + [t[2] for t in targets]
    idx = pick_index("Acao", options)
    if idx == 0:
        return None
    return Attack(unit.id, targets[idx - 1][0], targets[idx - 1][1])''',
    '''\
def prompt_attack(state, unit, targets) -> Attack | None:
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        console.print(f"  [yellow]{unit.id} nao pode atacar (Espoliou com Arken).[/yellow]")
        return None
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_short(state, unit.house)}")
    options = ["Nao atacar"] + [t[2] for t in targets]
    idx = pick_index("Acao", options)
    if idx == 0:
        return None
    return Attack(unit.id, targets[idx - 1][0], targets[idx - 1][1])'''
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