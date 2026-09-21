apply_update_v5v9 ordem de casas na noite, ordem de declaracao por inicio,
   cancelar por ultimo em mover, Musashi persistente.
from pathlib import Path
from datetime import datetime
import os
import re
import shutil

def _find_project_root() - Path
    env = os.environ.get(JESSICA_ROOT)
    if env
        p = Path(env)
        if (p  jessica  main.py).exists()
            return p
    candidates = [
        Path.home()  Downloads  jessica,
        Path.home()  jessica,
        Path.cwd(),
        Path(__file__).resolve().parent.parent,
    ]
    for c in candidates
        if (c  jessica  main.py).exists()
            return c
    return Path.home()  Downloads  jessica

ROOT = _find_project_root()
BACKUP_DIR = Path(__file__).resolve().parent.parent  backups  fv5v9_{datetime.now().strftime('%Y%m%d_%H%M%S')}

EDITS list[tuple[str, str, str]] = []

# =============================================================
# 1. models.py - Player.miyamoto_life_max_bonus + GameState.night_start_positions
# =============================================================
EDITS.append((
    jessicacoremodels.py,
        garoche_life_max_bonus int = 0n,
        garoche_life_max_bonus int = 0n
        miyamoto_life_max_bonus int = 0n
))

EDITS.append((
    jessicacoremodels.py,
        morning_gains list[dict] = field(default_factory=list)n,
        morning_gains list[dict] = field(default_factory=list)n
        night_start_positions dict = field(default_factory=dict)n
))

# =============================================================
# 2. serialize.py - persistir novos campos
# =============================================================
EDITS.append((
    jessicacoreserialize.py,
    '        garoche_life_max_bonus p.garoche_life_max_bonus,n',
    '        garoche_life_max_bonus p.garoche_life_max_bonus,n'
    '        miyamoto_life_max_bonus p.miyamoto_life_max_bonus,n'
))
EDITS.append((
    jessicacoreserialize.py,
    '        garoche_life_max_bonus=d.get(garoche_life_max_bonus, 0),n',
    '        garoche_life_max_bonus=d.get(garoche_life_max_bonus, 0),n'
    '        miyamoto_life_max_bonus=d.get(miyamoto_life_max_bonus, 0),n'
))
EDITS.append((
    jessicacoreserialize.py,
    '            morning_gains [dict(e) for e in s.morning_gains]}',
    '            morning_gains [dict(e) for e in s.morning_gains],n'
    '            night_start_positions dict(s.night_start_positions)}'
))
EDITS.append((
    jessicacoreserialize.py,
    '    state.morning_gains = [dict(e) for e in d.get(morning_gains, [])]n'
    '    return state',
    '    state.morning_gains = [dict(e) for e in d.get(morning_gains, [])]n'
    '    state.night_start_positions = dict(d.get(night_start_positions, {}))n'
    '    return state'
))

# =============================================================
# 3. peoples.py - Miyamoto persiste
# =============================================================
EDITS.append((
    jessicacorepeoples.py,
    '''
    for u in killer_player.units
        if not (isinstance(u, Hero) and u.is_alive())
            continue
        if not heroes.has_ability(u.hero_id, gain_max_life_on_kill)
            continue
        if u.house == dead_unit.house
            ganho = dead_unit.statuses.get(life_at_death, dead_unit.life_max)
            u.life_max += ganho
            log(state, f  {u.id} (Miyamoto) +{ganho} vida maxima.)''',
    '''
    for u in killer_player.units
        if not (isinstance(u, Hero) and u.is_alive())
            continue
        if not heroes.has_ability(u.hero_id, gain_max_life_on_kill)
            continue
        if u.house == dead_unit.house
            ganho = dead_unit.statuses.get(life_at_death, dead_unit.life_max)
            u.life_max += ganho
            killer_player.miyamoto_life_max_bonus += ganho
            log(state, f  {u.id} (Miyamoto) +{ganho} vida maxima 
                       f(persistente {killer_player.miyamoto_life_max_bonus}).)'''
))

# =============================================================
# 4. actions.py - summon_hero aplica bonus de Miyamoto
# =============================================================
EDITS.append((
    jessicacoreactions.py,
    '''
    hdef = heroes.get_hero(target_id)
    hero_life_max = hdef.life
    if hdef.hero_id == garoche
        hero_life_max += player.garoche_life_max_bonus
    if player.people == peoples.PEOPLE_GIGANTES and state.turn % 4 == 0
        hero_life_max = 2''',
    '''
    hdef = heroes.get_hero(target_id)
    hero_life_max = hdef.life
    if hdef.hero_id == garoche
        hero_life_max += player.garoche_life_max_bonus
    if hdef.hero_id == miyamoto
        hero_life_max += player.miyamoto_life_max_bonus
    if player.people == peoples.PEOPLE_GIGANTES and state.turn % 4 == 0
        hero_life_max = 2'''
))

# =============================================================
# 5. turn.py - snapshot de posicoes no inicio da noite
# =============================================================
EDITS.append((
    jessicacoreturn.py,
    '''
def end_day(state GameState) - None
    if state.phase != Phase.DAY
        raise TurnError(Nao esta na fase do Dia.)
    state.deaths_this_night = []
    artifacts_effects.on_night_start(state)
    _luna_return(state)
    state.phase = Phase.NIGHT
    log(state, f--- Fase da Noite (Turno {state.turn}) ---)''',
    '''
def end_day(state GameState) - None
    if state.phase != Phase.DAY
        raise TurnError(Nao esta na fase do Dia.)
    state.deaths_this_night = []
    # Snapshot das posicoes no inicio da noite (para ordem de declaracao)
    state.night_start_positions = {}
    for p in state.players
        for u in p.units
            if u.is_alive()
                state.night_start_positions[u.id] = u.house
    artifacts_effects.on_night_start(state)
    _luna_return(state)
    state.phase = Phase.NIGHT
    log(state, f--- Fase da Noite (Turno {state.turn}) ---)'''
))

# =============================================================
# 6. main.py - cancelar por ultimo em mover
# =============================================================
EDITS.append((
    jessicamain.py,
    '''
        dests = valid_destinations(state, unit)
        if not dests
            raise ActionError(Sem destinos.)
        labels = [Cancelar] + [house_short(state, d) for d in dests]
        idx2 = pick_index(Destino, labels)
        if idx2 == 0
            console.print([yellow]Movimento cancelado.[yellow])
            return None
        move_unit(state, pid, unit.id, dests[idx2 - 1])
        console.print([green]Movimento ok.[green])''',
    '''
        dests = valid_destinations(state, unit)
        if not dests
            raise ActionError(Sem destinos.)
        labels = [house_short(state, d) for d in dests] + [Cancelar]
        idx2 = pick_index(Destino, labels)
        if idx2 == len(dests)
            console.print([yellow]Movimento cancelado.[yellow])
            return None
        move_unit(state, pid, unit.id, dests[idx2])
        console.print([green]Movimento ok.[green])'''
))

# =============================================================
# 7. main.py - _order_players_for_house respeita night_start_positions
# =============================================================
EDITS.append((
    jessicamain.py,
    '''
def _order_players_for_house(state, pids_here list[int], house str) - list[int]
    for pid in pids_here
        p = get_player(state, pid)
        if p.bater_primeiro_turn == state.turn
            others = [x for x in pids_here if x != pid]
            return [pid] + others''',
    '''
def _was_present_at_night_start(state, unit, house str) - bool
    return state.night_start_positions.get(unit.id) == house


def _order_players_for_house(state, pids_here list[int], house str) - list[int]
    # Ordem de declaracao quem ja estava no inicio da Noite primeiro
    def _sort_key(pid)
        p = get_player(state, pid)
        # start se algum unit estava la no inicio da noite
        present_at_start = any(
            _was_present_at_night_start(state, u, house)
            for u in p.units
            if u.is_alive() and u.house == house
        )
        return 0 if present_at_start else 1
    pids_here = sorted(pids_here, key=_sort_key)
    for pid in pids_here
        p = get_player(state, pid)
        if p.bater_primeiro_turn == state.turn
            others = [x for x in pids_here if x != pid]
            return [pid] + others'''
))

# =============================================================
# 8. main.py - ordem de casas Centro - inverso do dia
# =============================================================
EDITS.append((
    jessicamain.py,
    '''
    house_order = [CENTER, city_4, city_3, city_2, city_1]
    for house in house_order
        pids_here = []
        for pid in all_pids
            player = get_player(state, pid)
            if any(u.house == house and u.is_alive() for u in player.units)
                pids_here.append(pid)''',
    '''
    day = day_order(state)
    city_order = list(reversed(day))
    house_order = [CENTER] + [fcity_{pid} for pid in city_order]
    for house in house_order
        pids_here = []
        for pid in all_pids
            player = get_player(state, pid)
            if any(u.house == house and u.is_alive() for u in player.units)
                pids_here.append(pid)'''
))


def _apply_edits(rel_path str, full Path, backup_dir Path) - bool
    if not full.exists()
        print(fAVISO - {rel_path} nao existe ({full}).)
        return False
    original = full.read_text(encoding=utf-8)
    current = original
    applied = 0
    for path, old, new in EDITS
        if path != rel_path
            continue
        if old not in current
            print(f  AVISO - snippet nao encontrado em {rel_path})
            print(f    {old[90]}...)
            continue
        current = current.replace(old, new, 1)
        applied += 1
    if current == original
        print(fAVISO - nenhuma edicao aplicada em {rel_path}.)
        return False
    backup_path = backup_dir  rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, backup_path)
    full.write_text(current, encoding=utf-8)
    print(fOK  - {rel_path} ({applied} edit(s)))
    return True


def main() - None
    print(fProjeto em {ROOT})
    print(fBackup em  {BACKUP_DIR}n)
    if not (ROOT  jessica  main.py).exists()
        print(fERRO nao achei {ROOT}jessicamain.py)
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    edited_paths = sorted({e[0] for e in EDITS})
    total = 0
    for rel_path in edited_paths
        full = ROOT  rel_path
        if _apply_edits(rel_path, full, BACKUP_DIR)
            total += 1

    print(fn{total} arquivo(s) modificado(s).)
    print(fBackup {BACKUP_DIR})
    print(nRode)
    print(  python testsrun_all.py)
    print(  python -m jessica.main)


if __name__ == __main__
    main()