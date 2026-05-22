from typing import List, Tuple, Optional

import numpy as np

import source.engine as eg
from source.data import UIDatabase, TeamConfig


MOUNTING_TRIALS = [
    "DefenseSkillUp", "DefenseLevelUp", "Resilient", "Growth", 
    "BodyUp", "Keen", "OffenseLevelUp", "TakeLessDamage", 
    "ClashPower", "FinalPower", "BasePower", "Brutality", "Headstrong"
]

def get_unowned_ego_coords(ui: UIDatabase, image: np.ndarray, team: TeamConfig) -> List[Tuple[int, int]]:
    """Returns a list of EGO coordinates that are NOT marked as owned."""
    owned_targets = ui.GrabMenu.owned.locate_all()
    owned_x_coords = [t.box[0] + t.box[2] for t in owned_targets]
    
    # Optional: If you want to restrict search to a specific region, pass it to locate_all_in
    ego_targets = ui.GrabMenu.ego_R.locate_all_in(image, team.gifts[0]["checks"][0])
    
    valid_coords = []
    for target in ego_targets:
        coord = target.center
        # Check if this EGO is far enough from all 'owned' markers (Legacy: 200px)
        if all(abs(coord[0] - ox) >= 200 for ox in owned_x_coords):
            valid_coords.append(coord)
            
    return valid_coords

def evaluate_best_egos(ctrl: eg.InputController, ui: UIDatabase, image: np.ndarray, team: TeamConfig, count: int = 1) -> List[Tuple[int, int]]:
    """
    Evaluates the screen and returns the top N coordinates to click.
    Replaces the horrifying 'draw_rect' loop.
    """
    valid_coords = get_unowned_ego_coords(ui, image, team)
    if not valid_coords:
        return []

    scored_egos = [] # List of tuples: (score, x, y)
    
    # 1. Check for high-priority keywordless/buy gifts
    if team.gifts[0]["sin"] or not ui.GrabMenu.ego_R.check_in(image, team.gifts[0]["checks"][0]):
        priority_gifts = list(team.keywordless_gifts.keys()) + [buy for aff in team.gifts if aff["sin"] for buy in aff["buy"]]
        for gift in priority_gifts:
            target = ui.GrabMenu.ego_R.transform(eg.resize, {"scale_factors": (0.94, 0.94)}).locate_in(image, str(gift))
            if target and target.center in valid_coords:
                # Arbitrary high score for priority gifts
                scored_egos.append((1000, target.center)) 

    # 2. Evaluate Tiers and Affinity
    for coord in valid_coords:
        # Check if this coordinate belongs to an affinity gift
        is_affinity = any(coord in [t.center for t in ui.GrabMenu.ego_R.locate_all_in(image, aff["checks"][0])] for aff in team.gifts)
        
        # Determine Tier (4 down to 1)
        tier = 0
        crop_region = (coord[0] - 106, 0, 66, 42)
        cropped_img = eg.crop(ctrl, image, crop_region)
        
        for lvl in range(4, 0, -1):
            if ui.GrabMenu.ego_tier_R.check_in(cropped_img, f"tier{lvl}"):
                tier = lvl
                break
                
        # Calculate Score: Tiers are base score (1-4). Affinity adds a massive weight (e.g., +10).
        score = tier + (10 if is_affinity else 0)
        scored_egos.append((score, coord))

    # Sort descending by score, take top 'count'
    scored_egos.sort(key=lambda x: x[0], reverse=True)
    return [coord for score, coord in scored_egos[:count]]


def evaluate_best_trials(ui: UIDatabase, trials_image: np.ndarray, count: int = 1) -> List[Tuple[int, int]]:
    """Finds the highest priority trial."""
    found_trials = []
    
    for name in MOUNTING_TRIALS:
        for scale in [1, 1.05]:
            targets = ui.GrabMenu.ego_tier_R.transform(eg.resize, {"scale_factors": (scale, scale)}).locate_all_in(trials_image, f"trial_{name}")
            for target in targets:
                # Store priority index (lower is better) and coordinate
                found_trials.append((MOUNTING_TRIALS.index(name), target.center))

    # Sort by priority index (ascending)
    found_trials.sort(key=lambda x: x[0])
    
    # Filter out duplicates (same coordinate found on different scales)
    unique_coords = []
    for _, coord in found_trials:
        if not any(abs(coord[0] - u[0]) < 50 for u in unique_coords): # 50px deduplication threshold
            unique_coords.append(coord)
            if len(unique_coords) == count:
                break
                
    return unique_coords