import logging
import time

import source.engine as eg
from source.game_states.main import wait_while_condition, loading_halt, pause
from source.data import UIDatabase, TeamConfig
from source_app.data.bot_config import GameMode


def click_bonus(ui: UIDatabase, team: TeamConfig):
    if team.difficulty >= GameMode.HARD:
        ui.MainMenu.hard_bonus.locate().click()
    else:
        ui.MainMenu.bonus.locate().click()

def bonus_gone(ui: UIDatabase, team: TeamConfig):
    if team.difficulty >= GameMode.HARD:
        if not ui.MainMenu.hard_bonus.check(wait=1):
            return ui.MainMenu.hard_bonus_off.check()
        else: return False
    elif not ui.MainMenu.bonus.check(wait=1):
        return ui.MainMenu.bonus_off.check()
    else: return False

def handle_bonus(ui: UIDatabase, team: TeamConfig):
    time.sleep(0.5)
    if team.collect_bonus or bonus_gone(): return

    if not wait_while_condition(
        condition=lambda: not bonus_gone(ui, team), 
        action=lambda: click_bonus(ui, team)
        ):
        raise RuntimeError

def collect_rewards(ui: UIDatabase):
    wait_while_condition(
        condition=lambda: not ui.UtilsMenu.loading.check() or
                          not ui.MainMenu.out_of_fuel.check(),
        action=lambda: ui.MainMenu.confirm_run.locate().click(),
        interval=0.1
    )
    if ui.MainMenu.out_of_fuel.check():
        logging.error("We are out of enkephalin!")
        raise eg.StopExecution
    loading_halt(ui)


def dungeon_end(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    menu = ui.MainMenu

    try:
        with eg.ActionChain(ctrl, max_attempts=5) as chain:
            chain.warp(menu.victory)
            @chain.call
            def click_victory():
                ctrl.click(1693, 841)
                ctrl.moveTo(1710, 982)
                wait_while_condition(lambda: not menu.claim.check())

            chain.warp(menu.claim)
            chain.click(menu.claim)
            
            chain.warp(menu.claim_invert)
            chain.call(lambda: handle_bonus(ui, team))
            chain.click(menu.claim_invert)

            chain.warp(menu.confirm_invert)
            chain.click(menu.confirm_invert, verify=menu.confirm_run)

            chain.warp(menu.confirm_run)
            chain.call(lambda: collect_rewards(ui))
            
    except eg.PauseException as e:
        pause(ctrl, str(e))
        return False
    except RuntimeError as e:
        if "No recognized UI" in str(e):
            return False
        
        print("Termination error")
        logging.error("Termination error")
        return False
    
    print("MD Finished!")
    logging.info('Run Completed')
    return True