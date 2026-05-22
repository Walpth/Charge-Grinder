import time

import cv2
import numpy as np

import source.engine as eg
from source.game_states.main import wait_while_condition
from source.data import UIDatabase, TeamConfig
from source_app.data.bot_config import GameMode


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


def find_ego_affinity(ctrl: eg.InputController, ui: UIDatabase, owned_x, image, team: TeamConfig):
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
    for aff in team.gifts:
        affinity += list(filter(
            lambda coord: far_from_owned(coord, owned_x),
            [target.center for target in ui.GrabMenu.ego_R.locate_all_in(image, aff["checks"][0])]
        ))
    return next((
        (lvl, aff)
        for lvl in range(4, 0, -1)
        for aff in affinity
        if ui.GrabMenu.ego_tier_R.check_in(eg.crop(ctrl, image, region=(aff[0]-106, 0, 66, 42)), f"tier{lvl}")
    ), None)


def get_gift(ctrl: eg.InputController, ui: UIDatabase, image, owned_x, team: TeamConfig):
    '''
    Locates EGO gift tiers, affinity, level and their coordinates, then selects the best

    Args:
        image: image with EGO gifts that can be modified
        owned_x: x coordinates of "owned" icons

    Returns:
        image: image with the selected EGO gift replaced with a black rectangle
        (removed from further analysis in case we are selecting multiple gifts)
    '''
    if team.gifts[0]["sin"] or not ui.GrabMenu.ego_R.check_in(image, team.gifts[0]["checks"][0]):
        for gift in list(team.keywordless_gifts.keys()) + [buy for aff in team.gifts if aff["sin"] for buy in aff["buy"]]:
            if (target := ui.GrabMenu.ego_R.transform(eg.resize, {"scale_factors": (0.94, 0.94)}).locate_in(image, str(gift))) \
            and far_from_owned(target.center, owned_x):
                ctrl.click(target.center)
                return eg.draw_rect(image, region=(int(target.center[0]-100), 0, 200, 110), comp=ctrl.comp)

    ego_aff = find_ego_affinity(ctrl, ui, owned_x, image, team) # (lvl, coord)

    for lvl in range(4, 0, -1):
        if ego_aff and lvl == ego_aff[0]:
            coord = ego_aff[1]
            ctrl.click(coord)
            return eg.draw_rect(image, region=(int(coord[0]-100), 0, 200, 110), comp=ctrl.comp)
        elif targets := ui.GrabMenu.ego_tier_R.locate_all_in(image, f"tier{lvl}"):
            for target in targets:
                coord = target.center
                if far_from_owned(coord, owned_x):
                    break
            ctrl.click(coord)
            return eg.draw_rect(image, region=(int(coord[0]-100), 0, 200, 110), comp=ctrl.comp)


def find_trial(ui: UIDatabase, trials_image):
    '''
    Locates the first prioritized mounting trial and returns its coordinates

    Args:
        trials_image: image with trials that can be modified

    Returns:
        res: list of matching bounding boxes
    '''
    for name in mounting_trials:
        for c in [1, 1.05]:
            targets = ui.GrabMenu.ego_tier_R.transform(eg.resize, {"scale_factors": (c, c)}).locate_all_in(trials_image, f"trial_{name}")
            if targets:
                print(name)
                return targets
    return []


def get_trial(ctrl: eg.InputController, ui: UIDatabase, image, trials_image):
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
    targets = find_trial(ui, trials_image)
    if len(targets) == 1:
        coord = targets[0].center
        ctrl.click(coord[0], 600)
        return eg.draw_rect(image, region=(int(coord[0]-140), 0, 280, 110)), \
               eg.draw_rect(trials_image, region=(int(coord[0]-140), 0, 280, 52))
    elif len(targets) > 1:
        coords = [target.center for target in targets]
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        mask = eg.draw_rect(mask, (int(coords[0][0]-140), 0, 280, 110), 255, -1)
        mask = eg.draw_rect(mask, (int(coords[1][0]-140), 0, 280, 110), 255, -1)
        return cv2.bitwise_and(image, image, mask=mask), None
    else:
        return image, None


def grab_EGO(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    '''
    Selects EGO gift(s) on the Ego Gift Selection screen
    retuns whether or not the EGO gift(s) is/are selected
    '''
    if not ui.GrabMenu.ego_bin.check(): return False
    time.sleep(0.8)

    owned_x = [t.box[0] + t.box[2] for t in ui.GrabMenu.owned.locate_all()]
    image = ui.GrabMenu.ego_R.screenshot()

    cycle = 1
    trials = None
    if team.difficulty > GameMode.NORMAL and ui.GrabMenu.trials.check(): 
        cycle = 2
        if team.difficulty == GameMode.EXTREME:
            trials = ui.GrabMenu.buffs_R.screenshot()
    elif team.graces[9]:
        for i in [2, 3]:
            if ui.GrabMenu.select_count_R.check(f"select{i}"):
                cycle = i
                break

    for _ in range(cycle):
        if trials is not None:
            image, trials = get_trial(ctrl, ui, image, trials)
            time.sleep(0.1)
        if trials is None:
            image = get_gift(ctrl, ui, image, owned_x, team)
            time.sleep(0.1)

    try:
        for _ in range(cycle):
            ui.point.click(coords=(1687, 870), verify=ui.GrabMenu.confirm_ego)
    except RuntimeError:
        ctrl.press("enter", 2, 1)
        time.sleep(1)
    return True


def get_card(ui: UIDatabase, card):
    '''
    Clicks the selected card

    Args:
        card: (x, y) coordinates
    '''
    try: 
        ui.GrabMenu.card_R.locate(card).click(verify=ui.GrabMenu.reward_count_R)
        ui.GrabMenu.confirm_card.locate().click(verify=ui.UtilsMenu.connecting)
    except RuntimeError:
        pass

def grab_card(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    '''
    Selects the Reward Card according to specified priority
    Returns whether the card was selected or not
    '''
    if not ui.GrabMenu.encounter_reward.check(): return False

    ctrl.moveTo(1000, 900)
    ui.GrabMenu.cancel.locate().click() # if was misclicked
    time.sleep(1.4)
    for i in team.cards:
        if ui.GrabMenu.card_R.check(f"card{i}"):
            get_card(ui, f"card{i}")
            wait_while_condition(
                condition=lambda: ui.GrabMenu.encounter_reward.check(), 
                action=lambda: ui.GrabMenu.confirm_ego.locate().click(),
                interval=0.1
            )
            return True
    else:
        return False
    

def confirm(ctrl: eg.InputController, ui: UIDatabase):
    '''Function to confirm EGO gift pop-ups'''
    if not ui.GrabMenu.confirm_ego.locate().click(): return False
    ctrl.moveTo(965, 878)
    time.sleep(0.3)
    ui.GrabMenu.confirm_ego.locate().click()
    return True


def get_adversity(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    if team.difficulty < GameMode.EXTREME or not ui.GrabMenu.adversity.check(): 
        return False
    
    x_coords = [target.box[0] for target in ui.GrabMenu.projection.locate_all()]
    sorted(x_coords)
    for x in x_coords:
        ui.point.click(coords=(x, 550), verify=ui.GrabMenu.select_count_R)
    time.sleep(0.3)
    ctrl.click(1725, 1000)
    wait_while_condition(lambda: ui.GrabMenu.adversity.check(), interval=0.2)
    return True