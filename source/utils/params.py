import threading

LIMBUS_NAME = "LimbusCompany"

SELECTED = ["YISANG", "DONQUIXOTE" , "ISHMAEL", "RODION", "SINCLAIR", "GREGOR"]
GIFTS = []
TEAM = ["BURN"]
NAME_ORDER = 0
DUPLICATES = False

LOG = True
BONUS = False
COLLECT = True
RESTART = True
ALTF4 = False
ALTF4_lux = False
NETZACH = False
SKIP = True
WINRATE = False
WISHMAKING = False
BUFF = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
CARD = [1, 0, 2, 3, 4]
KEYWORDLESS = {}
HARD = False
EXTREME = False
APP = None

HOS_MODE = False

PICK = {}
IGNORE = {}
PICK_ALL = {}

WARNING = None
WINDOW = (0, 0, 1920, 1080)
SCREEN = None

pause_event = threading.Event()
stop_event = threading.Event()
STOP_REASON = None

LVL = 1
SUPER = "shop" # for Hard MD
DEAD = 0
IDX = 0
TO_UPTIE = {}
MOVE_ANIMATION = False

# Macro behavior configuration.
MACRO_PROFILE = "SAFE"
MACRO_RHYTHM = True
KEY_ERRORS = 0


def resolve_window_rect(left, top, client_width, client_height):
    """Resolve the capture/click region inside the game client area.

    Clients at 16:9 or wider crop to a centered 16:9 region; clients taller
    than 16:9 (e.g. 2560x1600 fullscreen) keep the full client area - the
    game expands its canvas vertically instead of letterboxing.
    """
    target_ratio = 16 / 9
    if client_width / client_height > target_ratio:
        target_height = client_height
        target_width = int(target_height * target_ratio)
        left += (client_width - target_width) // 2
        top += (client_height - target_height) // 2
    else:
        target_width = client_width
        target_height = client_height
    return left, top, target_width, target_height


def is_supported_aspect(width, height):
    """True when the client aspect is a supported game aspect (16:9 or 16:10)."""
    return int(width / 16) in (int(height / 9), int(height / 10))


def expand_extra_height():
    """Extra vertical reference units (over the 1080 base) the game canvas
    gains on taller-than-16:9 clients (e.g. 120 at 2560x1600 fullscreen)."""
    comp = WINDOW[2] / 1920
    if comp <= 0:
        return 0
    return max(0, int(round(WINDOW[3] / comp)) - 1080)
