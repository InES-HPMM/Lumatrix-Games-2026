# ==============================================================
#   LUMA-ARCADE  -  eine komplette Spielkonsole auf 64 LEDs
# ==============================================================
# Dieses Programm verwandelt die Lumatrix in eine Mini-Spielkonsole: Nach der
# Startanimation wählst du im Menü zwischen SPIELE (Surf, Snake, Tetris, Flappy Bird,
# Überraschung) und ANIMATIONEN (Feuer, Plasma, Game of Life) - alle Namen laufen
# als Text über die Matrix. Rekorde bleiben auch nach dem Ausschalten gespeichert.
#
# Menü:   links/rechts = blättern, drücken = auswählen, hoch/runter = Helligkeit
# Überall: 1 Sekunde gedrückt halten = zurück
# Tipp:   Speichere die Datei auf dem Pico als "main.py", dann startet sie
#         automatisch, sobald die Lumatrix Strom bekommt.
# ==============================================================

from machine import Pin
from neopixel import NeoPixel
import utime
import random
import math

# ---------------- EINSTELLUNGEN (hier darfst du ändern) ----------------
HELLIGKEIT = 100           # Gesamthelligkeit in Prozent (25 bis 200)
ZURUECK_MS = 1000          # so lange drücken = zurück ins Menü
LAUFTEXT_MS = 160          # Tempo vom Lauftext (kleiner = schneller, größer = langsamer)
MENUE_PAUSE_MS = 1500      # Menü: so lange steht der Anfang vom Namen still

SNAKE_START_MS = 320       # Snake: Zeit pro Schritt am Anfang
SNAKE_MIN_MS = 120         # Snake: schnellstes Tempo
TETRIS_START_MS = 800      # Tetris: Fallzeit am Anfang
TETRIS_MIN_MS = 180        # Tetris: schnellste Fallzeit
FLAPPY_SPRUNG = 0.5        # Flappy: wie stark der Vogel hochspringt
FLAPPY_SCHWERKRAFT = 0.07  # Flappy: wie stark er nach unten fällt
FLAPPY_ROHR_MS = 280       # Flappy: Zeit, bis die Rohre ein Feld weiterrücken
FLAPPY_LUECKE = 3          # Flappy: Größe der Lücke im Rohr
LEBEN_MS = 250             # Game of Life: Zeit pro Generation
SURF_TEMPO = 0.10          # Surf: Grundtempo (wie schnell die Welle vorbeizieht)
SURF_SPRUNG = 0.46         # Surf: Sprungkraft
SURF_SCHWERKRAFT = 0.04    # Surf: Schwerkraft beim Springen
SURF_TAG_MS = 15000        # Surf: Dauer von Tag, Abend, Nacht und Morgen
PFEIL_MS = 600            # Überraschung: so lange wird jeder Pfeil gezeigt
UEBERRASCHUNG_CODE = ["hoch", "hoch", "runter", "runter", "links", "rechts", "links", "rechts"]
UEBERRASCHUNG_ZUFALL = False   # True = jedes Mal eine neue, zufällige Pfeil-Reihe

# Farben (rot, grün, blau)
SCHWARZ = (0, 0, 0)
WEISS = (35, 35, 35)
ROT = (60, 0, 0)
ORANGE = (60, 18, 0)
GELB = (50, 40, 0)
GRUEN = (0, 50, 0)
CYAN = (0, 40, 45)
BLAU = (0, 0, 60)
LILA = (35, 0, 55)
PINK = (55, 0, 30)
KOPF = (40, 60, 20)        # Kopf der Schlange
BRETT = (60, 22, 0)        # Surfbrett
ANZUG = (45, 0, 25)        # Neoprenanzug vom Surfer
HAUT = (40, 22, 10)        # Kopf vom Surfer
SCHAUM = (28, 38, 42)      # Wellenschaum
HAI = (24, 26, 32)         # Haiflosse
MOEWE = (40, 40, 36)       # Möwe

# ---------------- HARDWARE ----------------
np = NeoPixel(Pin(19, Pin.OUT), 64)
rechts = Pin(2, Pin.IN, Pin.PULL_UP)
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
hineindruecken = Pin(8, Pin.IN, Pin.PULL_UP)
TASTEN = {"rechts": rechts, "hoch": hoch, "runter": runter,
          "links": links, "mitte": hineindruecken}

# ---------------- BILD ----------------
# Wir malen zuerst in die Liste "bild" und schicken sie dann mit zeigen() an die LEDs.
bild = [SCHWARZ] * 64


def punkt(x, y, farbe):
    # Setzt eine LED (x von links, y von unten). Punkte außerhalb werden ignoriert.
    if 0 <= x < 8 and 0 <= y < 8:
        bild[y * 8 + x] = farbe


def leeren():
    for i in range(64):
        bild[i] = SCHWARZ


def zeigen():
    # Bild mit der eingestellten Helligkeit an die LEDs schicken
    h = HELLIGKEIT
    for i in range(64):
        r, g, b = bild[i]
        np[i] = (min(255, r * h // 100), min(255, g * h // 100), min(255, b * h // 100))
    np.write()


def dimmen(farbe, prozent):
    return (farbe[0] * prozent // 100, farbe[1] * prozent // 100, farbe[2] * prozent // 100)


def addieren(x, y, farbe):
    # Farbe zur vorhandenen Farbe dazuzählen (für leuchtende Funken)
    if 0 <= x < 8 and 0 <= y < 8:
        a = bild[y * 8 + x]
        bild[y * 8 + x] = (min(255, a[0] + farbe[0]), min(255, a[1] + farbe[1]),
                           min(255, a[2] + farbe[2]))


def farbrad(h, hell=60):
    # Regenbogen: h von 0 bis 255 läuft rot -> grün -> blau -> rot
    h = int(h) % 256
    if h < 85:
        return (hell * (85 - h) // 85, hell * h // 85, 0)
    if h < 170:
        h -= 85
        return (0, hell * (85 - h) // 85, hell * h // 85)
    h -= 170
    return (hell * h // 85, 0, hell * (85 - h) // 85)


def feuerfarbe(h, modus=0):
    # Hitze (0 bis 255) -> Farbe: schwarz, rot, orange, gelb, weiß
    if h < 20:
        return SCHWARZ
    r = min(60, h * 60 // 110)
    g = 0 if h < 90 else min(45, (h - 90) * 45 // 120)
    b = 0 if h < 200 else min(30, (h - 200) * 30 // 55)
    if modus == 1:
        return (b, g, r)   # blaues Feuer
    if modus == 2:
        return (g, r, b)   # grünes Giftfeuer
    return (r, g, b)


# ---------------- TASTEN ----------------
vorher = {}
for name in TASTEN:
    vorher[name] = False
mitte_seit = 0


def neue_tasten():
    # Liefert eine Liste der Tasten, die GERADE NEU gedrückt wurden
    global mitte_seit
    neu = []
    for name in TASTEN:
        jetzt = TASTEN[name].value() == 0
        if jetzt and not vorher[name]:
            neu.append(name)
            if name == "mitte":
                mitte_seit = utime.ticks_ms()
        vorher[name] = jetzt
    return neu


def gedrueckt(name):
    # Wird die Taste gerade festgehalten?
    return TASTEN[name].value() == 0


def zurueck():
    # True, wenn die Mitte lange gehalten wird -> zurück ins Menü
    return (vorher["mitte"] and gedrueckt("mitte")
            and utime.ticks_diff(utime.ticks_ms(), mitte_seit) > ZURUECK_MS)


def warten(ms):
    # Wartet, gibt aber True zurück, sobald jemand eine Taste drückt
    ende = utime.ticks_add(utime.ticks_ms(), ms)
    while utime.ticks_diff(ende, utime.ticks_ms()) > 0:
        if neue_tasten():
            return True
        utime.sleep_ms(10)
    return False


def warte_losgelassen():
    # Wartet (höchstens 1 Sekunde), bis keine Taste mehr gedrückt ist
    for i in range(100):
        if not any(p.value() == 0 for p in TASTEN.values()):
            break
        utime.sleep_ms(10)
    neue_tasten()


# ---------------- SCHRIFT UND LAUFTEXT ----------------
# Jeder Buchstabe ist 5 hoch (Zeilen von oben). "#" = LED an, "." = aus.
# Breite Buchstaben wie M und W sind breiter, damit man sie gut lesen kann.
SCHRIFT = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"),
    "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"),
    "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"),
    "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".###", "#...", "#.##", "#..#", ".###"),
    "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"),
    "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#..#", "#.#.", "##..", "#.#.", "#..#"),
    "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#"),
    "N": ("#..#", "##.#", "#.##", "#..#", "#..#"),
    "O": (".##.", "#..#", "#..#", "#..#", ".##."),
    "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".##.", "#..#", "#..#", "#.#.", ".#.#"),
    "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."),
    "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#..#", "#..#", "#..#", "#..#", ".##."),
    "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#...#", "#...#", "#.#.#", "##.##", "#...#"),
    "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."),
    "Z": ("###", "..#", ".#.", "#..", "###"),
    "0": ("###", "#.#", "#.#", "#.#", "###"),
    "1": (".#.", "##.", ".#.", ".#.", "###"),
    "2": ("##.", "..#", ".#.", "#..", "###"),
    "3": ("##.", "..#", ".#.", "..#", "##."),
    "4": ("#.#", "#.#", "###", "..#", "..#"),
    "5": ("###", "#..", "##.", "..#", "##."),
    "6": (".##", "#..", "###", "#.#", "###"),
    "7": ("###", "..#", ".#.", ".#.", ".#."),
    "8": ("###", "#.#", "###", "#.#", "###"),
    "9": ("###", "#.#", "###", "..#", "##."),
    " ": ("..", "..", "..", "..", ".."),
    "!": ("#", "#", "#", ".", "#"),
    "?": ("##.", "..#", ".#.", "...", ".#."),
    ":": (".", "#", ".", "#", "."),
    "-": ("...", "...", "###", "...", "..."),
    "<": ("..#", ".#.", "#..", ".#.", "..#"),
}


def text_spalten(text):
    # Wandelt Text in eine Liste von Spalten um (jedes Bit = ein Pixel, Bit 0 = oben)
    spalten = []
    for zeichen in text.upper():
        zeilen = SCHRIFT.get(zeichen, SCHRIFT["?"])
        for s in range(len(zeilen[0])):
            bits = 0
            for r in range(5):
                if zeilen[r][s] == "#":
                    bits |= 1 << r
            spalten.append(bits)
        spalten.append(0)          # eine leere Spalte zwischen den Buchstaben
    return spalten[:-1]


def text_malen(spalten, start, farbe, luecke=0):
    # Malt 8 Spalten ab "start" in die Zeilen 2 bis 6.
    # luecke > 0: Text wiederholt sich endlos mit so vielen leeren Spalten dazwischen.
    n = len(spalten)
    for x in range(8):
        i = start + x
        if luecke:
            i %= n + luecke
        bits = spalten[i] if 0 <= i < n else 0
        for r in range(5):
            if bits >> r & 1:
                punkt(x, 6 - r, farbe)


def lauftext(text, farbe=None):
    # Lässt Text einmal von rechts nach links durchlaufen. farbe=None -> Regenbogen.
    # Gibt True zurück, wenn jemand eine Taste gedrückt hat (= überspringen).
    spalten = text_spalten(text)
    t = 0
    for start in range(-8, len(spalten) + 1):
        leeren()
        text_malen(spalten, start, farbe if farbe else farbrad(t * 6))
        zeigen()
        if warten(LAUFTEXT_MS):
            return True
        t += 1
    return False


def countdown():
    # 3 - 2 - 1 vor dem Spielstart
    for zahl, farbe in (("3", ROT), ("2", GELB), ("1", GRUEN)):
        for hell in (100, 100, 100, 100, 100, 100, 60, 30, 10):
            leeren()
            text_malen(text_spalten(zahl), -2, dimmen(farbe, hell))
            zeigen()
            utime.sleep_ms(50)
    warte_losgelassen()


# ---------------- EFFEKTE FÜR SPIELENDE ----------------
def konfetti(runden=50):
    for t in range(runden):
        for i in range(64):
            bild[i] = dimmen(bild[i], 75)
        for k in range(3):
            punkt(random.randint(0, 7), random.randint(0, 7), farbrad(random.randint(0, 255)))
        zeigen()
        utime.sleep_ms(30)


# Rekorde werden in einer Datei auf dem Pico gespeichert
DATEI = "rekorde.txt"
rekorde = {}


def rekorde_laden():
    try:
        with open(DATEI) as f:
            for zeile in f:
                teile = zeile.split()
                if len(teile) == 2:
                    rekorde[teile[0]] = int(teile[1])
    except Exception:
        pass   # noch keine Datei da -> keine Rekorde


def rekorde_speichern():
    try:
        with open(DATEI, "w") as f:
            for name in rekorde:
                f.write(name + " " + str(rekorde[name]) + "\n")
    except Exception:
        pass


def spiel_ende(name, punkte, animation=True):
    # 1) dreimal rot blinken (nur wenn das Spiel keine eigene Animation hat)
    kopie = bild[:]
    for runde in range(3 if animation else 0):
        for i in range(64):
            bild[i] = ROT if kopie[i] != SCHWARZ else (10, 0, 0)
        zeigen()
        utime.sleep_ms(120)
        for i in range(64):
            bild[i] = kopie[i]
        zeigen()
        utime.sleep_ms(120)
    # 2) alles nach unten wegfallen lassen
    for runde in range(8 if animation else 0):
        for i in range(56):
            bild[i] = bild[i + 8]
        for i in range(56, 64):
            bild[i] = SCHWARZ
        zeigen()
        utime.sleep_ms(60)
    # 3) Punkte und Rekord zeigen
    alt = rekorde.get(name, 0)
    neuer_rekord = punkte > alt
    if neuer_rekord:
        rekorde[name] = punkte
        rekorde_speichern()
    warte_losgelassen()
    if lauftext("PUNKTE " + str(punkte), WEISS):
        return
    if neuer_rekord:
        konfetti()
        lauftext("NEUER REKORD!")
    else:
        lauftext("REKORD " + str(alt), GELB)


# ==============================================================
#   SPIEL 0: SURF  -  reite die Welle!
# ==============================================================
# hoch/drücken = springen, in der Luft links/rechts = Salto (+5, aber nicht
# mitten im Salto landen!), auf dem Wasser rechts/links halten = schneller/langsamer.
# Spring über Haie, pass in der Luft auf Möwen auf, sammle goldene Sterne (+3).
# Ab und zu rollt sich die Welle zu einer Röhre über dir ein: doppelte Punkte!

# Himmel für Tag, Sonnenuntergang, Nacht und Morgen: (Farbe am Horizont, Farbe oben)
HIMMEL = [((6, 14, 24), (1, 4, 16)),
          ((34, 9, 0), (12, 0, 16)),
          ((1, 1, 6), (0, 0, 2)),
          ((26, 6, 14), (3, 5, 16))]
WASSER_HELL = (0, 24, 40)
WASSER_TIEF = (0, 2, 14)
TUBE_DAUER = 170           # so viele Bilder dauert eine Röhre


def mischen(a, b, f):
    # Mischt zwei Farben: f = 0 -> nur a, f = 1 -> nur b
    f = max(0.0, min(1.0, f))
    return (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f),
            int(a[2] + (b[2] - a[2]) * f))


def welle(x, welt, t, staerke):
    # Höhe der Wasseroberfläche in Spalte x: drei Wellen werden überlagert
    w = x + welt
    h = (2.7 + staerke * (math.sin(w * 0.55) * 0.9 + math.sin(w * 1.3 + 1.7) * 0.3)
         + 0.3 * math.sin(w * 0.23 + t * 0.04))
    return max(0.6, min(4.9, h))


def spritzer(funken, x, y, anzahl, farbe, kraft, rundum=False):
    # Neue Wassertropfen oder Funken. rundum=True: in alle Richtungen (Explosion)
    for i in range(anzahl):
        if rundum:
            w = random.uniform(0, 6.283)
            s = random.uniform(0.1, kraft)
            vx, vy = math.cos(w) * s, math.sin(w) * s
        else:
            vx, vy = random.uniform(-kraft, kraft * 0.3), random.uniform(0.05, kraft + 0.1)
        f = farbe if farbe else farbrad(random.randint(0, 255))   # None = bunt
        funken.append([x, y, vx, vy, random.randint(8, 18), f])


def funken_bewegen(funken):
    # Bewegt alle Tropfen/Funken (mit Schwerkraft) und malt sie leuchtend dazu
    neu = []
    for f in funken:
        f[0] += f[2]
        f[1] += f[3]
        f[3] -= 0.03
        f[4] -= 1
        if f[4] > 0:
            neu.append(f)
            addieren(round(f[0]), round(f[1]), dimmen(f[5], min(100, f[4] * 10)))
    return neu


def welle_kommt():
    # Intro: eine riesige Welle rollt von rechts über die ganze Matrix
    funken = []
    for k in range(34):
        front = 9.0 - k * 0.45
        leeren()
        for x in range(8):
            for y in range(8):
                if x > front + 1:
                    bild[y * 8 + x] = mischen(WASSER_HELL, WASSER_TIEF, (7 - y) / 7)
                elif x > front:
                    bild[y * 8 + x] = dimmen(SCHAUM, random.randint(70, 100))
        if front > -1:   # Gischt fliegt vor der Welle her
            for i in range(2):
                funken.append([front, random.uniform(1, 7), random.uniform(-0.5, -0.15),
                               random.uniform(0.0, 0.25), random.randint(6, 12), SCHAUM])
        funken = funken_bewegen(funken)
        zeigen()
        utime.sleep_ms(35)
    # danach sinkt das Wasser auf die normale Höhe
    for k in range(12):
        pegel = 8 - k * 0.45
        for x in range(8):
            for y in range(8):
                tiefe = pegel - y - 0.5
                if tiefe < 0:
                    bild[y * 8 + x] = SCHWARZ
                elif tiefe < 0.8:
                    bild[y * 8 + x] = dimmen(SCHAUM, random.randint(70, 100))
                else:
                    bild[y * 8 + x] = mischen(WASSER_HELL, WASSER_TIEF, tiefe / 4)
        zeigen()
        utime.sleep_ms(40)


def wipeout(funken, y):
    # Sturz: riesiger Spritzer, alles wackelt, dann läuft die Matrix voll Wasser
    spritzer(funken, 2, y + 1, 25, SCHAUM, 0.5, True)
    kopie = bild[:]
    for k in range(18):
        wackeln = random.randint(-1, 1) if k < 10 else 0
        for yy in range(8):
            for x in range(8):
                q = x + wackeln
                bild[yy * 8 + x] = dimmen(kopie[yy * 8 + q], 100 - k * 3) if 0 <= q < 8 else SCHWARZ
        funken = funken_bewegen(funken)
        zeigen()
        utime.sleep_ms(35)
    blasen = []
    for k in range(24):
        pegel = k * 0.5
        for yy in range(8):
            if yy < pegel:
                for x in range(8):
                    bild[yy * 8 + x] = mischen((0, 14, 34), WASSER_TIEF, (pegel - yy) / 8)
        if random.randint(0, 1) == 0:
            blasen.append([random.randint(0, 7), 0.0])
        for b in blasen:   # Luftblasen steigen auf
            b[1] += 0.4
            if b[1] < pegel:
                addieren(b[0], int(b[1]), (12, 18, 22))
        zeigen()
        utime.sleep_ms(45)
    for k in range(10):
        for i in range(64):
            bild[i] = dimmen(bild[i], 75)
        zeigen()
        utime.sleep_ms(40)


def surf():
    countdown()
    welle_kommt()
    welt = 0.0                # wie weit wir schon gesurft sind
    t = 0                     # Bildzähler
    gas = 1.0                 # Tempo-Faktor (links/rechts halten)
    y = 3.0                   # Höhe vom Brett
    vy = 0.0
    in_luft = False
    trick = -1                # -1 = kein Salto, sonst: Bilder seit Salto-Beginn
    dreh = 1                  # Drehrichtung vom Salto
    punkte = 0
    strecke = 0.0
    dinge = []                # Haie, Möwen und Sterne: [art, x]
    naechstes = 10.0          # Abstand bis zum nächsten Ding
    funken = []               # Wassertropfen und Funken
    sternhimmel = [(random.randint(0, 7), random.randint(4, 7)) for i in range(7)]
    tube = 0                  # > 0: wir sind gerade in der Röhre
    tube_in = 600             # Bilder bis zur nächsten Röhre
    blitz = 0
    blitz_farbe = WEISS
    start = utime.ticks_ms()
    getroffen = False
    while not getroffen:
        bild_start = utime.ticks_ms()
        if zurueck():
            return
        tasten = neue_tasten()
        staerke = min(2.0, 1.2 + punkte * 0.012) * (0.45 if tube else 1.0)

        # --- Steuerung ---
        ziel = 1.0
        if not in_luft:
            if gedrueckt("rechts"):
                ziel = 1.7
            elif gedrueckt("links"):
                ziel = 0.6
            if ("hoch" in tasten or "mitte" in tasten) and not tube:
                in_luft = True
                vy = SURF_SPRUNG
                spritzer(funken, 1.5, y, 6, SCHAUM, 0.3)
        elif trick < 0 and ("links" in tasten or "rechts" in tasten):
            trick = 0
            dreh = 1 if "rechts" in tasten else -1
        gas += (ziel - gas) * 0.1
        tempo = (SURF_TEMPO + punkte * 0.0008) * gas

        # --- Welle und Surfer bewegen ---
        welt += tempo
        strecke += tempo
        if strecke >= 3:
            strecke -= 3
            punkte += 2 if tube else 1
        hoehen = [welle(x, welt, t, staerke) for x in range(8)]
        if in_luft:
            vy -= SURF_SCHWERKRAFT
            y += vy
            if trick >= 0:
                trick += 1
                if trick >= 8:            # Salto geschafft!
                    trick = -1
                    punkte += 5
                    blitz = 5
                    blitz_farbe = (14, 14, 14)
                    spritzer(funken, 2, y + 1, 14, None, 0.4, True)
            if vy < 0 and y <= hoehen[2]:
                if trick >= 0:            # mitten im Salto gelandet -> Sturz!
                    getroffen = True
                else:
                    in_luft = False
                    spritzer(funken, 2, hoehen[2], 10, SCHAUM, 0.35)
        if not in_luft:
            y = hoehen[2]
            vy = 0.0

        # --- Surfer-Figur (Brett, Körper, Kopf) ---
        by = int(y)
        if in_luft:
            schritt = (trick // 2) % 4 if trick >= 0 else 0
            figur = []
            for dx, dy, farbe in ((-1, -1, BRETT), (0, -1, BRETT), (0, 0, ANZUG), (0, 1, HAUT)):
                for k in range(schritt):          # beim Salto um 90° weiterdrehen
                    dx, dy = -dy * dreh, dx * dreh
                figur.append((2 + dx, by + 1 + dy, farbe))
        else:
            hinten = max(by - 1, min(by + 1, int(hoehen[1])))   # Brett neigt sich mit der Welle
            figur = [(1, hinten, BRETT), (2, by, BRETT), (2, by + 1, ANZUG), (2, by + 2, HAUT)]
        orte = [(fx, fy) for fx, fy, f in figur]
        # Trefferzone: nur die Spalte vom Surfer zählt, nicht das Brett-Ende
        koerper = [o for o in orte if o[0] == 2]

        # --- Haie, Möwen und Sterne ---
        naechstes -= tempo
        if naechstes <= 0:
            naechstes = random.uniform(6, 13)
            if tube or tube_in < 60:
                art = "stern"                     # kurz vor/in der Röhre keine Gefahren
            else:
                art = random.choice(("hai", "hai", "moewe", "stern", "stern"))
            dinge.append([art, 9.0])
        noch_da = []
        pixel_dinge = []
        for d in dinge:
            d[1] -= tempo + (0 if d[0] == "stern" else 0.08)   # Haie und Möwen sind schneller
            if d[1] < -3:
                continue
            cx = int(d[1] + 0.5)
            s = hoehen[max(0, min(7, cx))]
            if d[0] == "hai":
                pix = [(cx, int(s)), (cx + 1, int(s)), (cx + 1, int(s) + 1)]   # Flosse
                treff = pix[:2]                                 # die Spitze zählt nicht
                farbe = HAI
            elif d[0] == "moewe":
                if (t // 5) % 2:
                    pix = [(cx - 1, 7), (cx, 7), (cx + 1, 7)]   # Flügel oben
                else:
                    pix = [(cx - 1, 6), (cx, 7), (cx + 1, 6)]   # Flügel unten
                treff = [(cx, 7)]                                 # nur der Körper zählt
                farbe = MOEWE
            else:
                pix = [(cx, int(s + 2.5))]
                treff = pix
                farbe = dimmen(GELB, random.randint(60, 100))   # Stern funkelt
            if any(p in (orte if d[0] == "stern" else koerper) for p in treff):
                if d[0] == "stern":               # Stern eingesammelt!
                    punkte += 3
                    blitz = 4
                    blitz_farbe = (14, 10, 0)
                    spritzer(funken, cx, pix[0][1], 12, GELB, 0.35, True)
                    continue
                getroffen = True
            noch_da.append(d)
            for p in pix:
                pixel_dinge.append((p[0], p[1], farbe))
        dinge = noch_da

        # --- Röhre (die Welle rollt sich über dem Surfer ein) ---
        if tube:
            tube -= 1
        else:
            tube_in -= 1
            if tube_in <= 0 and not in_luft and all(d[0] == "stern" for d in dinge):
                tube = TUBE_DAUER
                tube_in = random.randint(700, 1000)
                blitz = 5
                blitz_farbe = (0, 12, 16)

        # --- Himmel: Tageszeit berechnen ---
        zeit = utime.ticks_diff(utime.ticks_ms(), start) / SURF_TAG_MS
        phase = int(zeit) % 4
        rest = zeit - int(zeit)
        u = max(0.0, (rest - 0.7) / 0.3)          # in den letzten 30 % zur nächsten Tageszeit
        a = HIMMEL[phase]
        b = HIMMEL[(phase + 1) % 4]
        horizont = mischen(a[0], b[0], u)
        zenit = mischen(a[1], b[1], u)
        himmel = [mischen(horizont, zenit, yy / 7) for yy in range(8)]

        # --- Wasser und Himmel malen (mit weichen Kanten) ---
        for x in range(8):
            h = hoehen[x]
            oben = mischen(mischen((0, 26, 44), SCHAUM, (h - 2.0) / 2.5), horizont, 0.3)
            for yy in range(8):
                deckung = h - yy                   # wie viel von diesem Pixel ist Wasser?
                if deckung <= 0:
                    bild[yy * 8 + x] = himmel[yy]
                    continue
                tiefe = deckung - 0.5
                if tiefe < 0.6:
                    w = dimmen(oben, random.randint(75, 100))          # Schaumkrone
                elif tiefe < 1.4:
                    w = mischen(oben, WASSER_HELL, (tiefe - 0.6) / 0.8)
                else:
                    w = mischen(WASSER_HELL, WASSER_TIEF, (tiefe - 1.4) / 3.0)
                    w = dimmen(w, 85 + int(15 * math.sin(t * 0.2 + x * 0.9 + yy * 1.7)))
                bild[yy * 8 + x] = w if deckung >= 1 else mischen(himmel[yy], w, deckung)

        # Sonne (geht im Meer unter), Mond und Sterne - nur dort, wo Himmel ist
        nacht = 0.0
        if phase < 2:
            fort = (phase + rest) / 2              # 0 = Mittag, 1 = Sonne im Meer
            sy = int(7.4 - fort * 5)
            licht = mischen((50, 40, 6), (60, 10, 0), fort)
            if phase == 1:
                nacht = u
                for gx in (5, 6, 7):               # Sonnenglitzern auf dem Wasser
                    gy = int(hoehen[gx]) - random.randint(0, 1)
                    if random.randint(0, 2) == 0:
                        addieren(gx, gy, dimmen(licht, 35))
        else:
            sy = 6
            licht = (22, 22, 16)                   # Mond
            nacht = 1.0 if phase == 2 else 1.0 - u
        for sx, sy2, p in ((6, sy, 100), (5, sy, 22), (7, sy, 22), (6, sy + 1, 22), (6, sy - 1, 22)):
            if 0 <= sy2 < 8 and hoehen[sx] <= sy2:
                addieren(sx, sy2, dimmen(licht, p))
        if nacht > 0:
            for sx, sy2 in sternhimmel:
                if hoehen[sx] <= sy2:
                    n = int(nacht * random.randint(3, 14))
                    addieren(sx, sy2, (n, n, n))

        # Röhre: von rechts rollt eine Wasserdecke über den Surfer
        if tube:
            lippe = max(0.0, 8 - min(TUBE_DAUER - tube, tube) * 0.5)
            for x in range(8):
                if x >= lippe:
                    abstand = x - lippe
                    dicke = 2 if abstand >= 2 else 1
                    for k in range(dicke):
                        if abstand < 1 or k == dicke - 1:
                            f = dimmen(SCHAUM, random.randint(70, 100))
                        else:
                            f = WASSER_HELL
                        punkt(x, 7 - k, f)
            if lippe < 7 and random.randint(0, 2) == 0:   # Tropfen fallen von der Decke
                funken.append([random.uniform(lippe, 7), 5.5, 0.0, -0.05, 10, SCHAUM])

        # Dinge, Surfer und Gischt
        for px, py, f in pixel_dinge:
            punkt(px, py, f)
        for fx, fy, f in figur:
            if trick >= 0 and f == ANZUG:
                f = farbrad(t * 25)               # beim Salto leuchtet der Surfer bunt
            punkt(fx, fy, f)
        if not in_luft and t % 2 == 0:
            funken.append([1.0, y + 0.3, random.uniform(-0.3, -0.1) - tempo,
                           random.uniform(0.1, 0.25) * gas, random.randint(5, 9), SCHAUM])
        if trick >= 0:
            funken.append([2.0, y + 1, random.uniform(-0.3, -0.1), 0.0, 8, farbrad(t * 25)])
        funken = funken_bewegen(funken)
        if blitz:
            for i in range(64):
                addieren(i % 8, i // 8, dimmen(blitz_farbe, blitz * 20))
            blitz -= 1
        zeigen()
        t += 1
        # immer gleich schnell: ca. 30 Bilder pro Sekunde
        utime.sleep_ms(max(1, 33 - utime.ticks_diff(utime.ticks_ms(), bild_start)))

    wipeout(funken, y)
    spiel_ende("surf", punkte, False)


# ==============================================================
#   SPIEL 1: SNAKE
# ==============================================================
RICHTUNGEN = {"hoch": (0, 1), "runter": (0, -1), "links": (-1, 0), "rechts": (1, 0)}


def freies_feld(belegt):
    frei = [(x, y) for y in range(8) for x in range(8) if (x, y) not in belegt]
    return random.choice(frei) if frei else None


def snake():
    countdown()
    schlange =[(3, 4), (2, 4), (1, 4)]   # das erste Element ist der Kopf
    richtung = (1, 0)
    plan = []                             # gemerkte Richtungswechsel
    futter = freies_feld(schlange)
    bissen = []                           # gefressenes Futter wandert durch den Bauch
    tempo = SNAKE_START_MS
    letzter = utime.ticks_ms()
    punkte = 0
    t = 0
    while True:
        if zurueck():
            return
        for taste in neue_tasten():
            if taste in RICHTUNGEN and len(plan) < 3:
                neu = RICHTUNGEN[taste]
                alt = plan[-1] if plan else richtung
                # nicht in die gleiche Richtung und nicht rückwärts in sich selbst
                if neu != alt and (neu[0] != -alt[0] or neu[1] != -alt[1]):
                    plan.append(neu)

        jetzt = utime.ticks_ms()
        if utime.ticks_diff(jetzt, letzter) >= tempo:
            letzter = jetzt
            if plan:
                richtung = plan.pop(0)
            # neuer Kopf (am Rand kommt die Schlange auf der anderen Seite raus)
            kopf = ((schlange[0][0] + richtung[0]) % 8, (schlange[0][1] + richtung[1]) % 8)
            gefressen = kopf == futter
            if not gefressen:
                schlange.pop()
            if kopf in schlange:
                spiel_ende("snake", punkte)
                return
            schlange.insert(0, kopf)
            bissen = [b + 1 for b in bissen if b + 1 < len(schlange)]
            if gefressen:
                punkte += 1
                bissen.append(0)
                tempo = max(SNAKE_MIN_MS, tempo - 10)
                futter = freies_feld(schlange)
                if futter is None:   # das ganze Feld ist voll: gewonnen!
                    konfetti(80)
                    spiel_ende("snake", punkte)
                    return

        # zeichnen
        leeren()
        n = len(schlange)
        for i in range(n):
            x, y = schlange[i]
            if i == 0:
                f = KOPF
            elif i in bissen:
                f = GELB
            else:
                f = farbrad(85 + i * 60 // n)   # Verlauf von grün nach blau
            punkt(x, y, f)
        if futter:
            punkt(futter[0], futter[1], dimmen(ROT, 60 + int(40 * math.sin(t * 0.2))))
        zeigen()
        utime.sleep_ms(15)
        t += 1


# ==============================================================
#   SPIEL 2: TETRIS
# ==============================================================
# Jedes Teil: (Kästchen relativ zum Drehpunkt, Farbe, darf man drehen?)
TEILE = [
    ([(-1, 0), (0, 0), (1, 0), (2, 0)], CYAN, True),     # I
    ([(0, 0), (1, 0), (0, 1), (1, 1)], GELB, False),     # O
    ([(-1, 0), (0, 0), (1, 0), (0, 1)], LILA, True),     # T
    ([(-1, 0), (0, 0), (0, 1), (1, 1)], GRUEN, True),    # S
    ([(-1, 1), (0, 1), (0, 0), (1, 0)], ROT, True),      # Z
    ([(-1, 1), (-1, 0), (0, 0), (1, 0)], BLAU, True),    # J
    ([(1, 1), (-1, 0), (0, 0), (1, 0)], ORANGE, True),   # L
]
PUNKTE_PRO_REIHEN = [0, 1, 3, 5, 8]


def passt(feld, form, px, py):
    # Kann das Teil an dieser Stelle stehen?
    for dx, dy in form:
        x = px + dx
        y = py + dy
        if x < 0 or x > 7 or y < 0:
            return False
        if y < 8 and feld[y * 8 + x]:
            return False
    return True


def tetris():
    countdown()
    feld =[None] * 64
    punkte = 0
    reihen = 0
    form, farbe, drehbar = random.choice(TEILE)
    px, py = 3, 6
    letzter = utime.ticks_ms()
    while True:
        if zurueck():
            return
        landen = False
        for taste in neue_tasten():
            if taste == "links" and passt(feld, form, px - 1, py):
                px -= 1
            elif taste == "rechts" and passt(feld, form, px + 1, py):
                px += 1
            elif taste == "hoch" and drehbar:
                neu = [(-dy, dx) for dx, dy in form]
                for schub in (0, -1, 1, -2, 2):   # notfalls etwas zur Seite schieben
                    if passt(feld, neu, px + schub, py):
                        form = neu
                        px += schub
                        break
            elif taste == "mitte":   # sofort ganz nach unten
                while passt(feld, form, px, py - 1):
                    py -= 1
                landen = True

        tempo = 60 if gedrueckt("runter") else max(TETRIS_MIN_MS, TETRIS_START_MS - reihen * 50)
        jetzt = utime.ticks_ms()
        if landen or utime.ticks_diff(jetzt, letzter) >= tempo:
            letzter = jetzt
            if not landen and passt(feld, form, px, py - 1):
                py -= 1
            else:
                # Teil festsetzen
                for dx, dy in form:
                    if py + dy > 7:          # ragt oben raus -> verloren
                        spiel_ende("tetris", punkte)
                        return
                    feld[(py + dy) * 8 + px + dx] = farbe
                # volle Reihen suchen
                volle = [y for y in range(8) if all(feld[y * 8 + x] for x in range(8))]
                if volle:
                    for blink in range(6):
                        for y in volle:
                            for x in range(8):
                                punkt(x, y, WEISS if blink % 2 == 0 else SCHWARZ)
                        zeigen()
                        utime.sleep_ms(70)
                    rest = [feld[y * 8:(y + 1) * 8] for y in range(8) if y not in volle]
                    while len(rest) < 8:
                        rest.append([None] * 8)
                    feld = [zelle for zeile in rest for zelle in zeile]
                    punkte += PUNKTE_PRO_REIHEN[len(volle)]
                    reihen += len(volle)
                # neues Teil
                form, farbe, drehbar = random.choice(TEILE)
                px, py = 3, 6
                if not passt(feld, form, px, py):
                    spiel_ende("tetris", punkte)
                    return

        # zeichnen: Feld, Schatten (wo das Teil landen wird), Teil
        for i in range(64):
            bild[i] = feld[i] if feld[i] else SCHWARZ
        sy = py
        while passt(feld, form, px, sy - 1):
            sy -= 1
        for dx, dy in form:
            punkt(px + dx, sy + dy, dimmen(farbe, 20))
        for dx, dy in form:
            punkt(px + dx, py + dy, farbe)
        zeigen()
        utime.sleep_ms(15)


# ==============================================================
#   SPIEL 3: FLAPPY BIRD
# ==============================================================
def flappy():
    countdown()
    y = 4.0                 # Höhe vom Vogel (mit Komma, für weiche Bewegung)
    vy = 0.0                 # Geschwindigkeit nach oben
    rohre = []               # jedes Rohr: [x, unterste Zeile der Lücke]
    luecke = 3
    sterne = [[random.randint(0, 7), random.randint(0, 7)] for i in range(4)]
    punkte = 0
    schritte = 0
    gestartet = False
    letzter = utime.ticks_ms()
    t = 0
    while True:
        if zurueck():
            return
        tasten = neue_tasten()
        if "hoch" in tasten or "mitte" in tasten:
            vy = FLAPPY_SPRUNG
            gestartet = True
        if gestartet:
            vy = max(vy - FLAPPY_SCHWERKRAFT, -0.5)
            y += vy
            if y > 7:
                y = 7.0
                vy = 0.0
        else:
            y = 4 + math.sin(t * 0.15) * 0.6   # schweben bis zum ersten Sprung

        jetzt = utime.ticks_ms()
        if gestartet and utime.ticks_diff(jetzt, letzter) >= max(150, FLAPPY_ROHR_MS - punkte * 6):
            letzter = jetzt
            schritte += 1
            for r in rohre:
                r[0] -= 1
                if r[0] == 0:
                    punkte += 1          # Rohr ist am Vogel vorbei
            if rohre and rohre[0][0] < 0:
                rohre.pop(0)
            if schritte % 4 == 1:        # alle 4 Schritte ein neues Rohr
                luecke = max(1, min(7 - FLAPPY_LUECKE, luecke + random.randint(-2, 2)))
                rohre.append([7, luecke])
            if schritte % 2 == 0:        # Sterne bewegen sich langsamer (sieht nach Tiefe aus)
                for s in sterne:
                    s[0] -= 1
                    if s[0] < 0:
                        s[0] = 7
                        s[1] = random.randint(0, 7)

        by = max(0, int(y + 0.5))
        tot = y < -0.4
        for r in rohre:
            if r[0] == 1 and not (r[1] <= by < r[1] + FLAPPY_LUECKE):
                tot = True

        # zeichnen
        leeren()
        for s in sterne:
            punkt(s[0], s[1], (0, 0, 8))
        for r in rohre:
            for ry in range(8):
                if not (r[1] <= ry < r[1] + FLAPPY_LUECKE):
                    punkt(r[0], ry, GRUEN)
        punkt(0, by, dimmen(GELB, 25))   # kleiner Schweif
        punkt(1, by, ROT if tot else GELB)
        zeigen()
        if tot:
            utime.sleep_ms(300)
            spiel_ende("flappy", punkte)
            return
        utime.sleep_ms(30)
        t += 1


# ==============================================================
#   EFFEKT 1: FEUER
# ==============================================================
def feuer():
    # hoch/runter = Flammenhöhe, links/rechts = Wind, drücken = Farbe
    hitze = [0] * 72      # 9 Zeilen, Zeile 0 ist die unsichtbare Glut
    modus = 0
    wind = 0
    kuehlung = 40
    while True:
        if zurueck():
            return
        for taste in neue_tasten():
            if taste == "mitte":
                modus = (modus + 1) % 3
            elif taste == "links":
                wind = max(-1, wind - 1)
            elif taste == "rechts":
                wind = min(1, wind + 1)
            elif taste == "hoch":
                kuehlung = max(10, kuehlung - 10)
            elif taste == "runter":
                kuehlung = min(90, kuehlung + 10)
        # unten neue Glut
        for x in range(8):
            hitze[x] = random.randint(140, 255)
        # Hitze steigt nach oben und kühlt dabei ab (weiter oben stärker)
        for y in range(8, 0, -1):
            for x in range(8):
                q = x - wind
                s = (hitze[(y - 1) * 8 + (q - 1) % 8] + hitze[(y - 1) * 8 + q % 8]
                     + hitze[(y - 1) * 8 + (q + 1) % 8] + hitze[max(0, y - 2) * 8 + q % 8])
                hitze[y * 8 + x] = max(0, s // 4 - random.randint(0, kuehlung + y * 8))
        for y in range(8):
            for x in range(8):
                punkt(x, y, feuerfarbe(hitze[(y + 1) * 8 + x], modus))
        zeigen()
        utime.sleep_ms(50)


# ==============================================================
#   EFFEKT 2: PLASMA
# ==============================================================
def plasma():
    # drücken = Farbschema, hoch/runter = Tempo, links/rechts = Farben verschieben
    abstand = [math.sqrt((x - 3.5) ** 2 + (y - 3.5) ** 2) for y in range(8) for x in range(8)]
    t = 0.0
    tempo = 0.12
    modus = 0
    verschiebung = 0
    while True:
        if zurueck():
            return
        for taste in neue_tasten():
            if taste == "mitte":
                modus = (modus + 1) % 3
            elif taste == "hoch":
                tempo = min(0.5, tempo + 0.04)
            elif taste == "runter":
                tempo = max(0.02, tempo - 0.04)
            elif taste == "links":
                verschiebung -= 20
            elif taste == "rechts":
                verschiebung += 20
        for y in range(8):
            for x in range(8):
                # vier Wellen überlagern sich
                v = (math.sin(x * 0.55 + t) + math.sin(y * 0.45 - t * 1.3)
                     + math.sin((x + y) * 0.35 + t * 0.7)
                     + math.sin(abstand[y * 8 + x] * 0.9 - t * 1.1))
                wert = int((v + 4) * 32)            # ergibt 0 bis 256
                if modus == 0:
                    f = farbrad(wert + verschiebung)                  # Regenbogen
                elif modus == 1:
                    f = farbrad(120 + wert // 3 + verschiebung)       # Ozean
                else:
                    f = feuerfarbe(wert)                              # Lava
                punkt(x, y, f)
        zeigen()
        utime.sleep_ms(25)
        t += tempo


# ==============================================================
#   EFFEKT 3: GAME OF LIFE
# ==============================================================
def zufalls_welt():
    return [1 if random.randint(0, 99) < 35 else 0 for i in range(64)]


def leben():
    # drücken = neue Welt, hoch/runter = Tempo
    # Junge Zellen sind weiß, alte werden blau und lila. Sterbende glühen rot nach.
    alter = zufalls_welt()       # 0 = tot, sonst: wie viele Runden die Zelle schon lebt
    geist = [0] * 64             # Nachglühen gestorbener Zellen
    verlauf = []                 # letzte Zustände, um Wiederholungen zu erkennen
    tempo = LEBEN_MS
    letzter = utime.ticks_ms()
    generation = 0
    while True:
        if zurueck():
            return
        neustart = False
        for taste in neue_tasten():
            if taste == "mitte":
                neustart = True
            elif taste == "hoch":
                tempo = max(50, tempo - 50)
            elif taste == "runter":
                tempo = min(1000, tempo + 50)

        jetzt = utime.ticks_ms()
        if utime.ticks_diff(jetzt, letzter) >= tempo:
            letzter = jetzt
            neu = [0] * 64
            for y in range(8):
                for x in range(8):
                    nachbarn = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if (dx or dy) and alter[((y + dy) % 8) * 8 + (x + dx) % 8]:
                                nachbarn += 1
                    i = y * 8 + x
                    if alter[i]:
                        if nachbarn == 2 or nachbarn == 3:
                            neu[i] = alter[i] + 1   # überlebt
                        else:
                            geist[i] = 30           # stirbt
                    elif nachbarn == 3:
                        neu[i] = 1                  # wird geboren
            alter = neu
            generation += 1
            zustand = tuple(1 if a else 0 for a in alter)
            # alles tot, Wiederholung oder zu lange? -> neue Welt
            if sum(zustand) == 0 or zustand in verlauf or generation > 200:
                neustart = True
            else:
                verlauf.append(zustand)
                if len(verlauf) > 8:
                    verlauf.pop(0)

        if neustart:
            for i in range(64):
                if alter[i]:
                    geist[i] = 30
            alter = zufalls_welt()
            verlauf = []
            generation = 0

        # zeichnen
        for i in range(64):
            a = alter[i]
            if a == 1:
                bild[i] = WEISS
            elif a > 1:
                bild[i] = farbrad(110 + min(a, 12) * 10)
            elif geist[i] > 0:
                bild[i] = (geist[i], 0, geist[i] // 3)
                geist[i] = max(0, geist[i] - 2)
            else:
                bild[i] = SCHWARZ
        zeigen()
        utime.sleep_ms(20)


# ==============================================================
#   BELOHNUNG: FEUERWERK
# ==============================================================
def feuerwerk(dauer_ms):
    # drücken = zusätzliche Rakete
    leeren()
    teile = []   # jedes Teilchen: [x, y, vx, vy, farbe, lebenszeit, ist_rakete]
    ende = utime.ticks_add(utime.ticks_ms(), dauer_ms)
    while utime.ticks_diff(ende, utime.ticks_ms()) > 0:
        if zurueck():
            return
        raketen = sum(1 for p in teile if p[6])
        if "mitte" in neue_tasten() or (raketen < 2 and random.randint(0, 25) == 0):
            teile.append([random.uniform(1, 6), 0.0, random.uniform(-0.04, 0.04),
                          random.uniform(0.36, 0.42), farbrad(random.randint(0, 255)), 0, True])
        # altes Bild etwas abdunkeln -> leuchtende Spuren
        for i in range(64):
            bild[i] = dimmen(bild[i], 55)
        neu = []
        for p in teile:
            p[0] += p[2]
            p[1] += p[3]
            if p[6]:
                p[3] -= 0.015
                if p[3] <= 0.04:
                    # Explosion: viele Funken in alle Richtungen
                    for k in range(16):
                        w = random.uniform(0, 6.283)
                        s = random.uniform(0.12, 0.38)
                        neu.append([p[0], p[1], math.cos(w) * s, math.sin(w) * s,
                                    p[4], random.randint(18, 32), False])
                    for i in range(64):   # kurzer Lichtblitz
                        bild[i] = (8, 8, 8)
                else:
                    neu.append(p)
                    addieren(round(p[0]), round(p[1]), (40, 30, 12))
            else:
                p[2] *= 0.92                 # Luftwiderstand
                p[3] = p[3] * 0.92 - 0.012   # Schwerkraft
                p[5] -= 1
                if p[5] > 0 and p[1] > -1:
                    neu.append(p)
                    funkeln = random.randint(50, 100)
                    addieren(round(p[0]), round(p[1]), dimmen(p[4], min(100, p[5] * 5) * funkeln // 100))
        teile = neu
        zeigen()
        utime.sleep_ms(30)


# ==============================================================
#   SPIEL 4: ÜBERRASCHUNG (Pfeile merken)
# ==============================================================
# Ein Pfeil, der nach oben zeigt. Die anderen Richtungen werden daraus gedreht.
PFEIL = ["...##...",
         "..####..",
         ".######.",
         "########",
         "...##...",
         "...##...",
         "...##...",
         "...##..."]
PFEIL_FARBEN = {"hoch": GRUEN, "runter": BLAU, "links": ROT, "rechts": GELB}

# Ein trauriges Gesicht (g = gelb, . = aus)
GESICHT = ["..gggg..",
           ".gggggg.",
           "gg.gg.gg",
           "gggggggg",
           "ggg..ggg",
           "gg.gg.gg",
           ".gggggg.",
           "..gggg.."]


def pfeil_malen(richtung, farbe):
    leeren()
    for zeile in range(8):
        for s in range(8):
            if PFEIL[zeile][s] == "#":
                x, y = s, 7 - zeile               # Pfeil nach oben
                if richtung == "runter":
                    y = zeile
                elif richtung == "links":
                    x, y = 7 - y, s
                elif richtung == "rechts":
                    x, y = y, 7 - s
                punkt(x, y, farbe)


def weinen():
    # Trauriges Gesicht, aus beiden Augen laufen Tränen
    for runde in range(3):
        for k in range(3, 9):
            leeren()
            for zeile in range(8):
                for x in range(8):
                    if GESICHT[zeile][x] == "g":
                        punkt(x, 7 - zeile, GELB)
            punkt(2, 7 - k, CYAN)                  # Träne links
            punkt(5, 7 - ((k + 2) % 6 + 3), CYAN)  # Träne rechts, etwas später
            zeigen()
            utime.sleep_ms(140)
    lauftext("SCHADE!", ROT)


def ueberraschung():
    # Zuerst werden Pfeile gezeigt. Wer sie richtig nachmacht, bekommt ein Feuerwerk!
    if UEBERRASCHUNG_ZUFALL:
        code = [random.choice(list(PFEIL_FARBEN)) for i in range(8)]
    else:
        code = UEBERRASCHUNG_CODE
    lauftext("MERK DIR DIE PFEILE!", WEISS)
    for richtung in code:
        pfeil_malen(richtung, PFEIL_FARBEN[richtung])
        zeigen()
        utime.sleep_ms(PFEIL_MS)
        leeren()
        zeigen()
        utime.sleep_ms(200)
    lauftext("JETZT DU!", GRUEN)
    warte_losgelassen()

    geschafft = 0          # so viele Pfeile sind schon richtig
    t = 0
    while geschafft < len(code):
        if zurueck():
            return
        for taste in neue_tasten():
            if taste not in PFEIL_FARBEN or geschafft >= len(code):
                continue
            if taste == code[geschafft]:
                geschafft += 1
                pfeil_malen(taste, PFEIL_FARBEN[taste])   # richtig: Pfeil kurz zeigen
                zeigen()
                utime.sleep_ms(250)
            else:
                pfeil_malen(taste, ROT)                   # falsch!
                zeigen()
                utime.sleep_ms(500)
                weinen()
                return
        # warten auf die Eingabe: blinkendes Fragezeichen, unten der Fortschritt
        leeren()
        text_malen(text_spalten("?"), -2, dimmen(WEISS, 60 + int(40 * math.sin(t * 0.15))))
        for i in range(len(code)):
            punkt(i, 0, GRUEN if i < geschafft else (4, 4, 4))
        zeigen()
        utime.sleep_ms(20)
        t += 1
    lauftext("SUPER!")
    feuerwerk(15000)


# ==============================================================
#   MENÜ
# ==============================================================
def wischen(farbe):
    # Kurzer Übergang: eine Linie wischt von links nach rechts über die Matrix
    for x in range(9):
        for y in range(8):
            punkt(x, y, farbe)
            punkt(x - 1, y, SCHWARZ)
        zeigen()
        utime.sleep_ms(18)


def auswahl(eintraege, wahl, punkt_farbe):
    # Zeigt ein Menü. Der Name der Auswahl läuft als Text über die Matrix.
    # Gibt die Nummer der Auswahl zurück - oder -1, wenn "drücken" lange
    # gehalten wurde (= zurück).
    global HELLIGKEIT
    n = len(eintraege)
    spalten = text_spalten(eintraege[wahl][0])
    pos = 0
    naechster = utime.ticks_add(utime.ticks_ms(), MENUE_PAUSE_MS)
    mitte_aktiv = False        # wurde "drücken" in diesem Menü begonnen?
    balken_bis = utime.ticks_ms()
    t = 0
    while True:
        for taste in neue_tasten():
            if taste == "mitte":
                mitte_aktiv = True
            elif taste == "links" or taste == "rechts":
                wahl = (wahl + (1 if taste == "rechts" else -1)) % n
                spalten = text_spalten(eintraege[wahl][0])
                pos = 0
                naechster = utime.ticks_add(utime.ticks_ms(), MENUE_PAUSE_MS)
            else:   # hoch/runter: Helligkeit
                HELLIGKEIT += 25 if taste == "hoch" else -25
                HELLIGKEIT = max(25, min(200, HELLIGKEIT))
                balken_bis = utime.ticks_add(utime.ticks_ms(), 800)
        # kurz drücken = auswählen (beim Loslassen), lange halten = zurück
        if mitte_aktiv:
            if zurueck():
                return -1
            if not vorher["mitte"]:
                return wahl

        # langer Name? -> weiterschieben, am Anfang kurz anhalten
        jetzt = utime.ticks_ms()
        if len(spalten) > 8 and utime.ticks_diff(jetzt, naechster) >= 0:
            pos = (pos + 1) % (len(spalten) + 6)
            naechster = utime.ticks_add(jetzt, MENUE_PAUSE_MS if pos == 0 else LAUFTEXT_MS)

        leeren()
        if utime.ticks_diff(balken_bis, jetzt) > 0:
            # Helligkeit als Treppe anzeigen
            for x in range(HELLIGKEIT // 25):
                for y in range(x + 1):
                    punkt(x, y, GELB)
        else:
            farbe = eintraege[wahl][1] or farbrad(t * 3)   # None = Regenbogen
            if len(spalten) <= 8:
                text_malen(spalten, -((8 - len(spalten)) // 2), farbe)   # kurz: mittig
            else:
                text_malen(spalten, pos, farbe, 6)
            for i in range(n):   # Punkte unten: wo bin ich in der Liste?
                punkt((8 - n) // 2 + i, 0, punkt_farbe if i == wahl else (4, 4, 4))
        zeigen()
        utime.sleep_ms(20)
        t += 1


# Menü-Einträge: (Name, Textfarbe, Funktion). Farbe None = Regenbogen.
SPIELE = [
    ("SURF", None, surf),
    ("SNAKE", GRUEN, snake),
    ("TETRIS", CYAN, tetris),
    ("FLAPPY BIRD", GELB, flappy),
    ("UEBERRASCHUNG", PINK, ueberraschung),
    ("< ZURUECK", WEISS, None),
]
ANIMATIONEN = [
    ("FEUER", ORANGE, feuer),
    ("PLASMA", PINK, plasma),
    ("GAME OF LIFE", CYAN, leben),
    ("< ZURUECK", WEISS, None),
]
HAUPTMENUE = [
    ("SPIELE", GRUEN, SPIELE),
    ("ANIMATIONEN", LILA, ANIMATIONEN),
]


# ==============================================================
#   STARTANIMATION
# ==============================================================
def spirale():
    # Liste aller 64 Felder als Spirale von außen nach innen
    weg = []
    li, re, un, ob = 0, 7, 0, 7
    while li <= re and un <= ob:
        for x in range(li, re + 1):
            weg.append((x, ob))
        ob -= 1
        for y in range(ob, un - 1, -1):
            weg.append((re, y))
        re -= 1
        if un <= ob:
            for x in range(re, li - 1, -1):
                weg.append((x, un))
            un += 1
        if li <= re:
            for y in range(un, ob + 1):
                weg.append((li, y))
            li += 1
    return weg


def startanimation():
    # Mit einer beliebigen Taste kann man die Animation überspringen
    weg = spirale()
    leeren()
    for i in range(64):
        punkt(weg[i][0], weg[i][1], farbrad(i * 4))
        zeigen()
        if warten(15):
            return
    for t in range(40):
        for i in range(64):
            punkt(weg[i][0], weg[i][1], farbrad(i * 4 + t * 10))
        zeigen()
        if warten(20):
            return
    for i in range(64):
        punkt(weg[i][0], weg[i][1], SCHWARZ)
        zeigen()
        if warten(10):
            return
    lauftext("LUMA ARCADE")


# ==============================================================
#   HAUPTPROGRAMM
# ==============================================================
rekorde_laden()
startanimation()
warte_losgelassen()
haupt = 0
while True:
    # Hauptmenü: SPIELE oder ANIMATIONEN
    haupt = auswahl(HAUPTMENUE, haupt, WEISS)
    if haupt < 0:
        haupt = 0
        continue
    liste = HAUPTMENUE[haupt][2]
    wischen(HAUPTMENUE[haupt][1])
    wahl = 0
    while True:
        # Untermenü: hier wird das Spiel oder die Animation gewählt
        wahl = auswahl(liste, wahl, HAUPTMENUE[haupt][1])
        if wahl < 0 or liste[wahl][2] is None:   # "< ZURUECK" oder lange gedrückt
            wischen(WEISS)
            break
        liste[wahl][2]()        # Spiel oder Animation starten
        warte_losgelassen()
    utime.sleep_ms(10)
