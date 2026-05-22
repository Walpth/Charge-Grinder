from PyQt6.QtCore import QObject, pyqtSignal
import threading

class BotEvents(QObject):
    request_pause_ui = pyqtSignal()
    request_stop_ui = pyqtSignal()
    request_lux_hide = pyqtSignal()
    warning_raised = pyqtSignal(str)
    error_raised = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()