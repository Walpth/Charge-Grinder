import ctypes
from ctypes import wintypes
import time
import random
import math

import numpy as np

from .helpers import WindowError, human_delay


try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()


SM_XVIRTUALSCREEN = 76 
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


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


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
SM_SWAPBUTTON = 23
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

if ctypes.sizeof(ctypes.c_void_p) == 8:  # 64-bit system
    ULONG_PTR = ctypes.c_ulonglong
else:  # 32-bit system
    ULONG_PTR = ctypes.c_ulong

# Structures
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION)
    ]


def get_virtual_screen_bounds():
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return (x, y, width, height)


def screenshot(imageFilename=None, region=None, display=None):
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    
    if display:
        x, y, width, height = display
    else:
        x, y, width, height = get_virtual_screen_bounds()
    
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


def _send_input(inp):
    sent = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    if sent != 1:
        err = ctypes.get_last_error()
        raise OSError(f"SendInput failed (returned {sent}), GetLastError={err}")

def mouseDown(button='left', delay=0.09): 
    swapped = user32.GetSystemMetrics(SM_SWAPBUTTON)
    flags = {
        'left': MOUSEEVENTF_LEFTDOWN if not swapped else MOUSEEVENTF_RIGHTDOWN,
        'right': MOUSEEVENTF_RIGHTDOWN if not swapped else MOUSEEVENTF_LEFTDOWN,
        'middle': MOUSEEVENTF_MIDDLEDOWN
    }.get(button.lower(), MOUSEEVENTF_LEFTDOWN)
    
    inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=MOUSEINPUT(
        dx=0, dy=0, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0
    )))
    
    _send_input(inp)
    human_delay(delay, delay + 0.02)

def mouseUp(button='left', delay=0.09):
    swapped = user32.GetSystemMetrics(SM_SWAPBUTTON)
    flags = {
        'left': MOUSEEVENTF_LEFTUP if not swapped else MOUSEEVENTF_RIGHTUP,
        'right': MOUSEEVENTF_RIGHTUP if not swapped else MOUSEEVENTF_LEFTUP,
        'middle': MOUSEEVENTF_MIDDLEUP
    }.get(button.lower(), MOUSEEVENTF_LEFTUP)
    
    inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=MOUSEINPUT(
        dx=0, dy=0, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0
    )))
    _send_input(inp)
    human_delay(delay, delay + 0.02)


def _to_absolute(x, y):
    _, _, screen_w, screen_h = get_virtual_screen_bounds()
    if screen_w <= 1 or screen_h <= 1:
        raise RuntimeError("invalid screen size")

    nx = int(round(x * 65535.0 / (screen_w - 1)))
    ny = int(round(y * 65535.0 / (screen_h - 1)))

    nx = max(0, min(65535, nx))
    ny = max(0, min(65535, ny))
    return nx, ny

def send_mouse_move(x, y):
    abs_x, abs_y = _to_absolute(x, y)
    flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=MOUSEINPUT(
        dx=abs_x, dy=abs_y, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=0
    )))
    _send_input(inp)

def mouseDown_fast(button='left', delay=0.03):
    mouseDown(button, delay=delay)

def mouseUp_fast(button='left', delay=0.03):
    mouseUp(button, delay=delay)


def scroll(clicks):   
    inp = INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=MOUSEINPUT(
        dx=0, dy=0,
        mouseData=clicks * 120,
        dwFlags=MOUSEEVENTF_WHEEL,
        time=0, dwExtraInfo=0
    )))
    _send_input(inp)
    human_delay()

# Keyboard functions
VK_MAP = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
    'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
    's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35,
    '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
    'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'esc': 0x1B, 'enter': 0x0D, 'tab': 0x09, 'space': 0x20, 'backspace': 0x08,
    'delete': 0x2E, 'insert': 0x2D, 'home': 0x24, 'end': 0x23, 'pageup': 0x21,
    'pagedown': 0x22, 'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12, 'win': 0x5B,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27
}

def pressDown(keys, delay=0.01):
    for key in keys:
        vk = VK_MAP.get(key.lower(), 0)
        if vk:
            scan = user32.MapVirtualKeyW(vk, 0)
            inp = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(
                wVk=vk,
                wScan=scan,
                dwFlags=KEYEVENTF_SCANCODE,
                time=0, dwExtraInfo=0
            )))
            _send_input(inp)
            time.sleep(delay)

def pressUp(keys, delay=0.01):
    for key in reversed(keys):
        vk = VK_MAP.get(key.lower(), 0)
        if vk:
            scan = user32.MapVirtualKeyW(vk, 0)
            inp = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(
                wVk=vk,
                wScan=scan,
                dwFlags=KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP,
                time=0, dwExtraInfo=0
            )))
            _send_input(inp)
            time.sleep(delay)


def detect_client_rect(window_name: str):
    hwnd = ctypes.windll.user32.FindWindowW(None, window_name)
    if not hwnd:
        raise RuntimeError("Launch Limbus Company!")

    rect = wintypes.RECT()
    if not ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise WindowError("GetClientRect failed")

    pt = wintypes.POINT(0, 0)
    if not ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        raise WindowError("ClientToScreen failed")

    client_width = rect.right - rect.left
    client_height = rect.bottom - rect.top
    left, top = int(pt.x), int(pt.y)

    if client_width <= 0 or client_height <= 0:
        raise WindowError("Client area has zero or negative size")
    
    return left, top, client_width, client_height

def within_screen_check(left: int, top: int, width: int, height: int, display=None):
    if display:
        vx, vy, vw, vh = display
    else:
        vx, vy, vw, vh = get_virtual_screen_bounds()

    vright = vx + vw
    vbottom = vy + vh

    right = left + width
    bottom = top + height

    in_bounds = (
        left >= vx and
        top >= vy and
        right <= vright and
        bottom <= vbottom
    )
    if not in_bounds:
        raise WindowError("Window is partially or completely out of screen bounds!")