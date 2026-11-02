# NOX DUNGEON 3D - 3D-Labyrinth fuer die Lumatrix (8x8 NeoPixel)
# Version 1.0 - von Mischa Joel Thie
#
# Beim Start laeuft ein Intro (Joystick Mitte = ueberspringen):
# Herzschlag -> Flug durchs Labyrinth -> Name -> Levelauswahl baut sich auf
#
# Du stehst in einem Labyrinth und siehst es aus der Ich-Perspektive.
# Finde die gruen leuchtende Wand - das ist der Ausgang!
#
# 64 Level = 64 Pixel. Im Levelauswahl-Screen ist jede Zeile ein Sektor
# mit 8 Leveln. Jeder Sektor bringt etwas Neues:
#   Sektor 1: Grundlagen
#   Sektor 2: 1 Schluessel  - erst alle Schluessel holen, dann geht der Ausgang auf
#   Sektor 3: 2 Schluessel
#   Sektor 4: 3 Schluessel
#   Sektor 5: Dunkelheit    - man sieht nur noch, was ganz nah ist
#   Sektor 6: Farbige Tueren - jede Tuer braucht den Schluessel in ihrer Farbe
#   Sektor 7: Teleporter    - der Weg zum Ausgang fuehrt nur durch das Portal
#   Sektor 8: Finale        - alles gemischt, mit Zeitlimit
#
# Steuerung im Spiel:
#   Joystick oben / unten:   vorwaerts / rueckwaerts
#   Joystick links / rechts: drehen
#   Joystick Mitte halten:   3 Sek. = zurueck zur Levelauswahl
#   Schiebeschalter:         Karte von oben (zeigt nur, wo du schon warst)
#
# In der Levelauswahl:
#   Joystick Mitte kurz:     Level starten
#   Joystick Mitte halten:   5 Sek. = Fortschritt loeschen ("RESET DONE!")
#                            vorher loslassen = abbrechen
#
# Levelstart: Ansage "LEVEL 12 - SEKTOR 2" -> Pixel fallen herunter und bauen
#             das Bild auf -> "GO!". Beim ersten Level eines Sektors sagt die
#             Ansage auch, was neu ist (z.B. "TELEPORTER").
# Levelende:  gruener Ring -> benoetigte Zeit als Lauftext
#
# Demo-Modus: 20 Sek. ohne Eingabe in der Levelauswahl -> das Spiel spielt sich
#             selbst, genau wie beim Spielen (Ansage, "GO!", Zeit am Schluss),
#             jedes Mal ein zufaelliges Level aus einem anderen Sektor.
#             Jede Joystick-Bewegung beendet die Demo.
#
# Anzeige oben links: Schluessel. Unterste Zeile: verbleibende Zeit.
#
# Technik: Raycasting. Fuer jede der 8 Spalten werden 2 Strahlen
# in die Welt geschickt (Kantenglaettung). Die Entfernung zur Wand
# bestimmt, wie hoch und wie hell die Wand gezeichnet wird.
# Schluessel und Teleporter sind leuchtende Kugeln, die von Waenden
# verdeckt werden koennen.
#
# Jedes Labyrinth wird zufaellig erzeugt (Tiefensuche). Der Ausgang liegt
# immer in der am weitesten entfernten Sackgasse. Schluessel, Tueren und
# Teleporter werden mit einer Breitensuche so platziert, dass jedes Level
# garantiert loesbar ist (jeder Schluessel liegt vor seiner Tuer).
#
# Der Autopilot (Intro und Demo) plant seinen Weg selbst: Breitensuche zum
# jeweils naechsten Schluessel, am Schluss zum Ausgang. Er merkt sich, welche
# Tuerschluessel er traegt und welche Tueren offen sind. Teleporter sind fuer
# ihn Spruenge auf die andere Seite des Labyrinths.
#
# Geschwindigkeit: Die Funktionen, die in jedem Bild laufen, werden mit
# @micropython.native als Maschinencode uebersetzt. Haeufig gebrauchte
# Werte (LED-Nummern, Abstaende, Strahlrichtungen) sind vorberechnet.
#
# Der Fortschritt wird in "fortschritt.txt" auf dem Pico gespeichert.
# Datei loeschen = Fortschritt zuruecksetzen.

from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms, ticks_ms, ticks_diff, ticks_add
import gc
import math
import micropython
import random

np = NeoPixel(Pin(19, Pin.OUT), 64)
joystick_oben = Pin(3, Pin.IN)
joystick_unten = Pin(6, Pin.IN)
joystick_links = Pin(7, Pin.IN)
joystick_rechts = Pin(2, Pin.IN)
joystick_mitte = Pin(8, Pin.IN)
schalter = Pin(9, Pin.IN)
JOYSTICK = (joystick_oben, joystick_unten, joystick_links, joystick_rechts, joystick_mitte)

# Name des Spiels, wird im Intro angezeigt (Grossbuchstaben, Ziffern und Leerzeichen)
NAME = "NOX DUNGEON 3D"
VERSION = "V1.0"
AUTOR = "MISCHA JOEL THIE"

# Maximale Helligkeit (0.0 bis 1.0)
HELLIGKEIT = 0.35

TEMPO = 1.6        # Felder pro Sekunde
DREHTEMPO = 2.4    # Radiant pro Sekunde (6.28 = eine ganze Drehung)
RADIUS = 0.25      # so "dick" ist die Spielfigur
SICHTFELD = 0.66   # Breite des Blickfelds
WANDHOEHE = 4 / SICHTFELD

WAND_A = (170, 0, 255)   # Waende in Ost-West Richtung
WAND_B = (90, 0, 160)    # Waende in Nord-Sued Richtung (dunkler -> Tiefe)
AUSGANG = (0, 255, 90)
GOLD = (255, 160, 0)
TELEPORT = (0, 200, 255)
TUER_FARBEN = [(255, 0, 0), (0, 60, 255), (255, 255, 255)]   # rot, blau, weiss

# Farbe jedes Sektors im Levelauswahl-Screen
SEKTOR_FARBEN = [
    (170, 0, 255), (255, 160, 0), (255, 80, 0), (255, 0, 0),
    (40, 40, 255), (255, 0, 150), (0, 200, 255), (0, 255, 90),
]

# Was jeder Sektor Neues bringt (fuer die Ansage)
SEKTOR_NAMEN = [
    "GRUNDLAGEN", "1 SCHLUESSEL", "2 SCHLUESSEL", "3 SCHLUESSEL",
    "DUNKELHEIT", "FARBIGE TUEREN", "TELEPORTER", "FINALE",
]

# Kartenfelder
GANG = 0
WAND = 1
ZIEL = 2
TUER = 3   # 3, 4, 5 = Tuer in Farbe 0, 1, 2

# Decke schwarz, Boden mit leichtem Verlauf (Zeile 0 = oben)
HINTERGRUND = [(0, 0, 0)] * 4 + [(1, 0, 2), (2, 0, 4), (3, 0, 6), (4, 0, 8)]
SCHWARZ = [(0, 0, 0)] * 8

# Ziffern 3x5 Pixel, Zeile fuer Zeile
ZIFFERN = [
    "111101101101111", "010110010010111", "111001111100111",
    "111001111001111", "101101111001001", "111100111001111",
    "111100111101111", "111001001010010", "111101111101111",
    "111101111001111",
]

# Buchstaben 5 Pixel hoch, unterschiedlich breit
SCHRIFT = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#"],
    "N": ["#..#", "##.#", "#.##", "#..#", "#..#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "#.#", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#...#", "#...#", "#.#.#", "##.##", "#...#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"], "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    "Z": ["###", "..#", ".#.", "#..", "###"], " ": ["..", "..", "..", "..", ".."],
    "!": ["#", "#", "#", ".", "#"], ".": [".", ".", ".", ".", "#"],
    "-": ["...", "...", "###", "...", "..."],
}

# Joystick Mitte gedrueckt halten (Millisekunden)
HALTEN_MENU = 3000    # im Level: zurueck zur Levelauswahl
HALTEN_RESET = 5000   # in der Levelauswahl: Fortschritt loeschen
ANTIPPEN = 500        # kuerzer = Level starten

# Demo-Modus
DEMO_NACH = 20000     # so lange ohne Eingabe in der Levelauswahl -> Demo (ms)
DEMO_TEMPO = 2.0      # Felder pro Sekunde (Spieler: TEMPO = 1.6)

# Symbole, die beim Halten in der Fuellung ausgespart bleiben
PFEIL_LINKS = [
    "........",
    "...#....",
    "..##....",
    ".######.",
    ".######.",
    "..##....",
    "...#....",
    "........",
]
AUSRUFEZEICHEN = [
    "...##...",
    "...##...",
    "...##...",
    "...##...",
    "...##...",
    "........",
    "...##...",
    "...##...",
]

DATEI = "fortschritt.txt"

# Testmodus: True = alle 64 Level sind sofort spielbar
ALLE_FREI = False

# Spielzustand
karte = []
besucht = bytearray(0)
objekte = []
px = 1.5
py = 1.5
winkel = 0.0
dunkel = False
schluessel_noetig = 0
schluessel_haben = 0
tuer_schluessel = []
im_teleporter = False
zeitlimit = 0
blitz_farbe = (0, 0, 0)
blitz_ende = 0
demo_aktiv = False

# Bildspeicher: 64 Pixel x 3 Farben, Zeile 0 = oben
bild = [0.0] * 192
# Entfernung zur Wand fuer jeden der 16 Strahlen (fuer Verdeckung)
tiefen = [0.0] * 16
# Zwischenspeicher fuer eine Bildspalte (8 Zeilen x 3 Farben)
spalten_summe = [0.0] * 24

# Vorberechnete Tabellen - spart in jedem Bild viele Rechnungen
# LED-Nummer fuer jedes Pixel (Zeile 0 = oben)
LED = bytearray([(7 - i // 8) * 8 + i % 8 for i in range(64)])
# Abstand jedes Pixels zur Bildmitte (fuer Ringe und Kreise)
ABSTAND = [math.sqrt((i % 8 - 3.5) ** 2 + (i // 8 - 3.5) ** 2) for i in range(64)]
# Kameraposition der 16 Strahlen (-1 = linker Rand, 1 = rechter Rand)
KAMERA = [2 * (i // 2 + 0.25 + 0.5 * (i % 2)) / 8 - 1 for i in range(16)]


def index(x, y):
    # x = 0 links, y = 0 oben. Index 0 ist unten links, darum y umdrehen
    return (7 - y) * 8 + x


def loeschen():
    for i in range(64):
        np[i] = (0, 0, 0)


@micropython.native
def ausgeben(faktor=1.0):
    b = bild
    for i in range(64):
        k = i * 3
        r = int(b[k] * faktor)
        g = int(b[k + 1] * faktor)
        bl = int(b[k + 2] * faktor)
        np[LED[i]] = (r if r < 255 else 255, g if g < 255 else 255, bl if bl < 255 else 255)
    np.write()


def pixel_setzen(x, y, farbe, stufe):
    k = (y * 8 + x) * 3
    bild[k] = farbe[0] * stufe
    bild[k + 1] = farbe[1] * stufe
    bild[k + 2] = farbe[2] * stufe


def gedrueckt(pin):
    return pin.value() == 0


def eingabe():
    # Wird der Joystick gerade bewegt oder gedrueckt?
    for pin in JOYSTICK:
        if gedrueckt(pin):
            return True
    return False


def warten_bis_losgelassen():
    while eingabe():
        sleep_ms(10)
    sleep_ms(50)


def verlauf(farben, anteil):
    # Farbe zwischen mehreren Farben, anteil = 0.0 (erste) bis 1.0 (letzte)
    pos = anteil * (len(farben) - 1)
    i = min(int(pos), len(farben) - 2)
    f = pos - i
    a = farben[i]
    b = farben[i + 1]
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)


def halten(ziel, symbol, farben):
    # Misst, wie lange die Joystick-Mitte gedrueckt wird. Die Matrix fuellt sich
    # dabei von unten, das Symbol bleibt dunkel ausgespart. Voll = ziel erreicht.
    # Rueckgabe: Dauer in ms (hoechstens ziel)
    start = ticks_ms()
    while gedrueckt(joystick_mitte):
        t = ticks_diff(ticks_ms(), start)
        if t > 300:   # kurzes Antippen zeigt nichts an
            anteil = min(1, t / ziel)
            farbe = verlauf(farben, anteil)
            for y in range(8):
                for x in range(8):
                    deckung = max(0, min(1, anteil * 8 - (7 - y)))
                    if symbol[y][x] == "#":
                        deckung = 0
                    pixel_setzen(x, y, farbe, HELLIGKEIT * 0.4 * deckung)
            ausgeben()
        if t >= ziel:
            return ziel
        sleep_ms(10)
    return ticks_diff(ticks_ms(), start)


def blitz(farbe):
    global blitz_farbe, blitz_ende
    blitz_farbe = farbe
    blitz_ende = ticks_add(ticks_ms(), 300)


# ---------------------------------------------------------------
# Fortschritt speichern / laden
# ---------------------------------------------------------------

def laden():
    try:
        with open(DATEI) as d:
            text = d.read()
        return bytearray([1 if text[i] == "1" else 0 for i in range(64)])
    except Exception:
        return bytearray(64)


def speichern(fortschritt):
    with open(DATEI, "w") as d:
        d.write("".join(["1" if v else "0" for v in fortschritt]))


def ist_frei(fortschritt, n):
    return ALLE_FREI or n == 0 or fortschritt[n - 1] or fortschritt[n]


# ---------------------------------------------------------------
# Level bauen
# ---------------------------------------------------------------

def level_regeln(n):
    sektor = n // 8
    stufe = n % 8
    r = {"schluessel": 0, "tueren": 0, "dunkel": False, "teleport": False, "zeit": False}
    if sektor in (1, 2, 3):
        r["schluessel"] = sektor
    elif sektor == 4:
        r["dunkel"] = True
        r["schluessel"] = 1 + stufe // 3
    elif sektor == 5:
        r["tueren"] = 1 + stufe // 3
    elif sektor == 6:
        r["teleport"] = True
        r["schluessel"] = stufe // 3
    elif sektor == 7:
        r["zeit"] = True
        r["dunkel"] = stufe >= 4
        if stufe % 2 == 0:
            r["tueren"] = 1 + stufe // 3
        else:
            r["teleport"] = True
            r["schluessel"] = 1 + stufe // 4
    r["groesse"] = min(4 + stufe // 2 + sektor // 2, 11)
    return r


def labyrinth_bauen(breite, hoehe):
    # Zellen liegen auf ungeraden Koordinaten, dazwischen die Waende
    karte = [bytearray([WAND] * (2 * breite + 1)) for _ in range(2 * hoehe + 1)]
    karte[1][1] = GANG
    stapel = [(0, 0)]
    tiefste = (0, 0)
    max_tiefe = 0
    while stapel:
        cx, cy = stapel[-1]
        nachbarn = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = cx + dx
            ny = cy + dy
            if 0 <= nx < breite and 0 <= ny < hoehe and karte[2 * ny + 1][2 * nx + 1] == WAND:
                nachbarn.append((nx, ny))
        if nachbarn:
            nx, ny = random.choice(nachbarn)
            karte[cy + ny + 1][cx + nx + 1] = GANG   # Wand dazwischen durchbrechen
            karte[2 * ny + 1][2 * nx + 1] = GANG
            stapel.append((nx, ny))
            if len(stapel) > max_tiefe:
                max_tiefe = len(stapel)
                tiefste = (nx, ny)
        else:
            stapel.pop()
    # Die am weitesten entfernte Zelle ist immer eine Sackgasse -> dort ist der Ausgang
    karte[2 * tiefste[1] + 1][2 * tiefste[0] + 1] = ZIEL
    return karte, (2 * tiefste[1] + 1) * (2 * breite + 1) + 2 * tiefste[0] + 1


def feld(i):
    # Feld ueber eine einzige Nummer ansprechen: i = y * breite + x
    w = len(karte[0])
    return karte[i // w][i % w]


def wege_suchen(start, gesperrt):
    # Breitensuche: Entfernung von start zu jedem erreichbaren Feld (-1 = nicht erreichbar)
    w = len(karte[0])
    dist = [-1] * (w * len(karte))
    vor = [-1] * (w * len(karte))
    dist[start] = 0
    schlange = [start]
    i = 0
    while i < len(schlange):
        a = schlange[i]
        i += 1
        for b in (a + 1, a - 1, a + w, a - w):
            if dist[b] == -1 and feld(b) != WAND and b not in gesperrt:
                dist[b] = dist[a] + 1
                vor[b] = a
                schlange.append(b)
    return dist, vor


def ist_sackgasse(i):
    w = len(karte[0])
    offen = 0
    for b in (i + 1, i - 1, i + w, i - w):
        if feld(b) != WAND:
            offen += 1
    return offen == 1


def platz_waehlen(kandidaten, belegt):
    # Bevorzugt Sackgassen - dort muss man extra hinlaufen
    frei = [c for c in kandidaten if c not in belegt]
    sack = [c for c in frei if ist_sackgasse(c)]
    wahl = random.choice(sack if sack else frei)
    belegt.append(wahl)
    return wahl


def objekt(art, i, farbe):
    w = len(karte[0])
    return {"art": art, "x": i % w + 0.5, "y": i // w + 0.5, "farbe": farbe, "partner": 0, "weg": False}


def level_bauen(regeln):
    global karte, besucht, objekte, px, py, winkel, dunkel
    global schluessel_noetig, schluessel_haben, tuer_schluessel, im_teleporter, zeitlimit
    karte, ausgang = labyrinth_bauen(regeln["groesse"], regeln["groesse"])
    w = len(karte[0])
    start = w + 1
    objekte = []
    belegt = [start]
    dunkel = regeln["dunkel"]
    schluessel_haben = 0
    tuer_schluessel = []
    im_teleporter = False

    # Weg vom Start zum Ausgang
    dist, vor = wege_suchen(start, ())
    pfad = []
    i = ausgang
    while i != -1:
        pfad.append(i)
        i = vor[i]
    pfad.reverse()
    laenge = len(pfad)

    kandidaten = [c for c in range(w * len(karte)) if dist[c] >= 0 and feld(c) == GANG and c != start]

    # Farbige Tueren auf dem Weg zum Ausgang, jeder Schluessel vor seiner Tuer.
    # Tueren stehen nur in Durchgaengen zwischen zwei Zellen (ungerade Stelle im Weg)
    # und mit Abstand zueinander -> vor jeder Tuer liegt mindestens eine freie Zelle
    # fuer ihren Schluessel.
    tueren = []
    p_min = 3
    for t in range(regeln["tueren"]):
        p = max(p_min, laenge * (t + 1) // (regeln["tueren"] + 1)) | 1
        if p > laenge - 2:
            break
        tueren.append(pfad[p])
        p_min = p + 2
    for t in range(len(tueren)):
        karte[tueren[t] // w][tueren[t] % w] = TUER + t
    vorher = set()
    for t in range(len(tueren)):
        dist, vor = wege_suchen(start, tueren[t:])
        bereich = [c for c in range(w * len(karte)) if dist[c] >= 0 and c not in vorher]
        vorher.update(bereich)
        platz = platz_waehlen([c for c in bereich if feld(c) == GANG and c != start], belegt)
        objekte.append(objekt("S", platz, t))

    # Teleporter: der Weg wird in der Mitte zugemauert, das Portal fuehrt auf die andere Seite
    if regeln["teleport"] and laenge >= 7:
        m = (laenge // 2) | 1   # ungerade = Feld zwischen zwei Zellen, hat keine Abzweigungen
        karte[pfad[m] // w][pfad[m] % w] = WAND
        b = pfad[m + 1]
        belegt.append(b)
        dist_a, vor = wege_suchen(start, ())
        dist_b, vor = wege_suchen(b, ())
        seite_a = [c for c in range(w * len(karte)) if dist_a[c] >= 0 and feld(c) == GANG and c != start]
        a = platz_waehlen(seite_a, belegt)
        objekte.append(objekt("T", a, None))
        objekte.append(objekt("T", b, None))
        objekte[-2]["partner"] = len(objekte) - 1
        objekte[-1]["partner"] = len(objekte) - 2
        kandidaten = [c for c in range(w * len(karte))
                      if (dist_a[c] >= 0 or dist_b[c] >= 0) and feld(c) == GANG and c != start]

    # Goldene Schluessel fuer den Ausgang
    schluessel_noetig = regeln["schluessel"]
    for _ in range(schluessel_noetig):
        objekte.append(objekt("S", platz_waehlen(kandidaten, belegt), None))

    # Zeitlimit abhaengig von der Groesse des Labyrinths
    zeitlimit = 0
    if regeln["zeit"]:
        gaenge = len([c for c in range(w * len(karte)) if feld(c) == GANG])
        zeitlimit = int((15 + 0.6 * gaenge) * 1000)

    besucht = bytearray(w * len(karte))
    px = 1.5
    py = 1.5
    winkel = 0.0 if karte[1][2] != WAND else math.pi / 2


# ---------------------------------------------------------------
# Zeichnen
# ---------------------------------------------------------------

@micropython.native
def strahl(rx, ry):
    # Schickt einen Strahl in Richtung (rx, ry) und liefert
    # (Entfernung, Seite der Wand, Feldtyp) zurueck
    k = karte
    mx = int(px)
    my = int(py)
    dx = abs(1 / rx) if rx != 0 else 1e9
    dy = abs(1 / ry) if ry != 0 else 1e9
    if rx < 0:
        sx = -1
        weg_x = (px - mx) * dx
    else:
        sx = 1
        weg_x = (mx + 1 - px) * dx
    if ry < 0:
        sy = -1
        weg_y = (py - my) * dy
    else:
        sy = 1
        weg_y = (my + 1 - py) * dy
    seite = 0
    typ = WAND
    for _ in range(64):
        if weg_x < weg_y:
            weg_x += dx
            mx += sx
            seite = 0
        else:
            weg_y += dy
            my += sy
            seite = 1
        typ = k[my][mx]
        if typ:
            break
    if seite == 0:
        return weg_x - dx, seite, typ
    return weg_y - dy, seite, typ


@micropython.native
def zeichne_3d(jetzt):
    blick_x = math.cos(winkel)
    blick_y = math.sin(winkel)
    ebene_x = -blick_y * SICHTFELD
    ebene_y = blick_x * SICHTFELD
    puls = 0.6 + 0.4 * math.sin(jetzt / 150)
    nebel = 1.5 if dunkel else 0.15
    hintergrund = SCHWARZ if dunkel else HINTERGRUND
    ausgang_offen = schluessel_haben >= schluessel_noetig

    # Waende
    summe = spalten_summe
    for spalte in range(8):
        for i in range(24):
            summe[i] = 0.0
        for teil in range(2):
            kamera = KAMERA[spalte * 2 + teil]
            d, seite, typ = strahl(blick_x + ebene_x * kamera, blick_y + ebene_y * kamera)
            if d < 0.05:
                d = 0.05
            tiefen[spalte * 2 + teil] = d
            h = WANDHOEHE / d
            oben = 4 - h / 2
            unten = 4 + h / 2
            licht = 1.0
            if typ == ZIEL:
                f = AUSGANG
                licht = puls if ausgang_offen else 0.25
            elif typ >= TUER:
                f = TUER_FARBEN[typ - TUER]
                licht = 0.6 if seite == 0 else 0.4
            else:
                f = WAND_A if seite == 0 else WAND_B
            licht = licht * HELLIGKEIT / (1 + nebel * d * d)
            r = f[0] * licht
            g = f[1] * licht
            b = f[2] * licht
            for zeile in range(8):
                # Wie viel von diesem Pixel wird von der Wand bedeckt? (0 bis 1)
                deckung = min(zeile + 1, unten) - max(zeile, oben)
                k = zeile * 3
                if deckung >= 1:
                    # ganz Wand
                    summe[k] += r
                    summe[k + 1] += g
                    summe[k + 2] += b
                elif deckung <= 0:
                    # ganz Hintergrund
                    hg = hintergrund[zeile]
                    summe[k] += hg[0]
                    summe[k + 1] += hg[1]
                    summe[k + 2] += hg[2]
                else:
                    # Wandkante: mischen
                    hg = hintergrund[zeile]
                    summe[k] += r * deckung + hg[0] * (1 - deckung)
                    summe[k + 1] += g * deckung + hg[1] * (1 - deckung)
                    summe[k + 2] += b * deckung + hg[2] * (1 - deckung)
        for zeile in range(8):
            k = zeile * 3
            j = (zeile * 8 + spalte) * 3
            bild[j] = summe[k] / 2
            bild[j + 1] = summe[k + 1] / 2
            bild[j + 2] = summe[k + 2] / 2

    # Schluessel und Teleporter als leuchtende Kugeln
    pp = SICHTFELD * SICHTFELD
    for o in objekte:
        if o["weg"]:
            continue
        sx = o["x"] - px
        sy = o["y"] - py
        tiefe = sx * blick_x + sy * blick_y
        if tiefe < 0.2:
            continue
        mitte_x = (1 + (sx * ebene_x + sy * ebene_y) / (pp * tiefe)) * 4
        skala = WANDHOEHE / tiefe
        if o["art"] == "T":
            f = TELEPORT
            radius = (0.25 + 0.05 * math.sin(jetzt / 120)) * skala
            mitte_y = 4.0
        else:
            f = GOLD if o["farbe"] is None else TUER_FARBEN[o["farbe"]]
            radius = 0.1 * skala
            mitte_y = 4 + (0.15 + 0.05 * math.sin(jetzt / 200)) * skala   # schwebt
        licht = HELLIGKEIT / (1 + 0.05 * tiefe * tiefe)
        for x in range(max(0, int(mitte_x - radius - 1)), min(8, int(mitte_x + radius + 2))):
            # Verdeckt eine Wand die Kugel? (pro Strahl)
            sicht = ((tiefen[x * 2] > tiefe) + (tiefen[x * 2 + 1] > tiefe)) / 2
            if sicht == 0:
                continue
            for y in range(max(0, int(mitte_y - radius - 1)), min(8, int(mitte_y + radius + 2))):
                d = math.sqrt((x + 0.5 - mitte_x) ** 2 + (y + 0.5 - mitte_y) ** 2)
                deckung = radius + 0.5 - d
                if deckung <= 0:
                    continue
                if deckung > 1:
                    deckung = 1
                s = licht * deckung * sicht
                k = (y * 8 + x) * 3
                bild[k] += f[0] * s
                bild[k + 1] += f[1] * s
                bild[k + 2] += f[2] * s


def zeichne_karte(jetzt):
    blink = (jetzt // 250) % 2
    w = len(karte[0])
    cx = int(px)
    cy = int(py)
    vx = int(px + math.cos(winkel) * 0.9)
    vy = int(py + math.sin(winkel) * 0.9)
    for y in range(8):
        for x in range(8):
            mx = cx + x - 3
            my = cy + y - 3
            f = (0, 0, 0)
            if 0 <= my < len(karte) and 0 <= mx < w and besucht[my * w + mx]:
                typ = karte[my][mx]
                if typ == WAND:
                    f = (10, 0, 20)
                elif typ == ZIEL:
                    f = (0, 60, 20) if blink else (0, 20, 6)
                elif typ >= TUER:
                    t = TUER_FARBEN[typ - TUER]
                    f = (t[0] // 6, t[1] // 6, t[2] // 6)
                elif mx == cx and my == cy:
                    f = (60, 60, 60) if blink else (20, 20, 20)
                elif mx == vx and my == vy:
                    f = (25, 20, 0)
                for o in objekte:
                    if not o["weg"] and int(o["x"]) == mx and int(o["y"]) == my and not (mx == cx and my == cy):
                        if o["art"] == "T":
                            t = TELEPORT
                        else:
                            t = GOLD if o["farbe"] is None else TUER_FARBEN[o["farbe"]]
                        f = (t[0] // 5, t[1] // 5, t[2] // 5)
            k = (y * 8 + x) * 3
            bild[k] = f[0]
            bild[k + 1] = f[1]
            bild[k + 2] = f[2]


def zeichne_anzeige(jetzt, rest):
    # Blitz beim Einsammeln / Teleportieren / Tuer oeffnen
    if ticks_diff(blitz_ende, jetzt) > 0:
        s = ticks_diff(blitz_ende, jetzt) / 300 * 0.3 * HELLIGKEIT
        for i in range(64):
            bild[i * 3] += blitz_farbe[0] * s
            bild[i * 3 + 1] += blitz_farbe[1] * s
            bild[i * 3 + 2] += blitz_farbe[2] * s
    # Oben links: Schluessel
    for i in range(schluessel_noetig):
        pixel_setzen(i, 0, GOLD, HELLIGKEIT * (0.5 if i < schluessel_haben else 0.05))
    for i in range(len(tuer_schluessel)):
        pixel_setzen(i, 0, TUER_FARBEN[tuer_schluessel[i]], HELLIGKEIT * 0.5)
    # Unterste Zeile: Zeitbalken, wird von gruen zu rot
    if zeitlimit:
        anteil = rest / zeitlimit
        farbe = (255 * (1 - anteil), 255 * anteil, 0)
        for x in range(8):
            deckung = max(0, min(1, anteil * 8 - x))
            pixel_setzen(x, 7, farbe, HELLIGKEIT * 0.4 * deckung)


def ring_animation(farbe, nach_aussen):
    # Ring, der sich ausbreitet oder zusammenzieht (kantengeglaettet)
    for schritt in range(40):
        if demo_aktiv:
            pruefen()
        radius = schritt * 0.25 if nach_aussen else 6 - schritt * 0.15
        for i in range(64):
            s = max(0, 1 - abs(ABSTAND[i] - radius)) * HELLIGKEIT
            np[LED[i]] = (int(farbe[0] * s), int(farbe[1] * s), int(farbe[2] * s))
        np.write()
        sleep_ms(25)


# ---------------------------------------------------------------
# Spiel
# ---------------------------------------------------------------

def bewegen(dx, dy):
    # Bewegt die Spielfigur, Waende blockieren. True = Ausgang erreicht
    global px, py
    nx = px + dx
    rand = RADIUS if dx > 0 else -RADIUS
    e = betreten(int(nx + rand), int(py))
    if e == 2:
        return True
    if e == 1:
        px = nx
    ny = py + dy
    rand = RADIUS if dy > 0 else -RADIUS
    e = betreten(int(px), int(ny + rand))
    if e == 2:
        return True
    if e == 1:
        py = ny
    return False


def betreten(mx, my):
    # 0 = blockiert, 1 = frei, 2 = Ausgang erreicht
    typ = karte[my][mx]
    if typ == GANG:
        return 1
    if typ == ZIEL:
        return 2 if schluessel_haben >= schluessel_noetig else 0
    if typ >= TUER and (typ - TUER) in tuer_schluessel:
        # Passender Schluessel: Tuer verschwindet
        karte[my][mx] = GANG
        tuer_schluessel.remove(typ - TUER)
        blitz(TUER_FARBEN[typ - TUER])
    return 0


def objekte_pruefen(teleport=True):
    # Schluessel einsammeln und Teleporter ausloesen.
    # teleport=False: die Teleporter uebernimmt der Autopilot selbst
    global schluessel_haben, im_teleporter, px, py
    auf_teleporter = False
    for o in objekte:
        if o["weg"]:
            continue
        d2 = (o["x"] - px) ** 2 + (o["y"] - py) ** 2
        if o["art"] == "S" and d2 < 0.2:
            o["weg"] = True
            if o["farbe"] is None:
                schluessel_haben += 1
                blitz(GOLD)
            else:
                tuer_schluessel.append(o["farbe"])
                blitz(TUER_FARBEN[o["farbe"]])
        elif o["art"] == "T" and teleport and d2 < 0.16:
            auf_teleporter = True
            if not im_teleporter:
                ziel = objekte[o["partner"]]
                px = ziel["x"]
                py = ziel["y"]
                im_teleporter = True
                blitz(TELEPORT)
                return
    # Erst wenn man vom Teleporter heruntergeht, kann er wieder ausloesen
    if not auf_teleporter:
        im_teleporter = False


def erkunden():
    # Felder rund um die Spielfigur auf der Karte aufdecken
    w = len(karte[0])
    cx = int(px)
    cy = int(py)
    for y in range(cy - 1, cy + 2):
        for x in range(cx - 1, cx + 2):
            besucht[y * w + x] = 1


def spielen(n):
    # Spielt ein Level. Rueckgabe: Zeit in ms, -1 = Zeit abgelaufen,
    # None = zurueck zur Levelauswahl
    global winkel
    level_bauen(level_regeln(n))
    # Speicher jetzt aufraeumen, damit es waehrend des Spiels nicht ruckelt
    gc.collect()
    # Erstes Bild berechnen, Pixel herunterfallen lassen, dann "GO!"
    jetzt = ticks_ms()
    zeichne_3d(jetzt)
    zeichne_anzeige(jetzt, zeitlimit)
    bild_aufbauen()
    go_anzeigen()
    start = ticks_ms()
    letzte = start
    while True:
        jetzt = ticks_ms()
        dt = ticks_diff(jetzt, letzte) / 1000
        letzte = jetzt
        if dt > 0.1:
            dt = 0.1

        if gedrueckt(joystick_mitte):
            dauer = halten(HALTEN_MENU, PFEIL_LINKS, [(255, 255, 255), (255, 200, 0), (0, 255, 0)])
            if dauer >= HALTEN_MENU:
                warten_bis_losgelassen()
                return None
            # Zu kurz gedrueckt -> weiterspielen, die Wartezeit zaehlt nicht
            start = ticks_add(start, dauer)
            letzte = ticks_ms()
            continue
        if gedrueckt(joystick_links):
            winkel -= DREHTEMPO * dt
        if gedrueckt(joystick_rechts):
            winkel += DREHTEMPO * dt
        schritt = 0
        if gedrueckt(joystick_oben):
            schritt = TEMPO * dt
        if gedrueckt(joystick_unten):
            schritt = -TEMPO * dt
        if schritt != 0:
            if bewegen(math.cos(winkel) * schritt, math.sin(winkel) * schritt):
                return ticks_diff(ticks_ms(), start)
        objekte_pruefen()
        erkunden()

        rest = 0
        if zeitlimit:
            rest = zeitlimit - ticks_diff(jetzt, start)
            if rest <= 0:
                return -1

        if schalter.value() == 1:
            zeichne_karte(jetzt)
        else:
            zeichne_3d(jetzt)
        zeichne_anzeige(jetzt, rest)
        ausgeben()


def bild_aufbauen():
    # Die Pixel des fertigen Bildes fallen von oben herunter, die unterste Zeile zuerst
    ziel = bild[:]
    verzoegerung = [(7 - i // 8) * 110 + random.randint(0, 120) for i in range(64)]
    start = ticks_ms()
    fertig = False
    while not fertig:
        if demo_aktiv:
            pruefen()
        t = ticks_diff(ticks_ms(), start) / 1000
        bild_loeschen()
        fertig = True
        for i in range(64):
            x = i % 8
            y = i // 8
            lokal = t - verzoegerung[i] / 1000
            if lokal < 0:
                fertig = False
                continue
            # Freier Fall: Weg = 1/2 * g * t^2 (g in Zeilen pro Sekunde^2)
            pos = -1 + 0.5 * 130 * lokal * lokal
            if pos >= y:
                pos = y
            else:
                fertig = False
            # Zwischen zwei Zeilen aufteilen -> weiches Fallen
            oben = int(math.floor(pos))
            f = pos - oben
            for zeile, anteil in ((oben, 1 - f), (oben + 1, f)):
                if 0 <= zeile < 8 and anteil > 0:
                    k = (zeile * 8 + x) * 3
                    bild[k] += ziel[i * 3] * anteil
                    bild[k + 1] += ziel[i * 3 + 1] * anteil
                    bild[k + 2] += ziel[i * 3 + 2] * anteil
        ausgeben()
        sleep_ms(10)


def go_anzeigen():
    # Gruenes "GO!" ueber dem abgedunkelten Bild, danach geht's los
    szene = bild[:]
    # G + Luecke + O + ! = genau 8 Spalten
    spalten = text_spalten("GO")[:-1] + text_spalten("!")[:-1]
    start = ticks_ms()
    while True:
        t = ticks_diff(ticks_ms(), start)
        if t > 2500:
            break
        if demo_aktiv:
            pruefen()
        hell = min(1, t / 150) * (0.75 + 0.25 * math.sin(t / 90))
        if t > 2200:
            hell *= (2500 - t) / 300   # ausblenden
        for i in range(192):
            bild[i] = szene[i] * (0.25 + 0.75 * max(0, (t - 2200) / 300))
        for x in range(8):
            for y in range(5):
                if spalten[x][y]:
                    pixel_setzen(x, y + 1, AUSGANG, HELLIGKEIT * hell)
            # Spiegelung auf dem Boden
            if spalten[x][4]:
                pixel_setzen(x, 6, AUSGANG, HELLIGKEIT * 0.25 * hell)
            if spalten[x][3]:
                pixel_setzen(x, 7, AUSGANG, HELLIGKEIT * 0.08 * hell)
        ausgeben()
        sleep_ms(10)


def levelauswahl(fortschritt, cursor):
    # Jedes Pixel ist ein Level, jede Zeile ein Sektor. Rueckgabe: gewaehltes Level.
    # Ohne Eingabe startet nach DEMO_NACH ms der Demo-Modus.
    letzte_bewegung = ticks_add(ticks_ms(), -1000)
    letzte_eingabe = ticks_ms()
    while True:
        jetzt = ticks_ms()
        if eingabe():
            letzte_eingabe = jetzt
        elif ticks_diff(jetzt, letzte_eingabe) > DEMO_NACH:
            demo()
            # Zurueck aus der Demo: die Levelauswahl baut sich wieder auf
            try:
                intro_raster(fortschritt, cursor)
            except Uebersprungen:
                pass
            letzte_eingabe = ticks_ms()
            continue
        schritt = 0
        if gedrueckt(joystick_links):
            schritt = -1
        elif gedrueckt(joystick_rechts):
            schritt = 1
        elif gedrueckt(joystick_oben):
            schritt = -8
        elif gedrueckt(joystick_unten):
            schritt = 8
        if schritt == 0:
            letzte_bewegung = ticks_add(jetzt, -1000)
        elif ticks_diff(jetzt, letzte_bewegung) > 200:
            neu = cursor + schritt
            if 0 <= neu < 64 and ist_frei(fortschritt, neu):
                cursor = neu
            letzte_bewegung = jetzt
        if gedrueckt(joystick_mitte):
            dauer = halten(HALTEN_RESET, AUSRUFEZEICHEN, [(0, 255, 0), (255, 80, 0), (255, 0, 0)])
            if dauer >= HALTEN_RESET:
                zuruecksetzen(fortschritt)
                cursor = 0
            elif dauer < ANTIPPEN:
                return cursor
            # Reset erledigt oder vorher losgelassen (= abgebrochen):
            # der Demo-Zaehler beginnt von vorne
            letzte_eingabe = ticks_ms()
            continue

        blink = (jetzt // 300) % 2
        for n in range(64):
            np[index(n % 8, n // 8)] = auswahl_farbe(fortschritt, cursor, n, blink)
        np.write()
        sleep_ms(20)


def auswahl_farbe(fortschritt, cursor, n, blink):
    # Farbe von Level n im Levelauswahl-Screen
    f = SEKTOR_FARBEN[n // 8]
    if n == cursor:
        stufe = 1.0 if blink else 0.3
        if blink:
            f = (255, 255, 255)
    elif fortschritt[n]:
        stufe = 0.6
    elif ist_frei(fortschritt, n):
        stufe = 0.15
    else:
        stufe = 0.02
    s = stufe * HELLIGKEIT
    return (int(f[0] * s), int(f[1] * s), int(f[2] * s))


# ---------------------------------------------------------------
# Intro
# ---------------------------------------------------------------

class Uebersprungen(Exception):
    pass


def pruefen():
    # Joystick Mitte ueberspringt Intro und Lauftexte.
    # Im Demo-Modus beendet jede Joystick-Bewegung die Demo.
    if gedrueckt(joystick_mitte) or (demo_aktiv and eingabe()):
        warten_bis_losgelassen()
        raise Uebersprungen()


def bild_loeschen():
    for i in range(192):
        bild[i] = 0


def farbrad(h):
    # Fliessender Uebergang durch alle Sektorfarben, h = 0.0 bis 1.0
    h = (h % 1) * 8
    f = h - int(h)
    i = int(h) % 8   # Rundungsfehler koennen genau 8.0 ergeben
    a = SEKTOR_FARBEN[i]
    b = SEKTOR_FARBEN[(i + 1) % 8]
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)


def intro_herzschlag():
    # Ein violetter Punkt schlaegt zweimal "ba-bumm" und zerplatzt zu einem Ring
    start = ticks_ms()
    while True:
        pruefen()
        t = ticks_diff(ticks_ms(), start)
        if t > 2200:
            break
        # Herzschlag einmal pro Bild berechnen, nicht fuer jedes Pixel
        if t < 1600:
            schlag = 0
            for mitte, staerke in ((400, 1.0), (620, 0.6), (1150, 1.0), (1370, 0.6)):
                schlag = max(schlag, staerke * math.exp(-((t - mitte) / 80) ** 2))
            radius = 0.3 + 1.4 * schlag
            einblenden = min(1, t / 300)
        else:
            anteil = (t - 1600) / 600
        for i in range(64):
            d = ABSTAND[i]
            if t < 1600:
                s = max(0, min(1, radius + 0.5 - d)) * einblenden
            else:
                s = max(0, 1 - abs(d - (0.5 + anteil * 6))) * (1 - anteil)
            pixel_setzen(i % 8, i // 8, WAND_A, HELLIGKEIT * s)
        ausgeben()
        sleep_ms(10)


def intro_flug():
    # Die Kamera fliegt automatisch durch ein Labyrinth bis zum Ausgang
    regeln = level_regeln(0)
    regeln["groesse"] = 5
    level_bauen(regeln)
    route = route_planen()
    autopilot(route, max(2.5, (len(route) - 1.7) / 6), True)

    # Gruener Blitz beim Ausgang
    for k in range(25):
        pruefen()
        s = HELLIGKEIT * (1 - k / 25)
        for i in range(64):
            pixel_setzen(i % 8, i // 8, AUSGANG, s)
        ausgeben()
        sleep_ms(20)


def text_spalten(text):
    # Text in eine Liste von Pixelspalten (je 5 Werte) umwandeln
    spalten = []
    for zeichen in text:
        if zeichen in "0123456789":
            z = ZIFFERN[int(zeichen)]
            muster = [z[0:3].replace("1", "#"), z[3:6].replace("1", "#"), z[6:9].replace("1", "#"),
                      z[9:12].replace("1", "#"), z[12:15].replace("1", "#")]
        else:
            muster = SCHRIFT.get(zeichen, SCHRIFT[" "])
        for x in range(len(muster[0])):
            spalten.append([1 if muster[y][x] == "#" else 0 for y in range(5)])
        spalten.append([0] * 5)
    return spalten


def lauftext(text, tempo=8):
    # Der Text gleitet weich durchs Bild, in Regenbogenfarben und mit Spiegelung.
    # tempo = Spalten pro Sekunde
    spalten = text_spalten(text)
    leer = [0] * 5
    start = ticks_ms()
    while True:
        pruefen()
        t = ticks_diff(ticks_ms(), start) / 1000
        versatz = -8 + t * tempo
        if versatz > len(spalten):
            break
        bild_loeschen()
        for x in range(8):
            pos = x + versatz
            i = int(math.floor(pos))
            f = pos - i
            # Zwischen zwei Spalten ueberblenden -> Bewegung ohne Ruckeln
            a = spalten[i] if 0 <= i < len(spalten) else leer
            b = spalten[i + 1] if 0 <= i + 1 < len(spalten) else leer
            farbe = farbrad(pos * 0.06 - t * 0.25)
            for y in range(5):
                pixel_setzen(x, y + 1, farbe, HELLIGKEIT * (a[y] * (1 - f) + b[y] * f))
            # Spiegelung auf dem Boden
            pixel_setzen(x, 6, farbe, HELLIGKEIT * 0.25 * (a[4] * (1 - f) + b[4] * f))
            pixel_setzen(x, 7, farbe, HELLIGKEIT * 0.08 * (a[3] * (1 - f) + b[3] * f))
        ausgeben()
        sleep_ms(10)


def intro_raster(fortschritt, cursor):
    # Die Levelauswahl baut sich diagonal auf, jedes Pixel blitzt kurz weiss auf
    start = ticks_ms()
    while True:
        pruefen()
        t = ticks_diff(ticks_ms(), start)
        if t > 1300:
            break
        for n in range(64):
            ziel = auswahl_farbe(fortschritt, cursor, n, 0)
            lokal = t - (n % 8 + n // 8) * 70
            if lokal < 0:
                f = (0, 0, 0)
            elif lokal < 250:
                m = lokal / 250
                weiss = 255 * HELLIGKEIT * 0.6 * (1 - m)
                f = (int(weiss + ziel[0] * m), int(weiss + ziel[1] * m), int(weiss + ziel[2] * m))
            else:
                f = ziel
            np[index(n % 8, n // 8)] = f
        np.write()
        sleep_ms(10)


def intro(fortschritt, cursor):
    try:
        intro_herzschlag()
        intro_flug()
        lauftext(NAME + " " + VERSION)
        intro_raster(fortschritt, cursor)
    except Uebersprungen:
        pass


# ---------------------------------------------------------------
# Autopilot (Intro-Flug und Demo-Modus)
# ---------------------------------------------------------------

def route_suchen(start, tele, gehalten, offen, ziel_erlaubt):
    # Breitensuche wie wege_suchen, aber nach den Regeln des Spiels: Tueren nur
    # mit passendem Schluessel (oder schon offen), Teleporter = Sprung.
    # Wer ueber einen Teleporter laeuft, wird sofort weggebeamt. Wer auf einem
    # Teleporter LANDET, darf von dort in jede Richtung weiterlaufen. Darum gilt
    # ein Teleporterfeld erst als besucht, wenn man darauf gelandet ist.
    w = len(karte[0])
    dist = [-1] * (w * len(karte))
    vor = [-1] * (w * len(karte))
    sprung = [-1] * (w * len(karte))   # ueber welchen Teleporter man hier gelandet ist
    dist[start] = 0
    schlange = [start]
    i = 0
    while i < len(schlange):
        a = schlange[i]
        i += 1
        for b in (a + 1, a - 1, a + w, a - w):
            typ = feld(b)
            if typ == WAND or (typ == ZIEL and not ziel_erlaubt):
                continue
            if typ >= TUER and b not in offen and (typ - TUER) not in gehalten:
                continue
            if b in tele:
                # Auf den Teleporter treten = auf der anderen Seite landen
                c = tele[b]
                if dist[c] == -1:
                    dist[c] = dist[a] + 1
                    vor[c] = a
                    sprung[c] = b
                    schlange.append(c)
                continue
            if dist[b] != -1:
                continue
            dist[b] = dist[a] + 1
            vor[b] = a
            if typ != ZIEL:   # der Ausgang ist Endstation
                schlange.append(b)
    return dist, vor, sprung


def route_anhaengen(route, vor, sprung, ziel, schluessel, gehalten, offen):
    # Weg bis ziel an die Route haengen und unterwegs Schluessel und Tueren nachspielen
    weg = []
    i = ziel
    while i != -1:
        weg.append(i)
        if sprung[i] != -1:
            weg.append(sprung[i])   # vorher auf diesen Teleporter getreten
        i = vor[i]
    weg.reverse()   # weg[0] ist die aktuelle Position
    for c in weg[1:]:
        typ = feld(c)
        if typ >= TUER and c not in offen:
            offen.append(c)
            if (typ - TUER) in gehalten:
                gehalten.remove(typ - TUER)
        if c in schluessel:
            farbe = schluessel.pop(c)
            if farbe is not None:
                gehalten.append(farbe)
    route.extend(weg[1:])


def route_planen():
    # Plant den Weg vom Start ueber alle Schluessel (immer zum naechsten) bis zum
    # Ausgang. Rueckgabe: Liste von Feldnummern, None = kein Weg gefunden
    w = len(karte[0])
    tele = {}
    schluessel = {}
    for o in objekte:
        nr = int(o["y"]) * w + int(o["x"])
        if o["art"] == "T":
            p = objekte[o["partner"]]
            tele[nr] = int(p["y"]) * w + int(p["x"])
        else:
            schluessel[nr] = o["farbe"]
    gehalten = []   # Farben der Tuerschluessel, die der Autopilot traegt
    offen = []      # Tueren, die schon offen sind
    route = [w + 1]
    while True:
        dist, vor, sprung = route_suchen(route[-1], tele, gehalten, offen, False)
        ziel = -1
        for c in schluessel:
            if dist[c] >= 0 and (ziel < 0 or dist[c] < dist[ziel]):
                ziel = c
        if ziel < 0:
            break   # alle Schluessel geholt
        route_anhaengen(route, vor, sprung, ziel, schluessel, gehalten, offen)
    ausgang = [c for c in range(w * len(karte)) if feld(c) == ZIEL][0]
    dist, vor, sprung = route_suchen(route[-1], tele, gehalten, offen, True)
    if dist[ausgang] < 0:
        return None
    route_anhaengen(route, vor, sprung, ausgang, schluessel, gehalten, offen)
    return route


def weg_punkt(punkte, s):
    # Position auf einer Route nach s Feldern (zwischen zwei Punkten gemischt)
    i = min(int(s), len(punkte) - 2)
    f = min(1, s - i)
    a = punkte[i]
    b = punkte[i + 1]
    return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f


def autopilot(route, tempo, einblenden):
    # Die Kamera folgt der Route bis kurz vor den Ausgang. Schluessel werden
    # eingesammelt, Tueren geoeffnet und Teleporter benutzt - wie beim Spielen.
    # einblenden=True: Bild langsam einblenden (Intro), sonst Levelstart wie beim
    # Spielen. Rueckgabe: benoetigte Zeit in ms
    global px, py, winkel
    w = len(karte[0])
    punkte = [(i % w + 0.5, i // w + 0.5) for i in route]
    # Teleporter-Spruenge: zwei Punkte nacheinander, die nicht nebeneinander liegen
    spruenge = [i for i in range(len(punkte) - 1)
                if abs(punkte[i][0] - punkte[i + 1][0]) + abs(punkte[i][1] - punkte[i + 1][1]) > 1.5]
    ende = len(punkte) - 1.7   # kurz vor der Ausgangswand anhalten
    s = 0.0
    px, py = punkte[0]
    winkel = math.atan2(punkte[1][1] - py, punkte[1][0] - px)
    if not einblenden:
        # Levelstart wie beim Spielen: Pixel fallen herunter, dann "GO!"
        jetzt = ticks_ms()
        zeichne_3d(jetzt)
        zeichne_anzeige(jetzt, zeitlimit)
        bild_aufbauen()
        go_anzeigen()
    start = ticks_ms()
    letzte = start
    while s < ende:
        pruefen()
        jetzt = ticks_ms()
        dt = min(0.1, ticks_diff(jetzt, letzte) / 1000)
        letzte = jetzt
        # Blick auf einen Punkt etwas weiter vorne -> weiche Kurven.
        # Aber nie ueber einen Teleporter hinaus schauen.
        vorne = s + 1.0
        for j in spruenge:
            if j > s:
                vorne = min(vorne, j)
                break
        vx, vy = weg_punkt(punkte, vorne)
        diff = 0.0
        if abs(vx - px) + abs(vy - py) > 0.01:
            soll = math.atan2(vy - py, vx - px)
            diff = (soll - winkel + math.pi) % (2 * math.pi) - math.pi
            winkel += diff * min(1, dt * 6)
        # In Kurven und Sackgassen langsamer: erst drehen, dann gehen
        s_neu = min(ende, s + tempo * dt * max(0.1, math.cos(diff)))
        for j in spruenge:
            if s < j and s_neu >= j - 0.4:
                # Teleporter erreicht -> auf der anderen Seite weiter
                s_neu = j + 1
                blitz(TELEPORT)
                break
        s = s_neu
        px, py = weg_punkt(punkte, s)
        # Tuer direkt vor uns? Mit dem passenden Schluessel oeffnen
        k = int(s + 0.75)
        if k < len(route) and feld(route[k]) >= TUER:
            farbe = feld(route[k]) - TUER
            karte[route[k] // w][route[k] % w] = GANG
            if farbe in tuer_schluessel:
                tuer_schluessel.remove(farbe)
            blitz(TUER_FARBEN[farbe])
        objekte_pruefen(False)
        zeichne_3d(jetzt)
        # Zeitbalken wie beim Spielen (laeuft er ab, faehrt der Autopilot trotzdem weiter)
        rest = max(0, zeitlimit - ticks_diff(jetzt, start)) if zeitlimit else 0
        zeichne_anzeige(jetzt, rest)
        ausgeben(min(1, ticks_diff(jetzt, start) / 600) if einblenden else 1.0)
    return ticks_diff(ticks_ms(), start)


def demo():
    # Das Spiel spielt sich selbst - genau wie beim Spielen: Ansage, Pixel fallen,
    # "GO!", am Schluss gruener Ring und die Zeit. Jedes Mal ein zufaelliges Level
    # aus einem anderen Sektor. Jede Joystick-Bewegung beendet die Demo.
    global demo_aktiv
    demo_aktiv = True
    letzter = -1
    try:
        while True:
            n = random.randint(0, 63)
            while n // 8 == letzter // 8:
                n = random.randint(0, 63)
            letzter = n
            level_ansage(n)
            level_bauen(level_regeln(n))
            gc.collect()
            route = route_planen()
            if route:
                zeit = autopilot(route, DEMO_TEMPO, False)
                ring_animation(AUSGANG, True)
                lauftext(str(zeit // 1000) + " SEK")
    except Uebersprungen:
        pass
    demo_aktiv = False


# ---------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------

def level_ansage(n):
    # "LEVEL 12 - SEKTOR 2", beim ersten Level eines Sektors auch was neu ist
    text = "LEVEL " + str(n + 1) + " - SEKTOR " + str(n // 8 + 1)
    if n % 8 == 0:
        text += " - " + SEKTOR_NAMEN[n // 8]
    lauftext(text, 12)


def zuruecksetzen(fortschritt):
    # Gesamten Fortschritt loeschen
    for i in range(64):
        fortschritt[i] = 0
    speichern(fortschritt)
    warten_bis_losgelassen()
    try:
        lauftext("RESET DONE!")
    except Uebersprungen:
        pass


def hauptprogramm():
    print(NAME + " " + VERSION + " - von Mischa Joel Thie")
    fortschritt = laden()
    cursor = 0
    while cursor < 63 and fortschritt[cursor]:
        cursor += 1

    intro(fortschritt, cursor)

    while True:
        level = levelauswahl(fortschritt, cursor)
        cursor = level
        while True:
            # Ansage "LEVEL X - SEKTOR Y" (Joystick Mitte = ueberspringen)
            try:
                level_ansage(level)
            except Uebersprungen:
                pass
            zeit = spielen(level)
            if zeit is None:
                break
            if zeit < 0:
                # Zeit abgelaufen -> nochmal
                ring_animation((255, 0, 0), False)
                continue
            ring_animation(AUSGANG, True)
            # Benoetigte Zeit als Lauftext (Joystick Mitte = ueberspringen)
            try:
                lauftext(str(zeit // 1000) + " SEK")
            except Uebersprungen:
                pass
            if not fortschritt[level]:
                fortschritt[level] = 1
                speichern(fortschritt)
                if level == 63:
                    # Alle 64 Level geschafft -> Abspann
                    try:
                        lauftext("ALL 64 LEVELS CLEAR! " + NAME + " " + VERSION + " BY " + AUTOR)
                    except Uebersprungen:
                        pass
            if level < 63:
                cursor = level + 1
            break


try:
    hauptprogramm()
finally:
    # Bei STOP in Thonny (oder einem Fehler) alle LEDs ausschalten
    loeschen()
    np.write()
