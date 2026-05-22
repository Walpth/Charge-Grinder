import time
import logging

from source.engine.input_controller import InputController, PauseException, StopExecution
from source.data import UIDatabase


def countdown(seconds):
    width = len(str(seconds))  # dynamic width based on max number
    bar_length = 20

    for i in range(seconds, 0, -1):
        progress = (seconds - i) / seconds
        filled = int(bar_length * progress)
        bar = "[" + "#" * filled + "-" * (bar_length - filled) + "]"
        
        print(f"Starting in: {i:{width}} {bar}", end="\r")
        time.sleep(1)

    clear_line = f"Starting in: {seconds:{width}} [{' ' * bar_length}]"
    print(" " * len(clear_line), end="\r")
    print("Grinding Time!")

def wait_while_condition(condition, action=None, interval=0.5, timer=20):
    deadline = time.monotonic() + timer
    while condition():
        if time.monotonic() >= deadline:
            return False # exit inf loop
        if action:
            action()
        time.sleep(interval)
    return True


def verify_active_window(ctrl: InputController):
    try:
        ctrl.check_active_window()
    except PauseException as msg:
        pause(ctrl, str(msg))

def pause(ctrl: InputController, msg: str):
    print(msg)
    logging.info(f"Execution paused")
    event = ctrl.window._event
    if event:
        event.request_pause_ui.emit()
        event.pause_event.clear()
        event.pause_event.wait()
        if event.stop_event.is_set():
            raise StopExecution
        countdown(5)
    else:
        raise StopExecution
    
    ctrl.window.update()
    logging.info("Execution resumed")


def close_limbus(ctrl: InputController):
    try:
        ctrl.hotkey('alt', 'f4')
    except PauseException:
        pass
    
    event = ctrl.window._event
    if event:
        event.request_stop_ui.emit()

def handle_fuckup(ctrl: InputController, ui: UIDatabase):
    ctrl.window.update()
    try:
        ctrl.click(1888, 901)
        ctrl.press("Esc")
        ctrl.press("Esc")
        if ui.UtilsMenu.forfeit.check(wait=1):
            ctrl.press("Esc")
    except PauseException as msg:
        pause(ctrl, str(msg))


def loading_halt(ui: UIDatabase):
    if not wait_while_condition(
        condition=lambda: not ui.UtilsMenu.loading.check(),
        timer=3,
        interval=0.1
    ): 
        return False
    
    return wait_while_condition(
        condition=lambda: ui.UtilsMenu.loading.check(),
    )

def connection(ui: UIDatabase):
    if not wait_while_condition(
        condition=lambda: not ui.UtilsMenu.connecting.check(),
        timer=0.5,
        interval=0.1
    ): 
        return False
    
    return wait_while_condition(
        condition=lambda: ui.UtilsMenu.connecting.check(),
    )