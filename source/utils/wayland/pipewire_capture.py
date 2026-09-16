from __future__ import annotations

import atexit
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .base import WaylandBackendError, which


PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"
REQUEST_IFACE = "org.freedesktop.portal.Request"
SESSION_IFACE = "org.freedesktop.portal.Session"

SOURCE_MONITOR = 1
SOURCE_WINDOW = 2
CURSOR_HIDDEN = 1
CURSOR_EMBEDDED = 2

SCALE_AXIS_TOLERANCE = 0.005


class _PortalSetupError(WaylandBackendError):
    """Portal/session setup failed. Do not retry automatically."""

    def __init__(self, message: str, *, method: Optional[str] = None, response: Optional[int] = None):
        super().__init__(message)
        self.method = method
        self.response = response


class _StreamRuntimeError(WaylandBackendError):
    """PipeWire/GStreamer stream failed after portal setup. Safe to restart."""


def _log(message: str) -> None:
    value = os.environ.get("LINUX_BACKEND_PIPEWIRE_LOG", "0").strip().lower()
    if value in {"", "0", "false", "no", "off"}:
        return
    print(f"[pipewire-screenshot] {message}", flush=True)


@dataclass(frozen=True)
class _PortalStream:
    node_id: int
    target: str
    target_is_serial: bool
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0


@dataclass
class _Frame:
    image: Any
    left: int
    top: int
    width: int
    height: int
    timestamp: float


def _trim_to_frame(image: Any, frame_rect: tuple[int, int, int, int]) -> Any:
    img_h, img_w = image.shape[:2]
    fw, fh = int(frame_rect[2]), int(frame_rect[3])
    if fw <= 0 or fh <= 0 or img_w <= 0 or img_h <= 0:
        return image

    rx, ry = img_w / fw, img_h / fh
    if abs(rx - ry) <= SCALE_AXIS_TOLERANCE * max(rx, ry):
        return image

    if image[-1].any() and image[:, -1].any():
        return image
    nonzero = image.any(axis=2)
    cols = nonzero.any(axis=0).nonzero()[0]
    rows = nonzero.any(axis=1).nonzero()[0]
    if cols.size == 0 or rows.size == 0:
        return image
    right = int(cols.max()) + 1
    bottom = int(rows.max()) + 1
    if right >= img_w and bottom >= img_h:
        return image
    return image[:bottom, :right]


def _crop_client(image: Any, frame_rect, client_rect, override_insets=None) -> Any:
    """Cut the logical client rect out of a physical-pixel frame image (HiDPI-aware)."""
    img_h, img_w = image.shape[:2]
    fl, ft, fw, fh = (int(v) for v in frame_rect)
    if override_insets is not None:
        il, it, ir, ib = override_insets
        client_rect = (fl + il, ft + it, fw - il - ir, fh - it - ib)
    cl, ct, cw, ch = (int(v) for v in client_rect)
    if cw <= 0 or ch <= 0 or fw <= 0 or fh <= 0 or img_w <= 0 or img_h <= 0:
        return image

    sx = img_w / fw
    sy = img_h / fh
    px1 = max(0, min(img_w, round((cl - fl) * sx)))
    py1 = max(0, min(img_h, round((ct - ft) * sy)))
    px2 = max(px1, min(img_w, round((cl - fl + cw) * sx)))
    py2 = max(py1, min(img_h, round((ct - ft + ch) * sy)))
    if px2 <= px1 or py2 <= py1:
        return image

    crop = image[py1:py2, px1:px2]
    if crop.shape[1] == cw and crop.shape[0] == ch:
        return crop
    import cv2

    return cv2.resize(crop, (cw, ch), interpolation=cv2.INTER_AREA)


class _Portal:
    def __init__(self, timeout: float = 30.0):
        try:
            import gi
            gi.require_version("Gio", "2.0")
            from gi.repository import Gio, GLib
        except Exception as exc:
            raise WaylandBackendError(
                "PipeWire screenshots require PyGObject/GIO. On Fedora: "
                "sudo dnf install python3-gobject"
            ) from exc

        self.Gio = Gio
        self.GLib = GLib
        self.timeout = int(timeout * 1000)
        # Start drives the interactive picker; allow time to click
        self.interactive_timeout = int(float(os.environ.get("LINUX_BACKEND_PIPEWIRE_INTERACTIVE_TIMEOUT", "120")) * 1000)
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._request_counter = 0

    def _variant(self, sig: str, value: Any):
        return self.GLib.Variant(sig, value)

    def _vardict(self, **items: tuple[str, Any]) -> dict[str, Any]:
        return {k: self._variant(sig, value) for k, (sig, value) in items.items()}

    @staticmethod
    def _unpack(value: Any) -> Any:
        return value.unpack() if hasattr(value, "unpack") else value

    def _result_get(self, results: dict[str, Any], key: str, default: Any = None) -> Any:
        if key not in results:
            return default
        return self._unpack(results[key])

    def _request_token(self, method: str) -> str:
        self._request_counter += 1
        safe = "".join(ch if ch.isalnum() else "_" for ch in method.lower())
        return f"linux_backend_{os.getpid()}_{int(time.time() * 1000)}_{safe}_{self._request_counter}"

    def _call_request(self, method: str, signature: str, values: tuple[Any, ...], *, options_index: int = -1, timeout: Optional[int] = None) -> dict[str, Any]:
        """Portal request call with the Response subscription installed before call_sync returns."""
        timeout = self.timeout if timeout is None else timeout
        token = self._request_token(method)
        values_l = list(values)
        options = dict(values_l[options_index]) if values_l[options_index] else {}
        options["handle_token"] = self._variant("s", token)
        values_l[options_index] = options
        params = self.GLib.Variant(signature, tuple(values_l))

        context = self.GLib.MainContext()
        context.push_thread_default()
        loop = self.GLib.MainLoop(context)
        state: dict[str, Any] = {"responses": {}, "handle": None}
        sub_id: Optional[int] = None
        timer_source = None

        def finish_from(path: str, response: int, results: Any) -> None:
            state["response"] = int(response)
            state["results"] = results
            state["response_path"] = path
            loop.quit()

        def on_response(_conn, _sender, path, _iface, _signal, response_params, _data):
            response, results = response_params.unpack()
            handle = state.get("handle")
            if handle is None:
                state["responses"][path] = (int(response), results)
                return
            if path == handle:
                finish_from(path, int(response), results)

        try:
            _log(f"portal {method}: request")
            sub_id = self.bus.signal_subscribe(
                None,
                REQUEST_IFACE,
                "Response",
                None,
                None,
                self.Gio.DBusSignalFlags.NONE,
                on_response,
                None,
            )
            self.bus.flush_sync(None)

            def on_timeout():
                state["timeout"] = True
                state["timer_fired"] = True
                loop.quit()
                return False

            timer_source = self.GLib.timeout_source_new(timeout)
            timer_source.set_callback(on_timeout)
            timer_source.attach(context)
            out = self.bus.call_sync(
                PORTAL_BUS,
                PORTAL_PATH,
                SCREENCAST_IFACE,
                method,
                params,
                self.GLib.VariantType.new("(o)"),
                self.Gio.DBusCallFlags.NONE,
                timeout,
                None,
            )
            handle = out.unpack()[0]
            state["handle"] = handle
            _log(f"portal {method}: handle {handle}")

            queued = state["responses"].pop(handle, None)
            if queued is not None:
                finish_from(handle, queued[0], queued[1])
            elif "response" not in state:
                loop.run()
        finally:
            if sub_id is not None:
                self.bus.signal_unsubscribe(sub_id)
            if timer_source is not None and not state.get("timer_fired"):
                timer_source.destroy()
            context.pop_thread_default()

        if state.get("timeout"):
            raise _PortalSetupError(f"Timed out waiting for portal {method} response", method=method)
        if state.get("response") != 0:
            response = int(state.get("response"))
            raise _PortalSetupError(
                f"Portal {method} denied or cancelled: {response}",
                method=method,
                response=response,
            )

        _log(f"portal {method}: ok")
        return state.get("results") or {}

    def available_source_types(self) -> int:
        try:
            out = self.bus.call_sync(
                PORTAL_BUS,
                PORTAL_PATH,
                "org.freedesktop.DBus.Properties",
                "Get",
                self.GLib.Variant("(ss)", (SCREENCAST_IFACE, "AvailableSourceTypes")),
                self.GLib.VariantType.new("(v)"),
                self.Gio.DBusCallFlags.NONE,
                self.timeout,
                None,
            )
            return int(self._unpack(out.unpack()[0]))
        except Exception as exc:
            _log(f"portal AvailableSourceTypes failed: {exc}")
            return SOURCE_MONITOR | SOURCE_WINDOW

    def _call_fd(self, session_handle: str) -> int:
        _log("portal OpenPipeWireRemote: request")
        try:
            out, fd_list = self.bus.call_with_unix_fd_list_sync(
                PORTAL_BUS,
                PORTAL_PATH,
                SCREENCAST_IFACE,
                "OpenPipeWireRemote",
                self.GLib.Variant("(oa{sv})", (session_handle, {})),
                self.GLib.VariantType.new("(h)"),
                self.Gio.DBusCallFlags.NONE,
                self.timeout,
                None,
                None,
            )
            index = out.unpack()[0]
            fd = os.dup(fd_list.get(index))
        except Exception as exc:
            raise _PortalSetupError(f"OpenPipeWireRemote failed: {exc}") from exc
        _log(f"portal OpenPipeWireRemote: fd {fd}")
        return fd

    def _restore_token_path(self, source_type: int) -> Path:
        env_path = os.environ.get("LINUX_BACKEND_PIPEWIRE_RESTORE_TOKEN")
        if env_path:
            return Path(env_path).expanduser()
        cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        suffix = "window" if source_type == SOURCE_WINDOW else "monitor"
        return cache / "linux-backend" / f"pipewire-restore-token-{suffix}"

    def _read_restore_token(self, source_type: int) -> Optional[str]:
        try:
            token = self._restore_token_path(source_type).read_text(encoding="utf-8").strip()
            return token or None
        except OSError:
            return None

    def _write_restore_token(self, source_type: int, token: str) -> None:
        if not token:
            return
        path = self._restore_token_path(source_type)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(token, encoding="utf-8")
            tmp.replace(path)
            _log(f"restore token saved: {path}")
        except OSError as exc:
            _log(f"restore token save failed: {exc}")

    def create_session(self, source_type: int, multiple: bool) -> tuple[str, list[_PortalStream], list[int]]:
        session_token = self._request_token("session")
        results = self._call_request(
            "CreateSession",
            "(a{sv})",
            (self._vardict(session_handle_token=("s", session_token)),),
            options_index=0,
        )
        session = self._result_get(results, "session_handle")
        if not session:
            raise _PortalSetupError("Screencast portal did not return a session handle")
        _log(f"session: {session}")

        fds: list[int] = []
        try:
            cursor = CURSOR_EMBEDDED if os.environ.get("LINUX_BACKEND_PIPEWIRE_CURSOR") == "1" else CURSOR_HIDDEN
            select_options = {
                "types": ("u", source_type),
                "multiple": ("b", multiple),
                "cursor_mode": ("u", cursor),
                "persist_mode": ("u", 2),
            }
            restore = self._read_restore_token(source_type)
            if restore:
                select_options["restore_token"] = ("s", restore)
                _log("restore token loaded")

            self._call_request(
                "SelectSources",
                "(oa{sv})",
                (session, self._vardict(**select_options)),
                options_index=1,
            )
            results = self._call_request(
                "Start",
                "(osa{sv})",
                (session, "", self._vardict()),
                options_index=2,
                timeout=self.interactive_timeout,
            )

            token = self._result_get(results, "restore_token")
            if token:
                self._write_restore_token(source_type, str(token))

            raw_streams = self._result_get(results, "streams", [])
            streams: list[_PortalStream] = []
            for node_id, props in raw_streams:
                props = props or {}
                serial = self._unpack(props.get("pipewire-serial")) if "pipewire-serial" in props else None
                position = self._unpack(props.get("position")) if "position" in props else (0, 0)
                size = self._unpack(props.get("size")) if "size" in props else (0, 0)
                if serial is not None:
                    target = str(serial)
                    target_is_serial = True
                else:
                    target = str(int(node_id))
                    target_is_serial = False
                streams.append(_PortalStream(
                    int(node_id),
                    target,
                    target_is_serial,
                    int(position[0]),
                    int(position[1]),
                    int(size[0]),
                    int(size[1]),
                ))

            if not streams:
                raise _PortalSetupError("Screencast portal did not return any PipeWire streams")

            # one remote fd per pipeline; a dup'd fd would share the PipeWire connection
            fds = [self._call_fd(session) for _ in streams]
            for stream in streams:
                kind = "serial" if stream.target_is_serial else "node"
                _log(f"stream: {kind}={stream.target} pos=({stream.left},{stream.top}) size={stream.width}x{stream.height}")
            return session, streams, fds
        except BaseException:
            for fd in fds:
                try:
                    os.close(fd)
                except OSError:
                    pass
            self.close_session(session)
            raise

    def close_session(self, session_handle: Optional[str]) -> None:
        if not session_handle:
            return
        try:
            _log(f"portal Session.Close: {session_handle}")
            self.bus.call_sync(
                PORTAL_BUS,
                session_handle,
                SESSION_IFACE,
                "Close",
                self.GLib.Variant("()", ()),
                None,
                self.Gio.DBusCallFlags.NONE,
                self.timeout,
                None,
            )
        except Exception as exc:
            _log(f"portal Session.Close failed: {exc}")


class _GstPipeWireStream:
    def __init__(self, fd: int, stream: _PortalStream, owner: "PipeWireCapture", generation: int):
        self.fd = fd
        self.stream = stream
        self.owner = owner
        self.generation = generation
        self.pipeline = None
        self._last_frame_at = 0.0
        self._bus_thread: Optional[threading.Thread] = None
        self._bus_stop = threading.Event()

    def start(self) -> None:
        Gst = self.owner.Gst
        target = (
            f"target-object={self.stream.target}"
            if self.stream.target_is_serial
            else f"path={self.stream.target}"
        )
        # max-framerate negotiates the cap with PipeWire itself, so the compositor only
        # sends cache_fps frames instead of us receiving 60fps and dropping (videorate
        # drop-only does NOT drop on these variable-rate streams - measured). The second,
        # unconstrained caps structure is the fallback for portals that reject the field.
        # BGR output makes numpy's per-frame copy a plain memcpy; the old BGRx followed by
        # [:, :, :3].copy() was a slow strided strip that dominated capture CPU.
        desc = (
            f"pipewiresrc fd={self.fd} {target} do-timestamp=true resend-last=true keepalive-time=1000 ! "
            f'capsfilter caps="video/x-raw,max-framerate={self.owner._cache_fps}/1;video/x-raw" ! '
            "queue max-size-buffers=2 leaky=downstream ! "
            "videoconvert n-threads=1 ! video/x-raw,format=BGR ! "
            "appsink name=sink emit-signals=true max-buffers=1 drop=true sync=false"
        )
        _log(f"gst: create pipeline for {target}")
        self.pipeline = Gst.parse_launch(desc)
        sink = self.pipeline.get_by_name("sink")
        if sink is None:
            raise _StreamRuntimeError("Could not create PipeWire appsink")
        sink.connect("new-sample", self._on_sample)

        bus = self.pipeline.get_bus()
        self._bus_stop.clear()
        self._bus_thread = threading.Thread(target=self._watch_bus, args=(bus,), name="pipewire-gst-bus", daemon=True)
        self._bus_thread.start()

        result = self.pipeline.set_state(Gst.State.PLAYING)
        _log(f"gst: PLAYING result={result.value_nick}")
        if result == Gst.StateChangeReturn.FAILURE:
            raise _StreamRuntimeError("Could not start PipeWire GStreamer pipeline")

    def close(self) -> None:
        self._bus_stop.set()
        if self.pipeline is not None:
            _log("gst: stopping pipeline")
            self.pipeline.set_state(self.owner.Gst.State.NULL)
            self.pipeline = None
        try:
            os.close(self.fd)
        except OSError:
            pass

    def _watch_bus(self, bus) -> None:
        Gst = self.owner.Gst
        mask = Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.WARNING | Gst.MessageType.STATE_CHANGED
        while not self._bus_stop.is_set():
            msg = bus.timed_pop_filtered(250 * Gst.MSECOND, mask)
            if msg is None:
                continue
            if msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                exc = _StreamRuntimeError(f"GStreamer error from {msg.src.get_name()}: {err}; debug={debug or ''}")
                _log(str(exc))
                self.owner._set_error(self.generation, exc)
                return
            if msg.type == Gst.MessageType.EOS:
                exc = _StreamRuntimeError("GStreamer PipeWire stream ended")
                _log(str(exc))
                self.owner._set_error(self.generation, exc)
                return
            if msg.type == Gst.MessageType.WARNING:
                warn, debug = msg.parse_warning()
                _log(f"GStreamer warning from {msg.src.get_name()}: {warn}; debug={debug or ''}")
            if msg.type == Gst.MessageType.STATE_CHANGED and msg.src is self.pipeline:
                old, new, pending = msg.parse_state_changed()
                _log(f"gst: state {old.value_nick}->{new.value_nick} pending={pending.value_nick}")

    def _video_stride(self, caps, buf, width: int) -> int:
        # BGR rows are padded to 4-byte alignment by GStreamer.
        stride = (width * 3 + 3) & ~3
        GstVideo = getattr(self.owner, "GstVideo", None)
        if GstVideo is None:
            return stride
        try:
            meta = GstVideo.buffer_get_video_meta(buf)
            meta_stride = getattr(meta, "stride", None) if meta is not None else None
            if meta_stride:
                return max(stride, int(meta_stride[0]))
        except Exception:
            pass
        try:
            info = GstVideo.VideoInfo()
            if info.from_caps(caps):
                cap_stride = getattr(info, "stride", None)
                if cap_stride:
                    return max(stride, int(cap_stride[0]))
        except Exception:
            pass
        return stride

    def _on_sample(self, sink):
        Gst = self.owner.Gst
        try:
            sample = sink.emit("pull-sample")
            if sample is None:
                return Gst.FlowReturn.ERROR
            now = time.monotonic()
            if now - self._last_frame_at < self.owner._cache_interval:
                return Gst.FlowReturn.OK
            self._last_frame_at = now

            caps = sample.get_caps()
            struct = caps.get_structure(0)
            width = int(struct.get_value("width"))
            height = int(struct.get_value("height"))
            buf = sample.get_buffer()
            ok, info = buf.map(Gst.MapFlags.READ)
            if not ok:
                return Gst.FlowReturn.ERROR

            try:
                import numpy as np

                stride = self._video_stride(caps, buf, width)
                row_bytes = width * 3
                needed = stride * max(height - 1, 0) + row_bytes
                raw = np.frombuffer(info.data, dtype=np.uint8)
                if raw.size < needed:
                    self.owner._set_error(self.generation, _StreamRuntimeError(
                        f"GStreamer buffer too small for frame: size={raw.size}, "
                        f"needed={needed}, width={width}, height={height}, stride={stride}"
                    ))
                    return Gst.FlowReturn.ERROR
                image3 = np.ndarray(
                    shape=(height, width, 3),
                    dtype=np.uint8,
                    buffer=raw,
                    strides=(stride, 3, 1),
                )
                image = image3.copy()

                if self.owner._source_type == SOURCE_WINDOW:
                    with self.owner._lock:
                        target = self.owner._target_region
                        frame_rect = self.owner._target_frame

                    if target is not None:
                        rect = frame_rect or target
                        image = _trim_to_frame(image, rect)
                        image = _crop_client(
                            image,
                            rect,
                            target,
                            self.owner._window_crop_insets,
                        )
            finally:
                buf.unmap(info)

            left, top, logical_w, logical_h = self.owner._frame_geometry(self.stream, image.shape[1], image.shape[0])
            self.owner._set_frame(
                self.generation,
                self.stream.target,
                _Frame(image, left, top, logical_w, logical_h, time.monotonic()),
            )
            return Gst.FlowReturn.OK
        except Exception as exc:
            err = exc if isinstance(exc, _StreamRuntimeError) else _StreamRuntimeError(str(exc))
            self.owner._set_error(self.generation, err)
            return Gst.FlowReturn.ERROR


class PipeWireCapture:
    """Persistent portal/PipeWire screenshot source; screenshot() crops/composes cached stream frames."""

    def __init__(self):
        self._lock = threading.Condition()
        self._started = False
        self._error: Optional[BaseException] = None
        self._portal: Optional[_Portal] = None
        self._session: Optional[str] = None
        self._frames: dict[str, _Frame] = {}
        self._expected_keys: list[str] = []
        self._target_region: Optional[tuple[int, int, int, int]] = None
        self._target_frame: Optional[tuple[int, int, int, int]] = None
        self._window_crop_insets = self._crop_insets_from_env()
        self._generation = 0
        self._streams: list[_GstPipeWireStream] = []
        self._active_uses = 0
        self._idle_timer: Optional[threading.Timer] = None
        self._idle_close_seconds = float(os.environ.get("LINUX_BACKEND_PIPEWIRE_IDLE_CLOSE_SECONDS", "300"))
        self._cache_fps = max(1, int(float(os.environ.get("LINUX_BACKEND_PIPEWIRE_CACHE_FPS", "20"))))
        # The negotiated max-framerate already caps delivery to cache_fps; keep the callback
        # throttle only as a safety net (for portals that ignore the caps field), slightly
        # loose so the two limiters don't beat and halve the effective rate.
        self._cache_interval = 0.8 / self._cache_fps
        # 0 = unthrottled reads. screenshot() only crops the cached frame (~0.2ms), so
        # throttling reads adds latency without reducing any load.
        self._screenshot_fps = float(os.environ.get("LINUX_BACKEND_PIPEWIRE_SCREENSHOT_FPS", "0"))
        self._screenshot_interval = 1.0 / self._screenshot_fps if self._screenshot_fps > 0 else 0.0
        self._next_screenshot_at = 0.0
        self._source_env = os.environ.get("LINUX_BACKEND_PIPEWIRE_SOURCE")
        self._source_fallback_allowed = self._source_env is None or not self._source_env.strip()
        self._source_type = self._source_type_from_env()
        self._logged_first_frame = False
        self._logged_all_streams = False

        try:
            import gi
            gi.require_version("Gst", "1.0")
            gi.require_version("GstVideo", "1.0")
            from gi.repository import Gst, GstVideo
        except Exception as exc:
            raise WaylandBackendError(
                "PipeWire screenshots require GStreamer Python bindings. On Fedora: "
                "sudo dnf install python3-gstreamer1 gstreamer1-plugin-pipewire "
                "gstreamer1-plugins-base gstreamer1-plugins-good"
            ) from exc

        if not which("pipewire"):
            raise WaylandBackendError("PipeWire screenshots require PipeWire to be installed and running")

        self.Gst = Gst
        self.GstVideo = GstVideo
        # PyGObject < 3.52 rejects None for the inout argv array; [] means the same thing.
        Gst.init([])
        atexit.register(self.close)

    @staticmethod
    def _source_type_from_env() -> int:
        mode = os.environ.get("LINUX_BACKEND_PIPEWIRE_SOURCE", "").strip().lower()
        if not mode:
            mode = _default_source or "window"
        if mode in {"monitor", "screen", "desktop"}:
            return SOURCE_MONITOR
        if mode == "window":
            return SOURCE_WINDOW
        raise WaylandBackendError(f"Unknown LINUX_BACKEND_PIPEWIRE_SOURCE={mode!r}")

    @staticmethod
    def _crop_insets_from_env() -> Optional[tuple[int, int, int, int]]:
        raw = os.environ.get("LINUX_BACKEND_WINDOW_CROP", "").strip()
        if not raw:
            return None
        try:
            parts = tuple(int(p) for p in raw.split(","))
        except ValueError:
            parts = ()
        if len(parts) == 4 and all(p >= 0 for p in parts):
            return parts
        raise WaylandBackendError(
            f"LINUX_BACKEND_WINDOW_CROP must be 'left,top,right,bottom' px, got {raw!r}"
        )

    @staticmethod
    def _source_name(source_type: int) -> str:
        return "window" if source_type == SOURCE_WINDOW else "monitor"

    def _select_multiple(self, source_type: int) -> bool:
        if source_type != SOURCE_MONITOR:
            return False
        value = os.environ.get("LINUX_BACKEND_PIPEWIRE_MULTIPLE", "1").strip().lower()
        return value not in {"", "0", "false", "no", "off"}

    def _source_type_for_portal(self, portal: _Portal) -> int:
        source_type = self._source_type
        available = portal.available_source_types()
        if available & source_type:
            return source_type
        if source_type == SOURCE_WINDOW and self._source_fallback_allowed and available & SOURCE_MONITOR:
            _log("portal window capture unavailable; falling back to monitor capture")
            return SOURCE_MONITOR
        raise _PortalSetupError(f"Portal does not support {self._source_name(source_type)} capture")

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._generation += 1
            generation = self._generation
            self._started = True
            self._error = None
            self._frames.clear()
            self._expected_keys = []
            self._logged_first_frame = False
            self._logged_all_streams = False

        fds: list[int] = []
        gst_streams: list[_GstPipeWireStream] = []
        portal: Optional[_Portal] = None
        session: Optional[str] = None
        try:
            portal = _Portal(timeout=float(os.environ.get("LINUX_BACKEND_PIPEWIRE_PORTAL_TIMEOUT", "30")))
            source_type = self._source_type_for_portal(portal)
            _log(f"start source={self._source_name(source_type)}")
            try:
                session, streams, fds = portal.create_session(source_type, self._select_multiple(source_type))
            except _PortalSetupError as exc:
                if not (
                    source_type == SOURCE_WINDOW
                    and self._source_fallback_allowed
                    and exc.method == "SelectSources"
                    and exc.response == 2
                ):
                    raise
                _log("portal window capture rejected; falling back to monitor capture")
                source_type = SOURCE_MONITOR
                session, streams, fds = portal.create_session(source_type, self._select_multiple(source_type))

            expected_keys = [stream.target for stream in streams]
            with self._lock:
                if generation != self._generation:
                    raise _StreamRuntimeError("PipeWire capture generation changed during startup")
                self._source_type = source_type
                self._expected_keys = expected_keys
                self._lock.notify_all()

            gst_streams = [_GstPipeWireStream(fd, stream, self, generation) for fd, stream in zip(fds, streams)]
            for gst_stream in gst_streams:
                gst_stream.start()

            with self._lock:
                if generation != self._generation:
                    raise _StreamRuntimeError("PipeWire capture generation changed after stream startup")
                self._portal = portal
                self._session = session
                self._streams = gst_streams
            _log(f"started {len(gst_streams)} stream(s)")
        except BaseException as exc:
            _log(f"start failed: {exc}")
            for stream in gst_streams:
                stream.close()
            if not gst_streams:
                for fd in fds:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            if portal is not None and session is not None:
                portal.close_session(session)
            with self._lock:
                if generation == self._generation:
                    self._portal = None
                    self._session = None
                    self._started = False
                    self._expected_keys = []
                    self._error = exc
                    self._lock.notify_all()
            raise

    def close(self) -> None:
        with self._lock:
            self._generation += 1
            idle_timer = self._idle_timer
            streams = self._streams
            portal = self._portal
            session = self._session
            self._idle_timer = None
            self._streams = []
            self._portal = None
            self._session = None
            self._frames.clear()
            self._expected_keys = []
            self._started = False
        if idle_timer is not None:
            idle_timer.cancel()
        for stream in streams:
            stream.close()
        if portal is not None and session is not None:
            portal.close_session(session)

    def _begin_use(self) -> None:
        with self._lock:
            self._active_uses += 1
            idle_timer = self._idle_timer
            self._idle_timer = None
        if idle_timer is not None:
            idle_timer.cancel()

    def _end_use(self) -> None:
        with self._lock:
            self._active_uses = max(0, self._active_uses - 1)
        self._arm_idle_close()

    def _arm_idle_close(self) -> None:
        if self._idle_close_seconds <= 0:
            return
        with self._lock:
            old_timer = self._idle_timer
            self._idle_timer = None
            if self._active_uses or not self._started:
                timer = None
            else:
                timer = threading.Timer(self._idle_close_seconds, self._close_if_idle)
                timer.daemon = True
                self._idle_timer = timer
        if old_timer is not None:
            old_timer.cancel()
        if timer is not None:
            timer.start()

    def _close_if_idle(self) -> None:
        with self._lock:
            if self._active_uses or not self._started:
                return
            self._idle_timer = None
        _log("idle timeout; closing PipeWire capture")
        self.close()

    def _throttle_screenshot(self) -> None:
        if self._screenshot_interval <= 0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                wait = self._next_screenshot_at - now
                if wait <= 0:
                    self._next_screenshot_at = now + self._screenshot_interval
                    return
            time.sleep(wait)

    def _restart_after_timeout(self) -> None:
        _log("first frame timeout; restarting PipeWire capture")
        self.close()
        self.start()

    def _set_error(self, generation: int, exc: BaseException) -> None:
        with self._lock:
            if generation != self._generation:
                return
            self._error = exc
            self._lock.notify_all()

    def _frame_geometry(self, stream: _PortalStream, image_width: int, image_height: int) -> tuple[int, int, int, int]:
        if self._source_type == SOURCE_WINDOW:
            with self._lock:
                target = self._target_region

            if target is not None:
                left, top, width, height = target
                return left, top, width, height

            return 0, 0, image_width, image_height

        return (
            stream.left,
            stream.top,
            stream.width or image_width,
            stream.height or image_height,
        )

    def _set_frame(self, generation: int, key: str, frame: _Frame) -> None:
        with self._lock:
            if generation != self._generation:
                return
            self._frames[key] = frame
            count = len(set(self._frames).intersection(self._expected_keys))
            total = len(self._expected_keys)
            if total and count == 1 and not self._logged_first_frame:
                self._logged_first_frame = True
                _log(f"first frame: {frame.image.shape[1]}x{frame.image.shape[0]} at ({frame.left},{frame.top})")
            if total and count == total and not self._logged_all_streams:
                self._logged_all_streams = True
                _log(f"all streams ready: {count}/{total}")
            self._lock.notify_all()

    def _wait_for_frames_once(self, timeout: float) -> list[_Frame]:
        self.start()
        deadline = time.monotonic() + timeout
        with self._lock:
            if self._error is not None:
                raise _StreamRuntimeError(f"PipeWire capture failed: {self._error}") from self._error
            while True:
                if self._error is not None:
                    raise _StreamRuntimeError(f"PipeWire capture failed: {self._error}") from self._error
                expected = list(self._expected_keys)
                if expected and all(key in self._frames for key in expected):
                    frames = [self._frames[key] for key in expected]
                    if self._error is not None:
                        raise _StreamRuntimeError(f"PipeWire capture failed after frames were cached: {self._error}") from self._error
                    return frames
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    missing = [key for key in expected if key not in self._frames] or expected or ["<unknown>"]
                    raise TimeoutError(f"Timed out waiting for PipeWire frames from all streams; missing={missing}")
                self._lock.wait(remaining)

    def _latest_frames(self, timeout: float) -> list[_Frame]:
        first_frame_retries = int(os.environ.get("LINUX_BACKEND_PIPEWIRE_FIRST_FRAME_RETRIES", "1"))
        error_retries = int(os.environ.get("LINUX_BACKEND_PIPEWIRE_ERROR_RETRIES", "1"))
        timeout_attempt = 0
        error_attempt = 0
        while True:
            try:
                return self._wait_for_frames_once(timeout)
            except TimeoutError as exc:
                if timeout_attempt >= first_frame_retries:
                    raise WaylandBackendError(str(exc)) from exc
                timeout_attempt += 1
                self._restart_after_timeout()
            except _StreamRuntimeError:
                if error_attempt >= error_retries:
                    raise
                error_attempt += 1
                _log("PipeWire stream error; restarting capture")
                self.close()
                self.start()

    @staticmethod
    def _crop_from_frame(frame: _Frame, left: int, top: int, width: int, height: int):
        fx1, fy1 = frame.left, frame.top
        fx2, fy2 = frame.left + frame.width, frame.top + frame.height
        ix1, iy1 = max(left, fx1), max(top, fy1)
        ix2, iy2 = min(left + width, fx2), min(top + height, fy2)
        if ix2 <= ix1 or iy2 <= iy1:
            return None

        img_h, img_w = frame.image.shape[:2]
        sx = img_w / max(frame.width, 1)
        sy = img_h / max(frame.height, 1)
        px1 = max(0, min(img_w, round((ix1 - fx1) * sx)))
        py1 = max(0, min(img_h, round((iy1 - fy1) * sy)))
        px2 = max(0, min(img_w, round((ix2 - fx1) * sx)))
        py2 = max(0, min(img_h, round((iy2 - fy1) * sy)))
        if px2 <= px1 or py2 <= py1:
            return None
        return ix1, iy1, frame.image[py1:py2, px1:px2]

    def set_window_region(self, region: tuple[int, int, int, int], frame: Optional[tuple[int, int, int, int]] = None) -> None:
        target = tuple(int(v) for v in region)
        frame_rect = tuple(int(v) for v in frame) if frame else None
        with self._lock:
            old = self._target_region
            old_frame = self._target_frame
            if old == target and old_frame == frame_rect:
                return
            self._target_region = target
            self._target_frame = frame_rect

            if self._source_type == SOURCE_WINDOW:
                # a pure move keeps the crop geometry, so cached pixels stay valid
                moved_only = (
                    old is not None
                    and old[2:] == target[2:]
                    and (old_frame[2:] if old_frame else None) == (frame_rect[2:] if frame_rect else None)
                )
                if moved_only:
                    for key, cached in list(self._frames.items()):
                        self._frames[key] = _Frame(cached.image, *target, cached.timestamp)
                    return
                self._frames.clear()
                self._logged_first_frame = False
                self._logged_all_streams = False

    def prepare_window(self, region: tuple[int, int, int, int], frame: Optional[tuple[int, int, int, int]] = None) -> None:
        target = tuple(int(v) for v in region)
        self.set_window_region(target, frame)
        self.screenshot(target)

    def screenshot(self, region=None, *, timeout: Optional[float] = None):
        import numpy as np

        self._begin_use()
        try:
            self._throttle_screenshot()
            wait = float(os.environ.get("LINUX_BACKEND_PIPEWIRE_FRAME_TIMEOUT", "2.0")) if timeout is None else timeout
            frames = self._latest_frames(wait)

            if region:
                left, top, width, height = [int(v) for v in region]
            else:
                left = min(f.left for f in frames)
                top = min(f.top for f in frames)
                width = max(f.left + f.width for f in frames) - left
                height = max(f.top + f.height for f in frames) - top

            if width <= 0 or height <= 0:
                raise ValueError("screenshot region must have positive width and height")

            hits = [hit for f in frames if (hit := self._crop_from_frame(f, left, top, width, height)) is not None]
            if not hits:
                raise WaylandBackendError(f"Requested screenshot region is outside PipeWire stream bounds: {region}")

            if len(hits) == 1:
                ix, iy, crop = hits[0]
                if ix == left and iy == top and crop.shape[1] == width and crop.shape[0] == height:
                    return crop.copy()

            canvas = np.zeros((height, width, 3), dtype=np.uint8)
            for ix, iy, crop in hits:
                dx, dy = ix - left, iy - top
                target_w = min(width - dx, crop.shape[1])
                target_h = min(height - dy, crop.shape[0])
                if target_w <= 0 or target_h <= 0:
                    continue
                if crop.shape[1] != target_w or crop.shape[0] != target_h:
                    import cv2

                    crop = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_AREA)
                canvas[dy:dy + target_h, dx:dx + target_w] = crop[:target_h, :target_w]
            return canvas
        finally:
            self._end_use()


_capture: Optional[PipeWireCapture] = None
_capture_window_region: Optional[tuple[int, int, int, int]] = None
_capture_window_frame: Optional[tuple[int, int, int, int]] = None
_capture_lock = threading.Lock()
_default_source: Optional[str] = None


def set_default_source(name: Optional[str]) -> None:
    """Compositor-preferred capture source; LINUX_BACKEND_PIPEWIRE_SOURCE still wins."""
    global _default_source
    _default_source = name


def get_capture() -> PipeWireCapture:
    global _capture
    with _capture_lock:
        if _capture is None:
            _capture = PipeWireCapture()
            if _capture_window_region is not None:
                _capture.set_window_region(_capture_window_region, _capture_window_frame)
        return _capture


def close_capture() -> None:
    global _capture
    with _capture_lock:
        capture = _capture
        _capture = None
    if capture is not None:
        capture.close()


def set_capture_window_region(region: tuple[int, int, int, int], frame: Optional[tuple[int, int, int, int]] = None) -> None:
    global _capture_window_region, _capture_window_frame
    target = tuple(int(v) for v in region)
    frame_rect = tuple(int(v) for v in frame) if frame else None
    with _capture_lock:
        _capture_window_region = target
        _capture_window_frame = frame_rect
        capture = _capture
    if capture is not None:
        capture.set_window_region(target, frame_rect)