# -*- mode: python ; coding: utf-8 -*-

import os
from glob import glob

def collect(src_dir, dst_dir, patterns=("*.png", "*.ttf", "*.ico")):
    files = []
    for pat in patterns:
        files += [(f, dst_dir) for f in glob(os.path.join(src_dir, pat))]
    return files


datas = []
datas += [('AppDir/app.png', '.')]

datas += collect('ImageAssets/GameUI', 'ImageAssets/GameUI')

datas += collect('ImageAssets/GameUI/lux', 'ImageAssets/GameUI/lux')
datas += collect('ImageAssets/GameUI/lux/select', 'ImageAssets/GameUI/lux/select')

datas += collect('ImageAssets/GameUI/pack', 'ImageAssets/GameUI/pack')
datas += collect('ImageAssets/GameUI/pack/easy', 'ImageAssets/GameUI/pack/easy')
datas += collect('ImageAssets/GameUI/pack/hard', 'ImageAssets/GameUI/pack/hard')
datas += collect('ImageAssets/GameUI/pack/level', 'ImageAssets/GameUI/pack/level')

datas += collect('ImageAssets/GameUI/battle', 'ImageAssets/GameUI/battle')
datas += collect('ImageAssets/GameUI/battle/ego', 'ImageAssets/GameUI/battle/ego')
datas += collect('ImageAssets/GameUI/battle/sins', 'ImageAssets/GameUI/battle/sins')

datas += collect('ImageAssets/GameUI/end', 'ImageAssets/GameUI/end')
datas += collect('ImageAssets/GameUI/event', 'ImageAssets/GameUI/event')
datas += collect('ImageAssets/GameUI/event/sinprob', 'ImageAssets/GameUI/event/sinprob')
datas += collect('ImageAssets/GameUI/event/favorite', 'ImageAssets/GameUI/event/favorite')
datas += collect('ImageAssets/GameUI/event/teams', 'ImageAssets/GameUI/event/teams')

datas += collect('ImageAssets/GameUI/grab', 'ImageAssets/GameUI/grab')
datas += collect('ImageAssets/GameUI/grab/card', 'ImageAssets/GameUI/grab/card')
datas += collect('ImageAssets/GameUI/grab/levels', 'ImageAssets/GameUI/grab/levels')
datas += collect('ImageAssets/GameUI/grab/buffs', 'ImageAssets/GameUI/grab/buffs')

datas += collect('ImageAssets/GameUI/move', 'ImageAssets/GameUI/move')
datas += collect('ImageAssets/GameUI/shop', 'ImageAssets/GameUI/shop')
datas += collect('ImageAssets/GameUI/start', 'ImageAssets/GameUI/start')

datas += collect('ImageAssets/GameUI/shop/buy', 'ImageAssets/GameUI/shop/buy')
datas += collect('ImageAssets/GameUI/shop/fuse', 'ImageAssets/GameUI/shop/fuse')
datas += collect('ImageAssets/GameUI/shop/cost', 'ImageAssets/GameUI/shop/cost')
datas += collect('ImageAssets/GameUI/shop/skill3', 'ImageAssets/GameUI/shop/skill3')

teams = [
    "Keywordless", "Bleed", "Burn", "Charge", "Poise",
    "Rupture", "Sinking", "Tremor", "Slash", "Pierce", "Blunt"
]

for team in teams:
    base = f"ImageAssets/GameUI/teams/{team}"
    datas += collect(base, base)
    datas += collect(f"{base}/gifts", f"{base}/gifts")
    datas += collect(f"{base}/select", f"{base}/select")

datas += collect('ImageAssets/AppUI', 'ImageAssets/AppUI')
datas += collect('ImageAssets/AppUI/font', 'ImageAssets/AppUI/font', patterns=("*.ttf",))
datas += collect('ImageAssets/AppUI/affinity', 'ImageAssets/AppUI/affinity')
datas += collect('ImageAssets/AppUI/selected', 'ImageAssets/AppUI/selected')


a = Analysis(
    ['App.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["source_app/runtime_hooks.py"],
    excludes=["source.utils.os_windows_backend"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='app',
    debug=False,
    strip=True,
    upx=False,
    console=False,
    icon='AppDir/app.png',
)