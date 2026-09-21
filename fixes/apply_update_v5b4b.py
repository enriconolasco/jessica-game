"""apply_update_v5b4b: UI das 10 acoes novas + apostas gnomos + Zebum 7 Anoes."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b4b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

EDITS: list[tuple[str, str, str]] = []

# =============================================================
# 1. models.py - flag zebum_seven_dwarves
# =============================================================
EDITS.append((
    "jessica/core/models.py",
    "    bets_need_realocacao: bool = False\n",
    "    bets_need_realocacao: bool = False\n    zebum_seven_dwarves: bool = False\n"
))

# =============================================================
# 2. serialize.py - persistir
# =============================================================
EDITS.append((
    "jessica/core/serialize.py",
    '        "bets_need_realocacao": p.bets_need_realocacao,\n',
    '        "bets_need_realocacao": p.bets_need_realocacao,\n'
    '        "zebum_seven_dwarves": p.zebum_seven_dwarves,\n'
))
EDITS.append((
    "jessica/core/serialize.py",
    '        bets_need_realocacao=d.get("bets_need_realocacao", False),\n',
    '        bets_need_realocacao=d.get("bets_need_realocacao", False),\n'
    '        zebum_seven_dwarves=d.get("zebum_seven_dwarves", False),\n'
))

# =============================================================
# 3. actions.py - bloqueia tropa se zebum_seven_dwarves
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '    player = get_player(state, player_id)\n'
    '    if peoples.has_7_dwarves_chosen(player):\n'
    '        raise ActionError("Escolheu Os 7 Anoes: nao pode invocar Tropas.")\n',
    '    player = get_player(state, player_id)\n'
    '    if peoples.has_7_dwarves_chosen(player) or player.zebum_seven_dwarves:\n'
    '        raise ActionError("Os 7 Anoes (ou Zebum que os obteve): sem Tropas.")\n'
))

# =============================================================
# 4. actions.py - Zebum + 7 Anoes (caso especial)
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    '    if hero_id in player.zebum_herois:\n'
    '        raise ActionError("Ja obtido; use reinvocacao (3 Magia).")\n'
    '    custo = _zebum_custo_atual(player)\n',
    '    if hero_id in player.zebum_herois:\n'
    '        raise ActionError("Ja obtido; use reinvocacao (3 Magia).")\n'
    '    custo = _zebum_custo_atual(player)\n'
    '    if hero_id == "seven_dwarves":\n'
    '        if player.zebum_seven_dwarves:\n'
    '            raise ActionError("Os 7 Anoes ja foram obtidos.")\n'
    '        if player.correct_bets < custo:\n'
    '            raise ActionError(f"Precisa {custo} apostas corretas.")\n'
    '        player.correct_bets -= custo\n'
    '        player.zebum_herois.append("seven_dwarves")\n'
    '        player.zebum_seven_dwarves = True\n'
    '        hdef = heroes.get_hero("dain")\n'
    '        n = sum(1 for u in player.units if isinstance(u, Hero))\n'
    '        unit_id = f"p{player_id}_zebum_dain_{n}"\n'
    '        h = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",\n'
    '                 life=hdef.life, life_max=hdef.life,\n'
    '                 hero_id="dain", has_moved_this_turn=True, moves_this_turn=1)\n'
    '        player.units.append(h)\n'
    '        log(state, f"{player.name}: Zebum obteve Os 7 Anoes (Dain). Tropas bloqueadas.")\n'
    '        return\n'
))

# =============================================================
# 5. actions.py - helper invocar proximo anao
# =============================================================
EDITS.append((
    "jessica/core/actions.py",
    'def zebum_reinvocar(state: GameState, player_id: int, hero_id: str) -> None:\n'
    '    player = get_player(state, player_id)\n'
    '    if hero_id not in player.zebum_herois:\n'
    '        raise ActionError("Heroi nao foi obtido via Zebum.")\n',
    'def zebum_invocar_proximo_anao(state: GameState, player_id: int) -> Hero:\n'
    '    player = get_player(state, player_id)\n'
    '    if not player.zebum_seven_dwarves:\n'
    '        raise ActionError("Zebum ainda nao obteve Os 7 Anoes.")\n'
    '    alive_dwarf_ids = {u.hero_id for u in player.units\n'
    '                       if isinstance(u, Hero) and u.is_alive()\n'
    '                       and heroes.is_seven_dwarf(u.hero_id)}\n'
    '    nxt = heroes.next_dwarf_to_summon(alive_dwarf_ids)\n'
    '    if nxt is None:\n'
    '        raise ActionError("Todos os 7 Anoes ja foram invocados.")\n'
    '    idx = heroes.dwarf_index(nxt)\n'
    '    if idx > 0:\n'
    '        prev = heroes.SEVEN_DWARVES_ORDER[idx - 1]\n'
    '        if prev not in alive_dwarf_ids:\n'
    '            raise ActionError(f"Corrente: precisa invocar {prev} antes.")\n'
    '    if player.city.magic < 2:\n'
    '        raise ActionError("Precisa 2 Magia.")\n'
    '    player.city.magic -= 2\n'
    '    hdef = heroes.get_hero(nxt)\n'
    '    n = sum(1 for u in player.units if isinstance(u, Hero))\n'
    '    unit_id = f"p{player_id}_zebum_{nxt}_{n}"\n'
    '    h = Hero(id=unit_id, owner_id=player_id, house=f"city_{player_id}",\n'
    '             life=hdef.life, life_max=hdef.life,\n'
    '             hero_id=nxt, has_moved_this_turn=True, moves_this_turn=1)\n'
    '    player.units.append(h)\n'
    '    log(state, f"{player.name}: Zebum invocou {hdef.name} (2 Magia).")\n'
    '    return h\n'
    '\n'
    '\n'
    'def zebum_reinvocar(state: GameState, player_id: int, hero_id: str) -> None:\n'
    '    player = get_player(state, player_id)\n'
    '    if hero_id == "seven_dwarves":\n'
    '        raise ActionError("Use a opcao de Zebum+Anoes para o proximo da corrente.")\n'
    '    if hero_id not in player.zebum_herois:\n'
    '        raise ActionError("Heroi nao foi obtido via Zebum.")\n'
))

# =============================================================
# 6. main.py - imports
# =============================================================
EDITS.append((
    "jessica/main.py",
    '    dandara_invisibilidade, luide_vampa_mover, ActionError,\n)',
    '    dandara_invisibilidade, luide_vampa_mover, ActionError,\n'
    '    transformar_em_centauro, aiquara_mover, aiquara_atacar,\n'
    '    baoba_pagar_magia, bimbo_invisibilidade, bimbo_gastar_5,\n'
    '    zebum_invocar_heroi, zebum_reinvocar, zebum_invocar_proximo_anao,\n'
    '    gnomo_alocar_aposta,\n)'
))

# =============================================================
# 7. main.py - helpers novos antes de _get_actions
# =============================================================
HELPERS = '''\
# =============================================================
# Helpers UI dos novos povos
# =============================================================

def _gnomo_bets_menu(state, player):
    if player.people != "gnomos_duendes":
        return
    if not player.bets_need_realocacao:
        return
    console.print(Panel.fit("[bold cyan]Continue Apostando...[/bold cyan]",
                            border_style="cyan"))
    console.print(f"Apostas corretas acumuladas: [yellow]{player.correct_bets}[/yellow]")
    other_ids = [p.id for p in state.players
                 if p.id != player.id and p.city.is_alive()]
    if not other_ids:
        player.bets_need_realocacao = False
        return
    labels_alvo = [f"{get_player(state, pid).name} (J{pid})" for pid in other_ids]
    labels_alvo.append("(deixar vazio)")
    suits = [
        ("H", "H Copas - alvo constroi/perde Muralha"),
        ("C", "C Paus - alvo usa Artefato"),
        ("D", "D Ouros - alvo ganha/vende Artefato"),
        ("S", "S Espadas - alvo invoca/mata Tropa ou Heroi"),
    ]
    for suit, desc in suits:
        console.print(f"\\n[bold]{desc}[/bold]")
        idx = pick_index("Alvo", labels_alvo)
        if idx == len(labels_alvo) - 1:
            setattr(player, f"bet_{suit}_target", None)
        else:
            setattr(player, f"bet_{suit}_target", other_ids[idx])
    player.bets_need_realocacao = False


def _escolher_decompor(state, player):
    opts = ["Heroi (+4 Magia)", "Tropa (+vida atual + 2)",
            "Muralha (-1 Vida, +3 Magia)"]
    idx = pick_index("Decompor", opts)
    if idx == 0:
        herois = [u for u in player.units if isinstance(u, Hero) and u.is_alive()]
        if not herois:
            raise ActionError("Sem herois.")
        labels = [f"{u.id} ({heroes.hero_name(u.hero_id)})" for u in herois]
        h = herois[pick_index("Heroi", labels)]
        return {"kind": "hero", "unit_id": h.id}
    if idx == 1:
        tropas = [u for u in player.units if isinstance(u, Troop) and u.is_alive()]
        if not tropas:
            raise ActionError("Sem tropas.")
        labels = [f"{u.id} ({u.archetype.value} {u.life}/{u.life_max})" for u in tropas]
        t = tropas[pick_index("Tropa", labels)]
        return {"kind": "troop", "unit_id": t.id}
    return {"kind": "city"}


def _spell_choice_ui(state, player, spell_id):
    cd: dict = {}
    if spell_id in ("resistencia", "transformar_morcego", "licantropo"):
        if not player.units:
            raise ActionError("Sem unidades.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        cd["unit_id"] = player.units[pick_index("Alvo", labels)].id
    elif spell_id == "linhagem_ancestral":
        gigantes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()
                    and u.hero_id in ("joao_grandao", "pe_descalco", "caroco")]
        if not gigantes:
            raise ActionError("Sem herois Gigantes vivos.")
        labels = [heroes.hero_name(u.hero_id) for u in gigantes]
        cd["hero_id"] = gigantes[pick_index("Heroi", labels)].hero_id
    elif spell_id == "levantar_mortos":
        labels = ["light", "medium", "heavy", "extra", "ghoul", "esqueleto"]
        i1 = pick_index("Arquetipo 1", labels)
        i2 = pick_index("Arquetipo 2", labels)
        cd["archetypes"] = [labels[i1], labels[i2]]
    elif spell_id == "decompor":
        return _escolher_decompor(state, player)
    elif spell_id == "imitacao_gnomerica":
        raise ActionError("Nao pode imitar a si mesmo.")
    return cd


def _escolher_imitacao(state, player):
    sp_id = player.spell_copia_id
    if not sp_id:
        raise ActionError("Nenhum feitico sorteado pelo dia.")
    if sp_id == "imitacao_gnomerica":
        raise ActionError("Sorteou imitacao; nao pode copiar a si mesmo.")
    try:
        nome = spells_mod.get_spell(sp_id).name
    except Exception:
        nome = sp_id
    console.print(f"[cyan]Imitacao Gnomerica: {nome}[/cyan]")
    return _spell_choice_ui(state, player, sp_id)


def _aiquara_ui(state, pid):
    player = get_player(state, pid)
    aiquara = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "aiquara"), None)
    if aiquara is None:
        raise ActionError("Aiquara nao esta viva.")
    inimigos = []
    for other in state.players:
        if other.id == pid or not other.city.is_alive():
            continue
        for u in other.units:
            if u.house == aiquara.house and u.is_alive():
                inimigos.append((other, u))
    if not inimigos:
        raise ActionError("Sem inimigos na casa de Aiquara.")
    labels = []
    for o, u in inimigos:
        tipo = heroes.hero_name(u.hero_id) if isinstance(u, Hero) else f"Tropa {u.archetype.value}"
        labels.append(f"{u.id} ({tipo}) de {o.name} ({u.life}/{u.life_max})")
    idx = pick_index("Alvo", labels)
    tgt_owner, tgt_unit = inimigos[idx]
    acao = pick_index("Aiquara", ["Forcar movimento", "Forcar ataque"])
    if acao == 0:
        dests = valid_destinations(state, tgt_unit)
        if not dests:
            raise ActionError("Sem destinos.")
        labels2 = ["Cancelar"] + [house_short(state, d) for d in dests]
        idx2 = pick_index("Destino", labels2)
        if idx2 == 0:
            return
        aiquara_mover(state, pid, tgt_unit.id, dests[idx2 - 1])
        console.print("[green]Movimento forcado.[/green]")
    else:
        alvos = []
        alvos_labels = []
        for other in state.players:
            if other.id == tgt_unit.owner_id:
                continue
            for u in other.units:
                if u.house == tgt_unit.house and u.is_alive():
                    alvos.append(("unit", u.id))
                    tipo = heroes.hero_name(u.hero_id) if isinstance(u, Hero) else f"Tropa {u.archetype.value}"
                    alvos_labels.append(f"{u.id} ({tipo}) de {other.name} ({u.life})")
        home = tgt_unit.house
        if home.startswith("city_"):
            city_pid = int(home.split("_")[1])
            if city_pid != tgt_unit.owner_id:
                pc = get_player(state, city_pid)
                if pc.city.is_alive():
                    alvos.append(("city", str(city_pid)))
                    alvos_labels.append(f"Cidade de {pc.name} ({pc.city.life})")
        if not alvos:
            raise ActionError("Sem alvos validos.")
        idx2 = pick_index("Alvo", alvos_labels)
        tt, ti = alvos[idx2]
        aiquara_atacar(state, pid, tgt_unit.id, tt, ti)
        console.print("[green]Ataque forcado.[/green]")


def _bimbo_ui(state, pid):
    player = get_player(state, pid)
    bimbo = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive()
                  and u.hero_id == "bimbo_do_mal"), None)
    if bimbo is None:
        raise ActionError("Bimbo nao esta vivo.")
    console.print(f"[cyan]Apostas corretas: {player.correct_bets}[/cyan]")
    opts = ["Invisivel (1 aposta correta)", "Artefato da Loja (5 apostas corretas)"]
    idx = pick_index("Bimbo", opts)
    if idx == 0:
        bimbo_invisibilidade(state, pid)
        console.print("[green]Bimbo invisivel ate o fim do turno.[/green]")
    else:
        bimbo_gastar_5(state, pid)
        console.print("[green]Artefato obtido.[/green]")


def _zebum_obter_novo(state, player):
    peoples_presentes = {p.people for p in state.players
                         if p.people and p.people != "gnomos_duendes"}
    candidatos = []
    labels = []
    for povo in peoples_presentes:
        try:
            for h in heroes.heroes_for_people(povo):
                hid = h.hero_id
                if hid == "zebum":
                    continue
                if hid in player.zebum_herois:
                    continue
                skip = False
                for other in state.players:
                    if other.id != player.id and other.chosen_hero_id == hid:
                        skip = True
                        break
                if skip:
                    continue
                outro = False
                for other in state.players:
                    if other.id != player.id and hid in other.zebum_herois:
                        outro = True
                        break
                if outro:
                    continue
                candidatos.append(hid)
                labels.append(h.name)
        except Exception:
            continue
    if not candidatos:
        raise ActionError("Sem herois disponiveis.")
    idx = pick_index("Heroi", labels)
    zebum_invocar_heroi(state, player.id, candidatos[idx])
    console.print("[green]Zebum obteve o heroi.[/green]")


def _zebum_ui(state, pid):
    player = get_player(state, pid)
    zebum = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive()
                  and u.hero_id == "zebum"), None)
    if zebum is None:
        raise ActionError("Zebum nao esta vivo.")
    console.print(f"[cyan]Apostas corretas: {player.correct_bets}[/cyan]")
    custo = 4 + 2 * len(player.zebum_herois)
    opts = [f"Obter novo heroi (custo {custo})"]
    outros = [h for h in player.zebum_herois if h != "seven_dwarves"]
    if outros:
        opts.append("Reinvocar heroi obtido (3 Magia)")
    if player.zebum_seven_dwarves:
        opts.append("Zebum + Anoes: invocar proximo (2 Magia)")
    idx = pick_index("Zebum", opts)
    if idx == 0:
        _zebum_obter_novo(state, player)
    elif idx == 1 and outros:
        labels = [heroes.hero_name(h) for h in outros]
        idx2 = pick_index("Heroi", labels)
        zebum_reinvocar(state, pid, outros[idx2])
        console.print("[green]Reinvocado.[/green]")
    elif player.zebum_seven_dwarves:
        zebum_invocar_proximo_anao(state, pid)
        console.print("[green]Anao invocado.[/green]")


'''
EDITS.append((
    "jessica/main.py",
    'def _get_actions(state, player) -> list[tuple[str, str, str]]:',
    HELPERS + 'def _get_actions(state, player) -> list[tuple[str, str, str]]:'
))

# =============================================================
# 8. main.py - novos botoes no menu
# =============================================================
EDITS.append((
    "jessica/main.py",
    '    luide = next((u for u in player.units\n'
    '                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa"), None)\n'
    '    if luide is not None and not player.has_cast_spell_this_turn:\n'
    '        r.append(("Especiais", "z", "Luide Vampa: ativar movimento noturno"))\n'
    '\n'
    '    besouro = next((u for u in player.units',
    '    luide = next((u for u in player.units\n'
    '                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa"), None)\n'
    '    if luide is not None and not player.has_cast_spell_this_turn:\n'
    '        r.append(("Especiais", "z", "Luide Vampa: ativar movimento noturno"))\n'
    '\n'
    '    if player.people == "gnomos_duendes" and player.bets_need_realocacao:\n'
    '        r.append(("Gnomos", "A", "Alocar apostas do turno"))\n'
    '\n'
    '    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "guarari"\n'
    '           for u in player.units):\n'
    '        r.append(("Especiais", "q", "Guarari: tropa -> Centauro (2 Magia)"))\n'
    '    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "aiquara"\n'
    '           for u in player.units):\n'
    '        r.append(("Especiais", "i", "Aiquara: controlar inimigo"))\n'
    '    if (player.people == "filhos_floresta"\n'
    '            and not any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "baoba_ba"\n'
    '                        for u in player.units)):\n'
    '        r.append(("Especiais", "b", f"Baoba-ba: pagar Magia ({player.baoba_pagamentos}/3)"))\n'
    '    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "bimbo_do_mal"\n'
    '           for u in player.units):\n'
    '        r.append(("Especiais", "p", f"Bimbo ({player.correct_bets} apostas corretas)"))\n'
    '    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zebum"\n'
    '           for u in player.units):\n'
    '        r.append(("Especiais", "g", "Zebum: invocar/reinvocar heroi"))\n'
    '\n'
    '    besouro = next((u for u in player.units'
))

# =============================================================
# 9. main.py - branches em handle_action
# =============================================================
EDITS.append((
    "jessica/main.py",
    '    elif choice == "z":\n'
    '        luide_vampa_mover(state, pid)\n'
    '        console.print("[green]Luide Vampa: movimento noturno ativo.[/green]")',
    '    elif choice == "z":\n'
    '        luide_vampa_mover(state, pid)\n'
    '        console.print("[green]Luide Vampa: movimento noturno ativo.[/green]")\n'
    '    elif choice == "A":\n'
    '        _gnomo_bets_menu(state, player)\n'
    '    elif choice == "q":\n'
    '        guarari = next((u for u in player.units\n'
    '                        if isinstance(u, Hero) and u.is_alive()\n'
    '                        and u.hero_id == "guarari"), None)\n'
    '        if guarari is None:\n'
    '            raise ActionError("Guarari nao esta vivo.")\n'
    '        tropas = [u for u in player.units\n'
    '                  if isinstance(u, Troop) and u.is_alive()\n'
    '                  and u.house == guarari.house]\n'
    '        if not tropas:\n'
    '            raise ActionError("Sem tropas na casa de Guarari.")\n'
    '        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in tropas]\n'
    '        t = tropas[pick_index("Tropa", labels)]\n'
    '        transformar_em_centauro(state, pid, t.id)\n'
    '        console.print("[green]Centauro ativo ate o fim da Noite.[/green]")\n'
    '    elif choice == "i":\n'
    '        _aiquara_ui(state, pid)\n'
    '    elif choice == "b":\n'
    '        baoba_pagar_magia(state, pid)\n'
    '        console.print(f"[green]Baoba-ba: {player.baoba_pagamentos}/3.[/green]")\n'
    '    elif choice == "p":\n'
    '        _bimbo_ui(state, pid)\n'
    '    elif choice == "g":\n'
    '        _zebum_ui(state, pid)'
))

# =============================================================
# 10. main.py - decompor/imitacao no feitico
# =============================================================
EDITS.append((
    "jessica/main.py",
    '        elif sp.spell_id == "levantar_mortos":\n'
    '            labels = ["light", "medium", "heavy", "extra", "ghoul", "esqueleto"]\n'
    '            i1 = pick_index("Arquetipo 1", labels)\n'
    '            i2 = pick_index("Arquetipo 2", labels)\n'
    '            choice_data["archetypes"] = [labels[i1], labels[i2]]\n'
    '        cast_spell(state, pid, choice_data)',
    '        elif sp.spell_id == "levantar_mortos":\n'
    '            labels = ["light", "medium", "heavy", "extra", "ghoul", "esqueleto"]\n'
    '            i1 = pick_index("Arquetipo 1", labels)\n'
    '            i2 = pick_index("Arquetipo 2", labels)\n'
    '            choice_data["archetypes"] = [labels[i1], labels[i2]]\n'
    '        elif sp.spell_id == "decompor":\n'
    '            choice_data = _escolher_decompor(state, player)\n'
    '        elif sp.spell_id == "imitacao_gnomerica":\n'
    '            choice_data = _escolher_imitacao(state, player)\n'
    '        cast_spell(state, pid, choice_data)'
))

# =============================================================
# 11. main.py - HERO_ABILITY_DESC
# =============================================================
EDITS.append((
    "jessica/main.py",
    '    "cova_rasa": "Cova Rasa: amaldicoa inimigos proximos no inicio da Noite.",\n}',
    '    "cova_rasa": "Cova Rasa: amaldicoa inimigos proximos no inicio da Noite.",\n'
    '    "guarari": "Centauro: 2 Magia transforma tropa da casa em Centauro ate fim da Noite.",\n'
    '    "aiquara": "Ninfa: controla inimigo da casa (mover no Dia, atacar na Noite).",\n'
    '    "baoba_ba": "Anciao: 1 Magia x 3 turnos para invocar. Tropas aliadas na casa dele.",\n'
    '    "bimbo_do_mal": "Gastar aposta: invisivel (1) ou artefato da Loja (5).",\n'
    '    "sao_tome": "Passivas dos alvos das apostas. 2 determinacoes por dia.",\n'
    '    "zebum": "Mistico: apostas corretas compram herois estrangeiros.",\n}'
))

# =============================================================
# 12. main.py - apostas no inicio do dia
# =============================================================
EDITS.append((
    "jessica/main.py",
    'def run_player_day(state, pid: int) -> str | None:\n'
    '    player = get_player(state, pid)\n'
    '    try:\n'
    '        _resolve_pending_choice_if_any(state, pid)\n'
    '    except (ActionError, ValueError) as e:\n'
    '        console.print(f"[red]Erro pendente: {e}[/red]")',
    'def run_player_day(state, pid: int) -> str | None:\n'
    '    player = get_player(state, pid)\n'
    '    try:\n'
    '        _resolve_pending_choice_if_any(state, pid)\n'
    '    except (ActionError, ValueError) as e:\n'
    '        console.print(f"[red]Erro pendente: {e}[/red]")\n'
    '    if player.people == "gnomos_duendes" and player.bets_need_realocacao:\n'
    '        _gnomo_bets_menu(state, player)'
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