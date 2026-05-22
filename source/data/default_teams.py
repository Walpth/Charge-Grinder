# Burn
TEAMS = {
    "BURN": {
        "checks" : ["Burn", "smallBurn", (315, 370), "reBurn", "bigBurn", 0],
        "floors" : ["TheOutcast", "HellsChicken", "LCBRegularCheckup"],
        "uptie1" : {"hellterfly": 2, "fiery": 2},
        "uptie2" : {"glimpse": 4},
        "uptie3" : {},
        "goal"   : ["soothe"],
        "fuse1"  : {"stew": 2, "paraffin": 1}, # book
        "fuse2"  : {"book": None, "dust": 3, "ash": 1}, # soothe
        "fuse_ex": {"disk": 3},
        "buy"    : ["glimpse", "wing", "dust", "stew", "paraffin", "ash", "disk", "hellterfly", "fiery"], # order is important
        "all"    : ["glimpse", "dust", "stew", "paraffin", "ash", "book", "hellterfly", "fiery", "wing", "soothe", "disk"],
        "sin"    : True
    },

    # Bleed
    "BLEED": {
        "checks" : ["Bleed", "smallBleed", (535, 370), "reBleed", "bigBleed", 0],
        "floors" : ["FaithErosion", "TheOutcast", "HellsChicken"],
        "uptie1" : {"clerid": 2}, # wolf
        "uptie2" : {"redstained": 4, "gossypium": 2},
        "uptie3" : {"muzzle": 1},
        "goal"   : ["redmist"],
        "fuse1"  : {"millarca": 2, "hymn": 1}, # devotion
        "fuse2"  : {"devotion": None, "smokeswires": 3, "muzzle": 1}, # redmist 
        "fuse_ex": {"gossypium": 2},
        "buy"    : ["redstained", "gossypium", "smokeswires", "millarca", "muzzle", "hymn", "contaminatedneedle", "fracturedblade", "scripture", "rustedknife", "clerid"],
        "all"    : ["clerid", "wolf", "devotion", "redmist", "redstained", "gossypium", "smokeswires", "millarca", "muzzle", "hymn", "contaminatedneedle", "fracturedblade", "scripture", "rustedknife"],
        "sin"    : True
    },

    # Tremor
    "TREMOR": {
        "checks" : ["Tremor", "smallTremor", (755, 370), "reTremor", "bigTremor", 0],
        "floors" : ["SEA", "ACertainWorld"],
        "uptie1" : {"bracelet": 2, "reverberation": 2},
        "uptie2" : {"downpour": 4},
        "uptie3" : {"truthbell": 3},
        "goal"   : ["oscillation"],
        "fuse1"  : {}, 
        "fuse2"  : {"truthbell": 3, "cogs": 2, "nixie": 1}, # oscillation
        "fuse_ex": {"eyeball": 3}, 
        "buy"    : ["downpour", "truthbell", "cogs", "nixie", "synaesthesia", "spanner", "clockwork", "biovial", "eyeball", "bracelet", "reverberation"],
        "all"    : ["oscillation", "bracelet", "reverberation", "downpour", "truthbell", "cogs", "nixie", "synaesthesia", "spanner", "clockwork", "biovial", "eyeball"],
        "sin"    : True
    },

    # Rupture
    "RUPTURE": {
        "checks" : ["Rupture", "smallRupture", (975, 370), "reRupture", "bigRupture", 1],
        "floors" : ["TheOutcast", "HellsChicken", "LCBRegularCheckup"],
        "uptie1" : {"lamp": 2}, # "thunderbranch" "lasso"
        "uptie2" : {"thrill": 4, "thunderbranch": 3},
        "uptie3" : {"bundle": 1},
        "goal"   : ["trance"],
        "fuse1"  : {},
        "fuse2"  : {"battery": 3, "rope": 2, "bundle": 1}, # trance
        "fuse_ex": {"thunderbranch": 3}, 
        "buy"    : ["thrill", "breast", "thunderbranch", "battery", "rope", "bundle", "umbrella", "lamp"],
        "all"    : ["thrill", "lasso", "lamp", "breast", "battery", "rope", "thunderbranch", "brooch", "bundle", "trance", "umbrella"],
        "sin"    : True
    },

    # Sinking
    "SINKING": {
        "checks" : ["Sinking", "smallSinking", (315, 665), "reSinking", "bigSinking", 0],
        "floors" : ["DregsoftheManor", "ACertainWorld"],
        "uptie1" : {"redorder": 2},
        "uptie2" : {"artisticsense": 4},
        "uptie3" : {},
        "goal"   : ["musicsheet"],
        "fuse1"  : {},
        "fuse2"  : {"midwinter": 3, "tangledbones": 2, "headlessportrait": 1}, # musicsheet
        "fuse_ex": {},    
        "buy"    : ["musicsheet", "midwinter", "tangledbones", "headlessportrait", "compass", "crumbs", "meltedspring", "redorder"],
        "all"    : ["redorder", "meltedspring", "artisticsense", "musicsheet", "midwinter", "tangledbones", "headlessportrait", "compass", "crumbs"],
        "sin"    : True
    },

    # Poise
    "POISE": {
        "checks" : ["Poise", "smallPoise", (535, 665), "rePoise", "bigPoise", 1],
        "floors" : [],
        "uptie1" : {"stonetomb": 2}, # holder
        "uptie2" : {"clearmirror": 4, "nebulizer": 2, "devil": 1},
        "uptie3" : {},
        "goal"   : ["luckypouch"],
        "fuse1"  : {"recollection": 2, "pendant": 1},
        "fuse2"  : {"reminiscence": None, "clover": 3, "horseshoe": 1}, # luckypouch 
        "fuse_ex": {"nebulizer": 2}, 
        "buy"    : ["clearmirror", "nebulizer", "clover", "recollection", "pendant", "horseshoe", "bamboohat", "brokenblade", "finifugality", "devil"],
        "all"    : ["luckypouch", "stonetomb", "holder", "reminiscence", "clearmirror", "nebulizer", "clover", "recollection", "pendant", "horseshoe", "bamboohat", "brokenblade", "finifugality", "devil"],
        "sin"    : True
    },

    # Charge
    "CHARGE": {
        "checks" : ["Charge", "smallCharge", (755, 665), "reCharge", "bigCharge", 0],
        "floors" : ["HellsChicken"],
        "uptie1" : {"employeecard": 2, "batterysocket": 2},
        "uptie2" : {"gloves": 4, "vitae": 1},
        "uptie3" : {"wristguards": 1},
        "goal"   : ["T-1"],
        "fuse1"  : {},
        "fuse2"  : {"forcefield": 3, "bolt": 2, "wristguards": 1}, # T-1
        "fuse_ex": {},   
        "buy"    : ["gloves", "forcefield", "bolt", "wristguards", "imitativegenerator", "vitae", "employeecard", "batterysocket"],
        "all"    : ["employeecard", "batterysocket", "T-1", "gloves", "forcefield", "bolt", "wristguards", "imitativegenerator", "vitae"],
        "sin"    : True
    },

    "SLASH": {
        "checks" : ["Slash", "smallSlash", (975, 665), "reSlash", "bigSlash", 1],
        "floors" : [],
        "uptie1" : {"shortcane": 2},
        "uptie2" : {"slashmemory": 4},
        "goal"   : [],
        "fuse1"  : {},
        "fuse2"  : {},
        "fuse_ex": {},
        "buy"    : ["slashmemory"],
        "all"    : ["shortcane", "slashmemory"],
        "sin"    : False
    },

    "PIERCE": {
        "checks" : ["Pierce", "smallPierce", (315, 840), "rePierce", "bigPierce", 1],
        "floors" : [],
        "uptie1" : {"plumeproof": 2},
        "uptie2" : {"piercememory": 4},
        "goal"   : [],
        "fuse1"  : {},
        "fuse2"  : {},
        "fuse_ex": {},
        "buy"    : ["piercememory"],
        "all"    : ["plumeproof", "piercememory"],
        "sin"    : False
    },

    "BLUNT": {
        "checks" : ["Blunt", "smallBlunt", (535, 840), "reBlunt", "bigBlunt", 0],
        "floors" : [],
        "uptie1" : {},
        "uptie2" : {"bluntmemory": 4},
        "goal"   : [],
        "fuse1"  : {},
        "fuse2"  : {},
        "fuse_ex": {},
        "buy"    : ["bluntmemory"],
        "all"    : ["bluntmemory"],
        "sin"    : False
    },
}

# HARDMODE
HARD = {
    "BURN": {
        "checks" : ["Burn", "smallBurn", (315, 370), "reBurn", "bigBurn", 0],
        "floors" : ["TheOutcast", "HellsChicken", "LCBRegularCheckup"],
        "uptie1" : {"hellterfly": 2, "fiery": 2},
        "uptie2" : {"glimpse": 4},
        "uptie3" : {},
        "goal"   : ["soothe", "purloinedflame"],
        "fuse1"  : {"stew": 2, "paraffin": 1}, # book
        "fuse2"  : {"book": None, "dust": 3, "ash": 1}, # soothe

        "fuse3"  : {},
        "fuse4"  : {"disk": 3, "hearthflame": 2, "intellect": 1}, # purloinedflame

        "fuse_ex": {},

        "buy"    : ["glimpse", "wing", "dust", "stew", "paraffin", "ash", "disk", "hearthflame", "intellect", "hellterfly", "fiery"], # order is important
        "all"    : ["glimpse", "dust", "stew", "paraffin", "ash", "book", "hellterfly", "fiery", "wing", "soothe",
                    "purloinedflame", "disk", "hearthflame", "intellect"],
        "sin"    : True
    },

    # Bleed
    "BLEED": {
        "checks" : ["Bleed", "smallBleed", (535, 370), "reBleed", "bigBleed", 0],
        "floors" : ["FaithErosion", "TheOutcast", "HellsChicken"],
        "uptie1" : {"clerid": 2}, # wolf
        "uptie2" : {"redstained": 4, "gossypium": 2},
        "uptie3" : {"muzzle": 1},
        "goal"   : ["redmist", "hemorrhagicshock"],
        "fuse1"  : {"millarca": 2, "hymn": 1}, # devotion
        "fuse2"  : {"devotion": None, "smokeswires": 3, "muzzle": 1}, # redmist

        "fuse3"  : {},
        "fuse4"  : {"bloodsack": 3, "rustedknife": 3, "ironstake": 1}, # hemorrhagicshock

        "fuse_ex": {"gossypium": 2},

        "buy"    : ["redstained", "gossypium", "smokeswires", "millarca", "muzzle", "hymn", "bloodsack", "rustedknife", "ironstake", "contaminatedneedle", "fracturedblade", "scripture", "clerid"],
        "all"    : ["clerid", "wolf", "devotion", "redmist", "redstained", "gossypium", "smokeswires", "millarca", "muzzle", "hymn", "contaminatedneedle", 
                    "fracturedblade", "scripture", "hemorrhagicshock", "rustedknife", "bloodsack", "ironstake"],
        "sin"    : True
    },

    # Tremor
    "TREMOR": {
        "checks" : ["Tremor", "smallTremor", (755, 370), "reTremor", "bigTremor", 0],
        "floors" : ["SEA", "ACertainWorld"],
        "uptie1" : {"bracelet": 2, "reverberation": 2},
        "uptie2" : {"downpour": 4},
        "uptie3" : {"truthbell": 3},
        "goal"   : ["oscillation", "vibrobell"],
        "fuse1"  : {},
        "fuse2"  : {"truthbell": 3, "cogs": 2, "nixie": 1}, # oscillation

        "fuse3"  : {"wobblingkeg": 2, "gemstone": 1}, # epicenter
        "fuse4"  : {"epicenter": None, "clockwork": 3, "venomousskin": 1}, # vibrobell

        "fuse_ex": {"eyeball": 3}, 

        "buy"    : ["downpour", "truthbell", "cogs", "nixie", "clockwork", "wobblingkeg", "gemstone", "venomousskin", "synaesthesia", "spanner", "biovial", "eyeball", "bracelet", "reverberation"],
        "all"    : ["oscillation", "bracelet", "reverberation", "downpour", "truthbell", "cogs", "nixie", "synaesthesia", "spanner", 
                    "clockwork", "biovial", "eyeball", "vibrobell", "epicenter", "venomousskin", "wobblingkeg", "gemstone"],
        "sin"    : True
    },

    # Rupture
    "RUPTURE": {
        "checks" : ["Rupture", "smallRupture", (975, 370), "reRupture", "bigRupture", 1],
        "floors" : ["TheOutcast", "HellsChicken", "LCBRegularCheckup"],
        "uptie1" : {"lamp": 2}, # "thunderbranch" "lasso"
        "uptie2" : {"thrill": 4},
        "uptie3" : {"thunderbranch": 3, "bundle": 1},
        "goal"   : ["trance", "ruin"],
        "fuse1"  : {},
        "fuse2"  : {"battery": 3, "rope": 2, "bundle": 1}, # trance
        
        "fuse3"  : {"apocalypse": 2, "bonestake": 1}, # effigy
        "fuse4"  : {"effigy": None, "thunderbranch": 3, "gun": 1}, # ruin

        "fuse_ex": {},  

        "buy"    : ["thrill", "breast", "thunderbranch", "battery", "rope", "apocalypse", "bundle", "bonestake", "gun", "umbrella", "lamp"],
        "all"    : ["thrill", "lasso", "lamp", "breast", "battery", "rope", "thunderbranch", "brooch", "bundle", "trance", "umbrella",
                    "ruin", "effigy", "gun", "apocalypse", "bonestake"],
        "sin"    : True
    },

    # Sinking
    "SINKING": {
        "checks" : ["Sinking", "smallSinking", (315, 665), "reSinking", "bigSinking", 0],
        "floors" : ["DregsoftheManor", "ACertainWorld"],
        "uptie1" : {"redorder": 2},
        "uptie2" : {"artisticsense": 4},
        "uptie3" : {},
        "goal"   : ["musicsheet", "wave"],
        "fuse1"  : {},
        "fuse2"  : {"midwinter": 3, "tangledbones": 2, "headlessportrait": 1}, # musicsheet

        "fuse3"  : {"overcoat": 2, "cantabile": 1},
        "fuse4"  : {"globe": None, "distantstar": 3, "thornypath": 1}, # wave

        "fuse_ex": {},  

        "buy"    : ["musicsheet", "midwinter", "tangledbones", "headlessportrait", "distantstar", "overcoat", "cantabile", "thornypath", "compass", "crumbs", "redorder"],
        "all"    : ["redorder", "meltedspring", "artisticsense", "musicsheet", "midwinter", "tangledbones", "headlessportrait", "compass", "crumbs",
                    "wave", "globe", "distantstar", "thornypath", "overcoat", "cantabile"],
        "sin"    : True
    },

    # Poise
    "POISE": {
        "checks" : ["Poise", "smallPoise", (535, 665), "rePoise", "bigPoise", 1],
        "floors" : [],
        "uptie1" : {"stonetomb": 2}, # holder
        "uptie2" : {"clearmirror": 4, "nebulizer": 2},
        "uptie3" : {"devil": 1},
        "goal"   : ["luckypouch", "spirits"],
        "fuse1"  : {"recollection": 2, "pendant": 1},
        "fuse2"  : {"reminiscence": None, "clover": 3, "horseshoe": 1}, # luckypouch

        "fuse3"  : {},
        "fuse4"  : {"endorphinkit": 3, "angel": 2, "devil": 1}, # spirits

        "fuse_ex": {"nebulizer": 2},

        "buy"    : ["clearmirror", "nebulizer", "clover", "recollection", "pendant", "horseshoe", "endorphinkit", "angel", "devil", "bamboohat", "brokenblade", "finifugality"],
        "all"    : ["luckypouch", "stonetomb", "holder", "reminiscence", "clearmirror", "nebulizer", "clover", "recollection", "pendant", 
                    "horseshoe", "bamboohat", "brokenblade", "finifugality", "spirits", "endorphinkit", "angel", "devil"],
        "sin"    : True
    },

    # Charge
    "CHARGE": {
        "checks" : ["Charge", "smallCharge", (755, 665), "reCharge", "bigCharge", 0],
        "floors" : ["HellsChicken"],
        "uptie1" : {"employeecard": 2, "batterysocket": 2},
        "uptie2" : {"gloves": 4},
        "uptie3" : {"wristguards": 1, "vitae": 1},
        "goal"   : ["T-1", "T-5"],
        "fuse1"  : {},
        "fuse2"  : {"forcefield": 3, "bolt": 2, "wristguards": 1}, # T-1

        "fuse3"  : {"minitelepole": 2, "UPS": 1}, # insulator
        "fuse4"  : {"insulator": None, "rod": 3, "vitae": 1}, # T-5

        "fuse_ex": {}, 

        "buy"    : ["gloves", "forcefield", "bolt", "wristguards", "minitelepole", "rod", "vitae", "UPS", "imitativegenerator", "employeecard", "batterysocket"],
        "all"    : ["employeecard", "batterysocket", "T-1", "gloves", "forcefield", "bolt", "wristguards", "imitativegenerator",
                    "T-5", "insulator", "rod", "vitae", "minitelepole", "UPS"],
        "sin"    : True
    },

    "SLASH": {
        "checks" : ["Slash", "smallSlash", (975, 665), "reSlash", "bigSlash", 1],
        "floors" : [],
        "uptie1" : {"shortcane": 2},
        "uptie2" : {"slashmemory": 4},
        "goal"   : [],
        "fuse1"  : {},
        "fuse2"  : {},
        "fuse3"  : {},
        "fuse4"  : {},
        "fuse_ex": {},
        "buy"    : ["slashmemory"],
        "all"    : ["shortcane", "slashmemory"],
        "sin"    : False
    },

    "PIERCE": {
        "checks" : ["Pierce", "smallPierce", (315, 840), "rePierce", "bigPierce", 1],
        "floors" : [],
        "uptie1" : {"plumeproof": 2},
        "uptie2" : {"piercememory": 4},
        "goal"   : [],
        "fuse1"  : {},
        "fuse2"  : {},
        "fuse3"  : {},
        "fuse4"  : {},
        "fuse_ex": {},
        "buy"    : ["piercememory"],
        "all"    : ["plumeproof", "piercememory"],
        "sin"    : False
    },

    "BLUNT": {
        "checks" : ["Blunt", "smallBlunt", (535, 840), "reBlunt", "bigBlunt", 0],
        "floors" : [],
        "uptie1" : {},
        "uptie2" : {"bluntmemory": 4},
        "goal"   : [],
        "fuse1"  : {},
        "fuse2"  : {},
        "fuse3"  : {},
        "fuse4"  : {},
        "fuse_ex": {},
        "buy"    : ["bluntmemory"],
        "all"    : ["bluntmemory"],
        "sin"    : False
    },
}

SINNERS = {
    "YISANG"    : ( 351, 207, 196, 285),
    "FAUST"     : ( 547, 207, 196, 285),
    "DONQUIXOTE": ( 743, 207, 196, 285),
    "RYOSHU"    : ( 939, 207, 196, 285),
    "MEURSAULT" : (1135, 207, 196, 285),
    "HONGLU"    : (1331, 207, 196, 285),
    "HEATHCLIFF": ( 351, 492, 196, 285),
    "ISHMAEL"   : ( 547, 492, 196, 285),
    "RODION"    : ( 743, 492, 196, 285),
    "SINCLAIR"  : ( 939, 492, 196, 285),
    "OUTIS"     : (1135, 492, 196, 285),
    "GREGOR"    : (1331, 492, 196, 285)
}