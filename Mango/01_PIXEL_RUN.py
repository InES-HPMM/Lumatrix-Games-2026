# Lumatrix – Ein Spiel für die 8x8-LED-Matrix

# Weiche Zügen und Vögeln aus und springe zwischen drei Ebenen.

# Sammle Punkte und versuche, möglichst lange zu überleben.
 
from machine import Pin

import neopixel

import utime

import random

import math
 
# ---------------- EINSTELLUNGEN ----------------
 
LED_PIN = 19

LED_ANZAHL = 64
 
JOYSTICK_RECHTS = 2

JOYSTICK_OBEN = 3

JOYSTICK_UNTEN = 6

JOYSTICK_LINKS = 7

JOYSTICK_DRUECKEN = 8
 
SPIELER_X = 1
 
# Zeit zwischen den Bewegungen in Millisekunden

SPIEL_GESCHWINDIGKEIT = 450
 
# Farben

AUS = (0, 0, 0)

SPIELER_FARBE = (40, 40, 40)

ZUG_FARBE = (40, 0, 0)

VOGEL_FARBE = (40, 20, 0)

STEG_FARBE = (18, 18, 18)

PISSE_FARBE = (18, 24, 0)

LINIE_FARBE = (0, 0, 20)

PUNKT_FARBE = (0, 35, 0)

ENDE_FARBE = (40, 0, 0)
 
# Ebenen

KANAL = 0

ZUGGLEISE = 1

LUFT = 2
 
# Spielerhöhe je Ebene

EBENEN_Y = [1, 3, 6]
 
# ---------------- HARDWARE ----------------
 
matrix = neopixel.NeoPixel(Pin(LED_PIN), LED_ANZAHL)
 
rechts = Pin(JOYSTICK_RECHTS, Pin.IN, Pin.PULL_UP)

oben = Pin(JOYSTICK_OBEN, Pin.IN, Pin.PULL_UP)

unten = Pin(JOYSTICK_UNTEN, Pin.IN, Pin.PULL_UP)

links = Pin(JOYSTICK_LINKS, Pin.IN, Pin.PULL_UP)

druecken = Pin(JOYSTICK_DRUECKEN, Pin.IN, Pin.PULL_UP)
 
 
def led(x, y, farbe):

    if 0 <= x < 8 and 0 <= y < 8:

        matrix[y * 8 + x] = farbe
 
 
def alles_loeschen():

    for i in range(LED_ANZAHL):

        matrix[i] = AUS
 
 
def bild_anzeigen():

    matrix.write()
 
 
# ---------------- SPIELWELT ----------------
 
stege = [True] * 8

zuege = [False] * 8

voegel = [False] * 8
 
ebene = KANAL

punkte = 0

spiel_aktiv = True
 
letzte_aktion = 0

letzte_bewegung = 0
 
# Die sichere Ebene beginnt unten.

sichere_ebene_alt = KANAL
 
 
def welt_zuruecksetzen():

    global stege, zuege, voegel, sichere_ebene_alt
 
    stege = [True] * 8

    zuege = [False] * 8

    voegel = [False] * 8
 
    sichere_ebene_alt = KANAL
 
 
def welt_bewegen():

    global stege, zuege, voegel, sichere_ebene_alt
 
    stege.pop(0)

    zuege.pop(0)

    voegel.pop(0)
 
    # Der sichere Weg kann sich nur um eine Ebene verändern.

    moegliche_ebenen = [sichere_ebene_alt]
 
    if sichere_ebene_alt > KANAL:

        moegliche_ebenen.append(sichere_ebene_alt - 1)
 
    if sichere_ebene_alt < LUFT:

        moegliche_ebenen.append(sichere_ebene_alt + 1)
 
    sichere_ebene = random.choice(moegliche_ebenen)

    sichere_ebene_alt = sichere_ebene
 
    # Auf der sicheren Ebene ist der Weg frei.

    neuer_steg = (

        sichere_ebene == KANAL or random.random() < 0.75

    )
 
    neuer_zug = (

        sichere_ebene != ZUGGLEISE and random.random() < 0.45

    )
 
    neuer_vogel = (

        sichere_ebene != LUFT and random.random() < 0.45

    )
 
    stege.append(neuer_steg)

    zuege.append(neuer_zug)

    voegel.append(neuer_vogel)
 
 
# ---------------- ZEICHNEN ----------------
 
def zeichne_spiel():

    alles_loeschen()
 
    # Kanalisation: Pisse unten, Steg darüber.

    for x in range(8):

        led(x, 0, PISSE_FARBE)
 
        if stege[x]:

            led(x, 1, STEG_FARBE)
 
    # Blaue Linien sind jeweils nur eine LED hoch.

    for x in range(8):

        led(x, 2, LINIE_FARBE)

        led(x, 5, LINIE_FARBE)
 
    # Züge sind zwei LEDs hoch.

    for x in range(8):

        if zuege[x]:

            led(x, 3, ZUG_FARBE)

            led(x, 4, ZUG_FARBE)
 
    # Vögel fliegen in der oberen Ebene.

    for x in range(8):

        if voegel[x]:

            led(x, 6, VOGEL_FARBE)
 
    # Punktestand als grüne Leiste.

    for x in range(min(punkte, 8)):

        led(x, 7, PUNKT_FARBE)
 
    # Spieler zuletzt zeichnen.

    led(SPIELER_X, EBENEN_Y[ebene], SPIELER_FARBE)
 
    bild_anzeigen()
 
 
def zeichne_ende():

    alles_loeschen()
 
    # Rotes X zeigt Game Over.

    for i in range(8):

        led(i, i, ENDE_FARBE)

        led(i, 7 - i, ENDE_FARBE)
 
    bild_anzeigen()
 
 
# ---------------- STEUERUNG ----------------
 
def steuerung():
    global ebene, letzte_aktion
 
    # Nur reagieren, wenn der Joystick neu gedrückt wird.
    if oben.value() == 0 and letzte_aktion != 1:
        if ebene < LUFT:
            ebene += 1
        letzte_aktion = 1
 
    elif unten.value() == 0 and letzte_aktion != 2:
        if ebene > KANAL:
            ebene -= 1
        letzte_aktion = 2
 
    # Joystick losgelassen: nächste Bewegung erlauben.
    elif oben.value() == 1 and unten.value() == 1:
        letzte_aktion = 0
 
 
# ---------------- KOLLISION ----------------
 
def kollidiert():

    x = SPIELER_X
 
    if ebene == KANAL and not stege[x]:

        return True
 
    if ebene == ZUGGLEISE and zuege[x]:

        return True
 
    if ebene == LUFT and voegel[x]:

        return True
 
    return False
 
 
# ---------------- SPIELSTART ----------------
 
def spiel_starten():

    global ebene, punkte, spiel_aktiv
 
    ebene = KANAL

    punkte = 0

    spiel_aktiv = True
 
    welt_zuruecksetzen()

    zeichne_spiel()
 
 
# ---------------- HAUPTPROGRAMM ----------------
 
spiel_starten()

letzte_bewegung = utime.ticks_ms()
 
while True:
 
    if spiel_aktiv:
 
        steuerung()
 
        jetzt = utime.ticks_ms()
 
        # Hindernisse in gleichmässigen Zeitabständen bewegen.

        if utime.ticks_diff(jetzt, letzte_bewegung) >= SPIEL_GESCHWINDIGKEIT:

            letzte_bewegung = jetzt
 
            welt_bewegen()

            punkte += 1
 
            if kollidiert():

                spiel_aktiv = False

                zeichne_ende()

            else:

                zeichne_spiel()
 
    else:

        # Joystick drücken, um neu zu starten.

        if druecken.value() == 0:

            utime.sleep_ms(250)

            spiel_starten()

            letzte_bewegung = utime.ticks_ms()
 
    utime.sleep_ms(5)
 