"""Jessica - Prototipo v0.4."""
from __future__ import annotations
import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box

from .core.setup import run_setup, roll_d20_order, horario_from
from .core.state import make_rng, get_player
from .core.actions import (
    collect_resources, raise_city_life, summon_troop, summon_hero,
    move_unit, build_monument, buy_artifact_with_gold,
    transmute_artifact_with_magic, sell_artifact, play_artifact,
    resolve_pending_artifact_choice, use_heal, cast_spell, arken_espolia,
    besouro_mandinga, use_or_give_pena, tintin_ficar_invisivel,
    dandara_invisibilidade, luide_vampa_mover, ActionError,
    transformar_em_centauro, aiquara_mover, aiquara_atacar,
    baoba_pagar_magia, bimbo_invisibilidade, bimbo_gastar_5,
    zebum_invocar_heroi, zebum_reinvocar, zebum_invocar_proximo_anao,
    gnomo_alocar_aposta,
)
from .core.combat import (
    resolve_attack, resolve_attack_day, Attack, CombatError,
    _effective_max_attacks, _attacks_used,
)
from .core import combat as _combat_mod
from .core.turn import start_turn, start_player_day, day_order, end_day, end_turn
from .core.constants import (
    CITY_HOUSES, CENTER, TroopArchetype, Phase, DEFAULT_SEED,
    TROOP_MAX_LIFE, RESOURCES_PER_DAY, CITY_LIFE_COST_GOLD,
    MONUMENT_COST_GOLD,
    ARTIFACT_GOLD_COST, ARTIFACT_MAGIC_COST, ARTIFACT_SELL_GOLD,
    DEFAULT_CITY_LIFE_START, DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC,
)
from .core.models import Hero, Troop
from .core.artifacts import card_display, get_definition, ARTIFACT_CATALOG
from .core.serialize import state_to_dict, state_from_dict
from .core import artifacts_effects, peoples, heroes, spells as spells_mod


console = Console()

PEOPLES = ["humanos", "anoes", "orcs", "fadas",
           "vampiros", "lobisomens", "gigantes", "mortos_vivos",
           "filhos_floresta", "gnomos_duendes"]

HEROES_BY_PEOPLE = {
    "humanos": ["Miyamoto Musashi", "Besouro Mangangá", "Iúna"],
    "anoes": ["Barbadourada", "Ori", "Os 7 Anões"],
    "orcs": ["Ga'Roche", "Arken", "Vovó Gamba"],
    "fadas": ["Ainai", "Valendar", "Luna"],
    "vampiros": ["Dracula", "Dandara", "Luide Vampa"],
    "lobisomens": ["Lupã", "Cigana", "Luarado"],
    "gigantes": ["João Grandão", "Pé Descalço", "Caroço"],
    "mortos_vivos": [],
    "filhos_floresta": ["Guarari", "Aiquara", "Baoba-bá"],
    "gnomos_duendes": ["Bimbo do Mal", "São Tomé", "Zebum"],
}

PASSIVA_DESC = {
    "humanos": "Roca de Quilombo: rola 1D4 (+1 por Pena ativa) toda manha.",
    "anoes": "Mineiro Carreiro: +1 Ouro por unidade ana viva, toda manha.",
    "orcs": "Berco de Guerreiros: -1 Magia em invocacoes. Arquetipo extra.",
    "fadas": "Asas Encantadas: +1 Magia ao mover. Herois ganham artefato ao matar Heroi.",
    "vampiros": "Sede de Sangue: mata -> cura 2. Empata -> sobrevive com 2. Nao vale contra Cidades.",
    "lobisomens": "Maldicao da Lua: em Lua Cheia, dobro de dano. Unidades mortas ficam infectadas.",
    "gigantes": "Estatura Colossal: herois custam 4 Magia. Turnos x4 dobram vida de Joao e Pe.",
    "mortos_vivos": "Heróis custam 2 Magia, sem escolha no setup. Os 3 disponiveis na partida.",
    "filhos_floresta": "Florescimento Exuberante: Cidade comeca com 1 vida; no turno 13 recebe +2 Vida, +2 Ouro, +2 Magia.",
    "gnomos_duendes": "Continue Apostando: 4 apostas (H/C/D/S) alocadas em outros jogadores no inicio do turno.",
}

FEITICO_DESC = {
    "resistencia": "Resistencia: de Resistencia a um aliado ate o fim do turno.",
    "armadura_de_ouro": "Armadura de Ouro: cap X de ouro por hit.",
    "espoliar": "Espoliar: +2 Ouro por Cidade inimiga ocupada.",
    "sonho_lucido": "Sonho Lucido: troca naipe do proximo artefato.",
    "transformar_morcego": "Transformar em Morcego: 1 aliado anda 2x (ou 1x se recem-invocado).",
    "licantropo": "Licantropo: 1 unidade sua vira Lobisomem ate fim do turno.",
    "linhagem_ancestral": "Linhagem Ancestral: ativa o feitico de 1 heroi Gigante vivo.",
    "levantar_mortos": "Levantar os Mortos: escolha 2 tropas e invoque com 1 de vida.",
    "decompor": "Decompor: sacrifica um elemento seu por Magia (Heroi +4 / Tropa vida+2 / Muralha -1vida +3).",
    "imitacao_gnomerica": "Imitacao Gnomerica: copia o feitico sorteado do dia.",
}

HERO_ABILITY_DESC = {
    "miyamoto": "Invencivel sob o Sol: ataca de Dia. +vida max ao matar. 2 ataques se for o mais forte.",
    "besouro": "o Maioral: dobro + resistencia vs >=. Mandinga: artefato na Noite.",
    "iuna": "Aguia Negra: 1 de dano fixo recebido. 1D4 ao atacar. Adiciona 4 Penas.",
    "barbadourada": "Filho das Cachoeiras: +1 Magia por artefato na mao.",
    "ori": "Velho Mestre Ferreiro: ele + aliados na casa ganham Resistencia.",
    "seven_dwarves": "Os 7 Anoes: 7 herois em corrente. Sem Tropas.",
    "dain": "Alergico: atacante morre no fim da Noite.",
    "buin": "Dengoso: nao pode ser atacado por Herois.",
    "bein": "Soneca: quem for atacado dorme ate os Anoes serem Curuna.",
    "boin": "Feliz: ve 2, escolhe 1 ao comprar/transmutar.",
    "tintin": "Bobao: fica Invisivel (recarga 1 turno).",
    "don": "Zangado: 1 ataque extra por Anao proximo.",
    "din": "Mestre: Anoes proximos atacam Cidades.",
    "garoche": "Rei do Sertao: executa sem aliados proximos. +1 vida por execucao.",
    "arken": "Cacador: Espoliar todo Dia.",
    "vovo_gamba": "Protetora: tropas na casa dela +1 dano. Escolhe posicao no local.",
    "ainai": "Fada da Vinganca: teleporta para onde Fada/Elfo morreu. +1 Magia.",
    "valendar": "Rainha Maga: substitui Sonho Lucido por bonus de naipe.",
    "luna": "Sonhadora: Sonho Lucido multi. Retorna ao local de origem.",
    "dracula": "Dracula: mata -> empala. Mata -> feitico sai da recarga.",
    "dandara": "Dandara: torna ela + aliados da casa invisiveis.",
    "luide_vampa": "Luide Vampa: ativa movimento noturno para aliados.",
    "lupa_lider": "Lupa Lider: em Lua Cheia, +Resistencia a todos os Lobisomens.",
    "cigana": "Cigana: em Lua Cheia, ataca Cidades e torna todos invisiveis.",
    "luarado": "Luarado: em Lua Cheia/transformado, anda 2x e infecta por dano.",
    "joao_grandao": "Joao Grandao: Presenca Magnetica forca ataques inimigos.",
    "pe_descalco": "Pe Descalco: +1 ataque sempre. Grito de Guerra: aliados x2 dano.",
    "caroco": "Caroco: gratis no turno 1. Multiplos Carocos gerados. Cabaca Cheia.",
    "cobra": "Cobra: herois mortos retornam como Espectros por 1 turno.",
    "zoia": "Zoia: 2 tropas extras (Ghoul e Esqueleto com 1 vida).",
    "cova_rasa": "Cova Rasa: amaldicoa inimigos proximos no inicio da Noite.",
    "guarari": "Centauro: 2 Magia transforma tropa da casa em Centauro ate fim da Noite.",
    "aiquara": "Ninfa: controla inimigo da casa (mover no Dia, atacar na Noite).",
    "baoba_ba": "Anciao: 1 Magia x 3 turnos para invocar. Tropas aliadas na casa dele.",
    "bimbo_do_mal": "Gastar aposta: invisivel (1) ou artefato da Loja (5).",
    "sao_tome": "Passivas dos alvos das apostas. 2 determinacoes por dia.",
    "zebum": "Mistico: apostas corretas compram herois estrangeiros.",
}


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


TUTORIAL_TXT = """\
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


class RestartGame(Exception):
    pass


def show_hud(state) -> None:
    curuna = get_player(state, state.curuna_id)
    console.print(
        f"[bold yellow]T{state.turn} · {state.phase.value.upper()} · "
        f"Curuna: {curuna.name} ({curuna.people})[/bold yellow]   "
        f"[dim][m]apa  [B]oard  [l]og[/dim]"
    )
    for p in state.players:
        if not p.city.is_alive():
            console.print(f"[red]{p.name} ({p.people}) - ELIMINADO[/red]")
            continue
        hero_str = "-"
        for u in p.units:
            if isinstance(u, Hero) and u.is_alive():
                hero_str = f"{heroes.hero_name(u.hero_id)} {u.life}/{u.life_max}"
                break
        name_pad = p.name.ljust(10)
        povo_pad = f"({p.people})".ljust(20)
        console.print(
            f"{name_pad} {povo_pad} "
            f"vida {p.city.life}/{p.city.life_max}  "
            f"ouro {p.city.gold}  magia {p.city.magic}  "
            f"mao {len(p.hand)}  heroi {hero_str}"
        )
    console.print()


def show_board(state) -> None:
    show_map(state)
    console.print()
    console.print("[bold]UNIDADES VIVAS POR CASA[/bold]")
    houses = [CENTER] + [f"city_{p.id}" for p in state.players]
    for house in houses:
        lines = []
        for p in state.players:
            for u in p.units:
                if u.house != house or not u.is_alive():
                    continue
                if isinstance(u, Hero):
                    kind = heroes.hero_name(u.hero_id)
                else:
                    kind = f"Tropa {u.archetype.value}"
                flags = []
                if u.double_damage:
                    flags.append("2xdano")
                if u.resistance_stacks:
                    flags.append(f"resx{u.resistance_stacks}")
                if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
                    flags.append("invis")
                if u.statuses.get("sono_until_turn", -1) > state.turn:
                    flags.append("dormindo")
                if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
                    flags.append("amaldicoado")
                if u.statuses.get("k_s_active"):
                    flags.append("Ks")
                if u.statuses.get("morcego_until_turn", -1) >= state.turn:
                    flags.append("morcego")
                if u.statuses.get("lobisomem_until_turn", -1) >= state.turn:
                    flags.append("lobisomem")
                flags_str = f" [{', '.join(flags)}]" if flags else ""
                lines.append(f"    {p.name[:6]} · {u.id} ({kind}) {u.life}/{u.life_max}{flags_str}")
        label = house_short(state, house)
        if lines:
            console.print(f"  [bold]{label}:[/bold]")
            for ln in lines:
                console.print(ln)
        else:
            console.print(f"  [dim]{label}: (vazio)[/dim]")


def show_turn_log(state) -> None:
    entries = [e for e in state.action_log if e["turn"] == state.turn]
    buckets: dict[str, list[str]] = {
        "MOV": [], "SUM": [], "ART": [], "FEIT": [], "COMB": [], "MORTE": [],
    }
    for e in entries:
        a = e["action"]
        params = e.get("params", {})
        try:
            pname = get_player(state, e["player_id"]).name
        except Exception:
            pname = f"J{e['player_id']}"
        if a == "move_unit":
            buckets["MOV"].append(
                f"{pname}: {params.get('unit_id')} "
                f"{params.get('origin')} -> {params.get('destination')}"
            )
        elif a == "summon_troop":
            buckets["SUM"].append(
                f"{pname}: tropa {params.get('archetype')} "
                f"({params.get('life')} vida)"
            )
        elif a == "summon_hero":
            buckets["SUM"].append(f"{pname}: heroi {params.get('hero_id')}")
        elif a == "play_artifact":
            buckets["ART"].append(f"{pname}: jogou {params.get('card')}")
        elif a == "buy_artifact_gold":
            buckets["ART"].append(f"{pname}: comprou {params.get('card')} (ouro)")
        elif a == "transmute_artifact_magic":
            buckets["ART"].append(f"{pname}: transmutou {params.get('card')}")
        elif a == "sell_artifact":
            buckets["ART"].append(f"{pname}: vendeu {params.get('card')}")
        elif a == "cast_spell":
            buckets["FEIT"].append(f"{pname}: {params.get('spell')}")
        elif a == "attack":
            buckets["COMB"].append(
                f"{pname}: atacou {params.get('target_id')} "
                f"(dano {params.get('damage')}, ret {params.get('retaliation')})"
            )
        elif a == "attack_city":
            buckets["COMB"].append(
                f"{pname}: atacou cidade J{params.get('target_player_id')} "
                f"(dano {params.get('damage')})"
            )
        elif a == "unit_died":
            buckets["MORTE"].append(
                f"{pname}: {params.get('unit_id')} morreu em {params.get('house')}"
            )
    console.print(f"[bold]TURNO {state.turn} - o que aconteceu ate agora[/bold]")
    found = False
    for label, items in buckets.items():
        if not items:
            continue
        found = True
        for item in items:
            console.print(f"[dim][{label}][/dim] {item}")
    if not found:
        console.print("[dim](nada ainda)[/dim]")
    console.print()


def show_passivas_ativas(state) -> None:
    console.print("[bold]STATUSES / PASSIVAS ATIVAS[/bold]")
    found = False
    for p in state.players:
        if p.double_damage_until_end_night:
            console.print(f"  {p.name}: dobro de dano (Qs)")
            found = True
        if p.invulnerable_until_end_turn:
            console.print(f"  {p.name}: invulneravel (Qh)")
            found = True
        if p.armor_active_until_turn >= state.turn:
            console.print(f"  {p.name}: Armadura de Ouro ativa")
            found = True
        for u in p.units:
            if u.statuses.get("k_s_active"):
                console.print(f"  {p.name} {u.id}: Ks (dobro de ataques)")
                found = True
    if not found:
        console.print("  [dim](nenhum)[/dim]")
    console.print()


def _menu_informacoes(state, pid: int) -> None:
    opts = [
        "Loja",
        "Inspecionar local / unidade",
        "Artefatos em campo (todos)",
        "Passivas ativas",
        "Unidades empaladas / infectadas",
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
        show_habilidades(state, pid)


def show_empalados_infectados(state) -> None:
    console.print("[bold]Empalados (nao podem ser reinvocados)[/bold]")
    found = False
    for p in state.players:
        if p.empalados:
            found = True
            for sig in p.empalados:
                console.print(f"  {p.name}: {sig['kind']} {sig['id']}")
    if not found:
        console.print("  [dim](nenhum)[/dim]")
    console.print()
    console.print("[bold]Infectados (viram Lobisomem em Lua Cheia)[/bold]")
    found = False
    for p in state.players:
        if p.infectados:
            found = True
            for sig in p.infectados:
                console.print(f"  {p.name}: {sig['kind']} {sig['id']}")
    if not found:
        console.print("  [dim](nenhum)[/dim]")
    console.print()


def _menu_especiais(state, pid: int) -> str | None:
    player = get_player(state, pid)
    opts = []
    keys = []
    if player.people == "gnomos_duendes" and player.bets_need_realocacao:
        opts.append("Alocar apostas do turno")
        keys.append("A")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto" for u in player.units):
        opts.append("Miyamoto: atacar de Dia")
        keys.append("d")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "arken" for u in player.units) \
            and player.arken_espolia_used_turn != state.turn:
        opts.append("Arken: Espoliar")
        keys.append("e")
    tintin = next((u for u in player.units
                   if isinstance(u, Hero) and u.is_alive() and u.hero_id == "tintin"), None)
    if tintin is not None and tintin.statuses.get("tintin_cooldown_until_turn", -1) <= state.turn:
        opts.append("Tin Tin: ficar invisivel")
        keys.append("t")
    dandara = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "dandara"), None)
    if dandara is not None and dandara.statuses.get("dandara_cooldown_until_turn", -1) <= state.turn:
        opts.append("Dandara: invisibilidade de grupo")
        keys.append("y")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa" for u in player.units) \
            and not player.has_cast_spell_this_turn:
        opts.append("Luide Vampa: movimento noturno")
        keys.append("z")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "guarari" for u in player.units):
        opts.append("Guarari: transformar tropa em Centauro (2 Magia)")
        keys.append("q")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "aiquara" for u in player.units):
        opts.append("Aiquara: controlar inimigo")
        keys.append("i")
    if (player.people == "filhos_floresta"
            and not any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "baoba_ba"
                        for u in player.units)):
        opts.append(f"Baoba-ba: pagar Magia ({player.baoba_pagamentos}/3)")
        keys.append("b")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "bimbo_do_mal" for u in player.units):
        opts.append(f"Bimbo ({player.correct_bets} apostas corretas)")
        keys.append("p")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zebum" for u in player.units):
        opts.append("Zebum: invocar/reinvocar heroi")
        keys.append("g")
    if player.pending_heals > 0:
        opts.append(f"Usar cura pendente ({player.pending_heals})")
        keys.append("h")
    if not opts:
        console.print("[dim]Sem acoes especiais disponiveis.[/dim]")
        return None
    opts.append("Voltar")
    idx = pick_index("Especiais", opts)
    if idx == len(opts) - 1:
        return None
    return _do_action(state, pid, keys[idx])


def _menu_sistema(state, pid: int) -> str | None:
    opts = [
        "Colher de cha (refazer meu turno)",
        "Mola (voltar ao jogador anterior)",
        "Recomecar jogo",
        "Voltar",
    ]
    idx = pick_index("Menu", opts)
    if idx == 0:
        return "undo"
    if idx == 1:
        return "mola"
    if idx == 2:
        return "restart"
    return None




def _armor_choice_prompt(player, dmg):
    cap = min(dmg, player.city.gold)
    console.print(f"[yellow]{player.name}: Armadura de Ouro ativa. "
                  f"Dano {dmg}, Ouro {player.city.gold}, cap {cap}.[/yellow]")
    v = IntPrompt.ask(f"Quanto Ouro pagar (0 a {cap})", default=cap)
    v = max(0, min(v, cap))
    return v


def house_display(state, house: str) -> str:
    if house == CENTER:
        return "Centro"
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        return f"Cidade {get_player(state, pid).name}"
    return house


def house_short(state, house: str) -> str:
    if house == CENTER:
        return "Centro"
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        p = get_player(state, pid)
        return f"Cidade J{pid} - {p.name} ({p.people})"
    return house


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
        console.print(f"\n[bold]{desc}[/bold]")
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
        "[bold]Atalhos de teclado[/bold]\n\n"
        "[cyan]1-6[/cyan]     Acoes do turno (coletar, subir vida, invocar, mover, monumento)\n"
        "[cyan]7,8,9[/cyan]   Comprar (Ouro), Transmutar (Magia), Vender\n"
        "[cyan]a[/cyan]       Jogar artefato da mao\n"
        "[cyan]f[/cyan]       Lancar feitico\n"
        "[cyan]E[/cyan]       Analisar campo de batalha (submenu)\n"
        "[cyan]B[/cyan]       Panorama (Board) - tudo de todos\n"
        "[cyan]m[/cyan]       Mapa\n"
        "[cyan]l[/cyan]       Log do turno\n"
        "[cyan]R[/cyan]       Relatorios (producao, combate, artefatos)\n"
        "[cyan]?[/cyan]       Ajuda (esta tela)\n"
        "[cyan]M[/cyan]       Menu (colher de cha, mola, recomecar)\n"
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


def _get_actions(state, player) -> list[tuple[str, str, str]]:
    sp = spells_mod.spell_for_people(player.people)

    r = []
    r.append(("Turno", "1", "Acoes (coletar, invocar, mover, monumento)"))
    r.append(("Turno", "2", "Artefatos (comprar, transmutar, vender, jogar)"))
    r.append(("Turno", "3", f"Lancar feitico: {sp.name}" if sp else "Lancar feitico"))
    r.append(("Turno", "4", "Especiais (herois, habilidades)"))


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

    dandara = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "dandara"), None)
    if dandara is not None:
        cd = dandara.statuses.get("dandara_cooldown_until_turn", -1)
        if cd <= state.turn:
            r.append(("Especiais", "y", "Dandara: invisibilidade do grupo"))

    luide = next((u for u in player.units
                  if isinstance(u, Hero) and u.is_alive() and u.hero_id == "luide_vampa"), None)
    if luide is not None and not player.has_cast_spell_this_turn:
        r.append(("Especiais", "z", "Luide Vampa: ativar movimento noturno"))

    if player.people == "gnomos_duendes" and player.bets_need_realocacao:
        r.append(("Gnomos", "A", "Alocar apostas do turno"))

    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "guarari"
           for u in player.units):
        r.append(("Especiais", "q", "Guarari: tropa -> Centauro (2 Magia)"))
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "aiquara"
           for u in player.units):
        r.append(("Especiais", "i", "Aiquara: controlar inimigo"))
    if (player.people == "filhos_floresta"
            and not any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "baoba_ba"
                        for u in player.units)):
        r.append(("Especiais", "b", f"Baoba-ba: pagar Magia ({player.baoba_pagamentos}/3)"))
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "bimbo_do_mal"
           for u in player.units):
        r.append(("Especiais", "p", f"Bimbo ({player.correct_bets} apostas corretas)"))
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "zebum"
           for u in player.units):
        r.append(("Especiais", "g", "Zebum: invocar/reinvocar heroi"))

    besouro = next((u for u in player.units
                    if isinstance(u, Hero) and u.is_alive() and u.hero_id == "besouro"), None)
    if besouro is not None and player.besouro_mandinga_used_turn != state.turn and player.hand:
        # Mandinga e na Noite, mas por simplicidade deixamos como opcao no Dia tambem.
        pass

    if player.pending_heals > 0:
        r.append(("Especiais", "h", f"Usar cura pendente ({player.pending_heals})"))

    r.append(("Info", "i", "Informacoes"))
    r.append(("Info", "m", "Mapa"))
    r.append(("Info", "p", "Panorama (Board)"))
    r.append(("Info", "l", "Log do turno"))
    r.append(("Info", "r", "Relatorios"))
    r.append(("Info", "?", "Ajuda"))
    r.append(("Info", "x", "Menu do sistema"))
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
        "[italic]Prototipo v0.4 - 8 povos[/italic]",
        border_style="cyan"))
    console.print()
    import random as _rnd
    default_seed = _rnd.randint(1, 999999999)
    seed = _ask_int(f"Seed (mesma seed = mesma partida) [{default_seed}]",
                    default=default_seed, min_val=1, max_val=999999999)
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
    povo_order = horario_from(order)
    table = Table(title="Ordem do D20 (anti-horario - ordem de JOGO)", box=box.SIMPLE)
    table.add_column("Posicao", justify="right")
    table.add_column("Jogador", justify="right")
    for i, pid in enumerate(order, 1):
        table.add_row(str(i), f"Jogador {pid}")
    console.print(table)
    table2 = Table(title="Ordem de ESCOLHA DE POVO (horario)", box=box.SIMPLE)
    table2.add_column("Posicao", justify="right")
    table2.add_column("Jogador", justify="right")
    for i, pid in enumerate(povo_order, 1):
        table2.add_row(str(i), f"Jogador {pid}")
    console.print(table2)
    console.print()
    console.print("[bold]Nomes dos jogadores[/bold]\n")
    names: dict[int, str] = {}
    for pid in range(1, 5):
        names[pid] = Prompt.ask(f"Nome do Jogador {pid}", default=f"Jogador {pid}")
    console.print()
    choices: dict[int, dict] = {}
    console.print("[bold]Escolha de povos (sentido horario)[/bold]\n")
    available_peoples = list(PEOPLES)
    for pid in povo_order:
        console.print(f"Vez de [bold]{names[pid]}[/bold] (Jogador {pid}).")
        idx = pick_index("Povo", available_peoples)
        chosen = available_peoples[idx]
        available_peoples.remove(chosen)
        choices[pid] = {"povo": chosen}
        console.print(f"[green]{names[pid]} escolheu: {chosen}[/green]\n")
    console.print("[bold]Escolha de herois[/bold]\n")
    for pid in povo_order:
        povo = choices[pid]["povo"]
        if povo == "mortos_vivos":
            console.print(f"[bold]{names[pid]}[/bold] (Mortos-Vivos): sem escolha de heroi.\n")
            choices[pid]["heroi"] = ""
            continue
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
    elif player.people == "mortos_vivos":
        hero_display = "(livre - escolhe na invocacao)"
    sp = spells_mod.spell_for_people(player.people)
    sp_str = ""
    if sp:
        cd = ""
        if state.turn < player.spell_cooldown_until_turn:
            cd = f" [recarga {player.spell_cooldown_until_turn - state.turn}]"
        sp_str = f" | Feitico: {sp.name}{cd}"

    console.print(f"[bold]{player.name}[/bold]{mark} - Povo: {player.people} - Heroi: {hero_display}{sp_str}")
    console.print(f"Cidade: vida {city.life}/{city.life_max} | Ouro: {city.gold} | Magia: {city.magic} | Mon: {'sim' if city.has_monument else 'nao'}")

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
            if u.original_owner_id is not None: flags.append("ctrl")
            if u.statuses.get("cannot_attack_on_turn") == state.turn: flags.append("sem ataque")
            if u.statuses.get("sono_until_turn", -1) > state.turn: flags.append("dormindo")
            if u.statuses.get("invisivel_until_turn", -1) >= state.turn: flags.append("invisivel")
            if u.statuses.get("lobisomem_until_turn", -1) >= state.turn: flags.append("lobisomem")
            if u.statuses.get("morcego_until_turn", -1) >= state.turn: flags.append("morcego")
            if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn: flags.append("amaldicoado")
            flags_str = ", ".join(flags) if flags else "-"
            table.add_row(u.id, kind, house_short(state, u.house),
                          f"{u.life}/{u.life_max}", flags_str)
        console.print(table)
    else:
        console.print("[dim]Sem unidades.[/dim]")

    # H2: mao + artefatos em campo
    if player.hand:
        mao = ", ".join(card_display(c) for c in player.hand)
        console.print(f"[bold]Mao ({len(player.hand)}):[/bold] {mao}")
    if player.field_artifacts:
        campo = ", ".join(card_display(a.card_id) for a in player.field_artifacts)
        console.print(f"[bold]Artefatos ativos:[/bold] {campo}")
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
    vida = f"Cidade {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"
    lines = [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width), _pad(vida, width)]
    units = []
    for u in player.units:
        if u.house == f"city_{pid}":
            kind = "H" if isinstance(u, Hero) else "T"
            units.append(f"{kind}{u.life}")
    if units:
        for u in units:
            lines.append(_pad(u, width))
    else:
        lines.append(_pad("[dim]-[/dim]", width))
    return lines


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
    table.add_column("Jogador")
    table.add_column("Povo")
    table.add_column("Heroi")
    table.add_column("Vida", justify="right")
    table.add_column("Ouro", justify="right")
    table.add_column("Magia", justify="right")
    table.add_column("Mao", justify="right")
    table.add_column("Mon.", justify="center")
    for p in state.players:
        mark = " *" if state.curuna_id == p.id else ""
        alive = p.city.is_alive()
        heroi = "-"
        if p.people == "mortos_vivos":
            vivos = [u for u in p.units if isinstance(u, Hero) and u.is_alive()]
            if vivos:
                heroi = ", ".join(heroes.hero_name(u.hero_id) for u in vivos)
            else:
                heroi = "(livre)"
        elif p.chosen_hero_id:
            try:
                heroi = heroes.hero_name(p.chosen_hero_id)
            except KeyError:
                heroi = p.chosen_hero_id
        table.add_row(
            f"{p.name}{mark}" if alive else f"[red]{p.name} (morto)[/red]",
            p.people or "-",
            heroi,
            f"{p.city.life}/{p.city.life_max}" if alive else "-",
            str(p.city.gold) if alive else "-",
            str(p.city.magic) if alive else "-",
            str(len(p.hand)),
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
            desc += " [Valendar ativa - bloqueado]"
        console.print(desc)
        if state.turn < player.spell_cooldown_until_turn:
            console.print(f"[yellow]Recarga: {player.spell_cooldown_until_turn - state.turn} turno(s)[/yellow]")
    console.print("\n[bold]Herois do jogador[/bold]")
    has_any = False
    for u in player.units:
        if isinstance(u, Hero) and u.is_alive():
            has_any = True
            hd = heroes.get_hero(u.hero_id)
            console.print(f"  [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_short(state, u.house)}")
            console.print(f"    {HERO_ABILITY_DESC.get(u.hero_id, hd.name)}")
    if not has_any:
        console.print("  [dim](nenhum)[/dim]")
    # Sao Tome: passivas virtuais dos alvos das apostas
    if player.people == "gnomos_duendes":
        sao_tome = next((u for u in player.units
                         if isinstance(u, Hero) and u.is_alive()
                         and u.hero_id == "sao_tome"), None)
        if sao_tome is not None:
            effective = peoples.sao_tome_effective_peoples(state, player)
            extras = sorted(p for p in effective if p != "gnomos_duendes")
            if extras:
                console.print("\n[bold]Passivas virtuais (Sao Tome):[/bold]")
                for povo in extras:
                    console.print(f"  [cyan]{povo}[/cyan]: {PASSIVA_DESC.get(povo, '-')}")

    console.print("\n[bold]Herois dos outros (em campo)[/bold]")
    has_other = False
    for other in state.players:
        if other.id == pid:
            continue
        for u in other.units:
            if isinstance(u, Hero) and u.is_alive():
                has_other = True
                hd = heroes.get_hero(u.hero_id)
                console.print(f"  {other.name}: [cyan]{hd.name}[/cyan] ({u.life}/{u.life_max}) em {house_short(state, u.house)}")
    if not has_other:
        console.print("  [dim](nenhum)[/dim]")


def _inspecionar_local(state, house: str) -> None:
    """Mostra tudo que esta no local."""
    console.print(Panel.fit(f"[bold]Local: {house_short(state, house)}[/bold]",
                            border_style="cyan"))
    # Cidade
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        p = get_player(state, pid)
        console.print(f"Cidade: vida {p.city.life}/{p.city.life_max}")
    # Unidades
    any_unit = False
    for p in state.players:
        for u in p.units:
            if u.house != house or not u.is_alive():
                continue
            any_unit = True
            if isinstance(u, Hero):
                tipo = f"Heroi {heroes.hero_name(u.hero_id)}"
            else:
                tipo = f"Tropa {u.archetype.value}"
            flags = []
            if u.double_damage: flags.append("2xdano")
            if u.resistance_stacks: flags.append(f"Resx{u.resistance_stacks}")
            if u.original_owner_id is not None: flags.append("ctrl")
            if u.statuses.get("sono_until_turn", -1) > state.turn: flags.append("dormindo")
            if u.statuses.get("invisivel_until_turn", -1) >= state.turn: flags.append("invisivel")
            if u.statuses.get("lobisomem_until_turn", -1) >= state.turn: flags.append("lobisomem")
            if u.statuses.get("morcego_until_turn", -1) >= state.turn: flags.append("morcego")
            if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn: flags.append("amaldicoado")
            flags_str = ", ".join(flags) if flags else "-"
            console.print(f"  {p.name} | {u.id} ({tipo}) | vida {u.life}/{u.life_max} | {flags_str}")
    if not any_unit:
        console.print("  [dim](vazio)[/dim]")


def estudar_campo(state) -> None:
    options = []
    labels = []
    for h in CITY_HOUSES:
        pid = int(h.split("_")[1])
        p = get_player(state, pid)
        labels.append(f"Cidade J{pid} - {p.name} ({p.people})")
        options.append(h)
    labels.append("Centro do mapa")
    options.append(CENTER)
    idx = pick_index("Local", labels)
    _inspecionar_local(state, options[idx])


def historico(state) -> None:
    log_lines = state.event_log
    if not log_lines:
        console.print("[dim]Nenhum evento registrado.[/dim]")
        return
    N = 20
    while True:
        chunk = log_lines[-N:] if len(log_lines) > N else log_lines
        table = Table(title=f"Historico (ultimas {len(chunk)} de {len(log_lines)})", box=box.SIMPLE)
        table.add_column("Linha")
        for line in chunk:
            table.add_row(line)
        console.print(table)
        if len(log_lines) <= N:
            break
        ans = Prompt.ask("Mostrar mais 20? (s/n)", choices=["s", "n"], default="n")
        if ans != "s":
            break
        N += 20


def menu_player_actions(state, player) -> str:
    actions = _get_actions(state, player)
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Secao", style="dim")
    table.add_column("Tecla", style="cyan", justify="center")
    table.add_column("Acao")
    current = None
    for section, key, label in actions:
        if section != current:
            table.add_section()
            current = section
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
                labels.append(f"{u.id} de {other.name} ({u.life}/{u.life_max}, {house_short(state, u.house)})")
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
        labels = [house_short(state, h) for h in options]
        return {"house": options[pick_index("Casa", labels)]}
    return {}


def _resolve_pending_choice_if_any(state, pid: int) -> None:
    player = get_player(state, pid)
    pending = player.pending_artifact_choice
    if not pending:
        return
    if pending["kind"] == "J_D":
        console.print(f"[yellow]{player.name}: Jd - escolha 2 de 3.[/yellow]")
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
    return targets[pick_index("Alvo", labels)]


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


def _escolher_heroi_mv() -> str:
    opts = ["Cobra, o Paje Caido (3 vida)",
            "Zoia Bulbo Negro (2 vida)",
            "Cova Rasa da Terra Funda (1 vida)"]
    idx = pick_index("Escolher heroi Mortos-Vivos", opts)
    return ["cobra", "zoia", "cova_rasa"][idx]


def _do_action(state, pid: int, choice: str) -> str | None:
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
        if player.people == "mortos_vivos":
            hid = _escolher_heroi_mv()
            summon_hero(state, pid, force_hero_id=hid)
        else:
            summon_hero(state, pid)
        console.print("[green]Heroi ok.[/green]")
    elif choice == "5":
        units = [u for u in player.units if not u.has_moved_this_turn and u.moves_this_turn < u.max_moves_this_turn]
        if not units:
            raise ActionError("Sem unidades.")
        idx = pick_index("Unidade", [f"{u.id} ({house_short(state, u.house)}, {u.life})" for u in units])
        unit = units[idx]
        dests = valid_destinations(state, unit)
        if not dests:
            raise ActionError("Sem destinos.")
        labels = ["Cancelar"] + [house_short(state, d) for d in dests]
        idx2 = pick_index("Destino", labels)
        if idx2 == 0:
            console.print("[yellow]Movimento cancelado.[/yellow]")
            return None
        move_unit(state, pid, unit.id, dests[idx2 - 1])
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
        console.print(f"[green]Jogou: {card_display(card)}[/green]")

    elif choice == "d":
        miyamoto = next((u for u in player.units
                         if isinstance(u, Hero) and u.is_alive() and u.hero_id == "miyamoto"), None)
        if miyamoto is None:
            raise ActionError("Miyamoto nao esta vivo.")
        atks = peoples.miyamoto_attacks_remaining(state, player)
        if atks <= 0:
            raise ActionError("Miyamoto ja atacou o maximo.")
        target = _pick_target_for_day_attack(state, miyamoto, player)
        resolve_attack_day(state, Attack(miyamoto.id, "unit", target.id))
        console.print("[green]Ataque diurno executado.[/green]")
    elif choice == "e":
        arken_espolia(state, pid)
        console.print("[green]Arken espoliou.[/green]")
    elif choice == "t":
        tintin_ficar_invisivel(state, pid)
        console.print("[green]Tin Tin invisivel.[/green]")
    elif choice == "y":
        dandara_invisibilidade(state, pid)
        console.print("[green]Dandara invisivel.[/green]")
    elif choice == "z":
        luide_vampa_mover(state, pid)
        console.print("[green]Luide Vampa: movimento noturno ativo.[/green]")
    elif choice == "A":
        _gnomo_bets_menu(state, player)
    elif choice == "q":
        guarari = next((u for u in player.units
                        if isinstance(u, Hero) and u.is_alive()
                        and u.hero_id == "guarari"), None)
        if guarari is None:
            raise ActionError("Guarari nao esta vivo.")
        tropas = [u for u in player.units
                  if isinstance(u, Troop) and u.is_alive()
                  and u.house == guarari.house]
        if not tropas:
            raise ActionError("Sem tropas na casa de Guarari.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in tropas]
        t = tropas[pick_index("Tropa", labels)]
        transformar_em_centauro(state, pid, t.id)
        console.print("[green]Centauro ativo ate o fim da Noite.[/green]")
    elif choice == "i":
        _aiquara_ui(state, pid)
    elif choice == "b":
        baoba_pagar_magia(state, pid)
        console.print(f"[green]Baoba-ba: {player.baoba_pagamentos}/3.[/green]")
    elif choice == "p":
        _bimbo_ui(state, pid)
    elif choice == "g":
        _zebum_ui(state, pid)
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
        elif sp.spell_id == "transformar_morcego":
            if not player.units:
                raise ActionError("Sem unidades.")
            labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
            choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
        elif sp.spell_id == "licantropo":
            if not player.units:
                raise ActionError("Sem unidades.")
            labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
            choice_data["unit_id"] = player.units[pick_index("Alvo", labels)].id
        elif sp.spell_id == "linhagem_ancestral":
            gigantes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()
                        and u.hero_id in ("joao_grandao", "pe_descalco", "caroco")]
            if not gigantes:
                raise ActionError("Sem herois Gigantes vivos.")
            labels = [heroes.hero_name(u.hero_id) for u in gigantes]
            choice_data["hero_id"] = gigantes[pick_index("Heroi", labels)].hero_id
        elif sp.spell_id == "levantar_mortos":
            labels = ["light", "medium", "heavy", "extra", "ghoul", "esqueleto"]
            i1 = pick_index("Arquetipo 1", labels)
            i2 = pick_index("Arquetipo 2", labels)
            choice_data["archetypes"] = [labels[i1], labels[i2]]
        elif sp.spell_id == "decompor":
            choice_data = _escolher_decompor(state, player)
        elif sp.spell_id == "imitacao_gnomerica":
            choice_data = _escolher_imitacao(state, player)
        cast_spell(state, pid, choice_data)
        console.print(f"[green]{sp.name} lancado.[/green]")
    elif choice == "h":
        if not player.units:
            raise ActionError("Sem unidades.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units]
        idx = pick_index("Alvo", labels)
        use_heal(state, pid, player.units[idx].id)
        console.print("[green]Cura ok.[/green]")
    return None


def handle_action(state, pid: int, choice: str) -> str | None:
    if choice == "1":
        return _menu_acoes_turno(state, pid)
    if choice == "2":
        return _menu_artefatos(state, pid)
    if choice == "3":
        return _do_action(state, pid, "f")
    if choice == "4":
        return _menu_especiais(state, pid)
    if choice == "i":
        _menu_informacoes(state, pid)
        return None
    if choice == "m":
        show_map(state)
        return None
    if choice == "p":
        show_board(state)
        return None
    if choice == "l":
        show_turn_log(state)
        return None
    if choice == "r":
        _menu_relatorios(state, pid)
        return None
    if choice == "?":
        _menu_ajuda(state, pid)
        return None
    if choice == "x":
        return _menu_sistema(state, pid)
    return _do_action(state, pid, choice)


def run_player_day(state, pid: int) -> str | None:
    player = get_player(state, pid)
    try:
        _resolve_pending_choice_if_any(state, pid)
    except (ActionError, ValueError) as e:
        console.print(f"[red]Erro pendente: {e}[/red]")
    if player.people == "gnomos_duendes" and player.bets_need_realocacao:
        _gnomo_bets_menu(state, player)
    while True:
        show_hud(state)
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


def prompt_attack(state, unit, targets) -> Attack | None:
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_short(state, unit.house)}")
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
    if ainai.statuses.get("ainai_used_turn") == state.turn:
        return False
    # Apenas fadas ALIADAS caidas neste turno (nao necessariamente nesta noite)
    casas_alvo = set()
    for oid, h in state.fae_fallen_this_turn:
        if oid != ainai.owner_id:
            continue
        if h == ainai.house:
            continue
        casas_alvo.add(h)
    if not casas_alvo:
        return False
    casas = sorted(casas_alvo)
    console.print("[yellow]Ainai pode teletransportar para casa com fada aliada caida neste turno.[/yellow]")
    labels = [house_short(state, h) for h in casas]
    idx = pick_index("Teleporte de Ainai?", ["Nao teleportar"] + labels)
    if idx == 0:
        return False
    destino = casas[idx - 1]
    ainai.house = destino
    ainai.statuses["ainai_used_turn"] = state.turn
    player.city.magic += 1
    console.print(f"[green]Ainai teleportou para {house_short(state, destino)} (+1 Magia).[/green]")
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


def _try_luna_return(state, player) -> None:
    luna = next((u for u in player.units
                 if isinstance(u, Hero) and u.is_alive() and u.hero_id == "luna"), None)
    if luna is None:
        return
    if "luna_origin_house" not in luna.statuses:
        console.print(f"[dim]{player.name}: Luna nao moveu este turno, nao pode teletransportar.[/dim]")
        return
    origin = luna.statuses["luna_origin_house"]
    console.print(f"[yellow]{player.name}: Luna andou neste turno. Teletransportar de volta para {house_short(state, origin)}?[/yellow]")
    opts = ["Sim", "Nao"]
    idx = pick_index("Luna:", opts)
    if idx == 0:
        luna.house = origin
        luna.statuses.pop("luna_origin_house", None)
        console.print(f"[green]Luna retornou para {house_short(state, origin)}.[/green]")


def _ask_vovo_position(state) -> None:
    for p in state.players:
        vovo = next((u for u in p.units
                     if isinstance(u, Hero) and u.is_alive() and u.hero_id == "vovo_gamba"), None)
        if vovo is None:
            continue
        console.print(f"[yellow]{p.name}: Vovo - posicao no local ({house_short(state, vovo.house)}).[/yellow]")
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


def _luide_janela_noturna(state, all_pids):
    """Oferece mover/usar feitico para vampiros com Luide vivo."""
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
                labels2 = ["Cancelar"] + [house_short(state, d) for d in dests]
                idx2 = pick_index("Destino", labels2)
                if idx2 == 0:
                    continue
                try:
                    move_unit(state, pid, u.id, dests[idx2 - 1])
                    console.print("[green]Movido.[/green]")
                except ActionError as e:
                    console.print(f"[red]{e}[/red]")
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


def _ainai_prompt_all(state, all_pids):
    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
            _try_ainai_teleport(state, player)


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

    # Ainai: ANTES
    _ainai_prompt_all(state, all_pids)
    # Luide: janela noturna antes
    _luide_janela_noturna(state, all_pids)

    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
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
            console.print()

        # Luide: janela entre casas (apos cada casa)
        _luide_janela_noturna(state, all_pids)
        # Ainai: nova chance a cada casa
        _ainai_prompt_all(state, all_pids)

    # Ainai: DEPOIS de tudo
    _ainai_prompt_all(state, all_pids)


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
    _combat_mod.set_armor_choice_fn(_armor_choice_prompt)
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
