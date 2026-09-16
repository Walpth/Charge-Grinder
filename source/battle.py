from source.utils.utils import *
from source.event import event
import source.utils.params as p
from itertools import product


exit_if = ["loading", "Move", "EGObin", "encounterreward", "victory", "defeat", "PackChoice"]

sins = { # bgr values
    "wrath"   : (  0,   0, 254),
    "gloom"   : (239, 197,  26),
    "sloth"   : ( 49, 205, 251),
    "lust"    : (  0, 108, 254),
    "pride"   : (213,  75,   1),
    "gluttony": (  1, 228, 146),
    "envy"    : (222,   1, 150),
}

def defense_skill(gear_start, gear_end):
    offset_x = 131
    offset_y = 142
    offset_x2 = 122
    spacing = 120

    length = gear_end[0] - gear_start[0]
    num_sinners = int(round((length - (offset_x+offset_x2)) / spacing)) + 1

    first_x = gear_start[0] + offset_x
    click_y = gear_start[1] + offset_y

    for i in range(num_sinners):
        x = first_x + i * spacing
        win_moveTo(x, click_y, curve=0.5, n_sub=1, inertia=True)
        win_click()

# HARD MD
comps = [0.71, 0.77, 0.89, 1]
low = {"struggle": (0, 199, 252), "hopeless": (2, 245, 214)}
ego = ["zayin", "teth", "he", "waw"]
best1 = ["FluidSac"]
best2 = [
    "DimensionShredder", "Sunshower", "MagicBullet", "Holiday", "EffervescentCorrosion", "EbonyStem", "Binds", "YaSunyataTadRupam",
    "GardenofThorns", "AEDD", "Lantern", "CavernousWailing", "Capote", "Pursuance", "Regret", "RimeShank", "WishingCairn",
    "ElectricScreaming", "4thMatchFlame", "RedEyesOpen", "ArdorBlossomStar", "BlindObsession", "FluidSac", "HexNail"
]

def get_lowskill():
    image = screenshot(region=(0, 820, 1920, 100))
    boxes = []
    for name in low.keys():
        target_color = low[name]
        mask = create_mask(image, target_color, 20)
        for comp in comps:
            boxes += LocateGray.locate_all(PTH[name], image=mask, region=(0, 820, 1920, 100), threshold=20, comp=comp, conf=0.8)
    coords_x = []
    for box in boxes:
        x, y = gui.center(box)
        if y > 870: # lower skill
            x += int(0.061*x - 93)
        else: # upper skill
            x += int(0.206*x - 224)
        if any(abs(x - px) <= 20 for px in coords_x): continue
        coords_x.append(int(x))
    return sorted(coords_x)

def ego_click(best_ego):
    gui.mouseDown()
    time.sleep(1.5)
    gui.mouseUp()
    image_all = screenshot(region=(0, 200, 1920, 50))
    _, image_best = cv2.threshold(cv2.cvtColor(screenshot(region=(0, 495, 1920, 50)), cv2.COLOR_BGR2GRAY), 100, 255, cv2.THRESH_TOZERO)
    for i, h_comp in product(best_ego, [0.95, 0.98, 1, 1.02, 1.05]):
        box = LocateGray.locate(PTH[i], image=image_best, region=(0, 495, 1920, 50), method=1, h_comp=h_comp, conf=0.6)
        if box:
            res = gui.center(box)
            win_click(res)
            win_click(res)
            break
    else:
        for i in ego:
            res = LocateRGB.locate(PTH[i], image=image_all, region=(0, 200, 1920, 50), method=1, conf=0.8)
            print(i, res)
            if res:
                c0, c1 = gui.center(res)
                win_click(c0, int(c1 + 200))
                win_click(c0, int(c1 + 200))
                break
        else:
            win_click(1850, 1000)
    if not loc.button("winrate", wait=2):
        win_click(1888, 901)
    time.sleep(0.2)


def check_selection(button="winrate_on", st_clicks=3):
    gui.press("p", st_clicks, 0.5)
    time.sleep(0.5)
    wait_while_condition(lambda: not loc.button(button, "winrate", wait=0.5, method=cv2.TM_SQDIFF_NORMED), lambda: gui.press("p"))

def select_ego():
    loc.button("winrate_on", "winrate", wait=1, method=cv2.TM_SQDIFF_NORMED)
    coords_x = get_lowskill()
    if not coords_x: return

    # try using zayin
    for x in coords_x:
        win_moveTo(x, 990)
        ego_click(best1)
    check_selection()
    coords_x = get_lowskill()
    if len(coords_x) < 3:
        # zayin kinda worked
        for x in coords_x: win_click(x, 990)
        return

    for x in coords_x: # zayin didn't work, so let's use something more deadly
        win_click(x, 990, clicks=2)
        time.sleep(0.1)
        ego_click(best2)
    check_selection()
    coords_x = get_lowskill()
    if len(coords_x) < 3:
        # we winrate with this
        for x in coords_x: win_click(x, 990)
        return

    # even that didn't work, so let's go for damage
    check_selection("damage_on", st_clicks=1)
    coords_x = get_lowskill()
    for x in coords_x: win_click(x, 990)


def is_ego():
    threshold=60
    background = screenshot(region=REG["ego_usage"])
    for color in sins.values():
        color = np.array(color).astype(int)
        lower_bound = np.clip(color - threshold, 0, 255)
        upper_bound = np.clip(color + threshold, 0, 255)
        mask = cv2.inRange(background, lower_bound, upper_bound)
        if now.button("ego_usage", image=mask, conf=0.8):
            return background
    return None


def find_skill3(background, known_rgb, threshold=40, min_pixels=10, max_pixels=100, sin="envy"):
    median_rgb = np.median(background, axis=(0, 1)).astype(int)
    blended_rgb = (median_rgb * 0.45 + np.array(known_rgb) * 0.55).astype(int)

    comp = p.WINDOW[2] / 1920

    lower_bound = np.clip(blended_rgb - threshold, 0, 255)
    upper_bound = np.clip(blended_rgb + threshold, 0, 255)
    mask = cv2.inRange(background, lower_bound, upper_bound)

    # collecting clusters (colors that are directly connected)
    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(mask)

    cluster_centers = []

    # some pixel value checks (colors in cluster may be disconnected)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        center = centroids[i]

        if min_pixels*comp <= area <= max_pixels*comp:
            x = int(center[0])
            x1, x2 = round(max(0, x-25*comp)), round(min(background.shape[1], x+25*comp))
            y1, y2 = 0, round(10*comp)

            region_mask = mask[y1:y2, x1:x2]
            similar_pixels = np.count_nonzero(region_mask)

            if 150*comp >= similar_pixels >= 20*comp:
                cluster_centers.append(center)
    # print(sin)
    # print(centroids)
    # print(cluster_centers)

    # merging neightbouring clusters
    merged = []
    while cluster_centers:
        current = cluster_centers.pop()
        group = [c for c in cluster_centers if np.linalg.norm(current - c) <= 50*comp]
        cluster_centers = [c for c in cluster_centers if np.linalg.norm(current - c) > 50*comp]
        merged.append(np.mean([current] + group, axis=0))

    # filter by color patterns
    filtered = []
    while merged:
        center = merged.pop()
        x = int(center[0])
        x1, x2 = round(max(0, x-30*comp)), round(min(background.shape[1], x+30*comp))
        y1, y2 = 0, round(min(mask.shape[0], 10*comp))

        region_mask = mask[y1:y2, x1:x2]
        pattern = np.zeros((y2-y1, x2-x1), dtype=np.uint8)
        pattern = np.maximum(pattern, region_mask)
        try:
            if pattern.shape[1] < 33*comp : raise gui.ImageNotFoundException
            LocateGray.try_locate(PTH[str(sin)], pattern, region=(0, 0, pattern.shape[1], round(10*comp)), conf=0.74, method=cv2.TM_CCORR_NORMED)
            filtered.append(int(center[0]*1920/p.WINDOW[2]))
        except gui.ImageNotFoundException:
            # print(sin)
            # cv2.imwrite(f"{time.time()}{sin}.png", pattern)
            continue

    return filtered

def select_team():
    time.sleep(1)

    affinity = p.TEAM[0].lower()
    idx = p.NAME_ORDER
    if not p.DUPLICATES and LocateGray.check(PTH[f"{affinity}_current"], region=REG["current_team"], conf=0.92, method=cv2.TM_SQDIFF_NORMED, wait=False):
        return

    win_moveTo(196, 480)
    for i in range(3):
        if now_rgb.button("arrow", conf=0.7):
            gui.scroll(20)
            time.sleep(0.1)
        else:
            time.sleep(1)
            break
    else:
        time.sleep(1)

    for i in range(7):
        coords = [gui.center(box) for box in LocateGray.locate_all(PTH[f"{affinity}_team"], region=REG["teams"], threshold=15, conf=0.85)]
        print(coords)
        sorted(coords, key=lambda coord: coord[1])

        if len(coords) > idx:
            win_click(coords[idx])
            break
        elif i != 6:
            idx -= len(coords)
            gui.scroll(-10)
            time.sleep(0.3)
    else:
        logging.info("Team selecton failed!")
        return
    logging.info(f"Selected {p.TEAM[0]}")
    time.sleep(1)

def select(sinners):
    selected = [gui.center(box) for box in LocateGray.locate_all(PTH["selected"])]
    backup = [gui.center(box) for box in LocateGray.locate_all(PTH["backup"])]
    correct = 0
    correct_back = 0
    to_click = []
    regions = [SINNERS[name] for name in sinners]
    death_offset = 0
    for i, region in enumerate(regions):
        if any(
            region[0] < point[0] < region[0]+region[2] and
            region[1] < point[1] < region[1]+region[3]
            for point in selected) and i < 7 + death_offset:
            correct += 1
            continue
        if i > 5 + death_offset and any(
            region[0] < point[0] < region[0]+region[2] and
            region[1] < point[1] < region[1]+region[3]
            for point in backup):
            correct_back += 1
            continue
        if is_grayscale(screenshot(region=region)): # dead
            death_offset += 1
            continue
        to_click.append(gui.center(region))
    
    if death_offset == len(p.SELECTED):
        for _ in range(2):
            gui.press("esc")
            time.sleep(0.5)
        chain_actions(click, [
            Action("forfeit"),
            Action("ConfirmInvert", ver="connecting"),
        ])
        connection()
        return False
    
    if len(selected) > correct or len(backup) > correct_back:
        ClickAction((1713, 712), ver="Confirm_alt").execute(click)
        time.sleep(0.21)
        click.button("Confirm_alt")
        time.sleep(0.5)
        for region in regions:
            win_click(gui.center(region))
            time.sleep(0.1)
    elif to_click:
        for i in to_click:
            win_click(i)
            time.sleep(0.1)

    input_with_fallback(
        "space",
        lambda: win_click(1728, 884, tsize=(200,  50)),
        lambda: loc.button("loading", wait=5)
    )
    loading_halt()
    return True

def chain(gear_start, gear_end, background, is_defense=False):
    # Finding skill3 positions
    x, y = gear_start
    length = gear_end[0] - gear_start[0]
    skill_num = int(round((length - 140)/115))
    skill3 = []
    for sin in sins.keys():
        skill3 += find_skill3(background, sins[sin], sin=sin)
    moves = [False]*skill_num
    for coord in skill3:
        bin_index = int(min(max((coord - 14 + 80*(2*((coord + gear_start[0] + 100)/1920) - 1)) // 115, 0), skill_num - 1))
        moves[bin_index] = True
    # print(gear_start)
    # print(gear_end)
    # print(length)
    # print(moves)
    # Chaining

    if p.HOS_MODE is False:
        win_moveTo(gear_start)
        gui.mouseDown()
        x += 75
        y -= 46
        for i in range(skill_num):
            if moves[i]:
                win_moveTo(x + 68, y + 190, duration=0.13, tsize=(40, 40), curve=0.5, n_sub=1, inertia=True)
            else:
                win_moveTo(x + 68, y + 80, duration=0.13, tsize=(40, 40), curve=0.5, n_sub=1, inertia=True)
            x += 115
        win_moveTo(x + 91, y + 131, duration=0.13, tsize=(25, 25), curve=0.5, n_sub=1, inertia=True)
        gui.mouseUp()

    else:
        if is_defense:
            win_moveTo(gear_start)
            gui.mouseDown()
            x += 75
            y += 46
            for i in range(skill_num):
                win_moveTo(x + 68, y + 80, duration=0.13, tsize=(40, 40), curve=0.5, n_sub=1, inertia=True)
                x += 115
            win_moveTo(x + 91, y, duration=0.13, tsize=(25, 25), curve=0.5, n_sub=1, inertia=True)
            gui.mouseUp()
        else:
            win_moveTo(gear_start)
            gui.mouseDown()
            x += 75
            y -= 46
            for i in range(skill_num):
                if moves[i]:
                    win_moveTo(x + 68, y + 80, duration=0.13, tsize=(40, 40), curve=0.5, n_sub=1, inertia=True)
                else:
                    win_moveTo(x + 68, y + 190, duration=0.13, tsize=(40, 40), curve=0.5, n_sub=1, inertia=True)
                x += 115
            win_moveTo(x + 91, y + 131, duration=0.13, tsize=(25, 25), curve=0.5, n_sub=1, inertia=True)
            gui.mouseUp()



def fight(lux=False):
    is_tobattle = now.button("TOBATTLE")
    is_battle   = now_rgb.button("winrate") or now.button("pause")
    if not is_tobattle and not is_battle: return False
    print("battle check")
    if is_tobattle:
        if lux:
            win_moveTo(880, 880)
            select_team()
        else:
            x, y = win_get_position()
            if x < 1560 and y < 820:
                win_moveTo(random.randint(1560, 1730), random.randint(250, 620))
                time.sleep(0.1)

        can_select = select(p.SELECTED)
        if not can_select:
            return False

        # for lux with 6 sinners max
        if lux and now.button("TOBATTLE"):
            select(p.SELECTED[:6])

    print("Entered Battle")
    last_error = 0
    attempts = 0
    defence_turns = 0
    max_defense = 0
    if p.HOS_MODE and len(p.SELECTED) - p.DEAD != 1:
        max_defense = min(((len(p.SELECTED) - p.DEAD + int(p.DEAD == 0)) // 2), 5)

    while True:
        ck = False
        if loc.button("winrate", wait=1):
            time.sleep(0.1)
            ck = True
            is_focused = True
            try:
                if p.HOS_MODE is False:
                    gear_start = gui.center(LocateEdges.try_locate(PTH["gear"], region=(0, 761, 900, 179), conf=0.7))
                    gear_end = gui.center(LocateEdges.try_locate(PTH["gear2"], region=(350, 730, 1570, 232), conf=0.7))
                    is_focused = False
                    # cv2.imwrite(f"data/battle_skills/{time.time()}.png", screenshot(region=(round(gear_start[0] + 100), 775, round(gear_end[0] - gear_start[0] - 200), 150)))
                    if lux or p.WINRATE: raise gui.ImageNotFoundException
                    background = screenshot(region=(round(gear_start[0] + 100), 775, round(gear_end[0] - gear_start[0] - 200), 10))
                    # cv2.imwrite(f"data/battle_state/{time.time()}.png", screenshot(region=(round(gear_start[0] + 100 - 55), 775, round(gear_end[0] - gear_start[0] - 200 + 125), 305)))
                    chain(gear_start, gear_end, background)

                else:
                    if defence_turns < max_defense:
                        print(f"use defense!!!")
                        gear_start = gui.center(LocateEdges.try_locate(PTH["gear"], region=(0, 761, 900, 179), conf=0.7))
                        gear_end = gui.center(LocateEdges.try_locate(PTH["gear2"], region=(350, 730, 1570, 232), conf=0.7))
                        # cv2.imwrite(f"data/battle_state/{time.time()}.png", screenshot(region=(round(gear_start[0] + 100 - 55), 775, round(gear_end[0] - gear_start[0] - 200 + 125), 305)))
                        defense_skill(gear_start, gear_end)
                        is_focused = False
                        # cv2.imwrite(f"data/battle_skills/{time.time()}.png", screenshot(region=(round(gear_start[0] + 100), 775, round(gear_end[0] - gear_start[0] - 200), 150)))
                        background = screenshot(region=(round(gear_start[0] + 100), 775, round(gear_end[0] - gear_start[0] - 200), 10))
                        chain(gear_start, gear_end, background, is_defense=True)
                        defence_turns += 1
                    else:
                        gear_start = gui.center(LocateEdges.try_locate(PTH["gear"], region=(0, 761, 900, 179), conf=0.7))
                        gear_end = gui.center(LocateEdges.try_locate(PTH["gear2"], region=(350, 730, 1570, 232), conf=0.7))
                        is_focused = False
                        # cv2.imwrite(f"data/battle_skills/{time.time()}.png", screenshot(region=(round(gear_start[0] + 100), 775, round(gear_end[0] - gear_start[0] - 200), 150)))
                        background = screenshot(region=(round(gear_start[0] + 100), 775, round(gear_end[0] - gear_start[0] - 200), 10))
                        # cv2.imwrite(f"data/battle_state/{time.time()}.png", screenshot(region=(round(gear_start[0] + 100 - 55), 775, round(gear_end[0] - gear_start[0] - 200 + 125), 305)))
                        chain(gear_start, gear_end, background)

                # success check
                time.sleep(1)
                if now.button("winrate"):
                    gui.press("p", 1, 0.1)
                    time.sleep(0.5)
                    gui.press("enter", 1, 0.1)
                    time.sleep(1)
            except gui.ImageNotFoundException:
                gui.press("p", 1, 0.1)
                time.sleep(0.5)

                if is_focused and not loc.button("winrate_on", "winrate", wait=2, method=cv2.TM_SQDIFF_NORMED):
                    win_click(1385, 930)

                # cv2.imwrite(f"data/battle_struggle/{time.time()}.png", screenshot(region=(0, 820, 1920, 100)))

                if not lux and p.HARD: select_ego()
                gui.press("enter", 1, 0.1)
                time.sleep(1)

        if now_rgb.button("event"):
            ck = True
            event()

        if now.button("ego_warning"): # skip corrosion
            ck = True
            gui.mouseDown()
            wait_while_condition(lambda: loc.button("ego_warning", wait=1), interval=0)
            gui.mouseUp()

        if (ego_image := is_ego()) is not None: # skip EGO animation
            ck = True
            gui.mouseDown()
            wait_while_condition(lambda: LocateRGB.check(ego_image, region=REG["ego_usage"], wait=1), interval=0)
            gui.mouseUp()

        if now.button("RetryStage"):
            attempts += 1
            if attempts >= 3:
                logging.info("Got stuck in hard battle")
                if not p.RESTART:
                    wait_while_condition(lambda: not now.button("Confirm_retry", method=cv2.TM_SQDIFF_NORMED), lambda: win_click(1200, 400), interval=1, timer=3)
                    gui.press("space")
                    loading_halt()
                    logging.info("Run Aborted: Hard battle could not continue.")
                    err = StopIteration("Dante, we failed... If you want to end run here, enable 'End stuck runs'")
                    if p.ALTF4: close_limbus(error=err)
                    raise err
                else:
                    wait_while_condition(lambda: not now.button("Confirm_retry", method=cv2.TM_SQDIFF_NORMED), lambda: win_click(1200, 670), interval=1, timer=3)
                    gui.press("space")
                    loading_halt()
                    print("Battle is over")
                    logging.info("Battle is over")
                    return True
            else:
                wait_while_condition(lambda: not now.button("Confirm_retry", method=cv2.TM_SQDIFF_NORMED), lambda: win_click(1200, 530), interval=1, timer=3)
                gui.press("space")
                loading_halt()
                logging.info(f"Re-attempting the battle (attempt {attempts + 1})")

        for i in exit_if:
            if now.button(i):
                if i == "loading": loading_halt()
                print("Battle is over")
                logging.info("Battle is over")
                return True

        # for i in range(3):
        #     if now_rgb.button(f"end_{i}", "skip_yap"):
        #         gui.press("space")

        if p.LIMBUS_NAME not in (win := gui.getActiveWindowTitle()):
            ck = True
            pause(win)

        if now.button("pause"):
            ck = True
            time.sleep(1)
        else:
            time.sleep(0.2)

        # stuck check
        if ck == False:
            if last_error != 0:
                if time.time() - last_error > 50:
                    raise RuntimeError('Stuck in battle')
            else:
                last_error = time.time()
        else:
            last_error = 0
