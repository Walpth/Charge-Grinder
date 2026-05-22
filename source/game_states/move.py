# from source.engine.locate import *

# Weights are the average battle time in seconds
priority = {"Event": 0, "Normal": 52, "Miniboss": 67, "Risky": 87, "Focused": 77}
v_list = [0.8, 0.9, 1]
d_list = [None, -0.1, -0.19]

def find_danteh(): # looks for high resolution Dante
    for i in range(2):
        try:
            Danteh = LocateRGB.try_locate(PTH[f"Danteh{i}"])
            print("Danteh found")
            x, y = gui.center(Danteh)
            return x, y
        except:
            continue
    return None


def find_bus(): # looks for low resolution Dante
    try:
        Bus = LocateRGB.try_locate(PTH["Bus"])
        print("Danteh found")
        x, y = gui.center(Bus)
        return x, y
    except:
        return None


def zoom(direction):
    for i in range(6):
        Danteh = find_danteh()
        if Danteh:
            return Danteh
        gui.scroll(direction)
        time.sleep(0.1)
    return None


def position(object, shift=0):
    win_moveTo(object)
    win_dragTo(429, 480 + shift*290, duration=0.4)
    win_click(329, 710)


def hook():
    Bus = find_bus()
    if Bus is None : return False
    position(Bus)
    return True


def is_boss(region, comp):
    image = screenshot(region=region)
    red_mask = cv2.inRange(image, np.array([0, 0, 180]), np.array([50, 50, 255]))
    for i in range(2):
        res = now_click.button(f"boss{i}", region, image=red_mask, comp=comp, conf=0.6)
        if res: return res
    return now_click.button("boss_ark", region, image=image, comp=comp)

def is_risky(_loc, comp, region):
    if _loc.button("risk0", region) or \
   any(_loc.button("risk1", region, comp=comp*(1 - 0.14*j)) for j in range(2)) or \
   any(_loc.button("risk2", region, comp=comp*(1 - 0.14*j), v_comp=None, distort=None) for j in range(2)):
        return True
    return False

def is_focused(_loc, region):
    if any(_loc.button(f"focus{j}", region, conf=0.85) for j in range(2)) or \
       any(_loc.button(f"focus{j+2}", region, conf=0.85, v_comp=None, distort=None) for j in range(2)):
        return True
    return False

def is_event(_loc, region):
    if any(_loc.button(f"event{j}", region, conf=0.85) for j in range(2)) or \
           _loc.button("event2", region, conf=0.9, v_comp=None, distort=None):
        return True
    return False

def is_shop(_loc, region):
    if _loc.button("shop0", region) or \
       _loc.button("shop1", region, v_comp=None, distort=None) or \
       (p.HARD and (_loc.button("super0", region) or _loc.button("super1", region, v_comp=None, distort=None))):
        return True
    return False


def directions():
    options = {
        0: "_up",
        1: "_forward",
        2: "_down"
    }
    regions = dict()
    for i, suffix in options.items():
        for j in range(2):
            comp_val = 1 - 0.14 * j
            if now.button(suffix, "directions", conf=0.85, comp=comp_val):
                regions[i] = (624, 101 + i * 275, 282, 275)
                break
    return regions


def get_connections():
    image = screenshot(region=(850, 340, 610, 370))
    h, w = image.shape[:2]
    crop_h = int(0.216 * h)
    crop_w = int(0.492 * w)

    images = [
        image[0:crop_h, 0:crop_w],
        image[0:crop_h, w - crop_w:w],
        image[h - crop_h:h, 0:crop_w],
        image[h - crop_h:h, w - crop_w:w]
    ]
    connections = []
    for i, image in enumerate(images):
        paths = dict()
        for j, direction in enumerate(["up", "down"]):
            paths[j] = LocateGray.get_conf(PTH[direction], image=image)
        j = max(paths, key=paths.get)
        if paths[j] >= 0.87:
            connections.append(((i % 2, (i//2) + 1 - j), (i % 2 + 1, (i//2) + j)))
    return connections

def check_connections(connections):
    levels = [y for pair in connections for (_, y) in pair]
    
    has_zero = 0 in levels
    has_two = 2 in levels
    
    if (has_zero and has_two) or (not has_zero and not has_two): return 0
    elif has_zero: return 1
    else: return -1

def next_step(nodes, extra_connections):
    L = len(nodes)
    adj = {}
    for i in range(L):
        for j in range(len(nodes[i])):
            if nodes[i][j] is not None:
                adj[(i,j)] = []
    for i in range(L-1):
        for j in range(len(nodes[i])):
            if nodes[i][j] is not None and nodes[i+1][j] is not None:
                adj[(i,j)].append((i+1, j))
    for (a,b),(c,d) in extra_connections:
        if 0 <= a < L and 0 <= b < len(nodes[a]) and 0 <= c < L and 0 <= d < len(nodes[c]):
            if nodes[a][b] is None or nodes[c][d] is None:
                continue
            if a + 1 == c:
                adj.setdefault((a,b), []).append((c,d))
            elif c + 1 == a:
                adj.setdefault((c,d), []).append((a,b))

    def dfs(i, j):
        base = priority[nodes[i][j]]
        if i == L - 1:
            return base
        best = float('inf')
        for (ni, nj) in adj.get((i,j), []):
            if ni != i + 1:
                continue
            sub = dfs(ni, nj)
            if sub < float('inf'):
                best = min(best, base + sub)
        return best

    best_idx = None
    best_cost = float('inf')
    for j0 in range(len(nodes[0])):
        if nodes[0][j0] is None:
            continue
        cost0 = dfs(0, j0)
        if cost0 < best_cost:
            best_cost = cost0
            best_idx = j0
    if best_idx is None:
        return None, None
    return best_idx, nodes[0][best_idx]


def enter(wait=1):
    button = None
    if now.button("enter", wait=wait):
        button = "enter"
    elif p.EXTREME and now.button("secretEncounter", wait=wait):
        if p.SKIP: button = "skipEncounter"
        else: button = "secretEncounter"
    if button:
        wait_while_condition(
            condition= lambda: now.button(button),
            action=lambda: click.button(button)
        )
        win_moveTo(1721, 999)
        connection()
        return True
    return False


def handle_move():
    enter(wait=False)
    is_move = now.button("Move")

    if is_move and p.MOVE_ANIMATION:
        wait_while_condition(condition=lambda: now.button("Move"), interval=0.1)
        p.MOVE_ANIMATION = False
        is_move = loc.button("Move", wait=2)
        time.sleep(0.5)
    
    if not is_move or now.button("Confirm"): return False
    
    if p.HARD:
        time.sleep(1.2) # node reveal animation
        if now.button("superposition"): return False
    else:
        time.sleep(0.2)

    print("move check passed")

    # run fail detection
    p.DEAD = len([gui.center(box) for box in LocateRGB.locate_all(PTH["0"], region=REG["alldead"], conf=0.9, threshold=40)])
    print(f"{p.DEAD} dead sinners")
    if p.DEAD >= len(p.SELECTED):
        gui.press("Esc")
        time.sleep(0.5)
        chain_actions(click, [
            Action("forfeit"),
            Action("ConfirmInvert", ver="connecting"),
        ])
        connection()
        return False
    # fail detection end

    comp = 1 # image compression is off

    Dante = find_danteh()
    if Dante is None: 
        Dante = zoom(-1)
        comp = 0.86 # image compression is on
        if Dante is None and find_bus(): hook()
        if Dante is None: Dante = zoom(1)
        if Dante is None: return False
    
    position(Dante)
    
    if now.button("victory"): return False

    regions = directions()
    inter_connect = get_connections()
    adjust = check_connections(inter_connect)

    if adjust:
        keys = [i + adjust for i in regions.keys() if 0 <= i + adjust <= 2]
        regions = {key: (624, 101 + key * 275, 282, 275) for key in keys}
        position((429, 480), shift=adjust)

    inter_connect = get_connections()
    print(inter_connect)
    nodes = [[None, None, None] for _ in range(3)]

    for depth in range(3):
        if depth == 0: srch_regions = regions.copy()
        else: srch_regions = {i: (624 + 380 * depth, 101 + i * 275, 282, 275) for i in range(3)}

        for level, region in srch_regions.items():
            _loc = LocatePreset(image=screenshot(region=region), comp=comp, v_comp=v_list[level], distort=d_list[depth], conf=0.8, wait=False)
            # gui.screenshot(f"region{depth}{level}.png", region=region)

            if depth == 0 and level == 1 and is_boss(region, comp):
                enter()
                logging.info("Entering Boss fight")
                return True

            elif now_rgb.button("coin", region, conf=0.9, comp=comp):
                if now_rgb.button("gift", region, conf=0.9, comp=comp):
                    if is_risky(_loc, comp, region):
                        nodes[depth][level] = "Risky"
                        continue
                    elif is_focused(_loc, region):
                        nodes[depth][level] = "Focused"
                        continue
                    else:
                        nodes[depth][level] = "Miniboss"
                        continue
                else:
                    nodes[depth][level] = "Normal"
                    continue

            elif is_event(_loc, region):
                nodes[depth][level] = "Event"
                continue

            elif depth == 0 and is_shop(_loc, region):
                win_click(gui.center(srch_regions[level]))
                enter()
                logging.info("Entering Shop")
                return True
        if not any(nodes[depth]):
            if depth != 0: nodes = nodes[:depth]
            break
    if any(nodes[0]):
        print(nodes)
        id, name = next_step(nodes, inter_connect)
        print(id)
        if not id is None:
            win_click(gui.center(regions[id]))
            enter()
            logging.info(f"Entering {name} {'fight'*(name!='Event')}")
            return True

    # if we fail
    Danteh = find_danteh()
    if Danteh is None: return False

    win_click(Danteh)
    if enter(): return True

    # if we double fail:
    for i in range(3):
        x_click = int(Danteh[0] + 336)
        y_click = int(Danteh[1] - 241 + i * 275)
        if 57 <= x_click <= 1809 and 110 <= y_click <= 934:
            win_moveTo(x_click, y_click)
            gui.click()
            if enter():
                logging.info(f"Entering unknown node")
                return True
    return False