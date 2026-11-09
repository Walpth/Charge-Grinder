from source.utils.utils import *
import source.utils.params as p


mounting_trials = [
    "DefenseSkillUp",
    "DefenseLevelUp",
    "Resilient",
    "Growth",
    "BodyUp",
    "Keen",
    "OffenseLevelUp",
    "TakeLessDamage",
    "ClashPower",
    "FinalPower",
    "BasePower",
    "Brutality",
    "Headstrong"
]


def far_from_owned(coord, owned_x):
    '''
    Checks whether the ego gift is owned

    Args:
        coord: ego gift coordinates (x, y)
        owned_x: x coordinates of located "owned" icons
    '''
    return all(abs(coord[0] - ox) >= 200 for ox in owned_x)


def find_ego_affinity(owned_x, image):
    '''
    Finds the first affinity EGO gift with the highest tier

    Args:
        owned_x: x coordinates of located "owned" icons
        affinity EGO gifts with those icons are excluded
        image: image with ego gifts that can be adjusted
    Returns:
        tuple (lvl, aff), where lvl is ego gift level and 
        aff is its coordinates (x, y) 
    '''
    affinity = []
    for aff in p.GIFTS:
        affinity += list(filter(
            lambda coord: far_from_owned(coord, owned_x),
            [gui.center(box) for box in LocateRGB.locate_all(PTH[aff["checks"][0]], image=image, region=REG["EGO"])]
        ))
    comp = p.WINDOW[2] / 1920
    return next((
        (lvl, aff)
        for lvl in range(4, 0, -1)
        for aff in affinity
        if LocateRGB.check(
            PTH[f"tier{lvl}"],
            image=image[0:int(42*comp), int((aff[0] - 106)*comp):int((aff[0] - 106 + 66)*comp)],
            wait=False
    )), None)


def get_gift(image, owned_x):
    '''
    Locates EGO gift tiers, affinity, level and their coordinates, then selects the best

    Args:
        image: image with EGO gifts that can be modified
        owned_x: x coordinates of "owned" icons

    Returns:
        image: image with the selected EGO gift replaced with a black rectangle
        (removed from further analysis in case we are selecting multiple gifts)
    '''
    if p.GIFTS[0]["sin"] or not LocateRGB.check(PTH[p.GIFTS[0]["checks"][0]], image=image, region=REG["EGO"], wait=False):
        for gift in list(p.KEYWORDLESS.keys()) + [buy for aff in p.GIFTS if aff["sin"] for buy in aff["buy"]]:
            if (coord := LocateRGB.locate(PTH[str(gift)], image=image, region=REG["EGO"], conf=0.84, comp=0.94)) \
            and far_from_owned(gui.center(coord), owned_x):
                point = gui.center(coord)
                win_click(point, tsize=(150, 160))
                return rectangle(image, (int(point[0]-100), 0), (int(point[0]+100), 110), (0, 0, 0), -1)

    ego_aff = find_ego_affinity(owned_x, image) # (lvl, coord)

    for lvl in range(4, 0, -1):
        if ego_aff and lvl == ego_aff[0]:
            point = ego_aff[1]
            win_click(point, tsize=(150, 230))
            return rectangle(image, (int(point[0]-100), 0), (int(point[0]+100), 110), (0, 0, 0), -1)
        elif boxes := LocateRGB.locate_all(PTH[f"tier{lvl}"], image=image, region=REG["EGO"], method=cv2.TM_SQDIFF_NORMED, threshold=30, conf=0.85):
            for box in boxes:
                point = gui.center(box)
                if far_from_owned(point, owned_x):
                    break
            win_click(point, tsize=(150, 130))
            return rectangle(image, (int(point[0]-100), 0), (int(point[0]+100), 110), (0, 0, 0), -1)
    return image


def find_trial(trials_image):
    '''
    Locates the first prioritized mounting trial and returns its coordinates

    Args:
        trials_image: image with trials that can be modified

    Returns:
        res: list of matching bounding boxes
    '''
    for name in mounting_trials:
        for c in [1, 1.05]:
            res = LocateRGB.locate_all(PTH[f"trial_{name}"], trials_image, method=cv2.TM_SQDIFF_NORMED, comp=c, conf=0.87, threshold=100)
            if res:
                print(name)
                return res
    return []


def get_trial(image, trials_image):
    '''
    Selects the best mounting trial

    Args:
        image: image with EGO gifts that can be modified
        trials_image: image with trials that can be modified

    Returns:
        image: image with the selected EGO gift replaced with a black rectangle
        (removed from further analysis in case we are selecting multiple gifts)
        trials_image: image with the selected trials replaced with a black rectangle
    '''
    res = find_trial(trials_image)
    print(res)
    if len(res) == 1:
        point = gui.center(res[0])
        win_click(point[0], 600, tsize=(150, 170))
        return rectangle(image, (int(point[0]-140), 0), (int(point[0]+140), 110), (0, 0, 0), -1), \
               rectangle(trials_image, (int(point[0]-140), 0), (int(point[0]+140), 52), (0, 0, 0), -1)
    elif len(res) > 1:
        points = [gui.center(res[i]) for i in range(len(res))]
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        mask = rectangle(mask, (int(points[0][0]-140), 0), (int(points[0][0]+140), 110), 255, -1)
        mask = rectangle(mask, (int(points[1][0]-140), 0), (int(points[1][0]+140), 110), 255, -1)
        return cv2.bitwise_and(image, image, mask=mask), None
    else:
        return image, None


def grab_EGO():
    '''
    Selects EGO gift(s) on the Ego Gift Selection screen
    retuns whether or not the EGO gift(s) is/are selected
    '''
    if not now.button("EGObin"): return False
    now_click.button("Cancel")
    time.sleep(0.8)
    print("grab ego check")
    owned_x = [p[0] + p[2] for p in LocateRGB.locate_all(PTH["Owned"], region=REG["Owned"])]
    image = screenshot(region=REG["EGO"])
    # cv2.imwrite(f"data/grab/{time.time()}.png", image)

    cycle = 1
    trials = None
    if p.HARD and now.button("trials"): 
        cycle = 2
        if p.EXTREME:
            trials = screenshot(region=REG["buffs"])
            # cv2.imwrite(f"data/trials/{time.time()}.png", trials)
    elif p.BUFF[9] or p.BUFF[5]:
        for i in [2, 3]:
            if now.button(f"select{i}", "selectCount"):
                cycle = i
                break

    for _ in range(cycle):
        if trials is not None:
            image, trials = get_trial(image, trials)
            time.sleep(0.1)
            # cv2.imwrite(f"{time.time()}.png", image)
            # if trials is not None:
            #     cv2.imwrite(f"{time.time()}.png", trials)
        if trials is None:
            image = get_gift(image, owned_x)
            time.sleep(0.1)

    wait_while_condition(lambda: now.button("EGObin"), lambda: gui.press("space"), interval=0.5, timer=2)
    return True


def get_card(card):
    '''
    Clicks the selected card

    Args:
        card: (x, y) coordinates
    '''
    chain_actions(click, [
        Action(card, "Card", ver="rewardCount!"),
        Action("Confirm.1", ver="connecting")
    ])

def grab_card():
    '''
    Selects the Reward Card according to specified priority
    Returns whether the card was selected or not
    '''
    if not now.button("encounterreward"): return False
    print("grab card check")

    win_moveTo(1000, 900)
    now_click.button("Cancel") # if was misclicked
    time.sleep(1.4)
    # cv2.imwrite(f"data/cards/{time.time()}.png", screenshot(region=REG["Card"]))
    for i in p.CARD:
        if now.button(f"card{i}", "Card"):
            get_card(f"card{i}")
            wait_while_condition(
                condition=lambda: now.button("encounterreward"), 
                action=lambda: win_click(1255, 924) if now.button("Confirm") else None,
                interval=0.1
            )
            return True
    else:
        return False
    

def confirm():
    '''Function to confirm EGO gift pop-ups'''
    if not now.button("Confirm"): return False
    print("confirming gift")
    gui.press("space")
    time.sleep(0.3)
    now_click.button("Confirm")
    return True


def get_adversity():
    if not now.button("adversity"): return False
    x_coords = [box[0] for box in LocateRGB.locate_all(PTH["projection"], region=REG["projection"], threshold=100)]
    sorted(x_coords)
    for x in x_coords:
        ClickAction((x + 90, 550), ver="selectCount!").execute(click)
    time.sleep(0.3)
    win_click(1725, 1000)
    wait_while_condition(lambda: now.button("adversity"), interval=0.2)
    return True
