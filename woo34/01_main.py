# Lumatrix Games 2026 - Falling tiles game arcade vibes 
# by Di Rienzo Alessandro (discord: woo34 / AleWoo345)
# Flip the switch to play: hit the falling notes with the joystick in the matching lane 
# Streaks speed the game up and shrink the hit zone 
# 4 errors end the run, and the best scores are saved with a 3-letter name
# hold joystick to the right while in standby mode to enter score table menu

# Key features of code implemented:
#  1. Joystick via IRQ handlers + debounce: handlers only raise a flag that the game loop consumes, so no press is los.
#  2. Software PWM: an LED 8-bit value is its duty cycle, modulating it gives smooth motion: trails, breathing, pulses
#  3. Effects are additive layers drawn into one canvas and sent with "single apply()" per frame
#  4. Hit detection uses the same continuous position the note is drawn at (row + progress): a hit counts when you see it
#  5. Difficulty is table-driven (LEVEL_* constants): speed, hit rows and error recovery for each streak level
#  6. Non-blocking timing with ticks_ms/ticks_diff; the leaderboard lives in flash (scores.txt) and survives power-off
#  7. It is not possible deleting the scores via the game, this persistence is meant to give an "arcade" feel to the game
#     same names entries in the score table is permitted, for giving the same "vintage" feel as point in 7.

import gc
import math
import random
from time import sleep_ms, ticks_diff, ticks_ms

from zhaw_led_matrix import Button, CharacterTable, ColorTable, LedMatrix

# =================================================================================================
# GAME PARAMETERS
# =================================================================================================

# --- Hardware and display ------------------------------------------------------------------------
MATRIX_Y0_IS_TOP = False   # True if row y=0 of the matrix is the TOP row on your board (notes would rise)
SIZE = 8                   # the matrix is SIZE x SIZE pixels
BRIGHTNESS = 30            # global LED brightness, 0-100
FRAME_MS = 33              # delay per frame (~30 fps)
DEBOUNCE_MS = 40           # joystick presses closer than this are treated as contact bounce

# --- Lanes and notes -----------------------------------------------------------------------------
LANES_X = (2, 3, 4, 5)     # columns of the lanes: left, up, down, right
LANE_COLORS = (ColorTable.BLUE, ColorTable.LIME, ColorTable.ORANGE, ColorTable.PINK)
SPAWN_EVERY = 2            # a new note every N steps
STRICT_PRESS = True        # True: pressing a direction with no note in the zone counts as an error
HIT_LEAD = 0.5             # rows of anticipation: a hit counts once the note's brightest pixel is in the zone
                           # (0 = only the logical row counts)

# --- Difficulty by streak level (streak = consecutive correct hits) one value per level ---------
STREAK_RESETS_ON_ERROR = True              # False: correct hits keep accumulating after an error
LEVEL_AT = (0, 10, 20)                      # minimum streak of each level: level 1 at 15, level 2 ten hits later
LEVEL_STEP_MS = (450, 380, 330)            # time for a note to fall one row
LEVEL_HIT_ROWS = ((6, 7), (6, 7), (7,))    # hit zone rows
LEVEL_ERROR_KEEP_ROWS = (2, SIZE, SIZE)    # on an error at this level only the top N rows keep their notes
                                           # (SIZE = clear nothing) gives the player time to recover

# --- Errors (lives) ------------------------------------------------------------------------------
LIFE_PIXELS = ((0, 0), (1, 0), (6, 0), (7, 0))   # (x, row) pixels at the top of the side columns, one per error
MAX_ERRORS = len(LIFE_PIXELS)                    # reaching this number of errors ends the run
LIFE_OK = (0, 120, 0)                            # pixel not yet used
LIFE_LOST = (255, 0, 0)                          # pixel used up by an error
GAME_OVER_HOLD_MS = 600                          # pause on the last frame so the 4th error is visible

# --- Streak visuals ------------------------------------------------------------------------------
STREAK_COLOR = (0, 255, 255)
LEVEL_STREAK_BASE = (0.0, 0.55, 0.70)      # resting duty of the streak columns for each level
PULSE_MS = 380                             # streak column pulse after a correct hit
RIPPLE_MS = 30                             # per-row delay: the pulse climbs from the bottom
LEVELUP_MS = 500                           # light sweep when reaching a new level
LEVELUP_COLOR = (150, 255, 255)

# --- Game effects --------------------------------------------------------------------------------
TRAIL = (1.0, 0.30, 0.10)                  # brightness of a note and of its trail pixels
BURST_MS = 300                             # burst on a correct hit
ERROR_FLASH_MS = 300                       # red flash over the lanes after an error

# --- Standby screen ------------------------------------------------------------------------------
WAVE_COLORS = (                            # equalizer gradient, bottom to top
    (0, 40, 255),
    (0, 90, 255),
    (0, 160, 255),
    (0, 220, 220),
    (0, 255, 150),
    (80, 255, 60),
    (200, 255, 0),
    (255, 200, 0),
)
BREATH_PERIOD_MS = 4000                    # period of the wave's slow breathing
BREATH_MIN, BREATH_MAX = 0.55, 1.0         # minimum and maximum duty of the breathing
HOLD_MS = 2000                             # hold the joystick right this long to open the leaderboard

# --- Tutorial ------------------------------------------------------------------------------------
SHOW_TUTORIAL = True                       # False: the game starts right after the wipe
TUTORIAL_ARROW_MS = 1000                   # how long each direction arrow is shown
TUTORIAL_PULSE_MS = 500                    # pulse period (two beats per arrow)

# --- Scores and name entry -----------------------------------------------------------------------
SCORES_FILE = "scores.txt"                 # stored in the Pico's flash, next to main.py
MAX_SCORES = 5                             # only the best N scores make it into the leaderboard
NAME_TIMEOUT_MS = 30000                    # idle time in name entry before the name is discarded
ENTRY_GRACE_MS = 500                       # ignore buttons still held from the game at the start of name entry
REPEAT_DELAY_MS = 450                      # holding up/down: wait this long before letters start scrolling
REPEAT_MS = 130                            # one letter every REPEAT_MS
SLIDE_MS = 140                             # vertical slide when the letter changes
SCROLL_SPEED = 18                          # scrolling text speed, in columns per second
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"     # letters available for the name
GLYPH_RIGHT_SHIFT = False                  # 5-px letters cannot be centred on 8 columns: False leaves the extra
                                           # blank column on the right, True moves it to the left
RANK_COLORS = (                            # gold, silver, bronze, then water aqua colour
    (255, 190, 0),
    (190, 205, 230),
    (205, 115, 40),
    (0, 200, 200),
    (0, 200, 200),
)

# --- Internal state ids (don't change) ---------------------------------------------------------
STANDBY, GAME = 0, 1


# =================================================================================================
# DRAWING AND TIMING HELPERS
# =================================================================================================
def put(m, x, y, color):
    """Write one pixel. y=0 is always the TOP row here, whatever the hardware orientation."""
    if not MATRIX_Y0_IS_TOP:
        y = SIZE - 1 - y
    m[x, y] = color


def duty_wave(t_ms, period_ms, lo, hi):
    """Sinusoidal duty cycle oscillating between lo and hi with period period_ms."""
    phase = (t_ms % period_ms) / period_ms
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(2 * math.pi * phase))


def with_duty(color, duty):
    """Scale a color by a duty 0..1. Gamma ~2 (duty^2): the eye is not linear, so the
    perceived brightness follows the duty."""
    k = duty * duty
    return (int(color[0] * k), int(color[1] * k), int(color[2] * k))


def dim(color, factor):
    """Linear scaling (use for crossfades, where light adds up)."""
    return (
        int(color[0] * factor),
        int(color[1] * factor),
        int(color[2] * factor),
    )


# =================================================================================================
# JOYSTICK
# =================================================================================================
# Presses arrive from interrupts (falling edge). The handler is minimal: it only raises a flag per
# lane, which the game loop consumes -> This way no short press is lost even if a frame is busy
pending = [False, False, False, False]        # lanes: 0 left, 1 up, 2 down, 3 right
_last_press = [-1000, -1000, -1000, -1000]


def _make_handler(lane):
    def handler(pin):
        now = ticks_ms()
        if ticks_diff(now, _last_press[lane]) > DEBOUNCE_MS:
            _last_press[lane] = now
            pending[lane] = True

    return handler


def setup_joystick():
    buttons = Button()
    buttons.set_left_handler(_make_handler(0))
    buttons.set_up_handler(_make_handler(1))
    buttons.set_down_handler(_make_handler(2))
    buttons.set_right_handler(_make_handler(3))
    return buttons


# =================================================================================================
# TRANSITION AND STANDBY
# =================================================================================================
def transition(m, color=ColorTable.WHITE):
    """Wipe: fills the matrix left to right, then empties it in the same direction."""
    c = dim(color, 0.6)
    for x in range(SIZE):
        for y in range(SIZE):
            m[x, y] = c
        m.apply()
        sleep_ms(35)
    for x in range(SIZE):
        for y in range(SIZE):
            m[x, y] = ColorTable.BLACK
        m.apply()
        sleep_ms(35)


def draw_standby(m, t, charge=0.0):
    """Equalizer-like wave: sum of two sines per column, with PWM.
    `charge` (0..1) is how long the joystick has been held right: the wave dims and a ring
    fills along the border."""
    m.clear()
    breath = duty_wave(t, BREATH_PERIOD_MS, BREATH_MIN, BREATH_MAX) * (1 - 0.5 * charge)
    for x in range(SIZE):
        v = 0.6 * math.sin(t * 0.004 + x * 0.7) + 0.4 * math.sin(t * 0.0027 + x * 1.3)
        height = 0.5 + (0.5 + 0.5 * v) * (SIZE - 0.5)   # 0.5..8.0 not rounded
        full = int(height)
        for r in range(full):                            # r = 0 is the bottom
            put(m, x, SIZE - 1 - r, with_duty(WAVE_COLORS[r], breath))
        if full < SIZE:                                  # partial pixel on top of the bar
            frac = height - full                         # 0..1 duty of that pixel
            put(m, x, SIZE - 1 - full, with_duty(WAVE_COLORS[full], breath * frac))
    if charge > 0:
        draw_charge(m, charge, t)
    m.apply()


# =================================================================================================
# TUTORIAL
# =================================================================================================
# A single arrow (up) drawn by hand; the other three are obtained by rotating it.
_ARROW_UP = (
    "...XX...",
    "..XXXX..",
    ".XXXXXX.",
    "XXXXXXXX",
    "...XX...",
    "...XX...",
    "...XX...",
    "...XX...",
)


def _arrow_pixels(direction):
    pts = []
    for y in range(SIZE):
        for x in range(SIZE):
            if _ARROW_UP[y][x] != "X":
                continue
            if direction == "up":
                pts.append((x, y))
            elif direction == "down":
                pts.append((x, SIZE - 1 - y))
            elif direction == "left":
                pts.append((y, SIZE - 1 - x))
            else:                                   # right
                pts.append((SIZE - 1 - y, x))
    return pts


# same order as the lanes: left, up, down, right
ARROWS = (
    _arrow_pixels("left"),
    _arrow_pixels("up"),
    _arrow_pixels("down"),
    _arrow_pixels("right"),
)


def tutorial(m):
    """Show the 4 directions in turn, each pulsing for TUTORIAL_ARROW_MS.
    Each arrow has its lane's color, so the player links direction and color before playing."""
    for lane in range(4):
        start = ticks_ms()
        while True:
            age = ticks_diff(ticks_ms(), start)
            if age >= TUTORIAL_ARROW_MS:
                break
            # the pulse starts at its minimum (+3/4 period) so every arrow fades in from and out to dark
            duty = duty_wave(age + TUTORIAL_PULSE_MS * 3 // 4, TUTORIAL_PULSE_MS, 0.05, 1.0)
            color = with_duty(LANE_COLORS[lane], duty)
            m.clear()
            for x, y in ARROWS[lane]:
                put(m, x, y, color)
            m.apply()
            sleep_ms(FRAME_MS)


# =================================================================================================
# EFFECTS CANVAS
# =================================================================================================
# VISUALIZING CONCEPT:
# A game frame is composed in an additive canvas: every effect "adds" light to the pixels, then
# _flush() saturates at 255 and sends everything with a single apply()
_canvas = [0] * (SIZE * SIZE * 3)


def _age(now, t0):
    """Milliseconds since t0 (None = effect never started -> very old)."""
    return 100000 if t0 is None else ticks_diff(now, t0)


def _fade(age, duration):
    """Duty falling linearly from 1 to 0 over `duration` ms (0 before and after)."""
    if age < 0 or age >= duration:
        return 0.0
    return 1.0 - age / duration


def _add(x, row, color):
    """Add light to pixel (x, row). Out-of-matrix coordinates are ignored."""
    if x < 0 or x >= SIZE or row < 0 or row >= SIZE:
        return
    i = (row * SIZE + x) * 3
    _canvas[i] += color[0]
    _canvas[i + 1] += color[1]
    _canvas[i + 2] += color[2]


def _flush(m):
    i = 0
    for row in range(SIZE):
        for x in range(SIZE):
            r, g, b = _canvas[i], _canvas[i + 1], _canvas[i + 2]
            put(m, x, row, (255 if r > 255 else r, 255 if g > 255 else g, 255 if b > 255 else b))
            _canvas[i] = _canvas[i + 1] = _canvas[i + 2] = 0
            i += 3
    m.apply()


# =================================================================================================
# GAME
# =================================================================================================
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        now = ticks_ms()
        self.now = now
        self.notes = []          # list of [lane, row]
        self.last_step = now
        self.step_count = 0
        self.last_lane = -1
        self.score = 0
        self.errors = 0
        self.streak = 0
        # effects: start times (None = never)
        self.bursts = []         # (x, row, t0, lane)
        self.pulse_t0 = None
        self.err_t0 = None
        self.levelup_t0 = None
        for i in range(4):       # drop presses made outside the game
            pending[i] = False
        self._spawn()            # first note right away, so the game starts without waiting

    def _level(self):
        """Current level (0, 1, 2), derived from the streak."""
        level = 0
        for i in range(len(LEVEL_AT)):
            if self.streak >= LEVEL_AT[i]:
                level = i
        return level

    def _error(self):
        keep_rows = LEVEL_ERROR_KEEP_ROWS[self._level()]   # level BEFORE the streak is reset
        self.errors += 1
        self.err_t0 = self.now
        if STREAK_RESETS_ON_ERROR:
            self.streak = 0
        # breathing room: only the notes in the top "keep_rows" rows survive
        self.notes = [n for n in self.notes if n[1] < keep_rows]

    def _spawn(self):
        lane = random.randint(0, 3)
        if lane == self.last_lane:      # never the same lane twice in a row
            lane = (lane + random.randint(1, 3)) % 4
        self.last_lane = lane
        self.notes.append([lane, 0])

    def _hit(self, lane):
        """Hit the lowest note of the lane inside the zone. Returns False if there is none.

        A note is DRAWN at the continuous position row + p (it slides toward the next row),
        so the hit is evaluated on that same position: it counts exactly when you see the
        note's brightest pixel inside the hit zone."""
        zone_top = min(LEVEL_HIT_ROWS[self._level()]) - HIT_LEAD
        p = self._progress()
        best = None
        for n in self.notes:
            if n[0] == lane and n[1] + p >= zone_top and (best is None or n[1] > best[1]):
                best = n
        if best is None:
            return False
        self.notes.remove(best)
        self.score += 1
        old_level = self._level()
        self.streak += 1
        # effects of a correct hit: burst, column pulse, and a sweep if the level went up
        self.bursts.append((LANES_X[lane], best[1], self.now, lane))
        self.pulse_t0 = self.now
        if self._level() > old_level:
            self.levelup_t0 = self.now
        return True

    def update(self, now):
        """Advance the game. Returns False when the errors reach MAX_ERRORS."""
        self.now = now
        self.bursts = [b for b in self.bursts if ticks_diff(now, b[2]) < BURST_MS]
        # 1) input first, so a key pressed in the same frame still counts
        for lane in range(4):
            if pending[lane]:
                pending[lane] = False
                if not self._hit(lane) and STRICT_PRESS:
                    self._error()                       # key with no note = error
        # 2) advance in fixed steps
        if self.errors < MAX_ERRORS and ticks_diff(now, self.last_step) >= LEVEL_STEP_MS[self._level()]:
            self.last_step = now
            self.step_count += 1
            alive = []
            missed = 0
            for n in self.notes:
                n[1] += 1
                if n[1] >= SIZE:                        # note fell off the bottom = error
                    missed += 1
                else:
                    alive.append(n)
            self.notes = alive
            for _ in range(missed):
                self._error()
            if self.step_count % SPAWN_EVERY == 0:
                self._spawn()
        return self.errors < MAX_ERRORS

    def _progress(self):
        """Progress (0..1) inside the current step: drives the smooth motion."""
        p = ticks_diff(self.now, self.last_step) / LEVEL_STEP_MS[self._level()]
        return 1.0 if p > 1.0 else (0.0 if p < 0.0 else p)

    def _draw_note(self, lane, row, p):
        """A note sliding from `row` to `row + 1` via a duty crossfade between two pixels.
        The trail is interpolated the same way, so nothing ever jumps."""
        x, color = LANES_X[lane], LANE_COLORS[lane]
        for k in range(len(TRAIL) + 1):
            w = 0.0
            if k < len(TRAIL):
                w += p * TRAIL[k]
            if k > 0:
                w += (1 - p) * TRAIL[k - 1]
            if w > 0:
                _add(x, row + 1 - k, dim(color, w))

    def draw(self, m):
        now, level, p = self.now, self._level(), self._progress()

        # 1) red flash over the lanes after an error
        k = _fade(_age(now, self.err_t0), ERROR_FLASH_MS)
        if k > 0:
            red = with_duty((255, 0, 0), 0.5 * k)
            for x in LANES_X:
                for y in range(SIZE):
                    _add(x, y, red)

        # 2) hit zone: lanes faintly lit to guide the eye
        for lane, x in enumerate(LANES_X):
            for y in LEVEL_HIT_ROWS[level]:
                _add(x, y, dim(LANE_COLORS[lane], 0.12))

        # 3) notes with smooth motion and a trail
        for lane, row in self.notes:
            self._draw_note(lane, row, p)

        # 4) burst on a correct hit: white core, then an expanding ring
        for x, row, t0, lane in self.bursts:
            age = ticks_diff(now, t0)
            core = _fade(age, 160)
            if core > 0:
                _add(x, row, with_duty(ColorTable.WHITE, core))
            ring = _fade(age - 60, BURST_MS - 60)
            if ring > 0:
                c = with_duty(LANE_COLORS[lane], ring)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    _add(x + dx, row + dy, c)

        # 5) streak columns: resting duty + a pulse climbing from the bottom on every correct hit
        if level >= 1:
            base = LEVEL_STREAK_BASE[level]
            pulse_age = _age(now, self.pulse_t0)
            for y in range(1, SIZE):                     # row 0 is the lives pixel
                delay = (SIZE - 1 - y) * RIPPLE_MS
                duty = base + (1 - base) * _fade(pulse_age - delay, PULSE_MS)
                c = with_duty(STREAK_COLOR, duty)
                for x in (0, 7):                  
                    _add(x, y, c)
                if level >= 2:
                    for x in (1, 6):
                        _add(x, y, c)

        # 6) light sweep across the matrix when a new level is reached
        age = _age(now, self.levelup_t0)
        if 0 <= age < LEVELUP_MS:
            centre = (SIZE - 1) * (1 - age / LEVELUP_MS)     # from bottom to top
            for y in range(SIZE):
                d = 1 - abs(y - centre) / 1.5
                if d > 0:
                    c = with_duty(LEVELUP_COLOR, d)
                    for x in range(SIZE):
                        _add(x, y, c)

        # 7) lives pixels (always at the top of the side columns)
        for i, (x, y) in enumerate(LIFE_PIXELS):
            _add(x, y, LIFE_LOST if i < self.errors else LIFE_OK)

        _flush(m)


# =================================================================================================
# SCORES (persistent, stored in flash)
# =================================================================================================
def load_scores():
    """Read the leaderboard from flash: list of (name, score), best first."""
    scores = []
    try:
        with open(SCORES_FILE) as f:
            for line in f:
                name, _, value = line.strip().partition(",")
                if len(name) == 3 and value.isdigit():
                    scores.append((name, int(value)))
    except OSError:
        pass                                   # first run: the file does not exist yet
    scores.sort(key=lambda e: -e[1])           # stable sort: on ties the earlier entry stays first
    return scores[:MAX_SCORES]


def qualifies(score, scores):
    return score > 0 and (len(scores) < MAX_SCORES or score > scores[-1][1])


def add_score(name, score):
    """Insert the score and save it to flash. Returns (rank, leaderboard)."""
    scores = load_scores()
    rank = 1
    for _, value in scores:
        if value >= score:                     # on a tie the new entry ranks below
            rank += 1
    scores.append((name, score))
    scores.sort(key=lambda e: -e[1])
    scores = scores[:MAX_SCORES]
    try:
        with open(SCORES_FILE, "w") as f:
            for n, v in scores:
                f.write("%s,%d\n" % (n, v))
    except OSError:
        print("could not save the leaderboard")
    return rank, scores


# =================================================================================================
# TEXT AND INPUT HELPERS
# =================================================================================================
EDGE = (0.35, 0.7, 1, 1, 1, 1, 0.7, 0.35)      # scrolling text fades toward the matrix edges


def wheel(pos):
    """Rainbow color: pos 0..255 walks around the whole color wheel."""
    pos %= 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def put_glyph(m, ch, x0, y0, color):
    """Draw a character of the library font (7 rows, y pointing up) through put(), so it stays
    upright whatever MATRIX_Y0_IS_TOP is. y0 = vertical offset."""
    for gx, gy in CharacterTable.CHAR_MAPPING[ch]:
        x, y = gx + x0, gy + y0
        if 0 <= x < SIZE and 0 <= y < 7:
            put(m, x, SIZE - 1 - y, color)


def glyph_x(ch):
    """Left column that centres a character. Odd-width glyphs cannot be centred exactly on
    an even number of columns: GLYPH_RIGHT_SHIFT picks which side gets the extra blank column."""
    width = CharacterTable.CHAR_MAPPING[ch].width
    return (SIZE - width + (1 if GLYPH_RIGHT_SHIFT else 0)) // 2


def clear_pending():
    for i in range(4):
        pending[i] = False


def any_press():
    for i in range(4):
        if pending[i]:
            return True
    return False


def scroll(m, text, color, speed=SCROLL_SPEED, skippable=False):
    """Text scrolling right to left. Returns True if the user skipped it with a button."""
    chars, length = CharacterTable.convert_str(text)
    pts = []
    for ch in chars:
        for point in ch:
            pts.append(point)
    clear_pending()
    start = ticks_ms()
    frame = 0
    while True:
        age = ticks_diff(ticks_ms(), start)
        shift = SIZE - age * speed // 1000       # starts just outside on the right
        if shift < -length:
            return False
        if skippable and age > 300 and any_press():
            clear_pending()
            return True
        m.clear()
        for gx, gy in pts:
            x = gx + shift
            if 0 <= x < SIZE:
                put(m, x, SIZE - 1 - gy, dim(color, EDGE[x]))
        m.apply()
        frame += 1
        if frame % 30 == 0:
            gc.collect()
        sleep_ms(FRAME_MS)


def flash_screen(m, color, ms=300):
    start = ticks_ms()
    while True:
        age = ticks_diff(ticks_ms(), start)
        if age >= ms:
            return
        m.fill(with_duty(color, 1 - age / ms))
        m.apply()
        sleep_ms(FRAME_MS)


def shine_color(base, s):
    """Add a white highlight (s = 0..1) to a color."""
    return (min(255, base[0] + int(200 * s)), min(255, base[1] + int(200 * s)),
            min(255, base[2] + int(200 * s)))


# =================================================================================================
# CHARGE RING (hold the joystick right in standby)
# =================================================================================================
def _ring_pixels():
    """The 28 border pixels in clockwise order, starting from the top-left corner."""
    pts = [(x, 0) for x in range(SIZE)]
    pts += [(SIZE - 1, y) for y in range(1, SIZE)]
    pts += [(x, SIZE - 1) for x in range(SIZE - 2, -1, -1)]
    pts += [(0, y) for y in range(SIZE - 2, 0, -1)]
    return pts


RING = _ring_pixels()


def draw_charge(m, charge, t):
    """Ring that fills while you hold: the last pixel is partial (duty), so the charge advances
    smoothly. Gold turning white, pulsing when almost full."""
    n = charge * len(RING)
    full = int(n)
    color = (255, 190 + int(65 * charge), int(255 * charge * charge))
    if charge > 0.85:
        color = with_duty(color, duty_wave(t, 160, 0.5, 1.0))
    for i in range(full):
        x, y = RING[i]
        put(m, x, y, color)
    if full < len(RING):
        x, y = RING[full]
        put(m, x, y, with_duty(color, n - full))


# =================================================================================================
# NAME ENTRY
# =================================================================================================
SEGMENTS = ((0, 1), (3, 4), (6, 7))            # 3 dashes on top: which letter you are choosing


class NameEntry:
    """Arcade-style 3-letter name, one letter per screen."""

    def __init__(self):
        now = ticks_ms()
        self.letters = [0, 0, 0]               # indexes into LETTERS
        self.pos = 0
        self.t0 = now
        self.last_input = now
        self.pop_t0 = now                      # fade-in of the current letter
        self.slide_t0 = None                   # vertical slide when the letter changes
        self.slide_dir = 1
        self.old = 0
        self.hold_dir = 0                      # up/down held down (auto-repeat)
        self.rep_ref = now
        self.rep_wait = REPEAT_DELAY_MS
        clear_pending()

    def name(self):
        return "".join([LETTERS[i] for i in self.letters])

    def _step(self, delta, now):
        self.old = self.letters[self.pos]
        self.letters[self.pos] = (self.old + delta) % len(LETTERS)
        self.slide_dir = delta
        self.slide_t0 = now
        self.last_input = now

    def update(self, now):
        """Returns "done" (name confirmed), "timeout" or None."""
        if ticks_diff(now, self.t0) < ENTRY_GRACE_MS:
            clear_pending()                    # ignore buttons still held from the game
            return None
        for lane, delta in ((1, 1), (2, -1)):  # up = next letter, down = previous letter
            if pending[lane]:
                pending[lane] = False
                self._step(delta, now)
                self.hold_dir, self.rep_ref, self.rep_wait = delta, now, REPEAT_DELAY_MS
        if pending[0]:                         # left: back to the previous letter
            pending[0] = False
            self.last_input = now
            if self.pos > 0:
                self.pos -= 1
                self.pop_t0 = now
        if pending[3]:                         # right: next letter, confirm on the third
            pending[3] = False
            self.last_input = now
            if self.pos == 2:
                return "done"
            self.pos += 1
            self.pop_t0 = now
        # auto-repeat: while up/down stay pressed the letters scroll by themselves
        held = 1 if Button.up.value() == 0 else (-1 if Button.down.value() == 0 else 0)
        if held == 0:
            self.hold_dir = 0
        elif held != self.hold_dir:
            self.hold_dir, self.rep_ref, self.rep_wait = held, now, REPEAT_DELAY_MS
        elif ticks_diff(now, self.rep_ref) >= self.rep_wait:
            self._step(held, now)
            self.rep_ref, self.rep_wait = now, REPEAT_MS
        if ticks_diff(now, self.last_input) > NAME_TIMEOUT_MS:
            return "timeout"
        return None

    def draw(self, m, now):
        m.clear()
        color = wheel(now // 10 + self.pos * 40)             # slow rainbow
        ch = LETTERS[self.letters[self.pos]]
        pop = min(1.0, ticks_diff(now, self.pop_t0) / 220)   # the letter fades in
        c = dim(color, pop * (0.85 + 0.15 * math.sin(now * 0.008)))
        age = _age(now, self.slide_t0)
        if age < SLIDE_MS:
            # the old letter leaves and the new one enters, in the joystick's direction
            q = age / SLIDE_MS
            d = self.slide_dir
            old = LETTERS[self.old]
            put_glyph(m, old, glyph_x(old), round(q * 7) * d, c)
            put_glyph(m, ch, glyph_x(ch), round((q - 1) * 7) * d, c)
        else:
            put_glyph(m, ch, glyph_x(ch), 0, c)
        for k in range(3):                                   # progress: done / current / upcoming
            if k < self.pos:
                sc = dim(wheel(now // 10 + k * 40), 0.6)
            elif k == self.pos:
                sc = with_duty(color, duty_wave(now, 500, 0.3, 1.0))
            else:
                sc = dim(color, 0.08)
            for x in SEGMENTS[k]:
                put(m, x, 0, sc)
        m.apply()


def run_name_entry(m):
    """Returns the entered name, or None if the player walked away."""
    entry = NameEntry()
    frame = 0
    while True:
        now = ticks_ms()
        result = entry.update(now)
        if result == "done":
            return entry.name()
        if result == "timeout":
            return None
        entry.draw(m, now)
        frame += 1
        if frame % 30 == 0:
            gc.collect()
        sleep_ms(FRAME_MS)


def celebrate(m, rank, ms=2400):
    """After saving: rings expanding in the medal color, with the player's rank in the middle."""
    color = RANK_COLORS[rank - 1]
    digit = str(rank)
    start = ticks_ms()
    while True:
        age = ticks_diff(ticks_ms(), start)
        if age >= ms:
            return
        life = 1.0 if age < ms - 500 else (ms - age) / 500
        radius = (age % 700) / 700 * 5.5
        m.clear()
        for y in range(SIZE):
            for x in range(SIZE):
                d = max(abs(x - 3.5), abs(y - 3.5))
                v = 1 - abs(d - radius) / 1.2
                if v > 0:
                    put(m, x, y, with_duty(color, v * 0.9 * life))
        if age > 250:
            glow = duty_wave(age, 500, 0.6, 1.0) * life
            put_glyph(m, digit, glyph_x(digit), 0, with_duty((255, 255, 255), glow))
        m.apply()
        sleep_ms(FRAME_MS)


def finish_run(m, score):
    """End of a run: show the score and, if it makes the leaderboard, ask for a name and celebrate."""
    scores = load_scores()
    qualified = qualifies(score, scores)
    scroll(m, "SCORE %d" % score, RANK_COLORS[0] if qualified else RANK_COLORS[3],
           skippable=True)
    if not qualified:
        return
    scroll(m, "ENTER NAME", RANK_COLORS[0], skippable=True)
    name = run_name_entry(m)
    if name:
        rank, _ = add_score(name, score)
        celebrate(m, rank)


# =================================================================================================
# LEADERBOARD
# =================================================================================================
_TROPHY = (
    ".XXXXXX.",
    "XXXXXXXX",
    "X.XXXX.X",
    "X.XXXX.X",
    ".XXXXXX.",
    "..XXXX..",
    "...XX...",
    "..XXXX..",
)
TROPHY_PIXELS = tuple([(x, y) for y in range(SIZE) for x in range(SIZE) if _TROPHY[y][x] == "X"])


def _trophy(m, ms=1400):
    """The trophy lights up and a diagonal highlight sweeps across it. True = skipped."""
    clear_pending()
    start = ticks_ms()
    while True:
        age = ticks_diff(ticks_ms(), start)
        if age >= ms:
            return False
        if age > 300 and any_press():
            clear_pending()
            return True
        fade = age / 400 if age < 400 else 1.0
        shine_pos = (age - 350) * 18 / 800 - 2           # the x+y diagonal crosses the trophy
        m.clear()
        for x, y in TROPHY_PIXELS:
            s = 1 - abs((x + y) - shine_pos) / 2
            c = shine_color(dim(RANK_COLORS[0], fade * 0.85), s if s > 0 else 0)
            put(m, x, y, c)
        m.apply()
        sleep_ms(FRAME_MS)


def _show_rank(m, rank, ms=900):
    """The rank, large, with a highlight sweeping across it. True = skipped."""
    color = RANK_COLORS[rank - 1]
    digit = str(rank)
    clear_pending()
    start = ticks_ms()
    while True:
        age = ticks_diff(ticks_ms(), start)
        if age >= ms:
            return False
        if age > 300 and any_press():
            clear_pending()
            return True
        glow = duty_wave(age + 340, 450, 0.55, 1.0)
        shine_pos = age * 14 / ms - 2
        m.clear()
        for gx, gy in CharacterTable.CHAR_MAPPING[digit]:
            x, y = gx + glyph_x(digit), SIZE - 1 - gy
            s = 1 - abs((x + y) - shine_pos) / 2
            put(m, x, y, shine_color(with_duty(color, glow), s if s > 0 else 0))
        m.apply()
        sleep_ms(FRAME_MS)


def show_leaderboard(m):
    """Trophy, then for each rank: the number and a "NAME SCORE" text. Any button exits."""
    gc.collect()
    scores = load_scores()
    if _trophy(m):
        return
    if not scores:
        scroll(m, "NO SCORES", RANK_COLORS[3], skippable=True)
        return
    for i in range(len(scores)):
        name, value = scores[i]
        if _show_rank(m, i + 1):
            return
        if scroll(m, "%s %d" % (name, value), RANK_COLORS[i], skippable=True):
            return


# =================================================================================================
# MAIN LOOP
# =================================================================================================
def main():
    m = LedMatrix(SIZE, SIZE)
    m.set_brightness(BRIGHTNESS)
    setup_joystick()
    game = Game()

    mode = STANDBY
    # the switch is only a "go" signal: what counts is the change of position, not the position itself
    sw_stable = Button.switch.value()
    candidate, stable = sw_stable, 3
    charge = 0.0                         # charge for entering score menu
    armed = Button.right.value() == 1    # after each use the joystick must be released before recharging
    last_t = ticks_ms()
    frame = 0

    while True:
        now = ticks_ms()
        dt = ticks_diff(now, last_t)
        last_t = now
        if dt > 100:
            dt = 100

        # switch debounce: 3 consecutive identical frames
        raw = Button.switch.value()
        if raw == candidate:
            stable = min(stable + 1, 3)
        else:
            candidate, stable = raw, 0
        flipped = False
        if stable >= 3 and candidate != sw_stable:
            sw_stable = candidate
            flipped = True

        if mode == STANDBY and flipped:
            charge = 0.0
            transition(m)
            if SHOW_TUTORIAL:
                tutorial(m)
            game.reset()            # also drops any presses made during the tutorial
            mode = GAME
            now = ticks_ms()

        if mode == STANDBY:
            # hold the joystick right for menu
            right_down = Button.right.value() == 0
            if not right_down:
                armed = True
            if right_down and armed:
                charge += dt / HOLD_MS
            else:
                charge -= dt * 3 / HOLD_MS
            charge = 0.0 if charge < 0 else (1.0 if charge > 1 else charge)
            draw_standby(m, now, charge)
            if charge >= 1.0:
                charge, armed = 0.0, False
                flash_screen(m, RANK_COLORS[0])
                show_leaderboard(m)
                transition(m)
                sw_stable = Button.switch.value()       # ignore switch flips made in the meantime
                candidate, stable = sw_stable, 3
                last_t = ticks_ms()
        elif game.update(now):
            game.draw(m)
        else:
            game.draw(m)                    # last frame: shows the final error
            sleep_ms(GAME_OVER_HOLD_MS)
            print("Game over - score:", game.score)
            transition(m)
            finish_run(m, game.score)
            transition(m)
            mode, armed, charge = STANDBY, False, 0.0
            sw_stable = Button.switch.value()
            candidate, stable = sw_stable, 3
            last_t = ticks_ms()

        frame += 1
        if frame % 30 == 0:
            gc.collect()
        sleep_ms(FRAME_MS)


main()