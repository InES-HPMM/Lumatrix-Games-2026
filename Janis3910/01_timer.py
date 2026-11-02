# ============================================================
# TIMER auf der Lumatrix (8x8)
# Die Zeit läuft sofort los (Start: 25 Minuten), und die ganze Animation
# dauert genau so lange wie die eingestellte Zeit. Sechs Szenen:
#   Feuer         - wird angezündet, brennt gross und wird immer kleiner,
#                   kurz vor Schluss wird es ausgepustet, raucht und ist weg
#   Sanduhr       - der Sand rieselt durch den Hals
#   Regen         - es regnet, das Wasser steigt, in den letzten 15 Sekunden blitzt es
#   Spirale       - füllt sich in Violett von aussen nach innen, mit hellem Kopf
#   Lavalampe     - dunkelrot, immer mehr Blasen, am Ende ist alles hellgelb
#   Baum          - wächst über die ganze Zeit, am Ende blüht er
# Ist die Zeit um, läuft eine grüne Welle über die Szene: Geschafft!
# Danach bleibt sie grün und schimmert ruhig.
#
# JOYSTICK
#   links / rechts = Szene wechseln (die Zeit läuft weiter)
#   hoch / runter  = Zeit +/- 1 Minute (gedrückt halten = schnell),
#                    danach beginnt alles von vorn
#   Mitte          = Pause (grosses rotes Dreieck) / Weiter,
#                    nach dem Ende: von vorn beginnen
# SCHIEBESCHALTER: jeder Wechsel = von vorn beginnen
#                  (ein noch nicht fertiger Baum verdorrt zuerst)
#
# SO IST DER CODE AUFGEBAUT
#   - Eine Uhr für alles: Das Hauptprogramm zählt die echten Millisekunden
#     (abgelaufen) und macht daraus den Fortschritt p = 0.0 ... 1.0.
#     Jede Szene bekommt nur dieses p und zeichnet daraus ein Bild.
#     So dauert jede Animation garantiert genau die eingestellte Zeit,
#     egal wie lange das Rechnen pro Bild dauert. In der Pause steht p still.
#   - Eine Szene ist eine Funktion f(p) oder ein Objekt mit reset(p) und
#     __call__(p) (für Szenen mit eigenem Gedächtnis wie Feuer, Regen, Lava).
#     Sie gibt eine Liste mit 64 Farben (r, g, b) zurück. Eine neue Szene
#     braucht nur diese eine Funktion und einen Eintrag in FIGUREN.
#   - Alle Zustände (laeuft / pause / fertig) laufen durch frame(), die
#     einzige Stelle, die entscheidet, was angezeigt wird.
# ============================================================
from machine import Pin
from neopixel import NeoPixel
import utime
import math
import random

# ---------- EINSTELLUNGEN ----------
START_MINUTEN = 25      # Startdauer (Joystick hoch/runter: +/- 1 Minute)
MAX_MINUTEN = 64        # längste einstellbare Dauer
START_FIGUR = 0         # 0 Feuer, 1 Sanduhr, 2 Regen, 3 Spirale, 4 Lavalampe, 5 Baum
ANZEIGE_MS = 1500       # so lange zeigt die Dauer-Anzeige die Minuten (danach startet die Zeit)
FRAME_MS = 30           # Ziel-Bildzeit (die Schleife passt sich der Rechenzeit an)
MAX_VAL = 60            # maximaler Wert pro Farbkanal (Schutz für Augen und Strom)
FALL_TEMPO_MS = 90      # Sanduhr: Fallgeschwindigkeit des Sandkorns (kleiner = schneller)
AUSPUSTEN_S = 10        # Feuer: so viele Sekunden vor Schluss wird es ausgepustet

DAUER_S = START_MINUTEN * 60    # Gesamtdauer in Sekunden (die Szenen lesen sie über rest_s)

# ---------- Hardware ----------
np = NeoPixel(Pin(19, Pin.OUT), 64)         # 64 LEDs an Pin 19, Pixel 0 ist unten links
schalter = Pin(9, Pin.IN, Pin.PULL_UP)      # Schiebeschalter: jeder Wechsel = von vorn

class Taste:
    # Ein Joystick-Knopf mit Flankenerkennung: neu() ist nur beim Drücken True,
    # nicht dauernd, solange gedrückt. Mit halten=True wiederholt es sich nach
    # 450 ms alle 110 ms (für schnelles Hoch-/Runterzählen der Zeit).
    def __init__(self, nr, halten=False):
        self.pin = Pin(nr, Pin.IN, Pin.PULL_UP)
        self.halten = halten                # True = wiederholt sich beim Gedrückthalten
        self.unten = False
        self.weiter = 0

    def neu(self, jetzt):
        # True beim neuen Druck (mit halten=True auch immer wieder, solange gedrückt)
        if self.pin.value():
            self.unten = False
            return False
        if not self.unten:
            self.unten = True
            self.weiter = utime.ticks_add(jetzt, 450)
            return True
        if self.halten and utime.ticks_diff(jetzt, self.weiter) >= 0:
            self.weiter = utime.ticks_add(jetzt, 110)
            return True
        return False

RECHTS, HOCH, RUNTER, LINKS, MITTE = Taste(2), Taste(3, True), Taste(6, True), Taste(7), Taste(8)

# ---------- Hilfsfunktionen ----------
# Koordinaten: x = 0 ist links, y = 0 ist die UNTERSTE Zeile; Index = y * 8 + x

def leer():
    return [(0, 0, 0)] * 64

def punkt(b, x, y, c):
    # Punkt setzen (ausserhalb der Matrix wird ignoriert)
    if 0 <= x < 8 and 0 <= y < 8:
        b[y * 8 + x] = c

def licht(f, i, c, k):
    # Farbe c (Anteile 0..1) mit Helligkeit k auf Pixel i addieren (begrenzt auf MAX_VAL)
    o = f[i]
    f[i] = (min(MAX_VAL, o[0] + int(c[0] * k)),
            min(MAX_VAL, o[1] + int(c[1] * k)),
            min(MAX_VAL, o[2] + int(c[2] * k)))

def skal(c, f):
    # Farbe mit Faktor f (0.0 bis 1.0) abdunkeln
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))

def heller(a, b):
    # pro Farbkanal den höheren Wert nehmen
    return (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))

def mischen(a, b, m):
    # fliessender Übergang von Farbe a (m=0) zu Farbe b (m=1)
    return (a[0] + (b[0] - a[0]) * m, a[1] + (b[1] - a[1]) * m, a[2] + (b[2] - a[2]) * m)

def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)

def rest_s(p):
    # verbleibende Sekunden bei Fortschritt p (für Szenen mit festen Zeitpunkten
    # wie das Auspusten des Feuers oder die Blitze, die von hinten gezählt werden)
    return (1.0 - p) * DAUER_S

def zeige(b):
    for i in range(64):
        np[i] = b[i]
    np.write()

# ---------- FARBEN (rot, grün, blau) ----------
ROT = (60, 0, 0)                                # Pause-Dreieck
SAND = (60, 35, 0)                              # Sanduhr und Dauer-Anzeige
MARKER = (40, 40, 40)                           # jede 5. Minute bei der Dauer-Anzeige
GLAS, WEISS = (3, 3, 3), (25, 25, 25)           # Sanduhr: leeres Glas, Glaswände
LAUB, WELK_LAUB, BRAUN = (5, 45, 5), (35, 16, 0), (30, 14, 0)
BLUETEN_FARBEN = [(60, 15, 35), (60, 50, 0)]    # rosa und gelb

# ---------- 1) SANDUHR ----------
# Pro Kammer 4 Zeilen mit 8, 6, 4, 2 Sandkörnern; jede Zeile braucht Zeit nach Sandmenge
BREITEN = [8, 6, 4, 2]                              # von aussen zum Hals
STARTS = [sum(BREITEN[:k]) for k in range(4)]       # ab wann läuft welche Zeile
GESAMT = sum(BREITEN)
WAND = [(x, y) for k in range(1, 4) for y in (k, 7 - k)        # Glaswände neben den schmalen Zeilen
        for x in ((8 - BREITEN[k]) // 2 - 1, (8 + BREITEN[k]) // 2)]

def sanduhr(p):
    q = p * GESAMT                                  # Fortschritt von 0 bis GESAMT
    b = leer()
    for x, y in WAND:
        b[y * 8 + x] = WEISS
    for k in range(4):
        w = BREITEN[k]
        a = min(1.0, max(0.0, (q - STARTS[k]) / w))             # wie weit ist diese Zeile durch?
        oben, unten = heller(GLAS, skal(SAND, 1 - a)), heller(GLAS, skal(SAND, a))
        for x in range((8 - w) // 2, (8 + w) // 2):
            b[(7 - k) * 8 + x] = oben               # oben wird die Zeile dunkler
            b[k * 8 + x] = unten                    # unten heller
    if q < GESAMT:                                  # ein Sandkorn fällt auf die gerade gefüllte Zeile
        k = 0
        while k < 3 and q >= STARTS[k] + BREITEN[k]:
            k += 1
        n = 4 - k                                   # Fallhöhe in Zeilen
        t = utime.ticks_ms()
        x = 3 + (t // (FALL_TEMPO_MS * (n + 1))) % 2            # wechselt zwischen 2 Halsspalten
        schritt = (t // FALL_TEMPO_MS) % (n + 1)
        if schritt < n:
            i = (3 - schritt) * 8 + x
            b[i] = heller(b[i], SAND)
    return b

# ---------- 2) BAUM ----------
# Alle 36 Teile (Stamm, Äste, Blätter, Blüten) wachsen nacheinander im gleichen
# Abstand über die GANZE Zeit und blenden langsam ein. Ganz am Ende blüht er.
HOLZ, BLATT, BLUETE = 0, 1, 2
STAMM = [(3, 0), (4, 0), (3, 1), (4, 1), (3, 2), (4, 2)]
AESTE = [(3, 3), (4, 3), (2, 3), (5, 3)]
BLAETTER = [(x, y) for y, w in ((4, 8), (5, 6), (6, 4), (7, 2))     # von unten nach oben,
            for x in sorted(range((8 - w) // 2, (8 + w) // 2),      # in jeder Zeile von der Mitte nach aussen
                            key=lambda x: abs(2 * x - 7))]
BLUETEN = [(3, 6), (1, 5), (5, 5), (6, 4), (2, 4), (4, 7)]
TEILE = ([(x, y, HOLZ) for x, y in STAMM + AESTE] +
         [(x, y, BLATT) for x, y in BLAETTER] +
         [(x, y, BLUETE) for x, y in BLUETEN])

def baum(p, welk=0.0):
    # welk: 0.0 gesund ... 1.0 verdorrt (nur für die Verdorr-Animation)
    b = leer()
    for x in range(8):
        b[x] = (0, 5, 0)                            # Gras
    n = p * len(TEILE)
    ganz = int(n)                                   # so viele Teile sind fertig gewachsen
    sichtbar = TEILE[:ganz + 1]                     # plus das gerade wachsende
    blaetter = sum(1 for t in sichtbar if t[2] == BLATT)
    behalten = blaetter - int(max(0.0, welk - 0.4) / 0.6 * blaetter)    # der Rest ist abgefallen
    laub = mischen(LAUB, WELK_LAUB, min(1.0, welk * 2))                 # welkes Laub wird gelbbraun
    nr = 0                                          # zählt die Blätter
    for i in range(len(sichtbar)):
        x, y, art = sichtbar[i]
        f = 1.0 if i < ganz else n - ganz           # das neue Teil blendet langsam ein
        if art == HOLZ:
            punkt(b, x, y, skal(BRAUN, f))
        elif art == BLATT:
            if nr < behalten:
                punkt(b, x, y, skal(laub, f))
            elif x != 3 and x != 4:
                punkt(b, x, 0, (25, 12, 0))         # abgefallenes Blatt liegt am Boden
            nr += 1
        elif welk < 0.2:
            punkt(b, x, y, skal(BLUETEN_FARBEN[i % 2], f))      # abwechselnd rosa und gelb
    return b

# ---------- 3) SPIRALE ----------
def spirale_liste():
    # alle 64 Felder von aussen nach innen (beginnt unten links)
    x0, y0, x1, y1 = 0, 0, 7, 7
    out = []
    while x0 <= x1 and y0 <= y1:
        out += [y0 * 8 + x for x in range(x0, x1 + 1)]
        out += [y * 8 + x1 for y in range(y0 + 1, y1 + 1)]
        if y0 < y1:
            out += [y1 * 8 + x for x in range(x1 - 1, x0 - 1, -1)]
        if x0 < x1:
            out += [y * 8 + x0 for y in range(y1 - 1, y0, -1)]
        x0, y0, x1, y1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
    return out

SPIRALE = spirale_liste()

VIOLETT_DUNKEL, VIOLETT_HELL = (22, 0, 40), (58, 22, 60)    # aussen tiefviolett, innen helles Flieder
KOMET = (60, 30, 60)                                        # heller Kopf der Spirale

def spirale(p):
    t = utime.ticks_ms()
    b = [(3, 0, 6)] * 64                            # leise leuchtende Bahn
    n = p * 64
    ganz = int(n)
    for k in range(min(ganz + 1, 64)):              # alle gefüllten Felder plus der Kopf
        c = mischen(VIOLETT_DUNKEL, VIOLETT_HELL, k / 63)               # Farbverlauf entlang der Bahn
        c = mischen(c, KOMET, clamp01(1.0 - (n - k - 1) / 6))           # Schweif: hinter dem Kopf noch hell
        f = 0.85 + 0.15 * math.sin(t / 500 - k * 0.45)                  # Schimmer wandert über die Bahn
        if k == ganz:
            f *= n - ganz                           # der Kopf blendet langsam ein
        b[SPIRALE[k]] = skal(c, f)
    return b

# ---------- 4) FEUER (aus dem Ambiente-Programm) ----------
def flamme(heat, wind, flick, fuel, size):
    # Prinzip: Die unterste Zeile wird mit Hitze gespeist, jede Zeile darüber
    # übernimmt die Hitze der Zeile darunter, abgeschwächt und zufällig gestört.
    # So steigt die Wärme nach oben und kühlt dabei ab: das sieht aus wie Feuer.
    # Ein Simulationsschritt der Flamme. wind: -1..1 (Neigung), flick: Unruhe,
    # fuel: Brennstoff, size: 0..1 (1 = fast das ganze Feld)
    base = heat[0]
    spread = 0.38 - 0.25 * size
    for x in range(8):
        m = max(0.0, 1.0 - abs(x - 3.5) * spread)
        base[x] = min(1.0, fuel * m * (0.85 + random.random() * 0.3 * flick))
    shift = wind * 0.35
    decay = 0.76 + 0.17 * size
    edge_pen = 0.04 - 0.03 * size
    edge_free = 0.5 + 2.0 * size
    turb = 0.07 - 0.03 * size
    k = 0.25 * size
    for y in range(7, 0, -1):
        prev = heat[y - 1]
        if k > 0:
            sm = [0.0] * 8
            for x in range(8):
                l = prev[x - 1] if x > 0 else 0.0
                r = prev[x + 1] if x < 7 else 0.0
                sm[x] = prev[x] * (1.0 - 2.0 * k) + (l + r) * k
            prev = sm
        row = heat[y]
        cx = 3.5 + shift * y
        for x in range(8):
            sx = x - shift
            x0 = int(math.floor(sx))
            fr = sx - x0
            a = prev[x0] if 0 <= x0 < 8 else 0.0
            b = prev[x0 + 1] if 0 <= x0 + 1 < 8 else 0.0
            v = (a + (b - a) * fr) * decay
            e = abs(x - cx) - edge_free
            if e > 0:
                v -= e * edge_pen * y
            v -= random.random() * turb * flick
            row[x] = v if v > 0 else 0.0

def flammenfarbe(h, scale):
    if h < 0.03:
        return (0, 0, 0)
    r = min(1.0, h * 1.9)
    g = clamp01((h - 0.22) * 1.25)
    b = clamp01((h - 0.82) * 2.0)
    return (int(r * r * scale), int(g * g * scale), int(b * scale))

class Feuer:
    # Ablauf: angezündet -> brennt auf der grössten Stufe -> wird immer kleiner ->
    # AUSPUSTEN_S vor Schluss ausgepustet -> Glut und Rauch -> zum Schluss ist alles weg
    SPARK, ZUENDEN, BLASEN = 10, 50, 12     # Bilder: Streichholz wandert / Anzünden gesamt / Ausblasen

    def __init__(self):
        self.heat = [[0.0] * 8 for _ in range(8)]
        self.reset(0.0)

    def kalt(self):
        for row in self.heat:
            for x in range(8):
                row[x] = 0.0

    def reset(self, p):
        self.kalt()
        self.t = 0
        self.gust = self.lick = self.fuel = self.drift = 0.0
        self.smoke = []
        self.blow_dir = self.blow_t = 0
        if p < 0.01:
            self.state, self.ig_t = "ZUENDEN", 0            # ganz am Anfang: Streichholz
        elif rest_s(p) <= AUSPUSTEN_S:
            self.state = "AUS"
        else:
            self.state = "BRENNT"

    def zeichne(self, f, scale):
        for y in range(8):
            row = self.heat[y]
            for x in range(8):
                if row[x] >= 0.03:
                    f[y * 8 + x] = flammenfarbe(row[x], scale)

    def __call__(self, p):
        self.t += 1
        f = leer()
        rest = rest_s(p)
        size = clamp01((rest - AUSPUSTEN_S) / (DAUER_S - AUSPUSTEN_S))  # 1 = grösste Stufe (8), schrumpft bis zum Auspusten
        scale = MAX_VAL * (0.45 + 0.55 * size)
        # Windböen neigen die Flamme
        self.gust = self.gust * 0.9 + (random.random() - 0.5) * 0.12
        if random.random() < 0.01:
            self.gust += (random.random() - 0.5) * 1.4
        wind = max(-1.3, min(1.3, self.gust + math.sin(self.t * 0.07) * 0.06))
        flick = 0.8 + abs(wind)
        s = self.state
        if s == "ZUENDEN":
            self.ig_t += 1
            t = self.ig_t
            if t < self.SPARK:                              # das Streichholz wandert zum Docht
                v = 0.6 + 0.4 * random.random()
                f[max(0, 2 - t // 5) * 8 + min(3, int(t * 0.4 + 0.5))] = (
                    int(scale * v), int(scale * 0.7 * v), int(scale * 0.2 * v))
            else:                                           # die Flamme wächst an
                fuel = min(1.0, ((t - self.SPARK) / (self.ZUENDEN - self.SPARK)) ** 1.4)
                flamme(self.heat, wind, flick, fuel, size)
                self.zeichne(f, scale)
            if t >= self.ZUENDEN:
                self.state = "BRENNT"
        elif s == "BRENNT":
            self.lick *= 0.8
            if random.random() < 0.03 * flick:
                self.lick = 0.35                            # kurzes Aufflackern
            self.fuel = 1.0 + math.sin(self.t * 0.11) * 0.06 + self.lick
            flamme(self.heat, wind, flick, self.fuel, size)
            self.zeichne(f, scale)
            if rest <= AUSPUSTEN_S:
                self.blow_dir = random.choice((-1, 1))
                self.blow_t = self.BLASEN
                self.state = "BLASEN"
        elif s == "BLASEN":                                 # Windstoss: die Flamme legt sich flach
            self.blow_t -= 1
            self.fuel *= 0.78
            flamme(self.heat, self.blow_dir * 1.8, 2.2, self.fuel, size)
            self.zeichne(f, scale)
            if self.blow_t <= 0:
                self.kalt()
                self.smoke = []
                self.drift = self.blow_dir * 0.1
                self.state = "AUS"
        else:                                               # Glut und Rauch, die bis zum Schluss verlöschen
            glut = clamp01(rest / (AUSPUSTEN_S - 0.5))
            if glut > 0:
                e = glut * (0.75 + 0.25 * random.random())
                r = int(MAX_VAL * 0.6 * e)
                f[3] = f[4] = (r, r // 8, 0)
                if glut > 0.25 and random.random() < glut * 0.8 and len(self.smoke) < 24:
                    self.smoke.append([3.5 + random.random() - 0.5, 1.0, 1.0])
            self.drift *= 0.99
            lebend = []
            for q in self.smoke:                            # Rauch: [x, y, Leben]
                q[1] += 0.2 + random.random() * 0.12
                q[0] += self.drift + (random.random() - 0.5) * 0.25
                q[2] -= 0.022
                px, py = int(q[0] + 0.5), int(q[1] + 0.5)
                if q[2] > 0 and 0 <= px < 8 and 0 <= py < 8:
                    v = min(MAX_VAL, int(MAX_VAL * 0.5 * q[2]) + f[py * 8 + px][0])
                    f[py * 8 + px] = (v, v, v)
                    lebend.append(q)
            self.smoke = lebend
        return f

# ---------- 5) REGEN (aus dem Ambiente-Programm) ----------
class Regen:
    # Tropfen mit Schweif fallen ins Wasser und lassen Wellenringe entstehen; das Wasser
    # steigt über die ganze Zeit bis oben. In den letzten 15 Sekunden blitzt es mehrmals.
    STAERKE = 0.6                                   # Regenstärke 0.1 bis 1.0
    BLAU = (0.30, 0.50, 1.00)
    HELL = (0.75, 0.85, 1.00)
    SCHWEIF = (0.45, 0.25, 0.10)
    BLITZ = (1.0, 0.1, 0.8, 0.0, 0.0, 0.5, 0.3, 0.15, 0.07)     # Helligkeit des Mehrfachblitzes pro Bild
    BLITZE_S = (13.5, 10.0, 6.5, 3.0, 0.8)          # bei dieser Restzeit (Sekunden) blitzt es

    def __init__(self):
        self.reset(0.0)

    def reset(self, p):
        self.t = 0
        self.tropfen = []                           # [x, y, Geschwindigkeit]
        self.ringe = []                             # [x, Radius, Leben]
        self.flash = []                             # Helligkeitsfolge des laufenden Blitzes
        self.strahl = []                            # Zickzack des Blitzes
        self.offen = [s for s in self.BLITZE_S if s < rest_s(p)]    # Blitze, die noch kommen

    def blitzen(self):
        # Mehrfachblitz mit sichtbarem Zickzack-Strahl
        self.flash = list(self.BLITZ)
        x = random.randint(2, 5)
        self.strahl = []
        for y in range(7, 0, -1):
            self.strahl.append((x, y))
            x = max(0, min(7, x + random.choice((-1, 0, 0, 1))))

    def __call__(self, p):
        self.t += 1
        f = leer()
        if self.offen and rest_s(p) <= self.offen[0]:
            self.offen.pop(0)
            self.blitzen()
        st = self.STAERKE
        scale = MAX_VAL * (0.55 + 0.45 * st)
        wasser = min(7, int(p * 7))                 # Zeile der Wasseroberfläche (0 = erste Pfütze)

        # neue Tropfen, solange noch Platz über dem Wasser ist
        if wasser < 7 and len(self.tropfen) < 3 + int(10 * st) and random.random() < 0.06 + 0.5 * st:
            speed = (0.22 + random.random() * 0.2) * (0.3 + 1.2 * st)
            self.tropfen.append([random.randint(0, 7), 7.4, speed])

        # Tropfen fallen (Kopf + Schweif nach oben) und treffen auf die Oberfläche
        lebend = []
        for d in self.tropfen:
            d[1] -= d[2]
            if d[1] < wasser + 1.0:
                self.ringe.append([d[0], 0.0, 1.0])
                continue
            lebend.append(d)
            zeile = min(7, int(d[1] + 0.5))
            licht(f, zeile * 8 + d[0], self.BLAU, scale)
            for j in range(3):
                if zeile + 1 + j < 8:
                    licht(f, (zeile + 1 + j) * 8 + d[0], self.BLAU, scale * self.SCHWEIF[j])
        self.tropfen = lebend

        # Wellenringe an den Aufschlagstellen
        lv = [0.0] * 8
        ringe = []
        for r in self.ringe:
            r[1] += 0.3
            r[2] -= 0.06
            if r[2] > 0:
                ringe.append(r)
                for x in range(8):
                    dd = abs(abs(x - r[0]) - r[1])
                    if dd < 0.8:
                        lv[x] += r[2] * (1.0 - dd / 0.8)
        self.ringe = ringe

        # Wasser: der Körper füllt sich von unten, die Oberfläche flackert und trägt die Ringe
        for y in range(wasser + 1):
            for x in range(8):
                v = 0.20 + 0.012 * y + 0.07 * math.sin(self.t * 0.13 + x * 1.7 + y) + random.random() * 0.06
                if y == wasser:
                    v += 0.10 + lv[x] * 0.8
                licht(f, y * 8 + x, self.BLAU, scale * min(1.0, v))

        # Blitz: Strahl + helles Aufleuchten des ganzen Feldes
        if self.flash:
            lvl = self.flash.pop(0)
            k = MAX_VAL * (0.35 + 0.65 * (0.55 + 0.45 * st)) * lvl
            if lvl > 0.4:
                for bx, by in self.strahl:
                    licht(f, by * 8 + bx, (1.0, 1.0, 1.0), k)
            for i in range(64):
                licht(f, i, self.HELL, k * 0.45)
        return f

# ---------- 6) LAVALAMPE (aus dem Ambiente-Programm) ----------
class Lava:
    # Blasen steigen auf und verschmelzen (Metaballs). Am Anfang ist alles dunkelrot, irgendwann
    # kommt die erste Blase, dann immer mehr; zum Schluss füllt sich die ganze Lampe hellgelb.
    DUNKEL = (0.17, 0.01, 0.00)                     # dunkles Rot (Lampenglut)
    MITTE = (1.00, 0.22, 0.00)                      # Orange
    HELL = (1.00, 0.92, 0.35)                       # Hellgelb
    HOMES = (1.3, 5.7, 3.5, 2.3, 4.7, 0.8, 6.3, 3.0)    # Bahn (Spalte) jeder Blase
    ERSTE, LETZTE = 0.10, 0.65                      # ab hier kommt die erste / die letzte Blase (Anteil der Zeit)
    FLUT = 0.45                                     # ab hier füllt sich der Rest der Lampe mit Gelb

    def __init__(self):
        self.reset(0.0)

    def reset(self, p):
        self.t = 0
        n = len(self.HOMES)
        self.blobs = []     # [x, y, vy, Temperatur, Radius, Bahn, Heizrate, Start]
        for i in range(n):
            start = self.ERSTE + (self.LETZTE - self.ERSTE) * i / (n - 1)
            unterwegs = p >= start                  # bei einem Neustart mittendrin: irgendwo in der Lampe
            self.blobs.append([self.HOMES[i], random.random() * 7.0 if unterwegs else 0.0, 0.0,
                               random.random() if unterwegs else 0.8, 1.0 + random.random() * 0.4,
                               self.HOMES[i], 0.6 + random.random() * 0.8, start])

    def __call__(self, p):
        self.t += 1
        spd = 0.8 + 0.8 * p                         # die Lampe wird immer lebhafter
        akt = []
        for i in range(len(self.blobs)):
            b = self.blobs[i]
            if p < b[7]:
                continue                            # diese Blase kommt erst noch
            if b[1] < 1.5:                          # Temperatur: unten heizt, oben kühlt
                b[3] += 0.012 * spd * b[6]
            elif b[1] > 6.2:
                b[3] -= 0.022 * spd * b[6]
            else:
                b[3] -= 0.0015 * spd
            b[3] = clamp01(b[3])
            b[2] += (b[3] - 0.5) * 0.006 * spd      # Auftrieb
            b[2] *= 0.96
            b[1] += b[2] * spd
            if b[1] < 0.0:
                b[1], b[2] = 0.0, 0.0
            elif b[1] > 7.4:
                b[1], b[2] = 7.4, 0.0
            b[0] = b[5] + 0.7 * math.sin(self.t * 0.011 + i * 2.1) + 0.35 * math.sin(self.t * 0.0063 + i * 1.3)
            b[0] = max(0.3, min(6.7, b[0]))
            r = b[4] * clamp01((p - b[7]) / 0.08) * (1.0 + 0.8 * p)    # die Blase wächst beim Erscheinen
            if r > 0.3:
                akt.append((b[0], b[1], r * r))
        flut = 2.2 * clamp01((p - self.FLUT) / (1.0 - self.FLUT)) ** 3     # füllt sich erst langsam, ganz am Ende ganz
        f = leer()
        for y in range(8):
            glow = 0.7 + 0.9 * (6 - min(y, 6)) / 7.0                    # unten glüht es stärker
            dunkel = (self.DUNKEL[0] * glow, self.DUNKEL[1] * glow, self.DUNKEL[2] * glow)
            for x in range(8):
                v = flut
                for bx, by, r2 in akt:
                    v += 0.4 * r2 / ((x - bx) * (x - bx) + (y - by) * (y - by) + 0.5)
                t = clamp01((v - 0.5) / 1.5)
                if t < 0.5:
                    c = mischen(dunkel, self.MITTE, t * 2.0)
                else:
                    c = mischen(self.MITTE, self.HELL, (t - 0.5) * 2.0)
                f[y * 8 + x] = (int(c[0] * MAX_VAL), int(c[1] * MAX_VAL), int(c[2] * MAX_VAL))
        return f

feuer, regen, lava = Feuer(), Regen(), Lava()
FIGUREN = [feuer, sanduhr, regen, spirale, lava, baum]   # Reihenfolge beim Wechseln mit links/rechts
SZENEN = (feuer, regen, lava)               # Szenen mit eigenem Zustand: bei jedem Neustart zurücksetzen

def alle_neu(p):
    for s in SZENEN:
        s.reset(p)

# ---------- Zustände: Pause, Ende, Dauer-Anzeige ----------
PAUSE_BILD = (".##.....",                           # grosses Dreieck in der Mitte (oben beginnend)
              ".###....",
              ".#####..",
              ".######.",
              ".######.",
              ".#####..",
              ".###....",
              ".##.....")
DREIECK = [(7 - r) * 8 + x for r in range(8) for x in range(8) if PAUSE_BILD[r][x] == "#"]

def pausiert(b):
    # die Szene bleibt ganz leise im Hintergrund sichtbar, davor das rote Dreieck
    out = [skal(c, 0.12) for c in b]
    for i in DREIECK:
        out[i] = ROT
    return out

def gruen(b):
    # Belohnung: die Szene wird grün, der Hintergrund glimmt leise, und ein weiches
    # Schimmern wandert diagonal darüber (alles bleibt grün, nichts blinkt)
    t = utime.ticks_ms()
    out = []
    for i in range(64):
        f = 0.725 + 0.275 * math.sin(t / 450 - (i % 8 + i // 8) * 0.7)
        out.append((0, int(max(14, max(b[i])) * f), 0))
    return out

def frame(figur, zustand, p):
    # das Bild für den aktuellen Zustand (für die Anzeige und als Ausgangsbild beim Wischen)
    if zustand == "fertig":
        return gruen(FIGUREN[figur](1.0))
    b = FIGUREN[figur](p)
    return pausiert(b) if zustand == "pause" else b

def dauer_bild(minuten):
    # 1 LED = 1 Minute, von unten links zeilenweise, jede 5. heller
    b = leer()
    for i in range(minuten):
        b[i] = MARKER if (i + 1) % 5 == 0 else SAND
    return b

def wischen(alt, neu, aufwaerts, kante=(30, 30, 30), ms=70):
    # eine helle Linie wischt über die Matrix, dahinter erscheint das neue Bild
    for k in range(9):
        b = []
        for i in range(64):
            y = i // 8 if aufwaerts else 7 - i // 8
            b.append(neu[i] if y < k else kante if y == k else alt[i])
        zeige(b)
        utime.sleep_ms(ms)

def neustart(figur, zustand, p):
    # alles von vorn: ein noch nicht fertiger Baum verdorrt zuerst, dann wischt eine Linie zum Start
    alt = frame(figur, zustand, p)
    if FIGUREN[figur] is baum and zustand != "fertig" and p > 0.03:
        for i in range(61):
            zeige(baum(p, i / 60))
            utime.sleep_ms(55)
        utime.sleep_ms(800)
        alt = baum(p, 1.0)
    alle_neu(0.0)
    wischen(alt, FIGUREN[figur](0.0), False)

# ---------- Hauptprogramm ----------
def main():
    # Zustände: "laeuft" -> "fertig" (Zeit um); Mitte schaltet "laeuft" <-> "pause"
    global DAUER_S
    figur, minuten = START_FIGUR, START_MINUTEN
    DAUER_S = minuten * 60
    alle_neu(0.0)
    zustand = "laeuft"           # laeuft, pause oder fertig
    abgelaufen = 0               # gelaufene Zeit in Millisekunden
    p = 0.0                      # Fortschritt 0.0 bis 1.0
    anzeige_bis = 0              # bis wann die Dauer-Anzeige zu sehen ist
    sw_alt = schalter.value()
    letzt = utime.ticks_ms()

    while True:
        jetzt = utime.ticks_ms()
        dt = utime.ticks_diff(jetzt, letzt)
        letzt = jetzt

        # Schiebeschalter: jeder Wechsel = von vorn beginnen
        if schalter.value() != sw_alt:
            neustart(figur, zustand, p)
            sw_alt = schalter.value()
            zustand, abgelaufen, p, anzeige_bis = "laeuft", 0, 0.0, 0
            letzt = utime.ticks_ms()
            continue

        # Joystick
        if RECHTS.neu(jetzt):
            figur = (figur + 1) % len(FIGUREN)
            alle_neu(p)
        if LINKS.neu(jetzt):
            figur = (figur - 1) % len(FIGUREN)
            alle_neu(p)
        mehr, weniger = HOCH.neu(jetzt), RUNTER.neu(jetzt)
        if mehr or weniger:                         # Zeit geändert: alles beginnt von vorn
            minuten = min(MAX_MINUTEN, max(1, minuten + int(mehr) - int(weniger)))
            DAUER_S = minuten * 60
            zustand, abgelaufen = "laeuft", 0
            anzeige_bis = jetzt + ANZEIGE_MS
            alle_neu(0.0)
        if MITTE.neu(jetzt):
            if zustand == "fertig":                 # nach dem Ende: von vorn
                neustart(figur, zustand, p)
                zustand, abgelaufen, p = "laeuft", 0, 0.0
                letzt = utime.ticks_ms()
                continue
            zustand = "pause" if zustand == "laeuft" else "laeuft"

        # Zeit läuft (nicht in der Pause und nicht, solange die Dauer-Anzeige zu sehen ist).
        # dt ist die echte Zeit seit dem letzten Durchlauf, deshalb bleibt die Dauer exakt.
        anzeige = utime.ticks_diff(anzeige_bis, jetzt) > 0
        if zustand == "laeuft" and not anzeige:
            abgelaufen += dt
        p = min(1.0, abgelaufen / (minuten * 60000))

        # Zeit um: grüne Welle läuft über die Szene, danach bleibt sie grün und schimmert
        if zustand == "laeuft" and p >= 1.0:
            ende = FIGUREN[figur](1.0)
            wischen(ende, gruen(ende), True, (0, 60, 0), 110)
            zustand = "fertig"
            letzt = utime.ticks_ms()
            continue

        zeige(dauer_bild(minuten) if anzeige else frame(figur, zustand, p))
        utime.sleep_ms(max(1, FRAME_MS - utime.ticks_diff(utime.ticks_ms(), jetzt)))   # gleichmässige Bildrate

if __name__ == "__main__":
    main()
