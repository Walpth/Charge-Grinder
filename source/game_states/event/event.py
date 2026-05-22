import time

from .evaluate_best import evaluate_best_choice
import source.engine as eg
from source.data import UIDatabase, TeamConfig
from source.game_states.main import connection, wait_while_condition


PROBS = ["VeryHigh", "High", "Normal", "Low", "VeryLow"]


def handle_event(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    if not ui.EventMenu.event_skip.check(): 
        return False
    print("event check passed")

    start_time = time.time()
    
    while time.time() - start_time < 100:
        for _ in range(3): 
            ctrl.click(906, 460)
        
        if ui.EventMenu.choices.check():
            time.sleep(0.1)
            
            best_target = evaluate_best_choice(ui, team)
            
            if best_target:
                best_target.click()
                wait_while_condition(
                    lambda: ui.EventMenu.choices.check(), 
                    interval=0.1, timer=1
                )
                continue
            else:
                # Try the 3 standard choice slots
                for y_coord in [316, 520, 730]:
                    ctrl.click(1348, y_coord)
                    if wait_while_condition(
                        lambda: ui.EventMenu.choices.check(), 
                        interval=0.5, timer=2): 
                        break
                continue

        for btn in [ui.EventMenu.proceed, ui.EventMenu.commence_battle]:
            btn.locate().click()

        if ui.EventMenu.check.check():
            if not any(ui.EventMenu.probs_R.check(prob) for prob in PROBS):
                continue

            for prob in PROBS:
                if ui.EventMenu.probs_R.locate(prob).click():
                    ui.EventMenu.commence.locate().click()
                    break

        if ui.EventMenu.continue_.locate().click():
            connection()
            return True
            
        time.sleep(0.1)
    
    return False