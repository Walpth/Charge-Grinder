import ctypes
from ctypes import wintypes
import time
import math
import random
import threading

import numpy as np

import source.utils.params as p
from source.utils.profiles import get_macro_profile, maybe_rhythm_jitter, randomize_with_profile
from source.utils.movement.builder import build_trajectory
from source.utils.movement.inertia import get_inherited_velocity, update_inertia
from source.utils.movement.pointer_gain import update_pointer_scale, execute_trajectory

from source.utils.bridge.bridge import Bridge


_bridge = None
_bridge_lock = threading.RLock()
_bridge_init_error = None
_mouse_settings_active = False


def _get_bridge():
    global _bridge, _bridge_init_error
    with _bridge_lock:
        if _bridge is None:
            try:
                _bridge = Bridge(auto_open=True)  # auto_open handles it
                _bridge_init_error = None
            except Exception as exc:
                _bridge_init_error = RuntimeError(f"Bridge initialization failed: {exc}")
                raise _bridge_init_error
        return _bridge


def _ensure_mouse_settings():
    global _mouse_settings_active
    if _mouse_settings_active:
        return
    _get_bridge().mouse_settings_apply()
    _mouse_settings_active = True


def restore_mouse_settings():
    global _mouse_settings_active
    if _bridge is None or not _mouse_settings_active:
        return
    try:
        _bridge.mouse_settings_restore()
    finally:
        _mouse_settings_active = False


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD)
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3)
    ]

def screenshot(imageFilename=None, region=None, allScreens=False):
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    
    if allScreens:
        width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        x, y = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)  # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN
    else:
        width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        x = y = 0
    
    if region:
        x, y, rwidth, rheight = region
        width, height = rwidth, rheight
    else:
        region = (x, y, width, height)
    
    hdc = user32.GetDC(None)
    mfc_dc = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(mfc_dc, bitmap)
    
    gdi32.BitBlt(mfc_dc, 0, 0, width, height, hdc, x, y, 0x00CC0020)  # SRCCOPY
    
    try:
        bmpinfo = BITMAPINFO()
        bmpinfo.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmpinfo.bmiHeader.biWidth = width
        bmpinfo.bmiHeader.biHeight = -height
        bmpinfo.bmiHeader.biPlanes = 1
        bmpinfo.bmiHeader.biBitCount = 32
        bmpinfo.bmiHeader.biCompression = 0
        
        buffer_len = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_len)
        gdi32.GetDIBits(mfc_dc, bitmap, 0, height, buffer, ctypes.byref(bmpinfo), 0)
        
        arr = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        arr = arr[:, :, :3]  # Remove alpha channel
        
        if imageFilename:
            import cv2  # Will raise error if not available
            cv2.imwrite(imageFilename, arr)
        return arr

    finally:
        # Cleanup
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mfc_dc)
        user32.ReleaseDC(None, hdc)


user32 = ctypes.windll.user32

# Tweening functions
def linear(t):
    return t

def easeInOutQuad(t):
    return 2*t*t if t < 0.5 else -1 + (4 - 2*t)*t

def easeOutElastic(t):
    c4 = (2 * math.pi) / 3
    if t == 0:
        return 0
    elif t == 1:
        return 1
    return 2**(-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1

# Helper functions
def get_screen_size():
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

def get_position():
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y

def getActiveWindowTitle():
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value

def center(target=None):
    """
    Returns the center coordinates of:
    - A window (if target is a string title)
    - A screen region (if target is a box tuple (left, top, width, height))
    - The primary screen (if no target)
    """
    if isinstance(target, str):  # Window title
        hwnd = user32.FindWindowW(None, target)
        if not hwnd:
            raise ValueError(f"Window not found: {target}")
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return (
            (rect.left + rect.right) // 2,
            (rect.top + rect.bottom) // 2
        )
    elif isinstance(target, (tuple, list)) and len(target) >= 4:  # Region box
        left, top, width, height = target[:4]
        return (left + width // 2, top + height // 2)
    else:  # Primary screen center
        width, height = get_screen_size()
        return (width // 2, height // 2)


def get_virtual_screen_bounds():
    x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return x, y, x + width, y + height


def clip_region_to_virtual(region):
    x, y, w, h = region
    min_x, min_y, max_x, max_y = p.SCREEN

    x2 = max(x, min_x)
    y2 = max(y, min_y)

    x_end = min(x + w, max_x)
    y_end = min(y + h, max_y)

    w2 = x_end - x2
    h2 = y_end - y2

    if w2 <= 0 or h2 <= 0:
        return None

    return x2, y2, w2, h2


def _human_delay(min_delay=0.01, max_delay=0.03):
    time.sleep(random.uniform(min_delay, max_delay))


def _profile_value(profile, key, default):
    if profile is None:
        return default
    return profile.get(key, default)


def _sample_hold_seconds(kind, profile=None):
    """Sample hold duration from median/IQR and clamp to profile bounds."""
    if kind == "click":
        median_ms = float(_profile_value(profile, "click_hold_median_ms", 90.0))
        iqr_ms = float(_profile_value(profile, "click_hold_iqr_ms", 18.0))
        min_ms, max_ms = _profile_value(profile, "click_hold_bounds_ms", (38.0, 220.0))
    else:
        median_ms = float(_profile_value(profile, "key_hold_median_ms", 100.0))
        iqr_ms = float(_profile_value(profile, "key_hold_iqr_ms", 31.0))
        min_ms, max_ms = _profile_value(profile, "key_hold_bounds_ms", (32.0, 260.0))

    sigma_ms = max(1.0, iqr_ms / 1.349)
    sampled_ms = random.gauss(median_ms, sigma_ms)
    sampled_ms = max(float(min_ms), min(float(max_ms), sampled_ms))
    return sampled_ms / 1000.0


def mouseDown(button='left', delay=0.16, jitter=0.04):
    _fail_safe_check()
    _ensure_mouse_settings()
    _get_bridge().mouse_press(button=button)
    if delay > 0:
        _human_delay(delay, delay + max(0.0, jitter))
    _fail_safe_check()


def mouseUp(button='left', delay=0.16, jitter=0.05):
    _fail_safe_check()
    _get_bridge().mouse_release(button=button)
    if delay > 0:
        _human_delay(delay, delay + max(0.0, jitter))
    _fail_safe_check()


class WindowError(Exception): pass
class FailSafeException(Exception): pass
class ImageNotFoundException(Exception): pass
class PauseException(Exception):
    def __init__(self, name):
        super().__init__(name)
        self.window = name

# Global fail-safe settings
FAILSAFE_ENABLED = True


def _apply_macro_rhythm(profile=None):
    profile = profile or get_macro_profile()
    pause, (dx, dy) = maybe_rhythm_jitter(profile)

    if dx != 0 or dy != 0:
        _get_bridge().mouse_move_relative(dx, dy)
        _human_delay(0.004, 0.012)

    if pause > 0:
        time.sleep(pause)

    _fail_safe_check()

def set_failsafe(state=True):
    """Enable or disable the fail-safe feature"""
    global FAILSAFE_ENABLED
    FAILSAFE_ENABLED = state


def _fail_safe_check():
    """Check if mouse is in fail-safe position and raise exception if needed"""
    if not FAILSAFE_ENABLED:
        return
    
    name = getActiveWindowTitle()
    
    if p.LIMBUS_NAME not in name:
        restore_mouse_settings()
        raise PauseException(name)


def _within_target(a, b, size=(20.0, 20.0)):
    width, height = size if size else (20.0, 20.0)
    return (
        abs(float(a[0]) - float(b[0])) <= max(float(width), 0.0) / 2.0 and
        abs(float(a[1]) - float(b[1])) <= max(float(height), 0.0) / 2.0
    )


def _clamp_point_to_screen_bounds(x, y):
    min_x, min_y, max_x, max_y = p.SCREEN
    max_x = max(min_x, max_x - 1)
    max_y = max(min_y, max_y - 1)
    return (
        int(round(min(max(float(x), min_x), max_x))),
        int(round(min(max(float(y), min_y), max_y))),
    )


def _project_points_to_screen_bounds(points):
    min_x, min_y, max_x, max_y = p.SCREEN
    max_x = max(min_x, max_x - 1)
    max_y = max(min_y, max_y - 1)

    projected = np.asarray(points, dtype=float).copy()
    projected[:, 0] = np.clip(projected[:, 0], min_x, max_x)
    projected[:, 1] = np.clip(projected[:, 1], min_y, max_y)
    return projected


def _emit_rel_open_loop(dev, dx, dy):
    _get_bridge().mouse_move_relative(int(dx), int(dy))


def moveTo(x, y, duration=0, delay=0.0, tsize=(5.0, 5.0), offset_x=0, offset_y=0, curve=1, n_sub=None, inertia=False):
    _fail_safe_check()
    _ensure_mouse_settings()

    start_x, start_y = get_position()
    end_x = int(round(x + offset_x))
    end_y = int(round(y + offset_y))
    end_x, end_y = _clamp_point_to_screen_bounds(end_x, end_y)

    tsize = tsize if tsize else (20.0, 20.0)
    if _within_target((start_x, start_y), (end_x, end_y), tsize):
        return

    if delay > 0:
        profile = get_macro_profile()
        time.sleep(randomize_with_profile(delay, profile=profile, key="delay_jitter"))

    duration_override = duration if duration and duration > 0 else None

    while True:
        traj = build_trajectory(
            (start_x, start_y),
            (end_x, end_y),
            duration_override=duration_override,
            target_width=tsize[0],
            target_height=tsize[1],
            initial_velocity=get_inherited_velocity() if inertia else None,
            curviness=curve,
            n_submovements=n_sub
        )

        raw_path = _project_points_to_screen_bounds(traj["points"])
        times = traj["times"]

        raw_delta = execute_trajectory(None, raw_path, times, emit_func=_emit_rel_open_loop)
        start_x, start_y = get_position()

        if not np.any(np.abs(raw_delta) > 15.0) or \
           _within_target((start_x, start_y), (end_x, end_y), tsize):
            break

        update_pointer_scale(raw_delta, raw_path[0], (start_x, start_y))
        _fail_safe_check()

    update_inertia(raw_path, times)


def click(x=None, y=None, button='left', clicks=1, interval=0.15, duration=0.0, tsize=(5.0, 5.0), delay=0.03):
    _fail_safe_check()
    profile = get_macro_profile()
    _apply_macro_rhythm(profile)
    delay = randomize_with_profile(delay, profile=profile, key="delay_jitter")
    
    if x is not None and y is not None:
        moveTo(x, y, duration=duration, delay=delay+0.02, tsize=tsize)

    for i in range(clicks):
        _fail_safe_check()
        click_hold = _sample_hold_seconds("click", profile=profile)
        mouseDown(button, delay=click_hold, jitter=0.0)
        mouseUp(button, delay=delay)
        
        if interval > 0 and i < clicks - 1:
            time.sleep(randomize_with_profile(interval, profile=profile, key="click_interval_jitter"))
            _fail_safe_check()


def dragTo(x, y, duration=0.1, button='left', tsize=(5.0, 5.0), start_x=None, start_y=None, hook=False):
    _fail_safe_check()
    _apply_macro_rhythm()
    
    if start_x is not None and start_y is not None:
        moveTo(start_x, start_y, tsize=tsize)

    mouseDown(button, delay=0.03)
    moveTo(x, y, duration=duration, tsize=tsize, n_sub=1, curve=0.2, inertia=False)
    mouseUp(button, delay=0.03)

    if hook:
        mouseDown(button, delay=0.03)
        mouseUp(button, delay=0.03)
    _fail_safe_check()

def scroll(clicks, x=None, y=None):
    _fail_safe_check()
    _ensure_mouse_settings()
    _apply_macro_rhythm()
    if x is not None and y is not None:
        moveTo(x, y)

    direction = 1 if clicks > 0 else -1
    count = abs(int(clicks))
    for _ in range(count):
        _fail_safe_check()
        _get_bridge().mouse_scroll(direction)
        time.sleep(0.02)
    _human_delay()


def press(keys, presses=1, interval=0.1, delay=0.09):
    profile = get_macro_profile()
    _apply_macro_rhythm(profile)
    time.sleep(randomize_with_profile(delay, profile=profile, key="delay_jitter"))

    if isinstance(keys, str):
        keys = [keys]

    for _p in range(presses):
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            _fail_safe_check()
            _get_bridge().key_press(key)
            key_hold = _sample_hold_seconds("key", profile=profile)
            time.sleep(key_hold)

        for key in reversed(keys):
            _get_bridge().key_release(key)

        if interval > 0 and _p < presses - 1:
            time.sleep(randomize_with_profile(interval, profile=profile, key="key_interval_jitter"))
            _fail_safe_check()

def hotkey(*args, **kwargs):
    press(list(args), **kwargs)


def check_window():
    min_x, min_y, max_x, max_y = p.SCREEN
    left, top, width, height = p.WINDOW
    in_bounds = (
        left >= min_x and
        top >= min_y and
        left + width <= max_x and
        top + height <= max_y
    )
    if not in_bounds:
        raise WindowError("Window is partially or completely out of screen bounds!")

def set_window():
    hwnd = ctypes.windll.user32.FindWindowW(None, p.LIMBUS_NAME)

    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))

    pt = ctypes.wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))

    client_width = rect.right - rect.left
    client_height = rect.bottom - rect.top
    left, top = pt.x, pt.y

    left, top, target_width, target_height = p.resolve_window_rect(left, top, client_width, client_height)

    p.WINDOW = (left, top, target_width, target_height)
    p.SCREEN = get_virtual_screen_bounds()
    check_window()

    if not p.is_supported_aspect(client_width, client_height):
        p.WARNING(f"Game window ({client_width} x {client_height}) has an unsupported aspect ratio\nIt is recommended to set the game to 16:9 (1920 x 1080 or 1280 x 720)\nor 16:10 (2560 x 1600)")

    print("WINDOW:", p.WINDOW)
