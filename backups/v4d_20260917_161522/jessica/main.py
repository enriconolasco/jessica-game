"""Jessica - Prototipo v0.3."""
from __future__ import annotations
import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box

from .core.setup import run_setup, roll_d20_order
from .core.state import make_rng, get_player
from .core.actions import (
    collect_resources, raise_city_life, summon_troop, summon_hero,
    move_unit, build_monument, buy_artifact_with_gold,
    transmute_artifact_with_magic, sell_artifact, play_artifact,
    resolve_pending_artifact_choice, use_heal, cast_spell, arken_espolia,
    besouro_mandinga, use_or_give_pena, tintin_ficar_invisivel, ActionError,
)
from .core.combat import (
    resolve_attack, resolve_attack_day, Attack, CombatError,
    _effective_max_attacks, _attacks_used,
)
from .core.turn import start_turn, start_player_day, day_order, end_day, end_turn
from .core.constants import (
    CITY_HOUSES, CENTER, TroopArchetype, Phase, DEFAULT_SEED,
    TROOP_MAX_LIFE, RESOURCES_PER_DAY, CITY_LIFE_COST_GOLD,
    HERO_SUMMON_COST_MAGIC, TROOP_SUMMON_COST_MAGIC, MONUMENT_COST_GOLD,
    ARTIFACT_GOLD_COST, ARTIFACT_MAGIC_COST, ARTIFACT_SELL_GOLD,
    DEFAULT_CITY_LIFE_START, DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC,
)
from .core.models import Hero, Troop
from .core.artifacts import card_display, get_definition, ARTIFACT_CATALOG
from .core.serialize import state_to_dict, state_from_dict
from .core import artifacts_effects, peoples, heroes, spells as spells_mod


console = Console()

PEOPLES = ["humanos", "anoes", "orcs", "fadas"]

HEROES_BY_PEOPLE = {
    "humanos": ["Miyamoto Musashi", "Besouro Mangangá", "Iúna"],
    "anoes": ["Barbadourada", "Ori", "Os 7 Anões"],
    "orcs": ["Ga'Roche", "Arken", "Vovó Gamba"],
    "fadas": ["Ainai", "Valendar", "Luna"],
}

PASSIVA_DESC = {
    "humanos": "Roca de Quilombo: rola 1D4 (+1 dado por Pena ativa) toda manha.",
    "anoes": "Mineiro Carreiro: +1 Ouro por unidade ana viva, toda manha.",
    "orcs": "Berco de Guerreiros: -1 Magia em invocacoes. Arquetipo extra (4 vida).",
    "fadas": "Asas Encantadas: +1 Magia quando unidade anda. Herois ganham 1 artefato ao matar Heroi.",
}

FEITICO_DESC = {
    "resistencia": "Resistencia (Humanos): de Resistencia a um aliado nesta Noite.",
    "armadura_de_ouro": "Armadura de Ouro (Anoes): cap X por hit.",
    "espoliar": "Espoliar (Orcs): +2 Ouro por Cidade inimiga ocupada.",
    "sonho_lucido": "Sonho Lucido (Fadas): troca o naipe do proximo artefato automaticamente.",
}

HERO_ABILITY_DESC = {
    "miyamoto": "Invencivel sob o Sol: ataca de Dia. +vida max ao matar. 2 ataques se for o mais forte.",
    "besouro": "o Maioral: dobro + resistencia vs >=. Mandinga: 1 artefato da mao no inicio da Noite.",
    "iuna": "Aguia Negra: recebe exatamente 1 de dano. Da 1D4 aleatorio. Adiciona 4 Penas ao ser invocada.",
    "barbadourada": "Filho das Cachoeiras: +1 Magia por artefato na mao, toda manha.",
    "ori": "Velho Mestre Ferreiro: ele + aliados na mesma casa ganham Resistencia.",
    "seven_dwarves": "Os 7 Anoes: invoque cada um com 2 Magia, em corrente. Sem Tropas.",
    "dain": "Alergico (1): quem ataca Dain morre no fim da Noite.",
    "buin": "Dengoso (2): nao pode ser atacado por Herois.",
    "bein": "Soneca (3): quem for atacado dorme ate os Anoes serem Curuna. Acorda se atacado.",
    "boin": "Feliz (4): ao comprar/transmutar, ve 2 e escolhe 1 artefato.",
    "tintin": "Bobao (5): pode ficar Invisivel no Dia (recarga 1 turno).",
    "don": "Zangado (6): 1 ataque extra por Anao proximo.",
    "din": "Mestre (7): Anoes proximos podem atacar Bases inimigas.",
    "garoche": "Rei do Sertao: executa sem aliados proximos. +1 vida ao executar.",
    "arken": "Cacador: pode Espoliar todo Dia.",
    "vovo_gamba": "Protetora: tropas na casa dela dao +1 dano. Escolhe posicao no local.",
    "ainai": "Fada da Vinganca: teleporta para onde morreu Fada/Elfo na Noite. +1 Magia.",
    "valendar": "Rainha Maga: substitui Sonho Lucido por bonus de naipe.",
    "luna": "Sonhadora: aplica Sonho Lucido a N artefatos. Retorna ao local de origem se andou.",
}


class RestartGame(Exception):
    pass


def house_display(state, house: str) -> str:
    if house == CENTER:
        return "Centro"
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        return f"Cidade {get_player(state, pid).name}"
    return house


def _get_actions(state, player) -> list[tuple[str, str, str]]:
    """Retorna (section, key, label)."""
    magic_reduction = peoples.magic_cost_reduction(player)
    troop_cost = max(0, TROOP_SUMMON_COST_MAGIC - magic_reduction)
    hero_cost = max(0, HERO_SUMMON_COST_MAGIC - magic_reduction)
    sp = spells_mod.spell_for_people(player.people)

    r: list[tuple[str, str, str]] = []

    # --- Acoes ---
    r.append(("Acoes", "1", "Coletar recursos (2)"))
    r.append(("Acoes", "2", f"Subir vida da Cidade ({CITY_LIFE_COST_GOLD} Ouro/+1)"))
    if not peoples.has_7_dwarves_chosen(player):
        r.append(("Acoes", "3", f"Invocar Tropa ({troop_cost} Magia + X Ouro)"))
    else:
        r.append(("Acoes", "3", "[bloqueado] Sem tropas (7 Anoes)"))
    if player.chosen_hero_id == "seven_dwarves":
        alive_ids = {u.hero_id for u in player.units if isinstance(u, Hero) and u.is_alive()}
        nxt = heroes.next_dwarf_to_summon(alive_ids)
        label = f"Invocar Heroi (proximo: {heroes.hero_name(nxt) if nxt else 'nenhum'})"
        r.append(("Acoes", "4", label))
    else:
        r.append(("Acoes", "4", f"Invocar Heroi ({hero_cost} Magia)"))
    r.append(("Acoes", "5", "Mover unidade"))
    r.append(("Acoes", "6", f"Construir Monumento ({MONUMENT_COST_GOLD} Ouro)"))

    # --- Artefatos ---
    r.append(("Artefatos", "7", f"Comprar com Ouro ({ARTIFACT_GOLD_COST}, no Centro)"))
    r.append(("Artefatos", "8", f"Transmutar com Magia ({ARTIFACT_MAGIC_COST})"))
    r.append(("Artefatos", "9", f"Vender ({ARTIFACT_SELL_GOLD} Ouro)"))
    r.append(("Artefatos", "a", "Jogar artefato da mao"))
    r.append(("Artefatos", "b", "Ver artefatos ativos"))

    # --- Especiais ---
    if sp:
        cd_str = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd_str = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        label = f"Lancar feitico: {sp.name}{cd_str}"
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            label += " (bloqueado)"
        r.append(("Especiais", "f", label))
    miyamoto_atks = peoples.miyamoto_attacks_remaining(state, player)
    if miyamoto_atks > 0:
        r.append(("Especiais", "d", f"Miyamoto: atacar de Dia ({miyamoto_atks})"))
    arken = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "arken"), None)
    if arken is not None and player.arken_espolia_used_turn != state.turn:
        r.append(("Especiais", "e", "Arken: Espoliar"))
    tintin = next((u for u in player.units
                   if isinstance(u, Hero) and u.is_alive() and u.hero_id == "tintin"), None)
    if tintin is not None:
        cd = tintin.statuses.get("tintin_cooldown_until_turn", -1)
        if cd <= state.turn:
            r.append(("Especiais", "t", "Tin Tin: ficar Invisivel"))
    if player.pending_heals > 0:
        r.append(("Especiais", "h", f"Usar cura pendente ({player.pending_heals})"))

    # --- Info ---
    r.append(("Info", "r", f"Resumo (turno {state.turn})"))
    r.append(("Info", "m", "Mapa"))
    r.append(("Info", "l", "Loja"))
    r.append(("Info", "k", "Habilidades do povo/herois"))

    # --- Sistema ---
    r.append(("Sistema", "u", "Colher de cha (refazer meu dia)"))
    r.append(("Sistema", "w", "Mola (jogador anterior)"))
    r.append(("Sistema", "x", "Reiniciar partida"))

    return r


def pick_index(prompt: str, options: list[str]) -> int:
    table = Table(box=box.SIMPLE)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Opcao")
    for i, opt in enumerate(options, 1):
        table.add_row(str(i), opt)
    console.print(table)
    while True:
        try:
            n = IntPrompt.ask(prompt, default=1)
            if 1 <= n <= len(options):
                return n - 1
        except Exception:
            pass
        console.print(f"[red]Escolha entre 1 e {len(options)}[/red]")


def valid_destinations(state, unit) -> list[str]:
    if unit.house.startswith("city_"):
        return [CENTER]
    if unit.house == CENTER:
        return [h for h in CITY_HOUSES
                if get_player(state, int(h.split("_")[1])).city.is_alive()]
    return []


def _ask_int(prompt: str, default: int, min_val: int = 0, max_val: int = 999) -> int:
    while True:
        try:
            v = IntPrompt.ask(prompt, default=default)
            if min_val <= v <= max_val:
                return v
        except Exception:
            pass
        console.print(f"[red]Valor entre {min_val} e {max_val}.[/red]")


def setup_ui():
    console.print(Panel.fit(
        "[bold cyan]JESSICA[/bold cyan]\n"
        "[italic]Prototipo v0.3[/italic]",
        border_style="cyan"))
    console.print()
    seed = DEFAULT_SEED
    console.print(f"[dim]Seed: {seed}[/dim]\n")
    console.print("[bold]Configuracao da partida[/bold]\n")
    city_life = _ask_int(f"Vida inicial da Cidade [{DEFAULT_CITY_LIFE_START}]",
                         default=DEFAULT_CITY_LIFE_START, min_val=1, max_val=100)
    city_life_max = _ask_int(f"Vida maxima da Cidade [{DEFAULT_CITY_LIFE_MAX}]",
                             default=DEFAULT_CITY_LIFE_MAX, min_val=city_life, max_val=100)
    gold_start = _ask_int(f"Ouro inicial [{DEFAULT_STARTING_GOLD}]",
                          default=DEFAULT_STARTING_GOLD, min_val=0, max_val=999)
    magic_start = _ask_int(f"Magia inicial [{DEFAULT_STARTING_MAGIC}]",
                           default=DEFAULT_STARTING_MAGIC, min_val=0, max_val=999)
    console.print()
    rng = make_rng(seed)
    order = roll_d20_order(rng, 4)
    table = Table(title="Ordem de turno", box=box.SIMPLE)
    table.add_column("Posicao", justify="right")
    table.add_column("Jogador", justify="right")
    for i, pid in enumerate(order, 1):
        table.add_row(str(i), f"Jogador {pid}")
    console.print(table)
    console.print()
    console.print("[bold]Nomes dos jogadores[/bold]\n")
    names: dict[int, str] = {}
    for pid in range(1, 5):
        names[pid] = Prompt.ask(f"Nome do Jogador {pid}", default=f"Jogador {pid}")
    console.print()
    choices: dict[int, dict] = {}
    console.print("[bold]Escolha de povos[/bold]\n")
    available_peoples = list(PEOPLES)
    for pid in order:
        console.print(f"Vez de [bold]{names[pid]}[/bold] (Jogador {pid}).")
        idx = pick_index("Povo", available_peoples)
        chosen = available_peoples[idx]
        available_peoples.remove(chosen)
        choices[pid] = {"povo": chosen}
        console.print(f"[green]{names[pid]} escolheu: {chosen}[/green]\n")
    console.print("[bold]Escolha de herois[/bold]\n")
    for pid in order:
        povo = choices[pid]["povo"]
        herois = HEROES_BY_PEOPLE[povo]
        console.print(f"Vez de [bold]{names[pid]}[/bold] ({povo}).")
        idx = pick_index("Heroi", herois)
        choices[pid]["heroi"] = herois[idx]
        console.print(f"[green]{names[pid]} escolheu: {herois[idx]}[/green]\n")
    state, _ = run_setup(
        all_peoples=PEOPLES, heroes_by_people=HEROES_BY_PEOPLE,
        choices=choices, seed=seed, turn_order=order,
        city_life=city_life, city_life_max=city_life_max,
        gold_start=gold_start, magic_start=magic_start,
    )
    for p in state.players:
        p.name = names[p.id]
    return state


def show_state_for_player(state, pid: int) -> None:
    player = get_player(state, pid)
    city = player.city
    mark = " [bold yellow]<- CURUNA[/bold yellow]" if state.curuna_id == pid else ""
    hero_display = "-"
    if player.chosen_hero_id:
        try:
            hd = heroes.get_hero(player.chosen_hero_id)
            hero_display = f"{hd.name} ({hd.life})"
        except KeyError:
            hero_display = player.chosen_hero_id
    sp = spells_mod.spell_for_people(player.people)
    sp_str = ""
    if sp:
        cd = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        sp_str = f" | Feitico: {sp.name}{cd}"
    console.print(f"[bold]{player.name}[/bold]{mark} - Povo: {player.people} - Heroi: {hero_display}{sp_str}")
    console.print(f"Cidade: vida {city.life}/{city.life_max} | Ouro: {city.gold} | Magia: {city.magic} | Mon: {'sim' if city.has_monument else 'nao'}")
    if player.pending_heals > 0:
        console.print(f"[green]Curas pendentes: {player.pending_heals}[/green]")
    if player.armor_gold_cap_per_hit > 0:
        console.print(f"[cyan]Armadura de Ouro - cap {player.armor_gold_cap_per_hit}/hit[/cyan]")
    if player.sonho_lucido_pending_turn == state.turn:
        suffix = " (multi - Luna)" if player.sonho_lucido_multi_turn == state.turn else ""
        console.print(f"[magenta]Sonho Lucido ATIVO neste turno{suffix}[/magenta]")
    if player.hand:
        table = Table(title="Mao", box=box.SIMPLE)
        table.add_column("Carta")
        for c in player.hand:
            table.add_row(card_display(c))
        console.print(table)
    else:
        console.print("[dim]Mao vazia.[/dim]")
    if player.field_artifacts:
        table = Table(title="Campo", box=box.SIMPLE)
        table.add_column("Carta")
        for a in player.field_artifacts:
            table.add_row(card_display(a.card_id))
        console.print(table)
    else:
        console.print("[dim]Campo vazio.[/dim]")
    if player.units:
        table = Table(title="Suas unidades", box=box.SIMPLE)
        table.add_column("ID"); table.add_column("Tipo"); table.add_column("Local")
        table.add_column("Vida", justify="right"); table.add_column("Flags", justify="left")
        for u in player.units:
            if isinstance(u, Hero):
                kind = f"Heroi {heroes.hero_name(u.hero_id)}"
            else:
                kind = f"Tropa {u.archetype.value}"
            flags = []
            if u.double_damage: flags.append("2xdano")
            if u.resistance_stacks: flags.append(f"Resx{u.resistance_stacks}")
            if u.original_owner_id is not None: flags.append("Qc")
            if u.statuses.get("cannot_attack_on_turn") == state.turn: flags.append("sem ataque")
            if u.statuses.get("sono_until_turn", -1) > state.turn: flags.append("dormindo")
            if u.statuses.get("invisivel_until_turn", -1) >= state.turn: flags.append("invisivel")
            flags_str = ", ".join(flags) if flags else "-"
            table.add_row(u.id, kind, house_display(state, u.house),
                          f"{u.life}/{u.life_max}", flags_str)
        console.print(table)
    else:
        console.print("[dim]Sem unidades.[/dim]")
    console.print()


def _strip_markup(s: str) -> str:
    return re.sub(r"\[/?[^\]]*\]", "", s)


def _pad(text: str, width: int) -> str:
    plain_len = len(_strip_markup(text))
    pad = max(0, width - plain_len)
    left = pad // 2
    right = pad - left
    return " " * left + text + " " * right


def _city_cell_lines(state, pid: int, width: int) -> list[str]:
    player = get_player(state, pid)
    city = player.city
    mark = " *" if state.curuna_id == pid else ""
    povo = player.people[:8]
    title = f"J{pid} {player.name[:8]}{mark}"
    sub = f"({povo})"
    vida = f"Vida {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"
    units = []
    for u in player.units:
        if u.house == f"city_{pid}":
            kind = "H" if isinstance(u, Hero) else "T"
            units.append(f"{kind}{u.life}")
    units_str = ", ".join(units) if units else "[dim]-[/dim]"
    return [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width),
            _pad(vida, width), _pad(units_str, width)]


def _center_cell_lines(state, width: int) -> list[str]:
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == CENTER:
                kind = "H" if isinstance(u, Hero) else "T"
                units.append(f"{p.name[:4]}-{kind}{u.life}")
    lines = [_pad("[bold]CENTRO[/bold]", width), _pad("", width)]
    if units:
        for u in units:
            lines.append(_pad(u, width))
    else:
        lines.append(_pad("[dim]-[/dim]", width))
    return lines


def _pad_to_height(lines: list[str], height: int, width: int) -> list[str]:
    while len(lines) < height:
        lines.append(" " * width)
    return lines[:height]


def show_map(state) -> None:
    w = 22
    j1 = _city_cell_lines(state, 1, w); j2 = _city_cell_lines(state, 2, w)
    j3 = _city_cell_lines(state, 3, w); j4 = _city_cell_lines(state, 4, w)
    center = _center_cell_lines(state, w)
    height = max(len(j1), len(j2), len(j3), len(j4), len(center), 3)
    j1 = _pad_to_height(j1, height, w); j2 = _pad_to_height(j2, height, w)
    j3 = _pad_to_height(j3, height, w); j4 = _pad_to_height(j4, height, w)
    center = _pad_to_height(center, height, w)
    empty = [" " * w for _ in range(height)]
    sep = " | "
    line_sep = "-" * (w * 3 + 6)
    for i in range(height):
        console.print(empty[i] + sep + j3[i] + sep + empty[i], highlight=False)
    console.print(line_sep, highlight=False)
    for i in range(height):
        console.print(j4[i] + sep + center[i] + sep + j2[i], highlight=False)
    console.print(line_sep, highlight=False)
    for i in range(height):
        console.print(empty[i] + sep + j1[i] + sep + empty[i], highlight=False)
    curuna = get_player(state, state.curuna_id)
    console.print()
    console.print(f"[bold yellow]* Curuna: {curuna.name}[/bold yellow]")
    console.print(f"[dim]Loja: {state.shop.size()} cartas[/dim]\n")


def show_resumo(state) -> None:
    table = Table(title=f"Resumo - Turno {state.turn} ({state.phase.value})", box=box.ROUNDED)
    table.add_column("Jogador"); table.add_column("Povo")
    table.add_column("Vida", justify="right"); table.add_column("Ouro", justify="right")
    table.add_column("Magia", justify="right"); table.add_column("Mao", justify="right")
    table.add_column("Campo", justify="right"); table.add_column("Mon.", justify="center")
    for p in state.players:
        mark = " *" if state.curuna_id == p.id else ""
        alive = p.city.is_alive()
        table.add_row(
            f"{p.name}{mark}" if alive else f"[red]{p.name} (morto)[/red]",
            p.people or "-",
            f"{p.city.life}/{p.city.life_max}" if alive else "-",
            str(p.city.gold) if alive else "-",
            str(p.city.magic) if alive else "-",
            str(len(p.hand)), str(len(p.field_artifacts)),
            "sim" if p.city.has_monument else "-")
    console.print(table)


def show_loja(state) -> None:
    from collections import Counter
    counts = Counter(state.shop.deck)
    table = Table(title=f"Loja - {state.shop.size()} cartas", box=box.ROUNDED)
    table.add_column("Carta"); table.add_column("Qtd", justify="right")
    for cid in sorted(ARTIFACT_CATALOG.keys()):
        table.add_row(card_display(cid), str(counts.get(cid, 0)))
    console.print(table)


def show_active_artifacts(state) -> None:
    table = Table(title="Artefatos ativos", box=box.ROUNDED)
    table.add_column("Jogador"); table.add_column("Carta"); table.add_column("Detalhes")
    found = False
    for p in state.players:
        for a in p.field_artifacts:
            found = True
            extra = ", ".join(f"{k}={v}" for k, v in a.extra.items()) if a.extra else "-"
            table.add_row(p.name, card_display(a.card_id), extra)
    if not found:
        console.print("[dim]Nenhum artefato ativo.[/dim]")
    else:
        console.print(table)


def show_habilidades(state, pid: int) -> None:
    player = get_player(state, pid)
    console.print(Panel.fit(
        f"[bold]{player.name}[/bold] - Povo: [cyan]{player.people}[/cyan]",
        border_style="cyan"))
    console.print("[bold]Passiva do povo[/bold]")
    console.print(PASSIVA_DESC.get(player.people, "-"))
    sp = spells_mod.spell_for_people(player.people)
    console.print("\n[bold]Feitico[/bold]")
    if sp is None:
        console.print("-")
    else:
        desc = FEITICO_DESC.get(sp.spell_id, sp.description)
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            desc += " [Valendar ativa: bloqueado, bonus por naipe em vigor]"
        console.print(desc)
        if state.turn < player.spell_cooldown_until_turn:
            console.print(f"[yellow]Recarga: {player.spell_cooldown_until_turn - state.turn} turno(s)[/yellow]")
    console.print("\n[bold]Herois do jogador[/bold]")
    has_any = False
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive():
            has_any = True
            hd = heroes.get_hero(u.hero_id)
            console.print(f"  [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_display(state, u.house)}")
            console.print(f"    {HERO_ABILITY_DESC.get(u.hero_id, hd.name)}")
    if not has_any:
        console.print("  [dim](nenhum heroi vivo)[/dim]")
    console.print("\n[bold]Herois dos outros (em campo)[/bold]")
    has_other = False
    for other in state.players:
        if other.id == pid:
            continue
        for u in other.units:
            if isinstance(u, Hero) and u.is_alive():
                has_other = True
                hd = heroes.get_hero(u.hero_id)
                console.print(f"  {other.name}: [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_display(state, u.house)}")
    if not has_other:
        console.print("  [dim](nenhum)[/dim]")


def menu_player_actions(state, player) -> str:
    actions = _get_actions(state, player)
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Secao", style="dim")
    table.add_column("Tecla", style="cyan", justify="center")
    table.add_column("Acao")
    current_section = None
    for section, key, label in actions:
        if section != current_section:
            table.add_section()
            current_section = section
        table.add_row(section, key, label)
    console.print(table)
    valid_keys = [k for _, k, _ in actions] + ["0"]
    return Prompt.ask("Acao (0 = Passar a vez)", choices=valid_keys, default="0")


def _ask_choice_for_artifact(state, pid: int, card_id: str) -> dict:
    player = get_player(state, pid)
    ctype = artifacts_effects.choice_type(card_id)
    if ctype == "own_unit":
        if not player.units:
            raise ActionError(f"{card_display(card_id)} precisa de alvo.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        return {"unit_id": player.units[pick_index("Alvo", labels)].id}
    if ctype == "any_unit":
        all_units, labels = [], []
        for other in state.players:
            if not other.city.is_alive():
                continue
            for u in other.units:
                all_units.append(u)
                labels.append(f"{u.id} de {other.name} ({u.life}/{u.life_max}, {house_display(state, u.house)})")
        if not all_units:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        return {"unit_id": all_units[pick_index("Alvo", labels)].id}
    if ctype == "any_player":
        others = [p for p in state.players if p.id != pid and p.city.is_alive()]
        if not others:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        labels = [f"{p.name} (J{p.id})" for p in others]
        return {"target_player_id": others[pick_index("Alvo", labels)].id}
    if ctype == "any_enemy_unit":
        all_units, labels = [], []
        for other in state.players:
            if other.id == pid or not other.city.is_alive():
                continue
            for u in other.units:
                all_units.append(u)
                labels.append(f"{u.id} de {other.name} ({u.life}/{u.life_max})")
        if not all_units:
            raise ActionError(f"{card_display(card_id)}: sem alvos.")
        return {"unit_id": all_units[pick_index("Alvo", labels)].id}
    if ctype == "people_hero":
        herois = HEROES_BY_PEOPLE.get(player.people, [])
        disponiveis = []
        for h in herois:
            hid = heroes.resolve_hero_for_people(player.people, h)
            if hid == player.chosen_hero_id:
                continue
            if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == hid
                   for u in player.units):
                continue
            disponiveis.append(h)
        if player.chosen_hero_id == "seven_dwarves":
            disponiveis = []
        if not disponiveis:
            raise ActionError("Todos os outros herois usados.")
        return {"hero_id": disponiveis[pick_index("Heroi", disponiveis)]}
    if ctype == "house":
        options = [h for h in CITY_HOUSES
                   if get_player(state, int(h.split("_")[1])).city.is_alive()]
        options.append(CENTER)
        labels = [house_display(state, h) for h in options]
        return {"house": options[pick_index("Casa", labels)]}
    return {}


def _resolve_pending_choice_if_any(state, pid: int) -> None:
    player = get_player(state, pid)
    pending = player.pending_artifact_choice
    if not pending:
        return
    if pending["kind"] == "J_D":
        console.print(f"[yellow]{player.name}: Jd Tabareu - escolha 2 de 3.[/yellow]")
        cards = list(pending["cards"])
        table = Table(box=box.SIMPLE)
        table.add_column("#", justify="right"); table.add_column("Carta")
        for i, c in enumerate(cards, 1):
            table.add_row(str(i), card_display(c))
        console.print(table)
        kept: list[str] = []
        while len(kept) < pending["pick"]:
            n = IntPrompt.ask(f"Escolha {len(kept)+1}a", default=1)
            if 1 <= n <= len(cards):
                c = cards[n - 1]
                if c not in kept:
                    kept.append(c)
        resolve_pending_artifact_choice(state, pid, kept_cards=kept)
        return
    if pending["kind"] == "BOIN":
        console.print(f"[yellow]{player.name}: Boin - escolha 1 de 2.[/yellow]")
        cards = list(pending["cards"])
        table = Table(box=box.SIMPLE)
        table.add_column("#", justify="right"); table.add_column("Carta")
        for i, c in enumerate(cards, 1):
            table.add_row(str(i), card_display(c))
        console.print(table)
        idx = IntPrompt.ask("Escolha", default=1)
        if not (1 <= idx <= len(cards)):
            idx = 1
        resolve_pending_artifact_choice(state, pid, kept_cards=[cards[idx - 1]])
        return
    if pending["kind"] == "Q_D":
        amount = pending["dead_unit_max_life"]
        console.print(f"[yellow]{player.name}: Qd - alvo morreu. Recompensa ({amount}):[/yellow]")
        idx = pick_index("Recurso", ["Ouro", "Magia"])
        resolve_pending_artifact_choice(state, pid, resource="gold" if idx == 0 else "magic")
        return


def _pick_target_for_day_attack(state, attacker, player):
    targets = []
    for other in state.players:
        if other.id == player.id or not other.city.is_alive():
            continue
        for u in other.units:
            if u.house == attacker.house and u.is_alive():
                targets.append(u)
    if not targets:
        raise ActionError("Sem alvos no local.")
    labels = [f"{u.id} de {get_player(state, u.owner_id).name} ({u.life}/{u.life_max})" for u in targets]
    return targets[pick_index("Alvo do ataque diurno", labels)]


def _handle_pena(state, pid: int, card_id: str) -> None:
    player = get_player(state, pid)
    console.print("[yellow]Voce recebeu uma Pena do Manto Sagrado.[/yellow]")
    if player.people == "humanos":
        use_or_give_pena(state, pid, card_id, give_to_iuna=False)
        return
    iuna_alive = any(
        isinstance(u, Hero) and u.is_alive() and u.hero_id == "iuna"
        for p in state.players for u in p.units
    )
    opts = ["Ficar com a Pena (vendavel por 7 Ouro)"]
    if iuna_alive:
        opts.append("Dar a Iuna e ganhar outro artefato")
    idx = pick_index("Pena:", opts)
    use_or_give_pena(state, pid, card_id, give_to_iuna=(idx == 1))


def handle_action(state, pid: int, choice: str) -> str | None:
    player = get_player(state, pid)
    if choice == "1":
        gold = IntPrompt.ask(f"Ouro (0 a {RESOURCES_PER_DAY})", default=RESOURCES_PER_DAY)
        if gold < 0 or gold > RESOURCES_PER_DAY:
            raise ActionError("Fora do intervalo.")
        collect_resources(state, pid, gold, RESOURCES_PER_DAY - gold)
        console.print("[green]Coleta ok.[/green]")
    elif choice == "2":
        raise_city_life(state, pid, IntPrompt.ask("Vezes", default=1))
        console.print("[green]Vida ok.[/green]")
    elif choice == "3":
        if peoples.has_7_dwarves_chosen(player):
            raise ActionError("Sem Tropas (7 Anoes).")
        archetypes = peoples.available_archetypes(player)
        labels = [f"{a.value} (max {TROOP_MAX_LIFE[a.value]})" for a in archetypes]
        archetype = archetypes[pick_index("Arquetipo", labels)]
        max_life = TROOP_MAX_LIFE[archetype.value]
        life = IntPrompt.ask(f"Vida (1 a {max_life})", default=max_life)
        summon_troop(state, pid, archetype, life)
        console.print("[green]Tropa ok.[/green]")
    elif choice == "4":
        summon_hero(state, pid)
        console.print("[green]Heroi ok.[/green]")
    elif choice == "5":
        units = [u for u in player.units if u.moves_this_turn < u.max_moves_this_turn]
        if not units:
            raise ActionError("Sem unidades.")
        idx = pick_index("Unidade", [f"{u.id} ({house_display(state, u.house)}, {u.life})" for u in units])
        unit = units[idx]
        dests = valid_destinations(state, unit)
        if not dests:
            raise ActionError("Sem destinos.")
        idx2 = pick_index("Destino", [house_display(state, d) for d in dests])
        move_unit(state, pid, unit.id, dests[idx2])
        console.print("[green]Movimento ok.[/green]")
    elif choice == "6":
        build_monument(state, pid)
        console.print("[green]Monumento ok.[/green]")
    elif choice == "7":
        card = buy_artifact_with_gold(state, pid)
        if card is None:
            _resolve_pending_choice_if_any(state, pid)
            return None
        console.print(f"[green]Comprou: {card_display(card)}[/green]")
        if card == "PENA":
            _handle_pena(state, pid, card)
    elif choice == "8":
        card = transmute_artifact_with_magic(state, pid)
        if card is None:
            _resolve_pending_choice_if_any(state, pid)
            return None
        console.print(f"[green]Transmutou: {card_display(card)}[/green]")
        if card == "PENA":
            _handle_pena(state, pid, card)
    elif choice == "9":
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = [card_display(c) for c in player.hand]
        card = player.hand[pick_index("Vender", labels)]
        sell_artifact(state, pid, card)
        console.print(f"[green]Vendeu: {card_display(card)}[/green]")
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
        console.print(f"[green]Jogou: {card_display(card)}[/green]")
    elif choice == "b":
        show_active_artifacts(state)
    elif choice == "r":
        show_resumo(state)
    elif choice == "m":
        show_map(state)
    elif choice == "l":
        show_loja(state)
    elif choice == "k":
        show_habilidades(state, pid)
    elif choice == "d":
        miyamoto = next((u for u in player.units
                         if isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto"), None)
        if miyamoto is None:
            raise ActionError("Miyamoto nao esta vivo.")
        atks_restantes = peoples.miyamoto_attacks_remaining(state, player)
        if atks_restantes <= 0:
            raise ActionError("Miyamoto ja atacou o maximo.")
        target = _pick_target_for_day_attack(state, miyamoto, player)
        resolve_attack_day(state, Attack(miyamoto.id, "unit", target.id))
        console.print("[green]Ataque diurno executado.[/green]")
    elif choice == "e":
        arken_espolia(state, pid)
        console.print("[green]Arken espoliou.[/green]")
    elif choice == "t":
        tintin_ficar_invisivel(state, pid)
        console.print("[green]Tin Tin invisivel ate o fim do turno.[/green]")
    elif choice == "f":
        sp = spells_mod.spell_for_people(player.people)
        if sp is None:
            raise ActionError("Sem feitico.")
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            raise ActionError("Valendar substitui Sonho Lucido.")
        choice_data: dict = {}
        if sp.spell_id == "resistencia":
            if not player.units:
                raise ActionError("Sem unidades.")
            labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
            choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
        elif sp.spell_id == "armadura_de_ouro":
            choice_data["cap"] = _ask_int("Cap por hit", default=2, min_val=1, max_val=10)
        cast_spell(state, pid, choice_data)
        console.print(f"[green]{sp.name} lancado.[/green]")
    elif choice == "h":
        if not player.units:
            raise ActionError("Sem unidades.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        idx = pick_index("Alvo", labels)
        use_heal(state, pid, player.units[idx].id)
        console.print("[green]Cura ok.[/green]")
    elif choice == "u":
        return "undo"
    elif choice == "w":
        return "mola"
    elif choice == "x":
        return "restart"
    return None


def run_player_day(state, pid: int) -> str | None:
    player = get_player(state, pid)
    try:
        _resolve_pending_choice_if_any(state, pid)
    except (ActionError, ValueError) as e:
        console.print(f"[red]Erro pendente: {e}[/red]")
    while True:
        show_state_for_player(state, pid)
        choice = menu_player_actions(state, player)
        if choice == "0":
            player.has_played_day_this_turn = True
            return None
        try:
            result = handle_action(state, pid, choice)
            if result is not None:
                return result
        except (ActionError, CombatError, ValueError) as e:
            console.print(f"[red]Erro: {e}[/red]")
        console.print()


def find_targets(state, unit):
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


def prompt_attack(state, unit, targets) -> Attack | None:
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_display(state, unit.house)}")
    options = ["Nao atacar"] + [t[2] for t in targets]
    idx = pick_index("Acao", options)
    if idx == 0:
        return None
    return Attack(unit.id, targets[idx - 1][0], targets[idx - 1][1])


def _try_ainai_teleport(state, player) -> bool:
    ainai = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "ainai"), None)
    if ainai is None:
        return False
    if ainai.statuses.get("ainai_used_this_night") == state.turn:
        return False
    if not state.deaths_this_night:
        return False
    casas = [h for h in state.deaths_this_night if h != ainai.house]
    if not casas:
        return False
    console.print("[yellow]Ainai pode teleportar para casa com morte nesta Noite.[/yellow]")
    labels = [house_display(state, h) for h in casas]
    idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)
    if idx == 0:
        return False
    destino = casas[idx - 1]
    ainai.house = destino
    ainai.statuses["ainai_used_this_night"] = state.turn
    player.city.magic += 1
    console.print(f"[green]Ainai teleportou para {house_display(state, destino)} (+1 Magia).[/green]")
    return True


def _try_besouro_mandinga(state, player) -> bool:
    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"), None)
    if besouro is None:
        return False
    if player.besouro_mandinga_used_turn == state.turn:
        return False
    if not player.hand:
        return False
    console.print(f"[yellow]{player.name}: Besouro pode usar Mandinga.[/yellow]")
    opts = ["Nao usar"] + [card_display(c) for c in player.hand]
    idx = pick_index("Mandinga:", opts)
    if idx == 0:
        return False
    card = player.hand[idx - 1]
    if card == "PENA":
        console.print("[red]Pena nao pode ser usada via Mandinga.[/red]")
        return False
    choice_data = _ask_choice_for_artifact(state, player.id, card)
    besouro_mandinga(state, player.id, card, choice=choice_data)
    console.print(f"[green]Mandinga: {card_display(card)} jogado.[/green]")
    return True


def _ask_vovo_position(state) -> None:
    for p in state.players:
        vovo = next((u for u in p.units
                     if isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba"), None)
        if vovo is None:
            continue
        console.print(f"[yellow]{p.name}: Vovo - posicao no local ({house_display(state, vovo.house)}).[/yellow]")
        pos = _ask_int("Posicao (1=primeiro, 4=ultimo)", default=1, min_val=1, max_val=4)
        p.vovo_position = pos


def _order_players_for_house(state, pids_here: list[int], house: str) -> list[int]:
    for pid in pids_here:
        p = get_player(state, pid)
        if p.bater_primeiro_turn == state.turn:
            others = [x for x in pids_here if x != pid]
            return [pid] + others
    vovo_owner = None
    for pid in pids_here:
        p = get_player(state, pid)
        for u in p.units:
            if (isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "vovo_gamba" and u.house == house):
                vovo_owner = pid
                break
        if vovo_owner is not None:
            break
    if vovo_owner is None:
        return pids_here
    pos = max(1, min(get_player(state, vovo_owner).vovo_position, len(pids_here)))
    ordered = [pid for pid in pids_here if pid != vovo_owner]
    ordered.insert(pos - 1, vovo_owner)
    return ordered


def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_map(state)
    _ask_vovo_position(state)
    all_pids = list(day_order(state))
    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
            _try_ainai_teleport(state, player)
            _try_besouro_mandinga(state, player)
    house_order = [CENTER, "city_4", "city_3", "city_2", "city_1"]
    for house in house_order:
        pids_here = []
        for pid in all_pids:
            player = get_player(state, pid)
            if any(u.house == house and u.is_alive() for u in player.units):
                pids_here.append(pid)
        if not pids_here:
            continue
        pids_here = _order_players_for_house(state, pids_here, house)
        for pid in pids_here:
            player = get_player(state, pid)
            units_here = [u for u in player.units if u.house == house and u.is_alive()]
            if not units_here:
                continue
            if not any(find_targets(state, u) for u in units_here):
                continue
            console.print(f"[bold]{player.name} declara ataques em {house_display(state, house)}.[/bold]")
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
            console.print()


def show_victory(state) -> None:
    if state.winner_id:
        player = get_player(state, state.winner_id)
        console.print()
        console.print(Panel.fit(
            f"[bold green]VITORIA![/bold green]\n\n{player.name} ({player.people}) venceu!",
            border_style="green"))
    else:
        console.print(Panel.fit("[bold red]Empate![/bold red]", border_style="red"))


def _run_one_game() -> None:
    console.clear()
    state = setup_ui()
    while not state.game_over:
        interest = start_turn(state)
        console.rule(f"[bold yellow]TURNO {state.turn} - DIA[/bold yellow]")
        curuna = get_player(state, state.curuna_id)
        console.print(f"[bold yellow]* Curuna: {curuna.name}[/bold yellow]\n")
        if interest:
            pros = ", ".join(f"{get_player(state, pid).name} (+{g})" for pid, g in interest)
            console.print(f"[yellow]Prosperidade:[/yellow] {pros}\n")
        skipped = [p.name for p in state.players
                   if p.city.is_alive() and p.skip_day_turn == state.turn]
        if skipped:
            console.print(f"[yellow]Pulados: {', '.join(skipped)}[/yellow]\n")
        show_map(state)
        console.print()
        day_players = day_order(state)
        snapshots: dict[int, dict] = {}
        i = 0
        while i < len(day_players):
            pid = day_players[i]
            player = get_player(state, pid)
            snapshots[pid] = state_to_dict(state)
            console.rule(f"[bold]Vez de {player.name}[/bold]")
            before = len(state.event_log)
            start_player_day(state, pid)
            for line in state.event_log[before:]:
                console.print(f"  [cyan]{line}[/cyan]")
            if player.skip_day_turn == state.turn:
                player.has_played_day_this_turn = True
                console.print(f"[yellow]{player.name} pulou.[/yellow]")
                i += 1
                continue
            result = run_player_day(state, pid)
            if result == "restart":
                raise RestartGame()
            if result == "undo":
                state = state_from_dict(snapshots[pid])
                console.print("[yellow]Colher de cha: refaz.[/yellow]")
                continue
            if result == "mola":
                if i > 0:
                    i -= 1
                prev = day_players[i]
                state = state_from_dict(snapshots[prev])
                console.print(f"[yellow]Mola: {get_player(state, prev).name} refaz.[/yellow]")
                continue
            i += 1
        end_day(state)
        night_skipped = [p.name for p in state.players
                         if p.city.is_alive() and p.skip_night_turn == state.turn]
        if night_skipped:
            console.print(f"[yellow]Pulados na Noite: {', '.join(night_skipped)}[/yellow]\n")
        run_night_phase(state)
        if state.game_over:
            break
        end_turn(state)
        if not state.game_over:
            console.input("\n[dim]Enter...[/dim] ")
            console.clear()
    show_victory(state)


def main() -> None:
    while True:
        try:
            _run_one_game()
        except RestartGame:
            console.print("[yellow]Reiniciando...[/yellow]\n")
            continue
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrompido.[/yellow]")
            return
        try:
            again = Prompt.ask("Jogar outra?", choices=["s", "n"], default="n")
        except KeyboardInterrupt:
            return
        if again != "s":
            return
        console.print()


if __name__ == "__main__":
    main()
