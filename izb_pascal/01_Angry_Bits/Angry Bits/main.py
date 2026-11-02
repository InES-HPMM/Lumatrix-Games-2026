# Angry Birds Klon fuer die Lumatrix (8x8 NeoPixel, Raspberry Pi Pico)
#
# Steuerung:
#   Menue                 -> Links/Rechts = Level waehlen, Mitte = Start
#                            ganz links: Papierkorb = Spielstand loeschen
#   Joystick Oben/Unten   -> Winkel
#   Joystick Rechts/Links -> Kraft (Balken rechts zeigt die Stufe)
#   Joystick Mitte        -> Schiessen (Bombe: nochmals druecken = Explosion)
#   Schiebeschalter       -> Pause, in der Pause: Mitte = zurueck zum Menue
#
# Voegel:  R = Rot, Y = Gelb (durchschlaegt 2 Bloecke), B = Bombe (3x3)
# Objekte: siehe levels.py
#
# Optional: Piezo-Summer an einem freien GPIO -> BUZZER_PIN setzen

import machine
import os
from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms, ticks_ms, ticks_diff, ticks_add
import math
from levels import LEVELS

# ---------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------
np = NeoPixel(Pin(19, Pin.OUT), 64)

UP = Pin(3, Pin.IN, Pin.PULL_UP)
DOWN = Pin(6, Pin.IN, Pin.PULL_UP)
LEFT = Pin(7, Pin.IN, Pin.PULL_UP)
RIGHT = Pin(2, Pin.IN, Pin.PULL_UP)
FIRE = Pin(8, Pin.IN, Pin.PULL_UP)
SWITCH = Pin(9, Pin.IN, Pin.PULL_UP)

BUZZER_PIN = None       # z.B. 15, wenn ein Piezo-Summer angeschlossen ist
# Im PC-Simulator gibt es immer einen Summer
if BUZZER_PIN is None and getattr(machine, "SIMULATED", False):
    BUZZER_PIN = 0

buzzer = None
if BUZZER_PIN is not None:
    buzzer = machine.PWM(Pin(BUZZER_PIN))
    buzzer.duty_u16(0)

SAVE_FILE = "save.txt"

# ---------------------------------------------------------------
# Farben (max. 40, damit es nicht blendet und wenig Strom braucht)
# ---------------------------------------------------------------
OFF = (0, 0, 0)
WOOD = (30, 12, 0)
STONE = (20, 20, 20)
STONE_CRACKED = (6, 6, 6)
GLASS = (0, 25, 25)
TNT = (40, 0, 15)
PLATFORM = (0, 6, 14)
PIG = (0, 40, 0)
PIG_HURT = (10, 18, 0)
SLING = (12, 5, 0)
AIM = (6, 6, 6)
AIM_BLOCKED = (25, 0, 0)
GHOST = (4, 0, 2)
BAR = (20, 15, 0)
TRAIL = (6, 0, 0)
WHITE = (40, 40, 40)
ORANGE = (40, 15, 0)
STAR = (40, 30, 0)
STAR_EMPTY = (4, 4, 4)
RED = (40, 0, 0)
GREEN = (0, 40, 0)

BIRD_COLORS = {"R": (40, 0, 0), "Y": (35, 25, 0), "B": (10, 0, 35)}
HP = {"W": 1, "S": 2, "G": 1, "T": 1, "F": 0, "P": 2}
POINTS = {"W": 1, "S": 2, "G": 1, "T": 3, "F": 0, "P": 5}
BONUS = 10              # Punkte pro nicht gebrauchtem Vogel

# ---------------------------------------------------------------
# Physik
# ---------------------------------------------------------------
ANGLES = [10, 20, 30, 40, 50, 60, 70, 80]                # Grad
POWERS = [0.50, 0.58, 0.66, 0.74, 0.82, 0.90, 0.98]      # Pixel pro Frame
G = 0.08                                    # Schwerkraft pro Frame
SUB = 4                                     # Teilschritte pro Frame
FRAME_MS = 60
PUSH_MIN = 0.35         # ab dieser Geschwindigkeit schiebt ein Treffer
PREVIEW_POINTS = 5

START = (1, 1)
SLING_POS = (1, 0)

# Tasten: erste Wiederholung nach REPEAT_DELAY, danach alle REPEAT_RATE ms
POLL_MS = 10
REPEAT_DELAY = 350
REPEAT_RATE = 110
BAR_MS = 700            # so lange bleibt der Kraftbalken sichtbar

# ---------------------------------------------------------------
# 3x5 Schrift fuer Lauftext
# ---------------------------------------------------------------
FONT = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"],
    "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "G": [".##", "#..", "#.#", "#.#", ".##"],
    "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    "B": ["##.", "#.#", "##.", "#.#", "##."],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "S": [".##", "#..", ".#.", "..#", "##."],
    "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "L": ["#..", "#..", "#..", "#..", "###"],
    "O": ["###", "#.#", "#.#", "#.#", "###"],
    "E": ["###", "#..", "##.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"],
    "3": ["##.", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "##.", "..#", "##."],
    "6": [".##", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "##."],
}

# ---------------------------------------------------------------
# 8x8 Bilder, oberste Zeile zuerst
# ---------------------------------------------------------------
BIRD_ICON = [
    "...RR...",
    ".RRRRRR.",
    "RKKRRKKR",         # boese Augenbrauen
    "RWKRRKWR",         # Augen
    "RRRYYRRR",         # Schnabel
    "RRROORRR",
    ".RBBBBR.",         # heller Bauch
    "..RRRR..",
]
TRASH_ICON = [                      # aus dem Pixel-Editor: "muelleimer"
    "...WW...",
    "WWWWWWWW",                     # Deckel
    ".W....W.",
    ".WR..RW.",                     # rotes X im Eimer
    ".W.RR.W.",
    ".WR..RW.",
    ".W....W.",
    ".WWWWWW.",
]
ICON_COLORS = {"R": (40, 0, 0), "W": (40, 40, 40), "K": OFF,
               "Y": (40, 30, 0), "O": (40, 12, 0), "B": (30, 20, 10)}
TRASH_COLORS = {"W": (40, 40, 40), "R": (40, 0, 0)}
TRASH_WARN = {"W": (40, 0, 0), "R": (40, 40, 40)}     # Farben vertauscht

switch_home = SWITCH.value()
score = 0
ghost = []              # Flugbahn des letzten Schusses


class Quit(Exception):
    # Zurueck ins Menue (aus der Pause heraus)
    pass


# ---------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------
def idx(x, y):
    return y * 8 + x


def inside(x, y):
    return 0 <= x < 8 and 0 <= y < 8


def rnd(v):
    return int(math.floor(v + 0.5))


def pressed(pin):
    return pin.value() == 0


def wait_release(pin):
    while pressed(pin):
        sleep_ms(10)


def show(buf):
    for i in range(64):
        np[i] = buf[i]
    np.write()


def fill(color):
    show([color] * 64)


def velocity(angle, power):
    a = angle * math.pi / 180
    return power * math.cos(a), power * math.sin(a)


def color_of(kind, hp):
    if kind == "W":
        return WOOD
    if kind == "S":
        return STONE if hp >= 2 else STONE_CRACKED
    if kind == "G":
        return GLASS
    if kind == "T":
        return TNT
    if kind == "F":
        return PLATFORM
    return PIG if hp >= 2 else PIG_HURT


def has_pigs(objs):
    for k, hp in objs.values():
        if k == "P":
            return True
    return False


def make_objs(level):
    objs = {}
    for x, y, k in level["objs"]:
        objs[(x, y)] = [k, HP[k]]
    return objs


class Button:
    # Meldet True einmal beim Druecken und beim Halten mit Wiederholung
    def __init__(self, pin, repeat=True):
        self.pin = pin
        self.repeat = repeat
        self.down = False
        self.next = 0

    def poll(self):
        now = ticks_ms()
        if not pressed(self.pin):
            self.down = False
            return False
        if not self.down:
            self.down = True
            self.next = ticks_add(now, REPEAT_DELAY)
            return True
        if self.repeat and ticks_diff(now, self.next) >= 0:
            self.next = ticks_add(now, REPEAT_RATE)
            return True
        return False


btn_up = Button(UP)
btn_down = Button(DOWN)
btn_left = Button(LEFT)
btn_right = Button(RIGHT)
btn_fire = Button(FIRE, repeat=False)


# ---------------------------------------------------------------
# Ton
# ---------------------------------------------------------------
def tone(freq, ms):
    # Ohne Summer wird nur gewartet, damit das Timing gleich bleibt
    if buzzer and freq:
        buzzer.freq(freq)
        buzzer.duty_u16(20000)
    sleep_ms(ms)
    if buzzer:
        buzzer.duty_u16(0)


def melody(notes, ms):
    for f in notes:
        tone(f, ms)


# ---------------------------------------------------------------
# Speicherstand: Sterne pro Level
# ---------------------------------------------------------------
def load_stars():
    try:
        with open(SAVE_FILE) as f:
            stars = [int(v) for v in f.read().split(",")]
    except Exception:
        stars = []
    return (stars + [0] * len(LEVELS))[:len(LEVELS)]


def save_stars(stars):
    try:
        with open(SAVE_FILE, "w") as f:
            f.write(",".join(str(s) for s in stars))
    except Exception:
        pass


def delete_save(stars):
    for i in range(len(stars)):
        stars[i] = 0
    try:
        os.remove(SAVE_FILE)
    except OSError:
        pass                # gab noch keinen Spielstand


# ---------------------------------------------------------------
# Zeichnen
# ---------------------------------------------------------------
def put(buf, x, y, color, shift=0):
    x += shift
    if inside(x, y):
        buf[idx(x, y)] = color


def draw(objs, queue, bird=None, kind=None, extra=None, shift=0):
    buf = [OFF] * 64
    put(buf, SLING_POS[0], SLING_POS[1], SLING, shift)
    for x, y in ghost:
        put(buf, x, y, GHOST, shift)
    # Verbleibende Voegel oben links
    for i in range(min(len(queue), 8)):
        put(buf, i, 7, BIRD_COLORS[queue[i]], shift)
    for (x, y), (k, hp) in objs.items():
        put(buf, x, y, color_of(k, hp), shift)
    if extra:
        for (x, y), c in extra:
            put(buf, x, y, c, shift)
    if bird:
        put(buf, bird[0], bird[1], BIRD_COLORS[kind], shift)
    show(buf)


def flash(objs, queue, cells, color, freq=0):
    for _ in range(2):
        draw(objs, queue, extra=[(c, color) for c in cells])
        tone(freq, 70)
        draw(objs, queue)
        sleep_ms(70)


def shake(objs, queue):
    for s in (1, -1, 1, -1, 0):
        draw(objs, queue, shift=s)
        sleep_ms(40)


def check_pause():
    if SWITCH.value() == switch_home:
        return
    t = 0
    while SWITCH.value() != switch_home:
        buf = [OFF] * 64
        if t % 30 < 15:
            for y in range(2, 6):
                buf[idx(2, y)] = AIM
                buf[idx(5, y)] = AIM
        show(buf)
        if btn_fire.poll():
            raise Quit()
        sleep_ms(20)
        t += 1


# ---------------------------------------------------------------
# Lauftext
# ---------------------------------------------------------------
def text_columns(text):
    cols = []
    for ch in text:
        g = FONT.get(ch)
        if g is None:
            cols += [0, 0]
            continue
        for cx in range(3):
            bits = 0
            for row in range(5):
                if g[row][cx] == "#":
                    bits |= 1 << row
            cols.append(bits)
        cols.append(0)
    return cols


def text_buf(cols, offset, color, top=6):
    buf = [OFF] * 64
    for sx in range(8):
        ci = sx + offset
        if 0 <= ci < len(cols):
            for row in range(5):
                if (cols[ci] >> row) & 1:
                    buf[idx(sx, top - row)] = color
    return buf


def scroll_text(text, color):
    # Gibt True zurueck, wenn Mitte gedrueckt wurde
    cols = text_columns(text)
    for offset in range(-8, len(cols)):
        show(text_buf(cols, offset, color))
        for _ in range(8):
            if pressed(FIRE):
                wait_release(FIRE)
                return True
            sleep_ms(10)
    return False


def show_digit(n):
    show(text_buf(text_columns(str(n)), -2, WHITE))
    sleep_ms(1000)


def icon_buf(icon, colors):
    # colors: Zeichen -> Farbe, "." und unbekannte Zeichen bleiben aus
    buf = [OFF] * 64
    for row, line in enumerate(icon):
        for x, ch in enumerate(line):
            buf[idx(x, 7 - row)] = colors.get(ch, OFF)
    return buf


def wait_or_fire(ms):
    # Wartet ms Millisekunden, gibt True zurueck, wenn Mitte gedrueckt wurde
    for _ in range(ms // 10):
        if pressed(FIRE):
            wait_release(FIRE)
            return True
        sleep_ms(10)
    return False


def show_bird():
    # Roter Vogel mit Blinzeln, gibt True zurueck, wenn uebersprungen
    blink = dict(ICON_COLORS)
    blink["W"] = ICON_COLORS["R"]
    show(icon_buf(BIRD_ICON, ICON_COLORS))
    melody((392, 523), 60)
    if wait_or_fire(1200):
        return True
    show(icon_buf(BIRD_ICON, blink))
    if wait_or_fire(150):
        return True
    show(icon_buf(BIRD_ICON, ICON_COLORS))
    return wait_or_fire(1000)


def confirm_delete(stars):
    # Papierkorb blinkt rot: Mitte = loeschen, andere Richtung = abbrechen
    wait_release(FIRE)
    for b in (btn_up, btn_down, btn_left, btn_right, btn_fire):
        b.poll()
    for t in range(400):                # max. 4 Sekunden
        colors = TRASH_WARN if t % 50 < 25 else TRASH_COLORS
        if t % 25 == 0:
            show(icon_buf(TRASH_ICON, colors))
        if btn_fire.poll():
            delete_save(stars)
            melody((523, 392, 262), 80)
            for _ in range(2):
                fill(RED)
                sleep_ms(120)
                fill(OFF)
                sleep_ms(120)
            return True
        if (btn_up.poll() or btn_down.poll() or btn_left.poll()
                or btn_right.poll()):
            break
        sleep_ms(10)
    tone(220, 60)
    return False


def star_row(buf, stars, y):
    # Drei Sterne als 2er-Bloecke: x=0-1, 3-4, 6-7
    for i, x0 in enumerate((0, 3, 6)):
        col = STAR if i < stars else STAR_EMPTY
        buf[idx(x0, y)] = col
        buf[idx(x0 + 1, y)] = col


# ---------------------------------------------------------------
# Menue
# ---------------------------------------------------------------
def unlocked(stars):
    # Freigeschaltet: alle geschafften Level + das naechste
    last = 0
    while last < len(LEVELS) - 1 and stars[last] > 0:
        last += 1
    return last


def menu(stars):
    # sel = -1 ist der Papierkorb links von Level 1
    last = unlocked(stars)
    sel = last
    wait_release(FIRE)
    btn_fire.poll()
    changed = True
    while True:
        if btn_left.poll() and sel > -1:
            sel -= 1
            changed = True
            tone(440, 15)
        if btn_right.poll() and sel < last:
            sel += 1
            changed = True
            tone(440, 15)
        if changed:
            if sel < 0:
                buf = icon_buf(TRASH_ICON, TRASH_COLORS)
            else:
                buf = text_buf(text_columns(str(sel + 1)), -2, WHITE, top=6)
                buf[idx(0, 4)] = AIM
                star_row(buf, stars[sel], 0)
            if sel < last:
                buf[idx(7, 4)] = AIM
            show(buf)
            changed = False
        if btn_fire.poll():
            if sel >= 0:
                tone(880, 40)
                return sel
            if confirm_delete(stars):
                last = 0
                sel = 0
            changed = True
        sleep_ms(POLL_MS)


# ---------------------------------------------------------------
# Zielen
# ---------------------------------------------------------------
def preview(angle, power, objs):
    # Gibt die Vorschau-Punkte und ggf. das getroffene Hindernis zurueck
    fx, fy = START
    vx, vy = velocity(angle, power)
    pts = []
    for step in range(1, PREVIEW_POINTS * 2 * SUB + 1):
        vy -= G / SUB
        fx += vx / SUB
        fy += vy / SUB
        c = (rnd(fx), rnd(fy))
        if fy < -0.5 or fx > 7.5:
            return pts, None
        if c in objs:
            return pts, c
        # Alle 2 Frames einen Punkt: Abstand zeigt die Kraft
        if step % (2 * SUB) == 0:
            pts.append(c)
    return pts, None


def aim(objs, queue, kind, setting):
    wait_release(FIRE)
    btn_fire.poll()
    changed = True
    bar_until = None
    while True:
        check_pause()
        if btn_up.poll() and setting[0] < len(ANGLES) - 1:
            setting[0] += 1
            changed = True
        if btn_down.poll() and setting[0] > 0:
            setting[0] -= 1
            changed = True
        if btn_right.poll() and setting[1] < len(POWERS) - 1:
            setting[1] += 1
            changed = True
            bar_until = ticks_add(ticks_ms(), BAR_MS)
        if btn_left.poll() and setting[1] > 0:
            setting[1] -= 1
            changed = True
            bar_until = ticks_add(ticks_ms(), BAR_MS)
        if bar_until is not None and ticks_diff(ticks_ms(), bar_until) >= 0:
            bar_until = None
            changed = True
        # Nur neu zeichnen, wenn sich etwas geaendert hat
        if changed:
            pts, hit = preview(ANGLES[setting[0]], POWERS[setting[1]], objs)
            extra = [(c, AIM) for c in pts]
            if hit:
                extra.append((hit, AIM_BLOCKED))
            if bar_until is not None:
                for y in range(setting[1] + 1):
                    extra.append(((7, y), BAR))
            draw(objs, queue, START, kind, extra)
            changed = False
        # Schuss sofort beim Druecken
        if btn_fire.poll():
            return
        sleep_ms(POLL_MS)


# ---------------------------------------------------------------
# Treffer
# ---------------------------------------------------------------
def damage(objs, c, n=1):
    # Gibt True zurueck, wenn das Objekt zerstoert wurde
    global score
    if c not in objs or objs[c][0] == "F":
        return False
    objs[c][1] -= n
    if objs[c][1] <= 0:
        score += POINTS[objs.pop(c)[0]]
        return True
    return False


def explode(objs, queue, cx, cy):
    # TNT im Explosionsbereich explodiert mit (Kettenreaktion)
    todo = [(cx, cy)]
    done = []
    while todo:
        x0, y0 = todo.pop()
        if (x0, y0) in done:
            continue
        done.append((x0, y0))
        cells = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if inside(x0 + dx, y0 + dy):
                    cells.append((x0 + dx, y0 + dy))
        flash(objs, queue, cells, ORANGE, 110)
        for c in cells:
            if c in objs and objs[c][0] == "T" and c not in done:
                todo.append(c)
            damage(objs, c, 2)
        shake(objs, queue)


def push(objs, c, vx):
    # Wucht: Getroffenes Objekt 1 Feld weiterschieben. Wurde es
    # zerstoert, bekommt das Objekt dahinter den Stoss.
    global score
    if vx < PUSH_MIN:
        return
    x, y = c
    if c not in objs:
        c = (x + 1, y)
        x += 1
    if c not in objs or objs[c][0] == "F":
        return
    target = (x + 1, y)
    if target in objs:
        return
    o = objs.pop(c)
    if x + 1 > 7:
        score += POINTS[o[0]]       # aus dem Bild geschoben
    else:
        objs[target] = o


# ---------------------------------------------------------------
# Flug
# ---------------------------------------------------------------
def fly(objs, queue, kind, angle, power):
    global ghost
    fx, fy = START
    vx, vy = velocity(angle, power)
    pierce = 2 if kind == "Y" else 0
    trail, path = [], []
    c = START
    melody((660, 990), 25)
    try:
        while True:
            check_pause()
            # Bombe per erneutem Knopfdruck zuenden (Schussdruck zaehlt nicht)
            if kind == "B" and btn_fire.poll():
                explode(objs, queue, c[0], c[1])
                return
            for _ in range(SUB):
                vy -= G / SUB
                fx += vx / SUB
                fy += vy / SUB
                c = (rnd(fx), rnd(fy))
                if fy < -0.5:
                    if kind == "B":
                        explode(objs, queue, c[0], 0)
                    return
                if fx > 7.5 or fx < -0.5:
                    return
                if inside(*c) and c not in path:
                    path.append(c)
                if c in objs:
                    k = objs[c][0]
                    if kind == "B" or k == "T":
                        explode(objs, queue, c[0], c[1])
                        return
                    flash(objs, queue, [c], WHITE, 220)
                    damage(objs, c, 2 if k == "P" else 1)
                    if pierce > 0 and c not in objs:
                        pierce -= 1
                        vx *= 0.7
                        if pierce == 0:
                            return
                    else:
                        push(objs, c, vx)
                        return
            draw(objs, queue, c, kind, [(t, TRAIL) for t in trail])
            if not trail or trail[-1] != c:
                trail.append(c)
                trail = trail[-2:]
            sleep_ms(FRAME_MS)
    finally:
        ghost = path


# ---------------------------------------------------------------
# Schwerkraft und Fallschaden
# ---------------------------------------------------------------
def settle(objs, queue):
    fall = {}
    moved_total = 0
    while True:
        moved = False
        for c in sorted(objs, key=lambda p: p[1]):
            x, y = c
            if objs[c][0] == "F":
                continue            # Plattformen schweben
            if y > 0 and (x, y - 1) not in objs:
                objs[(x, y - 1)] = objs.pop(c)
                fall[(x, y - 1)] = fall.pop(c, 0) + 1
                moved = True
                moved_total += 1
        if not moved:
            break
        draw(objs, queue)
        sleep_ms(90)
    if moved_total >= 3:
        shake(objs, queue)
    # Fallschaden: Schweine verletzt (1 Feld) oder tot (2+ Felder),
    # Glas zerbricht beim Fallen oder wenn etwas darauf landet
    hits = []
    for c, d in fall.items():
        if c not in objs:
            continue
        k = objs[c][0]
        below = (c[0], c[1] - 1)
        if k == "G":
            hits.append((c, 1))
        elif k == "P":
            hits.append((c, 2 if d >= 2 else 1))
        if below in objs and objs[below][0] == "G":
            hits.append((below, 1))
    if hits:
        flash(objs, queue, [c for c, n in hits], WHITE, 330)
        destroyed = False
        for c, n in hits:
            if damage(objs, c, n):
                destroyed = True
        if destroyed:
            settle(objs, queue)


# ---------------------------------------------------------------
# Animationen
# ---------------------------------------------------------------
def win_anim(stars):
    melody((523, 659, 784, 1047), 90)
    for x in range(8):
        buf = [OFF] * 64
        for xx in range(x + 1):
            for y in range(8):
                buf[idx(xx, y)] = GREEN
        show(buf)
        sleep_ms(50)
    sleep_ms(200)
    buf = [OFF] * 64
    for y in (3, 4):
        star_row(buf, stars, y)
    show(buf)
    for i in range(stars):
        tone(1047 + 200 * i, 120)
        sleep_ms(150)
    sleep_ms(1200)


def lose_anim():
    # Traurige Melodie, dann "LOSE" als Lauftext wie im Intro
    melody((392, 330, 262), 200)
    scroll_text("LOSE", RED)


def final_anim():
    colors = [RED, ORANGE, STAR, GREEN, (0, 20, 40), (10, 0, 35)]
    melody((523, 659, 784, 1047, 784, 1047), 110)
    for step in range(24):
        buf = [OFF] * 64
        for x in range(8):
            for y in range(8):
                buf[idx(x, y)] = colors[(x + y + step) % len(colors)]
        show(buf)
        sleep_ms(80)


# ---------------------------------------------------------------
# Spielablauf
# ---------------------------------------------------------------
def play_level(n):
    # Gibt die Sterne zurueck (0 = verloren)
    global score, ghost
    lv = LEVELS[n]
    objs = make_objs(lv)
    queue = list(lv["birds"])
    setting = [3, 3]    # Winkel- und Kraftstufe bleiben zwischen Schuessen
    score = 0
    ghost = []
    show_digit(n + 1)
    while queue:
        kind = queue.pop(0)
        aim(objs, queue, kind, setting)
        fly(objs, queue, kind, ANGLES[setting[0]], POWERS[setting[1]])
        settle(objs, queue)
        draw(objs, queue)
        if not has_pigs(objs):
            used = len(lv["birds"]) - len(queue)
            par = lv.get("par", 1)
            stars = 3 if used <= par else (2 if used == par + 1 else 1)
            score += BONUS * len(queue)
            sleep_ms(300)
            win_anim(stars)
            scroll_text(str(score), STAR)
            return stars
    sleep_ms(300)
    lose_anim()
    return 0


def main():
    stars = load_stars()
    # Titel: Vogel und Lauftext abwechselnd, bis Mitte gedrueckt wird
    while not show_bird() and not scroll_text("ANGRY BITS", WHITE):
        pass
    while True:
        level = menu(stars)
        while True:
            try:
                got = play_level(level)
            except Quit:
                break
            if got == 0:
                continue            # gleiches Level nochmals
            if got > stars[level]:
                stars[level] = got
                save_stars(stars)
            level += 1
            if level >= len(LEVELS):
                final_anim()
                break


if __name__ == "__main__":
    main()
