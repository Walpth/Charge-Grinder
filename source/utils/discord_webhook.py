import hashlib, json, logging, os, queue, re, sys, threading, time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from source.utils.paths import APP_VERSION
from source.utils import params


WEBHOOK_ENV = "CGRINDER_DISCORD_WEBHOOK_URL"
THREAD_ENV = "CGRINDER_DISCORD_THREAD_ID"
RUN_TARGET_ENV = "CGRINDER_DISCORD_TOTAL_RUNS"
EXP_TARGET_ENV = "CGRINDER_DISCORD_EXP_TOTAL_RUNS"
THREAD_TARGET_ENV = "CGRINDER_DISCORD_THREAD_TOTAL_RUNS"
COMPACT_ENV = "CGRINDER_DISCORD_COMPACT_MODE"
PING_ON_FINISH_ENV = "CGRINDER_DISCORD_PING_ON_FINISH"
PING_ROLE_ENV = "CGRINDER_DISCORD_PING_ROLE_ID"

_MAX_TITLE = 256
_MAX_DESCRIPTION = 4096
_MAX_FIELD_NAME = 256
_MAX_FIELD_VALUE = 1024
_MAX_FIELDS = 25
_MAX_FOOTER = 2048
_MAX_EMBED_CHARS = 6000
_OUTBOX_VERSION = 1
_MAX_SNOWFLAKE_LENGTH = 20

_DISCORD_WEBHOOK_HOSTS = {
    "discord.com",
    "discordapp.com",
    "ptb.discord.com",
    "canary.discord.com"
}

_RE_FLOOR = re.compile(r"^Floor\s+(\d+)$")
_RE_TEAM = re.compile(r"^Team:\s+(.+)$")
_RE_GROUP = re.compile(r"^Group:\s+(.+)$")
_RE_DIFFICULTY = re.compile(r"^Difficulty:\s+(.+)$")
_RE_PACK = re.compile(r"^Pack:\s+(.+)$")
_RE_ENTERING = re.compile(r"^Entering\s+(.+)$")
_RE_GROUP_VALUE = re.compile(r"^([A-Za-z\.]+)#(\d+)$")
_RE_WEBHOOK_PATH = re.compile(r"^/api/webhooks/\d{1,20}/[^/?#\s]+$")

_FOCUS_LABELS = {
    "BURN": "Fire",
    "BLEED": "Bleed",
    "TREMOR": "Tremor",
    "RUPTURE": "Rupture",
    "SINKING": "Sinking",
    "POISE": "Poise",
    "CHARGE": "Charge",
    "SLASH": "Slash",
    "PIERCE": "Pierce",
    "BLUNT": "Blunt",
    "WRATH": "Wrath",
    "LUST": "Lust",
    "SLOTH": "Sloth",
    "GLUT.": "Gluttony",
    "GLOOM": "Gloom",
    "PRIDE": "Pride",
    "ENVY": "Envy"
}

_CONTEXT_DEFAULT = {
    "team": None,
    "group": None,
    "difficulty": None,
    "floor": None,
    "pack": None,
    "runs_done": 0,
    "runs_failed": 0,
    "run_attempts": 0,
    "exp_runs_done": 0,
    "thread_runs_done": 0,
    "active_scope": "md",
    "start_announced": False,
    "script_boot": False
}


def _trim(text, limit):
    text = str(text)
    if limit <= 0:
        return ""
    if limit <= 3:
        return text[:limit]
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."


def _to_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def validate_snowflake(value, field_name):
    if not value:
        return None
    if not isinstance(value, str) or not value.isdigit() or len(value) > _MAX_SNOWFLAKE_LENGTH:
        return f"{field_name} must contain no more than {_MAX_SNOWFLAKE_LENGTH} digits."
    return None


def validate_webhook_url(webhook_url):
    value = webhook_url.strip()
    if not value:
        return "Discord webhook URL is empty."
    if len(value) > 2048:
        return "Discord webhook URL is too long."

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return "Discord webhook URL has an invalid port."

    if parsed.scheme != "https":
        return "Discord webhook URL must use HTTPS."
    if parsed.username or parsed.password or port is not None:
        return "Discord webhook URL must not contain credentials or a custom port."
    if (parsed.hostname or "").lower().rstrip(".") not in _DISCORD_WEBHOOK_HOSTS:
        return "Discord webhook URL must use an official Discord host."
    if parsed.fragment or not _RE_WEBHOOK_PATH.fullmatch(parsed.path):
        return "Discord webhook URL must have the /api/webhooks/<id>/<token> format."
    return None


def _warn_local(message):
    try:
        sys.stderr.write(f"[DiscordWebhook] {message}\n")
    except Exception:
        pass


class DiscordWebhookClient:
    def __init__(self, webhook_url, thread_id=None, timeout=4, max_queue=500, max_retries=2, outbox_path=None):
        self.webhook_url = webhook_url.strip()
        self.thread_id = thread_id
        self.timeout = timeout
        self.max_queue = max_queue
        self.max_retries = max_retries

        self._queue = queue.Queue(maxsize=max_queue)
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._outbox_lock = threading.Lock()
        self._next_allowed_at = 0.0
        self._disabled = False
        self._warned_disabled = False
        self._warned_queue_full = False
        self._destination_id = self._destination_fingerprint()
        self._outbox_path = outbox_path or os.path.join(
            os.path.expanduser("~"),
            f".chargegrinder-webhook-outbox-{self._destination_id[:16]}.json"
        )
        self._allow_legacy_outbox = outbox_path is not None
        self._pending_items = self._load_outbox()

        self._execute_url = self._build_execute_url()
        self._worker = threading.Thread(target=self._run, daemon=True, name="discord-webhook")

        for item in self._pending_items:
            if not self._push_item(item):
                break

    def _build_execute_url(self):
        params = {"wait": "true"}
        if self.thread_id:
            params["thread_id"] = self.thread_id
        separator = "&" if "?" in self.webhook_url else "?"
        return f"{self.webhook_url}{separator}{urlencode(params)}"

    def _destination_fingerprint(self):
        destination = f"{self.webhook_url}\0{self.thread_id or ''}".encode("utf-8")
        return hashlib.sha256(destination).hexdigest()

    def start(self):
        if not self._worker.is_alive():
            self._worker.start()

    def close(self):
        self._stop_event.set()
        if self._worker.is_alive():
            self._worker.join(timeout=self.timeout + 1)
        if self._worker.is_alive():
            _warn_local("Webhook worker did not stop before shutdown; pending events are saved for the next launch.")

    def disable(self, reason=""):
        with self._state_lock:
            self._disabled = True
        if not self._warned_disabled:
            extra = f" ({reason})" if reason else ""
            _warn_local(f"Webhook disabled{extra}.")
            self._warned_disabled = True

    def is_disabled(self):
        with self._state_lock:
            return self._disabled

    def send(self, payload, priority=False):
        if self.is_disabled():
            return False
        item = {
            "payload": payload,
            "attempt": 0,
            "priority": 0 if priority else 1
        }
        if not self._add_pending(item):
            if not self._warned_queue_full:
                _warn_local("Webhook queue is full; lower-priority events are being dropped.")
                self._warned_queue_full = True
            return False
        if self._push_item(item):
            return True
        return True

    def _load_outbox(self):
        try:
            with open(self._outbox_path, "r", encoding="utf-8") as file:
                items = json.load(file)
        except FileNotFoundError:
            return []
        except Exception as error:
            _warn_local(f"Could not load pending webhook events: {error}")
            return []

        if isinstance(items, dict):
            if items.get("version") != _OUTBOX_VERSION or items.get("destination") != self._destination_id:
                _warn_local("Pending webhook events belong to a different webhook and were not sent.")
                return []
            items = items.get("items")
        elif not self._allow_legacy_outbox:
            _warn_local("Pending webhook events use an unsupported legacy format and were not sent.")
            return []

        if not isinstance(items, list):
            _warn_local("Pending webhook events have an invalid format.")
            return []

        pending = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("payload"), dict):
                continue
            try:
                attempt = max(0, int(item.get("attempt", 0)))
                priority = int(item.get("priority", 1))
            except (TypeError, ValueError):
                continue
            pending.append({
                "payload": item["payload"],
                "attempt": attempt,
                "priority": priority
            })
        return pending

    def _save_outbox_locked(self):
        try:
            if not self._pending_items:
                if os.path.exists(self._outbox_path):
                    os.remove(self._outbox_path)
                return

            temp_path = f"{self._outbox_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump({
                    "version": _OUTBOX_VERSION,
                    "destination": self._destination_id,
                    "items": self._pending_items
                }, file, ensure_ascii=False)
            os.replace(temp_path, self._outbox_path)
        except Exception as error:
            _warn_local(f"Could not save pending webhook events: {error}")

    def _add_pending(self, item):
        with self._outbox_lock:
            if len(self._pending_items) >= self.max_queue:
                if item.get("priority", 1) == 0:
                    for index, pending in enumerate(self._pending_items):
                        if pending.get("priority", 1) != 0:
                            self._pending_items.pop(index)
                            break
                    else:
                        return False
                else:
                    return False
            self._pending_items.append(item)
            self._save_outbox_locked()
            return True

    def _remove_pending(self, item):
        with self._outbox_lock:
            for index, pending in enumerate(self._pending_items):
                if pending is item:
                    self._pending_items.pop(index)
                    break
            else:
                return
            self._save_outbox_locked()
            self._queue_next_pending()

    def _update_pending(self):
        with self._outbox_lock:
            self._save_outbox_locked()

    def _queue_next_pending(self):
        with self._queue.mutex:
            queued_items = {id(item) for item in self._queue.queue}
        for item in self._pending_items:
            if id(item) in queued_items:
                continue
            if self._push_item(item):
                return

    def _push_item(self, item):
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            try:
                dropped = self._queue.get_nowait()
                self._queue.task_done()
                if dropped.get("priority", 1) == 0 and item.get("priority", 1) == 1:
                    try:
                        self._queue.put_nowait(dropped)
                    except queue.Full:
                        pass
                    return False
            except queue.Empty:
                return False
            try:
                self._queue.put_nowait(item)
                return True
            except queue.Full:
                return False

    def _run(self):
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                if not self._wait_rate_limit():
                    continue
                should_retry = self._post(item["payload"], item["attempt"])
                if should_retry:
                    if not self._stop_event.is_set():
                        item["attempt"] += 1
                        self._update_pending()
                        if item["attempt"] <= self.max_retries and not self.is_disabled():
                            self._push_item(item)
                        else:
                            self._remove_pending(item)
                    else:
                        self._update_pending()
                else:
                    self._remove_pending(item)
            finally:
                self._queue.task_done()

    def _wait_rate_limit(self):
        with self._state_lock:
            wait_for = self._next_allowed_at - time.time()
        if wait_for > 0:
            return not self._stop_event.wait(wait_for)
        return not self._stop_event.is_set()

    def _set_next_allowed(self, seconds):
        if seconds <= 0:
            return
        with self._state_lock:
            self._next_allowed_at = max(self._next_allowed_at, time.time() + seconds)

    def _set_backoff(self, attempt):
        self._set_next_allowed(min(30.0, 2.0 ** (attempt + 1)))

    def _parse_retry_after(self, headers, body):
        header_delay = _to_float(headers.get("Retry-After"), 0.0) if headers else 0.0
        if header_delay > 0:
            return header_delay

        if not body:
            return 1.0
        try:
            payload = json.loads(body.decode("utf-8", errors="ignore"))
            return _to_float(payload.get("retry_after"), 1.0)
        except Exception:
            return 1.0

    def _update_bucket_limit(self, headers):
        if not headers:
            return

        remaining = headers.get("X-RateLimit-Remaining")
        reset_after = headers.get("X-RateLimit-Reset-After")
        if remaining == "0" and reset_after:
            self._set_next_allowed(_to_float(reset_after, 0.0))

    def _post(self, payload, attempt):
        request_data = json.dumps(payload).encode("utf-8")
        request = Request(
            self._execute_url,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"ChargeGrinder/{APP_VERSION} DiscordWebhook"
            },
            method="POST"
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                self._update_bucket_limit(response.headers)
            return False
        except HTTPError as err:
            body = b""
            try:
                body = err.read()
            except Exception:
                pass

            status = err.code
            if status == 400:
                self.disable("HTTP 400; check webhook URL/thread_id configuration")
                return False

            if status in (401, 403):
                self.disable(f"HTTP {status}")
                return False

            if status == 404:
                self.disable("HTTP 404")
                return False

            if status == 429:
                retry_after = self._parse_retry_after(err.headers, body)
                self._set_next_allowed(retry_after)
                return True

            if 500 <= status <= 599:
                self._set_backoff(attempt)
                return True

            return False
        except URLError:
            self._set_backoff(attempt)
            return True
        except Exception:
            self._set_backoff(attempt)
            return True


class WebhookLogHandler(logging.Handler):
    def __init__(self, client):
        super().__init__(level=logging.INFO)
        self.client = client
        self.client.start()

        self.compact_mode = False
        self.ping_on_finish = False
        self.ping_role_id = ""
        self.target_runs = None
        self.exp_target_runs = None
        self.thread_target_runs = None
        self.context = dict(_CONTEXT_DEFAULT)
        self.run_started_at = None
        self.floor_started_at = None
        self.room_started_at = None
        self.last_room_duration = None
        self.last_floor_duration = None
        self.last_run_duration = None
        self._last_sent = {}
        self.run_durations = []
        self._refresh_runtime_options()

    def _read_bool_env(self, env_name):
        value = os.environ.get(env_name, "").strip().lower()
        return value in ("1", "true", "yes", "on")

    def _read_ping_role_id(self):
        value = os.environ.get(PING_ROLE_ENV, "").strip()
        return value if value.isdigit() else ""

    def _read_target_runs(self):
        value = os.environ.get(RUN_TARGET_ENV, "").strip()
        if not value:
            return None
        if value.upper() == "ALL":
            return "ALL"
        if value.isdigit():
            return str(int(value))
        return None

    def _read_numeric_target(self, env_name):
        value = os.environ.get(env_name, "").strip()
        return str(int(value)) if value.isdigit() else None

    def _refresh_runtime_options(self):
        self.compact_mode = self._read_bool_env(COMPACT_ENV)
        self.ping_on_finish = self._read_bool_env(PING_ON_FINISH_ENV)
        self.ping_role_id = self._read_ping_role_id()
        self.target_runs = self._read_target_runs()
        self.exp_target_runs = self._read_numeric_target(EXP_TARGET_ENV)
        self.thread_target_runs = self._read_numeric_target(THREAD_TARGET_ENV)

    def _reset_run_timers(self):
        self.run_started_at = None
        self.floor_started_at = None
        self.room_started_at = None
        self.last_room_duration = None
        self.last_floor_duration = None
        self.last_run_duration = None
        self.context["floor"] = None
        self.context["pack"] = None
        self.context["start_announced"] = False

    def _reset_script_context(self):
        self.context.update(_CONTEXT_DEFAULT)
        self.run_durations = []
        self._reset_run_timers()

    def _format_duration(self, seconds):
        if seconds is None:
            return None
        total = max(0, int(round(seconds)))
        hours, rem = divmod(total, 3600)
        minutes, sec = divmod(rem, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"

    def _runs_done(self):
        return self.context["runs_done"]

    def _run_progress(self):
        done = self._runs_done()
        if self.target_runs is not None:
            return f"{done}/{self.target_runs}"
        return str(done)

    def _lux_runs_done(self, lux_type):
        return self.context[f"{lux_type.lower()}_runs_done"]

    def _lux_target_runs(self, lux_type):
        return self.exp_target_runs if lux_type == "EXP" else self.thread_target_runs

    def _selected_lux_types(self):
        return [
            lux_type
            for lux_type in ("EXP", "THREAD")
            if self._lux_target_runs(lux_type) not in (None, "0")
        ]

    def _lux_progress(self, lux_type):
        done = self._lux_runs_done(lux_type)
        target = self._lux_target_runs(lux_type)
        return f"{done}/{target}" if target is not None else str(done)

    def _lux_remaining(self, lux_type):
        target = self._lux_target_runs(lux_type)
        if target in (None, "0"):
            return None
        return str(max(0, int(target) - self._lux_runs_done(lux_type)))

    def _lux_label(self, lux_type):
        return "EXP" if lux_type == "EXP" else "Thread"

    def _focus_label(self, value):
        if not value:
            return value
        normalized = str(value).strip()
        return _FOCUS_LABELS.get(normalized.upper(), normalized.title() if normalized.isupper() else normalized)

    def _group_label(self, value):
        if not value:
            return value
        raw = str(value).strip()
        match = _RE_GROUP_VALUE.match(raw)
        if not match:
            return raw
        focus_raw, number = match.groups()
        return f"{self._focus_label(focus_raw)}#{number}"

    def _should_ping(self, record, event_name, event_value):
        if not self.ping_on_finish or not self.ping_role_id:
            return False
        if record.levelno >= logging.ERROR:
            return True
        if event_name == "Run":
            if not event_value.startswith("Completed"):
                return False
            if self.target_runs is None or self.target_runs == "ALL":
                return False
            try:
                target = int(self.target_runs)
            except (TypeError, ValueError):
                return False
            return self._runs_done() >= target
        if event_name == "Luxcavation Complete":
            targets = (self.exp_target_runs, self.thread_target_runs)
            if not any(target not in (None, "0") for target in targets):
                return False
            return all(
                target is None or self._lux_runs_done(lux_type) >= int(target)
                for lux_type, target in (("EXP", self.exp_target_runs), ("THREAD", self.thread_target_runs))
            )
        return False

    def _active_scope(self):
        return "lux" if self.context.get("active_scope") == "lux" else "md"

    def _make_event(self, name, value, description=None, extra_fields=None, scope="md", lux_type=None, floor=None, pack=None):
        return {
            "name": name,
            "value": value,
            "description": description,
            "extra_fields": extra_fields or [],
            "scope": scope,
            "lux_type": lux_type,
            "floor": floor,
            "pack": pack
        }

    def _finalize_lux_run(self, lux_type):
        self.context[f"{lux_type.lower()}_runs_done"] += 1
        self.context["active_scope"] = "lux"
        self.context["script_boot"] = False
        label = self._lux_label(lux_type)
        return self._make_event(
            "Luxcavation",
            "Completed",
            description=f"{label} Luxcavation run completed.",
            scope="lux",
            lux_type=lux_type
        )

    def _make_lux_start(self):
        self.context["active_scope"] = "lux"
        self.context["script_boot"] = False
        return self._make_event(
            "Luxcavation Start",
            "Started",
            description="Luxcavation queue started.",
            scope="lux"
        )

    def _make_lux_summary(self):
        self.context["active_scope"] = "lux"
        return self._make_event(
            "Luxcavation Complete",
            "All selected runs completed",
            description="Luxcavation queue completed.",
            scope="lux"
        )

    def _make_floor_event(self, floor_value, description, pack=None):
        extra = [("Floor Time", self._format_duration(self.last_floor_duration), True)]
        return self._make_event(
            "Floor Cleared",
            f"Floor {floor_value}",
            description=description,
            extra_fields=extra,
            floor=floor_value,
            pack=pack
        )

    def _finalize_run(self, now, result_value, description, floor_description, completed):
        self.context["active_scope"] = "md"
        self.last_run_duration = None if self.run_started_at is None else max(0.0, now - self.run_started_at)
        self.last_floor_duration = None if self.floor_started_at is None else max(0.0, now - self.floor_started_at)
        if self.last_run_duration != None:
            self.run_durations.append(self.last_run_duration)
        current_floor = self.context["floor"]
        current_pack = self.context["pack"]
        if completed:
            self.context["runs_done"] += 1
        else:
            self.context["runs_failed"] += 1

        extra = [("Attempt", str(self.context["run_attempts"]), True)]
        if self.context["runs_failed"]:
            extra.append(("Failed Attempts", str(self.context["runs_failed"]), True))
        run_event = self._make_event(
            "Run",
            f"{result_value} ({self._run_progress()})",
            description=description,
            extra_fields=extra,
            floor=current_floor,
            pack=current_pack
        )
        if self.compact_mode or current_floor is None:
            return run_event
        return [self._make_floor_event(current_floor, floor_description, current_pack), run_event]

    def _total_run_duration(self):
        return sum(self.run_durations) if self.run_durations else None

    def _average_run_duration(self):
        return sum(self.run_durations) / len(self.run_durations) if self.run_durations else None


    def _normalize_events(self, event):
        if event is None:
            return []

        items = event if isinstance(event, list) else [event]
        normalized = []
        for item in items:
            if item is None:
                continue
            if isinstance(item, dict):
                name = item.get("name")
                if not name:
                    continue
                normalized.append({
                    "name": str(name),
                    "value": str(item.get("value", "")),
                    "description": item.get("description"),
                    "extra_fields": item.get("extra_fields", []),
                    "scope": item.get("scope", "md"),
                    "lux_type": item.get("lux_type"),
                    "floor": item.get("floor"),
                    "pack": item.get("pack")
                })
                continue

            if isinstance(item, tuple) and len(item) == 2:
                normalized.append({
                    "name": str(item[0]),
                    "value": str(item[1]),
                    "description": None,
                    "extra_fields": [],
                    "scope": "md",
                    "lux_type": None,
                    "floor": None,
                    "pack": None
                })
        return normalized

    def _maybe_run_start_event(self, event_time):
        if self.context["start_announced"]:
            return None
        if not self.context["team"] or not self.context["difficulty"]:
            return None

        focus = self._focus_label(self.context["team"])
        group = self._group_label(self.context["group"]) if self.context["group"] else focus
        self.context["run_attempts"] += 1
        attempt = self.context["run_attempts"]
        prefix = "Script started. " if self.context["script_boot"] and self._runs_done() == 0 else ""

        self.run_started_at = event_time
        self.floor_started_at = None
        self.room_started_at = None
        self.last_room_duration = None
        self.last_floor_duration = None
        self.last_run_duration = None
        self.context["floor"] = None
        self.context["pack"] = None
        self.context["active_scope"] = "md"
        self.context["start_announced"] = True
        self.context["script_boot"] = False
        return self._make_event(
            "Run Start",
            f"Attempt {attempt}",
            description=(
                f"{prefix}Entered Mirror Dungeon with team {group}, "
                f"focus {focus}. Attempt {attempt} started."
            )
        )

    def close(self):
        try:
            self.client.close()
        finally:
            super().close()

    def emit(self, record):
        if self.client.is_disabled():
            return

        message = record.getMessage().strip()
        if not message:
            return

        try:
            event = self._parse_event(record.levelno, message, record.created)
            if event is None:
                return

            if self._is_duplicate(record.levelno, message):
                return

            events = self._normalize_events(event)
            for event_data in events:
                payload = self._build_payload(record, message, event_data)
                self.client.send(payload, priority=record.levelno >= logging.ERROR)
                if event_data["name"] == "Run":
                    self._reset_run_timers()
        except Exception:
            self.handleError(record)

    def _is_duplicate(self, level, message):
        if message in ("Run Completed", "Run Failed", "Exp Luxcavation", "Thread Luxcavation"):
            return False
        now = time.time()
        stale_before = now - 4.0
        self._last_sent = {
            sent_message: sent_at
            for sent_message, sent_at in self._last_sent.items()
            if sent_at >= stale_before
        }
        window = 2.0 if level >= logging.ERROR else 4.0
        last_time = self._last_sent.get(message)
        self._last_sent[message] = now
        return last_time is not None and (now - last_time) < window

    def _parse_event(self, level, message, event_time):
        now = event_time

        if message == "Script started":
            self._refresh_runtime_options()
            self._reset_script_context()
            self.context["script_boot"] = True
            return None

        match = _RE_TEAM.match(message)
        if match:
            self.context["team"] = match.group(1)
            self.context["group"] = None
            self.context["active_scope"] = "md"
            self.context["start_announced"] = False
            return None

        match = _RE_GROUP.match(message)
        if match:
            self.context["group"] = match.group(1)
            return self._maybe_run_start_event(now)

        match = _RE_DIFFICULTY.match(message)
        if match:
            self.context["difficulty"] = match.group(1)
            return self._maybe_run_start_event(now)

        match = _RE_FLOOR.match(message)
        if match:
            self.context["active_scope"] = "md"
            floor_value = int(match.group(1))
            previous_floor = self.context["floor"]
            previous_pack = self.context["pack"]
            floor_changed = previous_floor is not None and floor_value != previous_floor

            if floor_changed and self.floor_started_at is not None:
                self.last_floor_duration = max(0.0, now - self.floor_started_at)
            else:
                self.last_floor_duration = None

            self.context["floor"] = floor_value
            self.floor_started_at = now
            self.room_started_at = None
            self.last_room_duration = None
            self.context["pack"] = None

            # Compact mode now means minimal notifications: no floor-level messages.
            if self.compact_mode:
                return None

            if floor_changed:
                return self._make_floor_event(previous_floor, f"Floor {previous_floor} cleared.", previous_pack)
            return None

        match = _RE_PACK.match(message)
        if match:
            self.context["pack"] = match.group(1)

            if self.compact_mode:
                return None
            if self.context["floor"] is None:
                return None
            return self._make_event(
                "Floor Entered",
                f"Floor {self.context['floor']}",
                description=f"Entered Floor {self.context['floor']} with pack {self.context['pack']}.",
                floor=self.context["floor"],
                pack=self.context["pack"]
            )

        match = _RE_ENTERING.match(message)
        if match:
            if self.room_started_at is not None:
                self.last_room_duration = max(0.0, now - self.room_started_at)
            else:
                self.last_room_duration = None
            self.room_started_at = now
            if self.floor_started_at is None:
                self.floor_started_at = now
            return None

        if message == "Run Completed":
            return self._finalize_run(
                now,
                "Completed",
                "Run completed.",
                f"Floor {self.context['floor']} cleared.",
                completed=True
            )

        if message == "Run Failed":
            return self._finalize_run(
                now,
                "Defeat - all sinners down",
                "Run failed: all selected sinners are dead.",
                f"Floor {self.context['floor']} ended by defeat.",
                completed=False
            )

        if message.startswith("Run Aborted: "):
            return self._make_event("Run", "Aborted", description=message)

        if message in ("Execution paused", "Execution resumed"):
            return self._make_event(
                "Execution",
                message.replace("Execution ", "").capitalize(),
                description=message,
                scope=self._active_scope()
            )

        if message.startswith("Execution stopped: "):
            return self._make_event(
                "Execution",
                "Stopped",
                description=message,
                scope=self._active_scope()
            )

        if message in ("Server error happened", "We are stuck", "Initialization error", "Termination error"):
            return self._make_event(
                "Issue",
                message,
                description=message,
                scope=self._active_scope()
            )

        if message in ("Exp Luxcavation", "Exp Luxcavation Completed"):
            return self._finalize_lux_run("EXP")

        if message in ("Thread Luxcavation", "Thread Luxcavation Completed"):
            return self._finalize_lux_run("THREAD")

        if message == "Luxcavation started":
            return self._make_lux_start()

        if message == "Done with Luxcavation!":
            return self._make_lux_summary()

        if level >= logging.ERROR:
            return self._make_event("Error", message, description=message, scope=self._active_scope())

        if level >= logging.WARNING:
            return self._make_event("Warning", message, description=message, scope=self._active_scope())

        return None

    def _add_field(self, fields, name, value, inline=True):
        if value in (None, ""):
            return
        if len(fields) >= _MAX_FIELDS:
            return
        fields.append({
            "name": _trim(name, _MAX_FIELD_NAME),
            "value": _trim(value, _MAX_FIELD_VALUE),
            "inline": inline
        })

    def _fit_embed(self, title, description, fields, footer):
        remaining = max(0, _MAX_EMBED_CHARS - len(title) - len(footer))
        field_reserve = sum(
            len(field["name"]) + min(len(field["value"]), 128)
            for field in fields
        )
        description = _trim(description, min(len(description), max(0, remaining - field_reserve)))
        remaining -= len(description)

        fitted_fields = []
        for field in fields:
            if remaining < 2:
                break
            name = _trim(field["name"], min(len(field["name"]), remaining - 1))
            value_limit = remaining - len(name)
            if value_limit <= 0:
                break
            value = _trim(field["value"], min(len(field["value"]), value_limit))
            if not name or not value:
                break
            fitted_fields.append({"name": name, "value": value, "inline": field["inline"]})
            remaining -= len(name) + len(value)
        return description, fitted_fields

    def _build_payload(self, record, message, event):
        event_name = event["name"]
        event_value = event["value"]
        scope = event.get("scope", "md")
        lux_type = event.get("lux_type")
        event_floor = event.get("floor") if event.get("floor") is not None else self.context["floor"]
        event_pack = event.get("pack") if event.get("pack") is not None else self.context["pack"]

        if record.levelno >= logging.CRITICAL:
            color = 0x8B0000
            title = "ChargeGrinder Critical"
        elif record.levelno >= logging.ERROR:
            color = 0xE74C3C
            title = "ChargeGrinder Alert"
        elif record.levelno >= logging.WARNING:
            color = 0xF39C12
            title = "ChargeGrinder Warning"
        else:
            color = 0x3498DB
            title = "ChargeGrinder Update"

        fields = []
        if scope == "lux":
            self._add_field(fields, "Status", event_value)
            if event_name == "Luxcavation Start":
                for selected_type in self._selected_lux_types():
                    self._add_field(
                        fields,
                        f"{self._lux_label(selected_type)} Runs Remaining",
                        self._lux_remaining(selected_type)
                    )
            elif lux_type:
                self._add_field(fields, "Luxcavation", self._lux_label(lux_type))
                self._add_field(fields, "Runs Done/Total", self._lux_progress(lux_type))
            else:
                for selected_type in self._selected_lux_types():
                    self._add_field(
                        fields,
                        f"{self._lux_label(selected_type)} Runs Done/Total",
                        self._lux_progress(selected_type)
                    )
        else:
            if event_name == "Run":
                self._add_field(fields, "Status", event_value)
            elif event_name == "Run Start":
                self._add_field(fields, "Run", event_value)
            self._add_field(fields, "Group", self._group_label(self.context["group"]))
            self._add_field(fields, "Focus", self._focus_label(self.context["team"]))
            self._add_field(fields, "Difficulty", self.context["difficulty"])
            self._add_field(fields, "Arayashu", "Active" if params.HOS_MODE else "Inactive")

            if not self.compact_mode:
                if event_floor is not None:
                    self._add_field(fields, "Floor", str(event_floor))
                if event_pack:
                    self._add_field(fields, "Pack Group", event_pack, inline=False)

            if event_name == "Run":
                self._add_field(fields, "Current Run Time", self._format_duration(self.last_run_duration))
                self._add_field(fields, "Total Run Time", self._format_duration(self._total_run_duration()))
                self._add_field(fields, "Average Run Time", self._format_duration(self._average_run_duration()))
                if not self.compact_mode:
                    self._add_field(fields, "Last Floor Time", self._format_duration(self.last_floor_duration))
            elif self.run_started_at is not None:
                self._add_field(fields, "Run Time", self._format_duration(record.created - self.run_started_at))

        for extra in event.get("extra_fields", []):
            if not isinstance(extra, (list, tuple)) or len(extra) < 2:
                continue
            field_name = extra[0]
            field_value = extra[1]
            inline = bool(extra[2]) if len(extra) > 2 else True
            self._add_field(fields, field_name, field_value, inline=inline)

        if scope != "lux":
            self._add_field(fields, "Runs Done/Total", self._run_progress())

        now_utc = datetime.fromtimestamp(record.created, timezone.utc)
        footer = _trim(f"v{APP_VERSION} | {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}", _MAX_FOOTER)
        description = _trim(event.get("description") or f"[{record.levelname}] {message}", _MAX_DESCRIPTION)
        description, fields = self._fit_embed(title, description, fields, footer)

        embed = {
            "title": _trim(title, _MAX_TITLE),
            "description": description,
            "color": color,
            "fields": fields,
            "footer": {"text": footer}
        }

        payload = {
            "username": "ChargeGrinder",
            "embeds": [embed],
            "allowed_mentions": {"parse": []}
        }
        if self._should_ping(record, event_name, event_value):
            payload["content"] = f"<@&{self.ping_role_id}>"
            payload["allowed_mentions"] = {"parse": [], "roles": [self.ping_role_id]}
        return payload


def create_handler_from_env():
    webhook_url = os.environ.get(WEBHOOK_ENV, "").strip()
    if not webhook_url:
        return None, None

    url_error = validate_webhook_url(webhook_url)
    if url_error:
        return None, f"{WEBHOOK_ENV} is set but {url_error}"

    thread_id = os.environ.get(THREAD_ENV, "").strip()
    thread_error = validate_snowflake(thread_id, THREAD_ENV)
    if thread_error:
        return None, thread_error
    thread_id = thread_id or None

    try:
        client = DiscordWebhookClient(webhook_url=webhook_url, thread_id=thread_id)
        return WebhookLogHandler(client), None
    except Exception as error:
        return None, f"Failed to initialize Discord webhook handler: {error}"
