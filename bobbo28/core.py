from machine import Pin
from neopixel import NeoPixel
import random
from time import sleep_ms, ticks_ms, ticks_diff
import gc
gc.collect()
LED_BRIGHTNESS_PERCENT = 10
class DimNeoPixel:
    def __init__(self, pin, count):
        self._strip = NeoPixel(pin, count)
    def _dim(self, color):
        return tuple((int(channel) * LED_BRIGHTNESS_PERCENT) // 100 for channel in color)
    def __setitem__(self, index, color):
        self._strip[index] = self._dim(color)
    def __getitem__(self, index):
        return self._strip[index]
    def fill(self, color):
        self._strip.fill(self._dim(color))
    def write(self):
        self._strip.write()
def heist_level_animation(set_xy, clear, show, sleep_ms, GREEN, CYAN):
    for radius in range(1, 5):
        clear()
        left, right = 4 - radius, 3 + radius
        bottom, top = 4 - radius, 3 + radius
        for x in range(max(0, left), min(8, right + 1)):
            for y in range(max(0, bottom), min(8, top + 1)):
                set_xy(x, y, GREEN if (x + y + radius) % 2 == 0 else CYAN)
        show()
        sleep_ms(120)
    clear()
    show()
def heist_victory_animation(set_xy, clear, show, fill, sleep_ms, GREEN, CYAN):
    for _ in range(2):
        clear()
        for d in range(8):
            for x in range(8):
                y = d - x
                if 0 <= y < 8:
                    set_xy(x, y, GREEN)
            show()
            sleep_ms(60)
    for _ in range(5):
        fill(GREEN)
        sleep_ms(100)
        fill(CYAN)
        sleep_ms(100)
    clear()
    show()
def shuffle_list(items):
    """Shuffle a list in place; compatible with MicroPython."""
    for i in range(len(items) - 1, 0, -1):
        j = random.randint(0, i)
        items[i], items[j] = items[j], items[i]
ARCADE_LED_PIN = 19
ARCADE_LED_COUNT = 64
np = DimNeoPixel(Pin(ARCADE_LED_PIN, Pin.OUT), ARCADE_LED_COUNT)
LEFT = Pin(7, Pin.IN)
RIGHT = Pin(2, Pin.IN)
UP = Pin(3, Pin.IN)
DOWN = Pin(6, Pin.IN)
CENTER = Pin(8, Pin.IN)
OFF = (0, 0, 0)
WHITE = (80, 80, 80)
HEIST = (255, 190, 0)
SNAKE = (0, 255, 0)
SPACE = (170, 0, 255)  
HACKER = (0, 255, 255)
def arcade_clear():
    np.fill(OFF)
    np.write()
def arcade_set(x, y, color):
    if 0 <= x < 8 and 0 <= y < 8:
        np[x + y * 8] = color
def arcade_show():
    np.write()
def arcade_read():
    if UP.value() == 0:
        return "up"
    if DOWN.value() == 0:
        return "down"
    if LEFT.value() == 0:
        return "left"
    if RIGHT.value() == 0:
        return "right"
    if CENTER.value() == 0:
        return "center"
    return None
def arcade_release():
    while (
        UP.value() == 0 or
        DOWN.value() == 0 or
        LEFT.value() == 0 or
        RIGHT.value() == 0 or
        CENTER.value() == 0
    ):
        sleep_ms(20)
def arcade_wait_center():
    arcade_release()
    while CENTER.value() != 0:
        sleep_ms(20)
    sleep_ms(120)
    arcade_release()
SPRITES = [
    ["........", "........", "..GGGG..", "..G..G.R",
     "..GB.G..", ".....G..", ".Y...G..", "........"],
    ["........", ".KKKKKYY", "..W.W.YY", "..W.W.YY",
     ".KKKKK..", ".WWWWW..", ".KKKKK..", ".K...K.."],
    ["........", "...RRR..", "..RRRRR.", "..ORRRR.",
     "..AORRR.", ".AOAOWW.", ".OA..WW.", "........"],
    [".P....P.", "..P..P..", "P.PPPP.P", "P.P.RP.P",
     ".PPPPPP.", "..PPPP..", "..P..P..", "........"],
]
SPRITE_PALETTE = {
    ".": OFF,
    "G": (0, 255, 0), "Y": (255, 255, 0),
    "R": (255, 0, 0), "B": (0, 0, 255),
    "K": (102, 102, 102), "W": WHITE,
    "P": (255, 0, 255), "O": (219, 150, 0),
    "A": (255, 202, 87),
}
GAME_NAMES = ["HEIST", "SNAKE", "PING PONG", "CYBER VIRUS"]
SPRITE_COLORS = [HEIST, SNAKE, SPACE, HACKER]
def draw_arcade_menu(selected, hint_on=True):
    arcade_clear()
    sprite = SPRITES[selected]
    for y in range(8):
        for x in range(8):
            pixel = sprite[y][x]
            if pixel != ".":
                arcade_set(x, 7 - y, SPRITE_PALETTE.get(pixel, SPRITE_COLORS[selected]))
    if hint_on:
        arcade_set(0, 0, WHITE)
        arcade_set(7, 0, WHITE)
    arcade_show()
def arcade_boot():
    colors = (HEIST, SNAKE, SPACE, HACKER)
    while CENTER.value() != 0:
        for step in range(15):
            arcade_clear()
            for y in range(8):
                for x in range(8):
                    distance = (x + y + step) % 8
                    if distance in (0, 1):
                        arcade_set(x, y, colors[(x + y + step // 3) % len(colors)])
            arcade_show()
            sleep_ms(55)
            if CENTER.value() == 0:
                break
    arcade_clear()
    arcade_release()
    sleep_ms(120)
def arcade_menu():
    selected = 0
    last_input = ticks_ms()
    pulse_time = ticks_ms()
    hint_on = True
    draw_arcade_menu(selected, hint_on)
    while True:
        now = ticks_ms()
        if ticks_diff(now, pulse_time) >= 400:
            hint_on = not hint_on
            pulse_time = now
            draw_arcade_menu(selected, hint_on)
        if ticks_diff(now, last_input) >= 130:
            inp = arcade_read()
            if inp in ("left", "right"):
                selected = (selected + (1 if inp == "right" else -1)) % len(SPRITES)
                last_input = now
                arcade_release()
                draw_arcade_menu(selected, True)
            elif inp == "center":
                arcade_release()
                sleep_ms(120)
                return selected
        sleep_ms(10)
_RESULT_FONT = {
    'W': ("101", "101", "101", "111", "101"),
    'I': ("111", "010", "010", "010", "111"),
    'N': ("101", "111", "111", "111", "101"),
    'G': ("111", "100", "101", "101", "111"),
    'A': ("010", "101", "111", "101", "101"),
    'M': ("101", "111", "111", "101", "101"),
    'E': ("111", "100", "110", "100", "111"),
    'O': ("111", "101", "101", "101", "111"),
    'V': ("101", "101", "101", "101", "010"),
    'R': ("110", "101", "110", "101", "101"),
    ' ': ("000", "000", "000", "000", "000"),
}
def arcade_result_screen(won):
    # Mostra prima la scritta scorrevole, come nella versione originale.
    message = "WIN" if won else "GAME OVER"
    color = SNAKE if won else (255, 0, 0)
    width = len(message) * 4 - 1
    for offset in range(8, -width - 1, -1):
        arcade_clear()
        for ci, char in enumerate(message):
            glyph = _RESULT_FONT.get(char, _RESULT_FONT[' '])
            gx = offset + ci * 4
            for gy, row in enumerate(glyph):
                for px, bit in enumerate(row):
                    x = gx + px
                    y = 5 - gy
                    if bit == '1' and 0 <= x < 8:
                        arcade_set(x, y, color)
        arcade_show()
        sleep_ms(95 if won else 115)

    if won:
        # animazioni di vittoria
        animation = random.randint(0, 3)
        animation = random.randint(0, 3)

        # 1 - Fuochi d'artificio
        if animation == 0:
            cx = random.choice([2, 3, 4, 5])
            cy = random.choice([2, 3, 4, 5])
            for radius in range(1, 9):
                arcade_clear()
                for x in range(8):
                    for y in range(8):
                        dx = x - cx
                        dy = y - cy
                        dist = int((dx*dx + dy*dy) ** 0.5)
                        if dist == radius:
                            arcade_set(
                                x, y,
                                random.choice([
                                    (0, 255, 0),
                                    (0, 150, 255),
                                    (255, 0, 200),
                                    (255, 255, 0)
                                ])
                            )
                arcade_show()
                sleep_ms(random.randint(100, 220))

        # 2 - Confetti colorati
        elif animation == 1:
            for frame in range(18):
                arcade_clear()
                for i in range(18):
                    x = random.randint(0, 7)
                    y = (random.randint(0, 7) + frame) % 8
                    arcade_set(
                        x, y,
                        random.choice([
                            (0, 255, 0),
                            (0, 150, 255),
                            (255, 0, 200),
                            (255, 150, 0),
                            (255, 255, 0)
                        ])
                    )
                arcade_show()
                sleep_ms(180)

        # 3 - Quadrato luminoso
        elif animation == 2:
            for radius in range(1, 8):
                arcade_clear()
                for x in range(8):
                    for y in range(8):
                        if (
                            x == 3 - radius or
                            x == 4 + radius or
                            y == 3 - radius or
                            y == 4 + radius
                        ):
                            if 0 <= 3 - radius <= x <= 4 + radius <= 7:
                                arcade_set(x, y, (0, 255, 100))
                            elif 0 <= y <= 7:
                                arcade_set(x, y, (0, 150, 255))
                arcade_show()
                sleep_ms(random.randint(100, 220))

        # 4 - Esplosione di stelle
        else:
            stars = [
                (0, 0), (7, 0), (0, 7), (7, 7),
                (3, 0), (4, 0), (0, 3), (0, 4),
                (7, 3), (7, 4), (3, 7), (4, 7)
            ]

            for frame in range(8):
                arcade_clear()
                for i, (x, y) in enumerate(stars):
                    if (i + frame) % 4 != 0:
                        arcade_set(
                            x, y,
                            random.choice([
                                (0, 255, 0),
                                (255, 255, 0),
                                (0, 150, 255)
                            ])
                        )
                arcade_show()
                sleep_ms(180)

    else:
        # GAME OVER: mantiene la X rossa
        for frame in range(4):
            arcade_clear()
            for i in range(8):
                arcade_set(i, i, (255, 0, 0))
                arcade_set(7 - i, i, (255, 0, 0))
            arcade_show()
            sleep_ms(180)
    arcade_clear()
    arcade_show()
_LEVEL_FONT = {
    "L": ("100", "100", "100", "100", "111"),
    "v": ("000", "000", "101", "101", "010"),
    " ": ("000", "000", "000", "000", "000"),
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "110", "101", "010"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("010", "101", "010", "101", "010"),
    "9": ("010", "101", "011", "001", "110"),
}
def show_level_intro(level):
    label = "Lv " + str(level)
    text_width = len(label) * 4 - 1
    for offset in range(8, -text_width - 1, -1):
        arcade_clear()
        for ci, char in enumerate(label):
            glyph = _LEVEL_FONT.get(char, _LEVEL_FONT[" "])
            gx = offset + ci * 4
            for gy, row in enumerate(glyph):
                for px, bit in enumerate(row):
                    x = gx + px
                    y = 6 - gy
                    if bit == "1" and 0 <= x < 8 and 0 <= y < 8:
                        arcade_set(x, y, HEIST if char == "L" else HACKER)
        arcade_show()
        sleep_ms(90)
    arcade_clear()
    arcade_show()
    sleep_ms(100)
