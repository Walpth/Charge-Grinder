import time
import os
import platform

import numpy as np
import cv2

from .events import BotEvents
from .backend.helpers import WindowError, generate_move_path


if platform.system() == "Windows":
    from .backend import os_windows_backend as backend
elif platform.system() == "Linux":
    if os.environ.get("XDG_SESSION_TYPE") == "x11":
        from .backend import os_x11_backend as backend
    else:
        raise RuntimeError("Wayland is not supported. Use Plasma (X11).")
else:
    raise RuntimeError("Unsupported OS")


class StopExecution(Exception): pass
class PauseException(Exception):
    def __init__(self, name):
        self.window = name
        message = f"Switched to window: {name}"
        super().__init__(message)


class Window:
    target_ratio: float = 16 / 9

    def __init__(self, left: int, top: int, width: int, height: int, event: BotEvents = None):
        self._window_name = None
        self._display = backend.get_virtual_screen_bounds()
        self._event = event

        self.left = left
        self.top = top
        self.width = width
        self.height = height

    @classmethod
    def event_warning_check(cls, client_width: int, client_height: int, event: BotEvents):
        if event and int(client_width / 16) != int(client_height / 9):
            event.warning_raised.emit(
                f"Game window ({client_width} x {client_height}) is not 16:9\n \
                  It is recommended to set the game to either\n \
                  1920 x 1080 or 1280 x 720"
            )

    @classmethod
    def from_system(cls, window_name: str, event: BotEvents = None):
        left, top, client_w, client_h = backend.detect_client_rect(window_name)
        cls.event_warning_check(client_w, client_h, event)
        left, top, w, h = cls._crop_to_hd(left, top, client_w, client_h)

        instance = cls(left, top, w, h, event=event)
        instance._window_name = window_name
        instance._event = event
        backend.within_screen_check(left, top, w, h, display=instance._display)
        return instance

    def update(self):
        if self._window_name is None:
            raise WindowError("Cannot update: Window name not set. Use .from_system() to initialize.")
        
        self._display = backend.get_virtual_screen_bounds()
        left, top, client_w, client_h = backend.detect_client_rect(self._window_name)
        self.event_warning_check(client_w, client_h, self._event)
        left, top, w, h = self._crop_to_hd(left, top, client_w, client_h)

        backend.within_screen_check(left, top, w, h, display=self._display)
        self.left, self.top, self.width, self.height = left, top, w, h

    @classmethod
    def _crop_to_hd(cls, left: int, top: int, client_width: int, client_height: int):
        ratio = cls.target_ratio
        cw, ch = client_width, client_height

        if cw / ch > ratio:
            h = int(ch)
            w = int(h * ratio)
        elif cw / ch < ratio:
            w = int(cw)
            h = int(w / ratio)
        else:
            w, h = int(cw), int(ch)

        left = int(left + (client_width - w) // 2)
        top = int(top + (client_height - h) // 2)
        
        return left, top, w, h

    def as_tuple(self):
        return (self.left, self.top, self.width, self.height)

    def __iter__(self):
        yield from self.as_tuple()

    def __repr__(self):
        return f"Window(left={self.left}, top={self.top}, width={self.width}, height={self.height})"

    @property
    def name(self):
        return self._window_name or "LimbusCompany"
    
    
class InputController:
    def __init__(self, window: Window, failsafe_enabled=True):
        self.window = window
        self.failsafe_enabled = failsafe_enabled

    @property
    def comp(self):
        return self.window.width / 1920
            

    def check_active_window(self):
        if not self.failsafe_enabled:
            return
        
        active_window = backend.getActiveWindowTitle()
        if not self.window.name in active_window:
            raise PauseException(active_window)
        
        timer = 0
        while "(Not Responding)" in active_window:
            time.sleep(1)
            timer += 1
            if timer > 60:
                raise StopExecution
            
            active_window = backend.getActiveWindowTitle()
            if not self.window.name in active_window:
                raise PauseException(active_window)
    

    def screenshot(self, region=(0, 0, 1920, 1080)): # works only for cv2!
        self.check_active_window()

        x, y, w, h = region
        captured = np.array(backend.screenshot(region=(
            round(self.window.left + x*self.comp),
            round(self.window.top + y*self.comp),
            round(w*self.comp),
            round(h*self.comp)
            ), display=self.window._display))
        
        if self.comp > 1.0: # optimization
            return cv2.resize(captured, (w, h), interpolation=cv2.INTER_AREA)
        
        return captured
    
    def scale_for_backend(self, x, y):
        scaled_x = int(self.window.left + x * self.comp)
        scaled_y = int(self.window.top + y * self.comp)
        return scaled_x, scaled_y
    
    def get_position(self):
        x, y = backend.get_position()
        return int(round((x - self.window.left) / self.comp)), int(round((y - self.window.top) / self.comp))
    
            
    def mouseDown(self, button='left'):
        self.check_active_window()
        backend.mouseDown(button=button)

    def mouseUp(self, button='left'):
        self.check_active_window()
        backend.mouseUp(button=button)

    def click(self, *args, button='left', clicks=1, interval=0.1, duration=0.0):
        self.check_active_window()
        if len(args) == 0: x, y = None, None
        elif len(args) == 1: x, y = args[0]
        elif len(args) == 2: x, y = args
        else: raise TypeError(f"Too many args for click(). Have: {len(args)}. Expected: <= 2.")

        if x is not None and y is not None:
            self.moveTo(x, y, duration=0)
        else:
            time.sleep(0.02)

        for i in range(clicks):
            self.check_active_window()
            backend.mouseDown_fast(button=button)
            backend.mouseUp_fast(button=button)
            
            if interval > 0 and i < clicks - 1:
                time.sleep(interval)

    def moveTo(self, *args, duration=0.03, humanize=True):
        if len(args) == 1: x, y = args[0]
        elif len(args) == 2: x, y = args
        else: raise TypeError(f"Incorrect args for moveTo(). Have: {len(args)}. Expected: 1 or 2.")

        scaled_x, scaled_y = self.scale_for_backend(x, y)
        
        start_x, start_y = backend.get_position()
        path = generate_move_path(start_x, start_y, scaled_x, scaled_y, duration, humanize=humanize)
        
        for next_x, next_y, sleep_time in path:
            self.check_active_window() 
            backend.send_mouse_move(next_x, next_y) 
            time.sleep(sleep_time)

    def dragTo(self, *args, duration=0.13, button='left', start_x=None, start_y=None):
        if len(args) == 1: x, y = args[0]
        elif len(args) == 2: x, y = args
        else: raise TypeError(f"Incorrect args for dragTo(). Have: {len(args)}. Expected: 1 or 2.")

        if start_x is not None and start_y is not None:
            self.moveTo(start_x, start_y)

        backend.mouseDown_fast(button=button)
        self.moveTo(x, y, duration, humanize=False)
        backend.mouseUp_fast(button=button)

    def scroll(self, clicks, x=None, y=None):
        if x is not None and y is not None:
            self.moveTo(x, y)
        else:
            self.check_active_window()
        backend.scroll(clicks)

    def press(self, keys, presses=1, interval=0.1):
        for _ in range(presses):
            if isinstance(keys, str):
                keys = [keys]
            
            self.check_active_window()
            backend.pressDown(keys)
            backend.pressUp(keys)           
            
            if interval > 0 and _ < presses - 1:
                time.sleep(interval)

    def hotkey(self, *args, **kwargs):
        self.press(list(args), **kwargs)
        