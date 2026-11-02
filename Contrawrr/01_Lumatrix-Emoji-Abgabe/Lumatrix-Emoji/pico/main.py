#   .##..##.    Lumatrix Emoji (Pico side)
#   ########    A tiny AI on the Pico turns sung words into animated emojis.
#   ########
#   ########    The brain (wordmodel.py + model.bin, fast dot products in
#   .######.    fastdot.py) picks one of 107 animated emojis from icons.bin.
#   ..####..    Copy main.py, wordmodel.py, fastdot.py, riddle.py, font.py,
#   ...##...    model.bin and icons.bin onto the Pico.
#   ........
#
# Two modes; up/down switch between them (the mode's number shows first):
#   1 Emoji lyrics (with host/lumatrix_music.py on the laptop): the song's
#     cover, then an animated emoji for each important word, just before it
#     is sung; it stays until the next fitting word. Press = the song's
#     title scrolls by, left/right = previous/next song, double press =
#     play/pause.
#   2 Emoji-Rätsel (riddle.py): the brain turns a saying into emojis; you
#     guess. Press = answer, left/right = next/previous riddle, double press
#     = the brain's next guess, hold = "right, remember it", hold 3 s =
#     forget everything taught. Without a laptop it starts by itself.
#     Your own riddle: run main.py in Thonny and type a sentence in the
#     shell; the brain turns it into emojis for your friends to guess.
#
# Flip the toggle switch and up/down change the brightness instead
# (remembered). Cheat code: up up down down left right left right press.
#
# Messages are ASCII lines over the USB serial port:
#   laptop -> Pico   IMG <384 hex digits>   8x8 RGB cover, top row first
#                    PLAY 1 / PLAY 0        playing / paused
#                    VOL <0-100>            volume changed, show the level
#                    IDLE                   nothing playing
#                    TITLE <text>           the song's title, scrolls on a press
#                    WORD <word> [<next>]   a word being sung, and the word after
#                                           it; shows its emoji if the brain
#                                           finds one (a stop sign first for
#                                           "don't cry")
#                    NOICON                 back to the cover now
#   Pico -> laptop   HELLO lumatrix-music   sent once at start
#                    BTN <next|prev|playpause>
#                    CHEAT
#                    SAW <word> <emoji> <confidence %>   a word got an emoji
# Only ASCII is sent, so Thonny's Stop button (Ctrl+C) always works.
#
# Words: wordmodel.py and riddle.py call an emoji a "symbol"; EmojiZoo keeps
# the animated pictures as "icons".

import math
import random
import select
import struct
import sys
from binascii import unhexlify
from time import sleep_ms, ticks_add, ticks_diff, ticks_ms

from machine import Pin, bitstream

from font import FONT, SCROLL_PX_PER_S, text_columns
from riddle import QuizMaster
from wordmodel import TinyBrain

# ── Knobs and dials ── (pins, timings and colours)
BRIGHTNESS = 20  # percent at first start, like the ZHAW demos
MIN_BRIGHTNESS = 5
MAX_BRIGHTNESS = 60  # the power limit below still protects the USB port
BRIGHTNESS_STEP = 5
BRIGHTNESS_FILE = "brightness.txt"
# All 64 LEDs at full white would pull about 3.8 A. A USB port is not a toaster.
DONT_MELT_THE_USB_PORT_MA = 600  # all 64 LEDs together; USB 3 gives 900 mA, USB 2.0 promises 500
FRAME_MS = 25  # 40 frames per second

LED_PIN = 19
LED_TIMING = (400, 850, 800, 450)  # WS2812B, same as zhaw_led_matrix

BUTTON_PINS = {"up": 3, "down": 6, "left": 7, "right": 2, "center": 8, "switch": 9}
LAPTOP_COMMANDS = ("IMG", "PLAY", "VOL", "IDLE", "TITLE", "WORD", "NOICON")  # anything else is typed text
DEBOUNCE_MS = 20
REPEAT_DELAY_MS = 450  # holding up/down keeps changing the brightness
REPEAT_EVERY_MS = 150
HOLD_MS = 700  # holding the press this long is a "hold"
REALLY_HOLD_MS = 3000  # ...and this long a "longhold"
DOUBLE_PRESS_MS = 350  # a second press this soon is a double press
KONAMI_CODE = ("up", "up", "down", "down", "left", "right", "left", "right", "center")  # 30 extra lives not included
KONAMI_PATIENCE_MS = 1500  # a pause this long and the code starts over

MIN_SPOTLIGHT_MS = 1200  # every emoji deserves its 1.2 seconds of fame, unless the brain is surer
STOP_SIGN_MS = 700  # the stop sign before a negated word's emoji ("don't cry")
LONELY_AFTER_MS = 3000  # nothing from the laptop this long: it gets bored and starts quizzing you
MODE_DRUMROLL_MS = 900  # the mode's number after a switch
POP_MS = 90  # quick fade when an emoji appears
SLIDE_MS = 320
FADE_MS = 600
LEVEL_SHOW_MS = 1500  # volume or brightness level after a change

LYRICS, QUIZ = 1, 2  # the two modes, numbered as their drumroll shows them
MODE_COLORS = {LYRICS: b"\xff\xc8\x00", QUIZ: b"\x28\xc8\x28"}
ANSWER_YELLOW = b"\xff\xc8\x00"  # the riddle's answer
GOLD_STAR_GREEN = b"\x28\xc8\x28"  # border flash: the brain learned the word
HMM_ORANGE = b"\xff\x6e\x00"  # border flash: the brain's next guess
AMNESIA_RED = b"\xff\x14\x28"  # border flash: everything taught is forgotten

# Shown while nothing is playing (top row first)
LONELY_NOTE = (
    "....##..",
    "....#.#.",
    "....#..#",
    "....#...",
    "....#...",
    "..###...",
    ".####...",
    "..##....",
)


# ── Little helpers ── (four small jobs, no class needed)
def hue_color(h):
    """Fully saturated colour for a hue between 0 and 1."""
    h = (h % 1.0) * 6
    i = int(h) % 6
    up = int(255 * (h - int(h)))
    down = 255 - up
    return (
        (255, up, 0),
        (down, 255, 0),
        (0, 255, up),
        (0, down, 255),
        (up, 0, 255),
        (255, 0, down),
    )[i]


def cover_from_hex(text):
    """Turns the laptop's top-row-first hex picture into a bottom-row-first buffer."""
    data = unhexlify(text)
    cover = bytearray(192)
    for row in range(8):
        y = 7 - row
        cover[24 * y : 24 * y + 24] = data[24 * row : 24 * row + 24]
    return cover


def load_brightness():
    """The brightness saved last time, or the first-start default."""
    try:
        with open(BRIGHTNESS_FILE) as f:
            return max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, int(f.read())))
    except (OSError, ValueError):
        return BRIGHTNESS


def save_brightness(value):
    """Remembers the brightness for the next time the Lumatrix is plugged in."""
    try:
        with open(BRIGHTNESS_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        pass


# ── The emoji zoo ── (107 animated critters, 8x8 pixels each, fed from icons.bin)
class EmojiZoo:
    """The animated emojis from icons.bin (made by model/build_icons.py)."""

    def __init__(self, path="icons.bin"):
        with open(path, "rb") as f:
            data = f.read()
        magic, colours, count = struct.unpack("<4sBH", data[:7])
        if magic != b"LMI1":
            raise ValueError("not a Lumatrix icon file")
        p = 7
        self.palette = [b"\x00\x00\x00"] + [data[p + 3 * i : p + 3 * i + 3] for i in range(colours)]
        p += 3 * colours
        self.icons = {}  # name: (ms per frame, mode, where its frames start, frames)
        for _ in range(count):
            n = data[p]
            name = data[p + 1 : p + 1 + n].decode()
            p += 1 + n
            ms, mode, frames = struct.unpack("<HBB", data[p : p + 4])
            p += 4
            self.icons[name] = (ms, mode, p, frames)
            p += 64 * frames
        self.data = data

    def frame_at(self, name, elapsed):
        """Which frame of the emoji shows elapsed ms after it popped up."""
        ms, mode, _, frames = self.icons[name]
        if frames == 1 or ms == 0:
            return 0
        step = elapsed // ms
        if mode == 2:  # once, then stay on the last frame
            return min(step, frames - 1)
        if mode == 1:  # pingpong: 0 1 2 1 0 1 2 ...
            k = step % (2 * frames - 2)
            return k if k < frames else 2 * frames - 2 - k
        return step % frames  # loop

    def draw(self, name, k, out):
        """Paints frame k of the emoji into out."""
        start = self.icons[name][2] + 64 * k
        data = self.data
        palette = self.palette
        for i in range(64):
            out[3 * i : 3 * i + 3] = palette[data[start + i]]


# ── The 64 LEDs ── (gamma-corrected, and on a current diet for the USB port)
class LedWall:
    """The 8x8 LEDs. Frames are RGB bytearrays, (0, 0) = bottom left."""

    def __init__(self, brightness):
        self.brightness = brightness  # percent
        self.pin = Pin(LED_PIN, Pin.OUT)
        self.out = bytearray(192)
        # Perceived brightness -> LED duty, scaled to 0..65535 (gamma 2.2).
        # Eyes are not linear. Neither is a student's sleep before a deadline.
        self.gamma = [int(65535 * (i / 255) ** 2.2 + 0.5) for i in range(256)]
        # About 20 mA per colour channel at full duty
        self.limit = DONT_MELT_THE_USB_PORT_MA * 255 // 20

    def show(self, rgb, level=1.0):
        """Sends a frame to the LEDs: dimmed, gamma-corrected and within the power limit."""
        lvl = int(255 * self.brightness * level) // 100
        gamma = self.gamma
        out = self.out
        total = 0
        for i in range(0, 192, 3):
            r = (gamma[rgb[i]] * lvl + 32767) >> 16
            g = (gamma[rgb[i + 1]] * lvl + 32767) >> 16
            b = (gamma[rgb[i + 2]] * lvl + 32767) >> 16
            out[i] = g  # the LEDs expect GRB
            out[i + 1] = r
            out[i + 2] = b
            total += r + g + b
        if total > self.limit:
            scale = self.limit * 256 // total
            for i in range(192):
                out[i] = out[i] * scale >> 8
        bitstream(self.pin, 0, LED_TIMING, out)


# ── The joystick ── (one stick and a switch, nine events)
class Joystick:
    """Debounced joystick presses (the ZHAW library has no debouncing).

    The press counts once it is let go and no second press follows within
    DOUBLE_PRESS_MS, so that it can also mean something else: "double" for
    two quick presses, "hold" once it has been down for HOLD_MS and
    "longhold" after REALLY_HOLD_MS."""

    def __init__(self):
        now = ticks_ms()
        self.pins = {}
        self.raw = {}
        self.raw_at = {}
        self.down = {}
        self.repeat_at = {}
        for name, number in BUTTON_PINS.items():
            pin = Pin(number, Pin.IN, Pin.PULL_UP)
            self.pins[name] = pin
            self.raw[name] = self.down[name] = pin.value() == 0
            self.raw_at[name] = now
            self.repeat_at[name] = now
        self.held_since = now
        self.hold_sent = self.down["center"]  # held at start: not a long press
        self.longhold_sent = self.hold_sent
        self.click_at = None  # a press let go, waiting to see if a second follows
        self.repeat = True  # holding up/down repeats it

    def presses(self, now):
        """The joystick's new events, like ["up"] or ["double"]."""
        found = []
        if self.click_at is not None and ticks_diff(now, self.click_at) >= DOUBLE_PRESS_MS:
            self.click_at = None
            found.append("center")
        for name, pin in self.pins.items():
            pressed = pin.value() == 0
            if pressed != self.raw[name]:
                self.raw[name] = pressed
                self.raw_at[name] = now
            elif pressed != self.down[name]:
                if ticks_diff(now, self.raw_at[name]) >= DEBOUNCE_MS:
                    self.down[name] = pressed
                    if name == "center":
                        if pressed:
                            self.held_since = now
                            self.hold_sent = self.longhold_sent = False
                        elif not self.hold_sent:  # letting go after a hold means nothing
                            if self.click_at is None:
                                self.click_at = now
                            else:
                                self.click_at = None
                                found.append("double")
                    elif pressed:
                        found.append(name)
                        self.repeat_at[name] = ticks_add(now, REPEAT_DELAY_MS)
            elif pressed and name == "center":
                held = ticks_diff(now, self.held_since)
                if not self.hold_sent and held >= HOLD_MS:
                    self.hold_sent = True
                    self.click_at = None
                    found.append("hold")
                elif not self.longhold_sent and held >= REALLY_HOLD_MS:
                    self.longhold_sent = True
                    found.append("longhold")
            elif pressed and self.repeat and name in ("up", "down") and ticks_diff(now, self.repeat_at[name]) >= 0:
                found.append(name)
                self.repeat_at[name] = ticks_add(now, REPEAT_EVERY_MS)
        return found


def konami_progress(presses):
    """How many steps of KONAMI_CODE the most recent presses complete."""
    for n in range(min(len(presses), len(KONAMI_CODE)), 0, -1):
        if tuple(presses[-n:]) == KONAMI_CODE[:n]:
            return n
    return 0


class Konami:
    """Spots KONAMI_CODE among the presses.

    up/up/down/down just switch the mode (or the brightness) there and back,
    so those go through at once. After that, presses that could still finish
    the code are held back so that entering it doesn't skip songs; they are
    let through if the code breaks or stalls.
    """

    HOLD_BACK_FROM = 4  # up up down down are never held back

    def __init__(self):
        self.recent = []
        self.held = []
        self.last = ticks_ms()

    def press(self, name, now):
        """Returns (presses to act on now, True if the code was completed)."""
        release = self.expire(now)
        self.last = now
        self.recent = (self.recent + [name])[-len(KONAMI_CODE) :]
        done = konami_progress(self.recent)
        if done == len(KONAMI_CODE):
            self.recent = []
            self.held = []
            return release, True
        stream = self.held + [name]
        cut = len(stream) - max(0, done - self.HOLD_BACK_FROM)
        self.held = stream[cut:]
        return release + stream[:cut], False

    def expire(self, now):
        """Lets held presses through once the code has stalled."""
        if self.recent and ticks_diff(now, self.last) > KONAMI_PATIENCE_MS:
            release = self.held
            self.recent = []
            self.held = []
            return release
        return []


# ── Kaboom ── (the cheat code reward: up to 64 pixels of confetti, then they tidy up)
class Confetti:
    """One pixel of the exploding picture: where it flies, and where home is
    (from_x/from_y are set when it starts flying home)."""

    def __init__(self, x, y, color):
        self.home_x = self.x = x
        self.home_y = self.y = y
        self.color = color
        dx = x - 3.5
        dy = y - 3.5
        dist = math.sqrt(dx * dx + dy * dy)
        speed = 5 + random.getrandbits(8) / 40  # 5..11 pixels per second
        self.vx = dx / dist * speed + (random.getrandbits(8) - 128) / 50
        self.vy = dy / dist * speed + 7 + random.getrandbits(8) / 60


class Kaboom:
    """Cheat code reward: the picture's bright pixels burst apart, bounce
    around the bottom of the matrix and then fly back into place.
    No pixels were harmed: every single one finds its way home."""

    FLASH_MS = 150
    BURST_MS = 1800
    RETURN_MS = 900
    GRAVITY = -28.0  # pixels per second squared, y points up

    def __init__(self, image, now):
        self.start = now
        self.last = now
        self.returning = False
        self.confetti = []
        for y in range(8):
            for x in range(8):
                i = (x + 8 * y) * 3
                color = (image[i], image[i + 1], image[i + 2])
                if sum(color) >= 40:  # dark pixels would be invisible anyway
                    self.confetti.append(Confetti(x, y, color))
        if not self.confetti:  # a dark picture bursts into a rainbow instead
            for y in range(8):
                for x in range(8):
                    self.confetti.append(Confetti(x, y, hue_color((x + y) / 16)))

    def draw(self, frame, now):
        """Draws the next step into frame. Returns False when finished."""
        elapsed = ticks_diff(now, self.start)
        if elapsed >= self.BURST_MS + self.RETURN_MS:
            return False
        flash = 0
        if elapsed < self.FLASH_MS:
            flash = 255 - 255 * elapsed // self.FLASH_MS
        for i in range(192):
            frame[i] = flash

        if elapsed < self.BURST_MS:
            self.fly(min(ticks_diff(now, self.last), 50) / 1000)
        else:
            self.fly_home((elapsed - self.BURST_MS) / self.RETURN_MS)
        self.last = now

        for piece in self.confetti:
            x = int(piece.x + 0.5)
            y = int(piece.y + 0.5)
            if 0 <= x < 8 and 0 <= y < 8:
                i = (x + 8 * y) * 3
                for c in range(3):
                    if piece.color[c] > frame[i + c]:
                        frame[i + c] = piece.color[c]
        return True

    def fly(self, dt):
        """dt seconds of gravity, bouncing off the floor and the walls."""
        for piece in self.confetti:
            piece.vy += self.GRAVITY * dt
            piece.x += piece.vx * dt
            piece.y += piece.vy * dt
            if piece.y < 0:
                piece.y = -piece.y
                piece.vy = -piece.vy * 0.55
                piece.vx *= 0.8
            if piece.x < 0:
                piece.x = -piece.x
                piece.vx = -piece.vx * 0.7
            elif piece.x > 7:
                piece.x = 14 - piece.x
                piece.vx = -piece.vx * 0.7

    def fly_home(self, u):
        """Eases every piece from where it landed back home (u from 0 to 1)."""
        if not self.returning:
            self.returning = True
            for piece in self.confetti:
                piece.from_x = piece.x
                piece.from_y = piece.y
        # ease in and out
        e = 4 * u * u * u if u < 0.5 else 1 - (2 - 2 * u) ** 3 / 2
        for piece in self.confetti:
            piece.x = piece.from_x + (piece.home_x - piece.from_x) * e
            piece.y = piece.from_y + (piece.home_y - piece.from_y) * e


# ── The laptop ── (a USB cable full of ASCII)
class LaptopLink:
    """Reads ASCII lines from the laptop without blocking."""

    def __init__(self):
        self.poller = select.poll()
        self.poller.register(sys.stdin, select.POLLIN)
        self.chars = []

    def lines(self, budget=800):
        """The lines that arrived complete, reading at most budget characters."""
        found = []
        while budget and self.poller.poll(0):
            budget -= 1
            ch = sys.stdin.read(1)
            if ch == "\n":
                found.append("".join(self.chars))
                self.chars = []
            elif ch != "\r" and len(self.chars) < 500:
                self.chars.append(ch)
        return found


# ── Painting ── (by numbers: 192 bytes a frame, bottom row first)
def draw_idle(frame, now):
    """The lonely note in slowly changing colours, breathing."""
    # now % ... first: the Pico's floats are too coarse for large tick counts
    r, g, b = hue_color(now % 20000 / 20000)
    k = 0.6 + 0.4 * math.sin(now % 3000 * 2 * math.pi / 3000)
    color = (int(r * k), int(g * k), int(b * k))
    for row in range(8):
        y = 7 - row
        line = LONELY_NOTE[row]
        for x in range(8):
            i = (x + 8 * y) * 3
            on = line[x] == "#"
            for c in range(3):
                frame[i + c] = color[c] if on else 0


def draw_level(frame, left, percent, color):
    """A level (0..100) rising from the bottom in color over the dimmed
    picture. Returns how strongly it is shown (0..256)."""
    alpha = 256 if left > 300 else left * 256 // 300
    height = percent * 8  # in hundredths of a row
    for y in range(8):
        fill = min(max(height - 100 * y, 0), 100)
        for i in range(24 * y, 24 * y + 24):
            v = frame[i]
            dim = v * 3 // 10
            over = dim + (color[i % 3] - dim) * fill // 100
            frame[i] = (v * (256 - alpha) + over * alpha) >> 8
    return alpha


def slide(out, old, new, t, direction):
    """Old picture slides out and the new one in. direction 1 moves to the
    left (next song), -1 to the right (previous song)."""
    t = 1 - (1 - t) * (1 - t)  # ease out
    shift = int(t * 8 + 0.5)
    for x in range(8):
        s = x + shift * direction
        if 0 <= s < 8:
            src, sx = old, s
        else:
            src, sx = new, s - 8 * direction
        for y in range(8):
            d = (x + 8 * y) * 3
            i = (sx + 8 * y) * 3
            out[d : d + 3] = src[i : i + 3]


def draw_columns(out, cols, color):
    """Draws 8 text columns (bit 0 = top row) into an LED buffer."""
    for x in range(8):
        mask = cols[x]
        for row in range(8):
            i = (x + 8 * (7 - row)) * 3  # the buffer's bottom row comes first
            out[i : i + 3] = color if mask >> row & 1 else b"\x00\x00\x00"


def cover_color(cover):
    """The cover's most colourful pixel at full brightness, or white."""
    best, best_chroma = None, 60
    if cover is not None:
        for i in range(0, 192, 3):
            r, g, b = cover[i], cover[i + 1], cover[i + 2]
            chroma = max(r, g, b) - min(r, g, b)
            if chroma > best_chroma:
                best, best_chroma = (r, g, b), chroma
    if best is None:
        return b"\xff\xff\xff"
    top = max(best)
    return bytes(c * 255 // top for c in best)


# ── The show ── (three modes, one joystick, 40 frames a second)
class Lumatrix:
    """The whole show: listens to the laptop and the joystick, paints the LEDs."""

    def __init__(self):
        now = ticks_ms()
        self.wall = LedWall(load_brightness())
        self.joystick = Joystick()
        self.switch = self.joystick.down["switch"]
        self.brightness_mode = False  # flipping the switch: up/down change brightness
        self.konami = Konami()
        self.laptop = LaptopLink()
        self.cover = None  # None = nothing playing, show the note
        self.backdrop = bytearray(192)  # cover, note, emoji or quiz, mid-transition too
        self.prev = bytearray(192)  # the backdrop a transition starts from
        self.idle = bytearray(192)  # the note or the quiz, drawn fresh each frame
        self.frame = bytearray(192)  # what goes to the LEDs
        self.emoji_frame = bytearray(192)  # the emoji shown over the cover
        self.emoji_shown = False  # the backdrop shows the emoji now (a change starts a pop/fade)
        self.emoji = None  # the emoji in self.emoji_frame
        self.emoji_since = now  # when it popped up
        self.emoji_frame_no = 0  # its animation frame in self.emoji_frame
        self.emoji_confidence = 0.0  # how sure the brain was about it
        try:
            self.zoo = EmojiZoo("icons.bin")
        except (OSError, ValueError):
            self.zoo = None  # no emojis until icons.bin is on the Pico
            print("NOICONS")
        try:
            self.brain = TinyBrain("model.bin")
        except (OSError, ValueError):
            self.brain = None  # no emojis until model.bin is on the Pico
            print("NOMODEL")
        self.transition = None  # "next", "prev", "fade" or "pop"
        self.transition_start = now
        self.skip = None  # last next/prev press, picks the slide direction
        self.skip_at = now
        self.playing = True
        self.level = 1.0
        self.volume = 0
        self.overlay = "volume"  # level shown after a change: volume or brightness
        self.overlay_until = now
        self.save_at = None  # when to store a changed brightness
        self.kaboom = None  # the cheat code reward, while it plays
        self.last_heard = now  # last line from the laptop
        self.mode = LYRICS
        self.human_picked_mode = False  # picked with the joystick: no automatic switching
        self.mode_drumroll_until = now  # the mode's number shows until then
        self.quiz = None  # the game, made when the QUIZ mode starts
        self.title = None  # the song's title (TITLE from the laptop)
        self.ticker = None  # (text columns, since, colour) while text scrolls by
        self.waiting_in_line = None  # (emoji, confidence, when): waits for the stop sign

    def step(self, now):
        """One frame: read the laptop, check the clocks and the joystick, paint."""
        for line in self.laptop.lines():
            self.last_heard = now
            if self.mode == QUIZ and not self.human_picked_mode:
                self.switch_mode(LYRICS, now, by_human=False)  # the laptop is back
            try:
                self.handle(line, now)
            except ValueError:
                pass  # garbled line, the laptop sends the state again anyway
        if (self.mode != QUIZ and not self.human_picked_mode and self.cover is None
                and self.brain and self.zoo and ticks_diff(now, self.last_heard) > LONELY_AFTER_MS):
            self.switch_mode(QUIZ, now, by_human=False)  # no laptop: play the game

        if self.waiting_in_line is not None and ticks_diff(now, self.waiting_in_line[2]) >= 0:
            name, confidence, _ = self.waiting_in_line
            self.waiting_in_line = None
            if self.mode == LYRICS:
                self.pop(name, confidence, now)

        self.joystick.repeat = self.brightness_mode  # holding up/down only repeats brightness steps
        presses = self.joystick.presses(now)
        if self.joystick.down["switch"] != self.switch:
            self.switch = self.joystick.down["switch"]
            self.brightness_mode = not self.brightness_mode
            if self.brightness_mode:
                self.show_level("brightness", now)
            else:
                self.overlay_until = now
        if self.kaboom is None:
            for name in presses:
                if name == "switch":
                    continue
                release, done = self.konami.press(name, now)
                for held in release:
                    self.act(held, now)
                if done:
                    print("CHEAT")
                    self.kaboom = Kaboom(self.backdrop, now)
                    break
            for held in self.konami.expire(now):
                self.act(held, now)

        if self.save_at is not None and ticks_diff(now, self.save_at) >= 0:
            save_brightness(self.wall.brightness)  # once the joystick rests
            self.save_at = None

        self.render(now)

    def handle(self, line, now):
        """Acts on one line from the laptop (the messages are listed at the top)."""
        parts = line.split(" ", 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""
        if cmd == "IMG" and len(arg) == 384:
            self.set_cover(cover_from_hex(arg), now)
        elif cmd == "PLAY":
            self.playing = arg == "1"
        elif cmd == "VOL":
            self.volume = max(0, min(100, int(arg)))
            self.show_level("volume", now)
        elif cmd == "IDLE":
            self.set_cover(None, now)
        elif cmd == "TITLE":
            self.title = arg
        elif cmd == "WORD":
            word, _, after = arg.partition(" ")
            self.on_word(word, after, now)
        elif cmd == "NOICON":
            self.emoji = None
        elif cmd not in LAPTOP_COMMANDS and line.strip():
            self.ask_quiz(line.strip(), now)  # typed in Thonny's shell: your own riddle

    def on_word(self, word, after, now):
        """Mode 2: asks the brain about the word; an emoji stays until the next
        fitting word. Within MIN_SPOTLIGHT_MS a different emoji only takes over
        if the brain is surer about it, so busy lines don't flicker. A negation
        ("don't") before a word with an emoji shows a stop sign first."""
        if self.mode != LYRICS or self.brain is None or self.zoo is None:
            return
        if "stop" in self.zoo.icons and self.brain.negates(word, after):
            print("SAW", word, "stop", 100)
            self.pop("stop", 0.0, ticks_ms())  # the next word's emoji may follow
            return
        name, confidence = self.brain.guess(word)
        if name is None or name not in self.zoo.icons:
            return
        now = ticks_ms()  # the brain took a moment
        print("SAW", word, name.replace(" ", "_"), self.brain.percent(name, confidence))  # 50+ shows
        spotlight_ms = ticks_diff(now, self.emoji_since)  # how long the shown emoji has been up
        if self.emoji == "stop" and name != "stop" and spotlight_ms < STOP_SIGN_MS:
            self.waiting_in_line = (name, confidence, ticks_add(self.emoji_since, STOP_SIGN_MS))
            return
        if self.emoji is not None and name != self.emoji:
            if spotlight_ms < MIN_SPOTLIGHT_MS and confidence <= self.emoji_confidence:
                return
        self.pop(name, confidence, now)

    def pop(self, name, confidence, now):
        """Pops the emoji up (over the cover or the last emoji)."""
        if name != self.emoji:
            if self.emoji is not None:
                self.prev[:] = self.backdrop  # one emoji pops over the other
                self.transition = "pop"
                self.transition_start = now
            self.show_emoji(name, now)
            self.emoji_confidence = confidence

    def show_emoji(self, name, now):
        """Puts the emoji's first frame into emoji_frame."""
        self.emoji = name
        self.emoji_since = now
        self.emoji_frame_no = 0
        self.zoo.draw(name, 0, self.emoji_frame)

    def animate_emoji(self, now):
        """Moves the shown emoji on to its current animation frame."""
        if self.emoji is None or self.zoo is None:
            return
        k = self.zoo.frame_at(self.emoji, ticks_diff(now, self.emoji_since))
        if k != self.emoji_frame_no:
            self.emoji_frame_no = k
            self.zoo.draw(self.emoji, k, self.emoji_frame)

    def act(self, name, now):
        """Does what a joystick event means right now."""
        if name in ("up", "down"):
            if self.brightness_mode:
                step = BRIGHTNESS_STEP if name == "up" else -BRIGHTNESS_STEP
                wall = self.wall
                wall.brightness = max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, wall.brightness + step))
                self.show_level("brightness", now)
                self.save_at = ticks_add(now, 2000)
            else:
                self.switch_mode(QUIZ if self.mode == LYRICS else LYRICS, now)
        elif self.mode == QUIZ:
            self.play_quiz(name, now)
        elif name == "center":
            self.show_text(self.title or "?", now)
        elif name == "double":
            print("BTN playpause")
            self.playing = not self.playing  # the laptop confirms with PLAY
        elif name in ("right", "left"):
            action = "next" if name == "right" else "prev"
            print("BTN", action)
            self.skip = action
            self.skip_at = now

    def ask_quiz(self, sentence, now):
        """A sentence typed in Thonny's shell becomes a riddle in the QUIZ mode."""
        if self.brain is None or self.zoo is None:
            return
        if self.mode != QUIZ:
            self.switch_mode(QUIZ, now)
        self.quiz.ask(sentence, now)

    def play_quiz(self, name, now):
        """QUIZ mode: the joystick plays the Emoji-Rätsel."""
        if self.quiz is None:
            return
        if name == "right":
            self.quiz.move(1, now)
        elif name == "left":
            self.quiz.move(-1, now)
        elif name == "center":
            self.quiz.reveal(now)
        elif name == "double":
            self.quiz.wrong(now)
        elif name == "hold":
            self.quiz.right(now)
        elif name == "longhold":
            self.quiz.forget(now)

    def switch_mode(self, mode, now, by_human=True):
        """Shows the new mode's number for a moment (the drumroll), then the mode."""
        self.mode = mode
        self.human_picked_mode = by_human
        self.mode_drumroll_until = ticks_add(now, MODE_DRUMROLL_MS)
        self.ticker = None
        self.emoji = None  # LYRICS starts on the cover until the next fitting word
        self.waiting_in_line = None
        if mode == QUIZ and self.brain and self.zoo:
            if self.quiz is None:
                self.quiz = QuizMaster(self.brain, self.zoo.icons, now)
            self.quiz.start = ticks_add(now, MODE_DRUMROLL_MS)  # its clues start after the number

    def show_text(self, text, now):
        """Scrolls text by once, in the cover's most colourful colour."""
        self.ticker = (text_columns(text), now, cover_color(self.cover))

    def draw_quiz(self, now):
        """Paints the quiz's clue or answer, and a coloured border as feedback."""
        out = self.idle
        kind, what = self.quiz.current(now)
        if kind == "symbol":
            name, since = what
            self.zoo.draw(name, self.zoo.frame_at(name, ticks_diff(now, since)), out)
        elif kind == "text":
            draw_columns(out, what, ANSWER_YELLOW)
        else:
            out[:] = bytes(192)
        feedback = self.quiz.feedback_at(now)
        if feedback:
            color = {"taught": GOLD_STAR_GREEN, "next": HMM_ORANGE}.get(feedback, AMNESIA_RED)
            for k in range(8):
                for x, y in ((k, 0), (k, 7), (0, k), (7, k)):
                    i = (x + 8 * y) * 3
                    out[i : i + 3] = color
        return out

    def show_level(self, kind, now):
        """Shows the "volume" or "brightness" level for a moment."""
        self.overlay = kind
        self.overlay_until = ticks_add(now, LEVEL_SHOW_MS)

    def set_cover(self, cover, now):
        """A new cover (None = nothing playing), sliding or fading in."""
        self.prev[:] = self.backdrop
        self.cover = cover
        self.emoji = None  # a new song starts on its cover
        self.waiting_in_line = None
        self.transition_start = now
        if self.skip and ticks_diff(now, self.skip_at) < 5000:
            self.transition = self.skip
        else:
            self.transition = "fade"
        self.skip = None

    def render(self, now):
        """Paints the frame: kaboom, the mode's number, ticker, or the backdrop and a level."""
        frame = self.frame
        if self.kaboom is not None:
            if self.kaboom.draw(frame, now):
                self.wall.show(frame)
                return
            self.kaboom = None

        if ticks_diff(self.mode_drumroll_until, now) > 0:
            digit = list(FONT[str(self.mode)])
            left = (8 - len(digit)) // 2
            draw_columns(frame, [0] * left + digit + [0] * 8, MODE_COLORS[self.mode])
            self.wall.show(frame)
            return
        if self.ticker is not None:
            cols, since, color = self.ticker
            off = ticks_diff(now, since) * SCROLL_PX_PER_S // 1000
            if off + 8 < len(cols):
                draw_columns(frame, cols[off : off + 8], color)
                self.wall.show(frame)
                return
            self.ticker = None

        self.draw_backdrop(now)
        frame[:] = self.backdrop

        if self.cover is not None and not self.playing and self.mode != QUIZ:
            target = 0.3 + 0.1 * math.sin(now % 4000 * 2 * math.pi / 4000)  # paused: dim, breathing
        else:
            target = 1.0
        self.level += (target - self.level) * 0.12
        level = self.level

        left = ticks_diff(self.overlay_until, now)
        if left > 0:
            if self.overlay == "volume":
                alpha = draw_level(frame, left, self.volume, (230, 230, 230))
            else:
                percent = self.wall.brightness * 100 // MAX_BRIGHTNESS
                alpha = draw_level(frame, left, percent, (255, 170, 40))
            level += (1 - level) * alpha / 256
        self.wall.show(frame, level)

    def draw_backdrop(self, now):
        """Paints what lies under the level: emoji, quiz, note or cover, mid-transition too."""
        backdrop = self.backdrop
        emoji_on = self.mode == LYRICS and self.emoji is not None
        if emoji_on != self.emoji_shown:
            self.emoji_shown = emoji_on  # an emoji pops up, or the cover fades back
            self.prev[:] = backdrop
            self.transition = "pop" if emoji_on else "fade"
            self.transition_start = now
        if emoji_on:
            self.animate_emoji(now)
            new = self.emoji_frame
        elif self.mode == QUIZ and self.quiz is not None:
            new = self.draw_quiz(now)
        elif self.cover is None:
            draw_idle(self.idle, now)
            new = self.idle
        else:
            new = self.cover
        if self.transition is None:
            backdrop[:] = new
            return
        duration = {"fade": FADE_MS, "pop": POP_MS}.get(self.transition, SLIDE_MS)
        t = ticks_diff(now, self.transition_start) / duration
        if t >= 1:
            self.transition = None
            backdrop[:] = new
        elif self.transition in ("fade", "pop"):
            a = int(256 * t)
            prev = self.prev
            for i in range(192):
                backdrop[i] = (prev[i] * (256 - a) + new[i] * a) >> 8
        else:
            slide(backdrop, self.prev, new, t, 1 if self.transition == "next" else -1)


# ── Go! ── (Ctrl+C in Thonny turns the lights off on the way out)
def main():
    """Runs the show, one frame every FRAME_MS, until Ctrl+C."""
    lumatrix = Lumatrix()
    print("HELLO lumatrix-music")
    try:
        while True:
            now = ticks_ms()
            lumatrix.step(now)
            rest = FRAME_MS - ticks_diff(ticks_ms(), now)
            if rest > 0:
                sleep_ms(rest)
    except KeyboardInterrupt:
        lumatrix.wall.show(bytearray(192))
        print("Stopped.")


if __name__ == "__main__":
    main()
