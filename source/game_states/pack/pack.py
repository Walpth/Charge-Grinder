import logging
import time

from .update_lvl import update_lvl
from .pack_search import choose_best_pack
import source.engine as eg
from source.game_states.main import wait_while_condition
from source.data import UIDatabase, TeamConfig, RuntimeState
from source_app.data.bot_config import GameMode


def remove_pack(level: int, name: str, team: 'TeamConfig'):
    is_extreme = team.difficulty == GameMode.EXTREME
    for l in range(level, 6 + (is_extreme * 10)):
        floor_key = f"floor{l}"
        floor_packs = team.prioritized_packs_filtered.get(floor_key, [])
        if name in floor_packs:
            floor_packs.remove(name)

def setup_regions(ui: UIDatabase):
    start_time = time.time()
    pack_pull_coords = None
    while not pack_pull_coords and (time.time() - start_time < 4):
        time.sleep(0.2)
        target = ui.PackMenu.pack_pull.locate()
        if target:
            pack_pull_coords = target.center

    if pack_pull_coords:
        card_count = 5 - min((max((pack_pull_coords[0] - 21), 1) // 157), 2)
    else:
        card_count = 5
        
    offset = (5 - card_count) * 161
    regions = [(182 + offset + 322 * i, 280, 291, 624) for i in range(card_count)]
    print(f"{card_count} Packs detected.")
    return regions


def handle_packs(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig, run_state: RuntimeState) -> bool:
    if not ui.PackMenu.pack_choice.check():
        return False
    print("pack check passed")
    
    update_lvl(ui, team, run_state)
    lvl = run_state.floor_lvl

    if lvl in (6, 11): 
        time.sleep(2)  # animation

    # Ensure difficulty is correctly toggled           
    if lvl <= 5:
        wants_hard = team.difficulty >= GameMode.HARD
        is_hard_ui = ui.PackMenu.hard_difficulty.check()
        
        if wants_hard != is_hard_ui:
            ui.point.click(
                coords=(1349, 64), 
                verify=ui.PackMenu.hard_difficulty, 
                disappear_ver=(not wants_hard)
            )

    print(f"Entering Floor {lvl}")
    logging.info(f"Floor {lvl}")

    ctrl.moveTo(1721, 999)
    
    regions = setup_regions(ui)

    for skip in range(team.skips + 1):
        is_final_skip = (skip == team.skips)
        
        pack_name, region_idx = choose_best_pack(ui, lvl, regions, is_final_skip, team)
        
        if region_idx is not None:
            print(f"Entering {pack_name}")
            logging.info(f"Pack: {pack_name}")
            remove_pack(lvl, pack_name, team)
            
            rx, ry, rw, rh = regions[region_idx]
            center_x, center_y = rx + (rw // 2), ry + (rh // 2)
            ctrl.moveTo(center_x, center_y)
            ctrl.dragTo(center_x, center_y + 300, duration=0.5, button="left")
            break
            
        print("Refreshing packs...")
        ctrl.click(1617, 62)
        ctrl.moveTo(1721, 999)
        time.sleep(2)
    
    wait_while_condition(lambda: ui.PackMenu.pack_choice.check(), interval=0.1)
    
    if lvl != 1: 
        run_state.move_animation = True
    else: 
        time.sleep(0.5)
        
    return True