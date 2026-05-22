# from source.engine.locate import *
from itertools import combinations_with_replacement
# import source.data.constants as p
from source.data.default_teams import TEAMS

loc_shop = loc_rgb(conf=0.83, wait=False, method=cv2.TM_SQDIFF_NORMED)
shop_click = loc_shop(click=True, wait=5)

item_points = {1: 3, 2: 6, 3: 10, 4: 15}
COMBOS = list(combinations_with_replacement(range(1, 5), 3))
get_tier3 = [((1, 1, 4), 21), ((1, 2, 3), 19), ((1, 2, 4), 24), ((1, 3, 3), 23), ((2, 2, 2), 18), ((2, 2, 3), 22)]

EXTRA = []
for i in range(3, 6):
    EXTRA += list(combinations_with_replacement(range(1, 5), i))

TWO_ITEM_COMBOS = list(combinations_with_replacement(range(1, 5), 2))


enhance_cost = {
    1: 150,
    2: 180,
    3: 225,
    4: 300,
}

fusion_ranges = {
    1: (9, 10),
    2: (11, 16),
    3: (17, 24),
    4: (25, 45)
}

super_ranges = {
    1: (9, 9),
    2: (10, 14),
    3: (15, 21),
    4: (22, 75)
}


def combo_counter(combo):
    counter = {}
    for tier in combo:
        if tier in counter:
            counter[tier] += 1
        else:
            counter[tier] = 1
    return counter


def decide_fusion(target_tier, inventory, depth=0):
    if target_tier not in fusion_ranges: raise ValueError("Invalid target fusion tier")

    if p.SUPER == "shop":
        combos = COMBOS
        ranges = fusion_ranges
    else:
        combos = EXTRA
        ranges = super_ranges

    if p.WISHMAKING:
        combos += TWO_ITEM_COMBOS

    low, high = ranges[target_tier]
    valid_combos = [
        (combo, sum(item_points[t] for t in combo))
        for combo in combos
        if low <= sum(item_points[t] for t in combo) <= high
    ]
    
    best_choice = None
    best_missing = None
    best_missing_cost = None
    best_total_cost = None

    for combo, total in valid_combos:
        needed = combo_counter(combo)
        missing = {}
        missing_cost = 0
        for tier, count_needed in needed.items():
            have = len(inventory[tier])
            if have < count_needed:
                deficit = count_needed - have
                missing[tier] = deficit
                missing_cost += deficit * item_points[tier]
        
        if missing.get(4, 0) > 0: # we are not buying tier 4 for fusion, no way
            continue
        
        if p.SUPER == "shop" and not depth and missing.get(3, 0) == 1 and \
           sum([missing.get(i, 0) for i in range(1, 2)]) == 0:
            new_have = {tier: len(items) for tier, items in inventory.items()}
            skip_missing = True
            for i in range(1, 5): # update inventory
                if i in needed.keys():
                    for _ in range(needed[i]):
                        if i == 3 and skip_missing:
                            skip_missing = False
                            continue
                        if new_have[i] > 0:
                            new_have[i] -= 1
            new_combo = None
            best_price = None
            for tier3_combo, price in get_tier3: # I don't want to do a recursion
                need = combo_counter(tier3_combo)
                for tier, count_needed in need.items():
                    if new_have[tier] < count_needed:
                        break
                else:
                    if best_price is None or price < best_price:
                        new_combo = tier3_combo
                        best_price = price
            # new_combo, new_missing = decide_fusion(3, new_inventory, 1)
            if new_combo:
                combo = new_combo
                missing = {}
                missing_cost = 0
                total = total - item_points[3] + best_price

        if best_missing_cost is None        or \
           missing_cost < best_missing_cost or \
          (missing_cost == best_missing_cost and 
           total < best_total_cost):

            best_choice = combo
            best_missing = missing
            best_missing_cost = missing_cost
            best_total_cost = total

    return best_choice, best_missing


def is_in_range(res, coord):
    return res[0] - 103 < coord[0] < res[0] + 19 and res[1] - 105 < coord[1] < res[1] + 17

def inventory_check(reg, h, uptie_det=True):
    coords_agg = {1: [], 2: [], 3: [], 4: []}
    coords     = {1: [], 2: [], 3: [], 4: []}
    have = {}
    uptie = {}
    comp = p.WINDOW[2] / 1920

    fuse_shelf = screenshot(region=reg)
    image = amplify(fuse_shelf)

    for i in range(len(p.GIFTS)):
        if p.GIFTS[i]["sin"]:
            uptie_ego = p.GIFTS[i]["uptie1"] | p.GIFTS[i]["uptie2"] | (p.GIFTS[i]["uptie3"] if i != 0 else {})
        else:
            uptie_ego = {}

        for gift in p.GIFTS[i]["all"]:
            try:
                if gift in CACHE: template = CACHE[gift]
                else: template = amplify(cv2.imread(PTH[gift]))
                x, y = gui.center(LocateRGB.try_locate(template, image=image, region=reg, conf=0.87))
                # print(f"got {gift} at {x, y}")
                have[gift] = (x, y, h)

                if uptie_det and gift in uptie_ego.keys():
                    uptie_region = fuse_shelf[int((y-66-reg[1])*comp):int((y-22-reg[1])*comp), int((x-14-reg[0])*comp):int((x+55-reg[0])*comp)]
                    try:
                        if not LocateRGB.check(PTH["+"], image=uptie_region, wait=False):
                            uptie[gift] = enhance_cost[uptie_ego[gift]]
                    except cv2.error:
                        print("Uptie detection failed")
                
                fuse_shelf = rectangle(fuse_shelf, (int(x - 62 - reg[0]), int(y - 72 - reg[1])), (int(x + 60 - reg[0]), int(y + 60 - reg[1])), (0, 0, 0), -1)
                image = rectangle(image, (int(x - 62 - reg[0]), int(y - 72 - reg[1])), (int(x + 60 - reg[0]), int(y + 60 - reg[1])), (0, 0, 0), -1)
            except gui.ImageNotFoundException:
                continue
    
    for gift in list(p.KEYWORDLESS.keys()):
        try:
            if gift in CACHE: template = CACHE[gift]
            else: template = amplify(cv2.imread(PTH[gift]))
            x, y = gui.center(LocateRGB.try_locate(template, image=image, region=reg, conf=0.86))
            # print(f"got {gift}")
            have[gift] = (x, y, h)

            if uptie_det and p.KEYWORDLESS[gift] > 2:
                uptie_region = fuse_shelf[int((y-66-reg[1])*comp):int((y-22-reg[1])*comp), int((x-14-reg[0])*comp):int((x+55-reg[0])*comp)]
                try:
                    if not LocateRGB.check(PTH["+"], image=uptie_region, wait=False):
                        uptie[gift] = enhance_cost[WORDLESS_MAP[gift]]
                except cv2.error:
                    print("Uptie detection failed")

            fuse_shelf = rectangle(fuse_shelf, (int(x - 62 - reg[0]), int(y - 72 - reg[1])), (int(x + 60 - reg[0]), int(y + 60 - reg[1])), (0, 0, 0), -1)
            image = rectangle(image, (int(x - 62 - reg[0]), int(y - 72 - reg[1])), (int(x + 60 - reg[0]), int(y + 60 - reg[1])), (0, 0, 0), -1)
        except gui.ImageNotFoundException:
            continue

    found_aff = []
    for aff in p.GIFTS:
        found_aff += [gui.center(box) for box in LocateRGB.locate_all(PTH[aff["checks"][4]], region=reg, image=fuse_shelf, threshold=50, method=cv2.TM_SQDIFF_NORMED)]

    for i in range(4, 0, -1):
        found = [gui.center(box) for box in LocateRGB.locate_all(PTH[str(i)], region=reg, image=fuse_shelf, threshold=50, method=cv2.TM_SQDIFF_NORMED)]

        for res in found:
            fuse_shelf = rectangle(fuse_shelf, (int(res[0] - 20 - reg[0]), int(res[1] - 22 - reg[1])), (int(res[0] + 102 - reg[0]), int(res[1] + 100 - reg[1])), (0, 0, 0), -1)
            x, y = res
            coords_agg[i].append((x, y, h))
            coords[i].append((x, y, h))

    for res in found_aff:
        for i in range(1, 5):
            match = next((coord for coord in coords[i] if is_in_range(res, coord)), None)
            if match:
                coords[i].remove(match)
                break

    return coords, coords_agg, have, uptie

def browse(step=128, adj=0, dur=0.3, pr_end=True):
    win_moveTo(1227, 380)
    gui.mouseDown()
    win_moveTo(1227, 380 - step + adj, duration=dur)
    gui.mouseUp()
    if pr_end:
        win_click(1227, 380)

def concat(dict1, dict2):
    for key in dict2:
        if key in dict1:
            dict1[key].extend(dict2[key])
        else:
            dict1[key] = dict2[key]
    return dict1

def get_inventory():
    coords, coords_agg, have, uptie = inventory_check(REG["fuse_shelf"], 0)
    if now_rgb.button("scroll"):
        h = 1
        adj = 0
        while not now_rgb.button("scroll.0"):
            browse(adj=adj)
            new_coords, new_coords_agg, new_have, new_uptie = inventory_check(REG["fuse_shelf_low"], h)

            ck = LocateRGB.locate(PTH["height_ck"], region=REG["fuse_shelf_low"])
            adj = 607 - ck[1] if ck else 0

            coords = concat(coords, new_coords)
            coords_agg = concat(coords_agg, new_coords_agg)
            have.update(new_have)
            uptie.update(new_uptie)
            h += 1
    
        for _ in range(2*h): gui.scroll(1)
        win_moveTo(1227, 234)
        time.sleep(0.4)
    p.TO_UPTIE = uptie
    return coords, coords_agg, have


def actual_fuse(tier, coords):
    to_click = []
    combo, missing = decide_fusion(tier, coords)
    if not missing:
        for tier in combo:
            to_click.append(coords[tier][-1])
            coords[tier].pop(-1)
        perform_clicks(to_click)
        return None
    else: return missing

def perform_clicks(to_click):
    if p.WISHMAKING and not now_rgb.button("wishmaking"):
        time.sleep(0.1)
        wait_while_condition(lambda: not now.button("Confirm.0"), lambda: win_click(410, 755), interval=0.2, timer=0.2)
        wait_while_condition(lambda: now_click.button("Confirm.0"))
        win_moveTo(1194, 841)
        time.sleep(0.2)

    to_click = sorted(to_click, key=lambda x: x[2])
    h = 0
    adj = 0
    for pos in to_click:
        if pos[2] - h > 0:
            for _ in range(pos[2] - h):
                browse(adj=adj)
                ck = LocateRGB.locate(PTH["height_ck"], region=REG["fuse_shelf_low"])
                adj = 607 - ck[1] if ck else 0
            h = pos[2]
            time.sleep(0.2)
        ClickAction(pos[:2], ver="forecast!").execute(click_rgb)
    if h:
        win_moveTo(1227, 380)
        for _ in range(2*h+2): gui.scroll(1)
        time.sleep(0.4)
    chain_actions(click, [
        Action("fuse", click=(1197, 876)),
        Action("Confirm.2", ver="Confirm"),
        lambda: time.sleep(0.3),
        # Action("Confirm", ver="fuseButton"),
        lambda: wait_while_condition(lambda: now_click.button("Confirm"))
    ])
    to_click.clear()


def set_affinity(i, teams=None):
    if teams is None: teams = p.GIFTS
    if p.IDX == i: return
    p.IDX = i
    ClickAction((469, 602), ver="keywordSel").execute(shop_click)
    confirm_affinity(teams=teams)
    time.sleep(0.2)

def search_have(have, fuse_type, idx):
    missing = 0
    iterations = 0
    names = []
    if name := next((key for key, value in p.GIFTS[idx][f"fuse{fuse_type + 1}"].items() if value is None), None):
        if name in have:
            iterations += 2
        else:
            names += list(p.GIFTS[idx][f"fuse{fuse_type}"].keys())

    names += [key for key, value in p.GIFTS[idx][f"fuse{fuse_type + 1}"].items() if value is not None]
    for name in names:
        if name not in have.keys():
                missing += 1
        iterations += 1
    return missing/iterations

def fuse_search(have):
    advanced_fusing = []
    if p.GIFTS[0]["sin"] and not p.GIFTS[0]["goal"][0] in have.keys():
        advanced_fusing.append((0, search_have(have, 1, 0), 1))
    if p.HARD and p.GIFTS[0]["sin"] and not p.GIFTS[0]["goal"][1] in have.keys():
        advanced_fusing.append((0, search_have(have, 3, 0), 3))
    advanced_fusing.sort(key=lambda item: (item[1], item[0]))
    return advanced_fusing

def fuse():
    time.sleep(0.2)
    coords, coords_agg, have = get_inventory()
    to_click = []
    fuse_type = 0
    got_all = False
    advanced_fusing = fuse_search(have)

    if p.EXTREME: coords_agg = coords

    # get powerful ego gift
    for i in range(len(p.GIFTS)):
        if not list(p.GIFTS[i]["uptie2"].keys())[0] in have.keys():
            _, missing = decide_fusion(4, coords_agg)
            if missing: 
                if i == 0 or not advanced_fusing:
                    return missing
                else:
                    break
            else:
                set_affinity(i)
                actual_fuse(4, coords_agg)
                return None
    else:
        got_all = True

    # get recipe ego gifts 
    if advanced_fusing:
        i, _, fuse_type = advanced_fusing[0]
        set_affinity(i)
    elif got_all:
        for i in range(len(p.GIFTS)):
            for name, tier in p.GIFTS[i]["fuse_ex"].items():
                if not name in have.keys():
                    set_affinity(i)
                    missing = actual_fuse(tier, coords)
                    return missing

        # lunar memory
        if p.EXTREME and not "lunarmemory" in have.keys():
            teams = list(TEAMS.values())
            for i in range(7, 10):
                if not list(teams[i]["uptie2"].keys())[0] in have.keys():
                    set_affinity(i, teams=teams)
                    missing = actual_fuse(4, coords)
                    return missing
                to_click.append(have[list(teams[i]["uptie2"].keys())[0]])
            stones_have = list(set([f"stone{i}" for i in range(7)]) & set(have.keys()))
            if len(stones_have) < 2:
                for i in range(7):
                    if not f"stone{i}" in have.keys():
                        set_affinity(i, teams=teams)
                        missing = actual_fuse(4, coords)
                        return missing
            for i in range(2):
                to_click.append(have[stones_have[i]])
            if p.SUPER == "supershop":
                perform_clicks(to_click)
        raise NotImplementedError
    else:
        return None

    if fuse_type:
        for name, tier in p.GIFTS[p.IDX][f"fuse{fuse_type+1}"].items():
            if not name in have.keys():
                if tier != None:
                    missing = actual_fuse(tier, coords)
                    return missing
                else: # need to fuse
                    for name, tier in p.GIFTS[p.IDX][f"fuse{fuse_type}"].items():
                        if not name in have.keys():
                            missing = actual_fuse(tier, coords)
                            return missing
                        to_click.append(have[name])
                    perform_clicks(to_click)
                    return None
            to_click.append(have[name])
        perform_clicks(to_click)

    return None


def confirm_affinity(teams=None):
    if teams is None: teams = p.GIFTS
    if not (0 <= p.IDX < len(teams)): p.IDX = 0
    click_rgb.button(teams[p.IDX]["checks"][3], "affinity!")
    win_click(1194, 841)

def init_fuse():
    chain_actions(shop_click, [
        Action(p.SUPER, click=(469, 602), ver="fuse"),
        lambda: time.sleep(0.1),
        ClickAction((469, 602), ver="keywordSel")
    ])
    confirm_affinity()

def fuse_loop():
    init_fuse()
    ehnance_flag = True
    ref_count = 1 + (p.BUFF[5] > 2)
    try:
        while True:
            missing = fuse()
            if missing:
                Action("fuse", click=(750, 873), ver=p.SUPER).execute(click)
                time.sleep(0.1)

                if ehnance_flag and p.TO_UPTIE:
                    enhance(p.TO_UPTIE)
                    ehnance_flag = False

                if len(LocateRGB.locate_all(PTH["purchased"], region=REG["buy_shelf"], threshold=100)) == 8: return

                result = buy_loop(missing, keyword_ref=(ref_count > 0))
                ref_count -= 1
                if not result: return
                else:
                    init_fuse() # open fusing
    except NotImplementedError:
        Action("fuse", click=(750, 873), ver=p.SUPER).execute(click)
        print("We got everything!")
        time.sleep(0.1)

        if p.TO_UPTIE:
            enhance(p.TO_UPTIE)

        buy_some(2 + 2*(p.LVL < 11))


### EGO gift enhance logic
def uptie_inventory_check(gifts, reg):
    fuse_shelf = screenshot(region=reg)
    image = amplify(fuse_shelf)

    for gift in gifts:
        try:
            if gift in CACHE: template = CACHE[gift]
            else: template = amplify(cv2.imread(PTH[gift]))
            x, y = gui.center(LocateRGB.try_locate(template, image=image, region=reg, conf=0.88))
            print(f"got {gift}")
            win_click(x, y)
            for _ in range(2):
                chain_actions(click, [
                    Action("power"),
                    Action("Confirm.2", ver="power")
                ])
                win_moveTo(1215, 939)
            time.sleep(0.2)
        except gui.ImageNotFoundException:
            continue

def get_uptie_inventory(gift_list):
    uptie_inventory_check(gift_list, REG["fuse_shelf"])
    if now_rgb.button("scroll"):
        h = 1
        adj = 0
        while not now_rgb.button("scroll.0"):
            browse(adj=adj)
            uptie_inventory_check(gift_list, REG["fuse_shelf_low"])
            ck = LocateRGB.locate(PTH["height_ck"], region=REG["fuse_shelf_low"])
            adj = 607 - ck[1] if ck else 0
            h += 1

def search_sell(reg):
    coords, _, _, _ = inventory_check(reg, 0, uptie_det=True)
    for i in range(4, 0, -1):
        if coords[i] != []:
            try:
                chain_actions(click, [
                    lambda: win_click(coords[i][0][:2]),
                    lambda: time.sleep(0.2),
                    ClickAction((1182, 879)),
                    Action("Confirm_retry.0", ver="connecting"),
                    connection,
                    Action("sell", click=(750, 879), ver=p.SUPER)
                ])
            except RuntimeError:
                continue
            return True
    return False

def sell(gifts):
    while True:
        if balance() < sum(gifts.values()):
            Action(p.SUPER, click=(600, 585), ver="sell").execute(click)
            found_flag = False
            if now_rgb.button("scroll"):
                while not now_rgb.button("scroll.0"):
                    browse(step=300, dur=0.1, pr_end=False)
                    time.sleep(0.5)
                adj = 0
                while not now_rgb.button("scroll"):
                    if search_sell((920, 585, 790, 165)):
                        found_flag = True
                        break
                    browse(step=-143, adj=adj)
                    ck = LocateRGB.locate(PTH["height_ck"], region=(920, 585, 790, 165))
                    adj = 600 - ck[1] if ck else 0
                if search_sell((920, 295, 790, 345)):
                    found_flag = True
                    break
            else:
                if search_sell((920, 295, 790, 345)):
                    continue
            
                if found_flag: continue
            
            Action("sell", click=(750, 879), ver=p.SUPER).execute(click)
            return False # nothing to sell
        else:
            return True # got the cost

def check_ehance_cost(gifts):
    if not sell(gifts): # cutting costs
        cost = balance()
        uptie = []
        for k, v in gifts.items():
            cost -= v
            if cost > 0:
                uptie.append(k)
            else:
                break
    else:
        uptie = list(gifts.keys())
    return uptie


def enhance(gifts, floor1=False):
    if not floor1:
        gift_list = check_ehance_cost(gifts)
        if not gift_list: return

        ClickAction((250, 581), ver="power").execute(click)
    else:
        gift_list = [k for k in gifts.keys()]

    get_uptie_inventory(gift_list)
    Action("power", click=(750, 873), ver=p.SUPER).execute(click)
    time.sleep(0.3)


### Shop shelf-related logic
def balance():
    answer_me = True
    bal = -1
    start_time = time.time()
    # gui.screenshot(f"cost{time.time()}.png", region=(857, 175, 99, 57)) # debugging
    while bal == -1:
        if time.time() - start_time > 20: raise RuntimeError("Infinite loop exited")
        digits = []
        for i in range(9, -1, -1):
            pos = [gui.center(box) for box in LocateRGB.locate_all(PTH[f"cost{i}"], region=(857, 175, 99, 57), threshold=7, conf=0.9, method=cv2.TM_SQDIFF_NORMED)]
            for coord in pos:
                if all(abs(coord[0] - existing_coord) > 7 for _, existing_coord in digits):
                    digits.append((i, coord[0]))
        digits = sorted(digits, key=lambda x: x[1])

        bal = ""
        for i in digits: bal += str(i[0])
        bal = int(bal or -1)
        if bal != -1 and bal < 300 and answer_me: 
            time.sleep(0.2)
            answer_me = False # you game me an answer, but not your own
            bal = -1 # I will ask again
    print("money", bal)
    if p.LVL > 10:
        bal = apply_inflation(bal)
    return bal

def apply_inflation(value):
    if 13 > p.LVL > 10:
        value = value // 2
    elif p.LVL >= 13:
        value = value // 3
    return value

def conf_gift():
    connection()
    Action("purchase", ver="Confirm").execute(click)
    time.sleep(0.3)
    wait_while_condition(
        condition=lambda: now.button("Confirm"),
        action=lambda: now_click.button("Confirm"),
        interval=0.1
    )

def update_shelf():
    shop_shelf = screenshot(region=REG["buy_shelf"])
    shop_shelf = rectangle(shop_shelf, (52, 33), (224, 195), (0, 0, 0), -1)
    for ignore in ["purchased", "cost"]:
        found = [gui.center(box) for box in LocateRGB.locate_all(PTH[str(ignore)], region=REG["buy_shelf"], image=shop_shelf, threshold=20)]
        for res in found:
            shop_shelf = rectangle(shop_shelf, (int(res[0] - 70 - 809), int(res[1] - 25 - 300)), (int(res[0] + 70 - 809), int(res[1] + 150 - 300)), (0, 0, 0), -1)
    return shop_shelf

def filter_x_distance(points, x_tol=2, y_tol=25):
    points = sorted(points, key=lambda p: p[0])
    result = []
    for p in points:
        if all(abs(p[0] - q[0]) >= x_tol or abs(p[1] - q[1]) > y_tol for q in result):
            result.append(p)
    return result

def get_shop(shop_shelf):
    tier1 = [gui.center(box) for box in LocateRGB.locate_all(PTH["buy1"], region=REG["buy_shelf"], image=shop_shelf, threshold=3.5, conf=0.92, method=cv2.TM_SQDIFF_NORMED)]
    tier4 = [gui.center(box) for box in LocateRGB.locate_all(PTH["buy4"], region=REG["buy_shelf"], image=shop_shelf, threshold=10, conf=0.92, method=cv2.TM_SQDIFF_NORMED)]
    tier1 = filter_x_distance(tier1)
    have = {1: [], 2: [], 3: []}
    visited = set()
    for i, pt_i in enumerate(tier1):
        if i in visited: continue
        count = 1
        for j in range(i + 1, len(tier1)):
            pt_j = tier1[j]
            if all(abs(pt_i[k] - pt_j[k]) <= 25 for k in range(2)):
                visited.add(j)
                count += 1
        have[min(count, 3)].append(pt_i)
    have[1] = [
        (fx, fy) for (fx, fy) in have[1]
        if not any(abs(fx - x) <= 25 and abs(fy - y) <= 25 for (x, y) in tier4)
    ]
    return have


def buy_known(aff):
    shop_shelf = update_shelf()
    output = False
    for gift in aff["buy"]:
        try:
            res = gui.center(LocateRGB.try_locate(PTH[gift], image=shop_shelf, region=REG["buy_shelf"], comp=0.75, conf=0.83))
            print(f"got {gift}")
            win_click(res)
            conf_gift()
            time.sleep(0.1)
            shop_shelf = update_shelf()
            output = True
        except gui.ImageNotFoundException:
            continue
    return shop_shelf, output

def buy_affinity(aff):
    box = True
    while box:
        shop_shelf = update_shelf()
        box = LocateRGB.locate(PTH[aff["checks"][0]], region=REG["buy_shelf"], image=shop_shelf, method=cv2.TM_SQDIFF_NORMED, comp=0.88, conf=0.8)
        if box: 
            res = gui.center(box)
            win_click(res)
            conf_gift()
            time.sleep(0.1)
    return shop_shelf, False

def buy_some(rerolls=1, priority=False):
    time.sleep(0.2)
    iterations = rerolls + 1
    keywordless = [{"buy": [name for name, state in p.KEYWORDLESS.items() if state > 1], "sin": True}]
    sold_all = False
    for _ in range(iterations):
        if not priority and not sold_all and balance() < 200:
            sold_all = not sell({"all": 300})
        if p.EXTREME:
            for _ in range(1 + int(p.SUPER == "supershop")):
                buy_skill3()
        for aff in keywordless + p.GIFTS:
            if not priority or not aff["sin"]: # just buy same affinity
                if "checks" in aff: # all but keywordless
                    buy_affinity(aff)
                else:
                    buy_known(aff)
            else: # buy only necessary stuff
                buy_known(aff)
        if len(LocateRGB.locate_all(PTH["purchased"], region=REG["buy_shelf"], threshold=100)) == 8: break
        if rerolls and balance() >= 200:
            rerolls -= 1
            win_click(1489, 177)
            connection()
            time.sleep(0.1)
        elif balance() < 120: return

def buy(missing):
    output = False
    keywordless = [{"buy": [name for name, state in p.KEYWORDLESS.items() if state > 1], "sin": True}]
    for aff in keywordless + p.GIFTS:
        if aff["sin"]:
            shop_shelf, out = buy_known(aff)
        else:
            shop_shelf, out = buy_affinity(aff)
        if out: output = True

    if output: return True, missing # got build

    gained = {1: 0, 2: 0, 3: 0}
    for tier in sorted(missing.keys(), reverse=True):
        for _ in range(missing[tier]):
            have = get_shop(shop_shelf)
            print(f"got {have}")
            if have[tier]:
                win_click(have[tier][0])
                conf_gift()
                shop_shelf = update_shelf()
                gained[tier] += 1
            else:
                return output, {key: missing[key] - gained[key] for key in missing} # got something
    return True, {} # got everything

def buy_loop(missing, floor1=False, keyword_ref=True):
    print("need", missing)
    result, missing = buy(missing)
    if not result or floor1:
        try: 
            if keyword_ref and ((bal:= balance()) >= 300 or bal >= 200 and p.BUFF[5] > 0):
                Action(p.SUPER, click=(1715, 176), ver="keywordRef").execute(shop_click)
                wait_while_condition(
                    condition=lambda: now.button("keywordRef") and not now.button("connecting"), 
                    action=confirm_affinity
                )
                connection()
                if p.EXTREME:
                    time.sleep(0.2)
                    for _ in range(1 + int(p.SUPER == "supershop")):
                        buy_skill3()

                result, missing = buy(missing)

            if (not result or floor1) and balance() >= 200:
                win_click(1489, 177)
                connection()
                time.sleep(0.1)
                if p.EXTREME:
                    time.sleep(0.2)
                    for _ in range(1 + int(p.SUPER == "supershop")):
                        buy_skill3()

                new_result, _ = buy(missing)
                result = result or new_result
        except RuntimeError:
            print("no cash, sorry")
    return result


def buy_skill3():
    if balance() <= 120 or now.button("purchased") or now.button("cost", "purchased"): return
    for sinner in p.SELECTED[:7]:
        if now.button(f"{sinner.lower()}_s3", "buy_s3"):
            break
    else:
        return

    ClickAction((929, 388), ver="replace").execute(click)
    win_click(1442, 497, duration=0.2)
    win_click(1187, 798, duration=0.2)
    if not wait_while_condition(lambda: not now.button("connecting"), lambda: win_click(1187, 798), timer=1):
        win_click(953, 497, duration=0.2)
        win_click(1187, 798, duration=0.2)
        if not wait_while_condition(lambda: not now.button("connecting"), lambda: win_click(1187, 798), timer=2):
            win_click(772, 800)
            return
    connection()


def revive_idiots():
    revivals = min(p.DEAD, balance()//100)
    if revivals < 1: return
    
    ClickAction((293, 705), ver="return").execute(click)
    for _ in range(revivals):
        if not wait_while_condition(lambda: now.button("return"), lambda: win_click(1545, 690), timer=3):
            Action("return", ver=p.SUPER).execute(click)
            return
        Action("no_hp", ver="select").execute(click_rgb)
        Action("select", ver="connecting").execute(click)
        connection()
        ClickAction((1545, 500), ver="return").execute(click)
        time.sleep(0.2)
    Action("return", ver=p.SUPER).execute(click)
    time.sleep(0.2)

def heal_all():
    if balance() < 100: return

    ClickAction((293, 705), ver="return").execute(click)
    try:
        ClickAction((1545, 500), ver="connecting").execute(click)
        connection()
        time.sleep(0.2)
    finally:
        ClickAction((1545, 500), ver="return").execute(click)
        Action("return", ver=p.SUPER).execute(click)
        time.sleep(0.2)

### General
def leave():
    chain_actions(click, [
        ClickAction((1705, 967)),
        Action("ConfirmInvert", ver="Move")
    ])


def handle_shop():
    if now_click.button("return"): time.sleep(0.5)

    if now.button("shop"): p.SUPER = "shop"
    elif not p.HARD or not now.button("supershop"): return False
    else: p.SUPER = "supershop"
    print("shop check passed")

    time.sleep(0.2)

    wait_while_condition(lambda: now_click.button("Confirm"))

    if p.DEAD > 0 and p.HARD:
        revive_idiots()
        heal_all()

    if p.LVL > 11:
        for _ in range(min(p.LVL - 11, 3)):
            heal_all()

    if p.EXTREME:
        for _ in range(1 + int(p.SUPER == "supershop")):
            buy_skill3()

    if p.LVL == 1:
        ClickAction((250, 581), ver="power").execute(click)
        if not loc_shop.button("+", "fuse_shelf", conf=0.95):
            # we really are on the first floor
            try:
                enhance(p.GIFTS[0]["uptie1"], floor1=True)
                buy_loop({3: 2}, floor1=True)
            except RuntimeError:
                handle_fuckup()
        else:
            # the bot was started midway, so this is not the first floor
            p.LVL = 2
            Action("power", click=(750, 873), ver=p.SUPER).execute(click)
    if 5 + p.EXTREME*11 > p.LVL > 1 or not p.SKIP:
        buy_some(rerolls=0, priority=True)
        fuse_loop()
    
    if p.EXTREME:
        win_click(1489, 177)
        connection()
        time.sleep(0.1)
        for _ in range(1 + int(p.SUPER == "supershop")):
            buy_skill3()
    
    time.sleep(0.1)
    leave()
    return True