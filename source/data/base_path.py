import os
import sys


try:
    BASE_PATH = sys._MEIPASS
except AttributeError:
    BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


ASSETS_DIR = os.path.join(BASE_PATH, "ImageAssets/GameUI")

DATA_DIR   = os.path.join(BASE_PATH, "source/data")
JSON_PATH  = os.path.join(DATA_DIR, "assets.json")
GEN_PATH   = os.path.join(DATA_DIR, "assets_generated.py")