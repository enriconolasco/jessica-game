"""apply_fix_v5v8b: aplica v5v8 via regex (substitui funcao inteira)."""
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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / f"v5v8b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _replace_func(text: str, sig: str, new_body: str):
    """Substitui def <sig>(...) ate o proximo def/class. Retorna (novo_texto, aplicou)."""
    pattern = re.compile(
        r"def " + re.escape(sig) + r"\([^)]*\).*?(?=\n(?:def |class )|\Z)",
        re.DOTALL,
    )
    if not pattern.search(text):
        return text, False
    return pattern.sub(new_body.rstrip() + "\n", text, count=1), True


# =============================================================
# Novas versoes das funcoes
# =============================================================

NEW_MORCEGO = '''\
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
    log(state, f"{player.name}: {t.id} virou morcego (+1 movimento).")
'''

NEW_VOVO = '''\
def has_vovo_bonus(state: GameState, attacker: Unit) -> bool:
    """Vovo Gamba concede +1 dano GLOBAL a todas as tropas do dono."""
    if not isinstance(attacker, Troop):
        return False
    owner = get_player(state, attacker.owner_id)
    for u in owner.units:
        if isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba":
            return True
    return False
'''

NEW_EXTRA_SLOTS = '''\
def extra_troop_slots(player: Player, state: GameState | None = None) -> dict[str, int]:
    if player.people == PEOPLE_ORCS:
        return {"extra": 1}
    if player.people == PEOPLE_MORTOS_VIVOS:
        # MV: 3 tropas base + 2 (ghoul/esqueleto) SO com Zoia viva. Sem "extra".
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zoia"
               for u in player.units):
            return {"ghoul": 1, "esqueleto": 1}
    if player.people == PEOPLE_GNOMOS and state is not None:
        effective = sao_tome_effective_peoples(state, player)
        result: dict[str, int] = {}
        if PEOPLE_ORCS in effective:
            result["extra"] = 1
        return result
    return {}
'''

NEW_MENU_INFO = '''\
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
        show_habilidades(state, pid)
'''

NEW_FIND_TARGETS = '''\
def find_targets(state, unit):
    # Espoliado nao pode atacar nem declarar em cidade
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        return []
    targets = []
    house = unit.house
    can_attack_city = (not isinstance(unit, Hero)) or unit.hero_can_attack_city
    if isinstance(unit, Hero) and not can_attack_city:
        owner = get_player(state, unit.owner_id)
        for u in owner.units:
            if (isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "din" and u.house == house):
                can_attack_city = True
                break
        if (not can_attack_city and peoples.is_lua_cheia(state, owner.id)
                and owner.people == peoples.PEOPLE_LOBISOMENS):
            for u in owner.units:
                if isinstance(u, Hero) and u.is_alive() and u.hero_id == "cigana" and u.house == house:
                    can_attack_city = True
                    break
    if can_attack_city and house.startswith("city_"):
        target_pid = int(house.split("_")[1])
        if target_pid != unit.owner_id:
            target = get_player(state, target_pid)
            if target.city.is_alive():
                targets.append(("city", str(target_pid),
                                f"Cidade de {target.name} ({target.city.life})"))
    for other in state.players:
        if other.id == unit.owner_id:
            continue
        for u in other.units:
            if u.house == house and u.is_alive():
                if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
                    continue
                kind = "Heroi" if isinstance(u, Hero) else "Tropa"
                targets.append(("unit", u.id,
                                f"{kind} {u.id} de {other.name} ({u.life})"))
    return targets
'''

NEW_PROMPT_ATTACK = '''\
def prompt_attack(state, unit, targets) -> Attack | None:
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        console.print(f"  [yellow]{unit.id} nao pode atacar (Espoliou com Arken).[/yellow]")
        return None
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_short(state, unit.house)}")
    options = ["Nao atacar"] + [t[2] for t in targets]
    idx = pick_index("Acao", options)
    if idx == 0:
        return None
    return Attack(unit.id, targets[idx - 1][0], targets[idx - 1][1])
'''


def _apply_func(rel_path: str, full: Path, sig: str, new_body: str,
                backup_dir: Path) -> bool:
    if not full.exists():
        print(f"AVISO - {rel_path} nao existe.")
        return False
    original = full.read_text(encoding="utf-8")
    patched, ok = _replace_func(original, sig, new_body)
    if not ok:
        print(f"  AVISO - funcao '{sig}' nao achada em {rel_path}.")
        return False
    if patched == original:
        print(f"  AVISO - '{sig}' nao mudou.")
        return False
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(patched, encoding="utf-8")
    print(f"  OK  - {rel_path}: {sig} substituida")
    return True


def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("jessica/core/actions.py", "_spell_transformar_morcego", NEW_MORCEGO),
        ("jessica/core/peoples.py", "has_vovo_bonus", NEW_VOVO),
        ("jessica/core/peoples.py", "extra_troop_slots", NEW_EXTRA_SLOTS),
        ("jessica/main.py",         "_menu_informacoes",     NEW_MENU_INFO),
        ("jessica/main.py",         "find_targets",          NEW_FIND_TARGETS),
        ("jessica/main.py",         "prompt_attack",         NEW_PROMPT_ATTACK),
    ]

    total = 0
    for rel_path, sig, new_body in jobs:
        full = ROOT / rel_path
        if _apply_func(rel_path, full, sig, new_body, BACKUP_DIR):
            total += 1

    print(f"\n{total} funcao(oes) substituida(s).")
    print(f"Backup: {BACKUP_DIR}")
    print("\nRode:")
    print("  python tests\\run_all.py")
    print("  python -m jessica.main")


if __name__ == "__main__":
    main()