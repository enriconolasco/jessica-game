"""Jessica - Prototipo v0.4."""
from __future__ import annotations
from .core.state import city_houses
import re

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box

from .core.setup import run_setup, roll_d20_order, horario_from
from .core.state import (
    make_rng, get_player, declaration_order_for_house, sync_house_priority, log,
)
from .core.actions import (
    raise_city_life, summon_troop, summon_hero,
    move_unit, build_monument, buy_artifact_with_gold,
    transmute_artifact_with_magic, sell_artifact, play_artifact,
    resolve_pending_artifact_choice, use_heal, cast_spell, arken_espolia,
    besouro_mandinga, use_or_give_pena, tintin_ficar_invisivel,
    dandara_invisibilidade, luide_vampa_mover, ActionError,
    transformar_em_centauro, aiquara_mover, aiquara_atacar, rogue_clock_move,
    baoba_pagar_magia, bimbo_invisibilidade, bimbo_gastar_5,
    zebum_invocar_heroi, zebum_reinvocar, zebum_invocar_proximo_anao,
    gnomo_alocar_aposta, purpura_invisibilidade, barba_mar_de_chamas,
    barba_combater_como_heroi, barba_resolver_mar_de_chamas,
    valtherion_chamado,
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
from .core.headless import apply_action as apply_engine_action, legal_actions
from .core import artifacts_effects, peoples, heroes, spells as spells_mod
from .narrative.terminal import narrate, read_checkpoint, write_checkpoint


console = Console()

PEOPLES = ["humanos", "anoes", "orcs", "fadas",
           "vampiros", "lobisomens", "gigantes", "mortos_vivos",
           "filhos_floresta", "gnomos_duendes", "dragoes", "demonios"]

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
    "dragoes": ["Barba Negra", "Púrpura", "Valtherion"],
    "demonios": ["Belial", "Tuza", "Rogue Devil"],
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
    "dragoes": "Envolvimento Cosmologico: ate 1 Artefato por naipe na Canastra fortalece Herois Dragoes.",
    "demonios": "Banco de Almas: +1 Magia sempre que qualquer unidade morre.",
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
    "ressonancia_magica": "Ressonancia Magica: adiciona, remove ou troca Artefato da Canastra.",
    "sacrificio_de_demonio": "Sacrificio de Demonio: mate seu Heroi e troque Artefatos escolhidos.",
}

HERO_ABILITY_DESC = {
    "miyamoto": "Invencivel sob o Sol: ataca de Dia. +vida max ao matar. 2 ataques se for o mais forte.",
    "besouro": "o Maioral: dobro + resistencia vs >=. Mandinga: artefato na Noite.",
    "iuna": "Aguia Negra: 1 de dano fixo recebido. 1D4 ao atacar. Adiciona 4 Penas.",
    "barbadourada": "Filho das Cachoeiras: +1 Magia por artefato na mao.",
    "ori": "Velho Mestre Ferreiro: ele + aliados na casa ganham Resistencia.",
    "seven_dwarves": "Os 7 Anoes: 7 herois em corrente. Sem Tropas.",
    "dain": "Atim: quem declara combate contra ele morre no fim da Noite.",
    "buin": "Dengoso: Invulneravel contra Herois.",
    "bein": "Soneca: mortos por ele ficam empalados ate os Anoes serem Curuna.",
    "boin": "Feliz: ve 2, escolhe 1 ao comprar/transmutar.",
    "tintin": "Dunga: fica Invisivel (recarga 1 turno).",
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
    "guarari": "Centauro permanente: anda 2x (1x ao ser invocado). Transforma aliado por 1 Magia.",
    "aiquara": "Ninfa: controla inimigo da casa (mover no Dia, atacar na Noite).",
    "baoba_ba": "Anciao: 1 Magia x 3 turnos para invocar. Tropas aliadas na casa dele.",
    "bimbo_do_mal": "Gastar aposta: invisivel (1) ou artefato da Loja (5).",
    "sao_tome": "Herda passivas dos jogadores apostados e pode rerrolar o feitico copiado.",
    "zebum": "Mistico: apostas corretas compram herois estrangeiros.",
    "barba_negra": "Base movel. Mar de Chamas e modo Heroi por uma Noite.",
    "purpura": "Cresce conforme manhas pares passadas. Pode ficar Invisivel.",
    "valtherion": "Base movel que combate como Heroi. Chamado invoca Tropas Dragao.",
    "belial": "Chamas: 1 dano em inimigos e cura 1 em aliados proximos no inicio da Noite.",
    "tuza": "Tem Resistencia. Inimigos podem firmar pactos no turno Curuna dos Demonios.",
    "rogue_devil": "Vida 0. Ao firmar/completar pactos, conquista Capa, Adaga, Relogio e Bracelete; com os 4 ataca Bases.",
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


PEOPLE_COLORS = {
    "humanos": "bright_blue",
    "anoes": "yellow",
    "orcs": "orange3",
    "fadas": "magenta",
    "vampiros": "red",
    "lobisomens": "dark_blue",
    "gigantes": "dark_orange3",
    "mortos_vivos": "grey50",
    "filhos_floresta": "green",
    "gnomos_duendes": "bright_magenta",
}

TROOP_DISPLAY = {
    "light": "Tropa pequena",   # v5v10c #20
    "medium": "Tropa média",
    "heavy": "Tropa grande",
    "special": "especial",
    "extra": "extra",
    "ghoul": "carnical",
    "esqueleto": "esqueleto",
}

ROCA_EFFECTS = {1: "Magia", 2: "Ouro", 3: "Cura 2 pendente", 4: "Dano 1 na sua Cidade"}
CABACA_EFFECTS = {1: "Invulneravel", 2: "+1 movimento", 3: "+1 Ouro", 4: "+1 Magia"}


def _pcolor(povo: str) -> str:
    return PEOPLE_COLORS.get(povo, "white")


def _pname(state, pid: int) -> str:
    try:
        p = get_player(state, pid)
    except Exception:
        return f"J{pid}"
    c = _pcolor(p.people)
    return f"[{c}]{p.name}[/{c}]"


def _troop_display(arch) -> str:
    if hasattr(arch, "value"):
        arch = arch.value
    return TROOP_DISPLAY.get(arch, str(arch))


def _hero_short(hero_id: str) -> str:
    try:
        n = heroes.hero_name(hero_id)
    except Exception:
        return str(hero_id)
    return n.split(",")[0].strip()


def _describe_roll(source: str, results: list) -> str:
    if source == "roca_humanos":
        effects = ROCA_EFFECTS
    elif source == "cabaca_cheia":
        effects = CABACA_EFFECTS
    else:
        effects = None
    parts = []
    for r in results:
        eff = effects.get(r) if effects else None
        if eff:
            parts.append(f"{r} ({eff})")
        else:
            parts.append(str(r))
    return ", ".join(parts)


SYMBOL_DESC = {
    "A": "Sob aura de Ori (dano recebido dividido por 2)",
    "2x": "Dobro de dano (Kc, Qs, Vovo, etc.)",
    "R": "Resistencia (R1 = 1 stack, R2 = 2 stacks - divide dano por 2 cada)",
    "~": "Invisivel (nao pode ser atacado ate o fim do turno)",
    "z": "Dormindo (nao pode atacar; acorda se for atacado)",
    "\u2620": "Amaldicoado (recebe o dobro de dano de TODAS as fontes)",
    "\u00d7": "Ks ativo (dobra o numero de ataques)",
    "B": "Morcego (vampiro com 2 movimentos neste turno)",
    "W": "Lobisomem (em Lua Cheia: dobro de dano)",
    "E": "Esploiado (nao pode atacar neste turno)",
    "C": "Centauro (2 movimentos ate o fim da Noite)",
    "\u2605": "Invulneravel (nao recebe dano neste turno)",
    "I": "Infectado (vira Lobisomem durante a Lua Cheia)",
}


def _unit_symbols(state, u) -> str:
    syms = []
    # Ori aura: se ha Ori no local
    try:
        owner = get_player(state, u.owner_id)
        for o in owner.units:
            if isinstance(o, Hero) and o.is_alive() and o.hero_id == "ori" and o.house == u.house:
                if o.id != u.id:
                    syms.append("A")
                    break
    except Exception:
        pass
    if u.double_damage:
        syms.append("2x")
    if u.resistance_stacks:
        syms.append(f"R{u.resistance_stacks}")
    if u.statuses.get("invisivel_until_turn", -1) >= state.turn:
        syms.append("~")
    if u.statuses.get("sono_until_turn", -1) > state.turn:
        syms.append("z")
    if u.statuses.get("amaldicoado_until_turn", -1) >= state.turn:
        syms.append("\u2620")
    if u.statuses.get("k_s_active"):
        syms.append("\u00d7")
    if u.statuses.get("morcego_until_turn", -1) >= state.turn:
        syms.append("B")
    if u.statuses.get("lobisomem_until_turn", -1) >= state.turn:
        syms.append("W")
    if u.statuses.get("cannot_attack_on_turn") == state.turn:
        syms.append("E")
    if u.statuses.get("centauro_until_turn", -1) == state.turn:
        syms.append("C")
    if u.statuses.get("invulneravel_until_turn", -1) >= state.turn:
        syms.append("\u2605")
    if peoples.is_unit_infected(state, u):
        syms.append("I")
    return "".join(syms)


def _describe_card(card_id) -> str:
    if not card_id:
        return "?"
    try:
        return card_display(card_id)
    except Exception:
        return str(card_id)


def _describe_hero(hero_id) -> str:
    if not hero_id:
        return "?"
    try:
        return heroes.hero_name(hero_id)
    except Exception:
        return str(hero_id)


def _describe_player(state, pid) -> str:
    if pid is None:
        return "?"
    try:
        return get_player(state, pid).name
    except Exception:
        return f"J{pid}"


def _describe_unit_kind(params, prefix="target") -> str:
    kind = params.get(f"{prefix}_kind")
    if kind == "hero":
        return f"Heroi {_describe_hero(params.get(f'{prefix}_hero_id'))}"
    if kind == "troop":
        arch = params.get(f"{prefix}_archetype", "?")
        return f"Tropa {arch}"
    return params.get(f"{prefix}_id", "?")




def show_hud(state) -> None:
    # v5v10e #17: apostas corretas de Gnomos
    for _p in state.players:
        if _p.people == "gnomos_duendes" and _p.city.is_alive():
            console.print(f"  [cyan]{_p.name}: apostas corretas = {_p.correct_bets}[/cyan]")
            bets = (("Copas", _p.bet_H_target), ("Paus", _p.bet_C_target),
                    ("Ouros", _p.bet_D_target), ("Espadas", _p.bet_S_target))
            allocation = ", ".join(
                f"{suit}: {_pname(state, target) if target else 'vazia'}"
                for suit, target in bets)
            console.print(f"  [cyan]Apostas — {allocation}[/cyan]")
    # v5v10c #16: aviso de Lua Cheia (só se houver lobisomem no jogo)
    try:
        _tem_lobo = any(p.people == "lobisomens" and p.city.is_alive()
                        for p in state.players)
        if _tem_lobo:
            from .core import peoples as _ppl
            for _p in state.players:
                if _p.people == "lobisomens" and _ppl.is_lua_cheia(state, _p.id):
                    console.print("[bold yellow]*** LUA CHEIA ***[/bold yellow]")
                    break
    except Exception:
        pass
    curuna = get_player(state, state.curuna_id)
    console.print(
        f"[bold yellow]T{state.turn} · {state.phase.value.upper()} · "
        f"Curuna: {curuna.name} ({curuna.people})[/bold yellow]   "
        f"[dim][m]apa  [B]oard  [l]og[/dim]"
    )
    for p in state.players:
        c = _pcolor(p.people)
        if not p.city.is_alive():
            console.print(f"[{c}]{p.name} ({p.people}) - ELIMINADO[/{c}]")
            continue
        chosen_str = "livre" if p.people == "mortos_vivos" and not p.chosen_hero_id else (
            _hero_short(p.chosen_hero_id) if p.chosen_hero_id else "-")
        hero_str = "-"
        for u in p.units:
            if isinstance(u, Hero) and u.is_alive():
                hero_str = f"{_hero_short(u.hero_id)} {u.life}/{u.life_max}"
                break
        name_pad = p.name.ljust(10)
        povo_pad = f"({p.people})".ljust(20)
        console.print(
            f"[{c}]{name_pad} {povo_pad}[/{c}] "
            f"vida {p.city.life}/{p.city.life_max}  "
            f"ouro {p.city.gold}  magia {p.city.magic}  "
            f"mao {len(p.hand)}  escolha {chosen_str}  em campo {hero_str}"
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
                    kind = _troop_display(u.archetype)
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
                if peoples.is_unit_infected(state, u):
                    flags.append("infectado")
                flags_str = f" [{', '.join(flags)}]" if flags else ""
                lines.append(f"    {p.name[:6]} · {u.id} ({kind}) {u.life}/{u.life_max}{flags_str}")
        label = house_short(state, house)
        if lines:
            console.print(f"  [bold]{label}:[/bold]")
            for ln in lines:
                console.print(ln)
        else:
            console.print(f"  [dim]{label}: (vazio)[/dim]")
    _board_empalados_infectados(state)

def _status_signature_label(state, sig: dict, default_owner_id=None) -> str:
    if sig.get("kind") == "hero":
        name = heroes.hero_name(sig.get("id", "?"))
    else:
        name = f"Tropa {_troop_display(sig.get('id', '?'))}"
    owner_id = sig.get("owner_id", default_owner_id)
    if owner_id is None:
        return name
    owner = get_player(state, owner_id)
    return f"{name} — J{owner.id}/{owner.people}"


def _board_empalados_infectados(state) -> None:
    empal = []
    for p in state.players:
        for sig in p.empalados:
            empal.append(f"  {_status_signature_label(state, sig, p.id)}")
    infect = []
    for p in state.players:
        for sig in p.infectados:  # v5v10 #18/19
            infect.append(f"  {_status_signature_label(state, sig)} "
                          f"(infectado por {_pname(state, p.id)})")
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


def show_turn_log(state) -> None:
    historico(state)



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


def show_eventos_futuros(state) -> None:
    console.print("[bold]Eventos futuros previstos[/bold]")
    found = False
    for p in state.players:
        if p.city.has_monument and p.city.is_alive():
            next_mult = ((state.turn // 4) + 1) * 4
            console.print(f"  {p.name}: Monumento -> +1 artefato no turno {next_mult}")
            found = True
    for p in state.players:
        if state.turn < p.spell_cooldown_until_turn and p.city.is_alive():
            console.print(f"  {p.name}: Feitico disponivel no turno {p.spell_cooldown_until_turn}")
            found = True
    for e in state.pending_effects:
        try:
            pname = get_player(state, e["player_id"]).name
        except Exception:
            pname = f"J{e.get('player_id', '?')}"
        kind = e.get("kind", "?")
        due = e.get("due_turn", "?")
        console.print(f"  {pname}: {kind} no turno {due}")
        found = True
    for p in state.players:
        if (p.people == "filhos_floresta" and p.city.is_alive()
                and not p.filhos_bonus_recebido and state.turn < 13):
            console.print(f"  {p.name} (Filhos): Florescimento Exuberante no turno 13")
            found = True
    if state.turn >= 13:
        console.print("  [red]Turno 13+ ativo: ninguem pode mais subir muralha.[/red]")
    else:
        console.print(f"  [dim]A partir do turno 13, ninguem podera subir muralha.[/dim]")
    if not found:
        console.print("  [dim](nada previsto)[/dim]")
    console.print()


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
    if peoples.is_unit_infected(state, u):
        console.print("  - Infectado (vira Lobisomem durante a Lua Cheia)")
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


def _menu_informacoes(state, pid: int) -> None:
    opts = [
        "Loja",
        "Inspecionar local",
        "Inspecionar unidade (ficha completa)",
        "Artefatos em campo (todos)",
        "Unidades com condições",
        "Eventos futuros",
        "Ver povo (todos os 10)",
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
        show_unidades_condicionadas(state)
    elif idx == 5:
        show_eventos_futuros(state)
    elif idx == 6:
        _menu_povos(state, pid)

def show_unidades_condicionadas(state) -> None:
    console.print("[bold]Unidades com condições[/bold]")
    found = False
    for p in state.players:
        for u in p.units:
            conditions = []
            if u.double_damage: conditions.append("dobro de dano")
            if u.resistance_stacks: conditions.append(f"resistência x{u.resistance_stacks}")
            if u.max_moves_this_turn > 1: conditions.append(f"anda {u.max_moves_this_turn}x")
            attacks = _effective_max_attacks(state, u)
            if attacks > 1: conditions.append(f"bate {attacks}x")
            if u.statuses.get("invulneravel_until_turn", -1) >= state.turn: conditions.append("invulnerável")
            if u.statuses.get("invisivel_until_turn", -1) >= state.turn: conditions.append("invisível")
            if u.statuses.get("cannot_attack_on_turn") == state.turn: conditions.append("não pode atacar")
            if peoples.is_unit_infected(state, u): conditions.append("infectada")
            if peoples.has_vovo_bonus(state, u): conditions.append("+1 de dano")
            if conditions:
                found = True
                console.print(f"  {u.id} — {p.name}/{p.people}: {', '.join(conditions)}")
    if not found:
        console.print("  [dim](nenhuma unidade viva condicionada)[/dim]")
    console.print()
    console.print("[bold]Empalados (nao podem ser reinvocados)[/bold]")
    found = False
    for p in state.players:
        if p.empalados:
            found = True
            for sig in p.empalados:
                console.print(f"  {_status_signature_label(state, sig, p.id)}")
        for entry in p.dwarf_empalados:
            found = True
            console.print(f"  {_status_signature_label(state, entry['sig'], p.id)} (por Soneca)")
    if not found:
        console.print("  [dim](nenhum)[/dim]")  # v5v10 #18/19 (marcador W adicionado em _board_empalados_infectados)
    console.print()
    console.print("[bold]Infectados (viram Lobisomem em Lua Cheia)[/bold]")
    found = False
    for p in state.players:
        if p.infectados:
            found = True
            for sig in p.infectados:
                console.print(f"  {_status_signature_label(state, sig)} "
                              f"(infectado por {p.name})")
    if not found:
        console.print("  [dim](nenhum)[/dim]")  # v5v10 #18/19 (marcador W adicionado em _board_empalados_infectados)
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
        opts.append("Guarari: transformar tropa em Centauro (1 Magia)")
        keys.append("q")
    if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "aiquara" for u in player.units):
        opts.append("Aiquara: controlar inimigo")
        keys.append("i")
    if (player.people == "filhos_floresta"
            and player.chosen_hero_id == "baoba_ba"  # v5v10 #10
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
    if (player.people == "gnomos_duendes"
            and player.spell_copia_id
            and player.spell_copia_turn == state.turn
            and player.spell_copia_rerolled_turn != state.turn
            and not player.has_cast_spell_this_turn
            and any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "sao_tome"
                    for u in player.units)):
        opts.append(f"São Tomé: rerrolar feitiço ({player.spell_copia_id})")
        keys.append("R")
    if player.pending_heals > 0:
        opts.append(f"Usar cura pendente ({player.pending_heals})")
        keys.append("h")
    purpura = next((u for u in player.units if isinstance(u, Hero) and u.is_alive()
                    and u.hero_id == "purpura"), None)
    if purpura and purpura.statuses.get("purpura_cooldown_until_turn", -1) <= state.turn:
        opts.append("Purpura: ficar invisivel")
        keys.append("u")
    valtherion = next((u for u in player.units if isinstance(u, Hero) and u.is_alive()
                       and u.hero_id == "valtherion"), None)
    if valtherion and valtherion.statuses.get("chamado_cooldown_until_turn", -1) <= state.turn:
        opts.append("Valtherion: Chamado")
        keys.append("v")
    barba = next((u for u in player.units if isinstance(u, Hero) and u.is_alive()
                  and u.hero_id == "barba_negra"), None)
    if barba is not None:
        if barba.statuses.get("mar_chamas_cooldown_until_turn", -1) <= state.turn:
            opts.append("Barba Negra: preparar Mar de Chamas")
            keys.append("B")
        if barba.statuses.get("barba_hero_mode_turn") != state.turn:
            opts.append("Barba Negra: combater como Herói nesta Noite")
            keys.append("H")
    if player.demon_pact_offers and peoples.available_demon_pacts(state):
        opts.append("Escolher pacto demoniaco disponivel")
        keys.append("D")
    if peoples.can_take_tuza_pact(state, player.id) is not None and peoples.available_demon_pacts(state):
        opts.append("Firmar pacto com Tuza")
        keys.append("E")
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


def _gnomos_bets_inicio_turno(state):
    """Realoca apostas antes de qualquer jogador iniciar seu dia."""
    for player in state.players:
        if (player.people == "gnomos_duendes" and player.city.is_alive()
                and player.bets_need_realocacao):
            _gnomo_bets_menu(state, player)


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
    if spell_id == "sonho_lucido":
        return _sonho_lucido_ui(state, player)
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
        labels = ["light", "medium", "heavy", "ghoul", "esqueleto"]  # v5v10c #11
        i1 = pick_index("Arquetipo 1", labels)
        i2 = pick_index("Arquetipo 2", labels)
        cd["archetypes"] = [labels[i1], labels[i2]]
    elif spell_id == "decompor":
        return _escolher_decompor(state, player)
    elif spell_id == "ressonancia_magica":
        return _dragon_resonance_ui(player)
    elif spell_id == "sacrificio_de_demonio":
        return _sacrificio_demonio_ui(player)
    elif spell_id == "imitacao_gnomerica":
        raise ActionError("Nao pode imitar a si mesmo.")
    return cd


def _sonho_lucido_ui(state, player):
    pid = player.id
    choice_data = {}
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
            raise ActionError("Sonho Lucido cancelado.")
        choice_data["flip_cards"] = cards
    else:
        if not player.hand:
            raise ActionError("Mao vazia.")
        labels = [card_display(c) for c in player.hand] + ["Cancelar"]
        idx = pick_index("Inverter qual?", labels)
        if idx == len(player.hand):
            console.print("[yellow]Sonho Lucido cancelado.[/yellow]")
            return None
        choice_data["flip_cards"] = [player.hand[idx]]
    artifact_choices = []
    for original in choice_data.get("flip_cards", []):
        transformed = peoples.sonho_lucido_flip(original)
        artifact_choices.append(
            _ask_choice_for_artifact(state, pid, transformed)
            if artifacts_effects.needs_choice(transformed) else {}
        )
    choice_data["artifact_choices"] = artifact_choices
    return choice_data


def _dragon_resonance_ui(player):
    options = []
    occupied = {get_definition(c).suit for c in player.canastra}
    addable = [c for c in player.hand if get_definition(c).suit
               and get_definition(c).suit not in occupied]
    if addable:
        options.append("Adicionar")
    if player.canastra:
        options.append("Remover")
    swaps = [(old, new) for old in player.canastra for new in player.hand
             if get_definition(old).suit == get_definition(new).suit]
    if swaps:
        options.append("Trocar")
    if not options:
        raise ActionError("Nenhuma operacao valida para a Canastra.")
    op = options[pick_index("Ressonancia Magica", options)]
    if op == "Adicionar":
        card = addable[pick_index("Incorporar", [card_display(c) for c in addable])]
        return {"action": "add", "card_id": card}
    if op == "Remover":
        card = player.canastra[pick_index("Remover", [card_display(c) for c in player.canastra])]
        return {"action": "remove", "card_id": card}
    old, new = swaps[pick_index("Trocar", [f"{card_display(a)} -> {card_display(b)}"
                                            for a, b in swaps])]
    return {"action": "swap", "old_card_id": old, "new_card_id": new}


def _demon_pact_ui(state, player, demon_player_id, rogue=False, required=False):
    pact_ids = peoples.available_demon_pacts(state)
    if not pact_ids:
        raise ActionError("Todos os pactos demoníacos já foram escolhidos.")
    labels = [peoples.DEMON_PACTS[p] for p in pact_ids]
    if not required:
        labels.append("Não fazer pacto")
    idx = pick_index("Pacto demoníaco", labels)
    if idx == len(pact_ids):
        return False
    buff = None
    if rogue:
        rogue_unit = next((u for u in player.units if isinstance(u, Hero)
                           and u.hero_id == "rogue_devil"), None)
        owned = set(player.rogue_items)
        available_items = [i for i in peoples.ROGUE_ITEMS if i not in owned]
        labels_items = {
            "capa": "Capa — fica invisível ao derrotar inimigo",
            "adaga": "Adaga — executa inimigos menores isolados",
            "relogio": "Relógio — transporte antes do fim da Noite",
            "bracelete": "Bracelete — resistência a heróis e +1 Vida",
        }
        if available_items:
            buff = available_items[pick_index(
                "Item de Rogue Devil", [labels_items[i] for i in available_items])]
    peoples.make_demon_pact(state, demon_player_id, player.id, pact_ids[idx], buff,
                            rogue_pact=rogue)
    console.print(f"[green]Pacto firmado: {labels[idx]}.[/green]")
    return True


def _sacrificio_demonio_ui(player):
    living_heroes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()]
    if not living_heroes:
        raise ActionError("Sem Heroi vivo para sacrificar.")
    hero = living_heroes[pick_index(
        "Heroi sacrificado", [f"{heroes.hero_name(u.hero_id)} ({u.life}/{u.life_max})"
                              for u in living_heroes])]
    available = ([{"zone": "hand", "card_id": c} for c in player.hand]
                 + [{"zone": "field", "card_id": a.card_id}
                    for a in player.field_artifacts])
    selected = []
    while available:
        labels = [f"{item['zone']}: {card_display(item['card_id'])}" for item in available]
        labels.append("Concluir seleção")
        idx = pick_index("Reembaralhar", labels)
        if idx == len(available):
            break
        selected.append(available.pop(idx))
    if not selected:
        raise ActionError("Escolha ao menos um Artefato.")
    return {"hero_id": hero.id, "artifacts": selected}


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
                    if (other.id != player.id
                            and (other.chosen_hero_id == hid
                                 or hid in other.summoned_hero_ids)):
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
        "[cyan]l[/cyan]       Histórico da partida\n"
        "[cyan]R[/cyan]       Relatorios (producao, combate, artefatos)\n"
        "[cyan]?[/cyan]       Ajuda (esta tela)\n"
        "[cyan]M[/cyan]       Menu (colher de cha, mola, recomecar)\n"
        "[cyan]0[/cyan]       Passar a vez",
        border_style="cyan"))


def _ajuda_simbolos() -> None:
    table = Table(title="Simbolos no mapa", box=box.ROUNDED)
    table.add_column("Simbolo")
    table.add_column("Efeito")
    for k, v in SYMBOL_DESC.items():
        table.add_row(k, v)
    console.print(table)


def _menu_ajuda(state, pid: int) -> None:
    opts = [
        "Tutorial rapido",
        "Meu povo (passiva, feitico, herois)",
        "Outros povos em jogo",
        "Referencia de artefatos",
        "Referencia de statuses",
        "Referencia de simbolos (mapa)",
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
        _ajuda_simbolos()
    elif idx == 6:
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
            f"{p.name} ({_pcolor(p.people)}|{p.people})",
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


def _pick_unit_or_cancel(player, prompt="Alvo"):
    """Retorna unit_id ou None se cancelar. Cancelar no fim da lista."""
    if not player.units:
        raise ActionError("Sem unidades.")
    labels = [f"{u.id} ({u.life}/{u.life_max})" for u in player.units] + ["Cancelar"]
    idx = pick_index(prompt, labels)
    if idx == len(player.units):
        return None
    return player.units[idx].id


def _get_actions(state, player) -> list[tuple[str, str, str]]:
    sp = spells_mod.spell_for_people(player.people)

    r = []
    r.append(("Turno", "1", "Acoes (coletar, invocar, mover, monumento)"))
    r.append(("Turno", "2", "Artefatos (comprar, transmutar, vender, jogar)"))
    r.append(("Turno", "3", f"Lancar feitico: {sp.name}" if sp else "Lancar feitico"))
    r.append(("Turno", "4", "Especiais (herois, habilidades)"))


    r.append(("Info", "i", "Informacoes"))
    r.append(("Info", "m", "Mapa"))
    r.append(("Info", "p", "Panorama (Board)"))
    r.append(("Info", "l", "Histórico da partida"))
    r.append(("Info", "r", "Relatorios"))
    r.append(("Info", "?", "Ajuda"))
    r.append(("Info", "x", "Menu do sistema"))
    return r


def pick_index(prompt: str, options: list[str], secret: bool = False) -> int:
    table = Table(box=box.SIMPLE)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Opcao")
    for i, opt in enumerate(options, 1):
        table.add_row(str(i), opt)
    console.print(table)
    while True:
        try:
            n = IntPrompt.ask(prompt, default=1, password=secret)
            if 1 <= n <= len(options):
                return n - 1
        except Exception:
            pass
        console.print(f"[red]Escolha entre 1 e {len(options)}[/red]")


def valid_destinations(state, unit) -> list[str]:
    if unit.house.startswith("city_"):
        return [CENTER]
    if unit.house == CENTER:
        return [h for h in city_houses(state)
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


def _show_people_selection_help(peoples_available) -> None:
    table = Table(title="Consulta de povos", box=box.SIMPLE)
    table.add_column("Povo")
    table.add_column("Passiva")
    table.add_column("Feitiço")
    for people in peoples_available:
        spell = spells_mod.spell_for_people(people)
        table.add_row(people, PASSIVA_DESC.get(people, "—"),
                      f"{spell.name}: {spell.description}" if spell else "—")
    console.print(table)


def _show_hero_selection_help(people: str, hero_names) -> None:
    table = Table(title=f"Heróis de {people}", box=box.SIMPLE)
    table.add_column("Herói")
    table.add_column("Vida")
    table.add_column("Habilidade")
    for name in hero_names:
        hid = heroes.resolve_hero_for_people(people, name)
        definition = heroes.get_hero(hid)
        table.add_row(definition.name, str(definition.life),
                      HERO_DESCRIPTIONS.get(hid, ", ".join(definition.abilities) or "—"))
    console.print(table)


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
    num_players = _ask_int("Número de jogadores [4]", default=4, min_val=2, max_val=5)
    city_life = _ask_int(f"Vida inicial da Cidade [{DEFAULT_CITY_LIFE_START}]",
                         default=DEFAULT_CITY_LIFE_START, min_val=1, max_val=100)
    city_life_max = _ask_int(f"Vida maxima da Cidade [{DEFAULT_CITY_LIFE_MAX}]",
                             default=DEFAULT_CITY_LIFE_MAX, min_val=city_life, max_val=100)
    gold_start = _ask_int(f"Ouro inicial [{DEFAULT_STARTING_GOLD}]",
                          default=DEFAULT_STARTING_GOLD, min_val=0, max_val=999)
    magic_start = _ask_int(f"Magia inicial [{DEFAULT_STARTING_MAGIC}]",
                           default=DEFAULT_STARTING_MAGIC, min_val=0, max_val=999)
    artifacts_start = _ask_int("Artefatos iniciais por jogador [0]", default=0, min_val=0, max_val=24 // num_players)
    console.print()
    rng = make_rng(seed)
    order = roll_d20_order(rng, num_players)
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
    for pid in range(1, num_players + 1):
        names[pid] = Prompt.ask(f"Nome do Jogador {pid}", default=f"Jogador {pid}")
    console.print()
    choices: dict[int, dict] = {}
    console.print("[bold]Escolha de povos (sentido horario)[/bold]\n")
    available_peoples = list(PEOPLES)
    for pid in povo_order:
        console.print(f"Vez de [bold]{names[pid]}[/bold] (Jogador {pid}).")
        while True:
            options = list(available_peoples) + ["Consultar o que os povos fazem"]
            idx = pick_index("Povo", options)
            if idx < len(available_peoples):
                break
            _show_people_selection_help(available_peoples)
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
        console.clear()
        console.print("[bold]Povos confirmados (públicos)[/bold]")
        for other in povo_order:
            console.print(f"{names[other]}: {choices[other]['povo']}")
        Prompt.ask(f"Passe o terminal a {names[pid]}. Só essa pessoa deve ver a escolha. Enter para continuar", default="")
        # Ent permanece fora da selecao enquanto aguarda rework.
        herois = [name for name in HEROES_BY_PEOPLE[povo]
                  if name.strip().lower() != "ent"
                  and heroes.normalize_hero_id(name) != "ent"]
        console.print(f"Vez de [bold]{names[pid]}[/bold] ({povo}).")
        while True:
            options = list(herois) + ["Consultar o que os heróis fazem"]
            idx = pick_index("Heroi (escolha secreta)", options, secret=True)
            if idx < len(herois):
                break
            _show_hero_selection_help(povo, herois)
        choices[pid]["heroi"] = herois[idx]
        console.clear()
    console.print("[bold]Todos escolheram — revelação dos heróis[/bold]")
    for pid in povo_order:
        console.print(f"{names[pid]}: {choices[pid]['heroi'] or 'Mortos-Vivos: escolhe ao invocar'}")
    initial = {pid: {"artifacts": artifacts_start} if artifacts_start else {} for pid in names}
    if Prompt.ask("Personalizar condições por jogador?", choices=["s", "n"], default="n") == "s":
        for pid in names:
            console.print(f"[bold]{names[pid]}[/bold] — Enter mantém o padrão.")
            for key, label, minimum, maximum in (("city_life", "Vida da Base", 1, 100),
                    ("gold", "Ouro", 0, 999), ("magic", "Magia", 0, 999),
                    ("artifacts", "Artefatos", 0, 24 - sum(v.get("artifacts", 0) for other, v in initial.items() if other != pid))):
                while True:
                    value = Prompt.ask(label, default="").strip()
                    if not value:
                        break
                    if value.isdigit() and minimum <= int(value) <= maximum:
                        initial[pid][key] = int(value)
                        break
                    console.print(f"Informe um inteiro entre {minimum} e {maximum}.")
    state, _ = run_setup(
        all_peoples=PEOPLES, heroes_by_people=HEROES_BY_PEOPLE,
        choices=choices, seed=seed, turn_order=order,
        city_life=city_life, city_life_max=city_life_max,
        gold_start=gold_start, magic_start=magic_start,
        num_players=num_players, initial_conditions=initial,
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
                kind = _troop_display(u.archetype)
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
    if player.people == "dragoes":
        canastra = ", ".join(card_display(c) for c in player.canastra) or "(vazia)"
        console.print(f"[bold]Canastra:[/bold] {canastra}")
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
    povo = player.people[:10]
    c = _pcolor(player.people)
    title = f"[{c}]J{pid} {player.name[:8]}{mark}[/{c}]"
    sub = f"[{c}]({povo})[/{c}]"
    vida = f"Cidade {city.life}/{city.life_max}" if city.is_alive() else "[red]RUIDA[/red]"
    lines = [_pad(f"[bold]{title}[/bold]", width), _pad(sub, width), _pad(vida, width)]
    house = f"city_{pid}"
    units = []
    for p in state.players:
        for u in p.units:
            if u.house == house and u.is_alive():
                syms = _unit_symbols(state, u)
                if isinstance(u, Hero):
                    label = f"{_hero_short(u.hero_id)} {u.life}{syms}"
                else:
                    label = f"{_troop_display(u.archetype)} {u.life}{syms}"
                if p.id != pid:
                    label = f"J{p.id} {label}"
                units.append(label)
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
            if u.house == CENTER and u.is_alive():
                syms = _unit_symbols(state, u)
                if isinstance(u, Hero):
                    label = f"J{p.id} {_hero_short(u.hero_id)} {u.life}{syms}"
                else:
                    label = f"J{p.id} {_troop_display(u.archetype)} {u.life}{syms}"
                units.append(label)
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
    cells = {p.id: _city_cell_lines(state, p.id, w) for p in state.players}
    center = _center_cell_lines(state, w)
    height = max(*(len(cell) for cell in cells.values()), len(center), 3)
    cells = {pid: _pad_to_height(cell, height, w) for pid, cell in cells.items()}
    center = _pad_to_height(center, height, w)
    empty = [" " * w for _ in range(height)]
    sep = " | "
    line_sep = "-" * (w * 3 + 6)
    layouts = {2: [(None, 1, None), (None, "center", None), (None, 2, None)],
               3: [(None, 1, None), (None, "center", None), (2, None, 3)],
               4: [(None, 3, None), (4, "center", 2), (None, 1, None)],
               5: [(None, 1, None), (2, "center", 5), (3, None, 4)]}
    cells.update({None: empty, "center": center})
    for row_index, row in enumerate(layouts[len(state.players)]):
        if row_index:
            console.print(line_sep, highlight=False)
        for i in range(height):
            console.print(sep.join(cells[key][i] for key in row), highlight=False)
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





TODOS_POVOS = [
    "humanos", "anoes", "orcs", "fadas", "vampiros",
    "lobisomens", "gigantes", "mortos_vivos",
    "filhos_floresta", "gnomos_duendes", "dragoes", "demonios",
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
    for h in city_houses(state):
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
    previous_turn = None
    for line in log_lines:
        match = re.match(r"\[T(\d+)\s", line)
        turn = int(match.group(1)) if match else None
        if turn is not None and turn != previous_turn:
            console.rule(f"TURNO {turn}")
            previous_turn = turn
        console.print(line, markup=False, highlight=False)


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
        options = [h for h in city_houses(state)
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


def _collect_resources_via_engine(state, pid: int) -> dict:
    actions = [action for action in legal_actions(state, pid)
               if action["type"] == "collect_resources"]
    if not actions:
        raise ActionError("Coleta indisponivel.")
    labels = [f"{action['params']['gold']} Ouro / "
              f"{action['params']['magic']} Magia" for action in actions]
    action = actions[pick_index("Coletar", labels)]
    result = apply_engine_action(state, action)
    if not result["success"]:
        raise ActionError(result["error"]["message"])
    for event in result["events"]:
        if event["type"] == "resources_collected":
            data = event["data"]
            console.print(f"[green]Coletou {data['gold']} Ouro e "
                          f"{data['magic']} Magia.[/green]")
    return result


def _apply_simple_engine_action(state, action: dict) -> dict:
    result = apply_engine_action(state, action)
    if not result["success"]:
        raise ActionError(result["error"]["message"])
    return result


def _do_action(state, pid: int, choice: str) -> str | None:
    player = get_player(state, pid)
    if choice == "1":
        _collect_resources_via_engine(state, pid)
    elif choice == "2":
        times = IntPrompt.ask("Vezes", default=1)
        actions = [a for a in legal_actions(state, pid)
                   if a["type"] == "raise_city_life" and a["params"]["times"] == times]
        if not actions:
            raise ActionError("Quantidade de aumento não é legal no estado atual.")
        _apply_simple_engine_action(state, actions[0])
        console.print("[green]Vida ok.[/green]")
    elif choice == "3":
        if peoples.has_7_dwarves_chosen(player):
            raise ActionError("Sem Tropas (7 Anoes).")
        archetypes = peoples.available_archetypes(player)
        labels = [f"{a.value} (max {TROOP_MAX_LIFE[a.value]})" for a in archetypes]
        archetype = archetypes[pick_index("Arquetipo", labels)]
        max_life = TROOP_MAX_LIFE[archetype.value]
        life = IntPrompt.ask(f"Vida (1 a {max_life})", default=max_life)
        action = next((a for a in legal_actions(state, pid)
                       if a["type"] == "summon_troop"
                       and a["params"] == {"archetype": archetype.value,
                                           "life": life, "house": f"city_{pid}"}), None)
        if action is None:
            raise ActionError("Invocação de Tropa não é legal no estado atual.")
        _apply_simple_engine_action(state, action)
        console.print("[green]Tropa ok.[/green]")
    elif choice == "4":
        if player.people == "mortos_vivos":
            hid = _escolher_heroi_mv()
            params = {"hero_id": hid}
        elif (player.people == "gnomos_duendes"
              and peoples.PEOPLE_MORTOS_VIVOS in
              peoples.sao_tome_effective_peoples(state, player)):
            ids = ["bimbo_do_mal", "sao_tome", "zebum"]
            available = [hid for hid in ids if not any(
                isinstance(u, Hero) and u.is_alive() and u.hero_id == hid
                for u in player.units)]
            if not available:
                raise ActionError("Os 3 herois gnomos ja estao vivos.")
            hid = available[pick_index("Heroi", [heroes.hero_name(h) for h in available])]
            params = {"hero_id": hid}
        else:
            params = {}
        action = next((a for a in legal_actions(state, pid)
                       if a["type"] == "summon_hero" and a["params"] == params), None)
        if action is None:
            raise ActionError("Invocação de Herói não é legal no estado atual.")
        _apply_simple_engine_action(state, action)
        rogue_offer = next((offer for offer in player.demon_pact_offers
                            if offer.get("source") == "rogue_devil"
                            and offer.get("turn") == state.turn), None)
        if rogue_offer is not None:
            _demon_pact_ui(state, player, rogue_offer["demon_player_id"],
                           rogue=True, required=True)
            player.demon_pact_offers.remove(rogue_offer)
        console.print("[green]Heroi ok.[/green]")
    elif choice == "5":
        alive = [u for u in player.units if u.is_alive()]
        units = [u for u in alive if not u.has_moved_this_turn
                 and u.moves_this_turn < u.max_moves_this_turn
                 and not (u.statuses.get("summoned_turn") == state.turn
                          and not (isinstance(u, Hero) and u.hero_id in ("guarari", "luarado")
                                   and (u.hero_id == "guarari"
                                        or peoples.is_lua_cheia(state, player.id)
                                        or u.statuses.get("lobisomem_until_turn", -1) >= state.turn)))]
        if not units:
            if any(u.statuses.get("summoned_turn") == state.turn for u in alive):
                raise ActionError("Unidade recém invocada não pode se movimentar.")
            raise ActionError("Sem unidades.")
        labels = [f"{u.id} ({house_short(state, u.house)}, {u.life})" for u in units] + ["Cancelar"]
        idx = pick_index("Unidade", labels)
        if idx == len(units):
            console.print("[yellow]Movimento cancelado.[/yellow]")
            return None
        unit = units[idx]
        dests = valid_destinations(state, unit)
        if not dests:
            raise ActionError("Sem destinos.")
        destination = dests[0] if unit.house.startswith("city_") else dests[
            pick_index("Destino", [house_short(state, d) for d in dests])]
        _apply_simple_engine_action(state, next(
            a for a in legal_actions(state, pid)
            if a["type"] == "move_unit"
            and a["params"] == {"unit_id": unit.id, "destination": destination}))
        console.print("[green]Movimento ok.[/green]")
    elif choice == "6":
        actions = [a for a in legal_actions(state, pid) if a["type"] == "build_monument"]
        if not actions:
            raise ActionError("Construir Monumento não é legal no estado atual.")
        _apply_simple_engine_action(state, actions[0])
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
        labels = [card_display(c) for c in player.hand] + ["Cancelar"]
        idx = pick_index("Jogar", labels)
        if idx == len(player.hand):
            console.print("[yellow]Cancelado.[/yellow]")
            return None
        card = player.hand[idx]
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
        aliados = [u for u in player.units if u.is_alive() and u.id != guarari.id
                   and u.house == guarari.house]
        if not aliados:
            raise ActionError("Sem aliados na casa de Guarari.")
        labels = [f"{u.id} ({u.life}/{u.life_max})" for u in aliados]
        t = aliados[pick_index("Aliado", labels)]
        transformar_em_centauro(state, pid, t.id)
        console.print("[green]Centauro ativo ate o fim da Noite.[/green]")
    elif choice == "u":
        purpura_invisibilidade(state, pid)
        console.print("[green]Purpura ficou invisivel.[/green]")
    elif choice == "v":
        kinds = [TroopArchetype.DRAGON_LIGHT, TroopArchetype.DRAGON_MEDIUM,
                 TroopArchetype.DRAGON_HEAVY]
        labels = [f"{a.value} (max {TROOP_MAX_LIFE[a.value]})" for a in kinds]
        troop = valtherion_chamado(state, pid, kinds[pick_index("Chamado", labels)])
        console.print(f"[green]Chamado: {troop.id} ({troop.life}/{troop.life_max}).[/green]")
    elif choice == "B":
        barba_mar_de_chamas(state, pid)
        console.print("[green]Mar de Chamas preparado.[/green]")
    elif choice == "H":
        barba_combater_como_heroi(state, pid)
        console.print("[green]Barba Negra combaterá como Herói nesta Noite.[/green]")
    elif choice == "i":
        _aiquara_ui(state, pid)
    elif choice == "b":
        baoba_pagar_magia(state, pid)
        console.print(f"[green]Baoba-ba: {player.baoba_pagamentos}/3.[/green]")
    elif choice == "p":
        _bimbo_ui(state, pid)
    elif choice == "g":
        _zebum_ui(state, pid)
    elif choice == "R":
        new_spell = peoples.reroll_spell_copia(state, pid)
        console.print(f"[green]Novo feitiço copiado: {new_spell}.[/green]")
    elif choice == "D":
        offer = player.demon_pact_offers.pop(0)
        _demon_pact_ui(state, player, offer["demon_player_id"],
                       rogue=offer.get("source") == "rogue_devil")
    elif choice == "E":
        demon_pid = peoples.can_take_tuza_pact(state, pid)
        if demon_pid is None:
            raise ActionError("Tuza não oferece pacto agora.")
        _demon_pact_ui(state, player, demon_pid)
    elif choice == "f":
        sp = spells_mod.spell_for_people(player.people)
        if sp is None:
            raise ActionError("Sem feitico.")
        if sp.spell_id == "sonho_lucido" and peoples.valendar_is_alive(player):
            raise ActionError("Valendar substitui Sonho Lucido.")
        choice_data: dict = {}
        if sp.spell_id == "resistencia":
            _uid = _pick_unit_or_cancel(player, "Alvo")
            if _uid is None:
                console.print("[yellow]Cancelado.[/yellow]")
                return None
            choice_data["unit_id"] = _uid
        elif sp.spell_id == "armadura_de_ouro":
            choice_data["cap"] = _ask_int("Cap por hit", default=2, min_val=1, max_val=10)
        elif sp.spell_id == "transformar_morcego":
            _uid = _pick_unit_or_cancel(player, "Alvo")
            if _uid is None:
                console.print("[yellow]Cancelado.[/yellow]")
                return None
            choice_data["unit_id"] = _uid
        elif sp.spell_id == "licantropo":
            _uid = _pick_unit_or_cancel(player, "Alvo")
            if _uid is None:
                console.print("[yellow]Cancelado.[/yellow]")
                return None
            choice_data["unit_id"] = _uid
        elif sp.spell_id == "linhagem_ancestral":
            gigantes = [u for u in player.units if isinstance(u, Hero) and u.is_alive()
                        and u.hero_id in ("joao_grandao", "pe_descalco", "caroco")]
            if not gigantes:
                raise ActionError("Sem herois Gigantes vivos.")
            labels = [heroes.hero_name(u.hero_id) for u in gigantes]
            choice_data["hero_id"] = gigantes[pick_index("Heroi", labels)].hero_id
        elif sp.spell_id == "levantar_mortos":
            labels = ["light", "medium", "heavy", "ghoul", "esqueleto"]  # v5v10c #11
            i1 = pick_index("Arquetipo 1", labels)
            i2 = pick_index("Arquetipo 2", labels)
            choice_data["archetypes"] = [labels[i1], labels[i2]]
        elif sp.spell_id == "decompor":
            choice_data = _escolher_decompor(state, player)
        elif sp.spell_id == "imitacao_gnomerica":
            choice_data = _escolher_imitacao(state, player)
        elif sp.spell_id == "sonho_lucido":
            choice_data = _sonho_lucido_ui(state, player)
        elif sp.spell_id == "ressonancia_magica":
            choice_data = _dragon_resonance_ui(player)
        elif sp.spell_id == "sacrificio_de_demonio":
            choice_data = _sacrificio_demonio_ui(player)
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


def _visible_state_snapshot(state) -> dict:
    result = {}
    for p in state.players:
        result[p.id] = {
            "Ouro": p.city.gold, "Magia": p.city.magic,
            "Vida da Base": p.city.life, "Vida máxima da Base": p.city.life_max,
            "Artefatos na mão": len(p.hand), "Canastra": tuple(p.canastra),
            "Unidades": {
                u.id: (u.life, u.life_max, u.house, u.moves_this_turn,
                       u.max_moves_this_turn, u.attacks_made_this_night,
                       u.max_attacks_this_night, u.double_damage,
                       u.resistance_stacks, tuple(sorted(u.statuses.items())))
                for u in p.units
            },
        }
    return result


def _log_visible_state_changes(state, before: dict, source: str,
                               prior_lines: list[str] | None = None) -> None:
    after = _visible_state_snapshot(state)
    prior_lines = prior_lines or []
    for p in state.players:
        old, new = before.get(p.id, {}), after[p.id]
        for key in ("Ouro", "Magia", "Vida da Base", "Vida máxima da Base",
                    "Artefatos na mão", "Canastra"):
            if old.get(key) != new[key]:
                if (key in ("Ouro", "Magia") and any(
                        f"{p.name} coletou" in line for line in prior_lines)):
                    continue
                log(state, f"[STATE] {source}: {p.name} — {key}: {old.get(key)} -> {new[key]}.")
        old_units, new_units = old.get("Unidades", {}), new["Unidades"]
        for uid in sorted(set(old_units) | set(new_units)):
            previous, current = old_units.get(uid), new_units.get(uid)
            if previous == current:
                continue
            unit = next((u for u in p.units if u.id == uid), None)
            if isinstance(unit, Hero):
                unit_name = heroes.hero_name(unit.hero_id)
            elif isinstance(unit, Troop):
                size = {"light": "pequena", "medium": "média", "heavy": "grande",
                        "dragon_light": "dragão pequena", "dragon_medium": "dragão média",
                        "dragon_heavy": "dragão grande"}.get(unit.archetype.value,
                                                       unit.archetype.value)
                unit_name = f"Tropa {size}"
            else:
                unit_name = uid
            if previous is None or current is None:
                verb = "entrou em campo" if previous is None else "saiu de campo"
                log(state, f"[STATE] {source}: {unit_name} ({p.name}) {verb}.")
                continue
            labels = ("Vida", "Vida máxima", "Casa", "Movimentos usados",
                      "Movimentos permitidos", "Ataques usados", "Ataques permitidos",
                      "Dano dobrado", "Resistências")
            changes = []
            for i, label in enumerate(labels):
                if previous[i] == current[i]:
                    continue
                old_value, new_value = previous[i], current[i]
                if i == 2:
                    old_value = house_short(state, old_value)
                    new_value = house_short(state, new_value)
                changes.append(f"{label} {old_value} → {new_value}")
            old_status, new_status = dict(previous[9]), dict(current[9])
            status_names = {
                "summoned_turn": "invocada no turno",
                "barba_hero_mode_turn": "combate como herói no turno",
                "mar_chamas_queued_turn": "Mar de Chamas preparado no turno",
                "mar_chamas_cooldown_until_turn": "Mar de Chamas em recarga até o turno",
                "lobisomem_until_turn": "lobisomem até o turno",
                "invisivel_until_turn": "invisível até o turno",
                "invulneravel_until_turn": "invulnerável até o turno",
                "rogue_items": "itens de Rogue Devil",
            }
            for status in sorted(old_status.keys() | new_status.keys()):
                if old_status.get(status) != new_status.get(status):
                    label = status_names.get(status, status.replace("_", " "))
                    changes.append(f"{label}: {old_status.get(status, 'não')} → "
                                   f"{new_status.get(status, 'não')}")
            if changes:
                log(state, f"[STATE] {source}: {unit_name} ({p.name}) — "
                           + "; ".join(changes) + ".")


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
            before_state = _visible_state_snapshot(state)
            before_log = len(state.event_log)
            result = handle_action(state, pid, choice)
            _log_visible_state_changes(state, before_state, f"ação de {player.name}",
                                       state.event_log[before_log:])
            for line in state.event_log[before_log:]:
                console.print(f"  [cyan]{line}[/cyan]")
            if result is not None:
                return result
        except (ActionError, CombatError, ValueError) as e:
            console.print(f"[red]Erro: {e}[/red]")
        console.print()


from .core.night_rules import find_targets

def prompt_attack(state, unit, targets) -> Attack | None:
    if unit.statuses.get("cannot_attack_on_turn") == state.turn:
        console.print(f"  [yellow]{unit.id} nao pode atacar (Espoliou com Arken).[/yellow]")
        return None
    console.print(f"  [cyan]{unit.id}[/cyan] (vida {unit.life}) em {house_short(state, unit.house)}")
    forced = peoples.demon_mind_pact_active(state, unit.owner_id) and bool(targets)
    options = [t[2] for t in targets] if forced else ["Nao atacar"] + [t[2] for t in targets]
    idx = pick_index("Acao", options)
    if not forced and idx == 0:
        return None
    target_idx = idx if forced else idx - 1
    return Attack(unit.id, targets[target_idx][0], targets[target_idx][1])

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
    from .core.night_rules import teleport_ainai
    teleport_ainai(state, player, destino)
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
        from .core.night_rules import return_luna
        return_luna(state, player)
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


from .core.night_rules import order_players_for_house as _order_players_for_house



def _mostrar_resumo_local(state, house: str) -> None:
    console.print(f"\n[bold cyan]=== {house_short(state, house)} ===[/bold cyan]")
    if house.startswith("city_"):
        pid = int(house.split("_")[1])
        p = get_player(state, pid)
        console.print(f"Cidade: {p.city.life}/{p.city.life_max}")
    any_unit = False
    for p in state.players:
        for u in p.units:
            if u.house != house or not u.is_alive():
                continue
            any_unit = True
            tipo = (f"Heroi {heroes.hero_name(u.hero_id)}"
                    if isinstance(u, Hero) else _troop_display(u.archetype))
            syms = _unit_symbols(state, u)
            syms_str = f" {syms}" if syms else ""
            console.print(f"  {p.name}: {u.id} ({tipo}) {u.life}/{u.life_max}{syms_str}")
    if not any_unit:
        console.print("  [dim](vazio)[/dim]")
    show_map(state)
    console.print()


def _resolver_qd_pendente(state) -> None:
    """Se algum jogador tem Q_D pendente, resolver agora."""
    for p in state.players:
        pend = p.pending_artifact_choice
        if pend and pend.get("kind") == "Q_D":
            try:
                _resolve_pending_choice_if_any(state, p.id)
            except Exception as e:
                console.print(f"[red]Erro Q_D: {e}[/red]")


def _night_info_prompt(state) -> None:
    while True:
        opt = Prompt.ask("Noite: [m]apa / [p]anorama / [Enter] continuar", default="")
        if opt.lower() == "m":
            show_map(state)
        elif opt.lower() == "p":
            show_board(state)
        else:
            return


def _declarar_casa(state, house: str, pids_declaram: list[int],
                   processed_houses=None, allow_luide: bool = True) -> None:
    if processed_houses is None:
        processed_houses = set()
    has_combat = any(
        find_targets(state, unit)
        for pid in pids_declaram
        for unit in get_player(state, pid).units
        if unit.house == house and unit.is_alive()
    )
    has_luide_window = allow_luide and any(
        peoples.has_luide_bonus(get_player(state, pid))
        and any(u.house == house and u.is_alive() for u in get_player(state, pid).units)
        for pid in pids_declaram)
    if not has_combat and not has_luide_window:
        console.print(f"[dim]Não havia combates a declarar em {house_short(state, house)}.[/dim]")
        return
    for pid in pids_declaram:
        player = get_player(state, pid)
        units_here = [u for u in player.units if u.house == house and u.is_alive()]
        if not units_here:
            continue
        if (not any(find_targets(state, u) for u in units_here)
                and not (allow_luide and peoples.has_luide_bonus(player))):
            continue
        _night_info_prompt(state)
        if allow_luide:
            _luide_janela_noturna(state, pid, house, processed_houses)
        _mostrar_resumo_local(state, house)
        console.print(f"[bold]{player.name} declara ataques em {house_short(state, house)}.[/bold]")
        for unit in list(units_here):
            if not unit.is_alive() or unit.house != house:
                continue
            while True:
                if not unit.is_alive() or unit.house != house:
                    break
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
                _resolver_qd_pendente(state)
        console.print()


def _luide_janela_noturna(state, pid: int, house: str, processed_houses=None) -> None:
    """Janela de Luide na vez dos Vampiros declararem neste local."""
    if processed_houses is None:
        processed_houses = set()
    player = get_player(state, pid)
    while peoples.has_luide_bonus(player):
        disponiveis = [u for u in player.units
                       if u.is_alive() and u.house == house
                       and u.moves_this_turn < u.max_moves_this_turn]
        opts = []
        if disponiveis:
            opts.append("Mover unidade")
        if not player.has_cast_spell_this_turn:
            opts.append("Lancar feitico")
        opts.append("(declarar ataques)")
        idx = pick_index(f"{player.name} (Luide Vampa)", opts)
        escolha = opts[idx]
        if escolha == "(declarar ataques)":
            break
        if escolha == "Mover unidade":
            labels = [f"{u.id} ({house_short(state, u.house)}, {u.life})"
                      for u in disponiveis]
            u = disponiveis[pick_index("Unidade", labels)]
            dests = valid_destinations(state, u)
            if not dests:
                console.print("[red]Sem destinos.[/red]")
                continue
            labels2 = [house_short(state, d) for d in dests] + ["Cancelar"]
            idx2 = pick_index("Destino", labels2)
            if idx2 == len(dests):
                continue
            destino = dests[idx2]
            try:
                move_unit(state, pid, u.id, destino)
                console.print("[green]Movido.[/green]")
            except ActionError as e:
                console.print(f"[red]{e}[/red]")
                continue
            if destino in processed_houses:
                console.print(f"[cyan]{u.id} entrou em casa ja processada. Declara agora.[/cyan]")
                _declarar_casa(state, destino, [pid], processed_houses,
                               allow_luide=False)
        elif escolha == "Lancar feitico":
            try:
                living = [u for u in player.units if u.is_alive()]
                if not living:
                    raise ActionError("Sem unidades.")
                labels = [f"{u.id} ({u.life}/{u.life_max})" for u in living]
                choice_data = {"unit_id": living[pick_index("Alvo", labels)].id}
                cast_spell(state, pid, choice_data)
                console.print("[green]Feitico lancado.[/green]")
            except (ActionError, ValueError) as e:
                console.print(f"[red]{e}[/red]")


def _ainai_prompt_all(state, all_pids, processed_houses=None):  # v5v10g ainai
    """v5v10g: se Ainai teleporta para casa já processada, reabre e declara."""
    if processed_houses is None:
        processed_houses = set()
    for pid in all_pids:
        player = get_player(state, pid)
        if not player.units:
            continue
        ainai_before = next((u for u in player.units
                             if isinstance(u, Hero) and u.is_alive()
                             and u.hero_id == "ainai"), None)
        house_before = ainai_before.house if ainai_before else None
        try:
            _try_ainai_teleport(state, player)
        except Exception as e:
            console.print(f"[red]Erro Ainai: {e}[/red]")
            continue
        ainai_after = next((u for u in player.units
                            if isinstance(u, Hero) and u.is_alive()
                            and u.hero_id == "ainai"), None)
        if ainai_after is None:
            continue
        house_after = ainai_after.house
        if house_before != house_after and house_after in processed_houses:
            console.print("[cyan]Ainai entrou em casa já processada. "
                          "Declara agora.[/cyan]")
            try:
                _declarar_casa(state, house_after, [pid])
            except Exception as e:
                console.print(f"[red]Erro declaração Ainai: {e}[/red]")
def run_night_phase(state) -> None:
    console.rule("[bold]NOITE[/bold]")
    show_hud(state)
    show_map(state)
    _ask_vovo_position(state)

    all_pids = list(day_order(state))
    barba_resolver_mar_de_chamas(state)
    for pid in all_pids:
        player = get_player(state, pid)
        if any(isinstance(u, Hero) and u.is_alive() and u.hero_id == "aiquara"
               and u.statuses.get("aiquara_attacked_turn") != state.turn for u in player.units):
            try:
                _aiquara_ui(state, pid)
                _resolver_qd_pendente(state)
            except (ActionError, CombatError) as exc:
                console.print(f"[yellow]Aiquara: {exc}[/yellow]")
    for pid in all_pids:
        player = get_player(state, pid)
        _try_luna_return(state, player)

    _ainai_prompt_all(state, all_pids)

    for pid in all_pids:
        player = get_player(state, pid)
        if player.units:
            _try_besouro_mandinga(state, player)

    day = day_order(state)
    city_order = list(reversed(day))
    house_order = [CENTER] + [f"city_{pid}" for pid in city_order]
    processed_houses = set()

    for house in house_order:
        pids_here = []
        for pid in all_pids:
            player = get_player(state, pid)
            if any(u.house == house and u.is_alive() for u in player.units):
                pids_here.append(pid)
        if not pids_here:
            console.print(f"[dim]Não havia combates a declarar em {house_short(state, house)}.[/dim]")
            processed_houses.add(house)
            continue
        pids_here = _order_players_for_house(state, pids_here, house)
        if house == CENTER:
            console.rule("[bold]Combate no Centro iniciado[/bold]")
        else:
            owner = get_player(state, int(house.split("_")[1]))
            console.rule(f"[bold]Combate na Cidade de {owner.people} — {owner.name} (Jogador {owner.id})[/bold]")
        order = " -> ".join(f"{get_player(state, pid).name} (J{pid})" for pid in pids_here)
        console.print(f"[cyan]Ordem das declarações de combate: {order}[/cyan]")
        _declarar_casa(state, house, pids_here, processed_houses)
        processed_houses.add(house)
        _ainai_prompt_all(state, all_pids, processed_houses)

    _ainai_prompt_all(state, all_pids, processed_houses)

    for pid in all_pids:
        player = get_player(state, pid)
        rogue = next((u for u in player.units if isinstance(u, Hero) and u.is_alive()
                      and u.hero_id == "rogue_devil"
                      and "relogio" in u.statuses.get("rogue_items", [])), None)
        if (rogue is not None and state.combats_this_night
                and Prompt.ask(f"{player.name}: usar Relógio de bolso?",
                               choices=["s", "n"], default="n") == "s"):
            houses = list(state.combats_this_night)
            destination = houses[pick_index(
                "Destino", [house_short(state, h) for h in houses])]
            rogue_clock_move(state, pid, destination)

def show_victory(state) -> None:
    if state.winner_id:
        player = get_player(state, state.winner_id)
        console.print()
        console.print(Panel.fit(
            f"[bold green]VITORIA![/bold green]\n\n{player.name} ({player.people}) venceu!",
            border_style="green"))
    else:
        console.print(Panel.fit("[bold red]Empate![/bold red]", border_style="red"))


def _run_one_game(state=None, narrative_mode="desligada", checkpoint=None) -> None:
    console.clear()
    state = setup_ui() if state is None else state
    def save_boundary():
        if checkpoint:
            try:
                write_checkpoint(state, checkpoint)
            except (OSError, ValueError) as error:
                console.print(f"Checkpoint não salvo: {error}", markup=False)
    if not state.game_over:
        narrate(console, state, "match_started", narrative_mode)
        save_boundary()
    while not state.game_over:
        before_turn = _visible_state_snapshot(state)
        interest = start_turn(state)
        _log_visible_state_changes(state, before_turn, "início do turno")
        console.rule(f"[bold yellow]TURNO {state.turn} - DIA[/bold yellow]")
        curuna = get_player(state, state.curuna_id)
        console.print(f"[bold yellow]* Curuna: {curuna.name}[/bold yellow]\n")
        narrate(console, state, "turn_started", narrative_mode)
        _gnomos_bets_inicio_turno(state)
        if interest or state.morning_gains:
            by_pid: dict[int, list[dict]] = {}
            for g in state.morning_gains:
                by_pid.setdefault(g["pid"], []).append(g)
            console.print("[yellow]Prosperidade:[/yellow]")
            for p in state.players:
                if p.id not in by_pid:
                    continue
                parts = []
                for g in by_pid[p.id]:
                    kind = g.get("kind", "?")
                    bits = []
                    if g.get("gold"):
                        bits.append(f"+{g['gold']} Ouro")
                    if g.get("magic"):
                        bits.append(f"+{g['magic']} Magia")
                    if g.get("life"):
                        bits.append(f"+{g['life']} Vida")
                    if bits:
                        parts.append(f"{' '.join(bits)} ({kind})")
                if parts:
                    console.print(f"  {p.name}: {'; '.join(parts)}")
            console.print()
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
            state.active_player_id = pid
            player = get_player(state, pid)
            snapshots[pid] = state_to_dict(state)
            console.rule(f"[bold]Vez de {player.name}[/bold]")
            before = len(state.event_log)
            before_morning = _visible_state_snapshot(state)
            start_player_day(state, pid)
            _log_visible_state_changes(state, before_morning, f"manhã de {player.name}",
                                       state.event_log[before:])
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
            if not state.game_over:
                narrate(console, state, "player_turn_ended", narrative_mode, pid,
                        day_players[i + 1] if i + 1 < len(day_players) else None)
            i += 1
        state.active_player_id = None
        end_day(state)
        night_skipped = [p.name for p in state.players
                         if p.city.is_alive() and p.skip_night_turn == state.turn]
        if night_skipped:
            console.print(f"[yellow]Pulados na Noite: {', '.join(night_skipped)}[/yellow]\n")
        before_night = _visible_state_snapshot(state)
        run_night_phase(state)
        _log_visible_state_changes(state, before_night, "fase da Noite")
        if state.game_over:
            break
        end_turn(state)
        if not state.game_over:
            save_boundary()
            console.input("\n[dim]Enter...[/dim] ")
            console.clear()
    show_victory(state)
    narrate(console, state, "match_ended", narrative_mode)
    save_boundary()


def main(argv=None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Jéssica — terminal")
    parser.add_argument("--narrativa", choices=["desligada", "breve"], default="desligada")
    parser.add_argument("--salvar", metavar="ARQUIVO", help="Checkpoint automático entre turnos completos")
    parser.add_argument("--carregar", metavar="ARQUIVO", help="Retomar um checkpoint do terminal")
    options = parser.parse_args(argv)
    loaded = None
    if options.carregar:
        try:
            loaded = read_checkpoint(options.carregar)
        except (OSError, ValueError) as error:
            parser.error(str(error))
    _combat_mod.set_armor_choice_fn(_armor_choice_prompt)
    while True:
        try:
            _run_one_game(loaded, options.narrativa, options.salvar)
            loaded = None
        except RestartGame:
            loaded = None
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
