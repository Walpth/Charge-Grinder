import math, time, random

def linear(t):
    return t

def easeInOutQuad(t):
    return 2*t*t if t < 0.5 else -1 + (4 - 2*t)*t

def easeOutElastic(t):
    c4 = (2 * math.pi) / 3
    if t == 0:
        return 0
    elif t == 1:
        return 1
    return 2**(-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1

def human_delay(min_delay=0.01, max_delay=0.03):
    time.sleep(random.uniform(min_delay, max_delay))

def generate_move_path(start_x, start_y, x, y, duration=0.03, tween=easeInOutQuad, humanize=True):
    delay = 0.05
    distance = math.hypot(x - start_x, y - start_y)
    human_speed_delay = (distance / 2000.0)
    duration = max(0.001, duration + delay + human_speed_delay)

    steps = max(3, int(duration * 100))

    if humanize:
        curve_intensity = random.uniform(0.25, 0.75)
        jitter_frequency = random.randint(3, 7)
        jitter_magnitude = random.uniform(0.4, 1.8)

        # Speed profile controls
        speed_sigma = random.uniform(0.12, 0.22)
        speed_scale = random.uniform(0.9, 1.3)

        overshoot_chance = 0.15
        overshoot_distance_fraction = random.uniform(0.005, 0.02)
    else:
        curve_intensity = 0.0
        jitter_frequency = 0
        jitter_magnitude = 0.0
        speed_sigma = 0.18
        speed_scale = 1.0
        overshoot_chance = 0.0
        overshoot_distance_fraction = 0.0

    # Path geometry
    positions = []
    for i in range(steps):
        t = i / (steps - 1)
        progress = tween(t) if tween else t

        linear_x = start_x + (x - start_x) * progress
        linear_y = start_y + (y - start_y) * progress

        if humanize and duration > 0.1:
            curve_progress = math.sin(progress * math.pi)
            curve_offset_x = (y - start_y) * curve_intensity * curve_progress * 0.3
            curve_offset_y = (x - start_x) * curve_intensity * curve_progress * -0.3

            jitter_x = (
                math.sin(i * jitter_frequency)
                * (x - start_x) * 0.01 * jitter_magnitude
            )
            jitter_y = (
                math.cos(i * jitter_frequency)
                * (y - start_y) * 0.01 * jitter_magnitude
            )

            px = linear_x + curve_offset_x + jitter_x
            py = linear_y + curve_offset_y + jitter_y
        else:
            px, py = linear_x, linear_y

        positions.append((px, py))

    # Small overshoot + correction
    if humanize and random.random() < overshoot_chance:
        ox = (x - start_x) * overshoot_distance_fraction
        oy = (y - start_y) * overshoot_distance_fraction
        positions.append((x + ox, y + oy))
        positions.append((x, y))
    else:
        positions[-1] = (x, y)

    seg_lengths = []
    for i in range(len(positions) - 1):
        (ax, ay), (bx, by) = positions[i], positions[i + 1]
        seg_lengths.append(math.hypot(bx - ax, by - ay))

    # Speed profile (bell curve)
    def speed_profile(mid_t: float) -> float:
        gauss = math.exp(-((mid_t - 0.5) ** 2) / (2 * speed_sigma ** 2))
        return max(1e-6, gauss * speed_scale)

    raw_times = []
    for i, seg_len in enumerate(seg_lengths):
        mid_t = (i + 0.5) / (len(positions) - 1)
        desired_speed = speed_profile(mid_t)
        raw_times.append(seg_len / desired_speed)

    sum_raw = sum(raw_times) if raw_times else 1.0
    sleep_times = []

    if sum_raw <= 1e-9:
        even_time = duration / max(1, len(raw_times))
        for _ in raw_times:
            sleep_times.append(max(0.001, even_time))
    else:
        for rt in raw_times:
            base = duration * (rt / sum_raw)
            jitter_factor = random.uniform(0.9, 1.1) if humanize else 1.0
            sleep_times.append(max(0.001, base * jitter_factor))

    for i in range(len(sleep_times)):
        cx, cy = positions[i]

        out_x = int(min(max(cx, min(start_x, x)), max(start_x, x)))
        out_y = int(min(max(cy, min(start_y, y)), max(start_y, y)))

        yield (out_x, out_y, sleep_times[i])

    final_delay = random.uniform(0.02, 0.05) if humanize else 0.03
    yield (int(x), int(y), final_delay)

class WindowError(Exception): pass