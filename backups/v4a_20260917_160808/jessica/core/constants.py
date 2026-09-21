from enum import Enum

DEFAULT_NUM_PLAYERS = 4
DEFAULT_CITY_LIFE_START = 2
DEFAULT_CITY_LIFE_MAX = 6
DEFAULT_STARTING_GOLD = 0
DEFAULT_STARTING_MAGIC = 0
DEFAULT_STARTING_TROOPS = 0
DEFAULT_STARTING_HERO_ALIVE = False
DEFAULT_STARTING_ARTIFACTS = 0
DEFAULT_SEED = 20260916

RESOURCES_PER_DAY = 2
GOLD_INTEREST_DIVISOR = 5
CITY_LIFE_COST_GOLD = 2
HERO_SUMMON_COST_MAGIC = 3
TROOP_SUMMON_COST_MAGIC = 1
TROOP_MAX_LIFE = {
    "light": 4,
    "medium": 6,
    "heavy": 8,
    "special": 5,
    "extra": 4,     # Orc: tropa extra (4º arquétipo exclusivo dos Orcs)
}
MONUMENT_COST_GOLD = 1
MONUMENT_BONUS_INTERVAL = 4

ARTIFACT_GOLD_COST = 6
ARTIFACT_MAGIC_COST = 6
ARTIFACT_SELL_GOLD = 7
ARTIFACT_MAX_BUYS_GOLD_PER_DAY = 1
ARTIFACT_MAX_BUYS_MAGIC_PER_DAY = 1
ARTIFACTS_PER_CARD_IN_SHOP = 2

CITY_HOUSES = ("city_1", "city_2", "city_3", "city_4")
CENTER = "center"
ALL_HOUSES = CITY_HOUSES + (CENTER,)

FIRST_TURN = 1
FIRST_CURUNA_ID = 1


class Phase(Enum):
    DAY = "day"
    NIGHT = "night"


class Resource(Enum):
    GOLD = "gold"
    MAGIC = "magic"


class TroopArchetype(Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SPECIAL = "special"
    EXTRA = "extra"      # Orc