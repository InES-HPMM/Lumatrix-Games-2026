"""
Pixel-Labyrinth für die Lumatrix
Zuerst erscheint ein Logo, löst sich in blitzenden Pixeln auf, dann baut sich ein
zufälliges Labyrinth vor deinen Augen selbst. Steuere den grünen Punkt mit dem
Joystick zum blinkenden roten Ziel. Nach dem Sieg gibt es ein neues Labyrinth,
ein Druck auf den Joystick würfelt jederzeit ein neues aus.
"""
from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms, ticks_ms, ticks_diff
from random import randint, choice
from math import sqrt

# ---- Einstellungen, die du leicht ändern kannst ----
TEMPO = 140         # Millisekunden pro Schritt des Spielers (kleiner = schneller)
BAU_TEMPO = 90      # Millisekunden pro Schritt beim Bauen des Labyrinths
SIEG_STIL = 5       # Animation nach dem Sieg: 1 = Wellen, 2 = Zerfall, 3 = Konfetti, 4 = Spirale, 5 = Feuerwerk

HELLIGKEIT = 5     # Helligkeit des ganzen Spiels in Prozent (0 bis 100)

# Farben als (Rot, Grün, Blau), jeweils 0 bis 255 (ganz normale Werte)
WAND = (42, 98, 162)    # ZHAW-Blau
SPIELER = (0, 160, 0)   # Grün
ZIEL = (160, 0, 0)      # Rot (blinkt)
AUS = (0, 0, 0)         # Gänge: LED aus

# ---- Hardware ----


class Matrix:
    """Wie NeoPixel, dimmt aber jede Farbe automatisch auf HELLIGKEIT Prozent."""

    def __init__(self):
        self.leds = NeoPixel(Pin(19, Pin.OUT), 64)

    def __setitem__(self, nummer, f):
        self.leds[nummer] = (f[0] * HELLIGKEIT // 100,
                             f[1] * HELLIGKEIT // 100,
                             f[2] * HELLIGKEIT // 100)

    def write(self):
        self.leds.write()


np = Matrix()
rechts = Pin(2, Pin.IN, Pin.PULL_UP)
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
druck = Pin(8, Pin.IN, Pin.PULL_UP)

# ---- Logo: eine Spirale (oberste Zeile zuerst) ----
LOGO = (
    "########",
    "#......#",
    "#.####.#",
    "#.#..#.#",
    "#.#.##.#",
    "#.#....#",
    "#.######",
    "#.......",
)


def pos(x, y):
    """LED-Nummer: x von links, y von unten."""
    return y * 8 + x


def rad(p):
    """Regenbogenfarbe für p = 0..254."""
    p %= 255
    if p < 85:
        return (255 - p * 3, p * 3, 0)
    if p < 170:
        p -= 85
        return (0, 255 - p * 3, p * 3)
    p -= 170
    return (p * 3, 0, 255 - p * 3)


def blende(f, prozent):
    """Farbe auf prozent % abdunkeln (nur für das Einblenden des Logos)."""
    return (f[0] * prozent // 100, f[1] * prozent // 100, f[2] * prozent // 100)


def mische(liste):
    """Zufällige Reihenfolge (Fisher-Yates)."""
    for i in range(len(liste) - 1, 0, -1):
        j = randint(0, i)
        liste[i], liste[j] = liste[j], liste[i]


# ---------- Intro ----------
def logo_zeigen(prozent, versatz, spieler=None):
    for i in range(64):
        np[i] = AUS
    for z in range(8):
        for x in range(8):
            if LOGO[z][x] == "#":
                np[pos(x, 7 - z)] = blende(rad(x * 20 + z * 20 + versatz), prozent)
    if spieler:
        np[pos(*spieler)] = SPIELER
    np.write()


def logo_pfad():
    """Der Gang im Logo: von der Öffnung unten rechts bis zum Ende in der Mitte."""
    x, z = 7, 7
    pfad = [(x, z)]
    while True:
        for dx, dz in ((-1, 0), (0, -1), (1, 0), (0, 1)):
            nx, nz = x + dx, z + dz
            if 0 <= nx < 8 and 0 <= nz < 8 and LOGO[nz][nx] == "." and (nx, nz) not in pfad:
                x, z = nx, nz
                pfad.append((x, z))
                break
        else:
            return pfad


def logo_aufloesen():
    pixel = [pos(x, 7 - z) for z in range(8) for x in range(8) if LOGO[z][x] == "#"]
    mische(pixel)
    for i, n in enumerate(pixel):
        np[n] = (255, 255, 255)                         # weisses Aufblitzen
        if i >= 3:
            np[pixel[i - 3]] = AUS                      # ältere Pixel erlöschen
        np.write()
        sleep_ms(35)
    for n in pixel[-3:]:
        np[n] = AUS
    np.write()


def intro():
    for p in range(0, 101, 5):                          # einblenden
        logo_zeigen(p, p * 2)
        sleep_ms(30)
    pfad = logo_pfad()
    for i, (x, z) in enumerate(pfad):                   # Spieler läuft durch den Gang
        logo_zeigen(100, 200 + i * 6, (x, 7 - z))
        sleep_ms(70)
    sleep_ms(300)
    logo_zeigen(100, 200 + len(pfad) * 6)               # Spieler verschwindet am Ende
    sleep_ms(200)
    logo_aufloesen()


# ---------- Labyrinth ----------
def zeichne(wand):
    for y in range(8):
        for x in range(8):
            np[pos(x, y)] = WAND if wand[y][x] else AUS


def baue_labyrinth(animiert):
    """Zufälliges Labyrinth per Tiefensuche. Gibt (wand, start, ziel) zurück.
    Das Ziel ist die tiefste Sackgasse, also immer weit vom Start entfernt."""
    wand = [[True] * 8 for _ in range(8)]
    start = (randint(0, 3) * 2, randint(0, 3) * 2)      # Zellen liegen auf geraden Koordinaten
    x, y = start
    wand[y][x] = False
    stapel = [start]
    ziel, tiefe = start, 1
    if animiert:
        zeichne(wand)
        np.write()
    while stapel:
        x, y = stapel[-1]
        frei = [(dx, dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))
                if 0 <= x + dx <= 6 and 0 <= y + dy <= 6 and wand[y + dy][x + dx]]
        if frei:
            dx, dy = choice(frei)
            wand[y + dy // 2][x + dx // 2] = False      # Durchgang öffnen
            wand[y + dy][x + dx] = False                # neue Zelle öffnen
            stapel.append((x + dx, y + dy))
            if len(stapel) > tiefe:
                tiefe, ziel = len(stapel), (x + dx, y + dy)
            if animiert:
                zeichne(wand)
                np.write()
                sleep_ms(BAU_TEMPO)
        else:
            stapel.pop()
    return wand, start, ziel


# ---------- Spiel ----------
def spiele(wand, start, ziel):
    """True = Ziel erreicht, False = Joystick gedrückt (neues Labyrinth)."""
    x, y = start
    letzter = ticks_ms()
    while True:
        if druck.value() == 0:
            while druck.value() == 0:
                sleep_ms(10)
            return False
        dx = (rechts.value() == 0) - (links.value() == 0)
        dy = (hoch.value() == 0) - (runter.value() == 0)
        if (dx or dy) and ticks_diff(ticks_ms(), letzter) > TEMPO:
            if dx:
                dy = 0                                  # immer nur eine Richtung
            nx, ny = x + dx, y + dy
            if 0 <= nx < 8 and 0 <= ny < 8 and not wand[ny][nx]:
                x, y = nx, ny
            letzter = ticks_ms()
        zeichne(wand)
        np[pos(*ziel)] = ZIEL if (ticks_ms() // 250) % 2 else AUS
        np[pos(x, y)] = SPIELER
        np.write()
        if (x, y) == ziel:
            return True
        sleep_ms(10)


def sieg_wellen(ziel):
    """Farbige Wellen breiten sich vom Ziel über die ganze Matrix aus."""
    zx, zy = ziel
    r = 0.0
    while r < 12:
        for y in range(8):
            for x in range(8):
                d = sqrt((x - zx) ** 2 + (y - zy) ** 2)
                if abs(d - r) < 0.8:                    # vordere Welle
                    np[pos(x, y)] = rad(int(r * 30))
                elif abs(d - (r - 3)) < 0.8:            # zweite Welle dahinter
                    np[pos(x, y)] = rad(int(r * 30) + 120)
                else:
                    np[pos(x, y)] = AUS
        np.write()
        sleep_ms(60)
        r += 0.5
    for i in range(64):                                 # am Ende alles aus
        np[i] = AUS
    np.write()


def sieg_zerfall(wand, ziel):
    """Die Wände stürzen spaltenweise nach unten weg."""
    start = [randint(0, 6) for _ in range(8)]           # jede Spalte fällt zu anderer Zeit
    for t in range(16):
        for x in range(8):
            fall = max(0, t - start[x])                 # so viele Zeilen ist die Spalte schon gefallen
            for y in range(8):
                oben = y + fall
                np[pos(x, y)] = WAND if oben < 8 and wand[oben][x] else AUS
        np.write()
        sleep_ms(70)


def sieg_konfetti():
    """Bunte Pixel funkeln zufällig auf und verblassen wie Konfetti."""
    farben = [AUS] * 64
    for t in range(60):
        for i in range(64):                             # alle Pixel etwas abdunkeln
            f = farben[i]
            farben[i] = (f[0] * 6 // 10, f[1] * 6 // 10, f[2] * 6 // 10)
        if t < 45:                                      # neue Funken (die letzten Bilder nur noch verblassen)
            for _ in range(4):
                farben[randint(0, 63)] = rad(randint(0, 254))
        for i in range(64):
            np[i] = farben[i]
        np.write()
        sleep_ms(50)


def spirale_reihenfolge():
    """Alle 64 Felder in Spiralreihenfolge, von aussen nach innen."""
    x0, y0, x1, y1 = 0, 0, 7, 7
    liste = []
    while x0 <= x1 and y0 <= y1:
        for x in range(x0, x1 + 1):
            liste.append((x, y0))
        for y in range(y0 + 1, y1 + 1):
            liste.append((x1, y))
        if y0 < y1:
            for x in range(x1 - 1, x0 - 1, -1):
                liste.append((x, y1))
        if x0 < x1:
            for y in range(y1 - 1, y0, -1):
                liste.append((x0, y))
        x0, y0, x1, y1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    return liste


def sieg_spirale():
    """Ein Regenbogen wickelt sich spiralförmig nach innen auf und dann wieder ab."""
    reihenfolge = spirale_reihenfolge()
    for i, (x, y) in enumerate(reihenfolge):            # aufwickeln
        np[pos(x, y)] = rad(i * 4)
        np.write()
        sleep_ms(25)
    for x, y in reihenfolge:                            # in gleicher Reihenfolge wieder löschen
        np[pos(x, y)] = AUS
        np.write()
        sleep_ms(25)


def loesche():
    for i in range(64):
        np[i] = AUS


def sieg_feuerwerk():
    """Drei Raketen steigen auf und explodieren in bunten Ringen."""
    for _ in range(3):
        x = randint(1, 6)
        hoehe = randint(4, 6)
        farbe = rad(randint(0, 254))
        for y in range(hoehe + 1):                      # Rakete steigt auf
            loesche()
            np[pos(x, y)] = (255, 255, 255)
            if y > 0:
                np[pos(x, y - 1)] = blende(farbe, 40)   # Schweif
            np.write()
            sleep_ms(70)
        for r in range(1, 5):                           # Explosion: Ring wird grösser und dunkler
            loesche()
            for yy in range(8):
                for xx in range(8):
                    d = sqrt((xx - x) ** 2 + (yy - hoehe) ** 2)
                    if abs(d - r) < 0.7:
                        np[pos(xx, yy)] = blende(farbe, 110 - r * 22)
            np.write()
            sleep_ms(90)
        loesche()
        np.write()
        sleep_ms(150)


def ziel_blinken(wand, ziel):
    """Das Ziel blinkt dreimal weiss (läuft vor jeder Sieg-Animation)."""
    for i in range(6):
        zeichne(wand)
        np[pos(*ziel)] = (255, 255, 255) if i % 2 == 0 else AUS
        np.write()
        sleep_ms(120)


def sieg(wand, ziel):
    ziel_blinken(wand, ziel)
    if SIEG_STIL == 1:
        sieg_wellen(ziel)
    elif SIEG_STIL == 2:
        sieg_zerfall(wand, ziel)
    elif SIEG_STIL == 3:
        sieg_konfetti()
    elif SIEG_STIL == 4:
        sieg_spirale()
    else:
        sieg_feuerwerk()


if __name__ == "__main__":
    intro()
    while True:
        wand, start, ziel = baue_labyrinth(True)
        if spiele(wand, start, ziel):
            sieg(wand, ziel)
