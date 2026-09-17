import os, sys, platform


def _configure_appimage_ca_bundle():
    if (
        "__compiled__" not in globals()
        or sys.platform != "linux"
        or not os.environ.get("APPIMAGE")
        or os.environ.get("SSL_CERT_FILE")
    ):
        return

    bundle_path = os.path.join(BASE_PATH, "cacert.pem")
    if os.path.isfile(bundle_path):
        os.environ["SSL_CERT_FILE"] = bundle_path


def _runtime_base_path():
    # For compiled binaries, keep asset lookup relative to the executable folder.
    if "__compiled__" in globals():
        exe_path = os.path.abspath(sys.executable)
        return os.path.dirname(exe_path)

    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


BASE_PATH = _runtime_base_path()


_configure_appimage_ca_bundle()

VERSION_FILE = os.path.join(BASE_PATH, "version")


def _read_app_version(default="0.0.0"):
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as fh:
            return fh.read().strip() or default
    except OSError:
        return default


APP_VERSION = _read_app_version()


ASSETS_DIR = os.path.join(BASE_PATH,"ImageAssets/UI")

def collect_png_paths(base_dir):
    path_dict = {}
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith(".png") or file.lower().endswith(".ttf"):
                name = os.path.splitext(file)[0]
                if name in path_dict:
                    raise ValueError(f"Duplicate image name detected: {name}")
                full_path = os.path.join(root, file).replace("\\", "/")
                path_dict[name] = full_path
    return path_dict

PTH = collect_png_paths(ASSETS_DIR)

# App.py assets
APP_DIR = os.path.join(BASE_PATH,"ImageAssets/AppUI")
APP_PTH = collect_png_paths(APP_DIR)

if platform.system() == "Windows":
    ICON = os.path.join(BASE_PATH,"ImageAssets","app_icon.ico")
else:
    ICON = os.path.join(BASE_PATH,"ImageAssets","app.png")

# regions for some buttons
REG = {
    # Bot.py
    "Drive"          : (1413,  909,  116,   94),
    "MD"             : ( 528,  354,  279,  196),
    "Start"          : (1473,  657,  315,  161),
    "resume"         : ( 794,  567,  336,   63),
    "enterInvert"    : ( 943,  669,  382,  106),
    "ConfirmTeam"    : (1593,  830,  234,   90),
    "enterBonus"     : (1702,  957,  166,   85),
    "starlight"      : (1069,  525,   42,   42),
    "refuse"         : (1181,  818,  295,  124),
    "giftSearch"     : (1640,  207,   70,   60),
    "giftSearchOn"   : (1640,  207,   70,   60),
    "StartEGO"       : ( 198,  207,  937,  682),
    "Claim"          : (1540,  831,  299,  132),
    "ConfirmInvert"  : ( 987,  704,  318,   71),
    "ClaimInvert"    : (1165,  790,  300,   56),
    "victory"        : (1426,  116,  366,  184),
    "defeat"         : (1426,  116,  366,  184),
    "GiveUp"         : ( 420,  790,  330,   54),
    "Confirm.0"      : ( 816,  657,  471,  197),
    "ServerError"    : ( 651,  640,  309,  124),
    "EventEffect"    : ( 710,  215,  507,   81),
    "bonus"          : ( 763,  348,  151,   59),
    "bonus_off"      : ( 763,  348,  151,   59),
    "hardbonus"      : ( 916,  348,  151,   59),
    "ConfirmInvert.1": ( 987,  704,  318,  130),
    "infinite_off"   : (1690,  500,   45,   30),
    "out_of_fuel"    : ( 750,  150,  424,   66),
    # regions not binded to an image
    "money!"         : (1526,   52,   80,   30),
    "gifts!"         : (1173,  324,  129,  125),
    "selected!"      : (1682,  855,   30,   42),

    # battle.py
    "TOBATTLE"       : (1586,  820,  254,  118),
    "winrate"        : ( 350,  730, 1570,  232),
    "pause"          : (1724,   16,   83,   84),
    "Confirm_alt"    : ( 960,  689,  350,  100),
    "teams"          : (  96,  441,  180,  350),
    "current_team"   : ( 330,  165,  200,   50),
    "arrow"          : ( 189,  443,   16,   15),
    "skip_yap"       : ( 740,  450,  470,  200),
    "ego_warning"    : (1250,  880,  670,  200),
    "ego_usage"      : (1850, 1020,   70,   60),
    "RetryStage"     : ( 937,  476,  170,   46),
    "Confirm_retry"  : ( 829,  763,  278,   53),
    "arayashu"       : (   0,  940, 1920,  140),

    # event.py
    "textEGO"        : (1031,  254,  713,  516),
    "event"          : ( 444,   30,  158,  140),
    "check"          : (1265,  434,  430,   87),
    "choices"        : (1036,  152,  199,   77),
    "skip"           : (1539,  906,  316,  126),
    "Proceed"        : (1539,  906,  316,  126),
    "Commence"       : (1539,  906,  316,  126),
    "Continue"       : (1539,  906,  316,  126),
    "CommenceBattle" : (1539,  906,  316,  126),
    "probs"          : (  42,  900, 1271,   50),

    # grab.py
    "encounterreward": ( 412,  165,  771,   72),
    "Confirm"        : ( 791,  745,  336,  104),
    "Cancel"         : ( 660,  650,  278,   92),
    "EGObin"         : (  87,   49,   90,   90),
    "EGO"            : (   0,  309, 1920,  115),
    "Owned"          : (   0,  216, 1725,   50),
    "Card"           : ( 219,  283, 1531,  242),
    "Confirm.1"      : (1118,  754,  189,   70),
    "trials"         : (   0,  615, 1920,   55),
    "buffs"          : (   0,  664, 1920,   52),
    "adversity"      : (  50,   58,  320,   70),
    "projection"     : (   0,  713, 1920,  100),
    "selectCount"    : (1790,  843,   30,   45),
    # regions not binded to an image
    "rewardCount!"   : (1494,  181,   23,   42),
    "selectCount!"   : (1745,  975,   32,   44),

    # move.py
    "Move"           : (1805,  107,   84,   86),
    "Danteh"         : ( 654,  335,  100,   90),
    "enter"          : (1537,  739,  310,  141),
    "alldead"        : ( 261, 1019, 1391,   41),
    "suicide"        : ( 756,  233,  437,  121),
    "forfeit"        : ( 740,  547,  151,  208),
    "directions"     : ( 482,  130,  200,  800),
    "directions_init": ( 800,  130,  200,  800),
    "secretEncounter": (1595,  767,  183,  100),
    "skipEncounter"  : (1379,  763,  195,  110),

    # pack.py
    "lvl"            : ( 950,  151,   40,   52),
    "PackChoice"     : (1757,  126,  115,  116),
    "PackPull"       : (  40,  440,  440,  200),
    "hardDifficulty" : ( 893,  207,  115,   44),

    # shop.py
    "shop"           : ( 332,  158,  121,   55),
    "supershop"      : ( 275,  158,  220,   55),
    "sell"           : ( 776,  118,  127,   70),
    "notSelected"    : (1209,  435,  153,  140),
    "fusion_available":( 928,  304,  300,   82),
    "fuse_shelf_top" : ( 920,  364,  790,  150),
    "fuse_shelf_peak": ( 920,  304,  790,  150),
    "gifts_owned"    : ( 920,  304,  790,  210),
    "fuse_shelf"     : ( 920,  295,  790,  482),
    "fuse_shelf_low" : ( 920,  591,  790,  150),
    "buy_shelf"      : ( 809,  300,  942,  402),
    "purchase"       : ( 972,  679,  288,   91),
    "power"          : ( 990,  832,  393,   91),
    "Confirm.2"      : ( 990,  832,  393,   91),
    "keywordSel"     : ( 832,  119,  469,   58),
    "keywordRef"     : ( 678,  162,  340,   53),
    "fuse"           : ( 754,  117,  161,   81),
    "scroll"         : (1647,  321,   64,   81),
    "scroll.0"       : (1647,  662,   64,   81),
    "scroll_full"    : (1647,  321,   64,  422),
    "wishmaking"     : ( 384,  731,   49,   53),
    "buy_s3"         : ( 880,  494,  620,   38),
    "replace"        : ( 280,  165,  530,   80),
    "purchased"      : ( 860,  317,  150,   50),
    "purchased_sup!" : (1090,  317,  385,   50),
    "no_hp"          : (  70,  985, 1400,   50),
    "return"         : (1569,  920,  260,  100),
    "select"         : (1569,  920,  260,  100),
    "Confirm_retry.0": ( 987,  704,  318,   71),
    # regions not binded to an image
    "affinity!"      : ( 368,  327, 1160,  442),
    "revenue!"       : (1405,  126,  241,   56),
    "forecast!"      : ( 280,  257,  540,  334),

    # utils.py
    "connecting"     : (1548,   66,  293,   74),
    "loading"        : (1577,  408,  302,   91),

    # lux.py
    "Lux"            : ( 523,  145,  301,  212),
    "Exp"            : (  68,  319,  289,  135),
    "Window"         : (1160,  900,  148,  127),
    "Settings"       : (1726,  116,  150,  150),
    "PassMissions"   : ( 459,   57,  198,   56),
    "Daily"          : ( 372,  328,   70,  115),
    "collect"        : ( 974,  266,   80,  600),
    # regions not binded to an image
    "pick!"          : ( 417,  667, 1428,   95),
    "thd!"           : (1152,  324,  163,  462),
}

SINNERS = {
    "YISANG"    : ( 350, 227, 188, 270),
    "FAUST"     : ( 549, 227, 188, 270),
    "DONQUIXOTE": ( 747, 227, 188, 270),
    "RYOSHU"    : ( 946, 227, 188, 270),
    "MEURSAULT" : (1144, 227, 188, 270),
    "HONGLU"    : (1343, 227, 188, 270),
    "HEATHCLIFF": ( 350, 523, 188, 270),
    "ISHMAEL"   : ( 549, 523, 188, 270),
    "RODION"    : ( 747, 523, 188, 270),
    "SINCLAIR"  : ( 946, 523, 188, 270),
    "OUTIS"     : (1144, 523, 188, 270),
    "GREGOR"    : (1343, 523, 188, 270)
}

WORDLESS = {
    0:  {"name": "falsehalo",           "state": 3, "tier": 4},
    1:  {"name": "pieceofrelationship", "state": 3, "tier": 4},
    2:  {"name": "carmilla",            "state": 3, "tier": 2},
    3:  {"name": "investigatorbadge",   "state": 3, "tier": 2},
    4:  {"name": "ancienteffigy",       "state": 2, "tier": 4},
    5:  {"name": "faith",               "state": 2, "tier": 4},
    6:  {"name": "kimjihoon",           "state": 2, "tier": 4},
    7:  {"name": "grandwelcome",        "state": 2, "tier": 3},
    8:  {"name": "illusoryhunt",        "state": 2, "tier": 3},
    9:  {"name": "prestigecard",        "state": 2, "tier": 3},
    10: {"name": "rustycoin",           "state": 2, "tier": 3},
    11: {"name": "specialcontract",     "state": 2, "tier": 3},
    12: {"name": "blessing",            "state": 2, "tier": 3},
    13: {"name": "tango",               "state": 2, "tier": 3},
    14: {"name": "childwithinflask",    "state": 2, "tier": 2},
    15: {"name": "coffeecranes",        "state": 2, "tier": 2},
    16: {"name": "motheclipse",         "state": 2, "tier": 2},
    17: {"name": "goldenurn",           "state": 2, "tier": 2},
    18: {"name": "homeward",            "state": 2, "tier": 2},
    19: {"name": "oracle",              "state": 2, "tier": 2},
    20: {"name": "painkiller",          "state": 2, "tier": 2},
    21: {"name": "hammer",              "state": 2, "tier": 2},
    22: {"name": "lithograph",          "state": 2, "tier": 1},
    23: {"name": "phlebotomypack",      "state": 2, "tier": 1},
}

WORDLESS_MAP = {v["name"]: v["tier"] for v in WORDLESS.values()}

PACKS = {
    'TheForgotten'                : ((1,), (1,)),
    'TheOutcast'                  : ((1,), (1,)),
    'FlatbrokeGamblers'           : ((1, 2), (1,)),
    'AutomatedFactory'            : ((1, 2), (1, 2)),
    'TheUnloving'                 : ((1, 2), (1, 2)),
    'NagelundHammer'              : ((1,), (1,)),
    'FaithErosion'                : ((1, 2), (1,)),
    'TheUnconfronting'            : ((3,), (2, 3)),
    'NestWorkshopandTechnology'   : ((1, 2), (1,)),
    'FallingFlowers'              : ((3,), (2, 3)),
    'TearfulThings'               : ((4, 5), (3, 4)),
    'TheUnchanging'               : ((), (4, 5)),
    'LakeWorld'                   : ((2,), (1,)),
    'CrawlingAbyss'               : ((4, 5), (3, 4)),
    'TheEvilDefining'             : ((), (4, 5)),
    'DregsoftheManor'             : ((3,), (1,)),
    'ACertainWorld'               : ((4, 5), (3, 4)),
    'TheHeartbreaking'            : ((), (5,)),
    'LaManchalandReopening'       : ((), (5,)),
    'TheInfiniteProcession'       : ((), (5,)),
    'TheDreamEnding'              : ((), (5,)),
    'FourHousesandGreed'          : ((), (5,)),
    'TheSurrenderedWitnessing'    : ((), (5,)),
    'CharmWanderDoubt'            : ((4, 5), (3, 4)),
    'Textbook'                    : ((), (5,)),
    'BladeandArtwork'             : ((), (5,)),
    'TheUnsevering'               : ((), (5,)),
    'HellsChicken'                : ((2,), (2,)),
    'SEA'                         : ((2,), (2, 3)),
    'MiracleinDistrict20'         : ((4,), (3, 4)),
    'toClaimTheirBones'           : ((4, 5), (3, 4)),
    'TimekillingTime'             : ((4, 5), (4, 5)),
    'MurderontheWARPExpress'      : ((4, 5), (4, 5)),
    'TheNoonofViolet'             : ((4,), (3, 4)),
    'Line1'                       : ((), (5,)),
    'Line2'                       : ((), (4, 5)),
    'Line3'                       : ((), (5, 15)),
    'Line4'                       : ((), (5, 15)),
    'MiracleinDistrict20BokGak'   : ((), (4, 5)),
    'FullStoppedbyaBullet'        : ((4,), (3, 4)),
    'LCBRegularCheckup'           : ((5,), (5,)),
    'toClaimTheirBonesBokGak'     : ((), (4, 5)),
    'NocturnalSweeping'           : ((5,), (5,)),
    'Line5'                       : ((), (5, 15)),
    'HatredandDespair'            : ((3, 4), (3, 4)),
    'TimekillingTimeBokGak'       : ((), (4, 5)),
    'SpringCultivation'           : ((5,), (5,)),
    'WARPExpressBokGak'           : ((), (4, 5)),
    'TheDuskofAmber'              : ((4, 5), (4, 5)),
    'LCBRegularCheckupBokGak'     : ((), (4, 5)),
    'TwiningThreads'              : ((5,), (5,)),
    'NocturnalSweepingBokGak'     : ((), (4, 5)),
    'SlicersDicers'               : ((5,), (4,)),
    'TobeCleaved'                 : ((2, 3), (1, 2)),
    'PiercersPenetrators'         : ((5,), (4,)),
    'TobePierced'                 : ((2, 3), (1, 2)),
    'CrushersBreakers'            : ((5,), (4,)),
    'TobeCrushed'                 : ((2, 3), (1, 2)),
    'RepressedWrath'              : ((4, 5), (3, 4)),
    'UnboundWrath'                : ((), (5,)),
    'EmotionalRepression'         : ((3,), (2,)),
    'AddictingLust'               : ((4, 5), (3, 4)),
    'TanglingLust'                : ((), (5,)),
    'EmotionalSeduction'          : ((3,), (2,)),
    'TreadwheelSloth'             : ((4, 5), (3, 4)),
    'InertSloth'                  : ((), (5,)),
    'EmotionalIndolence'          : ((3,), (2,)),
    'DevouredGluttony'            : ((4, 5), (3, 4)),
    'ExcessiveGluttony'           : ((), (5,)),
    'EmotionalCraving'            : ((3,), (2,)),
    'DegradedGloom'               : ((4, 5), (3, 4)),
    'SunkGloom'                   : ((), (5,)),
    'EmotionalFlood'              : ((3,), (2,)),
    'VainPride'                   : ((4, 5), (3, 4)),
    'TyrannicalPride'             : ((), (5,)),
    'EmotionalSubservience'       : ((3,), (2,)),
    'InsignificantEnvy'           : ((4, 5), (3, 4)),
    'PitifulEnvy'                 : ((), (5,)),
    'EmotionalJudgment'           : ((3,), (2,)),
    'BurningHaze'                 : ((), (3,)),
    'SeasonoftheFlame'            : ((), (4, 5)),
    'TrickledSanguineBlood'       : ((), (3,)),
    'MountainofCorpsesSeaofBlood' : ((), (4, 5)),
    'DizzyingWaves'               : ((), (3,)),
    'AbnormalSeismicZone'         : ((), (4, 5)),
    'CrushingExternalForce'       : ((), (3,)),
    'UnrelentingMight'            : ((), (4, 5)),
    'SinkingPang'                 : ((), (3,)),
    'SinkingDeluge'               : ((), (4, 5)),
    'DeepSigh'                    : ((), (3,)),
    'PoisedBreathing'             : ((), (4, 5)),
    'RisingPowerSupply'           : ((), (3,)),
    'ThunderandLightning'         : ((), (4, 5)),
    'NCorp'                       : ((), (15,)),
    'EfflorescingGreenery'        : ((), (15,)),
    'Line3Terminus'               : ((), (15,)),
    'BridleofInfinity'            : ((), (15,)),
    'SeaCR'                       : ((), (15,)),
    'ImpenetrablePath'            : ((), (15,)),
    'Bloodfiends'                 : ((), (15,)),
    'BeautifulVoice'              : ((), (15,)),
    'TheGreenDawn'                : ((), (15,)),
    'CertainLibrary'              : ((), (15,)),
    'CodePurple'                  : ((), (15,)),
    'BearersofWeight'             : ((), (15,)),
    'Line1Madness'                : ((), (15,)),
    'BlessedCarnival'             : ((), (15,)),
    'FairyTale'                   : ((), (15,)),
    'IchthyicOdor'                : ((), (15,)),
    'CompleteExtermination'       : ((), (15,)), 
    'LaManchaMaster'              : ((), (15,)),
    'Chachihu'                    : ((), (15,)),
    'MidspringDream2'             : ((), (15,)),
    'The_BE'                      : ((), (3, 4, 5)),
    'MnesticExperience'           : ((5,), (5,))
}

def packs_to_floors(packs, hard=False):
    floors = {}
    for pack, floor_tuple in packs.items():
        for f in floor_tuple[int(hard)]:
            if f in floors.keys():
                floors[f].append(pack)
            else:
                floors[f] = [pack]
    return floors


FLOORS = packs_to_floors(PACKS, hard=False)
HARD_FLOORS = packs_to_floors(PACKS, hard=True)

BANNED = [
    "AutomatedFactory", "TheUnloving", "FaithErosion", "TobeCrushed", "TheNoonofViolet", 
    "MurderontheWARPExpress", "FullStoppedbyaBullet", "VainPride", "CrawlingAbyss", "TimekillingTime", 
    "NocturnalSweeping", "toClaimTheirBones", "TheDuskofAmber", "CharmWanderDoubt"
]

HARD_BANNED = [
    "TheNoonofViolet", "MurderontheWARPExpress", "FullStoppedbyaBullet", "TimekillingTime", 
    "NocturnalSweeping", 'Line4', 'Line3', 'toClaimTheirBonesBokGak', 'TheEvilDefining', 
    'SinkingDeluge', 'PoisedBreathing', 'InertSloth', 'EmotionalFlood', 'CrawlingAbyss', 
    'TreadwheelSloth', 'VainPride', 'PitifulEnvy', 'TyrannicalPride', 'UnrelentingMight', 
    'Line5', 'TheSurrenderedWitnessing', 'ImpenetrablePath', "TheDuskofAmber", 
    "CharmWanderDoubt", "Textbook", "BladeandArtwork", "TheUnsevering"
]


def get_unique(pack_list):
    unique = []
    seen = set()
    for floor in sorted(pack_list):
        for item in pack_list[floor]:
            if item not in seen:
                seen.add(item)
                unique.append(item)
    return unique


FLOORS_UNIQUE = get_unique(FLOORS)
HARD_UNIQUE = get_unique(HARD_FLOORS)



if __name__ == "__main__":
    count = 0
    for name, floors in PACKS.items():
        easy, hard = floors
        
        if 5 in hard:
            print(f"{name}")
            count += 1
        
    print(count, "packs")
