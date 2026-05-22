import logging
from typing import Optional, Tuple, List, Dict

from source.data import UIDatabase, TeamConfig
from source.data.packs_data import FLOORS, HARD_FLOORS, format_lvl
from source_app.data.bot_config import GameMode


def within_region(x: int, regions: List[Tuple[int, int, int, int]]) -> Optional[int]:
    for i, (rx, _, rw, _) in enumerate(regions):
        if rx < x < rx + rw:
            return i
    return None


def perceive_packs(ui: UIDatabase, lvl: int, regions: list, team: TeamConfig) -> Dict[str, int]:
    pack_list = HARD_FLOORS[format_lvl(lvl)] if team.difficulty >= GameMode.HARD else FLOORS[format_lvl(lvl)]
    found_packs = {}
    
    screen = ui.PackMenu.sift_search_R.screenshot()
    for pack_name in pack_list:
        if len(found_packs) >= len(regions): 
            break
            
        target = ui.PackMenu.sift_search_R.locate_in(screen, pack_name)
        if target and target.center:
            region_idx = within_region(target.center[0], regions)
            if region_idx is not None and region_idx not in found_packs.values():
                found_packs[pack_name] = region_idx
                
    return found_packs


def evaluate_ego_weights(ui: UIDatabase, valid_packs: Dict[str, int], regions: list, team: TeamConfig) -> str:
    ego_targets = ui.MainMenu.full_R.locate_all(team.gifts[0]["checks"][1])
    owned_targets = ui.MainMenu.full_R.locate_all("owned_small")
    
    owned_x_coords = [t.box[0] + t.box[2] for t in owned_targets]
    
    # Filter out owned EGO gifts
    unowned_ego_coords = [
        t.center for t in ego_targets 
        if all(abs(t.center[0] - ox) >= 25 for ox in owned_x_coords)
    ]

    weights = {idx: 0 for idx in valid_packs.values()}
    for coord in unowned_ego_coords:
        idx = within_region(coord[0], regions)
        if idx in weights:
            weights[idx] += 1

    best_idx = max(weights, key=weights.get)
    return next(name for name, idx in valid_packs.items() if idx == best_idx)


def choose_best_pack(ui: 'UIDatabase', lvl: int, regions: list, is_final_skip: bool, team: 'TeamConfig') -> Tuple[Optional[str], Optional[int]]:
    """
    The decision engine. Returns (pack_name, region_idx).
    Returns (None, None) if the board should be refreshed.
    """
    attempts = 2
    found_packs = dict()
    while len(found_packs.keys()) < len(regions) and attempts > 0:
        found_packs = perceive_packs(ui, lvl, regions, team)
        attempts -= 1
    logging.info(f"Packs on screen: {found_packs}")
     
    # Check Primary Priority List
    priority = team.prioritized_packs_filtered.get(f"floor{lvl}", [])
    for pack in priority:
        if pack in found_packs:
            return pack, found_packs[pack]

    # Check Fallback Priority List (Only on final skip)
    if is_final_skip:
        fallback_priority = team.prioritized_packs_all.get(f"floor{lvl}", [])
        for pack in fallback_priority:
            if pack in found_packs:
                return pack, found_packs[pack]

    # Filter out S.H.I.T. packs
    banned = team.avoided_packs.get(f"floor{lvl}", [])
    valid_packs = {name: idx for name, idx in found_packs.items() if name not in banned}

    if not valid_packs:
        if not is_final_skip:
            return None, None # All packs are banned, and we can refresh. DO IT.
        elif len(found_packs) > 0:
            print("May Ayin save us all!") # We are forced to pick a S.H.I.T. pack

            # Select a second pack when we can to avoid event packs
            default_key = 1 if len(found_packs) > 1 and 0 in found_packs.values() else 0

            sorted_packs = sorted(found_packs, key=found_packs.get)
            forced_pack = sorted_packs[default_key]
            return forced_pack, found_packs[forced_pack]
        else:
            raise RuntimeError("No valid packs found")

    # If multiple valid packs remain, evaluate based on EGO gifts
    best_pack = evaluate_ego_weights(ui, valid_packs, regions, team)
    return best_pack, valid_packs[best_pack]