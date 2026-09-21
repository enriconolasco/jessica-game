"""apply_update_v5b1: bug fixes do playtest + Sao Tome completo + estado.

Escopo:
- H1: unidade invocada nao move no mesmo turno.
- H4: retaliacao aplica executar/cura vampiro/hooks de kill.
- H7: Fadas ganham artefato so quando o HEROI mata.
- H8: Ga'Roche mantem vida maxima apos morrer.
- H10: Miyamoto +1 ataque (Ks dobra, nao soma).
- A1: Sao Tome herda passivas continuas dos alvos das apostas.
- Modelos: garoche_life_max_bonus, armor_active_until_turn,
           fae_fallen_this_turn, killed_by_unit_id.
"""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = ROOT / "backups" / f"v5b1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

FILES: dict[str, str] = {}

# =============================================================
# constants.py - nada novo por enquanto
# =============================================================

# =============================================================
# models.py - campos novos
# =============================================================
FILES["jessica/core/models.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .constants import Phase, TroopArchetype
from .artifacts import Shop
from .rng import DeterministicRNG


@dataclass
class City:
    owner_id: int
    life: int
    life_max: int
    gold: int = 0
    magic: int = 0
    has_monument: bool = False

    def is_alive(self) -> bool:
        return self.life > 0


@dataclass
class Unit:
    id: str
    owner_id: int
    house: str
    life: int
    life_max: int
    has_moved_this_turn: bool = False
    double_damage: bool = False
    resistance_stacks: int = 0
    attacks_made_this_night: int = 0
    max_attacks_this_night: int = 1
    attacks_made_this_day: int = 0
    max_attacks_this_day: int = 0
    hero_can_attack_city: bool = False
    killed_by_player_id: Optional[int] = None
    killed_by_unit_id: Optional[str] = None
    original_owner_id: Optional[int] = None
    statuses: dict = field(default_factory=dict)
    moves_this_turn: int = 0
    max_moves_this_turn: int = 1
    infectado: bool = False
    bloqueado_mover_proximo: bool = False

    def is_alive(self) -> bool:
        return self.life > 0


@dataclass
class Hero(Unit):
    hero_id: str = ""


@dataclass
class Troop(Unit):
    archetype: TroopArchetype = TroopArchetype.LIGHT


@dataclass
class ArtifactOnField:
    card_id: str
    owner_id: int
    extra: dict = field(default_factory=dict)


@dataclass
class Player:
    id: int
    name: str
    people: str
    city: City
    chosen_hero_id: Optional[str] = None
    spell_cooldown_until_turn: int = 0
    has_collected_this_turn: bool = False
    has_cast_spell_this_turn: bool = False
    morning_done_this_turn: bool = False
    has_played_day_this_turn: bool = False
    artifacts_bought_gold_today: int = 0
    artifacts_bought_magic_today: int = 0
    pending_heals: int = 0
    hand: list[str] = field(default_factory=list)
    field_artifacts: list[ArtifactOnField] = field(default_factory=list)
    units: list[Unit] = field(default_factory=list)
    arken_espolia_used_turn: int = -1
    vovo_position: int = 1
    sonho_lucido_used_turn: int = -1
    sonho_lucido_pending_turn: int = -1
    sonho_lucido_multi_turn: int = -1
    vender_por_magia_turn: int = -1
    andar_duas_vezes_turn: int = -1
    bater_primeiro_turn: int = -1
    pena_added_once: bool = False
    besouro_mandinga_used_turn: int = -1
    carocos_gerados: int = 0
    empalados: list[str] = field(default_factory=list)
    infectados: list[dict] = field(default_factory=list)

    # Filhos da Floresta
    filhos_bonus_recebido: bool = False
    baoba_pagamentos: int = 0
    baoba_invocado: bool = False

    # Gnomos e Duendes
    bet_H_target: Optional[int] = None
    bet_C_target: Optional[int] = None
    bet_D_target: Optional[int] = None
    bet_S_target: Optional[int] = None
    correct_bets: int = 0
    zebum_herois: list[str] = field(default_factory=list)
    spell_copia_id: Optional[str] = None
    spell_copia_turn: int = -1
    bets_need_realocacao: bool = False

    # Orcs
    garoche_life_max_bonus: int = 0

    double_damage_until_end_night: bool = False
    invulnerable_until_end_turn: bool = False
    no_city_attacks_until_end_turn: bool = False
    armor_gold_cap_per_hit: int = 0
    armor_active_until_turn: int = -1

    skip_day_turn: Optional[int] = None
    skip_night_turn: Optional[int] = None

    pending_artifact_choice: Optional[dict] = None


@dataclass
class GameState:
    seed: int
    rng: DeterministicRNG = field(default_factory=lambda: DeterministicRNG(0))
    players: list[Player] = field(default_factory=list)
    turn_order: list[int] = field(default_factory=list)
    shop: Shop = field(default_factory=Shop)
    turn: int = 1
    phase: Phase = Phase.DAY
    curuna_id: int = 1
    event_log: list[str] = field(default_factory=list)
    action_log: list[dict] = field(default_factory=list)
    game_over: bool = False
    winner_id: Optional[int] = None
    pending_effects: list[dict] = field(default_factory=list)
    deaths_this_night: list[str] = field(default_factory=list)
    dain_kills: list[dict] = field(default_factory=list)
    espectros_pendentes: list[dict] = field(default_factory=list)
    lobisomens_transformados: list[dict] = field(default_factory=list)
    fae_fallen_this_turn: list[tuple[int, str]] = field(default_factory=list)

    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.city.is_alive()]

    def player(self, pid: int) -> Player:
        for p in self.players:
            if p.id == pid:
                return p
        raise ValueError(f"Jogador {pid} nao encontrado")
'''

# =============================================================
# serialize.py - persistir os campos novos
# =============================================================
FILES["jessica/core/serialize.py"] = '''\
from __future__ import annotations
import json
from .models import City, Player, Unit, Hero, Troop, GameState, ArtifactOnField
from .artifacts import Shop
from .rng import DeterministicRNG
from .constants import Phase, TroopArchetype


def city_to_dict(c: City) -> dict:
    return {"owner_id": c.owner_id, "life": c.life, "life_max": c.life_max,
            "gold": c.gold, "magic": c.magic, "has_monument": c.has_monument}


def city_from_dict(d: dict) -> City:
    return City(owner_id=d["owner_id"], life=d["life"], life_max=d["life_max"],
                gold=d["gold"], magic=d["magic"], has_monument=d["has_monument"])


def unit_to_dict(u: Unit) -> dict:
    kind = "hero" if isinstance(u, Hero) else "troop"
    d = {"kind": kind, "id": u.id, "owner_id": u.owner_id, "house": u.house,
         "life": u.life, "life_max": u.life_max,
         "has_moved_this_turn": u.has_moved_this_turn,
         "double_damage": u.double_damage,
         "resistance_stacks": u.resistance_stacks,
         "attacks_made_this_night": u.attacks_made_this_night,
         "max_attacks_this_night": u.max_attacks_this_night,
         "attacks_made_this_day": u.attacks_made_this_day,
         "max_attacks_this_day": u.max_attacks_this_day,
         "hero_can_attack_city": u.hero_can_attack_city,
         "killed_by_player_id": u.killed_by_player_id,
         "killed_by_unit_id": u.killed_by_unit_id,
         "original_owner_id": u.original_owner_id,
         "statuses": dict(u.statuses),
         "moves_this_turn": u.moves_this_turn,
         "max_moves_this_turn": u.max_moves_this_turn,
         "infectado": u.infectado,
         "bloqueado_mover_proximo": u.bloqueado_mover_proximo}
    if kind == "hero":
        d["hero_id"] = u.hero_id
    else:
        d["archetype"] = u.archetype.value
    return d


def unit_from_dict(d: dict) -> Unit:
    common = dict(id=d["id"], owner_id=d["owner_id"], house=d["house"],
                  life=d["life"], life_max=d["life_max"],
                  has_moved_this_turn=d["has_moved_this_turn"],
                  double_damage=d.get("double_damage", False),
                  resistance_stacks=d.get("resistance_stacks", 0),
                  attacks_made_this_night=d.get("attacks_made_this_night", 0),
                  max_attacks_this_night=d.get("max_attacks_this_night", 1),
                  attacks_made_this_day=d.get("attacks_made_this_day", 0),
                  max_attacks_this_day=d.get("max_attacks_this_day", 0),
                  hero_can_attack_city=d.get("hero_can_attack_city", False),
                  killed_by_player_id=d.get("killed_by_player_id", None),
                  killed_by_unit_id=d.get("killed_by_unit_id", None),
                  original_owner_id=d.get("original_owner_id", None),
                  statuses=dict(d.get("statuses", {})),
                  moves_this_turn=d.get("moves_this_turn", 0),
                  max_moves_this_turn=d.get("max_moves_this_turn", 1),
                  infectado=d.get("infectado", False),
                  bloqueado_mover_proximo=d.get("bloqueado_mover_proximo", False))
    if d["kind"] == "hero":
        return Hero(**common, hero_id=d["hero_id"])
    return Troop(**common, archetype=TroopArchetype(d["archetype"]))


def artifact_on_field_to_dict(a: ArtifactOnField) -> dict:
    return {"card_id": a.card_id, "owner_id": a.owner_id, "extra": dict(a.extra)}


def artifact_on_field_from_dict(d: dict) -> ArtifactOnField:
    return ArtifactOnField(card_id=d["card_id"], owner_id=d["owner_id"],
                           extra=dict(d.get("extra", {})))


def player_to_dict(p: Player) -> dict:
    return {
        "id": p.id, "name": p.name, "people": p.people,
        "chosen_hero_id": p.chosen_hero_id,
        "spell_cooldown_until_turn": p.spell_cooldown_until_turn,
        "has_collected_this_turn": p.has_collected_this_turn,
        "has_cast_spell_this_turn": p.has_cast_spell_this_turn,
        "morning_done_this_turn": p.morning_done_this_turn,
        "has_played_day_this_turn": p.has_played_day_this_turn,
        "artifacts_bought_gold_today": p.artifacts_bought_gold_today,
        "artifacts_bought_magic_today": p.artifacts_bought_magic_today,
        "pending_heals": p.pending_heals,
        "arken_espolia_used_turn": p.arken_espolia_used_turn,
        "vovo_position": p.vovo_position,
        "sonho_lucido_used_turn": p.sonho_lucido_used_turn,
        "sonho_lucido_pending_turn": p.sonho_lucido_pending_turn,
        "sonho_lucido_multi_turn": p.sonho_lucido_multi_turn,
        "vender_por_magia_turn": p.vender_por_magia_turn,
        "andar_duas_vezes_turn": p.andar_duas_vezes_turn,
        "bater_primeiro_turn": p.bater_primeiro_turn,
        "pena_added_once": p.pena_added_once,
        "besouro_mandinga_used_turn": p.besouro_mandinga_used_turn,
        "carocos_gerados": p.carocos_gerados,
        "empalados": list(p.empalados),
        "infectados": [dict(e) for e in p.infectados],
        "filhos_bonus_recebido": p.filhos_bonus_recebido,
        "baoba_pagamentos": p.baoba_pagamentos,
        "baoba_invocado": p.baoba_invocado,
        "bet_H_target": p.bet_H_target,
        "bet_C_target": p.bet_C_target,
        "bet_D_target": p.bet_D_target,
        "bet_S_target": p.bet_S_target,
        "correct_bets": p.correct_bets,
        "zebum_herois": list(p.zebum_herois),
        "spell_copia_id": p.spell_copia_id,
        "spell_copia_turn": p.spell_copia_turn,
        "bets_need_realocacao": p.bets_need_realocacao,
        "garoche_life_max_bonus": p.garoche_life_max_bonus,
        "hand": list(p.hand),
        "field_artifacts": [artifact_on_field_to_dict(a) for a in p.field_artifacts],
        "units": [unit_to_dict(u) for u in p.units],
        "city": city_to_dict(p.city),
        "double_damage_until_end_night": p.double_damage_until_end_night,
        "invulnerable_until_end_turn": p.invulnerable_until_end_turn,
        "no_city_attacks_until_end_turn": p.no_city_attacks_until_end_turn,
        "armor_gold_cap_per_hit": p.armor_gold_cap_per_hit,
        "armor_active_until_turn": p.armor_active_until_turn,
        "pending_artifact_choice": p.pending_artifact_choice,
        "skip_day_turn": p.skip_day_turn,
        "skip_night_turn": p.skip_night_turn,
    }


def player_from_dict(d: dict) -> Player:
    return Player(
        id=d["id"], name=d["name"], people=d["people"],
        chosen_hero_id=d["chosen_hero_id"],
        spell_cooldown_until_turn=d.get("spell_cooldown_until_turn", 0),
        has_collected_this_turn=d["has_collected_this_turn"],
        has_cast_spell_this_turn=d["has_cast_spell_this_turn"],
        morning_done_this_turn=d.get("morning_done_this_turn", False),
        has_played_day_this_turn=d.get("has_played_day_this_turn", False),
        artifacts_bought_gold_today=d["artifacts_bought_gold_today"],
        artifacts_bought_magic_today=d["artifacts_bought_magic_today"],
        pending_heals=d.get("pending_heals", 0),
        arken_espolia_used_turn=d.get("arken_espolia_used_turn", -1),
        vovo_position=d.get("vovo_position", 1),
        sonho_lucido_used_turn=d.get("sonho_lucido_used_turn", -1),
        sonho_lucido_pending_turn=d.get("sonho_lucido_pending_turn", -1),
        sonho_lucido_multi_turn=d.get("sonho_lucido_multi_turn", -1),
        vender_por_magia_turn=d.get("vender_por_magia_turn", -1),
        andar_duas_vezes_turn=d.get("andar_duas_vezes_turn", -1),
        bater_primeiro_turn=d.get("bater_primeiro_turn", -1),
        pena_added_once=d.get("pena_added_once", False),
        besouro_mandinga_used_turn=d.get("besouro_mandinga_used_turn", -1),
        carocos_gerados=d.get("carocos_gerados", 0),
        empalados=list(d.get("empalados", [])),
        infectados=[dict(e) for e in d.get("infectados", [])],
        filhos_bonus_recebido=d.get("filhos_bonus_recebido", False),
        baoba_pagamentos=d.get("baoba_pagamentos", 0),
        baoba_invocado=d.get("baoba_invocado", False),
        bet_H_target=d.get("bet_H_target", None),
        bet_C_target=d.get("bet_C_target", None),
        bet_D_target=d.get("bet_D_target", None),
        bet_S_target=d.get("bet_S_target", None),
        correct_bets=d.get("correct_bets", 0),
        zebum_herois=list(d.get("zebum_herois", [])),
        spell_copia_id=d.get("spell_copia_id", None),
        spell_copia_turn=d.get("spell_copia_turn", -1),
        bets_need_realocacao=d.get("bets_need_realocacao", False),
        garoche_life_max_bonus=d.get("garoche_life_max_bonus", 0),
        hand=list(d["hand"]),
        field_artifacts=[artifact_on_field_from_dict(a) for a in d.get("field_artifacts", [])],
        units=[unit_from_dict(u) for u in d["units"]],
        city=city_from_dict(d["city"]),
        double_damage_until_end_night=d.get("double_damage_until_end_night", False),
        invulnerable_until_end_turn=d.get("invulnerable_until_end_turn", False),
        no_city_attacks_until_end_turn=d.get("no_city_attacks_until_end_turn", False),
        armor_gold_cap_per_hit=d.get("armor_gold_cap_per_hit", 0),
        armor_active_until_turn=d.get("armor_active_until_turn", -1),
        pending_artifact_choice=d.get("pending_artifact_choice", None),
        skip_day_turn=d.get("skip_day_turn", None),
        skip_night_turn=d.get("skip_night_turn", None),
    )


def state_to_dict(s: GameState) -> dict:
    return {"seed": s.seed, "rng": s.rng.to_dict(),
            "players": [player_to_dict(p) for p in s.players],
            "turn_order": list(s.turn_order),
            "shop": {"deck": list(s.shop.deck)},
            "turn": s.turn, "phase": s.phase.value,
            "curuna_id": s.curuna_id,
            "event_log": list(s.event_log),
            "action_log": list(s.action_log),
            "game_over": s.game_over, "winner_id": s.winner_id,
            "pending_effects": [dict(e) for e in s.pending_effects],
            "deaths_this_night": list(s.deaths_this_night),
            "dain_kills": [dict(e) for e in s.dain_kills],
            "espectros_pendentes": [dict(e) for e in s.espectros_pendentes],
            "lobisomens_transformados": [dict(e) for e in s.lobisomens_transformados],
            "fae_fallen_this_turn": [list(t) for t in s.fae_fallen_this_turn]}


def state_from_dict(d: dict) -> GameState:
    state = GameState(seed=d["seed"], rng=DeterministicRNG.from_dict(d["rng"]))
    state.players = [player_from_dict(p) for p in d["players"]]
    state.turn_order = list(d["turn_order"])
    state.shop = Shop(deck=list(d["shop"]["deck"]))
    state.turn = d["turn"]
    state.phase = Phase(d["phase"])
    state.curuna_id = d["curuna_id"]
    state.event_log = list(d["event_log"])
    state.action_log = list(d["action_log"])
    state.game_over = d["game_over"]
    state.winner_id = d["winner_id"]
    state.pending_effects = [dict(e) for e in d.get("pending_effects", [])]
    state.deaths_this_night = list(d.get("deaths_this_night", []))
    state.dain_kills = [dict(e) for e in d.get("dain_kills", [])]
    state.espectros_pendentes = [dict(e) for e in d.get("espectros_pendentes", [])]
    state.lobisomens_transformados = [dict(e) for e in d.get("lobisomens_transformados", [])]
    state.fae_fallen_this_turn = [tuple(t) for t in d.get("fae_fallen_this_turn", [])]
    return state


def save_to_file(state: GameState, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state_to_dict(state), f, ensure_ascii=False, indent=2)


def load_from_file(path: str) -> GameState:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return state_from_dict(data)
'''

# =============================================================
# setup.py - Filhos 1 vida inicial
# =============================================================
FILES["jessica/core/setup.py"] = '''\
from __future__ import annotations
from dataclasses import dataclass
from .constants import (
    DEFAULT_CITY_LIFE_START, DEFAULT_CITY_LIFE_MAX,
    DEFAULT_STARTING_GOLD, DEFAULT_STARTING_MAGIC,
)
from .state import make_rng, create_empty_state, get_player, log
from .models import GameState
from .rng import DeterministicRNG
from . import heroes


FILHOS_PEOPLE = "filhos_floresta"


@dataclass
class SetupResult:
    turn_order: list[int]
    banned_peoples: list[str]
    chosen_peoples: dict[int, str]
    chosen_heroes: dict[int, str]


def roll_d20_order(rng: DeterministicRNG, num_players: int) -> list[int]:
    rolls: dict[int, int] = {i + 1: rng.randint(1, 20) for i in range(num_players)}
    while True:
        by_value: dict[int, list[int]] = {}
        for pid, val in rolls.items():
            by_value.setdefault(val, []).append(pid)
        tied_groups = [pids for pids in by_value.values() if len(pids) > 1]
        if not tied_groups:
            break
        for group in tied_groups:
            for pid in group:
                rolls[pid] = rng.randint(1, 20)
    ordered = sorted(rolls.items(), key=lambda kv: kv[1], reverse=True)
    return [pid for pid, _ in ordered]


def horario_from(order: list[int]) -> list[int]:
    if not order:
        return []
    return [order[0]] + list(reversed(order[1:]))


def run_setup(
    all_peoples: list[str],
    heroes_by_people: dict[str, list[str]],
    choices: dict[int, dict],
    seed: int,
    num_players: int = 4,
    turn_order: list[int] | None = None,
    city_life: int = DEFAULT_CITY_LIFE_START,
    city_life_max: int = DEFAULT_CITY_LIFE_MAX,
    gold_start: int = DEFAULT_STARTING_GOLD,
    magic_start: int = DEFAULT_STARTING_MAGIC,
) -> tuple[GameState, SetupResult]:
    rng = make_rng(seed)
    state = create_empty_state(
        num_players=num_players,
        city_life=city_life,
        city_life_max=city_life_max,
        seed=seed,
        gold_start=gold_start,
        magic_start=magic_start,
    )
    if turn_order is None:
        order = roll_d20_order(rng, num_players)
    else:
        order = list(turn_order)
    state.turn_order = order
    log(state, f"Ordem de turno (anti-horario): {order}")
    povo_order = horario_from(order)
    log(state, f"Ordem de povo (horario): {povo_order}")

    banned: list[str] = []
    reversed_order = list(reversed(order))
    for pid in reversed_order[:2]:
        if "ban" in choices[pid] and choices[pid]["ban"]:
            povo = choices[pid]["ban"]
            banned.append(povo)
            log(state, f"Jogador {pid} banou: {povo}")
    if banned:
        log(state, f"Povos disponiveis: {[p for p in all_peoples if p not in banned]}")
    else:
        log(state, "Nenhum povo banido.")

    chosen_peoples: dict[int, str] = {}
    for pid in povo_order:
        povo = choices[pid]["povo"]
        chosen_peoples[pid] = povo
        get_player(state, pid).people = povo
        log(state, f"Jogador {pid} escolheu: {povo}")

    chosen_heroes: dict[int, str] = {}
    for pid in povo_order:
        povo = choices[pid]["povo"]
        if povo == "mortos_vivos":
            chosen_heroes[pid] = ""
            get_player(state, pid).chosen_hero_id = None
            log(state, f"Jogador {pid} (Mortos-Vivos): escolha de heroi pulada.")
            continue
        raw_hero = choices[pid]["heroi"]
        canonical = heroes.resolve_hero_for_people(povo, raw_hero)
        chosen_heroes[pid] = canonical
        get_player(state, pid).chosen_hero_id = canonical
        log(state, f"Jogador {pid} escolheu heroi: {canonical}")

    # Filhos da Floresta: passiva Florescimento Exuberante (vida inicial 1)
    for pid in povo_order:
        if chosen_peoples[pid] == FILHOS_PEOPLE:
            p = get_player(state, pid)
            p.city.life = 1
            log(state, f"Jogador {pid} (Filhos): Florescimento Exuberante - vida inicial 1.")

    state.curuna_id = order[0]
    log(state, f"Curuna inicial: J{state.curuna_id}")

    return state, SetupResult(
        turn_order=order,
        banned_peoples=banned,
        chosen_peoples=chosen_peoples,
        chosen_heroes=chosen_heroes,
    )
'''

def main() -> None:
    print(f"Projeto em: {ROOT}")
    print(f"Backup em:  {BACKUP_DIR}\\n")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for rel_path, content in FILES.items():
        full = ROOT / rel_path
        if full.exists():
            backup_path = BACKUP_DIR / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full, backup_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        print(f"OK  - {rel_path}")
    print(f"\\n{len(FILES)} arquivos escritos.")
    print(f"Backup: {BACKUP_DIR}")


if __name__ == "__main__":
    main()