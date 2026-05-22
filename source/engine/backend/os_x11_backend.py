# Linux (X11) port
# Extra dependencies: python-xlib, mss
import numpy as np
import time

import mss
from Xlib import X, XK, display
from Xlib.ext import xtest

from .helpers import WindowError, human_delay


# Display + root
_disp = display.Display()
_root = _disp.screen().root


def get_screen_size():
    """Return (width, height) of the X screen (root window)."""
    screen = _disp.screen()
    return screen.width_in_pixels, screen.height_in_pixels

def get_position():
    """Return (x, y) cursor position relative to root."""
    pointer = _root.query_pointer()
    return pointer.root_x, pointer.root_y

def _get_window_title(win):
    """Return window title attempting _NET_WM_NAME then WM_NAME."""
    try:
        atom_net_wm_name = _disp.intern_atom('_NET_WM_NAME')
        prop = win.get_full_property(atom_net_wm_name, X.AnyPropertyType)
        if prop and prop.value:
            # prop.value may be bytes -> decode
            if isinstance(prop.value, bytes):
                try:
                    return prop.value.decode('utf-8')
                except Exception:
                    return prop.value.decode('latin-1', errors='ignore')
            return prop.value

        # Fallback to WM_NAME
        prop2 = win.get_wm_name()
        if prop2:
            return prop2
    except Exception:
        pass
    return ""

def getActiveWindowTitle():
    """Return active window title, or empty string if none."""
    try:
        atom_net_active = _disp.intern_atom('_NET_ACTIVE_WINDOW')
        prop = _root.get_full_property(atom_net_active, X.AnyPropertyType)
        if not prop:
            return ""
        win_id = prop.value[0]
        win = _disp.create_resource_object('window', win_id)
        title = _get_window_title(win)
        return title or ""
    except Exception:
        return ""

# Helper to find a top-level window by title (exact or substring)
def _find_window_by_name(name):
    """Search _NET_CLIENT_LIST for a window whose title contains `name`."""
    try:
        atom_clients = _disp.intern_atom('_NET_CLIENT_LIST')
        prop = _root.get_full_property(atom_clients, X.AnyPropertyType)
        if not prop:
            return None
        for wid in prop.value:
            try:
                w = _disp.create_resource_object('window', wid)
                title = _get_window_title(w)
                if not title:
                    continue
                if title == name or name in title:
                    return w
            except Exception:
                continue
    except Exception:
        pass
    return None
    

def get_virtual_screen_bounds():
    """
    Returns (min_x, min_y, max_x, max_y) of the virtual desktop.
    Equivalent to Windows' SM_XVIRTUALSCREEN / SM_CXVIRTUALSCREEN.
    Coordinates may be negative.
    """
    from Xlib.ext import randr

    res = randr.get_screen_resources(_root)

    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    for crtc in res.crtcs:
        info = randr.get_crtc_info(_root, crtc, res.config_timestamp)

        # Skip disabled CRTCs
        if info.width == 0 or info.height == 0:
            continue

        min_x = min(min_x, info.x)
        min_y = min(min_y, info.y)
        max_x = max(max_x, info.x + info.width)
        max_y = max(max_y, info.y + info.height)

    # Fallback: no RandR info
    if min_x == float("inf"):
        geom = _root.get_geometry()
        min_x = geom.x
        min_y = geom.y
        max_x = geom.x + geom.width
        max_y = geom.y + geom.height

    return int(min_x), int(min_y), int(max_x), int(max_y)
  

def screenshot(imageFilename=None, region=None, display=None):
    """
    Capture screenshot using XShm via mss (falls back to XGetImage if needed).
    region: (x, y, width, height)
    Returns numpy array in BGR order (height, width, 3) for cv2 compatibility.
    """
    with mss.mss() as sct:
        if region:
            if display:
                min_x, min_y, _, _ = display
            else:
                min_x, min_y, _, _ = get_virtual_screen_bounds()
            
            left, top, width, height = region

            x0 = left - min_x
            y0 = top - min_y

            monitor = {"left": x0, "top": y0, "width": width, "height": height}
        else:
            monitor = sct.monitors[0]

        full = sct.grab(monitor)
        img = np.array(full)[:, :, :3]

        if imageFilename:
            import cv2
            cv2.imwrite(imageFilename, img)

        return img


# Map logical buttons to X button numbers
_BUTTON_MAP = {'left': 1, 'middle': 2, 'right': 3}
_WHEEL_UP = 4
_WHEEL_DOWN = 5


# Mouse functions using XTest
def mouseDown(button='left', delay=0.09):
    _button = _BUTTON_MAP.get(button.lower(), 1)
    xtest.fake_input(_disp, X.ButtonPress, _button)
    _disp.sync()
    human_delay(delay, delay + 0.02)

def mouseUp(button='left', delay=0.09):
    _button = _BUTTON_MAP.get(button.lower(), 1)
    xtest.fake_input(_disp, X.ButtonRelease, _button)
    _disp.sync()
    human_delay(delay, delay + 0.02)

def send_mouse_move(x, y):
    xtest.fake_input(_disp, X.MotionNotify, x=x, y=y)
    _disp.sync()

def mouseDown_fast(button='left', delay=0.03):
    mouseDown(button, delay=delay)

def mouseUp_fast(button='left', delay=0.03):
    mouseUp(button, delay=delay)


def scroll(clicks):
    """Scroll vertically: positive clicks -> up, negative -> down."""
    count = abs(int(clicks))
    if clicks > 0:
        btn = _WHEEL_UP
    else:
        btn = _WHEEL_DOWN
    for _ in range(count):
        xtest.fake_input(_disp, X.ButtonPress, btn)
        xtest.fake_input(_disp, X.ButtonRelease, btn)
    _disp.sync()
    human_delay()

# Keyboard functions
_BASIC_KEYSYM_MAP = {
    'enter': 'Return',
    'esc': 'Escape',
    'space': 'space',
    'tab': 'Tab',
    'backspace': 'BackSpace',
    'delete': 'Delete',
    'insert': 'Insert',
    'home': 'Home',
    'end': 'End',
    'pageup': 'Page_Up',
    'pagedown': 'Page_Down',
    'shift': 'Shift_L',
    'ctrl': 'Control_L',
    'alt': 'Alt_L',
    'win': 'Super_L',
    'up': 'Up',
    'down': 'Down',
    'left': 'Left',
    'right': 'Right',
    'f1': 'F1', 'f2': 'F2', 'f3': 'F3', 'f4': 'F4',
    'f5': 'F5', 'f6': 'F6', 'f7': 'F7', 'f8': 'F8',
    'f9': 'F9', 'f10': 'F10', 'f11': 'F11', 'f12': 'F12',
}

def _resolve_keysym_and_keycode(token):
    """
    Accepts 'a', 'A', 'enter', 'space', etc.
    Returns (keycode, modifiers_list) where modifiers_list contains strings like 'Shift_L'.
    Returns (None, None) if resolution fails.
    """
    if len(token) == 1:
        lower = token.lower()
        ks_lower = XK.string_to_keysym(lower)
        ks_upper = XK.string_to_keysym(token.upper())
        kc = 0
        if ks_lower:
            kc = _disp.keysym_to_keycode(ks_lower)
        if not kc and ks_upper:
            kc = _disp.keysym_to_keycode(ks_upper)
        if not kc:
            return None, None

        ksym_level0 = _disp.keycode_to_keysym(kc, 0)
        ksym_level1 = _disp.keycode_to_keysym(kc, 1)
        if ksym_level0 == ks_lower:
            return kc, []
        if ksym_level1 == ks_upper:
            return kc, ['Shift_L']
        return kc, []
    else:
        mapped = _BASIC_KEYSYM_MAP.get(token.lower(), token)
        ks = XK.string_to_keysym(mapped)
        if ks == 0:
            return None, None
        kc = _disp.keysym_to_keycode(ks)
        if not kc:
            return None, None
        return kc, []

def _press_modifier(name):
    """Press a modifier key by name (e.g. 'Shift_L', 'Control_L')."""
    ks = XK.string_to_keysym(name)
    if not ks:
        return False
    kc = _disp.keysym_to_keycode(ks)
    if not kc:
        return False
    xtest.fake_input(_disp, X.KeyPress, kc)
    return True

def _release_modifier(name):
    ks = XK.string_to_keysym(name)
    if not ks:
        return False
    kc = _disp.keysym_to_keycode(ks)
    if not kc:
        return False
    xtest.fake_input(_disp, X.KeyRelease, kc)
    return True

def pressDown(keys, delay=0.01):
    """Press a sequence of keys. Handles Shift when required."""
    pressed_mods = []
    for key in keys:
        kc, mods = _resolve_keysym_and_keycode(key)
        if not kc:
            continue

        for m in mods:
            if m not in pressed_mods:
                _press_modifier(m)
                pressed_mods.append(m)

        xtest.fake_input(_disp, X.KeyPress, kc)
        time.sleep(delay)
    _disp.sync()

def pressUp(keys, delay=0.01):
    """Release keys in reverse order."""
    released_mods = []
    for key in reversed(keys):
        kc, mods = _resolve_keysym_and_keycode(key)
        if not kc:
            continue

        xtest.fake_input(_disp, X.KeyRelease, kc)
        time.sleep(delay)

        for m in reversed(mods):
            if m not in released_mods:
                _release_modifier(m)
                released_mods.append(m)
    _disp.sync()


def get_absolute_position(win):
    x = y = 0
    while True: # Ugly!!!
        geom = win.get_geometry()
        x += geom.x
        y += geom.y
        parent = win.query_tree().parent
        if parent.id == _root.id:
            break
        win = parent
    return x, y


def detect_client_rect(window_name: str):
    w = _find_window_by_name(window_name)
    if not w:
        raise RuntimeError("Launch Limbus Company!")

    _disp.sync()
    try:
        geom = w.get_geometry()
    except Exception:
        raise RuntimeError("Launch Limbus Company!")

    client_width, client_height = geom.width, geom.height
    left, top = get_absolute_position(w)
    
    return left, top, client_width, client_height

def within_screen_check(left: int, top: int, width: int, height: int, display=None):
    if display:
        min_x, min_y, max_x, max_y = display
    else:
        min_x, min_y, max_x, max_y = get_virtual_screen_bounds()

    in_bounds = (
        left >= min_x and
        top >= min_y and
        left + width <= max_x and
        top + height <= max_y
    )
    if not in_bounds:
        raise WindowError("Window is partially or completely out of screen bounds!")