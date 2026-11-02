'''
LumaEcho ist ein Zeitschleifen-Puzzle fuer die Lumatrix: Nach jedem Durchlauf wird dein Weg als
Echo gespeichert und laeuft im naechsten Durchlauf mit. Gemeinsam mit deinen frueheren Ichs
haeltst du Keys und Schalter gedrueckt, oeffnest Tore und erreichst den Ausgang.

Anleitung
  Joystick           Held bewegen: ein Druck = ein Schritt, gedrueckt halten = weiterlaufen
  Joystick druecken  Durchlauf sofort beenden und als Echo speichern (nach 8 s geschieht das
                     von selbst); 1 Sekunde gedrueckt halten = Level neu starten
  Ausgang            Dunkelrot = zu, gruen = offen. Er oeffnet sich, wenn alle Keys (gelb)
                     gehalten werden. Du kannst nicht gleichzeitig auf dem Key und im Ausgang
                     stehen, dafuer sind deine Echos da.
  Tore               Orange Tore sind offen, solange ihr Schalter gehalten wird.
  Echos              Hoechstens 3. Danach ist der naechste Durchlauf der letzte.
  Farben             weiss = du, rosa = Echos, oben = Zeitleiste (1 Pixel = 1 Sekunde)
'''

from machine import Pin
from neopixel import NeoPixel
import utime

# ---------- Einstellungen (hier kannst du alles leicht aendern) ----------
TICK_MS      = 200    # Dauer eines Spielschritts (kleiner = schneller)
LOOP_SECONDS = 8      # Dauer eines Durchlaufs (Zeitleiste: 8 Pixel = 1 Pixel pro Sekunde)
LOOP_TICKS   = LOOP_SECONDS * 1000 // TICK_MS
MAX_GHOSTS   = 3      # Mehr Echos gibt es nicht
HOLD_MS      = 1000   # Mitteltaste so lange halten = Level neu starten
REPEAT_MS    = 350    # Richtung so lange halten = Held laeuft von selbst weiter
LOCK_MS      = 800    # So lange nach einem Bildwechsel (Titel, Pokal) ignoriert das Spiel Tasten
BLINK_MS     = 150    # Blinktempo des offenen Ausgangs
DANCE_MS     = 110    # Titelbild: Zeit pro Schritt der tanzenden Figuren
FRAME_MS     = 30     # Pause pro Schleifendurchgang
ROWS         = 7      # Hoehe des Spielfelds, darueber liegt die Zeitleiste
BRIGHTNESS   = 100    # Gesamthelligkeit in Prozent (bei weissen Blitzen testweise 50)

# Animationen (Millisekunden)
SPIRAL_MS     = 5    # Gruene Spirale am Ausgang: Zeit pro Schritt (ein Schritt = ein Pixel)
SPIRAL_TAIL   = 20    # Gruene Spirale: Laenge des leuchtenden Schweifs (Pixel)
RESET_MS      = 300   # Roter Blitz beim Neustart
REWIND_MS     = 25    # Zeitruecklauf: Zeit pro Bild
LEVEL_FADE_MS = 45    # Level-Zahl: Zeit pro Einblend-Stufe
LEVEL_HOLD_MS = 700   # Level-Zahl: So lange bleibt sie stehen
BOB_MS        = 400   # Titel-Geist: Zeit pro Schwebe-Schritt
FEET_MS       = 300   # Titel-Geist: Zeit pro Fuss-Wackler

# Farben (0-255, bis etwa 60 reicht)
BLACK       = (0, 0, 0)
WALL        = (8, 8, 30)       # Wand: dunkelblau
PLAYER      = (60, 60, 60)     # Held: weiss
GHOST       = (60, 25, 40)     # Echos: hellpink
PLATE       = (40, 32, 0)      # Platte: gelb
SWITCH      = (35, 20, 0)      # Schalter: gelborange
GATE        = (60, 20, 0)      # Tor zu: orange (alle Tore gleich)
GATE_OPEN   = (12, 4, 0)       # Tor offen: dunkles Orange
EXIT_CLOSED = (30, 0, 0)       # Ausgang zu: dunkelrot
EXIT_OPEN   = (0, 60, 20)      # Ausgang offen: gruen, blinkt
TIMER       = (14, 14, 14)     # Zeitleiste oben (dunkelgrau, damit der Held heller ist)
TIMER_LOW   = (55, 0, 0)       # Zeitleiste fast leer
FAIL        = (30, 0, 0)       # Neustart-Blitz
EYE         = (50, 50, 55)     # Augen des Titel-Geists
GOLD        = (60, 48, 0)      # Pokal (pulsiert zwischen 2/3 und voller Helligkeit)
SHINE       = (60, 60, 30)     # Lichtreflex auf dem Pokal
CONFETTI    = (10, 10, 25)     # Funkeln im Hintergrund des Pokals
NUMBER      = (0, 55, 25)      # Level-Zahl
LEVEL_NOW   = (35, 35, 35)     # Level-Punkte unten: aktuelles Level
LEVEL_DONE  = (0, 30, 10)      # Level-Punkte unten: geschafft
LEVEL_TODO  = (6, 6, 12)       # Level-Punkte unten: noch offen

# Level: 7 Zeilen (oben zuerst), darueber liegt die Zeitleiste. Nur die erste Zeile ist Wand.
# # Wand   P Platte/Key (alle noetig fuer den Ausgang)   S Start   E Ausgang   . Boden
# K Schalter oeffnet Tor G   L Schalter oeffnet Tor H   (Level 1-4 nutzen nur K und G)
LEVELS = (
    (   # 1: Der Key liegt links, der Ausgang am Ende des Ganges rechts
        "########",
        ".#.###..",
        "P#....#.",
        ".#.###..",
        ".#.S....",
        ".#.#.##.",
        "...#.##E",
    ),
    (   # 2: Der Schalter liegt links, das Tor rechts
        "########",
        "...#.#..",
        ".#...#..",
        ".##.S#.#",
        ".###.G.#",
        "K..#.#.E",
        ".##..#.#",
    ),
    (   # 3: Schalter links, hinter dem Tor liegt der Key
        "########",
        ".#...#.E",
        "K###.G.#",
        ".#.S.#.#",
        ".#.#.#..",
        ".#.###.P",
        "...###..",
    ),
    (   # 4: Zwei Keys und ein Tor: erst links, dann hinter dem Tor
        "########",
        ".K...#.#",
        ".#####P.",
        ".#.###..",
        ".#..S#..",
        "P#.#.G.#",
        ".....#.E",
    ),
    (   # 5: Jedes Tor hat seinen eigenen Schalter, der Key liegt dazwischen
        "########",
        "....#..E",
        "K#.##..#",
        ".#.###H#",
        ".#.S#..P",
        ".##.G.##",
        ".#..#..L",
    ),
)

# 3x5-Schrift fuer die Level-Zahl (Zeile 0 = oben, bis Level 9)
FONT = {
    "1": (".X.", "XX.", ".X.", ".X.", "XXX"),
    "2": ("XXX", "..X", "XXX", "X..", "XXX"),
    "3": ("XXX", "..X", "XXX", "..X", "XXX"),
    "4": ("X.X", "X.X", "XXX", "..X", "..X"),
    "5": ("XXX", "X..", "XXX", "..X", "XXX"),
    "6": ("XXX", "X..", "XXX", "X.X", "XXX"),
    "7": ("XXX", "..X", "..X", "..X", "..X"),
    "8": ("XXX", "X.X", "XXX", "X.X", "XXX"),
    "9": ("XXX", "X.X", "XXX", "..X", "XXX"),
}

# Kleiner Geist fuer das Titelbild (X = Koerper, W = Auge), Zeile 0 = oben; Fuesse wackeln extra
GHOST_ART = (".XX.", "XWWX", "XXXX")

# Pokal fuer den Endbildschirm (x, y)
TROPHY_PIXELS = {
    (2, 7), (3, 7), (4, 7), (5, 7),
    (0, 6), (2, 6), (3, 6), (4, 6), (5, 6), (7, 6),
    (0, 5), (2, 5), (3, 5), (4, 5), (5, 5), (7, 5),
    (2, 4), (3, 4), (4, 4), (5, 4),
    (3, 3), (4, 3),
    (3, 2), (4, 2),
    (2, 1), (3, 1), (4, 1), (5, 1),
    (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),
}

# Kreis um den Rand fuer das Titelbild
RING = ([(x, 0) for x in range(8)] + [(7, y) for y in range(1, 8)] +
        [(x, 7) for x in range(6, -1, -1)] + [(0, y) for y in range(6, 0, -1)])

# ---------- Hardware (Lumatrix Standard) ----------
np = NeoPixel(Pin(19, Pin.OUT), 64)

btn_right  = Pin(2, Pin.IN, Pin.PULL_UP)
btn_up     = Pin(3, Pin.IN, Pin.PULL_UP)
btn_down   = Pin(6, Pin.IN, Pin.PULL_UP)
btn_left   = Pin(7, Pin.IN, Pin.PULL_UP)
btn_center = Pin(8, Pin.IN, Pin.PULL_UP)

BUTTONS = (btn_right, btn_up, btn_down, btn_left, btn_center)
MOVES = ((btn_up, 0, 1), (btn_down, 0, -1), (btn_left, -1, 0), (btn_right, 1, 0))


def put(pos, color):
    '''Setzt den Pixel pos = (x, y) im Puffer auf die Farbe.'''
    np[pos[1] * 8 + pos[0]] = color


def fill(color):
    '''Faerbt den ganzen Puffer in einer Farbe.'''
    for i in range(64):
        np[i] = color


def dim(color, num, den):
    '''Gibt die Farbe mit der Helligkeit num/den zurueck.'''
    return tuple(c * num // den for c in color)


def show():
    '''Schreibt den Puffer auf die LEDs (bei BRIGHTNESS < 100 vorher abgedunkelt).
    Jedes Bild wird vor dem Aufruf neu gezeichnet, der Puffer wird hier veraendert.'''
    if BRIGHTNESS < 100:
        for i in range(64):
            np[i] = dim(np[i], BRIGHTNESS, 100)
    np.write()


def flash(color, ms):
    '''Zeigt die ganze Matrix ms Millisekunden lang in einer Farbe.'''
    fill(color)
    show()
    utime.sleep_ms(ms)


def pressed():
    '''Gibt True zurueck, wenn eine Joystick-Richtung oder der Druckknopf aktiv ist.'''
    return any(b.value() == 0 for b in BUTTONS)


def wait_release(max_ms=1000):
    '''Wartet hoechstens max_ms Millisekunden, bis der Joystick losgelassen wurde.'''
    t = utime.ticks_ms()
    while pressed() and utime.ticks_diff(utime.ticks_ms(), t) < max_ms:
        utime.sleep_ms(10)


def draw_digit(digit, color):
    '''Zeichnet eine Ziffer (3x5-Schrift) in die Mitte des Spielfelds.'''
    rows = FONT[str(digit)]
    for r in range(5):
        for c in range(3):
            if rows[r][c] == "X":
                put((2 + c, 6 - r), color)


def spiral_order(center):
    '''Gibt alle 64 Felder in Spiralreihenfolge zurueck, beginnend bei center.'''
    x, y = center
    dx, dy, steps = 1, 0, 1
    cells = []
    while len(cells) < 64:
        for _ in range(2):                       # jede Seitenlaenge kommt zweimal vor
            for _ in range(steps):
                if 0 <= x < 8 and 0 <= y < 8:
                    cells.append((x, y))
                x, y = x + dx, y + dy
            dx, dy = -dy, dx                     # Richtung um 90 Grad drehen
        steps += 1
    return cells


def show_spiral(center):
    '''Zeigt eine gruene Spirale, die vom Feld center nach aussen die Matrix durchlaeuft.'''
    cells = spiral_order(center)
    start = utime.ticks_ms()
    for head in range(len(cells) + SPIRAL_TAIL):
        fill(BLACK)
        for age in range(SPIRAL_TAIL):           # Kopf ist am hellsten, der Schweif wird dunkler
            i = head - age
            if 0 <= i < len(cells):
                put(cells[i], dim(EXIT_OPEN, SPIRAL_TAIL - age, SPIRAL_TAIL))
        show()
        wait = (head + 1) * SPIRAL_MS - utime.ticks_diff(utime.ticks_ms(), start)
        if wait > 0:                             # feste Zeit pro Schritt
            utime.sleep_ms(wait)


def pos_at(path, t):
    '''Gibt die Position eines Echos zum Schritt t zurueck (nach dem Ende bleibt es stehen).'''
    return path[min(t, len(path) - 1)]


class LumaEcho:
    '''Das Spiel: Zustand, Eingabe und Darstellung.'''

    def __init__(self):
        '''Startet auf dem Titelbild.'''
        self.level = 0
        self.ghosts = []                 # Echos: je eine Liste von Positionen pro Schritt
        self.rec = []                    # Aufzeichnung des aktuellen Durchlaufs
        self.walls, self.plates = set(), []
        self.gates, self.switches = {}, {}   # Feld -> Paar (0 = K/G, 1 = L/H)
        self.start = self.exit = (0, 0)
        self.x = self.y = self.t = 0
        self.want = (0, 0)               # gemerkte Richtung bis zum naechsten Schritt
        self.held = (0, 0)               # Richtung, die gerade gehalten wird
        self.held_since = 0
        self.last_tick = 0
        self.hold_start = None           # Beginn des Mitteltasten-Drucks
        self.hold_done = False
        self.state = "TITLE"             # TITLE -> PLAY -> TROPHY
        self.state_since = utime.ticks_ms()

    def set_state(self, state):
        '''Wechselt den Zustand und merkt sich den Zeitpunkt.'''
        self.state = state
        self.state_since = utime.ticks_ms()

    def load_level(self):
        '''Liest das Level-Raster ein (erste Zeile = oben).'''
        self.walls, self.plates = set(), []
        self.gates, self.switches = {}, {}
        for row, line in enumerate(LEVELS[self.level]):
            for x, ch in enumerate(line):
                pos = (x, ROWS - 1 - row)
                if ch == "#":
                    self.walls.add(pos)
                elif ch in "GH":
                    self.gates[pos] = "GH".index(ch)
                elif ch == "P":
                    self.plates.append(pos)
                elif ch in "KL":
                    self.switches[pos] = "KL".index(ch)
                elif ch == "S":
                    self.start = pos
                elif ch == "E":
                    self.exit = pos

    def start_level(self):
        '''Laedt das Level, zeigt den Fortschritt und beginnt den ersten Durchlauf.'''
        self.load_level()
        self.ghosts = []
        self.show_level()
        self.new_loop()
        self.set_state("PLAY")

    def draw_progress(self, scale):
        '''Zeichnet in der untersten Reihe einen Punkt pro Level
        (gruen = geschafft, weiss = aktuelles Level), Helligkeit scale/8.'''
        n = len(LEVELS)
        for i in range(n):
            col = LEVEL_DONE if i < self.level else (LEVEL_NOW if i == self.level else LEVEL_TODO)
            put(((8 - n) // 2 + i, 0), dim(col, scale, 8))

    def show_level(self):
        '''Blendet die Level-Zahl mit dem Fortschritt ein und laesst sie kurz stehen.'''
        for b in range(1, 9):
            fill(BLACK)
            draw_digit(self.level + 1, dim(NUMBER, b, 8))
            self.draw_progress(b)
            show()
            utime.sleep_ms(LEVEL_FADE_MS)
        utime.sleep_ms(LEVEL_HOLD_MS)

    def new_loop(self):
        '''Setzt den Helden an den Start und beginnt einen neuen Durchlauf.'''
        self.x, self.y = self.start
        self.rec = [self.start]
        self.t = 0
        self.want = (0, 0)
        self.last_tick = utime.ticks_ms()

    def occupied(self, t, pos):
        '''Gibt alle Felder zurueck, auf denen zum Schritt t jemand steht (Echos und Held).'''
        return [pos_at(g, t) for g in self.ghosts] + [pos]

    def gate_open(self, pair, spots):
        '''Gibt True zurueck, wenn alle Schalter des Paares pair gehalten werden.'''
        return all(p in spots for p, g in self.switches.items() if g == pair)

    def exit_open(self, spots):
        '''Gibt True zurueck, wenn alle Keys (Platten) gehalten werden (Ausgang offen).'''
        return all(p in spots for p in self.plates)

    def blocked(self, pos):
        '''Gibt True zurueck, wenn der Held pos nicht betreten darf
        (Rand, Wand, Tor zu oder Ausgang zu).'''
        if not (0 <= pos[0] < 8 and 0 <= pos[1] < ROWS) or pos in self.walls:
            return True
        spots = self.occupied(self.t, pos)
        if pos in self.gates:
            return not self.gate_open(self.gates[pos], spots)
        if pos == self.exit:
            return not self.exit_open(spots)
        return False

    def step(self):
        '''Ein Spielschritt: Held bewegen, Weg aufzeichnen, Ausgang und Zeit pruefen.'''
        self.t += 1
        new = (self.x + self.want[0], self.y + self.want[1])
        self.want = (0, 0)
        if new != (self.x, self.y) and not self.blocked(new):
            self.x, self.y = new
        self.rec.append((self.x, self.y))
        if (self.x, self.y) == self.exit:
            self.level_complete()
        elif self.t >= LOOP_TICKS:
            self.next_loop()

    def next_loop(self):
        '''Speichert den Durchlauf als Echo und startet den naechsten
        (zu viele Echos = Neustart).'''
        if len(self.ghosts) >= MAX_GHOSTS:
            self.restart_level()
            return
        self.rewind()
        self.ghosts.append(self.rec)
        self.new_loop()

    def rewind(self):
        '''Spielt den letzten Durchlauf rueckwaerts ab (Zeitruecklauf-Effekt).'''
        for t in range(len(self.rec) - 1, -1, -2):
            self.draw(t, self.rec[t])
            show()
            utime.sleep_ms(REWIND_MS)

    def restart_level(self):
        '''Loescht alle Echos und startet das Level neu.'''
        flash(FAIL, RESET_MS)
        self.ghosts = []
        self.new_loop()

    def level_complete(self):
        '''Ausgang erreicht: gruene Spirale vom Ausgang aus, dann naechstes Level oder Pokal.'''
        show_spiral(self.exit)
        self.level += 1
        if self.level < len(LEVELS):
            self.start_level()
        else:
            wait_release()
            self.set_state("TROPHY")

    def read_direction(self, now):
        '''Ein neuer Druck loest genau einen Schritt aus, Halten (ab REPEAT_MS) laeuft weiter.'''
        direction = (0, 0)
        for btn, dx, dy in MOVES:
            if btn.value() == 0:
                direction = (dx, dy)
        if direction != self.held:
            self.held, self.held_since = direction, now
            if direction != (0, 0):
                self.want = direction
        elif direction != (0, 0) and utime.ticks_diff(now, self.held_since) >= REPEAT_MS:
            self.want = direction

    def read_center(self, now):
        '''Mitteltaste: kurz gedrueckt = Durchlauf beenden, lange gehalten = Level neu starten.'''
        if btn_center.value() == 0:
            if self.hold_start is None:
                self.hold_start = now
            elif not self.hold_done and utime.ticks_diff(now, self.hold_start) >= HOLD_MS:
                self.hold_done = True
                self.restart_level()
        else:
            short = self.hold_start is not None and not self.hold_done and self.t > 0
            self.hold_start, self.hold_done = None, False
            if short:
                self.next_loop()

    def update(self):
        '''Verteilt die Arbeit je nach Zustand.'''
        now = utime.ticks_ms()
        if self.state == "PLAY":
            self.update_play(now)
        else:
            self.update_menu(now)

    def update_play(self, now):
        '''Liest den Joystick und fuehrt im Takt TICK_MS einen Spielschritt aus.'''
        self.read_direction(now)
        self.read_center(now)
        if utime.ticks_diff(now, self.last_tick) >= TICK_MS:
            self.last_tick = now
            self.step()

    def update_menu(self, now):
        '''Titelbild und Pokal: Ein Druck startet das Spiel bzw. fuehrt zurueck zum Titelbild.'''
        if utime.ticks_diff(now, self.state_since) > LOCK_MS and pressed():
            wait_release()
            if self.state == "TITLE":
                self.level = 0
                self.start_level()
            else:
                self.set_state("TITLE")

    def draw_timer(self, t):
        '''Zeichnet die Zeitleiste in der obersten Reihe (1 Pixel = 1 Sekunde).'''
        lit = ((LOOP_TICKS - t) * 8 + LOOP_TICKS - 1) // LOOP_TICKS
        for x in range(lit):
            put((x, ROWS), TIMER_LOW if lit <= 2 else TIMER)

    def exit_color(self, is_open):
        '''Gibt die Farbe des Ausgangs zurueck (zu = dunkelrot, offen = gruen blinkend).'''
        if not is_open:
            return EXIT_CLOSED
        return EXIT_OPEN if (utime.ticks_ms() // BLINK_MS) % 2 else dim(EXIT_OPEN, 1, 4)

    def draw(self, t, pos):
        '''Zeichnet die Szene zum Schritt t mit dem Helden an pos.'''
        spots = self.occupied(t, pos)
        fill(BLACK)
        for w in self.walls:
            put(w, WALL)
        for cell, pair in self.gates.items():
            put(cell, GATE_OPEN if self.gate_open(pair, spots) else GATE)
        for cell in self.switches:
            put(cell, SWITCH)
        for p in self.plates:
            put(p, PLATE)
        put(self.exit, self.exit_color(self.exit_open(spots)))
        for g in self.ghosts:
            put(pos_at(g, t), GHOST)
        put(pos, PLAYER)
        self.draw_timer(t)

    def title(self):
        '''Titelbild: Held und zwei Echos tanzen im Kreis, in der Mitte schwebt ein Geist.'''
        fill(BLACK)
        ms = utime.ticks_ms()
        for k in (2, 1, 0):
            put(RING[(ms // DANCE_MS - 6 * k) % len(RING)], PLAYER if k == 0 else GHOST)
        bob = (0, 1, 0, -1)[ms // BOB_MS % 4]                  # Geist schwebt auf und ab
        feet = ("X..X", ".XX.")[ms // FEET_MS % 2]              # Fuesse wackeln
        for r, line in enumerate(GHOST_ART + (feet,)):
            for c, ch in enumerate(line):
                if ch != ".":
                    put((2 + c, 5 + bob - r), EYE if ch == "W" else GHOST)

    def trophy(self):
        '''Pokal: glaenzendes Gold mit wanderndem Lichtreflex und Konfetti im Hintergrund.'''
        f = (utime.ticks_ms() // FRAME_MS) % 20
        glow = dim(GOLD, 20 + (f if f < 10 else 20 - f), 30)
        for y in range(8):
            for x in range(8):
                if (x, y) in TROPHY_PIXELS:
                    put((x, y), SHINE if (x + y) % 6 == f // 3 else glow)
                else:
                    put((x, y), CONFETTI if (x * 3 + y * 7 + f) % 8 == 0 else BLACK)

    def render(self):
        '''Zeichnet das Bild passend zum Zustand.'''
        if self.state == "PLAY":
            self.draw(self.t, (self.x, self.y))
        elif self.state == "TITLE":
            self.title()
        else:
            self.trophy()
        show()


game = LumaEcho()

while True:
    game.update()
    game.render()
    utime.sleep_ms(FRAME_MS)
