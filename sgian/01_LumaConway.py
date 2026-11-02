# LumaConway
# Game of Life auf der Lumatrix. Joystick bewegt den Cursor, kurzer Klick
# schaltet eine Zelle um. Langer Druck startet oder stoppt die Simulation.
# S1 schaltet zwischen zwei Farben und Regenbogen-Alter.
# Muster-Ideen: https://www.gameoflifelab.com/patterns

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms, ticks_ms, ticks_diff
from zhaw_led_matrix import Lumatrix, CharacterTable

LED_PIN = 19
HELL = 75
CURSOR = (HELL, HELL, HELL)
LEBEND = (0, HELL, 0)
TOT = (0, 0, 0)
SCHRITT_MS = 500 # Pause zwischen den Generationen in Millisekunden
LANG_MS = 800

FARBEN = (
    (HELL, 0, 0),
    (HELL, HELL // 2, 0),
    (HELL, HELL, 0),
    (0, HELL, 0),
    (0, 0, HELL),
    (HELL // 2, 0, HELL),
)

np = NeoPixel(Pin(LED_PIN, Pin.OUT), 64)
lumatrix = Lumatrix()
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
rechts = Pin(2, Pin.IN, Pin.PULL_UP)
mitte = Pin(8, Pin.IN, Pin.PULL_UP)
s1 = Pin(9, Pin.IN, Pin.PULL_UP)

gitter = [[False] * 8 for _ in range(8)]
alter = [[0] * 8 for _ in range(8)]
cx, cy = 3, 3
s1_letzter = s1.value()


def regenbogen_an():
    return s1.value() == 0


def begruessung():
    text, laenge = CharacterTable.convert_str("LumaConway")
    farben = [FARBEN[i % 6] for i in range(len(text))]
    lumatrix._matrix.set_brightness(20)
    lumatrix._matrix.move_across(text, laenge, colors=farben)
    sleep_ms(50)


def leeren():
    for y in range(8):
        for x in range(8):
            gitter[y][x] = False
            alter[y][x] = 0


def farbe_fuer(a):
    if a <= 0:
        return TOT
    if a > 6:
        a = 6
    return FARBEN[a - 1]


def zeichnen(cursor=True):
    regen = regenbogen_an()
    for y in range(8):
        for x in range(8):
            if cursor and x == cx and y == cy:
                np[y * 8 + x] = CURSOR
            elif gitter[y][x]:
                np[y * 8 + x] = farbe_fuer(alter[y][x]) if regen else LEBEND
            else:
                np[y * 8 + x] = TOT
    np.write()


def nachbarn(x, y):
    n = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            if gitter[(y + dy) % 8][(x + dx) % 8]:
                n += 1
    return n


def schritt():
    neu = [[False] * 8 for _ in range(8)]
    for y in range(8):
        for x in range(8):
            n = nachbarn(x, y)
            if gitter[y][x]:
                neu[y][x] = n == 2 or n == 3
            else:
                neu[y][x] = n == 3
    for y in range(8):
        for x in range(8):
            if neu[y][x]:
                alter[y][x] = alter[y][x] + 1 if gitter[y][x] else 1
            else:
                alter[y][x] = 0
            gitter[y][x] = neu[y][x]


def warte_loslassen(pin):
    while pin.value() == 0:
        sleep_ms(15)


def s1_geaendert():
    global s1_letzter
    jetzt = s1.value()
    if jetzt != s1_letzter:
        s1_letzter = jetzt
        return True
    return False


def lesen_richtung():
    if hoch.value() == 0:
        warte_loslassen(hoch)
        return 0, 1
    if runter.value() == 0:
        warte_loslassen(runter)
        return 0, -1
    if links.value() == 0:
        warte_loslassen(links)
        return -1, 0
    if rechts.value() == 0:
        warte_loslassen(rechts)
        return 1, 0
    return None


def editieren():
    global cx, cy
    zeichnen()
    while True:
        if s1_geaendert():
            zeichnen()
            continue
        r = lesen_richtung()
        if r:
            dx, dy = r
            cx = (cx + dx) % 8
            cy = (cy + dy) % 8
            zeichnen()
            continue
        if mitte.value() == 0:
            gehalten = ticks_ms()
            lang = False
            while mitte.value() == 0:
                if ticks_diff(ticks_ms(), gehalten) > LANG_MS:
                    lang = True
                    break
                sleep_ms(20)
            warte_loslassen(mitte)
            if lang:
                return
            if gitter[cy][cx]:
                gitter[cy][cx] = False
                alter[cy][cx] = 0
            else:
                gitter[cy][cx] = True
                alter[cy][cx] = 1
            zeichnen()
        sleep_ms(20)


def simulieren():
    while True:
        if s1_geaendert():
            zeichnen(cursor=False)
        schritt()
        zeichnen(cursor=False)
        start = ticks_ms()
        while ticks_diff(ticks_ms(), start) < SCHRITT_MS:
            if s1_geaendert():
                zeichnen(cursor=False)
            if mitte.value() == 0:
                gehalten = ticks_ms()
                lang = False
                while mitte.value() == 0:
                    if ticks_diff(ticks_ms(), gehalten) > LANG_MS:
                        lang = True
                        break
                    sleep_ms(20)
                warte_loslassen(mitte)
                if lang:
                    return
            sleep_ms(20)


begruessung()
while True:
    editieren()
    simulieren()


