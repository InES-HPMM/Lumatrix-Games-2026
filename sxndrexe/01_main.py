"""
Lumatrix Minesweeper

Beim Einschalten läuft ein Radar über das Feld, danach erklärt eine Legende
den Farbcode. Mitte drücken überspringt das.

Steuerung
  Joystick           Cursor bewegen (gedrückt halten = weiterlaufen)
  Mitte kurz         Feld aufdecken
  Mitte kurz auf     sind rundherum alle Minen markiert: übrige Nachbarn aufdecken,
    farbigem Feld    sonst blinken die Nachbarn kurz, die noch verdeckt sind
  Mitte lang         Flagge setzen oder entfernen
  Schiebeschalter    Spielfeld <-> Zeit und Fortschritt
  nach Spielende     Mitte drücken = neues Spiel

Farben
  verdeckt = schwach weiss, keine Mine daneben = aus,
  1 = blau, 2 = grün, 3 = gelb, 4 und mehr = violett, Flagge = rot

Als main.py auf dem Pico speichern, dann startet das Spiel beim Einschalten.
"""

import random
from math import atan2, pi

from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms, ticks_add, ticks_diff, ticks_ms, ticks_us

# ---------------------------------------------------------------- Einstellungen

SIZE = 8
CELLS = SIZE * SIZE
MINES = 10              # 8x8 mit 10 Minen war das Anfänger-Level im alten Windows-Minesweeper
BRIGHTNESS = 20         # Prozent. Tief halten, sonst überbelichtet die Handykamera.

LONG_PRESS_MS = 400     # so lange halten = Flagge statt Aufdecken
REPEAT_DELAY_MS = 300   # Joystick halten: erster Wiederholschritt nach ...
REPEAT_MS = 110         # ... und dann alle ...
DEBOUNCE_MS = 20        # so lange muss ein Taster stabil sein (gegen Prellen)
BLINK_MS = 300          # Cursor: so lange an, dann gleich lange aus
LOOP_MS = 10            # Pause pro Durchlauf der Hauptschleife
RIPPLE_MS = 45          # Pause zwischen zwei Wellen beim Aufdecken
EXPLOSION_MS = 55       # Pause zwischen zwei Bildern der Explosion
WIN_MS = 30             # Pause zwischen zwei Bildern des Regenbogens
FLASH_MS = 120          # Blinken der Nachbarn beim Klick auf eine Zahl
RADAR_STEPS = 24        # Bilder pro Radar-Umdrehung beim Start ...
RADAR_MS = 40           # ... und Pause zwischen zwei Bildern
LEGEND_MS = 900         # so lange steht jedes Bild der Farblegende

# --------------------------------------------------------------------- Zustände

PLAYING, WON, LOST = 0, 1, 2        # Spielstand
HIDDEN, OPEN, FLAGGED = 0, 1, 2     # Zustand eines Feldes
SHORT, LONG = 1, 2                  # Klick-Arten der Joystick-Mitte

# ----------------------------------------------------------------------- Farben


def rgb(r, g, b):
    """Farbe (0–255 pro Kanal) auf BRIGHTNESS herunterrechnen.

    Es wird aufgerundet, damit schwache Farben nicht ganz verschwinden.
    """
    return (
        (r * BRIGHTNESS + 99) // 100,
        (g * BRIGHTNESS + 99) // 100,
        (b * BRIGHTNESS + 99) // 100,
    )


OFF = (0, 0, 0)
HIDDEN_COLOR = rgb(50, 50, 50)
CURSOR_COLOR = rgb(255, 255, 255)
FLAG_COLOR = rgb(255, 0, 0)
MINE_COLOR = FLAG_COLOR                 # nach Spielende sehen alle Minen wie Flaggen aus
WRONG_FLAG_COLOR = rgb(255, 90, 0)      # Flagge ohne Mine darunter (nur nach Niederlage)
NUMBER_COLORS = (
    OFF,                # 0: keine Mine daneben
    rgb(0, 0, 255),     # 1: blau
    rgb(0, 255, 0),     # 2: grün
    rgb(255, 190, 0),   # 3: gelb
) + (rgb(190, 0, 255),) * 5             # 4 bis 8: violett
FIRE = (rgb(255, 255, 200), rgb(255, 170, 0), rgb(255, 50, 0), rgb(110, 0, 0))
STATUS_COLORS = (rgb(255, 255, 255), rgb(0, 255, 0), rgb(255, 0, 0))   # PLAYING, WON, LOST
PROGRESS_COLOR = rgb(0, 120, 255)
RADAR_COLOR = rgb(0, 255, 90)

# 3x5-Ziffern für die Zeitanzeige: 5 Zeilen von oben nach unten, je 3 Bit = 3 Spalten
DIGITS = (
    (0b111, 0b101, 0b101, 0b101, 0b111),
    (0b010, 0b110, 0b010, 0b010, 0b111),
    (0b111, 0b001, 0b111, 0b100, 0b111),
    (0b111, 0b001, 0b111, 0b001, 0b111),
    (0b101, 0b101, 0b111, 0b001, 0b001),
    (0b111, 0b100, 0b111, 0b001, 0b111),
    (0b111, 0b100, 0b111, 0b101, 0b111),
    (0b111, 0b001, 0b001, 0b001, 0b001),
    (0b111, 0b101, 0b111, 0b101, 0b111),
    (0b111, 0b101, 0b111, 0b001, 0b111),
)

# --------------------------------------------------------------------- Hardware

np = NeoPixel(Pin(19, Pin.OUT), CELLS)
switch = Pin(9, Pin.IN, Pin.PULL_UP)


class Button:
    """Ein Taster des Joysticks: entprellt, mit Auto-Repeat und langem Klick.

    Gedrückt zieht der Taster den Pin auf 0 (Pull-up). update() muss in jedem
    Durchlauf der Hauptschleife einmal aufgerufen werden.
    """

    def __init__(self, gpio):
        self._pin = Pin(gpio, Pin.IN, Pin.PULL_UP)
        now = ticks_ms()
        self.held = False       # entprellter Zustand
        self.pressed = False    # in diesem Durchlauf gedrückt worden
        self.released = False   # in diesem Durchlauf losgelassen worden
        self._since = now       # seit wann `held` gilt
        self._raw = False
        self._raw_since = now
        self._next_repeat = now
        self._armed = False     # Druck gesehen, Klick noch nicht gemeldet

    def update(self, now):
        raw = self._pin.value() == 0
        if raw != self._raw:    # Pin hat gewechselt: abwarten, ob er stabil bleibt
            self._raw = raw
            self._raw_since = now
        stable = ticks_diff(now, self._raw_since) >= DEBOUNCE_MS
        self.pressed = stable and raw and not self.held
        self.released = stable and self.held and not raw
        if self.pressed or self.released:
            self.held = raw
            self._since = now

    def held_ms(self, now):
        return ticks_diff(now, self._since) if self.held else 0

    def repeat(self, now):
        """True beim Drücken und danach im Takt, solange der Taster gehalten wird."""
        if self.pressed:
            self._next_repeat = ticks_add(now, REPEAT_DELAY_MS)
            return True
        if self.held and ticks_diff(now, self._next_repeat) >= 0:
            self._next_repeat = ticks_add(now, REPEAT_MS)
            return True
        return False

    def click(self, now):
        """LONG, sobald LONG_PRESS_MS erreicht sind, SHORT beim Loslassen, sonst None."""
        if self.pressed:
            self._armed = True
        if not self._armed:
            return None
        if self.held and self.held_ms(now) >= LONG_PRESS_MS:
            self._armed = False
            return LONG
        if self.released:
            self._armed = False
            return SHORT
        return None


up, down, left, right, center = Button(3), Button(6), Button(7), Button(2), Button(8)
JOYSTICK = (up, down, left, right, center)

# ------------------------------------------------------------------- Spiellogik


def neighbors_of(i):
    """Indizes der bis zu 8 Nachbarfelder von Feld i (Index = y * 8 + x, 0 = unten links)."""
    x, y = i % SIZE, i // SIZE
    return [ny * SIZE + nx
            for ny in range(y - 1, y + 2)
            for nx in range(x - 1, x + 2)
            if 0 <= nx < SIZE and 0 <= ny < SIZE and (nx, ny) != (x, y)]


NEIGHBORS = [neighbors_of(i) for i in range(CELLS)]    # einmal vorberechnet


class Board:
    """Ein Spielfeld: Minen, Zahlen, aufgedeckte Felder und Flaggen."""

    def __init__(self):
        self.mine = bytearray(CELLS)    # 1 = hier liegt eine Mine
        self.count = bytearray(CELLS)   # Anzahl Minen in den Nachbarfeldern
        self.state = bytearray(CELLS)   # HIDDEN, OPEN oder FLAGGED
        self.status = PLAYING
        self.opened = 0                 # aufgedeckte Felder ohne Mine
        self.exploded = None            # Feld der ausgelösten Mine
        self.started = None             # ticks_ms() beim ersten Aufdecken
        self.ended = None

    def elapsed_ms(self, now):
        if self.started is None:
            return 0
        return ticks_diff(now if self.ended is None else self.ended, self.started)

    def toggle_flag(self, i):
        if self.state[i] == HIDDEN:
            self.state[i] = FLAGGED
        elif self.state[i] == FLAGGED:
            self.state[i] = HIDDEN

    def can_chord(self, i):
        """Ist Feld i eine aufgedeckte Zahl mit genau so vielen Flaggen rundherum?"""
        if self.state[i] != OPEN or self.count[i] == 0:
            return False
        flags = sum(1 for n in NEIGHBORS[i] if self.state[n] == FLAGGED)
        return flags == self.count[i]

    def reveal(self, i):
        """Feld i aufdecken. Generator: liefert nach jeder Welle einmal None,
        damit die Anzeige das Aufdecken animieren kann.

        Ist Feld i schon eine aufgedeckte Zahl und stimmen die Flaggen rundherum,
        werden alle übrigen Nachbarn aufgedeckt ("Chording" wie im Original).
        """
        if self.status != PLAYING:
            return
        if self.can_chord(i):
            yield from self._open([n for n in NEIGHBORS[i] if self.state[n] == HIDDEN])
        elif self.state[i] == HIDDEN:
            if self.started is None:    # erster Klick: erst jetzt Minen legen
                self._place_mines(i)
                self.started = ticks_ms()
            yield from self._open([i])

    def _open(self, wave):
        """Die Felder in `wave` aufdecken (Generator wie reveal).

        Felder ohne Nachbarminen decken ihre Nachbarn automatisch mit auf.
        Das geschieht Welle für Welle (Breitensuche) statt rekursiv, weil
        MicroPython nur wenig Rekursionstiefe verträgt.
        """
        for i in wave:
            if self.mine[i]:            # falsche Flagge beim Chording oder Pech
                self.state[i] = OPEN
                self.exploded = i
                self._finish(LOST)
                return
        for i in wave:
            self.state[i] = OPEN
        while wave:
            self.opened += len(wave)
            yield
            next_wave = []
            for j in wave:
                if self.count[j] == 0:
                    for n in NEIGHBORS[j]:
                        if self.state[n] == HIDDEN:
                            self.state[n] = OPEN
                            next_wave.append(n)
            wave = next_wave
        if self.opened == CELLS - MINES:
            self._finish(WON)

    def _place_mines(self, safe):
        """Minen zufällig verteilen. Feld `safe` und seine Nachbarn bleiben frei,
        so öffnet der erste Klick immer eine ganze Fläche."""
        random.seed(ticks_us())     # Zeitpunkt des ersten Klicks: jedes Spiel ist anders
        free = [j for j in range(CELLS) if j != safe and j not in NEIGHBORS[safe]]
        for _ in range(MINES):
            self.mine[free.pop(random.randint(0, len(free) - 1))] = 1
        for j in range(CELLS):
            self.count[j] = sum(self.mine[n] for n in NEIGHBORS[j])

    def _finish(self, status):
        """Spiel beenden und alle Minen zeigen (bei Sieg als Flaggen)."""
        self.status = status
        self.ended = ticks_ms()
        for j in range(CELLS):
            if self.mine[j] and self.state[j] == HIDDEN:
                self.state[j] = FLAGGED if status == WON else OPEN

# ---------------------------------------------------------------------- Anzeige


def cell_color(board, i):
    state = board.state[i]
    if state == HIDDEN:
        return HIDDEN_COLOR
    if state == FLAGGED:
        if board.status == LOST and not board.mine[i]:
            return WRONG_FLAG_COLOR
        return FLAG_COLOR
    if board.mine[i]:
        return MINE_COLOR
    return NUMBER_COLORS[board.count[i]]


def paint(board):
    """Alle Felder in den LED-Puffer schreiben (sichtbar erst mit np.write())."""
    for i in range(CELLS):
        np[i] = cell_color(board, i)


def blink_on(ms):
    return ms // BLINK_MS % 2 == 0


def mix(a, b, t):
    """Zwischen Farbe a (t = 0) und Farbe b (t = 1) überblenden."""
    t = min(t, 1)
    return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def show_game(board, now, cursor, blink_from):
    paint(board)
    if board.status == PLAYING:
        if center.held and board.state[cursor] != OPEN:
            # Halten färbt den Cursor nach und nach rot: gleich kommt die Flagge
            np[cursor] = mix(CURSOR_COLOR, FLAG_COLOR, center.held_ms(now) / LONG_PRESS_MS)
        elif center.held or blink_on(ticks_diff(now, blink_from)):
            np[cursor] = CURSOR_COLOR
    elif board.status == LOST and blink_on(now):
        np[board.exploded] = CURSOR_COLOR   # die ausgelöste Mine blinkt
    np.write()


def flash_neighbors(board, i):
    """Zahl angeklickt, aber die Flaggen passen noch nicht: kurz zeigen,
    welche verdeckten Felder die Zahl meint."""
    hidden = [n for n in NEIGHBORS[i] if board.state[n] == HIDDEN]
    if not hidden:
        return
    for _ in range(2):
        for n in hidden:
            np[n] = CURSOR_COLOR
        np.write()
        sleep_ms(FLASH_MS)
        paint(board)
        np.write()
        sleep_ms(FLASH_MS)


def draw_digit(digit, x0, color):
    """3x5-Ziffer zeichnen: linke Spalte x0, oberste Zeile y = 6."""
    for row, bits in enumerate(DIGITS[digit]):
        for col in range(3):
            if (bits >> (2 - col)) & 1:
                np[(6 - row) * SIZE + x0 + col] = color


def show_stats(board, now):
    """Zweite Ansicht: Sekunden (Farbe = Spielstand), unten der Fortschritt als Balken."""
    for i in range(CELLS):
        np[i] = OFF
    seconds = min(board.elapsed_ms(now) // 1000, 99)
    color = STATUS_COLORS[board.status]
    draw_digit(seconds // 10, 0, color)
    draw_digit(seconds % 10, 5, color)
    for x in range(board.opened * SIZE // (CELLS - MINES)):
        np[x] = PROGRESS_COLOR
    np.write()


def animate_explosion(board, before):
    """Druckwelle ab der Mine: vor der Welle das alte Bild, dahinter alle Minen."""
    cx, cy = board.exploded % SIZE, board.exploded // SIZE
    dist = [int(((i % SIZE - cx) ** 2 + (i // SIZE - cy) ** 2) ** 0.5 + 0.5)
            for i in range(CELLS)]
    for t in range(max(dist) + len(FIRE)):
        for i in range(CELLS):
            age = t - dist[i]       # wie lange die Welle schon über Feld i hinweg ist
            if age < 0:
                np[i] = before[i]
            elif age < len(FIRE):
                np[i] = FIRE[age]
            else:
                np[i] = cell_color(board, i)
        np.write()
        sleep_ms(EXPLOSION_MS)


def rainbow(pos):
    """Farbrad: 0–255 ergibt rot -> grün -> blau -> rot."""
    pos &= 255
    if pos < 85:
        return rgb(255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return rgb(0, 255 - pos * 3, pos * 3)
    pos -= 170
    return rgb(pos * 3, 0, 255 - pos * 3)


def animate_win():
    """Diagonaler Regenbogen, der über das Feld läuft."""
    for t in range(48):
        for i in range(CELLS):
            np[i] = rainbow((i % SIZE + i // SIZE) * 16 + t * 12)
        np.write()
        sleep_ms(WIN_MS)

# ---------------------------------------------------------------- Startanimation


def pause(ms):
    """ms warten. True, sobald die Joystick-Mitte gedrückt wird (Intro überspringen)."""
    end = ticks_add(ticks_ms(), ms)
    while ticks_diff(end, ticks_ms()) > 0:
        center.update(ticks_ms())
        if center.pressed:
            return True
        sleep_ms(LOOP_MS)
    return False


def animate_radar():
    """Minensucher-Radar: Ein Strahl dreht zwei Runden im Uhrzeigersinn und zieht
    eine grüne Spur hinter sich her. Wo er eine Mine streift, glüht sie rot nach."""
    angle = [atan2(i // SIZE - 3.5, i % SIZE - 3.5) / (2 * pi) for i in range(CELLS)]
    echoes = {random.randrange(CELLS) for _ in range(MINES)}
    for step in range(2 * RADAR_STEPS):
        beam = -step / RADAR_STEPS
        for i in range(CELLS):
            behind = (angle[i] - beam) % 1      # Bruchteil einer Runde, seit der Strahl hier war
            if behind > step / RADAR_STEPS:     # noch gar nie überstrichen
                np[i] = OFF
            elif i in echoes:
                np[i] = mix(FLAG_COLOR, OFF, behind)
            else:
                np[i] = mix(RADAR_COLOR, OFF, behind * 3)
        np.write()
        if pause(RADAR_MS):
            return True
    return False


def animate_legend():
    """Farbcode erklären: links die Zahl, rechts ein Stück Spielfeld, in dem das
    mittlere Feld genau so viele Minen um sich hat. Mit jeder Zahl kommt eine dazu."""
    middle = 4 * SIZE + 6                                   # x = 6, y = 4
    corners = (SIZE - 1, 1 - SIZE, SIZE + 1, -SIZE - 1)     # Nachbarn diagonal, gut verteilt
    for n in range(1, 5):
        for i in range(CELLS):
            np[i] = OFF
        draw_digit(n, 0, NUMBER_COLORS[n])
        for i in NEIGHBORS[middle]:
            np[i] = HIDDEN_COLOR
        for offset in corners[:n]:
            np[middle + offset] = MINE_COLOR
        np[middle] = NUMBER_COLORS[n]
        np.write()
        if pause(LEGEND_MS):
            return True
    return False


def intro():
    """Beim Einschalten: erst das Radar, dann die Legende."""
    if not animate_radar():
        animate_legend()

# ---------------------------------------------------------------- Hauptschleife


def play_reveal(board, cursor):
    """Aufdecken mit Wellen-Animation, danach Explosion oder Regenbogen."""
    before = [cell_color(board, i) for i in range(CELLS)]   # Bild vor dem Klick
    for _ in board.reveal(cursor):
        paint(board)
        np.write()
        sleep_ms(RIPPLE_MS)
    if board.status == LOST:
        animate_explosion(board, before)
    elif board.status == WON:
        animate_win()


def main():
    board = Board()
    cursor = 3 * SIZE + 3           # Start bei x = 3, y = 3
    game_side = switch.value()      # Schalterstellung beim Einschalten = Spielfeld
    intro()
    blink_from = ticks_ms()

    while True:
        now = ticks_ms()
        for button in JOYSTICK:
            button.update(now)

        if switch.value() != game_side:
            show_stats(board, now)
        else:
            click = center.click(now)
            if board.status == PLAYING:
                # Während die Mitte gedrückt ist, nicht bewegen: sonst landet
                # die Flagge bei leicht schrägem Drücken im falschen Feld.
                if not center.held:
                    x, y = cursor % SIZE, cursor // SIZE
                    if left.repeat(now):
                        x = max(x - 1, 0)
                    if right.repeat(now):
                        x = min(x + 1, SIZE - 1)
                    if down.repeat(now):
                        y = max(y - 1, 0)
                    if up.repeat(now):
                        y = min(y + 1, SIZE - 1)
                    if y * SIZE + x != cursor:
                        cursor = y * SIZE + x
                        blink_from = now        # nach einer Bewegung sofort sichtbar
                if click == SHORT:
                    if board.state[cursor] == OPEN and not board.can_chord(cursor):
                        flash_neighbors(board, cursor)
                    else:
                        play_reveal(board, cursor)
                elif click == LONG:
                    board.toggle_flag(cursor)
            elif click:
                board = Board()                 # Spiel vorbei: Klick startet neu
            show_game(board, ticks_ms(), cursor, blink_from)

        sleep_ms(LOOP_MS)


main()
