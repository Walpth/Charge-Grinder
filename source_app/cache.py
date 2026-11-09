from source_app.utils import *
from source.teams import HARD, TEAMS
from source.utils.utils import amplify
from source.utils.paths import PTH
from cv2 import imread
from source_app.params import CACHE


class CacheWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, teams, settings, hard):
        super().__init__()
        names = self.get_gifts(teams, settings, hard)
        self.paths = [(PTH[name], name) for name in names]

    def get_gifts(self, teams, settings, hard):
        team_list = HARD if hard else TEAMS
        affinities = {x for team in teams for x in teams[team]["affinity"]}
        gifts = {item for i in affinities for item in list(team_list.values())[i]["all"]}
        keywordless = list(settings['keywordless'].keys())
        if settings['infinity']:
            keywordless += ["lunarmemory", "slashmemory", "piercememory", "bluntmemory"]
        if any(settings['hos_mode'].values()):
            keywordless += ["spiderweb"]
        gifts |= set(keywordless)
        return list(gifts)

    def run(self):
        for (read, write) in self.paths:
            image = imread(read)
            CACHE[write] = amplify(image)
        self.finished.emit()