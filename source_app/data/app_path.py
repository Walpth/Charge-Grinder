import os
import platform

from source.data import BASE_PATH


APP_DIR = os.path.join(BASE_PATH,"ImageAssets/AppUI")
FONT = os.path.join(APP_DIR,"font/ExcelsiorSans.ttf")

if platform.system() == "Windows":
    ICON = os.path.join(BASE_PATH,"app_icon.ico")
else:
    ICON = os.path.join(BASE_PATH,"app.png")