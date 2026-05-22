import json
import logging
import traceback

from PyQt6.QtCore import QObject, pyqtSignal, QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from source_app.data import BotConfig, VERSION
from Bot import execute_me


class VersionChecker(QObject):
    updateAvailable = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self._on_finished)

    def check(self):
        req = QNetworkRequest(QUrl("https://api.github.com/repos/AlexWalp/Mirror-Dungeon-Bot/releases/latest"))
        req.setRawHeader(b"User-Agent", b"MirrorDungeonBot-VersionChecker/1.0")
        req.setRawHeader(b"Accept", b"application/vnd.github.v3+json")
        self.manager.get(req)

    def _on_finished(self, reply):
        reply.deleteLater()

        if reply.error() != QNetworkReply.NetworkError.NoError:
            status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            err_str = reply.errorString()
            print("Network error:", err_str, "status:", status_code)
            self.updateAvailable.emit(True)
            return

        data = bytes(reply.readAll()).decode('utf-8')
        try:
            j = json.loads(data)
            tag = j.get("tag_name", "").lstrip("vV")
            is_up_to_date = self._compare_versions(tag, VERSION)
        except Exception as e:
            print("Parse error:", e)
            is_up_to_date = True
        self.updateAvailable.emit(is_up_to_date)

    def _compare_versions(self, latest, current):
        try:
            a = [int(x) for x in latest.split(".") if x.isdigit()]
            b = [int(x) for x in current.split(".") if x.isdigit()]
            n = max(len(a), len(b))
            a += [0] * (n - len(a)); b += [0] * (n - len(b))
            return a <= b
        except Exception:
            return True


class BotWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, config: BotConfig, events):
        super().__init__()
        self.config = config
        self.events = events

    @pyqtSlot()
    def run(self):
        try:
            execute_me(self.config, self.events)
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(tb)
            self.events.error_raised.emit(str(e))
        finally:
            self.finished.emit()