import datetime, csv, sys, os, statistics


class Floor:
    def __init__(self, st_time):
        self.st_time = st_time
        self.time = None

        self.pack = None
        self.battles = {
            "Normal": [],
            "Focused": [],
            "Risky": [],
            "Miniboss": [],
            "Boss": [],
        }
    
    def add_pack(self, pack):
        self.pack = pack

    def add_event(self, time, event):
        self.battles[event].append(time)
    
    def end(self, end_time):
        self.time = end_time - self.st_time


class Run:
    def __init__(self, st_time, team):
        self.st_time = st_time
        self.time = None

        self.team = team
        self.diff = None
        self.state = 0
        self.floors = {}
        self.event = {"name": None, "st_time": None}

    def check_order(self, floor):
        if floor == self.state + 1:
            self.state = floor
        else:
            raise ValueError

    def add_floor(self, number, st_time):
        if self.state != 0:
            self.floors[self.state].end(st_time)
        self.check_order(number)
        self.floors[self.state] = Floor(st_time)

    def add_pack(self, pack):
        self.floors[self.state].add_pack(pack)

    def add_diff(self, diff):
        self.diff = diff

    def add_event(self, st_time, event):
        self.event["name"] = event
        self.event["st_time"] = st_time

    def end_event(self, end_time):
        if self.event["name"] == None or self.event["st_time"] == None or self.state == 0:
            raise ValueError
        time = end_time - self.event["st_time"]
        self.floors[self.state].add_event(time, self.event["name"])

    def end(self, end_time):
        self.time = end_time - self.st_time


def get_next_word(text, search_word):
    words = text.split()
    try:
        index = words.index(search_word)
        if index + 1 < len(words):
            return words[index + 1]
        return None
    except ValueError:
        return None

def unix_time(timestamp_str, shift=0):
    dt_str = timestamp_str.split(',')[0]
    dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp()) - shift




KEYWORDS = ["fight", "Battle is over", "Floor", "Pack:", "Team:", "Difficulty:", "Run Completed", "paused", "resumed"]

def process_log_file(file_path):
    # Can raise FileNotFoundError
    useful_lines = []
    with open(file_path, 'r') as file:
        for line in file:
            for word in KEYWORDS:
                if word in line:
                    useful_lines.append(line[:-1])
                    break
    return useful_lines


def build_data(lines):
    data = []
    run = None

    shift = 0
    st_shift = None

    reset = True

    for line in lines:
        if reset and "Team:" not in line:
            continue

        try:
            if "fight" in line and run:
                run.add_event(unix_time(line, shift), get_next_word(line, "Entering"))
            elif "Battle is over" in line and run:
                run.end_event(unix_time(line, shift))
            elif "Floor" in line and run:
                run.add_floor(int(get_next_word(line, "Floor")), unix_time(line, shift))
            elif "Pack:" in line and run:
                run.add_pack(get_next_word(line, "Pack:"))
            elif "Run Completed" in line:
                if run and ((run.diff != "EXTREME" and run.state == 5) or run.diff == "EXTREME"):
                    run.floors[run.state].end(unix_time(line, shift))
                    run.end(unix_time(line, shift))
                    data.append(run)
                    run = None
            elif "Team:" in line:
                reset = False
                shift = 0
                run = Run(unix_time(line, shift), get_next_word(line, "Team:"))
            elif "Difficulty:" in line and run:
                run.add_diff(get_next_word(line, "Difficulty:"))
            elif "paused" in line:
                st_shift = unix_time(line, shift)
            elif "resumed" in line:
                shift += unix_time(line, shift) - st_shift
        except ValueError:
            reset = True

    return data



TEAMS = ["BURN", "BLEED", "TREMOR", "RUPTURE", "SINKING", "POISE", "CHARGE", "SLASH", "PIERCE", "BLUNT"]
MODES = ["NORMAL", "HARD", "EXTREME"]

def format_time(total_seconds):
    if total_seconds is None:
        return "no data"
    total_seconds = round(total_seconds)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{int(minutes):02d}:{int(seconds):02d}"

def export_to_csv(data, filename):
    modes_data = {}
    for run in data:
        if not run.team or not run.diff:
            continue
        if run.diff not in modes_data:
            modes_data[run.diff] = {}
        if run.team not in modes_data[run.diff]:
            modes_data[run.diff][run.team] = []
        modes_data[run.diff][run.team].append(run)
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        
        for mode in MODES:
            if mode not in modes_data:
                continue
            
            writer.writerow([mode])
            writer.writerow([])
            
            for team in TEAMS:
                if team not in modes_data[mode]:
                    continue
                runs = modes_data[mode][team]
            
                writer.writerow([team])
                writer.writerow([])
                
                total_times = []
                for run in runs:
                    if run.time is not None:
                        total_times.append(run.time)
                if total_times:
                    avg_total = sum(total_times) / len(total_times)
                    med_total = statistics.median(total_times)
                    avg_total_str = format_time(avg_total)
                    med_total_str = format_time(med_total)
                else:
                    avg_total_str = "no data"
                    med_total_str = "no data"
                
                writer.writerow(["Avg Time", "Median Time", "Count"])
                writer.writerow([avg_total_str, med_total_str, len(runs)])
                writer.writerow([])
                
                battle_types = ["Normal", "Focused", "Risky", "Miniboss", "Boss"]
                writer.writerow(["Fights"] + battle_types + ["Total"])
                
                for floor_num in range(1, 6 + 10*(mode == "EXTREME")):
                    battle_times = {bt: [] for bt in battle_types}
                    floor_total_times = []
                    
                    for run in runs:
                        if floor_num in run.floors:
                            floor = run.floors[floor_num]
                            if floor.time is not None:
                                floor_total_times.append(floor.time)
                            for bt in battle_types:
                                battle_list = floor.battles.get(bt, [])
                                if battle_list:
                                    battle_times[bt].extend(battle_list)
                    
                    if floor_total_times:
                        avg_floor_total = sum(floor_total_times) / len(floor_total_times)
                        avg_floor_total_str = format_time(avg_floor_total)
                    else:
                        avg_floor_total_str = "no data"
                    
                    row = [f"Floor{floor_num}"]
                    for bt in battle_types:
                        times = battle_times[bt]
                        if times:
                            avg_bt = sum(times) / len(times)
                            row.append(format_time(avg_bt))
                        else:
                            row.append("no data")
                    row.append(avg_floor_total_str)
                    writer.writerow(row)
                
                writer.writerow([])

                for floor_num in range(1, 6 + 10 * (mode == "EXTREME")):
                    pack_data = {}

                    for run in runs:
                        if floor_num in run.floors:
                            floor = run.floors[floor_num]
                            if floor.pack is not None and floor.time is not None:
                                pack_name = floor.pack
                                pack_data.setdefault(pack_name, []).append(floor.time)

                    if pack_data:
                        pack_avg = {pack: sum(times)/len(times) for pack, times in pack_data.items()}
                        pack_med = {pack: statistics.median(times) for pack, times in pack_data.items()}
                        sorted_packs = sorted(pack_avg.keys(), key=lambda x: pack_avg[x])

                        writer.writerow([f"Floor {floor_num} packs"] + sorted_packs)
                        writer.writerow(["Avg Time"] + [format_time(pack_avg[pack]) for pack in sorted_packs])
                        writer.writerow(["Median Time"] + [format_time(pack_med[pack]) for pack in sorted_packs])
                        writer.writerow(["Count"] + [len(pack_data[pack]) for pack in sorted_packs])
                    else:
                        writer.writerow([f"Floor {floor_num} packs"])
                        writer.writerow(["Avg Time"])
                        writer.writerow(["Median Time"])
                        writer.writerow(["Count"])
                
                writer.writerow([])


def log_to_csv():
    appimage_path = os.environ.get("APPIMAGE")
    if appimage_path:
        base_path = os.path.dirname(appimage_path)    
    elif getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    lines = process_log_file(f"{base_path}/game.log")
    data = build_data(lines)
    export_to_csv(data, f"{base_path}/game.csv")


# print(get_next_word("2025-07-06 18:52:35,809 - INFO - Team: BLEED", "Team:"))