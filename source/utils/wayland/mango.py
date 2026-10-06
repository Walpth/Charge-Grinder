from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any, Iterator, Optional

from .base import BaseCompositorBackend, Snapshot, WaylandBackendError, WindowInfo


class MangoBackend(BaseCompositorBackend):
    """mangoWM backend talking to its line-based JSON IPC socket.

    Protocol (mango src/ipc/ipc.c): the compositor listens on the Unix socket
    named by MANGO_INSTANCE_SIGNATURE (which stores the socket *path*, unlike
    Hyprland's signature). Commands are a single "\n"-terminated line;
    responses are newline-delimited JSON. `get` pushes one JSON object and the
    connection closes afterwards, so every query opens a fresh socket. `watch`
    registers the connection and pushes the initial state followed by one JSON
    object per state change, indefinitely.
    Client geometry is already absolute layout coordinates (c->geom), so no
    per-monitor translation is needed.
    """

    name = "mango"

    def __init__(self):
        super().__init__()
        self._event_thread_started = False
        self._event_thread_lock = threading.Lock()

    @classmethod
    def _socket_path(cls) -> Optional[Path]:
        path = os.environ.get("MANGO_INSTANCE_SIGNATURE")
        return Path(path) if path else None

    @classmethod
    def available(cls) -> bool:
        sock = cls._socket_path()
        return bool(sock and sock.exists())

    @staticmethod
    def _connect(path: Path, *, timeout: float = 1.0) -> socket.socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect(str(path))
        except OSError as exc:
            sock.close()
            raise WaylandBackendError(f"Could not connect to mango IPC socket {path}: {exc}") from exc
        return sock

    def _send(self, command: str, *, timeout: float = 1.0) -> str:
        """Send a one-shot `get` command and return the last received JSON line."""
        path = self._socket_path()
        if not path:
            raise WaylandBackendError("MANGO_INSTANCE_SIGNATURE is not set")
        with self._connect(path, timeout=timeout) as sock:
            sock.sendall(f"{command}\n".encode("utf-8"))
            sock.shutdown(socket.SHUT_WR)

            chunks: list[bytes] = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)

        lines = raw.decode("utf-8", errors="replace").strip().splitlines()
        if not lines:
            raise WaylandBackendError(f"Mango IPC returned no data for '{command}'")
        return lines[-1]

    def _send_json(self, command: str) -> Any:
        raw = self._send(command)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise WaylandBackendError(f"Mango IPC returned non-JSON for '{command}': {raw[:200]!r}") from exc

    @staticmethod
    def _iter_lines(sock: socket.socket) -> Iterator[str]:
        buffer = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                return
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                yield line.decode("utf-8", errors="replace")

    def _start_event_listener_once(self) -> None:
        with self._event_thread_lock:
            if self._event_thread_started:
                return
            self._event_thread_started = True

        def run_listener() -> None:
            while True:
                path = self._socket_path()
                if not path:
                    time.sleep(1.0)
                    continue
                try:
                    with self._connect(path, timeout=1.0) as sock:
                        sock.sendall(b"watch all-clients\n")
                        # NOTE: no SHUT_WR here: the watch handler removes the
                        # client when recv() returns 0 (half-close == removal).
                        self._invalidate_cache()

                        sock.settimeout(None)
                        for line in self._iter_lines(sock):
                            if line.strip():
                                self._invalidate_cache()
                except Exception:
                    pass
                time.sleep(1.0)

        threading.Thread(target=run_listener, name="mango-ipc-events", daemon=True).start()

    def _raw_snapshot(self) -> Snapshot:
        self._start_event_listener_once()
        windows, active_title = self._windows()
        return Snapshot(
            backend=self.name,
            active_title=active_title,
            windows=windows,
            outputs=self._outputs(),
            pointer=None,
            keyboard_layout=self._keyboard_layout(),
        )

    def _windows(self) -> tuple[list[WindowInfo], str]:
        data = self._send_json("get all-clients")
        windows: list[WindowInfo] = []
        active_title = ""
        for item in data.get("clients") or []:
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            if width <= 0 or height <= 0:
                continue
            windows.append(WindowInfo(
                title=str(item.get("title") or ""),
                left=int(item.get("x") or 0),
                top=int(item.get("y") or 0),
                width=width,
                height=height,
                app_id=str(item.get("appid") or ""),
                wm_class="",
                backend=self.name,
            ))
            if item.get("is_focused"):
                active_title = str(item.get("title") or "")
        return windows, active_title

    def _outputs(self) -> list[tuple[int, int, int, int]]:
        data = self._send_json("get all-monitors")
        result: list[tuple[int, int, int, int]] = []
        for mon in data.get("monitors") or []:
            x, y = int(mon.get("x") or 0), int(mon.get("y") or 0)
            w, h = int(mon.get("width") or 0), int(mon.get("height") or 0)
            if w > 0 and h > 0:
                result.append((x, y, w, h))
        if not result:
            raise WaylandBackendError("Mango returned no monitors")
        return result

    def _keyboard_layout(self):
        try:
            data = self._send_json("get keyboardlayout")
            if isinstance(data, dict) and data.get("layout"):
                return {"source": "mango ipc get keyboardlayout", "layout": data["layout"]}
        except Exception:
            pass
        return None
