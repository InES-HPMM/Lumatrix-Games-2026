# ============================================================
# SCHIFFE VERSENKEN - LUMATRIX EDITION
# Mit drehbaren Schiffen und lernender KI
# Raspberry Pi Pico / MicroPython
# ============================================================

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms
import random

# ============================================================
# EINSTELLUNGEN
# ============================================================

LED_PIN = 19
LED_ANZAHL = 64

SCHIFFE = [3, 2, 2, 2]
TEMPO = 140
LANGDRUCK_MS = 600

# Farben
AUS = (0, 0, 0)
WASSER = (0, 0, 18)
TREFFER = (50, 0, 0)
DANEBEN = (25, 25, 25)
SCHIFF = (0, 30, 0)
CURSOR = (40, 18, 0)
STARTFARBE = (0, 25, 35)
SIEG = (0, 45, 0)
VERLUST = (45, 0, 0)
FEHLER = (45, 0, 0)
DREH_FARBE = (35, 0, 35)

np = NeoPixel(Pin(LED_PIN, Pin.OUT), LED_ANZAHL)

rechts = Pin(2, Pin.IN, Pin.PULL_UP)
oben = Pin(3, Pin.IN, Pin.PULL_UP)
unten = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
knopf = Pin(8, Pin.IN, Pin.PULL_UP)


# ============================================================
# LERNENDE KI
# Bleibt zwischen Spielen aktiv, solange das Programm laeuft.
# Hoehere Werte bedeuten: Hier hat die KI schon einmal getroffen.
# ============================================================

ki_erinnerung = [[0 for x in range(8)] for y in range(8)]


# ============================================================
# ANLEITUNG IN DER THONNY-KOMMANDOZEILE
# ============================================================

def anleitung():
    print("")
    print("========================================")
    print("       SCHIFFE VERSENKEN")
    print("========================================")
    print("")
    print("STEUERUNG")
    print("Joystick bewegen: Cursor bewegen")
    print("Kurzer Knopfdruck: Schiff platzieren")
    print("                    oder schiessen")
    print("Langer Knopfdruck: Schiff drehen")
    print("                   (nur beim Platzieren)")
    print("")
    print("SCHIFFPLATZIERUNG")
    print("Du platzierst deine Schiffe selbst.")
    print("Die Vorschau zeigt die aktuelle Richtung.")
    print("Gruen = eigenes Schiff")
    print("Orange = Cursor / Schiffsposition")
    print("Violett = Drehung")
    print("")
    print("IM SPIEL")
    print("Blau = Wasser")
    print("Rot = Treffer")
    print("Weiss = daneben")
    print("")
    print("KI")
    print("Nach einem Treffer sucht sie in der Naehe.")
    print("Sie merkt sich Trefferpositionen zwischen")
    print("den Spielen, solange das Programm laeuft.")
    print("")
    print("Zum Starten den Joystick-Knopf druecken.")
    print("========================================")
    print("")


# ============================================================
# LED- UND JOYSTICK-FUNKTIONEN
# ============================================================

def pixel(x, y, farbe):
    if 0 <= x < 8 and 0 <= y < 8:
        np[y * 8 + x] = farbe


def loeschen():
    for i in range(LED_ANZAHL):
        np[i] = AUS


def anzeigen():
    np.write()


def warte_loslassen():
    while knopf.value() == 0:
        sleep_ms(10)


def warte_knopfdruck():
    while knopf.value() == 1:
        sleep_ms(10)

    warte_loslassen()
    sleep_ms(120)


def knopf_dauer():
    # Misst, wie lange der Knopf gedrueckt bleibt.
    dauer = 0

    while knopf.value() == 0:
        sleep_ms(10)
        dauer += 10

    return dauer


def bewegung(cursor):
    bewegt = False

    if oben.value() == 0:
        cursor[1] = min(7, cursor[1] + 1)
        bewegt = True
    elif unten.value() == 0:
        cursor[1] = max(0, cursor[1] - 1)
        bewegt = True
    elif links.value() == 0:
        cursor[0] = max(0, cursor[0] - 1)
        bewegt = True
    elif rechts.value() == 0:
        cursor[0] = min(7, cursor[0] + 1)
        bewegt = True

    if bewegt:
        sleep_ms(TEMPO)

        while (oben.value() == 0 or unten.value() == 0 or
               links.value() == 0 or rechts.value() == 0):
            sleep_ms(10)

    return bewegt


def neues_raster():
    return [[0 for x in range(8)] for y in range(8)]


# ============================================================
# SCHIFFPLATZIERUNG
# Richtung: 0 = horizontal, 1 = vertikal
# Langer Knopfdruck dreht das Schiff.
# Kurzer Knopfdruck platziert es.
# ============================================================

def platzierung_zeichnen(raster, cursor, laenge, richtung):
    loeschen()

    for y in range(8):
        for x in range(8):
            if raster[y][x] == 1:
                pixel(x, y, SCHIFF)
            else:
                pixel(x, y, WASSER)

    x, y = cursor

    if richtung == 0:
        moeglich = x + laenge <= 8
    else:
        moeglich = y + laenge <= 8

    if moeglich:
        vorschau_farbe = CURSOR
    else:
        vorschau_farbe = FEHLER

    for i in range(laenge):
        if richtung == 0:
            pixel(x + i, y, vorschau_farbe)
        else:
            pixel(x, y + i, vorschau_farbe)

    # Kleine Anzeige der Ausrichtung oben rechts:
    # Violett = vertikal, Orange = horizontal.
    if richtung == 0:
        pixel(7, 7, CURSOR)
    else:
        pixel(7, 7, DREH_FARBE)

    anzeigen()


def platziere_eigene_schiffe():
    raster = neues_raster()
    cursor = [0, 0]

    for nr, laenge in enumerate(SCHIFFE, 1):
        richtung = 0

        print("Platziere Schiff", nr, "mit Laenge", laenge)
        print("Kurzer Druck = platzieren, langer Druck = drehen")

        while True:
            platzierung_zeichnen(
                raster, cursor, laenge, richtung
            )

            if bewegung(cursor):
                continue

            if knopf.value() == 0:
                dauer = knopf_dauer()

                # Langer Druck: Richtung wechseln.
                if dauer >= LANGDRUCK_MS:
                    richtung = 1 - richtung
                    print("Ausrichtung gewechselt")
                    sleep_ms(180)
                    continue

                x, y = cursor

                if richtung == 0:
                    felder = [
                        (x + i, y) for i in range(laenge)
                    ]
                else:
                    felder = [
                        (x, y + i) for i in range(laenge)
                    ]

                # Schiff muss vollstaendig im Spielfeld liegen.
                innerhalb = all(
                    0 <= fx < 8 and 0 <= fy < 8
                    for fx, fy in felder
                )

                if not innerhalb:
                    print("Zu nah am Rand! Andere Position waehlen.")
                    sleep_ms(250)
                    continue

                # Keine Ueberlappung mit bereits platzierten Schiffen.
                frei = all(
                    raster[fy][fx] == 0
                    for fx, fy in felder
                )

                if not frei:
                    print("Schiffe duerfen sich nicht ueberlappen.")
                    sleep_ms(250)
                    continue

                for fx, fy in felder:
                    raster[fy][fx] = 1

                print("Schiff platziert.")
                sleep_ms(250)
                break

            sleep_ms(20)

    print("Alle eigenen Schiffe sind platziert!")
    return raster


def platziere_computer_schiffe():
    raster = neues_raster()

    for laenge in SCHIFFE:
        while True:
            horizontal = random.randint(0, 1) == 0

            if horizontal:
                x = random.randint(0, 8 - laenge)
                y = random.randint(0, 7)
                felder = [(x + i, y) for i in range(laenge)]
            else:
                x = random.randint(0, 7)
                y = random.randint(0, 8 - laenge)
                felder = [(x, y + i) for i in range(laenge)]

            if all(raster[fy][fx] == 0 for fx, fy in felder):
                for fx, fy in felder:
                    raster[fy][fx] = 1
                break

    return raster


# ============================================================
# SPIELFELDER ANZEIGEN
# ============================================================

def zeichne_gegnerfeld(beschossen, cursor):
    loeschen()

    for y in range(8):
        for x in range(8):
            if beschossen[y][x] == 1:
                pixel(x, y, TREFFER)
            elif beschossen[y][x] == 2:
                pixel(x, y, DANEBEN)
            else:
                pixel(x, y, WASSER)

    pixel(cursor[0], cursor[1], CURSOR)
    anzeigen()


def zeichne_eigenes_feld(raster, beschossen):
    loeschen()

    for y in range(8):
        for x in range(8):
            if beschossen[y][x] == 1:
                pixel(x, y, TREFFER)
            elif beschossen[y][x] == 2:
                pixel(x, y, DANEBEN)
            elif raster[y][x] == 1:
                pixel(x, y, SCHIFF)
            else:
                pixel(x, y, WASSER)

    anzeigen()


def treffer_zaehlen(beschossen):
    anzahl = 0

    for y in range(8):
        for x in range(8):
            if beschossen[y][x] == 1:
                anzahl += 1

    return anzahl


# ============================================================
# KI: TREFFER VERFOLGEN UND POSITIONEN MERKEN
# ============================================================

def ki_schuss(raster, beschossen, ki_treffer):
    prioritaet = []
    treffer_set = set(ki_treffer)

    def ziel_hinzufuegen(x, y):
        if 0 <= x < 8 and 0 <= y < 8:
            if beschossen[y][x] == 0:
                punkt = (x, y)

                if punkt not in prioritaet:
                    prioritaet.append(punkt)

    # Wenn bereits zwei Treffer nebeneinander liegen,
    # zuerst entlang dieser Linie weitersuchen.
    for hx, hy in reversed(ki_treffer):
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            if (hx + dx, hy + dy) in treffer_set:
                ziel_hinzufuegen(hx + 2 * dx, hy + 2 * dy)

    # Danach direkt angrenzende Felder der letzten Treffer pruefen.
    if ki_treffer:
        hx, hy = ki_treffer[-1]

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            ziel_hinzufuegen(hx + dx, hy + dy)

    # Weitere offene Nachbarfelder frueherer Treffer.
    for hx, hy in reversed(ki_treffer):
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            ziel_hinzufuegen(hx + dx, hy + dy)

    if prioritaet:
        x, y = prioritaet[0]

    else:
        # Keine aktiven Treffer verfolgen:
        # Zuerst Felder bevorzugen, an denen die KI
        # in frueheren Spielen bereits Schiffe getroffen hat.
        beste_felder = []
        bester_wert = 0

        for y0 in range(8):
            for x0 in range(8):
                if beschossen[y0][x0] != 0:
                    continue

                wert = ki_erinnerung[y0][x0]

                if wert > bester_wert:
                    bester_wert = wert
                    beste_felder = [(x0, y0)]
                elif wert == bester_wert and wert > 0:
                    beste_felder.append((x0, y0))

        if beste_felder:
            x, y = random.choice(beste_felder)
        else:
            # Noch keine hilfreichen Erinnerungen: zufaellig suchen.
            moeglich = []

            for y0 in range(8):
                for x0 in range(8):
                    if beschossen[y0][x0] == 0:
                        moeglich.append((x0, y0))

            if not moeglich:
                return

            x, y = random.choice(moeglich)

    # Schuss auswerten und Trefferposition lernen.
    if raster[y][x] == 1:
        beschossen[y][x] = 1
        ki_treffer.append((x, y))

        # Erinnerung fuer kommende Spiele erhoehen.
        ki_erinnerung[y][x] += 1

        print("KI trifft bei x =", x, "y =", y)
        print("KI merkt sich diese Position fuer spaetere Spiele.")
    else:
        beschossen[y][x] = 2
        print("KI schiesst daneben bei x =", x, "y =", y)


# ============================================================
# SPIELABLAUF
# ============================================================

def endbild(farbe):
    loeschen()

    for i in range(8):
        pixel(i, i, farbe)
        pixel(7 - i, i, farbe)

    anzeigen()
    sleep_ms(1800)


def spiel():
    eigene_schiffe = platziere_eigene_schiffe()
    gegner_schiffe = platziere_computer_schiffe()

    eigene_schuesse = neues_raster()
    gegner_schuesse = neues_raster()
    ki_treffer = []

    cursor = [3, 3]

    print("")
    print("Das Spiel beginnt!")
    print("Rot = Treffer, Weiss = daneben")
    print("")

    while True:
        # ---------------- DEIN ZUG ----------------
        while True:
            zeichne_gegnerfeld(eigene_schuesse, cursor)

            if bewegung(cursor):
                continue

            if knopf.value() == 0:
                x, y = cursor

                if eigene_schuesse[y][x] != 0:
                    print("Dieses Feld hast du schon beschossen.")
                    warte_loslassen()
                    continue

                if gegner_schiffe[y][x] == 1:
                    eigene_schuesse[y][x] = 1
                    print("TREFFER!")
                else:
                    eigene_schuesse[y][x] = 2
                    print("DANEBEN!")

                warte_loslassen()
                break

            sleep_ms(20)

        # Schussresultat sofort anzeigen, ohne Cursor.
        zeichne_gegnerfeld(eigene_schuesse, [-1, -1])
        sleep_ms(1000)

        if treffer_zaehlen(eigene_schuesse) == sum(SCHIFFE):
            print("Du hast gewonnen!")
            endbild(SIEG)
            return

        # ---------------- KI-ZUG ----------------
        ki_schuss(
            eigene_schiffe,
            gegner_schuesse,
            ki_treffer
        )

        # Dein eigenes Feld zeigt sofort, wo die KI getroffen hat.
        zeichne_eigenes_feld(eigene_schiffe, gegner_schuesse)
        sleep_ms(1000)

        print("Knopf druecken, um weiterzuspielen.")
        warte_knopfdruck()

        if treffer_zaehlen(gegner_schuesse) == sum(SCHIFFE):
            print("Die KI hat gewonnen!")
            endbild(VERLUST)
            return

# ============================================================
# PROGRAMMSTART
# ============================================================

anleitung()

while True:
    loeschen()

    for x in range(8):
        pixel(x, 3, STARTFARBE)
        pixel(x, 4, STARTFARBE)

    anzeigen()

    print("Joystick-Knopf druecken, um zu starten.")
    warte_knopfdruck()

    spiel()

    print("")
    print("Neue Runde: Die KI behaelt ihre Treffer-Erinnerung.")
    print("Joystick-Knopf druecken, um eine neue Runde zu starten.")

    warte_knopfdruck()
    sleep_ms(400)