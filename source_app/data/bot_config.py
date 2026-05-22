from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional
from enum import IntEnum


VERSION = "3.2.0"

class GameMode(IntEnum):
    NORMAL = 0
    HARD = 1
    EXTREME = 2

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class TeamSelection:
    sinners: Any
    duplicates: bool = False
    affinity_idx: int = 0
    affinity: Any = None
    priority: Optional[Tuple[Any, Any]] = None
    avoid: Optional[Tuple[Any, Any, Any]] = None


@dataclass(frozen=True)
class BotConfig:
    window_name: str
    
    md_run_count: int
    thread_lux_count: int
    exp_lux_count: int
    
    teams_selections: Dict[int, TeamSelection]
    
    difficulty: GameMode
    
    bonus_charge: bool
    restart_run: bool
    altf4: bool
    convert_enkephalin: bool
    skip_secret_nodes: bool
    shop_wishmaking: bool
    chained_winrate: bool
    
    starting_graces: List[Any]  
    card_priority: List[int]
    keywordless_gifts: Dict[str, int]