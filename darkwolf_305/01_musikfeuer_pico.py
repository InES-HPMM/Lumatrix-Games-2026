# ============================================================
#  MUSIKFEUER - Anzeigeteil fuer die Lumatrix
#
#  Ein Kaminfeuer, das auf Musik reagiert.
#
#  Ohne Ton brennt es ruhig auf kleiner Flamme. Kommt Musik, treibt
#  sie das Feuer an: Die acht Frequenzbaender liegen genau auf den
#  acht Glutstellen am Boden. Tiefe Toene lassen die Flamme links
#  aufwallen, hohe sprenkeln rechts Funken. Ein kraeftiger Bass-
#  schlag wirft eine Stichflamme hoch.
#
#  Der Joystick regelt weiter mit:
#    HOCH / RUNTER   = Grundfeuer anfachen oder daempfen
#    LINKS / RECHTS  = Wind, die Flamme legt sich zur Seite
#    MITTE           = Scheit nachlegen
#
#  Starten musst du dieses Programm nicht von Hand - das macht
#  musikfeuer.py auf dem Laptop.
# ============================================================

import sys
import select
from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms, ticks_ms, ticks_diff
from random import randint

np = NeoPixel(Pin(19, Pin.OUT), 64)  # 8x8 LED-Matrix, (0,0) = unten links

JOY = {  # gedrueckt = 0
    "up": Pin(3, Pin.IN, Pin.PULL_UP),
    "down": Pin(6, Pin.IN, Pin.PULL_UP),
    "left": Pin(7, Pin.IN, Pin.PULL_UP),
    "right": Pin(2, Pin.IN, Pin.PULL_UP),
    "center": Pin(8, Pin.IN, Pin.PULL_UP),
}

W = H = 8

# ============================================================
#  Hier kannst du alles einstellen
# ============================================================
BRIGHTNESS = 0.25

# Stromgrenze. Die Lumatrix meldet sich am USB-Anschluss mit
# bMaxPower = 250 mA an - mehr darf sie laut eigener Anmeldung nicht
# ziehen. Genau darauf ist die Grenze gesetzt.
# Umrechnung: eine LED zieht bei vollem Weiss rund 60 mA, das sind
# 3 * 255 = 765 Farbwert-Einheiten. Eine Einheit sind also 0.0784 mA.
# Ohne diesen Deckel wuerden alle 64 LEDs zusammen fast 4 Ampere
# ziehen. Nur erhoehen, wenn die Lumatrix an einem eigenen Netzteil
# oder einem Hub mit Stromversorgung haengt.
STROM_GRENZE_MA = 250
STROM_GRENZE = int(STROM_GRENZE_MA / 0.0784)

BILD_MS = 12         # Pause pro Bild - der Rest kommt vom Rechnen

# ---------- das ruhige Grundfeuer ----------
GRUND_GLUT = 0.40    # kleine Flamme, wenn keine Musik laeuft
GLUT_SPIEL = 0.12    # wie stark die Glut von allein schwankt
KRAFT_START = 0.80   # Grundkraft, mit dem Joystick verstellbar
ZERFALL = 0.90       # wie schnell die Hitze nach oben abnimmt
UNRUHE = 0.16        # wie stark das Feuer zuckt

# ---------- wie stark die Musik eingreift ----------
MUSIK_GLUT = 0.70    # wie weit ein lautes Band seine Glutstelle anhebt
MUSIK_KRAFT = 0.45   # wie stark die Gesamtlautstaerke das Feuer antreibt
MUSIK_NACHHALL = 0.80  # kleiner = die Musik verebbt schneller im Feuer

BASS_SCHWELLE = 0.50   # ab hier gilt ein Bass als Schlag
BASS_SPRUNG = 0.16     # und er muss so viel lauter sein als eben noch
BASS_FLAMME = 500      # ms Stichflamme pro Bassschlag

FUNKEN_GRUND = 5     # Prozent pro Bild im ruhigen Feuer
FUNKEN_HOEHEN = 45   # so viel mehr Prozent bei vollen Hoehen
KNISTER = 3          # Prozent pro Bild, dass eine Glut von allein aufflammt

STILL_NACH_MS = 1500  # ohne Daten so lange, dann nur noch ruhiges Feuer


# ============================================================
#  Farben der Flamme
# ============================================================
STUFEN = (
    (0.00, (0, 0, 0)),
    (0.14, (35, 0, 0)),
    (0.32, (130, 8, 0)),
    (0.52, (240, 45, 0)),
    (0.72, (255, 125, 0)),
    (0.88, (255, 205, 35)),
    (1.00, (255, 250, 190)),
)


def palette_bauen(n=48):
    """Aus den Stufen eine weiche Farbtabelle mit n Eintraegen rechnen."""
    tabelle = []
    for i in range(n):
        p = i / (n - 1)
        for k in range(len(STUFEN) - 1):
            p0, c0 = STUFEN[k]
            p1, c1 = STUFEN[k + 1]
            if p0 <= p <= p1:
                t = (p - p0) / (p1 - p0)
                tabelle.append((int(c0[0] + (c1[0] - c0[0]) * t),
                                int(c0[1] + (c1[1] - c0[1]) * t),
                                int(c0[2] + (c1[2] - c0[2]) * t)))
                break
    return tabelle


PALETTE = palette_bauen()
LETZTE = len(PALETTE) - 1

# Fuer jedes Pixel eine Zufallszahl zu wuerfeln ist auf dem Pico zu
# langsam. Darum einmal eine Tabelle fuellen und im Kreis durchlaufen -
# die Laenge ist eine Primzahl, damit sich kein Muster einschleicht.
ZUFALL = [1.0 - UNRUHE * randint(0, 100) / 100.0 for _ in range(97)]
_zi = 0


# ============================================================
#  Zustand
# ============================================================
hitze = [0.0] * (W * H)    # Hitze jedes Pixels, 0.0 bis 1.0
ruheglut = [GRUND_GLUT] * W  # das stille Glutbett
musik = [0.0] * W          # was die Musik gerade je Spalte beitraegt
funken = []                # [x, y, Leben]

kraft = KRAFT_START        # Grundkraft, vom Joystick geregelt
wind = 0.0                 # -1.0 links bis +1.0 rechts
flamme_bis = 0             # bis wann eine Stichflamme nachwirkt
bass_vorher = 0.0
hat_musik = False


# ============================================================
#  Daten vom Laptop holen
# ============================================================
_poll = select.poll()
_poll.register(sys.stdin, select.POLLIN)
_puffer = ""


def empfangen():
    """Alles lesen, was anliegt. Nur das neueste vollstaendige Bild zaehlt,
    damit das Feuer nicht hinterherhinkt, wenn es mal stockt."""
    global _puffer
    neuestes = None
    while _poll.poll(0):
        z = sys.stdin.read(1)
        if not z:
            break
        if z == "\n":
            if len(_puffer) == W:
                neuestes = _puffer
            _puffer = ""
        else:
            _puffer += z
            if len(_puffer) > W:   # aus dem Takt geraten - wegwerfen
                _puffer = ""
    return neuestes


def musik_uebernehmen(bild):
    """Die acht Baender auf die acht Glutstellen legen. Laut geht sofort
    durch, leise klingt weich ab - sonst flackert es nervoes."""
    global bass_vorher, flamme_bis
    for x in range(W):
        ziel = (ord(bild[x]) - 48) / 62.0
        abgeklungen = musik[x] * MUSIK_NACHHALL
        musik[x] = ziel if ziel > abgeklungen else abgeklungen

    bass = (musik[0] + musik[1]) * 0.5
    if bass > BASS_SCHWELLE and bass > bass_vorher + BASS_SPRUNG:
        flamme_bis = ticks_ms() + BASS_FLAMME      # Stichflamme!
        for _ in range(6):
            funken.append([float(randint(0, W - 1)), 1.0, 1.0])
    bass_vorher = bass


# ============================================================
#  Das Feuer
# ============================================================
def glut_bewegen():
    """Das stille Glutbett atmet und knistert vor sich hin."""
    for x in range(W):
        ruheglut[x] += (randint(0, 100) - 50) / 500.0
        if ruheglut[x] < GRUND_GLUT - GLUT_SPIEL:
            ruheglut[x] = GRUND_GLUT - GLUT_SPIEL
        elif ruheglut[x] > GRUND_GLUT + GLUT_SPIEL:
            ruheglut[x] = GRUND_GLUT + GLUT_SPIEL
    if randint(0, 99) < KNISTER:
        ruheglut[randint(0, W - 1)] = GRUND_GLUT + GLUT_SPIEL


def hitze_steigen_lassen():
    """Jede Reihe uebernimmt die Hitze der Reihe darunter - verwischt,
    abgekuehlt und vom Wind zur Seite gezogen. Unten sitzt die Glut,
    und dort mischt sich die Musik ein."""
    global _zi
    h, z = hitze, ZUFALL
    zi, nz = _zi, len(ZUFALL)

    wl = 0.28 - wind * 0.20
    wr = 0.28 + wind * 0.20
    wm = 1.0 - wl - wr

    for y in range(H - 1, 0, -1):
        unten = (y - 1) * W
        oben = y * W
        kuehlung = ZERFALL - y * 0.010
        for x in range(W):
            i = unten + x
            mitte = h[i]
            links = h[i - 1] if x > 0 else mitte
            rechts = h[i + 1] if x < W - 1 else mitte
            wert = (links * wl + mitte * wm + rechts * wr) * kuehlung * z[zi]
            zi += 1
            if zi == nz:
                zi = 0
            h[oben + x] = wert if wert > 0.0 else 0.0
    _zi = zi

    # Lautstaerke insgesamt treibt das ganze Feuer an
    laut = 0.0
    for x in range(W):
        laut += musik[x]
    laut /= W
    antrieb = kraft * (1.0 + laut * MUSIK_KRAFT)
    if ticks_diff(ticks_ms(), flamme_bis) < 0:
        antrieb *= 1.35   # Stichflamme nach einem Bassschlag

    for x in range(W):   # unterste Reihe: Glutbett plus Musik
        wert = (ruheglut[x] + musik[x] * MUSIK_GLUT) * antrieb
        h[x] = wert if wert < 1.0 else 1.0


def funken_bewegen():
    """Funken steigen auf, driften mit dem Wind und verglimmen.
    Je mehr Hoehen in der Musik, desto mehr spruehen."""
    hoehen = (musik[6] + musik[7]) * 0.5
    chance = FUNKEN_GRUND + int(hoehen * FUNKEN_HOEHEN)
    if randint(0, 99) < chance:
        heisseste = 0
        for x in range(1, W):
            if ruheglut[x] + musik[x] > ruheglut[heisseste] + musik[heisseste]:
                heisseste = x
        funken.append([float(heisseste), 1.0, 1.0])

    for f in funken[:]:
        f[0] += wind * 0.35 + (randint(0, 100) - 50) / 300.0
        f[1] += 0.34
        f[2] -= 0.055
        if f[2] <= 0 or f[1] >= H or f[0] < -1 or f[0] > W:
            funken.remove(f)


def joystick_lesen():
    """Anfachen, daempfen, Wind machen, Scheit nachlegen."""
    global kraft, wind, flamme_bis

    if JOY["up"].value() == 0:
        kraft = min(1.3, kraft + 0.02)
    elif JOY["down"].value() == 0:
        kraft = max(0.35, kraft - 0.02)

    if JOY["left"].value() == 0:
        wind = max(-1.0, wind - 0.12)
    elif JOY["right"].value() == 0:
        wind = min(1.0, wind + 0.12)
    else:
        wind *= 0.92   # ohne Zutun legt sich der Wind wieder

    if JOY["center"].value() == 0 and ticks_diff(ticks_ms(), flamme_bis) > 400:
        flamme_bis = ticks_ms() + 1400
        for x in range(W):
            ruheglut[x] = GRUND_GLUT + GLUT_SPIEL
        for _ in range(10):
            funken.append([float(randint(0, W - 1)), 1.0, 1.0])


def zeichnen():
    puffer = [(0, 0, 0)] * (W * H)
    summe = 0

    for i in range(W * H):
        h = hitze[i]
        if h > 0.02:
            k = int(h * LETZTE)
            r, g, b = PALETTE[k if k < LETZTE else LETZTE]
            r, g, b = int(r * BRIGHTNESS), int(g * BRIGHTNESS), int(b * BRIGHTNESS)
            puffer[i] = (r, g, b)
            summe += r + g + b

    for fx, fy, leben in funken:
        x, y = int(fx + 0.5), int(fy)
        if 0 <= x < W and 0 <= y < H:
            f = BRIGHTNESS * leben
            alt = puffer[y * W + x]
            neu = (int(255 * f), int(190 * f), int(90 * f))
            puffer[y * W + x] = neu
            summe += neu[0] + neu[1] + neu[2] - alt[0] - alt[1] - alt[2]

    if summe > STROM_GRENZE:   # zu hell: ganzes Bild gleichmaessig daempfen
        d = STROM_GRENZE / summe
        for i in range(W * H):
            r, g, b = puffer[i]
            np[i] = (int(r * d), int(g * d), int(b * d))
    else:
        for i in range(W * H):
            np[i] = puffer[i]
    np.write()


# ============================================================
#  Hauptprogramm
# ============================================================
def run():
    # Meldet sich beim Laptop, damit der pruefen kann, dass
    # wirklich dieses Programm laeuft und nicht ein altes.
    print("ANZEIGE musikfeuer")
    global hat_musik
    letzte_daten = 0
    try:
        while True:
            jetzt = ticks_ms()
            bild = empfangen()
            if bild is not None:
                letzte_daten = jetzt
                musik_uebernehmen(bild)

            # Kommt nichts mehr, verebbt die Musik und es bleibt das
            # ruhige Kaminfeuer uebrig.
            if letzte_daten == 0 or ticks_diff(jetzt, letzte_daten) > STILL_NACH_MS:
                hat_musik = False
                for x in range(W):
                    musik[x] *= 0.90
            else:
                hat_musik = True

            joystick_lesen()
            glut_bewegen()
            hitze_steigen_lassen()
            funken_bewegen()
            zeichnen()
            sleep_ms(BILD_MS)
    finally:
        for i in range(64):   # beim Beenden geht das Feuer aus
            np[i] = (0, 0, 0)
        np.write()


if __name__ == "__main__":
    run()
