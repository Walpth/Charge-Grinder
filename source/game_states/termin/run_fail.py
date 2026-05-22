import logging

import source.engine as eg
from source.game_states.main import wait_while_condition, loading_halt, pause
from source.data import UIDatabase


def dungeon_fail(ctrl: eg.InputController, ui: UIDatabase):
    if not ui.MainMenu.defeat.check():
        return False
    
    logging.info('Run Failed')
    menu = ui.MainMenu
    
    try:
        with eg.ActionChain(ctrl, max_attempts=5) as chain:
            chain.warp(menu.defeat)
            @chain.call
            def click_defeat():
                ctrl.click(1693, 841)
                ctrl.moveTo(1710, 982)
                wait_while_condition(lambda: not menu.claim.check())

            chain.warp(menu.claim)
            chain.click(menu.claim)
            
            chain.warp(menu.give_up)
            chain.click(menu.give_up)

            chain.warp(menu.confirm_invert)
            chain.click(menu.confirm_invert, verify=ui.UtilsMenu.loading)

            chain.warp(ui.UtilsMenu.loading)
            chain.call(lambda: loading_halt(ui))
    except eg.PauseException as e:
        pause(ctrl, str(e))
        return False
    except RuntimeError as e:
        if "No recognized UI" in str(e):
            return False
        
        print("Termination error")
        logging.error("Termination error")
        return False
    
    print("MD Failed!")
    return True