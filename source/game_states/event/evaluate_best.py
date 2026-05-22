import source.engine as eg
from source.data import UIDatabase, TeamConfig


favorites = ["chicken", "factory"]


def evaluate_best_choice(ui: UIDatabase, team: TeamConfig) -> eg.Target:
    """Scans the event screen and returns the Target for the best available option."""
    # 1. New content or Level ups
    for high_priority in [ui.EventMenu.text_new, ui.EventMenu.text_lvl]:
        target = high_priority.locate()
        if target: return target

    # 2. Favorite Event Options
    for favorite in favorites:
        target = ui.EventMenu.text_ego.locate(f"choice_{favorite}")
        if target: return target

    # 3. EGO gifts without battle
    egos = ui.EventMenu.text_ego.locate_all()
    if not egos:
        return None

    win_target = ui.EventMenu.text_win.locate()
    win_y = win_target.center[1] if win_target else None
    
    affinities = []
    for kw in team.team_keywords:
        affinities += ui.EventMenu.text_ego.locate_all(f"{kw.lower()}_choice")

    candidates = []
    egos.sort(key=lambda target: target.center[1])
    for ego in egos:
        if win_y and abs(ego.center[1] - win_y) < 80:
            continue
        
        if any(abs(ego.center[1] - aff.center[1]) < 10 for aff in affinities):
            return ego
        
        candidates.append(ego)

    if candidates:
        return candidates[0]
        
    return None