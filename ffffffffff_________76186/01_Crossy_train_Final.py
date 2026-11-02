# ============================================
#   CROSSY TRAIN  -  Lumatrix Games 2026
# ============================================
#
# Ziel: so viele Gleise wie moeglich ueberqueren, ohne vom Zug erwischt
# zu werden.
#
# - Du bist der gelbe Punkt.
# - Dunkel = frei, gruen = Baum (da kommst du nicht durch),
#   braun = Gleis.
# - Blinken am Ende von einem Gleis zwei rote Lichter -> gleich kommt
#   ein Zug!
# - Rote Zuege = Schnellzug (schnell und lang)
#   Blaue Zuege = Regionalzug (langsamer und kuerzer)
#   Alle haben vorne einen weissen Kopf.
# - Alle 22 Reihen kommt ein Bahnhof (graue Perrons). Dort halten die
#   blauen Zuege an, die Tueren blinken gelb und dann fahren sie weiter.
#   Ein Zug der steht ist wie eine Wand, ein Zug der faehrt ist toedlich.
# - Der Bildschirm faehrt von selbst nach oben, also nicht zu lange warten!
#
# Punkte: 1 pro neue Reihe, 5 extra fuer jeden Bahnhof.
#
# Steuerung:
#   Joystick            -> ein Schritt hoch / runter / links / rechts
#   Joystick druecken   -> Start, nochmal spielen, Pause im Spiel
#   nach Game Over: Mitte = nochmal, Joystick bewegen = Level wechseln
#
# Am Anfang waehlst du das Level (Gesicht in der Mitte):
#   gruen und froh = leicht, orange = mittel, rot und hungrig = schwer
#
# Jedes Level hat seinen eigenen Rekord. Nach dem Neustart (oder neu
# programmieren) faengt er wieder bei 0 an.

# NOTIZ fuer mich: machine und neopixel gibts nur auf der Lumatrix (MicroPython),
# auf dem PC laeuft das nicht. hab ich am Anfang nicht gecheckt
from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms
from random import getrandbits

# Helligkeit in Prozent (zum Filmen hab ich manchmal 50 genommen)
BRIGHTNESS = 100

# 64 LEDs an Pin 19. np[0] ist unten links, nicht oben!! (hab lange gesucht)
np = NeoPixel(Pin(19, Pin.OUT), 64)

# Joystick: hoch, runter, links, rechts, druecken
BUTTONS = [Pin(3, Pin.IN, Pin.PULL_UP),
           Pin(6, Pin.IN, Pin.PULL_UP),
           Pin(7, Pin.IN, Pin.PULL_UP),
           Pin(2, Pin.IN, Pin.PULL_UP),
           Pin(8, Pin.IN, Pin.PULL_UP)]
# PULL_UP heisst: normal ist der Pin 1 und wenn man drueckt 0.
# deswegen steht weiter unten == 0 (fand ich zuerst voll verwirrend)
UP = 0
DOWN = 1
LEFT = 2
RIGHT = 3
PRESS = 4


def lit(r, g, b):
    # macht aus einer Farbe die Farbe mit der richtigen Helligkeit
    # // = Division ohne Komma (ganze Zahl), hab ich nachgeschaut
    r2 = min(255, r * BRIGHTNESS // 100)
    g2 = min(255, g * BRIGHTNESS // 100)
    b2 = min(255, b * BRIGHTNESS // 100)
    # wenn die Farbe sonst ganz aus waere: wenigstens 1 lassen,
    # sonst sieht man sie bei wenig Helligkeit gar nicht mehr
    if (r or g or b) and r2 == 0 and g2 == 0 and b2 == 0:
        if r >= g and r >= b:
            r2 = 1
        elif g >= b:
            g2 = 1
        else:
            b2 = 1
    return (r2, g2, b2)


# ======== Farben ========
# (hier kann man alles umfaerben)
# wiso zwei mal das gleiche? -> frueher war das ein Schachbrett mit 2 Gruentoenen,
# jetzt sind einfach beide aus
GRASS = ((0, 0, 0), (0, 0, 0))             # freier Boden = dunkel
TREE = lit(0, 14, 2)                       # Baum
TRACK = (lit(12, 6, 1), lit(9, 4, 1))      # Gleis, zwei Brauntoene
WARNING = lit(70, 0, 0)                    # rote Lichter vor dem Zug
LIGHTS = lit(65, 65, 75)                   # weisser Kopf vom Zug
RED_TRAIN = lit(55, 0, 2)
BLUE_TRAIN = lit(2, 8, 50)
DOORS = lit(50, 30, 0)                     # Tueren blinken
PLATFORM = (lit(18, 18, 20), lit(15, 15, 17))   # graue Perrons
PLAYER = lit(70, 50, 0)                    # das bin ich :)
BOOM = lit(70, 22, 0)                      # Explosion
HIT = lit(70, 0, 0)
SCORE = lit(0, 55, 0)
BEST = lit(0, 18, 50)
GOLD = lit(60, 40, 0)
LEVEL_COLOURS = (lit(0, 45, 0), lit(60, 25, 0), lit(60, 0, 0))   # gruen, orange, rot


# ======== Einstellungen ========
FRAME_MS = 40       # 40ms pro Bild = 25 Bilder pro Sekunde
AHEAD = 32          # so viele Reihen werden schon ueber dem Bildschirm gebaut
                    # (sonst kann man einfach hoch spammen, hab ich getestet...)
MAX_RAILS = 2       # max. 2 Gleise direkt nebeneinander

# Baeume beim Start (T = Baum), die unterste Reihe zuerst
SPAWN_TREES = ("TT....TT",
               "T......T",
               ".T....T.")

# Bahnhof: alle 22 Reihen, ab Reihe 15 kommt das hier
# P = Perron, T = Gleis
BLOCK = 22
STATION = 15
STATION_PLAN = "PTTPTTP"

# was fuer eine Reihe es ist
MEADOW = 0
RAIL = 1
PLATFORM_ROW = 2

# die Zuege: (Farbe, Tempo, Laenge)
# Tempo ist in 1/16 Pixel pro Bild, sonst waeren die langsamen Zuege zu schnell
# 1/16 Pixel?? -> ah: pos wird spaeter durch 16 geteilt, so kann ein Zug auch
# weniger als 1 Pixel pro Bild fahren und ruckelt nicht
EXPRESS = (RED_TRAIN, 10, 11)     # schnell und lang
REGIONAL = (BLUE_TRAIN, 4, 8)     # langsamer, haelt am Bahnhof

# was der Zug gerade macht
ARRIVE = 0   # faehrt in den Bahnhof ein (bremst)
STAND = 1    # steht
LEAVE = 2    # Tueren blinken, gleich gehts los
GO = 3       # faehrt

# Die Levels:
#   screen  = wie schnell der Bildschirm am Anfang hochfaehrt
#   faster  = wie viel schneller er mit den Punkten noch wird
#   speed   = so viel schneller ist jeder Zug
#   pause   = Bilder (mindestens) zwischen zwei Zuegen auf dem gleichen Gleis
#   warning = wie lange die roten Lichter blinken (25 = 1 Sekunde)
LEVELS = (
    # screen faster speed pause warning
    (4, 10, 0, 45, 35),   # leicht
    (5, 14, 0, 30, 27),   # mittel
    (7, 18, 2, 15, 20),   # schwer
)
# level faengt bei 0 an! also 0 = leicht, 1 = mittel, 2 = schwer
level = 1
SCREEN, FASTER, SPEED, PAUSE, WARN_FRAMES = LEVELS[level]
# (die Zeile oben setzt 5 Variabeln auf einmal, heisst tuple auspacken)

# Zahlen 0-9, je 3x5 Pixel (1 = an)
DIGITS = ("111101101101111", "010110010010111", "111001111100111",
          "111001111001111", "101101111001001", "111100111001111",
          "111100111101111", "111001001001001", "111101111101111",
          "111101111001111")


def set_level(n):
    # global brauchts, sonst macht python eine neue Variabel nur in der Funktion
    # und die draussen bleibt gleich
    global level, SCREEN, FASTER, SPEED, PAUSE, WARN_FRAMES
    level = n
    SCREEN = LEVELS[n][0]
    FASTER = LEVELS[n][1]
    SPEED = LEVELS[n][2]
    PAUSE = LEVELS[n][3]
    WARN_FRAMES = LEVELS[n][4]


# ======== eine Reihe der Welt ========
# Eine Reihe ist entweder Wiese, Perron oder Gleis.
# Auf einem Gleis faehrt max. 1 Zug.

class Row:

    # __init__ wird automatisch aufgerufen wenn man Row() macht
    # self = die Reihe selber
    def __init__(self):
        self.kind = MEADOW
        self.trees = [False] * 8   # wo Baeume sind
        self.last = False          # letztes Perron vom Bahnhof? (fuer den Bonus)
        self.run = 0               # wie viele Gleise schon nebeneinander
        self.pos = None            # None = kein Zug da

    def make_rail(self, r, station, run):
        self.kind = RAIL
        self.station = station
        self.run = run
        # von links oder von rechts?
        # getrandbits(1) gibt 0 oder 1, also wie Muenze werfen
        # getrandbits(2) = 0 bis 3, getrandbits(3) = 0 bis 7 usw.
        if getrandbits(1):
            self.dir = 1
        else:
            self.dir = -1

        if station:
            # im Bahnhof immer ein blauer Regionalzug, der langsam reinkommt
            self.colour = REGIONAL[0]
            self.length = REGIONAL[2]
            self.speed = 3
        else:
            # je weiter oben, desto mehr Schnellzuege
            # getrandbits(8) = 0 bis 255. am Anfang ist die Grenze 64 -> ca. 25% Schnellzuege,
            # ab Reihe 60 ist sie 144 -> ca. 56% (hab ich ausgerechnet)
            if getrandbits(8) < 64 + min(r, 60) * 4 // 3:
                zug = EXPRESS
            else:
                zug = REGIONAL
            self.colour = zug[0]
            self.speed = zug[1]
            self.length = zug[2]
            # jeder Zug ein bisschen anders + schneller weiter oben und im schwereren Level
            self.speed = self.speed + getrandbits(2) + min(r // 30, 2) + SPEED

        self.timer = getrandbits(6)   # wie lange bis die Lichter blinken
        self.warn = 0

    def head(self):
        # wo der Kopf vom Zug ist (in Pixel)
        # +8 damit es richtig rundet (8 ist die Haelfte von 16)
        return (self.pos + 8) // 16

    def car(self, x):
        # 0 = Kopf, 1, 2, 3... = Wagen dahinter, -1 = da ist nichts
        if self.kind != RAIL or self.pos == None:
            return -1
        # mal self.dir weil der Zug auch von rechts kommen kann, dann ist alles umgedreht
        hinten = (self.head() - x) * self.dir
        if hinten >= 0 and hinten < self.length:
            return hinten
        return -1

    def moving(self):
        if self.pos == None:
            return False
        return self.phase == ARRIVE or self.phase == GO

    def blocked(self, x):
        # Baeume und stehende Zuege kann man nicht betreten
        if self.trees[x]:
            return True
        if self.car(x) >= 0 and not self.moving():
            return True
        return False

    def update(self):
        if self.kind != RAIL:
            return

        # --- kein Zug: warten, dann blinken, dann kommt er ---
        if self.pos == None:
            if self.warn > 0:
                self.warn = self.warn - 1
                if self.warn == 0:
                    # jetzt kommt der Zug!
                    if self.dir > 0:
                        self.pos = -16
                    else:
                        self.pos = 128
                    self.v = self.speed
                    if self.station:
                        self.phase = ARRIVE
                    else:
                        self.phase = GO
                    # wo er im Bahnhof anhaelt
                    stop = 1 + getrandbits(1) + getrandbits(1)
                    if self.dir > 0:
                        self.stop = 7 - stop
                    else:
                        self.stop = stop
            else:
                self.timer = self.timer - 1
                if self.timer <= 0:
                    self.warn = WARN_FRAMES
            return

        # --- Zug ist da ---
        # phase sagt was der Zug grad macht, siehe oben (ARRIVE, STAND, LEAVE, GO)
        if self.phase == ARRIVE:
            # bremsen kurz vor dem Halt
            rest = (self.stop * 16 - self.pos) * self.dir
            # je naeher am Halt desto langsamer, aber nie unter 1 sonst bleibt er stecken
            self.v = max(1, min(self.speed, rest // 12))
            if rest <= self.v:
                self.pos = self.stop * 16
                self.phase = STAND
                self.wait = 50 + getrandbits(6)
            else:
                self.pos = self.pos + self.dir * self.v

        elif self.phase == STAND:
            self.wait = self.wait - 1
            if self.wait <= 0:
                self.phase = LEAVE
                self.wait = 22

        elif self.phase == LEAVE:
            # Tueren blinken...
            self.wait = self.wait - 1
            if self.wait <= 0:
                self.phase = GO
                self.v = 1

        else:
            # der Regionalzug wird langsam schneller
            if self.station:
                self.wait = self.wait + 1
                if self.wait % 3 == 0 and self.v < 9:
                    self.v = self.v + 1
            self.pos = self.pos + self.dir * self.v
            # ist das Ende vom Zug raus? dann weg damit
            ende = self.head() - (self.length - 1) * self.dir
            if self.dir > 0 and ende > 7:
                self.pos = None
                self.timer = PAUSE + getrandbits(6)
            if self.dir < 0 and ende < 0:
                self.pos = None
                self.timer = PAUSE + getrandbits(6)

    def draw(self, r, y, frame):
        # % = Rest beim Teilen. frame // 4 % 2 wechselt alle 4 Bilder zwischen 0 und 1
        # -> so blinkt es. eigendlich einfach wenn mans mal verstanden hat
        blink = frame // 4 % 2 == 0
        for x in range(8):
            if self.kind == MEADOW:
                if self.trees[x]:
                    c = TREE
                else:
                    c = GRASS[(x + r) % 2]
            elif self.kind == PLATFORM_ROW:
                c = PLATFORM[(x + r) % 2]
            else:
                c = TRACK[x % 2]
                i = self.car(x)
                if self.pos == None and self.warn > 0:
                    # zwei rote Lichter blinken abwechselnd, wie beim Bahnuebergang
                    if self.dir > 0:
                        anfang = 0
                    else:
                        anfang = 7
                    if x == anfang + self.dir * (frame // 5 % 2):
                        c = WARNING
                elif i == 0:
                    c = LIGHTS          # Kopf
                elif i > 0:
                    if self.phase == LEAVE and blink:
                        c = DOORS
                    else:
                        c = self.colour
            np[y * 8 + x] = c


def make_row(r, prev):
    row = Row()

    # ganz unten: kleiner Park mit Baeumen, die Mitte bleibt frei
    if r < 3:
        for x in range(8):
            if SPAWN_TREES[r][x] == "T":
                row.trees[x] = True
        return row

    # Bahnhof?
    # m = wo wir im 22er Block sind (0 bis 21)
    m = r % BLOCK
    if m >= STATION:
        if STATION_PLAN[m - STATION] == "T":
            row.make_rail(r, True, 0)
        else:
            row.kind = PLATFORM_ROW
            if m == STATION + len(STATION_PLAN) - 1:
                row.last = True
        return row

    # sonst: Gleis (ca. 58%) oder Wiese
    zu_viele = prev.kind == RAIL and prev.run >= MAX_RAILS
    if not zu_viele and getrandbits(8) < 148:
        if prev.kind == RAIL and not prev.station:
            run = prev.run + 1
        else:
            run = 1
        row.make_rail(r, False, run)
    else:
        # 0 bis 3 Baeume
        for i in range(getrandbits(2)):
            row.trees[getrandbits(3)] = True
    return row


# ======== Knoepfe ========
held = [False, False, False, False, False]


def pressed(button):
    # True nur in dem Moment wo der Knopf runtergeht (nicht beim Halten)
    down = BUTTONS[button].value() == 0
    # held merkt sich ob der Knopf schon vorher unten war.
    # ohne das wuerde man beim gedrueckt halten 25 Schritte pro Sekunde machen lol
    neu = down and not held[button]
    held[button] = down
    return neu


def any_pressed():
    # alle Knoepfe abfragen (nicht beim ersten aufhoeren, sonst merkt
    # man die anderen erst spaeter)
    irgendwas = False
    for b in range(5):
        if pressed(b):
            irgendwas = True
    return irgendwas


def boom(x, y):
    # Explosion: oranger Ring wird groesser, ich blinke rot
    vorher = []
    for i in range(64):
        vorher.append(np[i])
    for step in range(1, 12):
        for i in range(64):
            # i % 8 = x vom LED, i // 8 = y vom LED
            # ** 2 = hoch 2, also Pythagoras ohne Wurzel (braucht man nicht, man vergleicht ja nur)
            d = (i % 8 - x) ** 2 + (i // 8 - y) ** 2
            if (step - 2) ** 2 < d <= step ** 2:
                np[i] = BOOM
            else:
                np[i] = vorher[i]
        if y >= 0 and y < 8:
            if step % 2 == 1:
                np[y * 8 + x] = HIT
            else:
                np[y * 8 + x] = PLAYER
        np.write()
        sleep_ms(70)
    sleep_ms(300)


# ======== das Spiel ========
# gibt am Schluss die Punkte zurueck

def play():
    # {} ist ein dictionary: rows[17] = Reihe Nummer 17. naehmlich praktisch weil
    # man unten Reihen loeschen kann ohne dass sich die Nummern verschieben
    rows = {}
    top = 0          # naechste Reihe die noch nicht gebaut ist
    x = 3
    y = 1            # y = Reihe in der Welt, nicht auf dem Bildschirm!
    best = 1         # hoechste Reihe bis jetzt
    bonus = 0
    cam = 0          # unterer Rand vom Bildschirm (in 1/1000 Reihen)
    frame = 0
    flash = 0
    started = False

    while True:
        frame = frame + 1
        score = best - 1 + bonus

        # Bildschirm faehrt hoch (erst wenn ich mich bewegt habe)
        if started:
            cam = cam + SCREEN + min(FASTER, score // 3)
        # cam ist in tausendstel, damit der Bildschirm auch gaaanz langsam fahren kann
        # (gleicher Trick wie bei den Zuegen mit 1/16)
        base = cam // 1000
        # wenn ich zu weit oben bin, faehrt er mit
        if y - base > 3:
            base = y - 3
            cam = base * 1000

        # neue Reihen bauen (schon AHEAD Reihen im Voraus)
        # rows.get(top - 1) gibt die Reihe darunter, oder None wenn es sie nicht gibt
        while top < base + 8 + AHEAD:
            rows[top] = make_row(top, rows.get(top - 1))
            top = top + 1
        # alte Reihen unten loeschen, sonst geht der Speicher aus
        alte = []
        for r in rows:
            if r < base - 1:
                alte.append(r)
        for r in alte:
            del rows[r]

        # --- bewegen ---
        nx = x
        ny = y
        links = pressed(LEFT)
        rechts = pressed(RIGHT)
        hoch = pressed(UP)
        runter = pressed(DOWN)
        if links:
            nx = nx - 1
        if rechts:
            nx = nx + 1
        if hoch:
            ny = ny + 1
        if runter:
            ny = ny - 1

        if (nx, ny) != (x, y) and nx >= 0 and nx < 8 and ny >= base:
            if not rows[ny].blocked(nx):
                x = nx
                y = ny
                started = True
                if y > best:
                    best = y
                    # durch den Bahnhof durch -> Bonus!
                    if rows[y].last:
                        bonus = bonus + 5
                        flash = 6

        # alle Zuege bewegen
        # auch die Reihen ueber dem Bildschirm! sonst stehen dort die Zuege still
        for r in range(base, top):
            rows[r].update()

        # zeichnen
        for screen_y in range(8):
            rows[base + screen_y].draw(base + screen_y, screen_y, frame)

        # erwischt? (vom Zug oder vom Bildschirm)
        if y < base:
            boom(x, y - base)
            return best - 1 + bonus
        if rows[y].car(x) >= 0 and rows[y].moving():
            boom(x, y - base)
            return best - 1 + bonus

        # y - base = wo ich auf dem Bildschirm bin (0 = unten)
        np[(y - base) * 8 + x] = PLAYER

        # nach dem Bahnhof: alles kurz heller
        if flash > 0:
            flash = flash - 1
            for i in range(64):
                r, g, b = np[i]
                np[i] = (min(255, r + 12), min(255, g + 12), min(255, b + 12))

        # Mitte druecken = Pause
        if pressed(PRESS):
            pause()

        # erst bei write() gehen die LEDs wirklich an!! vorher ist alles nur im Speicher
        np.write()
        sleep_ms(FRAME_MS)


def pause():
    # alles dunkler und zwei weisse Striche | |
    vorher = []
    for i in range(64):
        vorher.append(np[i])
    for i in range(64):
        r, g, b = vorher[i]
        np[i] = (r // 4, g // 4, b // 4)
    for y in range(2, 6):
        np[y * 8 + 2] = LIGHTS
        np[y * 8 + 5] = LIGHTS
    np.write()
    # warten bis man nochmal drueckt
    while not pressed(PRESS):
        # die anderen Richtungen machen in der Pause nichts
        # muss man trotzdem abfragen, sonst macht man nach der Pause ploetzlich
        # einen Schritt wenn man waehrend der Pause rumgedrueckt hat
        pressed(UP)
        pressed(DOWN)
        pressed(LEFT)
        pressed(RIGHT)
        sleep_ms(20)
    # Bild wieder wie vorher
    for i in range(64):
        np[i] = vorher[i]


# ======== Punkte und Rekord ========
# Rekord fuer jedes Level (leicht, mittel, schwer).
# Ist nur im Speicher -> beim Neustart wieder 0
# records[0] = leicht, records[1] = mittel, records[2] = schwer
records = [0, 0, 0]


def draw_digit(digit, color, left):
    # eine grosse Zahl, 3 Pixel breit
    for i in range(15):
        if DIGITS[digit][i] == "1":
            np[(6 - i // 3) * 8 + left + i % 3] = color


def show_number(number, color, line=None):
    np.fill((0, 0, 0))
    if number > 99:
        number = 99   # mehr passt nicht drauf
    # number // 10 = Zehner, number % 10 = Einer. z.B. 26 -> 2 und 6
    draw_digit(number // 10, color, 1)
    draw_digit(number % 10, color, 5)
    if line:
        for x in range(1, 7):
            np[x] = line
    np.write()


def wait(ms):
    # warten, aber sofort aufhoeren wenn man was drueckt
    # gibt zurueck: "mitte", "richtung" oder None (nichts gedrueckt)
    for i in range(ms // 20):
        sleep_ms(20)
        if pressed(PRESS):
            return "mitte"
        richtung = False
        for b in (UP, DOWN, LEFT, RIGHT):
            if pressed(b):
                richtung = True
        if richtung:
            return "richtung"
    return None


def game_over(score):
    # Mitte druecken    -> "mitte"    = gleiches Level nochmal
    # Joystick bewegen  -> "richtung" = anderes Level waehlen
    # nichts (ca. 10 s) -> None       = zurueck zum Titel
    # (das sagt dem Hauptprogramm unten was als naechstes kommt)

    # alle Knoepfe einmal abfragen, damit ein Druck von vorher
    # (waehrend der Explosion) nicht zaehlt
    any_pressed()

    record = records[level]
    if score > record:
        # neuer Rekord!! blinkt gold
        records[level] = score
        for blink in range(6):
            if blink % 2 == 0:
                show_number(score, GOLD, GOLD)
            else:
                show_number(score, SCORE, GOLD)
            antwort = wait(300)
            if antwort:
                return antwort
        record = score
    for i in range(4):
        show_number(score, SCORE)
        antwort = wait(1500)
        if antwort:
            return antwort
        show_number(record, BEST, BEST)   # Rekord hat einen Strich unten
        antwort = wait(1000)
        if antwort:
            return antwort
    return None


# ======== Level waehlen ========
# 6x6 Gesichter (# = an), von oben nach unten

# TODO vileicht noch ein 4. Level? (mega schwer)
FACES = (
    (".####.",     # leicht: froh
     "#.##.#",
     "######",
     "#.##.#",
     "##..##",
     ".####."),
    (".####.",     # mittel: normal
     "#.##.#",
     "######",
     "######",
     "##..##",
     ".####."),
    (".####.",     # schwer: hungrig, boese Augen, Mund weit offen
     "#.##.#",     # (geht bis in die unterste Reihe)
     "##..##",
     "######",
     "##..##",
     "#....#",
     ".#..#."),
)


# diese Funtkion bleibt so lange drin bis man in der Mitte drueckt
def choose_level():
    n = level
    frame = 0
    while True:
        frame = frame + 1
        # links/runter = leichter, rechts/hoch = schwerer
        if pressed(LEFT) or pressed(DOWN):
            if n > 0:
                n = n - 1
        if pressed(RIGHT) or pressed(UP):
            if n < 2:
                n = n + 1
        if pressed(PRESS):
            set_level(n)
            return

        # fill = alle LEDs auf einmal (hier alle aus)
        np.fill((0, 0, 0))
        # Gesicht in der Mitte
        gesicht = FACES[n]
        for row in range(len(gesicht)):
            for x in range(6):
                if gesicht[row][x] == "#":
                    np[(6 - row) * 8 + x + 1] = LEVEL_COLOURS[n]
        # Pfeile links/rechts blinken, in der Farbe vom Level daneben
        if frame // 10 % 2 == 0:
            if n > 0:
                np[3 * 8] = LEVEL_COLOURS[n - 1]
                np[4 * 8] = LEVEL_COLOURS[n - 1]
            if n < 2:
                np[3 * 8 + 7] = LEVEL_COLOURS[n + 1]
                np[4 * 8 + 7] = LEVEL_COLOURS[n + 1]
        np.write()
        sleep_ms(40)


# ======== Titel ========
# Buchstaben 3x5 wie die Zahlen
FONT = {"L": "100100100100111", "U": "101101101101111",
        "M": "101111111101101", "A": "010101111101101",
        "T": "111010010010010", "R": "110101110101101",
        "I": "111010010010111", "X": "101101010101101",
        "G": "111100101101111", "E": "111100111100111",
        "S": "111100111001111", "C": "111100100100111",
        "O": "111101101101111", "Y": "101101010010010",
        "N": "110101101101101", " ": "000000000000000"}

# der Zug hinter dem Text (r = rot, y = weisser Kopf, w = Fenster, o = Raeder)
TRAIN_ART = (
    ".rrrrrrrrrrrrrrr",
    "ywrrwwrwwrwwrwwr",
    "yrrrrrrrrrrrrrrr",
    "yrrrrrrrrrrrrrrr",
    ".o..o..o..o..o..",
)


def make_banner(text):
    # Text in grossen Buchstaben + Zug dahinter
    lines = ["", "", "", "", ""]
    for letter in text:
        if letter >= "0" and letter <= "9":
            form = DIGITS[int(letter)]
        else:
            form = FONT[letter]
        for line in range(5):
            # [a:b] schneidet ein Stueck aus dem Text raus, hier 3 Zeichen = eine Zeile vom Buchstaben
            stueck = form[line * 3:line * 3 + 3]
            stueck = stueck.replace("1", "#").replace("0", ".")
            lines[line] = lines[line] + stueck + "."
    for line in range(5):
        lines[line] = lines[line] + "....." + TRAIN_ART[line]
    return lines


BANNER = make_banner("LMG26 CROSSY TRAIN")
INTRO_RAIL = (lit(16, 16, 18), lit(10, 10, 12))   # graues Gleis unter dem Titel
PAINT = {"#": GOLD, "r": RED_TRAIN, "w": lit(3, 6, 12), "y": LIGHTS,
         "o": lit(12, 12, 12)}


def intro():
    # Titel einmal durchscrollen. True wenn jemand was drueckt
    # start faengt bei -8 an, damit der Text von rechts reinkommt und nicht einfach schon da ist
    for start in range(-8, len(BANNER[0])):
        for i in range(64):
            np[i] = GRASS[(i + i // 8) % 2]
        for x in range(8):
            np[8 + x] = INTRO_RAIL[(start + x) % 2]
            if start + x >= 0 and start + x < len(BANNER[0]):
                for line in range(5):
                    punkt = BANNER[line][start + x]
                    if punkt != ".":
                        np[(6 - line) * 8 + x] = PAINT[punkt]
        np.write()
        if any_pressed():
            return True
        sleep_ms(70)
    return False


# ======== los gehts ========
while True:
    # Titel laeuft immer wieder, bis jemand den Joystick beruehrt
    # pass = mach garnichts. die Schleife wartet einfach bis intro() True gibt
    while not intro():
        pass
    choose_level()
    while True:
        antwort = game_over(play())
        if antwort == "mitte":
            pass               # gleiches Level nochmal
        elif antwort == "richtung":
            choose_level()     # Level wechseln, dann weiter spielen
        else:
            break              # niemand da -> zurueck zum Titel