import threading
from enum import IntEnum
from dataclasses import dataclass
from typing import Dict, List, Any

VERSION = "3.2.0"
LIMBUS_NAME = "LimbusCompany"

SELECTED = ["YISANG", "DONQUIXOTE" , "ISHMAEL", "RODION", "SINCLAIR", "GREGOR"]
GIFTS = []
TEAM = ["BURN"]
NAME_ORDER = 0
DUPLICATES = False

BONUS = False
RESTART = True
ALTF4 = False
ALTF4_lux = False
NETZACH = False
SKIP = True
WINRATE = False
WISHMAKING = False
BUFF = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
CARD = [1, 0, 2, 3, 4]
KEYWORDLESS = {}
HARD = False
EXTREME = False
APP = None

PICK = {}
IGNORE = {}
PICK_ALL = {}

WARNING = None
WINDOW = (0, 0, 1920, 1080)
SCREEN = None

pause_event = threading.Event()
stop_event = threading.Event()

LVL = 1
SUPER = "shop" # for Hard MD
DEAD = 0
IDX = 0
TO_UPTIE = {}
MOVE_ANIMATION = False


class GameMode(IntEnum):
    NORMAL = 0
    HARD = 1
    EXTREME = 2

@dataclass(frozen=True)
class BotConfig:
    game_mode: GameMode
    auto_restart: bool
    convert_enkephalin: bool
    
    target_teams: Dict[str, Any]
    
    card_priority: List[int]
    buff_priority: List[int]