from source.data import UIDatabase, TeamConfig, RuntimeState
from source_app.data.bot_config import GameMode


def update_lvl(ui: UIDatabase, team: TeamConfig, run_state: RuntimeState):
    is_extreme = team.difficulty == GameMode.EXTREME
    max_floor = 15 if is_extreme else 5
    search_digits = range(10) if is_extreme else range(1, 6)
    
    found_digits = []
    for i in search_digits:
        targets = ui.PackMenu.lvl_R.locate_all(f"lvl{i}", conf=0.95)
        for t in targets:
            x_pos, score = t.box[0], t.score
            found_digits.append((x_pos, score, i))
    
    found_digits.sort(key=lambda item: item[0])
    
    filtered = []
    for current in found_digits:
        if not filtered:
            filtered.append(current)
            continue
        
        last_x, last_score, _ = filtered[-1]
        curr_x, curr_score, _ = current
        
        if abs(curr_x - last_x) <= 5:
            if curr_score > last_score:
                filtered[-1] = current
        else:
            filtered.append(current)

    assumed_lvl = 0
    for _, _, val in filtered:
        assumed_lvl = assumed_lvl * 10 + val
    
    if 1 <= assumed_lvl <= max_floor:
        run_state.update_floor(assumed_lvl)