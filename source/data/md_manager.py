from dataclasses import dataclass
from typing import List, Dict, Any
from itertools import cycle

from .default_teams import TEAMS, HARD, SINNERS
from .packs_data import generate_packs_all, generate_packs_av, generate_packs_pr
from source_app.data.bot_config import GameMode, BotConfig


@dataclass(frozen=True)
class TeamConfig:
    difficulty: GameMode
    collect_bonus: bool
    graces: List[int]
    team_keywords: List[str]
    name_order: int
    check_duplicate_names: bool
    gifts: List[Dict[str, Any]]
    cards: List[int]
    sinners: List[str]
    skips: int
    prioritized_packs_filtered: Any
    avoided_packs: Any
    prioritized_packs_all: Any
    keywordless_gifts: Dict[str, int]


class DungeonManager:
    def __init__(self, config: BotConfig):
        self.config = config
        
        self.team_keys = [key for key in config.teams_selections.keys() if key < 7]
        self.rotator = cycle(self.team_keys) if self.team_keys else None
        
        self.total_runs = config.md_run_count
        self.current_run = 0

    def has_runs(self) -> bool:
        return bool(self.team_keys) and self.total_runs > 0

    def generate_runs(self):
        for i in range(self.total_runs):
            team_key = next(self.rotator)
            raw_team_data = self.config.teams_selections[team_key]
            
            active_team = self._build_team_config(raw_team_data)
            yield i, active_team

    def _build_team_config(self, team_data) -> TeamConfig:
        is_hard = self.config.difficulty >= GameMode.HARD
        is_extreme = self.config.difficulty == GameMode.EXTREME
        
        team_list = HARD if is_hard else TEAMS
        
        team_keywords = [list(team_list.keys())[aff] for aff in team_data.affinity]
        gifts = [team_list[keyword] for keyword in team_keywords]
        
        if not self.config.starting_graces[3]: 
            gifts[0]['uptie1'] = {k: gifts[0]['uptie1'][k] for k in list(gifts[0]['uptie1'])[:1]}
        
        skips = 1 + self.config.starting_graces[2] + int(self.config.starting_graces[2] > 0)

        selected_sinners = [list(SINNERS.keys())[i] for i in team_data.sinners]
        
        keywordless = self.config.keywordless_gifts.copy()
        
        if is_extreme:
            lunar_comp = list(set(["slashmemory", "piercememory", "bluntmemory"]) - set([f"{name.lower()}memory" for name in team_keywords]))
            stones = [f"stone{i}" for i in range(7)] + lunar_comp
            keywordless.update({"lunarmemory": 2})
            keywordless.update({gift: 2 for gift in stones})

        return TeamConfig(
            difficulty=self.config.difficulty,
            collect_bonus=self.config.bonus_charge,
            graces=self.config.starting_graces,
            team_keywords=team_keywords,
            name_order=team_data.affinity_idx,
            check_duplicate_names=team_data.duplicates,
            gifts=gifts,
            cards=self.config.card_priority,
            sinners=selected_sinners,
            skips=skips,
            prioritized_packs_filtered=generate_packs_pr(team_data.priority, self.config.difficulty),
            avoided_packs=generate_packs_av(team_data.avoid, self.config.difficulty),      
            prioritized_packs_all=generate_packs_all(team_data.priority, self.config.difficulty),
            keywordless_gifts=keywordless,
        )