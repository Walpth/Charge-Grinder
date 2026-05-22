PACKS = {
    'TheForgotten'                : ((1,), (1,)),
    'TheOutcast'                  : ((1,), (1,)),
    'FlatbrokeGamblers'           : ((1, 2), (1,)),
    'AutomatedFactory'            : ((1, 2), (1, 2)),
    'TheUnloving'                 : ((1, 2), (1, 2)),
    'NagelundHammer'              : ((1,), (1,)),
    'FaithErosion'                : ((1, 2), (1,)),
    'TheUnconfronting'            : ((3,), (3,)),
    'NestWorkshopandTechnology'   : ((1, 2), (1,)),
    'FallingFlowers'              : ((3,), (2,)),
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
    'SEA'                         : ((2,), (2,)),
    'MiracleinDistrict20'         : ((4,), (3,)),
    'toClaimTheirBones'           : ((4, 5), (3, 4)),
    'TimekillingTime'             : ((4, 5), (4, 5)),
    'MurderontheWARPExpress'      : ((4, 5), (4, 5)),
    'TheNoonofViolet'             : ((4,), (3,)),
    'Line1'                       : ((), (4, 5)),
    'Line2'                       : ((), (4,)),
    'Line3'                       : ((), (5, 15)),
    'Line4'                       : ((), (5, 15)),
    'MiracleinDistrict20BokGak'   : ((), (4, 5)),
    'FullStoppedbyaBullet'        : ((4,), (3,)),
    'LCBRegularCheckup'           : ((5,), (5,)),
    'toClaimTheirBonesBokGak'     : ((), (4, 5)),
    'NocturnalSweeping'           : ((5,), (5,)),
    'Line5'                       : ((), (5, 15)),
    'HatredandDespair'            : ((3, 4), (3, 4)),
    'TimekillingTimeBokGak'       : ((), (4, 5)),
    'SpringCultivation'           : ((5,), (5,)),
    'WARPExpressBokGak'           : ((), (4, 5)),
    'TheDuskofAmber'              : ((4, 5), (4, 5)),
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
    "NocturnalSweeping", "toClaimTheirBones"
]

HARD_BANNED = [
    "TheNoonofViolet", "MurderontheWARPExpress", "FullStoppedbyaBullet", "TimekillingTime", 
    "NocturnalSweeping", 'Line4', 'Line3', 'toClaimTheirBonesBokGak', 'TheEvilDefining', 
    'SinkingDeluge', 'PoisedBreathing', 'InertSloth', 'EmotionalFlood', 'CrawlingAbyss', 
    'TreadwheelSloth', 'VainPride', 'PitifulEnvy', 'TyrannicalPride', 'UnrelentingMight', 
    'Line5', 'TheSurrenderedWitnessing', 'TheDreamEnding', 'HatredandDespair', 
    'TimekillingTimeBokGak', 'ImpenetrablePath'
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


from source_app.data.bot_config import GameMode

def generate_packs_pr(input_priority, difficulty):
    priority, priority_f = input_priority
    is_hard = difficulty >= GameMode.HARD
    is_extreme = difficulty == GameMode.EXTREME
    
    packs = {f"floor{i}": [] for i in range(1, 6 + is_extreme*10)}
    floors = HARD_FLOORS if is_hard else FLOORS

    for i in range(1, 6 + is_extreme*10):
        for pack in priority:
            assigned_on_this_floor = {pack for pack, fl in priority_f.items() if fl == i}
            if (pack in floors[format_lvl(i)] and (
               (pack in priority_f and priority_f[pack] == i) or
               (pack not in priority_f and not assigned_on_this_floor))):
                packs[f"floor{i}"].append(pack)
    return packs

def generate_packs_av(input_avoid, difficulty):
    avoid, priority_f, avoid_f = input_avoid
    is_hard = difficulty >= GameMode.HARD
    is_extreme = difficulty == GameMode.EXTREME
    
    packs = {f"floor{i}": [] for i in range(1, 6 + is_extreme*10)}
    floors = HARD_FLOORS if is_hard else FLOORS

    for i in range(1, 6 + is_extreme*10):
        for pack in avoid:
            if (pack in floors[format_lvl(i)] and (
               (pack in avoid_f and avoid_f[pack] == i) or
               (pack not in avoid_f))):
                packs[f"floor{i}"].append(pack)
        for pack in priority_f.keys():
            if pack in floors[format_lvl(i)] and priority_f[pack] != i:
                packs[f"floor{i}"].append(pack)
    return packs

def format_lvl(lvl):
    if lvl < 6: return lvl
    elif lvl < 11: return 5
    else: return 15

def generate_packs_all(input_priority, difficulty):
    priority, priority_f = input_priority
    is_hard = difficulty >= GameMode.HARD
    is_extreme = difficulty == GameMode.EXTREME

    packs = {f"floor{i}": [] for i in range(1, 6 + is_extreme*10)}
    floors = HARD_FLOORS if is_hard else FLOORS

    for i in range(1, 6 + is_extreme*10):
        packs[f"floor{i}"] = list((set(priority) - set(priority_f.keys())) & set(floors[format_lvl(i)]))
    return packs