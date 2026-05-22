import time

import source.engine as eg
from source.data import UIDatabase, TeamConfig
from source_app.data.bot_config import GameMode
from source.game_states.main import wait_while_condition
from .grab_perception import evaluate_best_egos, evaluate_best_trials


def grab_EGO(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    '''
    Selects EGO gift(s) on the Ego Gift Selection screen
    retuns whether or not the EGO gift(s) is/are selected
    '''
    if not ui.GrabMenu.ego_bin.check(): 
        return False
    print("grab ego check passed")
    time.sleep(0.8)

    cycle_count = 1
    prioritize_trials = False
    
    if team.difficulty > GameMode.NORMAL and ui.GrabMenu.trials.check(): 
        cycle_count = 2
        if team.difficulty == GameMode.EXTREME:
            prioritize_trials = True
    elif team.graces[9]:
        for i in [3, 2]:
            if ui.GrabMenu.select_count_R.check(f"select{i}"):
                cycle_count = i
                break

    # 2. Perceive Screen
    image = ui.GrabMenu.ego_R.screenshot()
    best_egos = evaluate_best_egos(ui, ctrl, image, team, count=cycle_count)
    
    best_trials = []
    if prioritize_trials:
        trials_image = ui.GrabMenu.buffs_R.screenshot()
        best_trials = evaluate_best_trials(ui, trials_image, count=1) # Legacy code only ever clicked 1 trial

    # 3. Execute Clicks
    if best_trials:
        # Legacy code offset Y by 600 for trials
        ctrl.click(best_trials[0][0], 600)
        time.sleep(0.1)

    for coord in best_egos:
        ctrl.click(coord)
        time.sleep(0.1)

    # Confirm selection
    try:
        for _ in range(cycle_count):
            ui.point.click(coords=(1687, 870), verify=ui.GrabMenu.confirm_ego)
    except RuntimeError:
        ctrl.press("enter", presses=2, interval=1)
        time.sleep(1)
        
    return True


def grab_card(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    '''
    Selects the Reward Card according to specified priority
    Returns whether the card was selected or not
    '''
    if not ui.GrabMenu.encounter_reward.check(): 
        return False

    ctrl.moveTo(1000, 900)
    ui.GrabMenu.cancel.locate().click() # if was misclicked
    time.sleep(1.4)
    
    for i in team.cards:
        card_target = ui.GrabMenu.card_R.locate(f"card{i}")
        if not card_target:
            continue

        try:
            card_target.click(verify=ui.GrabMenu.reward_count_R)
            ui.GrabMenu.confirm_card.locate().click(verify=ui.UtilsMenu.connecting)
            
            wait_while_condition(
                condition=lambda: ui.GrabMenu.encounter_reward.check(), 
                action=lambda: ui.GrabMenu.confirm_ego.locate().click(),
                interval=0.1
            )
            return True
        except RuntimeError:
            continue
                
    return False


def confirm(ctrl: eg.InputController, ui: UIDatabase):
    '''Function to confirm EGO gift pop-ups'''
    if not ui.GrabMenu.confirm_ego.locate().click(): 
        return False
    
    ctrl.moveTo(965, 878)
    time.sleep(0.3)
    ui.GrabMenu.confirm_ego.locate().click()
    return True


def get_adversity(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    if team.difficulty < GameMode.EXTREME or not ui.GrabMenu.adversity.check(): 
        return False
    
    targets = ui.GrabMenu.projection.locate_all()
    x_coords = [target.box[0] for target in targets]
    x_coords.sort() 
    
    for x in x_coords:
        ui.point.click(coords=(x, 550), verify=ui.GrabMenu.select_count_R)
        
    time.sleep(0.3)
    ctrl.click(1725, 1000)
    
    wait_while_condition(lambda: ui.GrabMenu.adversity.check(), interval=0.2)
    return True