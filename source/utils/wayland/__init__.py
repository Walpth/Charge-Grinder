from __future__ import annotations

import os
from typing import Optional

from .base import BaseCompositorBackend, WaylandBackendError, WindowInfo
from .hyprland import HyprlandBackend
from .kwin import KWinBackend
from .mango import MangoBackend
from .mutter import MutterBackend
from .pipewire_capture import (
    close_capture,
    get_capture,
    set_capture_window_region,
    set_default_source,
)
from .sway import SwayBackend


_CONTENT_ASPECT = 16 / 9

_backend: Optional[BaseCompositorBackend] = None
_last_window_frame: Optional[tuple[int, int, int, int]] = None


def _decoration_insets() -> tuple[int, int, int, int]:
    raw = os.environ.get("LINUX_BACKEND_WINDOW_DECORATION", "4,30,4,4").strip()
    try:
        parts = tuple(int(p) for p in raw.split(","))
    except ValueError:
        parts = ()
    if len(parts) == 4 and all(p >= 0 for p in parts):
        return parts
    raise WaylandBackendError(
        f"LINUX_BACKEND_WINDOW_DECORATION must be 'left,top,right,bottom' px, got {raw!r}"
    )


def _is_16_9(width: int, height: int, tol: float = 0.01) -> bool:
    return height > 0 and abs(width / height - _CONTENT_ASPECT) <= tol


def content_rect(left: int, top: int, width: int, height: int) -> tuple[int, int, int, int]:
    """Strip XWayland/Wine decorations, but only when the insets yield an exact 16:9 content rect."""
    if _is_16_9(width, height):
        return left, top, width, height
    bl, bt, br, bb = _decoration_insets()
    cw, ch = width - bl - br, height - bt - bb
    if cw > 0 and ch > 0 and _is_16_9(cw, ch):
        return left + bl, top + bt, cw, ch
    return left, top, width, height


def _session_order() -> list[type[BaseCompositorBackend]]:
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "").lower()
    ordered: list[type[BaseCompositorBackend]] = []

    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        ordered.append(HyprlandBackend)
    if os.environ.get("SWAYSOCK") or os.environ.get("I3SOCK"):
        ordered.append(SwayBackend)
    if os.environ.get("MANGO_INSTANCE_SIGNATURE"):
        ordered.append(MangoBackend)
    if "gnome" in desktop or "mutter" in desktop:
        ordered.append(MutterBackend)
    if "kde" in desktop or "plasma" in desktop or os.environ.get("KDE_FULL_SESSION"):
        ordered.append(KWinBackend)

    for cls in (MutterBackend, HyprlandBackend, SwayBackend, MangoBackend, KWinBackend):
        if cls not in ordered:
            ordered.append(cls)
    return ordered


def _make_backend() -> BaseCompositorBackend:
    requested = os.environ.get("WAYLAND_BACKEND", "").strip().lower()
    classes = _session_order()
    if requested:
        classes = [cls for cls in classes if cls.name == requested]
        if not classes:
            raise WaylandBackendError(f"Unknown WAYLAND_BACKEND={requested!r}")

    for cls in classes:
        if cls.available():
            backend = cls()
            if backend.preferred_pipewire_source:
                set_default_source(backend.preferred_pipewire_source)
            return backend

    supported = ", ".join(cls.name for cls in [KWinBackend, MutterBackend, HyprlandBackend, SwayBackend, MangoBackend])
    raise WaylandBackendError(
        "No supported Wayland compositor backend detected. "
        f"Set WAYLAND_BACKEND to one of: {supported}."
    )


def get_backend() -> BaseCompositorBackend:
    global _backend
    if _backend is None:
        _backend = _make_backend()
    return _backend


def get_virtual_screen_bounds():
    outputs = get_backend().outputs()
    min_x = min(x for x, y, w, h in outputs)
    min_y = min(y for x, y, w, h in outputs)
    max_x = max(x + w for x, y, w, h in outputs)
    max_y = max(y + h for x, y, w, h in outputs)
    return int(min_x), int(min_y), int(max_x), int(max_y)


def get_screen_size():
    min_x, min_y, max_x, max_y = get_virtual_screen_bounds()
    return max_x - min_x, max_y - min_y


def active_title() -> str:
    try:
        return get_backend().active_title()
    except Exception:
        return ""


def find_window(name: str) -> Optional[WindowInfo]:
    return get_backend().find_window(name)


def register_window_frame(frame: Optional[tuple[int, int, int, int]]) -> None:
    """Remember the portal-stream frame rect used to crop window captures."""
    global _last_window_frame
    _last_window_frame = frame


def prepare_window_capture(region: tuple[int, int, int, int]) -> None:
    target = tuple(region)
    set_capture_window_region(target, frame=_last_window_frame)
    get_capture().prepare_window(target, frame=_last_window_frame)


def screenshot(region=None):
    """BGR screenshot from the persistent PipeWire stream; intentionally no CLI-tool fallback (latency)."""
    return get_capture().screenshot(tuple(region) if region else None)


def close_pipewire():
    close_capture()


__all__ = [
    "WaylandBackendError",
    "WindowError",
    "WindowInfo",
    "get_backend",
    "get_virtual_screen_bounds",
    "get_screen_size",
    "active_title",
    "find_window",
    "content_rect",
    "register_window_frame",
    "prepare_window_capture",
    "screenshot",
    "close_pipewire",
]
