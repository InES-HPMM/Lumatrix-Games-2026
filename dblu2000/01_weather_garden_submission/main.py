"""Weather Garden - a bioluminescent plant you tend with weather.   (Lumatrix Games Challenge 2026)

It grows from a seed, blooms when it is warm and bright, shrinks when ignored, never dies.
Its shape remembers the wind it lived through. Everything is readable from the 64 LEDs.

  UP (hold) rain     LEFT/RIGHT wind gust (blows clouds, bends growth)     DOWN prune
  CENTER sunshine    growth boost, warms the plant for a while -> the stem tips open into blooms
  Warmth (optional)  breathe on / touch the RP2040 (internal temperature sensor); sun = warmth
  Slide switch       LOW = night (plant glows, blooms close)    [flip NIGHT_LOW if reversed]
  Blue dots blink next to the stem when it is thirsty. Clouds dim the light.
  Auto-mode          leave the joystick alone for AUTO_AFTER seconds and the garden tends itself
  Secret             one hidden cheat code - the most famous one in video games. See CHEATS below.
Tune rain / wind / bloom / auto-mode in the "tunables" block below.
"""
import gc, math, random
from machine import Pin, ADC
from time import sleep_ms, ticks_ms, ticks_diff
from zhaw_led_matrix import LedMatrix

# --- config -------------------------------------------------------------------------------
BRIGHTNESS = 15
TICK_MS = 350                 # one growth tick
FRAME_MS = 40                 # ~25 fps
TIME_LAPSE = 1                # >1 = faster growth and drying (for the video)
MAX_CELLS = 40
DRAIN = 0.003                 # water lost per tick (easy game: a full tank lasts several minutes)
GROW_COST = 0.02              # water used up by every new cell
WITHER = 0.04                 # how fast a thirsty cell fades per tick once the plant has run dry
WARM_FLOOR = 0.35             # daylight warmth without touching the chip
WARM_RANGE = 4.0              # degrees above start-up temperature = full warmth
NIGHT_LOW = True              # slide switch LOW = night
# --- tunables: rain, wind, bloom -------------------------------------------------------------
RAIN_EVERY = 0.09             # seconds between drops while UP is held
RAIN_WATER = 0.04             # water added by each drop that lands
WIND_LEAN = 0.25              # how far each LEFT/RIGHT bends future growth (max 1)
WIND_SWAY = 0.9               # how far a gust bends the plant (pixels at the top)
GUST_DECAY = 0.96             # per frame: closer to 1 = a gust lasts longer
BUD_WARMTH, OPEN_WARMTH, CLOSE_WARMTH = 0.6, 0.7, 0.4    # warmth needed to bud / open / (below) close
BUD_MIN_Y, BUD_CHANCE, OPEN_CHANCE = 2, 0.25, 0.3       # lowest bud row; chance per tick
SUN_BLOOM = 25                # CENTER also warms the plant for this many seconds (0 = off)
TOP = 6                       # highest row a stem can reach; row 7 stays free for the flower heads
BLOOM_HUE = 0.01              # colour of the blooms: 0 red, 0.07 orange, 0.15 yellow, 0.6 blue, 0.8 purple, 0.9 pink
AUTO_AFTER = 30               # seconds without a joystick press before the garden tends itself (0 = never)
UP, DOWN, LEFT, RIGHT, CENTER, SWITCH = 3, 6, 7, 2, 8, 9
KEYS = {UP: 'U', DOWN: 'D', LEFT: 'L', RIGHT: 'R', CENTER: 'C'}
CHEATS = {'UUDDLRLR': {'rainbow': 3, 'bloom': 30}}      # hint: a classic cheat code -> mega bloom (UP/DOWN/LEFT/RIGHT)
LOOK = {'S': (0.33, 1, 1), 'L': (0.33, 1, 1),         # the plant is one green: stem, leaves
        'B': (0.33, 1, 1), 'F': (BLOOM_HUE, 1, 1)}         # and buds; blooms use BLOOM_HUE (hue, saturation, value)
RAIN, CLOUD, DEAD = (40, 120, 255), (90, 90, 105), (120, 70, 20)     # drop, cloud, withered cell
CENTRE = (255, 190, 40)       # yellow middle of a bloom
STARS = ((0, 7), (3, 6), (5, 7), (6, 5))
SUN = ((6, 6), (7, 6), (6, 7), (7, 7))                  # 2x2 sun, top right
CLOUDS = (((0, 0, .8), (1, 0, 1), (2, 0, 1), (3, 0, .8), (1, 1, .9), (2, 1, .9)),   # (dx, dy, brightness)
          ((0, 0, .7), (1, 0, 1), (2, 0, .8), (1, 1, .8)),
          ((0, 1, .6), (1, 1, 1), (2, 1, .8), (1, 0, .9), (2, 0, 1), (3, 0, .6)))

m = LedMatrix(8, 8)
m.set_brightness(BRIGHTNESS)
fb = [0] * 192                # additive frame buffer (ints), same G,R,B order as m.buf

# --- helpers ------------------------------------------------------------------------------
def clamp(v, lo=0, hi=1):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, k):
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k)

def hsv(h, s, v):
    h = (h % 1) * 6
    i = int(h) % 6                                   # float32 can round h up to exactly 6
    f = h - int(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i]
    return (r * 255, g * 255, b * 255)

def put(fx, y, col, k=1.0):
    """Add colour*k into the frame buffer at fractional x (anti-aliased over two pixels)."""
    y = int(y + 0.5)
    x0 = int(fx + 8) - 8                             # floor
    f = fx - x0
    if 0 <= y < 8:
        r, g, b = col[0] * k, col[1] * k, col[2] * k
        for j in (0, 1):
            w = f if j else 1 - f
            if w > 0 and 0 <= x0 + j < 8:
                i = (y * 8 + x0 + j) * 3
                fb[i] += int(g * w)
                fb[i + 1] += int(r * w)
                fb[i + 2] += int(b * w)

def dot(x, y, col, k=1.0):
    """Add colour*k to one whole pixel (no anti-aliasing, so cheaper than put)."""
    if 0 <= x < 8 and 0 <= y < 8:
        i = (y * 8 + x) * 3
        fb[i] += int(col[1] * k)
        fb[i + 1] += int(col[0] * k)
        fb[i + 2] += int(col[2] * k)

# --- input --------------------------------------------------------------------------------
pins = {n: Pin(n, Pin.IN, Pin.PULL_UP) for n in (UP, DOWN, LEFT, RIGHT, CENTER, SWITCH)}
held = {n: False for n in KEYS}
changed = {n: 0 for n in KEYS}

def read_inputs(now):
    """Poll all pins. Returns (new presses as a string like 'LR', UP held, night)."""
    presses = ''
    for n, ch in KEYS.items():
        raw = not pins[n].value()
        if raw != held[n] and ticks_diff(now, changed[n]) >= 30:      # 30 ms debounce
            held[n], changed[n] = raw, now
            if raw:
                presses += ch
    return presses, held[UP], bool(pins[SWITCH].value()) != NIGHT_LOW

# --- sensor -------------------------------------------------------------------------------
adc = ADC(4)

def read_temp():
    v = sum(adc.read_u16() for _ in range(16)) / 16 * 3.3 / 65535
    return 27 - (v - 0.706) / 0.001721

class Thermo:
    """Low-passed chip temperature relative to the start-up baseline (first ~2 s)."""
    def __init__(self):
        self.t = self.base = read_temp()
        self.n = 0

    def update(self):                    # call ~2x per second, returns 0..1
        x = read_temp()
        if self.n < 4:
            self.n += 1
            self.base += (x - self.base) / self.n
            self.t = self.base
        else:
            self.t += (x - self.t) * 0.25
            self.base += (self.t - self.base) * 0.003    # very slow drift: room temperature changes
        return clamp((self.t - self.base) / WARM_RANGE)

# --- world --------------------------------------------------------------------------------
class Garden:
    def __init__(self):
        self.cells = [[3, 0, 'S', 0.0]]              # [x, y, kind, wither]; cells[0] is the base
        self.water, self.warmth, self.lean, self.wind = 1.0, WARM_FLOOR, 0.0, 0.0
        self.clouds, self.drops = [], []             # clouds [x, y, speed], drops [x, y]
        self.night, self.energy, self.dry = False, 0.0, 0
        self.clear = False                           # a bloom is open: the sky clears
        self.rain_acc, self.hist = 0.0, ''
        self.rain_t, self.next_t, self.full_t, self.pruning = 0.0, 5.0, 0.0, False    # autopilot state
        self.fx = {'rainbow': 0, 'sun': 0, 'bloom': 0, 'cut': 0}    # effect timers in seconds

    def side(self):                                  # -1 or +1, biased by accumulated wind
        return 1 if random.random() < 0.5 + self.lean * 0.4 else -1

    def tops(self, kinds):                           # cells of these kinds with nothing directly above
        occ = {(c[0], c[1]) for c in self.cells}
        return [c for c in self.cells if c[2] in kinds and (c[0], c[1] + 1) not in occ]

    def covers(self, c):                             # does cloud c reach the sun (columns 6-7)?
        return 2 < c[0] < 8

    def room(self, c):                               # blooms keep a one-pixel gap, so the heads never melt into red
        return not any(o[2] == 'F' and o is not c and abs(o[0] - c[0]) < 4 and abs(o[1] - c[1]) < 4 for o in self.cells)

    def open_blooms(self, cells):                    # tallest first; low tips keep a green base under the head
        for c in sorted(cells, key=lambda c: -c[1]):
            if c[1] >= BUD_MIN_Y and self.room(c):
                c[2] = 'F'

    def grow(self):
        """Add one cell at a random tip (leaf 18 %, else stem). Stems and leaves never fill gaps."""
        tips = self.tops('SBF')
        if not tips or len(self.cells) >= MAX_CELLS:
            return False
        occ = {(c[0], c[1]) for c in self.cells}
        ends = [c for c in tips if (c[0] - 1, c[1] + 1) not in occ and (c[0] + 1, c[1] + 1) not in occ]
        for _ in range(4):                           # a few tries, so one bad pick does not waste the tick
            tip = random.choice(ends if ends and random.random() < 0.9 else tips)    # forks are rare
            if random.random() < 0.18:
                x, y, kind = tip[0] + self.side(), tip[1], 'L'
            else:
                x, y, kind = tip[0] + (0 if random.random() < 0.55 else self.side()), tip[1] + 1, 'S'
            if not (0 <= x < 8 and y <= TOP) or (x, y) in occ:
                continue
            if kind == 'L':
                if (2 * x - tip[0], y) in occ:
                    continue                         # a leaf only hangs off a stem, never fills a gap between two
            else:
                if (x - 1, y) in occ or (x + 1, y) in occ:
                    continue                         # a stem never hugs another one: that looks like a tree
                tip[2] = 'S'                         # a bud/bloom makes way for new growth
            self.cells.append([x, y, kind, 0.0])
            return True
        return False

    def tick(self):
        """One growth step: light, water, growth, buds, blooms, drought, clouds."""
        day = not self.night
        light = 0.15 if self.night else max(0.2, 1 - 0.25 * sum(self.covers(c) for c in self.clouds))
        warm = 1.0 if day and self.fx['bloom'] > 0 else self.warmth
        self.lean *= 0.995
        self.water = clamp(self.water - DRAIN * (1 + self.warmth), 0, 2)
        self.energy = min(self.energy + (self.warmth * 0.6 + light * 0.4) * min(self.water * 1.4, 1) * 0.5, 3)
        if self.energy > 1 and self.grow():
            self.energy -= 1
            self.water = max(0, self.water - GROW_COST)
        if day and warm > BUD_WARMTH and not self.fx['cut']:    # a freshly cut tip rests before it buds again
            for c in self.tops('S'):
                if c[1] >= BUD_MIN_Y and random.random() < BUD_CHANCE:
                    c[2] = 'B'
        for c in self.cells:
            if c[2] == 'B' and day and warm > OPEN_WARMTH and random.random() < OPEN_CHANCE and self.room(c):
                c[2] = 'F'
            elif c[2] == 'F' and (not day or warm < CLOSE_WARMTH):
                c[2] = 'B'
        self.dry = self.dry + 1 if self.water < 0.12 else 0
        if self.dry > 6:                             # drought: tips wither away, base survives
            cand = [c for c in self.tops('SLBF') if c is not self.cells[0]]
            if cand:
                c = random.choice(cand)
                c[3] += WITHER
                if c[3] > 1:
                    self.cells.remove(c)
        elif self.water > 0.3:
            for c in self.cells:
                c[3] = max(0, c[3] - 0.05)           # watered cells recover
        self.clear = any(c[2] == 'F' for c in self.cells)
        if not self.clear and len(self.clouds) < 4 and random.random() < 0.04:
            v = (0.3 + random.random() * 0.4) * random.choice((-1, 1))
            self.clouds.append([-4.0 if v > 0 else 8.0, 6, v, random.randrange(len(CLOUDS))])

    def press(self, ch):
        """Single-press actions, then check the cheat history."""
        if ch in 'LR':
            d = -1 if ch == 'L' else 1
            self.wind, self.lean = d, clamp(self.lean + WIND_LEAN * d, -1, 1)
            for c in self.clouds:
                c[0] += d
        elif ch == 'C':
            self.energy += 1.5
            self.fx['sun'] = 0.4
            self.fx['bloom'] = max(self.fx['bloom'], SUN_BLOOM)    # sunshine warms it: buds and blooms
            if not self.night:
                self.open_blooms(self.tops('SBF'))   # sunshine opens the tall enough tips right away
        elif ch == 'D' and len(self.cells) > 1:
            self.cells.remove(max(self.cells[1:], key=lambda c: c[1]))
            self.fx['cut'] = 10
        self.hist = (self.hist + ch)[-10:]
        for seq, effects in CHEATS.items():
            if self.hist.endswith(seq):
                self.hist = ''
                self.fx.update(effects)              # start the timers
                if 'rainbow' in effects:             # Konami: every tip opens at once
                    self.open_blooms(self.tops('SBF'))

    def autopilot(self, dt):
        """Auto-mode: plays the controls by itself, so the garden grows, blooms and shrinks alone."""
        self.next_t -= dt
        n = len(self.cells)
        self.full_t = self.full_t + dt if any(c[1] >= TOP for c in self.cells) else 0
        if self.water < 0.4 and self.rain_t == 0:
            self.rain_t = 3                          # thirsty: let it rain
        if self.next_t > 0:
            return
        self.pruning = self.full_t > 40 or n > 34 or (self.pruning and n > 8)   # full grown for a while: cut back
        if self.pruning:
            self.next_t = 0.3
            self.press('D')
            return
        self.next_t = 5 + random.random() * 10
        r = random.random()
        if r < 0.08:                                 # now and then the cheat code
            seq = random.choice(list(CHEATS))
            self.hist = seq[:-1]
            self.press(seq[-1])
        else:
            self.press('C' if r < 0.5 else random.choice('LR'))    # sunshine (blooms) or a gust

    def step(self, dt, rain):
        """Per-frame motion: wind, clouds, rain, effect timers."""
        self.wind *= GUST_DECAY
        for c in self.clouds:
            c[0] += c[2] * dt * (4 if self.clear else 1)    # open blooms blow the clouds away
        self.clouds = [c for c in self.clouds if -4.1 < c[0] < 8.1]
        self.rain_t = max(0, self.rain_t - dt)
        period = RAIN_EVERY if rain or self.rain_t > 0 else 0
        self.rain_acc = self.rain_acc + dt if period else 0
        while period and self.rain_acc >= period:
            self.rain_acc -= period
            if len(self.drops) < 30:
                self.drops.append([random.randrange(8), 7.4])
        for d in self.drops:
            d[1] -= 9 * dt
        landed = len([d for d in self.drops if d[1] < 0.5])
        self.water = min(2, self.water + RAIN_WATER * landed)
        self.drops = [d for d in self.drops if d[1] >= 0.5]
        for k in self.fx:
            self.fx[k] = max(0, self.fx[k] - dt)

# --- render -------------------------------------------------------------------------------
def flower(px, y, col, v):
    """Bloom head: a 3x3 round of petals around one yellow centre pixel."""
    left, bottom = clamp(round(px) - 1, 0, 5), clamp(y - 1, 0, 5)
    petal = (int(col[1] * v * 0.8), int(col[0] * v * 0.8), int(col[2] * v * 0.8))   # G, R, B
    mid = (int(CENTRE[1] * v), int(CENTRE[0] * v), int(CENTRE[2] * v))
    for fy in range(3):
        for fx in range(3):
            i = ((bottom + fy) * 8 + left + fx) * 3
            fb[i], fb[i + 1], fb[i + 2] = mid if fx == 1 and fy == 1 else petal

def render(g, t):
    fx = g.fx
    night = g.night
    if night:
        for i, (x, y) in enumerate(STARS):
            put(x, y, (80, 80, 120), 0.5 + 0.5 * math.sin(t * 2 + i * 1.7))
    for c in g.clouds:                               # puffs, only in the top two rows
        for dx, dy, k in CLOUDS[c[3]]:
            dot(round(c[0]) + dx, c[1] + dy, CLOUD, k * (0.4 if night else 1))
    if not (night or any(g.covers(c) for c in g.clouds)):
        w = 1 if fx['bloom'] > 0 else g.warmth      # the sun glows hotter while sunshine keeps the plant warm
        sun, k = hsv(0.14 - 0.08 * w, 0.3 if fx['sun'] > 0 else 1, 1), 1 if fx['sun'] > 0 else 0.3 + 0.7 * w
        for x, y in SUN:
            dot(x, y, sun, k)
    for d in g.drops:
        put(d[0], d[1], RAIN)
    if g.water < 0.25 and int(t * 4) % 2 == 0:       # thirst: blinking blue dots by the stem
        for x in (g.cells[0][0] - 1, g.cells[0][0] + 1):
            put(x, 0, (30, 90, 255))
    glow = 0.55 + 0.45 * math.sin(t * 1.6) if night else 1
    sway = [(g.wind * WIND_SWAY + math.sin(t * 1.3 + y) * 0.12 * (1 + abs(g.wind))) * y / 6 for y in range(8)]
    cols = {k: hsv(h, s, v) for k, (h, s, v) in LOOK.items()}    # colours once per frame, not per cell
    rainbow = [hsv(y * 0.1 + t * 0.8, 1, 1) for y in range(8)] if fx['rainbow'] > 0 else None
    blooms = []
    for x, y, kind, wither in g.cells:
        col, v = cols[kind], glow
        if rainbow:
            col = rainbow[y]
        if kind == 'F':
            v *= 0.8 + 0.2 * math.sin(t * 3 + x)
        if wither:
            col = lerp(col, DEAD, wither)
        if kind == 'F':
            blooms.append((x + sway[y], y, col, v))
        else:
            put(x + sway[y], y, col, v)
    for b in blooms:                                 # heads last: stems and leaves never tint a petal
        flower(*b)
    buf = m.buf                                      # copy to the LEDs and clear fb for the next frame
    for i in range(192):
        v = fb[i]
        buf[i] = 255 if v > 255 else v
        fb[i] = 0
    m.apply()

# --- main loop ----------------------------------------------------------------------------
def main():
    random.seed()                                    # every plant is unique: seed from hardware randomness
    g, thermo = Garden(), Thermo()
    t0 = last = last_tick = last_temp = last_input = ticks_ms()
    raw, frames = 0.0, 0
    while True:
        now = ticks_ms()
        dt = ticks_diff(now, last) / 1000
        last = now
        presses, up, g.night = read_inputs(now)
        if presses or up:
            last_input = now                         # any joystick use ends auto-mode
        for ch in presses:
            g.press(ch)
        if AUTO_AFTER and ticks_diff(now, last_input) > AUTO_AFTER * 1000:
            g.autopilot(dt)
        if ticks_diff(now, last_temp) >= 500:
            last_temp, raw = now, thermo.update()
        g.warmth = raw if g.night else max(raw, WARM_FLOOR)
        if ticks_diff(now, last_tick) >= TICK_MS // TIME_LAPSE:
            last_tick = now
            g.tick()
        g.step(dt, up)
        render(g, ticks_diff(now, t0) / 1000)
        frames += 1
        if frames % 50 == 0:
            gc.collect()
        sleep_ms(max(1, FRAME_MS - ticks_diff(ticks_ms(), now)))

main()
