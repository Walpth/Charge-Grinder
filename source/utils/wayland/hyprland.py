from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .base import BaseCompositorBackend, Snapshot, WaylandBackendError, WindowInfo, run_json, which


class HyprlandBackend(BaseCompositorBackend):
    """Hyprland backend over its Unix IPC sockets; hyprctl only as a last-resort fallback."""

    name = "hyprland"
    # portal window capture is unreliable on Hyprland (streams the screen instead)
    preferred_pipewire_source = "monitor"

    def __init__(self):
        super().__init__()
        self._event_thread_started = False
        self._event_thread_lock = threading.Lock()

    @classmethod
    def _runtime_dir(cls) -> Optional[Path]:
        his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
        if not his or not xdg_runtime:
            return None
        return Path(xdg_runtime) / "hypr" / his

    @classmethod
    def _request_socket_path(cls) -> Optional[Path]:
        base = cls._runtime_dir()
        return base / ".socket.sock" if base else None

    @classmethod
    def _event_socket_path(cls) -> Optional[Path]:
        base = cls._runtime_dir()
        return base / ".socket2.sock" if base else None

    @classmethod
    def available(cls) -> bool:
        sock = cls._request_socket_path()
        if sock and sock.exists():
            return True
        # Compatibility only: allows diagnostics under odd environments.
        if which("hyprctl"):
            try:
                run_json(["hyprctl", "-j", "monitors"], timeout=1.0)
                return True
            except Exception:
                return False
        return False

    def _ipc(self, command: str, *, timeout: float = 1.0) -> str:
        sock_path = self._request_socket_path()
        if sock_path and sock_path.exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                    sock.settimeout(timeout)
                    sock.connect(str(sock_path))
                    sock.sendall(command.encode("utf-8"))
                    chunks: list[bytes] = []
                    while True:
                        chunk = sock.recv(65536)
                        if not chunk:
                            break
                        chunks.append(chunk)
                return b"".join(chunks).decode("utf-8", errors="replace")
            except OSError as exc:
                raise WaylandBackendError(f"Hyprland IPC failed for {command!r}: {exc}") from exc

        # Compatibility fallback; not the production hot path.
        if not which("hyprctl"):
            raise WaylandBackendError("Hyprland IPC socket not found and hyprctl is unavailable")
        if command.startswith("j/"):
            subcmd = command[2:]
            data = run_json(["hyprctl", "-j", subcmd], timeout=timeout)
            return json.dumps(data)
        from .base import run
        return run(["hyprctl", command], timeout=timeout)

    def _ipc_json(self, subcommand: str) -> Any:
        raw = self._ipc(f"j/{subcommand}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise WaylandBackendError(f"Hyprland IPC returned non-JSON for {subcommand}: {raw[:200]!r}") from exc

    def _invalidate_cache(self) -> None:
        super()._invalidate_cache()

    def _start_event_listener_once(self) -> None:
        with self._event_thread_lock:
            if self._event_thread_started:
                return
            self._event_thread_started = True

        sock_path = self._event_socket_path()
        if not sock_path or not sock_path.exists():
            return

        def run_listener() -> None:
            while True:
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                        sock.settimeout(None)
                        sock.connect(str(sock_path))
                        self._invalidate_cache()
                        buf = b""
                        while True:
                            data = sock.recv(4096)
                            if not data:
                                break
                            buf += data
                            while b"\n" in buf:
                                line, buf = buf.split(b"\n", 1)
                                event = line.decode("utf-8", errors="ignore")
                                if event.startswith((
                                    "activewindow",
                                    "activewindowv2",
                                    "openwindow",
                                    "closewindow",
                                    "movewindow",
                                    "resizewindow",
                                    "windowtitle",
                                    "focusedmon",
                                    "monitoradded",
                                    "monitorremoved",
                                    "configreloaded",
                                    "activelayout",
                                )):
                                    self._invalidate_cache()
                except Exception:
                    pass
                time.sleep(1.0)

        threading.Thread(target=run_listener, name="hyprland-ipc-events", daemon=True).start()

    def _active_title(self) -> str:
        try:
            data = self._ipc_json("activewindow")
            return str(data.get("title") or data.get("class") or "")
        except Exception:
            return ""

    def _windows(self) -> list[WindowInfo]:
        data = self._ipc_json("clients")
        result: list[WindowInfo] = []
        for item in data or []:
            if item.get("mapped") is False or item.get("hidden") is True:
                continue
            at = item.get("at") or [0, 0]
            size = item.get("size") or [0, 0]
            if len(at) < 2 or len(size) < 2:
                continue
            width = int(size[0])
            height = int(size[1])
            if width <= 0 or height <= 0:
                continue
            result.append(WindowInfo(
                title=str(item.get("title") or ""),
                left=int(at[0]),
                top=int(at[1]),
                width=width,
                height=height,
                app_id=str(item.get("initialClass") or item.get("class") or ""),
                wm_class=str(item.get("class") or ""),
                backend=self.name,
            ))
        return result

    def _outputs(self) -> list[tuple[int, int, int, int]]:
        data = self._ipc_json("monitors")
        result: list[tuple[int, int, int, int]] = []
        for mon in data or []:
            if mon.get("disabled") is True:
                continue
            x = int(mon.get("x", 0))
            y = int(mon.get("y", 0))
            try:
                scale = float(mon.get("scale", 1.0) or 1.0)
            except (TypeError, ValueError):
                scale = 1.0
            if scale <= 0:
                scale = 1.0
            w = int(round(int(mon.get("width", 0)) / scale))
            h = int(round(int(mon.get("height", 0)) / scale))
            if w > 0 and h > 0:
                result.append((x, y, w, h))
        if not result:
            raise WaylandBackendError("Hyprland returned no active monitors")
        return result

    def _keyboard_layout(self):
        try:
            data = self._ipc_json("devices")
            keyboards = data.get("keyboards") or [] if isinstance(data, dict) else []
            active = None
            for kb in keyboards:
                if kb.get("main") is True:
                    active = kb
                    break
            if active is None and keyboards:
                active = keyboards[0]
            if active:
                return {
                    "source": "hyprland-ipc devices",
                    "active_keymap": active.get("active_keymap"),
                    "layout": active.get("layout"),
                    "name": active.get("name"),
                }
        except Exception:
            pass
        return None

    def _raw_snapshot(self) -> Snapshot:
        self._start_event_listener_once()
        return Snapshot(
            backend=self.name,
            active_title=self._active_title(),
            windows=self._windows(),
            outputs=self._outputs(),
            pointer=None,
            keyboard_layout=self._keyboard_layout(),
        )