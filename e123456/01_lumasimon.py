# LumaSimon
# Vier farbige Dreiecke auf der Lumatrix. Das Spiel zeigt eine Folge,
# die bei jedem Durchgang um ein Dreieck waechst. Wiederhole sie mit
# dem Joystick. Ein Fehler beendet die Runde, die Mitte startet neu.

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms
from zhaw_led_matrix import Lumatrix, ColorTable
import random

LED_PIN = 19
HELL = 25
AUS_MS = 300
AN_MS = 400
PAUSE_MS = 700

ROT = (HELL, 0, 0)          # oben, Joystick hoch
GELB = (HELL, HELL, 0)      # unten, Joystick runter
BLAU = (0, 0, HELL)         # links, Joystick links
GRUEN = (0, HELL, 0)        # rechts, Joystick rechts
SCHWARZ = (0, 0, 0)
WEISS = (HELL, HELL, HELL)

FARBEN = (ROT, GELB, BLAU, GRUEN)

np = NeoPixel(Pin(LED_PIN, Pin.OUT), 64)
lumatrix = Lumatrix()
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
rechts = Pin(2, Pin.IN, Pin.PULL_UP)
mitte = Pin(8, Pin.IN, Pin.PULL_UP)

ZUEGE = (
    (hoch, ROT),
    (runter, GELB),
    (links, BLAU),
    (rechts, GRUEN),
)


def farbe_bei(y, x):
    if y == x or y + x == 7:
        return SCHWARZ
    if y + x < 7:
        return GELB if y < x else BLAU
    return GRUEN if y < x else ROT


def zeichnen(leer=None, voll=None):
    for y in range(8):
        for x in range(8):
            farbe = voll if voll is not None else farbe_bei(y, x)
            if leer is not None and farbe == leer:
                farbe = SCHWARZ
            np[y * 8 + x] = farbe
    np.write()


def blink(farbe):
    zeichnen(leer=farbe)
    sleep_ms(AUS_MS)
    zeichnen()
    sleep_ms(AN_MS)


def begruessung():
    lumatrix.writeText("LumaSimon", ColorTable.PINK)
    zeichnen()


def warte_mitte():
    while mitte.value() != 0:
        sleep_ms(20)
    while mitte.value() == 0:
        sleep_ms(20)


def lese_zug():
    while True:
        for pin, farbe in ZUEGE:
            if pin.value() == 0:
                while pin.value() == 0:
                    sleep_ms(20)
                return farbe
        sleep_ms(20)


def fehler(punkte):
    for _ in range(3):
        zeichnen(voll=ROT)
        sleep_ms(250)
        zeichnen(voll=SCHWARZ)
        sleep_ms(250)
    lumatrix.writeText("Punkte: " + str(punkte), ColorTable.PINK)
    sleep_ms(500)
    zeichnen()


def runde():
    folge = []
    while True:
        folge.append(random.choice(FARBEN))
        sleep_ms(PAUSE_MS)
        for farbe in folge:
            blink(farbe)
        sleep_ms(PAUSE_MS)
        for erwartet in folge:
            bekommen = lese_zug()
            blink(bekommen)
            if bekommen != erwartet:
                fehler(len(folge) - 1)
                return
#        zeichnen(voll=WEISS)
        sleep_ms(200)
        zeichnen()


while True:
    begruessung()
    warte_mitte()
    runde()



