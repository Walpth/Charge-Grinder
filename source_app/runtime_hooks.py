import os
import sys
import platform

if getattr(sys, "frozen", False):
    base = sys._MEIPASS

    qt_plugins = os.path.join(base, "PyQt6", "Qt6", "plugins")

    if os.path.isdir(qt_plugins):
        os.environ["QT_PLUGIN_PATH"] = qt_plugins
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(qt_plugins, "platforms")

    if platform.system() == "Windows":
        os.add_dll_directory(base)