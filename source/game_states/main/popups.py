import time
import logging

from .execution import connection
import source.engine as eg
from source.data import UIDatabase, TeamConfig
from source_app.data.bot_config import GameMode


def resolve_server_error(ctrl: eg.InputController, ui: UIDatabase) -> None:
    if not ui.MainMenu.server_error.check():
        return
    
    for _ in range(3):
        time.sleep(6)
        ctrl.click(1100, 700)
        time.sleep(1)
        if not ui.MainMenu.server_error.check(): 
            break

    time.sleep(10)
    if ui.MainMenu.server_error.locate().click():
        logging.error('Server error occured')


def resolve_event_effect(ctrl: eg.InputController, ui: UIDatabase) -> None:
    if not ui.MainMenu.event_effect.check():
        return 
    
    ctrl.click(773, 521)
    time.sleep(0.2)
    ctrl.click(967, 774)


def resolve_extreme_popup(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig) -> None:
    if team.difficulty < GameMode.HARD or not ui.MoveMenu.superposition.check():
        return
    
    if team.difficulty != GameMode.EXTREME:
        ctrl.click(815, 700)
    else:
        ctrl.click(1117, 700)
    connection()