import logging
import time

import source.engine as eg
from source.game_states.main import wait_while_condition, loading_halt, pause
# from source.game_states.battle import select_team
from source.data import UIDatabase, TeamConfig
from source_app.data.bot_config import GameMode


def select_graces(ui: UIDatabase, team: TeamConfig):
    for i in range(len(team.graces)):
        if not team.graces[i]:
            continue

        x = int(335 + 297 * (i % 5))
        y = int(375 + 357 * (i // 5))
        
        ui.point.click(coords=(x, y), verify=ui.MainMenu.money_R)
        
        if team.graces[i] <= 1:
            continue

        offset_x = 60 * (1 - 2 * (team.graces[i] < 3))
        ui.point.click(coords=(x + offset_x, y + 155), verify=ui.MainMenu.money_R)


def dungeon_start(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    menu = ui.MainMenu

    try:
        with eg.ActionChain(ctrl, max_attempts=5) as chain:
            chain.warp(menu.drive)
            chain.click(menu.drive)

            chain.warp(menu.mirror_dungeon)
            chain.click(menu.mirror_dungeon, verify=menu.start)

            chain.call(lambda: time.sleep(1.4))
            chain.warp(menu.start)

            @chain.call
            def check_extreme_button():
                if team.difficulty == GameMode.EXTREME:
                    menu.infinite_off.locate().click(coords=(1588, 567))

            @chain.call
            def start_options():
                menu.start.locate().click()
                if menu.enter_invert.check(wait=1):
                    return
                if menu.resume.locate().click():
                    loading_halt(ui)
                

            chain.warp(menu.enter_invert)
            chain.click(menu.enter_invert, verify=menu.confirm_team)
            
            chain.warp(menu.confirm_team)
            # chain.call(lambda: select_team(ctrl, ui)) 
            
            @chain.call
            def confirm_team():
                menu.confirm_team.try_locate().click()
                time.sleep(0.5)
                menu.confirm_invert.locate().click()
                wait_while_condition(lambda: not menu.enter_bonus.check())
                time.sleep(0.2)

            chain.warp(menu.enter_bonus)
            chain.call(lambda: select_graces(ui, team))

            chain.click(menu.enter_bonus)
            
            chain.warp(menu.confirm_run)
            @chain.call
            def click_starlight():
                menu.starlight.locate().click()
            
            chain.click(menu.confirm_run, verify=menu.refuse)
            
            chain.warp(menu.refuse)
            @chain.call
            def click_gift_search():
                time.sleep(0.2)
                menu.gift_search.locate().click()

            gift_x, gift_y = team.gifts[0]["checks"][2]
            chain.coord_click(gift_x, gift_y, verify=menu.gifts_R)
            
            if team.graces[3] or team.gifts[0]['checks'][5] == 0:
                chain.coord_click(1239, 395, verify=menu.selected_R)
            if team.graces[3] or team.gifts[0]['checks'][5] == 1:
                chain.coord_click(1239, 549, verify=menu.selected_R)
            if team.graces[9]:
                chain.coord_click(1239, 703, verify=menu.selected_R)

            chain.coord_click(1624, 882)

            if team.graces[9]:
                chain.click(ui.GrabMenu.confirm_ego)
            if team.graces[3]:
                chain.click(ui.GrabMenu.confirm_ego)
            
            chain.warp(ui.GrabMenu.confirm_ego)
            chain.click(ui.GrabMenu.confirm_ego, verify=ui.UtilsMenu.loading)
            chain.call(lambda: loading_halt(ui))

    except eg.PauseException as e:
        pause(ctrl, str(e))
        return True
    except RuntimeError as e:
        if "No recognized UI" in str(e):
            return False
        
        print("Initialization error")
        logging.error("Initialization error")
        return False

    return True