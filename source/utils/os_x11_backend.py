# Linux (X11) port
# Extra dependencies: python-xlib, mss

import atexit, signal, threading

import mss
import evdev
from evdev import UInput, ecodes as e
from Xlib import X, display, XK
import numpy as np, time, math, random

import source.utils.params as p
from source.utils.profiles import get_macro_profile, maybe_rhythm_jitter, randomize_with_profile
from source.utils.movement.builder import build_trajectory
from source.utils.movement.inertia import get_inherited_velocity, update_inertia
from source.utils.movement.pointer_gain import update_pointer_scale, execute_trajectory


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

# Display + root
_disp = display.Display()
_root = _disp.screen().root

FAILSAFE = True
FAILSAFE_ENABLED = True

def set_failsafe(state=True):
    global FAILSAFE_ENABLED
    FAILSAFE_ENABLED = state

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
    if not FAILSAFE_ENABLED:
        return "LimbusCompany"
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

def center(target=None):
    """
    Returns the center coordinates of:
     - A window (if target is string title)
     - A region (if target is a box tuple (left, top, width, height))
     - The primary screen (if no target)
    """
    if isinstance(target, str):
        w = _find_window_by_name(target)
        if not w:
            raise ValueError(f"Window not found: {target}")
        geom = w.get_geometry()
        # translate window coords to root coords
        try:
            tx = w.translate_coords(_root, 0, 0)
            left, top = tx.x, tx.y
        except Exception:
            left, top = geom.x, geom.y
        center_x = left + geom.width // 2
        center_y = top + geom.height // 2
        return center_x, center_y

    elif isinstance(target, (tuple, list)) and len(target) >= 4:
        left, top, width, height = target[:4]
        return (left + width // 2, top + height // 2)

    else:
        width, height = get_screen_size()
        return (width // 2, height // 2)
    

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
  

def screenshot(imageFilename=None, region=None):
    """
    Capture screenshot using XShm via mss (falls back to XGetImage if needed).
    region: (x, y, width, height)
    Returns numpy array in BGR order (height, width, 3) for cv2 compatibility.
    """
    with mss.mss() as sct:
        if region:
            min_x, min_y, _, _ = p.SCREEN
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


# --- UINPUT VIRTUAL DEVICE SETUP ---

def _print_device_data(config):
    print(*[f"{k}{' '*(12-len(k))}: {v}" for k, v in config.items()], sep="\n", end="\n\n")


MOUSE_FALLBACK = {
    'name': 'Logitech USB Receiver',
    'vendor': 0x046d,
    'product': 0xc52b,
    'version': 0x0111,
    'bustype': 0x03,
    'phys': 'usb-0000:00:14.0-1.2/input0',
    'events': {
        e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE, e.BTN_SIDE, e.BTN_EXTRA],
        e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL, e.REL_WHEEL_HI_RES],
        e.EV_MSC: [e.MSC_SCAN]
    },
    'input_props': []
}

_EVDEV_KEYSYM_MAP = {
    'enter': e.KEY_ENTER, 'esc': e.KEY_ESC, 'space': e.KEY_SPACE,
    'tab': e.KEY_TAB, 'backspace': e.KEY_BACKSPACE, 'delete': e.KEY_DELETE,
    'insert': e.KEY_INSERT, 'home': e.KEY_HOME, 'end': e.KEY_END,
    'pageup': e.KEY_PAGEUP, 'pagedown': e.KEY_PAGEDOWN,
    'shift': e.KEY_LEFTSHIFT, 'ctrl': e.KEY_LEFTCTRL, 
    'alt': e.KEY_LEFTALT, 'win': e.KEY_LEFTMETA,
    'rightshift': e.KEY_RIGHTSHIFT, 'rightctrl': e.KEY_RIGHTCTRL,
    'rightalt': e.KEY_RIGHTALT, 'rightwin': e.KEY_RIGHTMETA,
    'up': e.KEY_UP, 'down': e.KEY_DOWN, 'left': e.KEY_LEFT, 'right': e.KEY_RIGHT,
    'capslock': e.KEY_CAPSLOCK, 'numlock': e.KEY_NUMLOCK, 'scrolllock': e.KEY_SCROLLLOCK,
    'printscreen': e.KEY_SYSRQ, 'pause': e.KEY_PAUSE,
}

_symbols = {
    '-': e.KEY_MINUS, '=': e.KEY_EQUAL, '[': e.KEY_LEFTBRACE, ']': e.KEY_RIGHTBRACE,
    ';': e.KEY_SEMICOLON, "'": e.KEY_APOSTROPHE, '`': e.KEY_GRAVE, '\\': e.KEY_BACKSLASH,
    ',': e.KEY_COMMA, '.': e.KEY_DOT, '/': e.KEY_SLASH,
}

_EVDEV_KEYSYM_MAP.update(_symbols)

for char in "abcdefghijklmnopqrstuvwxyz":
    _EVDEV_KEYSYM_MAP[char] = getattr(e, f"KEY_{char.upper()}")
for num in "0123456789":
    _EVDEV_KEYSYM_MAP[num] = getattr(e, f"KEY_{num}")

for i in range(1, 25):
    _EVDEV_KEYSYM_MAP[f'f{i}'] = getattr(e, f"KEY_F{i}")

_numpad = {
    'kp0': e.KEY_KP0, 'kp1': e.KEY_KP1, 'kp2': e.KEY_KP2, 'kp3': e.KEY_KP3,
    'kp4': e.KEY_KP4, 'kp5': e.KEY_KP5, 'kp6': e.KEY_KP6, 'kp7': e.KEY_KP7,
    'kp8': e.KEY_KP8, 'kp9': e.KEY_KP9, 'kpdot': e.KEY_KPDOT, 
    'kpenter': e.KEY_KPENTER, 'kpplus': e.KEY_KPPLUS, 'kpminus': e.KEY_KPMINUS,
    'kpasterisk': e.KEY_KPASTERISK, 'kpslash': e.KEY_KPSLASH, 'kpequal': e.KEY_KPEQUAL,
}
_EVDEV_KEYSYM_MAP.update(_numpad)

_media = {
    'mute': e.KEY_MUTE, 'volumedown': e.KEY_VOLUMEDOWN, 'volumeup': e.KEY_VOLUMEUP,
    'playpause': e.KEY_PLAYPAUSE, 'stop': e.KEY_STOPCD, 'next': e.KEY_NEXTSONG,
    'previous': e.KEY_PREVIOUSSONG, 'search': e.KEY_SEARCH, 'email': e.KEY_EMAIL,
    'calc': e.KEY_CALC, 'computer': e.KEY_COMPUTER,
}
_EVDEV_KEYSYM_MAP.update(_media)

_safe_keys = sorted(list(set(_EVDEV_KEYSYM_MAP.values())))

KEYBOARD_FALLBACK = {
    'name': 'Dell USB Keyboard',
    'vendor': 0x413c,
    'product': 0x2003,
    'version': 0x0111,
    'bustype': 0x03,
    'phys': 'usb-0000:00:14.0-1.3/input0',
    'events': {
        e.EV_KEY: _safe_keys, 
        e.EV_LED: [e.LED_NUML, e.LED_CAPSL, e.LED_SCROLLL, e.LED_COMPOSE, e.LED_KANA],
        e.EV_MSC: [e.MSC_SCAN],
    },
    'input_props': []
}

mouse = None
keyboard = None
_uinput_error = None
_uinput_init_started = False
_uinput_ready = threading.Event()
_uinput_lock = threading.Lock()

def clone_device(path: str) -> UInput:
    real = evdev.InputDevice(path)
    caps = real.capabilities()
    
    if e.EV_KEY in caps:
        caps[e.EV_KEY] = list(set(caps[e.EV_KEY] + _safe_keys))
    else:
        caps[e.EV_KEY] = _safe_keys
    
    if e.EV_MSC not in caps:
        caps[e.EV_MSC] = [e.MSC_SCAN]
    elif e.MSC_SCAN not in caps[e.EV_MSC]:
        caps[e.EV_MSC].append(e.MSC_SCAN)

    if e.EV_REP not in caps:
        caps[e.EV_REP] = [e.REP_DELAY, e.REP_PERIOD]
    
    kwargs = {
        "name": real.name,
        "vendor": real.info.vendor,
        "product": real.info.product,
        "version": real.info.version,
        "bustype": real.info.bustype,
        "phys": real.phys if real.phys else "usb-0000:00:14.0-1/input0",
        "input_props": real.input_props(),
    }
    # raise Exception
    device = UInput.from_device(real, filtered_types=(e.EV_SYN, e.EV_FF, e.EV_REP), **kwargs)
    _print_device_data(kwargs)
    return device


def _is_virtual(dev):
    name = (dev.name or "").lower()
    phys = (dev.phys or "").lower()
    
    if any(x in name for x in ["virtual", "uinput", "keyd", "python"]):
        return True
    if not phys or phys.startswith("py-evdev"):
        return True
    return False

def _is_touchpad(caps, dname):
    abs_caps = caps.get(e.EV_ABS, [])
    abs_codes = [cap[0] for cap in abs_caps] if abs_caps else []
    key_caps = caps.get(e.EV_KEY, [])
    
    is_touchpad = (
        # Multi-touch capabilities
        e.ABS_MT_SLOT in abs_codes or
        e.ABS_MT_POSITION_X in abs_codes or
        e.ABS_MT_POSITION_Y in abs_codes or
        
        # Pressure/touch sensors
        e.ABS_PRESSURE in abs_codes or
        
        # Touchpad-specific buttons
        e.BTN_TOOL_FINGER in key_caps or
        e.BTN_TOUCH in key_caps or
        e.BTN_TOOL_DOUBLETAP in key_caps or
        e.BTN_TOOL_TRIPLETAP in key_caps or
        
        # Absolute positioning (touchpads report abs x/y)
        (e.ABS_X in abs_codes and e.ABS_Y in abs_codes) or
        
        # Name-based detection
        any(name in (dname or "").lower() 
            for name in ["touchpad", "trackpad", "synaptics", 
                        "elan", "clickpad", "glidepoint"])
    )
    return is_touchpad

def _pick_device_paths():
    paths = evdev.list_devices()
    mouse_path = None
    mouse_name = None
    kbd_data = {}
    kbd_candidates = []

    for path in paths:
        try:
            dev = evdev.InputDevice(path)
            
            if _is_virtual(dev):
                continue

            caps = dev.capabilities()
            rel_caps = caps.get(e.EV_REL, [])

            # 1. Mouse Selection (Must have Rel X/Y)
            if e.REL_X in rel_caps and e.REL_Y in rel_caps:
                if _is_touchpad(caps, dev.name):
                    continue

                if mouse_path is None:
                    mouse_path = path
                    mouse_name = dev.name.lower()
                continue

            kbd_data[path] = {"dev": dev, "key_caps": caps.get(e.EV_KEY, [])}
        
        except Exception:
            continue
        
    for path in kbd_data:
        try:
            dev = kbd_data[path]["dev"]
            key_caps = kbd_data[path]["key_caps"]

            # 2. Keyboard Selection
            # Hardware keyboards usually have the 'ESC' key and a high count
            if e.KEY_ESC in key_caps and len(key_caps) > 50:
                name = (dev.name or "").lower()
                phys = (dev.phys or "").lower()
                score = 0
                
                if dev.info.bustype == e.BUS_USB:
                    score += 20
                if "keyboard" in name or "kbd" in name:
                    score += 10
                if mouse_name and mouse_name in name:
                    score -= 30

                if phys.endswith("/input0"):
                        score += 50  # Huge bonus for primary typing endpoint
                elif phys.endswith("/input1") or phys.endswith("/input2"):
                        score -= 50  # Massive penalty for media/NKRO endpoints
                kbd_candidates.append((score, path))

        except Exception:
            continue

    if kbd_candidates:
        kbd_candidates.sort(key=lambda x: x[0], reverse=True)
        keyboard_path = kbd_candidates[0][1]
    else:
        keyboard_path = None

    return mouse_path, keyboard_path


def _init_uinput_devices():
    """Initialize uinput devices once and publish result to globals."""
    global mouse, keyboard, _uinput_error
    try:
        mouse_path, keyboard_path = _pick_device_paths()

        if mouse_path:
            try:
                print(f"Cloning mouse from {mouse_path}")
                local_mouse = clone_device(mouse_path)
            except Exception as ex:
                print(f"[!] Mouse clone failed ({mouse_path}): {ex}")
                print("No mouse found – using fallback.")
                local_mouse = UInput(**MOUSE_FALLBACK)
                _print_device_data(MOUSE_FALLBACK)
        else:
            print("No mouse found – using fallback.")
            local_mouse = UInput(**MOUSE_FALLBACK)
            _print_device_data(MOUSE_FALLBACK)

        if keyboard_path:
            try:
                print(f"Cloning keyboard from {keyboard_path}")
                local_keyboard = clone_device(keyboard_path)
            except Exception as ex:
                print(f"[!] Keyboard clone failed ({keyboard_path}): {ex}")
                print("No keyboard found – using fallback.")
                local_keyboard = UInput(**KEYBOARD_FALLBACK)
                _print_device_data(KEYBOARD_FALLBACK)
        else:
            print("No keyboard found – using fallback.")
            local_keyboard = UInput(**KEYBOARD_FALLBACK)
            _print_device_data(KEYBOARD_FALLBACK)

        with _uinput_lock:
            mouse = local_mouse
            keyboard = local_keyboard
    except Exception as ex:
        _uinput_error = ex
    finally:
        _uinput_ready.set()

def _prewarm_uinput_async():
    """Start async uinput init so startup can continue immediately."""
    global _uinput_init_started
    with _uinput_lock:
        if _uinput_init_started:
            return
        _uinput_init_started = True
    threading.Thread(target=_init_uinput_devices, name="uinput-init", daemon=True).start()

def _ensure_uinput_ready():
    _prewarm_uinput_async()
    _uinput_ready.wait()
    if _uinput_error is not None:
        raise _uinput_error


def _get_mouse():
    _ensure_uinput_ready()
    return mouse

def _get_keyboard():
    _ensure_uinput_ready()
    return keyboard

# Map logical buttons
_BUTTON_MAP = {'left': e.BTN_LEFT, 'middle': e.BTN_MIDDLE, 'right': e.BTN_RIGHT}

def release_all(signum=None, frame=None):
    for dev in (mouse, keyboard):
        if dev is None:
            continue
        for btn in  _BUTTON_MAP.values():
            try:
                dev.write(e.EV_KEY, btn, 0)
            except Exception:
                pass
        for key in _safe_keys:
            try:
                dev.write(e.EV_KEY, key, 0)
            except Exception:
                pass
        try:
            dev.syn()
        except Exception:
            pass

signal.signal(signal.SIGINT, release_all)
signal.signal(signal.SIGTERM, release_all)
atexit.register(release_all)

# Kick off async init immediately; first input call blocks only if still warming up.
_prewarm_uinput_async()

def _fail_safe_check():
    """Check fail-safe"""
    if not FAILSAFE_ENABLED:
        return

    name = getActiveWindowTitle()

    if p.LIMBUS_NAME not in name:
        release_all()
        raise PauseException(name)

class WindowError(Exception): pass
class FailSafeException(Exception): pass
class ImageNotFoundException(Exception): pass
class PauseException(Exception):
    def __init__(self, name):
        super().__init__(name)
        self.window = name

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
    dev = _get_mouse()
    _btn = _BUTTON_MAP.get(button.lower(), e.BTN_LEFT)
    dev.write(e.EV_KEY, _btn, 1)
    dev.syn()
    if delay > 0:
        _human_delay(delay, delay + max(0.0, jitter))
    _fail_safe_check()

def mouseUp(button='left', delay=0.16, jitter=0.05):
    _fail_safe_check()
    dev = _get_mouse()
    _btn = _BUTTON_MAP.get(button.lower(), e.BTN_LEFT)
    dev.write(e.EV_KEY, _btn, 0)
    dev.syn()
    if delay > 0:
        _human_delay(delay, delay + max(0.0, jitter))
    _fail_safe_check()

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
    """Emit a relative movement step using rounded carry to preserve sub-pixel intent."""
    ix = int(round(dx))
    iy = int(round(dy))
    if ix == 0 and iy == 0:
        return
    dev.write(e.EV_REL, e.REL_X, ix)
    dev.write(e.EV_REL, e.REL_Y, iy)
    dev.syn()


def _apply_macro_rhythm(profile=None):
    _fail_safe_check()
    profile = profile or get_macro_profile()
    pause, (dx, dy) = maybe_rhythm_jitter(profile)
    dev = _get_mouse()

    if dx != 0 or dy != 0:
        dev.write(e.EV_REL, e.REL_X, dx)
        dev.write(e.EV_REL, e.REL_Y, dy)
        dev.syn()
        _human_delay(0.004, 0.012)

    if pause > 0:
        time.sleep(pause)
    _fail_safe_check()


def moveTo(x, y, duration=0, delay=0.0, tsize=(3.0, 3.0), offset_x=0, offset_y=0, curve=1, n_sub=None, inertia=False):
    _fail_safe_check()
    dev = _get_mouse()
    
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

        raw_delta = execute_trajectory(dev, raw_path, times, emit_func=_emit_rel_open_loop)
        start_x, start_y = get_position()

        if not np.any(np.abs(raw_delta) > 15.0) or \
           _within_target((start_x, start_y), (end_x, end_y), tsize):
            break

        update_pointer_scale(raw_delta, raw_path[0], (start_x, start_y))
        _fail_safe_check()

    update_inertia(raw_path, times)


def click(x=None, y=None, button='left', clicks=1, interval=0.15, duration=0.0, tsize=(3.0, 3.0), delay=0.03):
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


def dragTo(x, y, duration=0.1, button='left', tsize=(3.0, 3.0), start_x=None, start_y=None, hook=False):
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
    """Scroll vertically: positive clicks -> up, negative -> down."""
    _fail_safe_check()
    dev = _get_mouse()
    _apply_macro_rhythm()
    if x is not None and y is not None:
        moveTo(x, y)
    direction = 1 if clicks > 0 else -1
    count = abs(int(clicks))
    
    for _ in range(count):
        _fail_safe_check()
        dev.write(e.EV_REL, e.REL_WHEEL, direction)
        # Emit the hi-res wheel tick when supported (120 units per detent).
        if hasattr(e, "REL_WHEEL_HI_RES"):
            try:
                dev.write(e.EV_REL, e.REL_WHEEL_HI_RES, direction * 120)
            except OSError:
                pass
        dev.syn()
        time.sleep(0.02)
    _human_delay()

# Keyboard functions
_X_KEYCODE_CACHE = {}

def _get_x_keycode(keysym):
    """Get X keycode for a keysym, respecting current XKB layout, with caching."""
    if keysym in _X_KEYCODE_CACHE:
        return _X_KEYCODE_CACHE[keysym]

    keycode = _disp.keysym_to_keycode(keysym)
    # X keycode 0 means "no key"
    result = keycode if keycode != 0 else None
    
    _X_KEYCODE_CACHE[keysym] = result
    return result

# Map lowercase letters and numbers to X keysyms for X11 lookup
_ASCII_TO_XK = {}
for c in "abcdefghijklmnopqrstuvwxyz":
    _ASCII_TO_XK[c] = getattr(XK, f"XK_{c}")
for c in "0123456789":
    _ASCII_TO_XK[c] = getattr(XK, f"XK_{c}")
# Add symbols
_ASCII_TO_XK.update({
    '-': XK.XK_minus, '=': XK.XK_equal, '[': XK.XK_bracketleft, ']': XK.XK_bracketright,
    ';': XK.XK_semicolon, "'": XK.XK_apostrophe, '`': XK.XK_grave, '\\': XK.XK_backslash,
    ',': XK.XK_comma, '.': XK.XK_period, '/': XK.XK_slash, ' ': XK.XK_space,
})

def _key_to_ecode(key):
    """Convert key name to evdev scancode using layout-aware X11 mapping."""
    key_lower = key.lower()
    
    # LETTERS & SYMBOLS
    if key_lower in _ASCII_TO_XK:
        xk = _ASCII_TO_XK[key_lower]
        x_keycode = _get_x_keycode(xk)
        
        if x_keycode is not None:
            # Shift the X11 code to match evdev
            evdev_code = x_keycode - 8
            return evdev_code
            
    if key_lower in _EVDEV_KEYSYM_MAP:
        return _EVDEV_KEYSYM_MAP[key_lower]
    
    return None

def press(keys, presses=1, interval=0.1, delay=0.09):
    dev = _get_keyboard()
    profile = get_macro_profile()
    _apply_macro_rhythm(profile)
    time.sleep(randomize_with_profile(delay, profile=profile, key="delay_jitter"))
    
    for _p in range(presses):
        if isinstance(keys, str):
            keys = [keys]

        ecodes = []
        for key in keys:
            # print(f"Pressing key: {key}")
            _fail_safe_check()
            kc = _key_to_ecode(key)
            if not kc:
                continue
            ecodes.append(kc)
            dev.write(e.EV_KEY, kc, 1) # Press
            dev.syn()
            key_hold = _sample_hold_seconds("key", profile=profile)
            time.sleep(key_hold)

        for kc in reversed(ecodes):
            dev.write(e.EV_KEY, kc, 0) # Release
            dev.syn()

        if interval > 0 and _p < presses - 1:
            time.sleep(randomize_with_profile(interval, profile=profile, key="key_interval_jitter"))
            _fail_safe_check()

def hotkey(*args, **kwargs):
    press(list(args), **kwargs)


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
    """
    Find window by p.LIMBUS_NAME, calculate its client center and set p.WINDOW
    to a centered 16:9 region for wide clients, or the full client area for
    16:9/16:10 clients (like Windows module).
    """
    w = _find_window_by_name(p.LIMBUS_NAME)
    if not w:
        raise WindowError(f"Window '{p.LIMBUS_NAME}' not found.")

    _disp.sync()
    try:
        geom = w.get_geometry()
    except Exception:
        raise WindowError(f"Window '{p.LIMBUS_NAME}' not found.")

    client_width, client_height = geom.width, geom.height

    left, top = get_absolute_position(w)
    left, top, target_width, target_height = p.resolve_window_rect(left, top, client_width, client_height)

    p.WINDOW = (left, top, target_width, target_height)
    p.SCREEN = get_virtual_screen_bounds()
    check_window()

    if not p.is_supported_aspect(client_width, client_height):
        p.WARNING(f"Game window ({client_width} x {client_height}) has an unsupported aspect ratio\nIt is recommended to set the game to 16:9 (1920 x 1080 or 1280 x 720)\nor 16:10 (2560 x 1600)")

    print("WINDOW:", p.WINDOW)
