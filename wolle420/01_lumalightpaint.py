# Luma Lightpaint - Lumatrix Games 2026
# Die ganze Matrix leuchtet als ein farbiger Punkt für Langzeitbelichtungen.
# Auf der Lumatrix als main.py speichern, dann startet es beim Einschalten automatisch.
#
# Menü:        links/rechts = Symbol wählen, Mitte = öffnen / bestätigen / starten
# Einstellen:  hoch/runter = Wert ändern (Grösse = wie viele Pixel leuchten)
# Farbmischer: links/rechts = Rot, Grün, Blau wählen, hoch/runter = Anteil
# Im Lauf:     beliebige Taste = abbrechen
#              Anfang und Ende werden überblendet: Fliegt die Drohne eine Runde in
#              Laufzeit - 2 s, ergänzen sich Ein- und Ausblenden zu voller Helligkeit
# Schalter:    manueller Modus, Licht brennt nur, solange eine Taste gehalten wird
#              Mitte = Farbe A, hoch = Weiss, rechts = Rot, runter = Grün, links = Blau

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms, ticks_ms, ticks_diff

matrix = NeoPixel(Pin(19, Pin.OUT), 64)
joy_up = Pin(3, Pin.IN, Pin.PULL_UP)
joy_down = Pin(6, Pin.IN, Pin.PULL_UP)
joy_left = Pin(7, Pin.IN, Pin.PULL_UP)
joy_right = Pin(2, Pin.IN, Pin.PULL_UP)
joy_center = Pin(8, Pin.IN, Pin.PULL_UP)
switch = Pin(9, Pin.IN, Pin.PULL_UP)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

DIRS = ((joy_left, -1, 0), (joy_right, 1, 0), (joy_up, 0, 1), (joy_down, 0, -1))
PENS = ((joy_center, None), (joy_up, WHITE), (joy_right, (255, 0, 0)),
        (joy_down, (0, 255, 0)), (joy_left, (0, 0, 255)))       # None = Farbe A

# Ein Programm bekommt Farbe A und B, den Fortschritt im Lauf (0-255),
# die Phase im Takt (0-255) und die Nummer des Takts.
GOLDEN = 98     # 256 / Goldener Schnitt² --> jede neue Farbe liegt weit weg von den vorherigen
PROGRAMS = (
    lambda a, b, progress, phase, count: a,                             # Dauerlicht
    lambda a, b, progress, phase, count: blend(a, b, progress),         # Verlauf A -> B
    lambda a, b, progress, phase, count: wheel(progress),               # Regenbogen
    lambda a, b, progress, phase, count: scale(a, abs(2 * phase - 255)),  # Pulsieren
    lambda a, b, progress, phase, count: (a, b)[count % 2],             # Farbfolge A/B
    lambda a, b, progress, phase, count: a if phase < 51 else BLACK,    # Punkte
    lambda a, b, progress, phase, count: wheel(count * GOLDEN),         # Zufallsfarben
)


# Jede Einstellung wählt einen Eintrag aus ihrer Liste. Die Farben haben einen eigenen Mischer.
OPTIONS = (
    PROGRAMS,
    (0,),                                           # Farbe A
    (0,),                                           # Farbe B
    (3, 6, 12, 25, 50, 100, 180, 255),              # Helligkeit
    (8, 6, 4, 2, 1),                                # Grösse: Seitenlänge des Quadrats
    (5, 10, 15, 20, 30, 45, 60, 90),                # Laufzeit in s
    (0, 3, 5, 10, 15, 20, 30, 60),                  # Startverzögerung in s
    (100, 200, 300, 500, 800, 1000, 1500, 2000),    # Takt in ms
)
PROG, COL_A, COL_B, BRIGHT, SIZE, RUN, DELAY, BEAT = range(len(OPTIONS))
START = len(OPTIONS)                                # letztes Symbol im Menü
settings = [0, 0, 0, 3, 0, 3, 2, 3]
colors = [[7, 0, 0], [0, 0, 7]]                     # Farbe A und B: Rot, Grün, Blau je 0-7
FILE = "lightpaint.txt"

MENU_LEVEL = 20
FADE_MS = 2000          # Ein- und Ausblenden am Anfang und Ende jedes Laufs
COUNTDOWN_MS = 3000     # vor dem Start blitzt ein Pixel bei 3, 2, 1

# Strombegrenzung für die 5-W-Powerbank. Gemessen --> alles weiss (R+G+B = 765) = 2400 mA
MAX_MA = 800
BUDGET = MAX_MA * 765 * 64 // 2400     # erlaubte Summe aller Farbwerte aller LEDs

ICONS = (
    ("........",     # Programm
     ".#...#..",
     "#.#.#.#.",
     "...#...#",
     "........",
     ".#...#..",
     "#.#.#.#.",
     "...#...#"),

    ("...##...",     # Farbe A
     "..#..#..",
     ".#....#.",
     ".#....#.",
     ".######.",
     ".#....#.",
     ".#....#.",
     "........"),

    (".#####..",     # Farbe B
     ".#....#.",
     ".#....#.",
     ".#####..",
     ".#....#.",
     ".#....#.",
     ".#####..",
     "........"),

    ("...#....",     # Helligkeit
     ".#...#..",
     "..###...",
     "#.###.#.",
     "..###...",
     ".#...#..",
     "...#....",
     "........"),

    ("########",     # Grösse
     "#......#",
     "#.####.#",
     "#.#..#.#",
     "#.#..#.#",
     "#.####.#",
     "#......#",
     "########"),

    (".######.",     # Laufzeit
     ".#....#.",
     "..#..#..",
     "...##...",
     "...##...",
     "..#..#..",
     ".#....#.",
     ".######."),

    ("..####..",     # Startverzögerung
     ".#....#.",
     "#..#...#",
     "#..#...#",
     "#..###.#",
     "#......#",
     ".#....#.",
     "..####.."),

    ("....##..",     # Takt
     "....#.#.",
     "....#..#",
     "....#...",
     "....#...",
     "..###...",
     ".####...",
     "..##...."),

    ("..#.....",     # Start
     "..##....",
     "..###...",
     "..####..",
     "..####..",
     "..###...",
     "..##....",
     "..#....."),
)
ICON_COLORS = ((255, 255, 255), None, None, (255, 200, 0), (255, 40, 120), (0, 255, 255),
               (255, 90, 0), (255, 0, 255), (0, 255, 0))

FONT = ("111101101101111", "010110010010111", "111001111100111", "111001111001111",
        "101101111001001", "111100111001111", "111100111101111", "111001001001001",
        "111101111101111", "111101111001111")


def load_settings():
    try:
        with open(FILE) as f:
            values = [int(v) for v in f.read().split(",")]
    except (OSError, ValueError):
        return
    if len(values) == len(settings) + 6:            # Einstellungen + 2 x RGB
        settings[:] = [v % len(o) for v, o in zip(values, OPTIONS)]
        colors[:] = [[v & 7 for v in values[-6:-3]], [v & 7 for v in values[-3:]]]


def save_settings():
    with open(FILE, "w") as f:
        f.write(",".join(str(v) for v in settings + colors[0] + colors[1]))


def value(item):
    return OPTIONS[item][settings[item]]


def scale(color, level):
    return tuple(c * level // 255 for c in color)


def blend(a, b, weight):
    return tuple(x + (y - x) * weight // 255 for x, y in zip(a, b))


def limit(color, pixels=64):
    # je weniger Pixel leuchten, desto heller darf jedes einzelne sein
    total = sum(color) * pixels
    return color if total <= BUDGET else scale(color, BUDGET * 255 // total)


def mixed(n):
    return tuple(c * 255 // 7 for c in colors[n])


def visible(color):
    return color if color != BLACK else (90, 90, 90)


def wheel(pos):
    pos %= 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def color_at(t, total, beat):
    return value(PROG)(mixed(0), mixed(1), t * 256 // total, t % beat * 256 // beat, t // beat)


def set_pixel(x, y, color):
    matrix[(7 - y) * 8 + x] = color                 # Zeile 0 ist oben


def draw_square(size, color):
    lo = (8 - size) // 2
    for y in range(lo, lo + size):
        for x in range(lo, lo + size):
            set_pixel(x, y, color)


def light(color, fade=255):
    size = value(SIZE)
    matrix.fill(BLACK)
    draw_square(size, scale(limit(scale(color, value(BRIGHT)), size * size), fade))
    matrix.write()


def dark():
    matrix.fill(BLACK)
    matrix.write()


def draw_bitmap(rows, color):
    for y in range(8):
        for x in range(8):
            if rows[y][x] == "#":
                set_pixel(x, y, color)


def draw_number(number, color):
    digits = [(number, 2)] if number < 10 else [(number // 10, 0), (number % 10, 4)]
    for digit, x0 in digits:
        for i in range(15):
            if FONT[digit][i] == "1":
                set_pixel(x0 + i % 3, 1 + i // 3, color)


def draw_icon(item):
    color = ICON_COLORS[item]
    if item in (COL_A, COL_B):
        color = visible(mixed(item - COL_A))
    draw_bitmap(ICONS[item], scale(color, MENU_LEVEL))


def draw_mixer(n, channel):
    # drei Balken (R, G, B), dazwischen die gemischte Farbe, unten der gewählte Kanal
    preview = scale(mixed(n), MENU_LEVEL)
    for y in range(7):
        set_pixel(2, y, preview)
        set_pixel(5, y, preview)
    for ch in range(3):
        x = ch * 3
        base = [0, 0, 0]
        base[ch] = MENU_LEVEL
        for step in range(colors[n][ch]):
            set_pixel(x, 6 - step, tuple(base))
            set_pixel(x + 1, 6 - step, tuple(base))
        base[ch] = 90 if ch == channel else 4
        set_pixel(x, 7, tuple(base))
        set_pixel(x + 1, 7, tuple(base))


def draw_value(item, channel):
    white = scale(WHITE, MENU_LEVEL)
    if item == PROG:                                # Lichtspur, wie im Foto
        for x in range(8):
            color = scale(color_at(x * 1000, 8000, 4000), MENU_LEVEL)
            set_pixel(x, 3, color)
            set_pixel(x, 4, color)
    elif item in (COL_A, COL_B):
        draw_mixer(item - COL_A, channel)
    elif item == BRIGHT:                            # Treppe in echter Helligkeit
        color = limit(scale(visible(mixed(0)), value(BRIGHT)))
        for x in range(settings[BRIGHT] + 1):
            for y in range(7 - x, 8):
                set_pixel(x, y, color)
    elif item == SIZE:
        draw_square(value(SIZE), scale(visible(mixed(0)), MENU_LEVEL))
    elif item in (RUN, DELAY):
        draw_number(value(item), white)
    elif ticks_ms() % value(BEAT) < value(BEAT) // 2:   # Takt: Quadrat blinkt
        draw_square(4, white)


def pressed(pin):
    return not pin.value()


def manual_on():
    return pressed(switch)


def any_key():
    return any(pressed(pin) for pin, _ in PENS)


def interrupted():
    return manual_on() or any_key()


def direction():
    for pin, dx, dy in DIRS:
        if pressed(pin):
            return dx, dy
    return 0, 0


def wait_release():
    while any_key():
        sleep_ms(10)
    sleep_ms(30)


def wait_delay():
    total = value(DELAY) * 1000
    start = ticks_ms()
    while True:
        rest = total - ticks_diff(ticks_ms(), start)
        if rest <= 0:
            return True
        if interrupted():
            return False
        matrix.fill(BLACK)
        if rest < COUNTDOWN_MS and rest % 1000 > 900:
            set_pixel(0, 0, (15, 0, 0))
        matrix.write()
        sleep_ms(10)


def show_program():
    total = value(RUN) * 1000
    start = ticks_ms()
    while True:
        t = ticks_diff(ticks_ms(), start)
        if t >= total or interrupted():
            dark()
            return t >= total
        fade = min(255, 255 * t // FADE_MS, 255 * (total - t) // FADE_MS)
        light(color_at(t, total, value(BEAT)), fade)
        sleep_ms(5)


def run():
    save_settings()
    dark()
    wait_release()
    if wait_delay() and show_program():
        while not interrupted():    # dunkel bleiben bis zur nächsten Taste (kein Streulicht)
            sleep_ms(20)
    wait_release()


def manual():
    # Farbe hängt an der Taste: kein Auswählen, also kein Lichtpunkt im Bild
    while manual_on():
        color = BLACK
        for pin, pen in PENS:
            if pressed(pin):
                color = pen or mixed(0)
                break
        light(color)
        sleep_ms(5)
    dark()
    wait_release()


def menu():
    item, editing, channel = START, False, 0
    while True:
        if manual_on():
            manual()

        matrix.fill(BLACK)
        if editing:
            draw_value(item, channel)
        else:
            draw_icon(item)
        matrix.write()

        dx, dy = direction()
        if pressed(joy_center):
            wait_release()
            if item == START:
                run()
            else:
                if editing:
                    save_settings()
                editing, channel = not editing, 0
        elif editing and item in (COL_A, COL_B):
            channel = (channel + dx) % 3
            mix = colors[item - COL_A]
            mix[channel] = min(7, max(0, mix[channel] + dy))
        elif editing:
            settings[item] = (settings[item] + dy) % len(OPTIONS[item])
        else:
            item = (item + dx) % len(ICONS)
        sleep_ms(200 if dx or dy else 20)


load_settings()
wait_release()
menu()
