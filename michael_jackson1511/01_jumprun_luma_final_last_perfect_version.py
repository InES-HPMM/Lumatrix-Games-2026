# Jump'n'Run fuer die ZHAW Luma Matrix (8x8 WS2812) mit Raspberry Pi Pico
# MicroPython - laeuft direkt in Thonny
#   Interpreter: "MicroPython (Raspberry Pi Pico)"  (unten rechts in Thonny)
#
# Ziel: 25 Pixel hoch klettern und den goldenen Coin einsammeln.
# Der Coin setzt das ganze Spiel zurueck (neue Runde, neue Hindernisse, neuer Coin).
# Die Welt ist hoeher als das Display - das Bild scrollt mit dem Spieler.
# Gesetzte gruene Bloecke verschwinden nach 10 Sekunden (jeder Block ab seinem
# Setzen). Ab der Haelfte (5 s) blinken sie, und zwar immer schneller. Wer danach (oder
# sonst wie) wieder auf den Boden faellt, muss von vorn anfangen.
# Unterwegs liegen weisse Hindernis-Balken (2-3 Felder lang). Sie sind fest und
# koennen nicht entfernt werden: man muss daran vorbeibauen. Der erste Balken
# liegt immer ueber deiner Startspalte. Von oben kann man auf ihnen stehen.
#
# Steuerung (Joystick auf der Rueckseite der Luma Matrix):
#   links / rechts ... laufen (gedrueckt halten = weiterlaufen)
#   hoch ............. springen
#   Mitte druecken ... gruenen Block setzen (Standard: UNTER den Spieler)
#   runter ........... Neustart (alle Bloecke loeschen)
#
# Tipp zum Hochbauen: springen, in der Luft Mitte druecken, auf dem Block landen.
# Ist der Coin ausserhalb des Bildes, blinkt oben am Rand ein schwacher goldener
# Punkt in seiner Spalte.

from machine import Pin
import neopixel
import random
import time

# ------------------------------------------------------------ Pins (Luma Matrix)
# GPIO-Nummern laut ZHAW-Shield-Definition in Zephyr (zhaw_lumamatrix.overlay)
PIN_LEDS = 19
PIN_RIGHT = 2
PIN_UP = 3
PIN_DOWN = 6
PIN_LEFT = 7
PIN_CENTER = 8
# (Dip-Schalter waere GPIO 9 - wird hier nicht gebraucht)

# ------------------------------------------------------------ Einstellungen
W = 8                 # Display-Breite
H = 8                 # Display-Hoehe
GOAL_HEIGHT = 25      # so viele Pixel ueber dem Startpunkt liegt der Coin
WORLD_H = GOAL_HEIGHT + 3         # Welt-Hoehe (Boden + Startfeld + Luft ueber dem Coin)
FLOOR_Y = WORLD_H - 1             # unterste Reihe der Welt = Boden
COIN_Y = FLOOR_Y - 1 - GOAL_HEIGHT  # Reihe des Coins (ganz oben, 1 Reihe Luft darueber)

OBSTACLE_EVERY = 4    # alle 4 Reihen ein Hindernis-Balken
OBSTACLE_MIN_LEN = 2  # Balkenlaenge: 2 bis 3 Felder
OBSTACLE_MAX_LEN = 3

BLOCK_LIFE_MS = 10000   # gesetzte Bloecke verschwinden nach 10 Sekunden
BLINK_START_MS = BLOCK_LIFE_MS // 2  # ab der Haelfte (5 s) fangen sie an zu blinken ...
BLINK_SLOW_HZ = 1.5     # ... zuerst langsam (Blinken pro Sekunde)
BLINK_FAST_HZ = 8.0     # ... und kurz vor dem Verschwinden ganz schnell
RESET_ON_FALL = True    # zurueck auf den Boden gefallen = neu anfangen

TICK_MS = 130         # Dauer eines Spielschritts
DRAW_MS = 30          # Bild alle 30 ms neu zeichnen (damit schnelles Blinken sichtbar ist)
DEBOUNCE_MS = 30      # Entprellzeit der Tasten
JUMP_HEIGHT = 3       # Sprunghoehe in Pixeln
MOVE_EVERY = 2        # gedrueckt gehalten: alle 2 Schritte ein Feld weiter
JUMP_BUFFER = 2       # Sprung-Tastendruck bleibt so viele Schritte "gemerkt"
PLACE_MODE = "unten"  # "unten" = Block unter dem Spieler, "vorne" = vor dem Spieler
FLIP_Y = True         # Bild oben/unten drehen (True = Boden unten auf deiner Luma Matrix)
FLIP_X = False        # Bild links/rechts spiegeln (nur aendern, falls links und rechts vertauscht sind)

# Farben (bewusst gedimmt: 64 LEDs bei voller Helligkeit ziehen viel Strom)
BLACK = (0, 0, 0)
RED = (60, 0, 0)      # Spieler
GREEN = (0, 60, 0)    # Bloecke
FLOOR = (0, 0, 10)    # Boden (dunkelblau)
OBSTACLE = (30, 30, 30)  # Hindernisse (weiss)
GOLD = (70, 45, 0)    # Coin (hell)
GOLD_DIM = (25, 15, 0)  # Coin (funkelt zwischen hell und schwach) / Hinweis-Punkt
CELEBRATE = (40, 25, 0)  # Blinken beim Einsammeln
FALL_FLASH = (40, 0, 0)  # Blinken beim Herunterfallen

LEFT, RIGHT, UP, CENTER, DOWN = 0, 1, 2, 3, 4
PINS = [Pin(n, Pin.IN, Pin.PULL_UP)           # Tasten ziehen den Pin gegen GND
        for n in (PIN_LEFT, PIN_RIGHT, PIN_UP, PIN_CENTER, PIN_DOWN)]
np = neopixel.NeoPixel(Pin(PIN_LEDS), W * H)


# ------------------------------------------------------------ Tasten
class Buttons:
    """Entprellt alle Joystick-Richtungen und merkt sich kurze Tipper."""

    def __init__(self):
        n = len(PINS)
        self.state = [False] * n    # entprellter Zustand (True = gedrueckt)
        self.raw = [False] * n      # letzter Rohwert
        self.t = [0] * n            # Zeitpunkt der letzten Rohwert-Aenderung
        self.tap = [False] * n      # neuer Tastendruck seit dem letzten Schritt
        self.rep = 0                # Zaehler fuer Dauerlauf

    def poll(self, now):
        for i in range(len(PINS)):
            r = PINS[i].value() == 0
            if r != self.raw[i]:
                self.raw[i] = r
                self.t[i] = now
            if r != self.state[i] and time.ticks_diff(now, self.t[i]) >= DEBOUNCE_MS:
                self.state[i] = r
                if r:
                    self.tap[i] = True

    def clear(self):
        """Gemerkte Tastendruecke verwerfen."""
        for i in range(len(PINS)):
            self.tap[i] = False
        self.rep = 0

    def consume(self):
        """Eingabe fuer einen Spielschritt: (move, jump, place, reset)."""
        tapdir = (1 if self.tap[RIGHT] else 0) - (1 if self.tap[LEFT] else 0)
        held = (1 if self.state[RIGHT] else 0) - (1 if self.state[LEFT] else 0)
        move = 0
        if tapdir != 0:                     # neuer Druck: sofort ein Feld
            move = tapdir
            self.rep = MOVE_EVERY
        elif held != 0:                     # gehalten: im Takt weiterlaufen
            self.rep -= 1
            if self.rep <= 0:
                move = held
                self.rep = MOVE_EVERY
        else:
            self.rep = 0
        jump = self.tap[UP]
        place = self.tap[CENTER]
        reset = self.tap[DOWN]
        for i in range(len(PINS)):
            self.tap[i] = False
        return move, jump, place, reset


# ------------------------------------------------------------ Spiel
class Game:
    """Welt WORLD_H x W (0 = leer, 1 = gesetzter Block, 2 = Hindernis),
    Spieler x/y in Weltkoordinaten
    (y = 0 ganz oben), vertikale Geschwindigkeit vy, Blickrichtung facing,
    Kamera cam (oberste sichtbare Weltreihe), der Coin (cx, COIN_Y) und die
    Setz-Zeitpunkte der gruenen Bloecke (blocks). now = aktuelle Zeit in ms."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.grid = [[0] * W for _ in range(WORLD_H)]
        self.x = 1
        self.y = FLOOR_Y - 1    # steht auf dem Boden
        self.vy = 0             # -1 steigt, 0 steht/schwebt, +1 faellt
        self.rise = 0           # noch verbleibende Aufwaertsschritte
        self.facing = 1
        self.jump_buf = 0       # gemerkter Sprung-Wunsch
        self.cx = random.randint(0, W - 1)   # Coin: zufaellige Spalte, ganz oben
        self.won = False        # True, sobald der Coin eingesammelt wurde
        self.fell = False       # True, wenn man nach dem Klettern auf den Boden faellt
        self.climbed = False    # True, sobald man auf einem Block/Balken gestanden hat
        self.blocks = {}        # (y, x) -> Zeitpunkt (ms), an dem der Block gesetzt wurde
        self.now = 0
        self.anim = 0           # Zaehler fuer das Funkeln
        self.make_obstacles()
        self.cam = 0
        self.follow()

    def make_obstacles(self):
        # Balken (2-3 Felder) alle OBSTACLE_EVERY Reihen, bis kurz unter den Coin.
        # Der unterste Balken liegt ueber der Startspalte des Spielers.
        y = FLOOR_Y - 1 - OBSTACLE_EVERY
        first = True
        while y >= COIN_Y + 3:
            n = random.randint(OBSTACLE_MIN_LEN, OBSTACLE_MAX_LEN)
            if first:
                lo = max(0, self.x - n + 1)
                hi = min(self.x, W - n)
                a = random.randint(lo, hi)
            else:
                a = random.randint(0, W - n)
            for i in range(n):
                self.grid[y][a + i] = 2
            first = False
            y -= OBSTACLE_EVERY

    def solid(self, x, y):
        # fest = Spielfeldrand, Decke, Boden oder gruener Block
        if x < 0 or x >= W or y < 0 or y >= FLOOR_Y:
            return True
        return self.grid[y][x] != 0

    def on_ground(self):
        return self.solid(self.x, self.y + 1)

    def place_block(self):
        if PLACE_MODE == "vorne":
            tx = self.x + self.facing
            ty = self.y
        else:                               # "unten"
            tx = self.x
            ty = self.y + 1
        if tx < 0 or tx >= W or ty < 0 or ty >= FLOOR_Y:
            return                          # ausserhalb der Welt / auf dem Boden
        if self.grid[ty][tx] or (tx == self.x and ty == self.y):
            return                          # belegt oder Spieler steht dort
        if tx == self.cx and ty == COIN_Y:
            return                          # den Coin nicht zubauen
        self.grid[ty][tx] = 1
        self.blocks[(ty, tx)] = self.now

    def expire_blocks(self):
        # Bloecke, die laenger als BLOCK_LIFE_MS stehen, verschwinden
        old = []
        for k in self.blocks:
            if time.ticks_diff(self.now, self.blocks[k]) >= BLOCK_LIFE_MS:
                old.append(k)
        for k in old:
            self.grid[k[0]][k[1]] = 0
            del self.blocks[k]

    def block_visible(self, y, x):
        # Ab BLINK_START_MS blinken Bloecke, die Blinkfrequenz steigt bis zum Ende
        age = time.ticks_diff(self.now, self.blocks.get((y, x), self.now))
        if age < BLINK_START_MS:
            return True
        ts = (age - BLINK_START_MS) / 1000
        span = (BLOCK_LIFE_MS - BLINK_START_MS) / 1000
        phase = BLINK_SLOW_HZ * ts + (BLINK_FAST_HZ - BLINK_SLOW_HZ) * ts * ts / (2 * span)
        return (phase - int(phase)) < 0.5

    def check_coin(self):
        if self.x == self.cx and self.y == COIN_Y:
            self.won = True

    def follow(self):
        # Kamera folgt dem Spieler: er bleibt in den Bildreihen 2..5
        sy = self.y - self.cam
        if sy < 2:
            self.cam = self.y - 2
        elif sy > H - 3:
            self.cam = self.y - (H - 3)
        if self.cam < 0:
            self.cam = 0
        if self.cam > WORLD_H - H:
            self.cam = WORLD_H - H

    def step(self, move, jump, place):
        self.anim += 1
        self.expire_blocks()                     # abgelaufene Bloecke entfernen

        # 1) horizontal bewegen (Blickrichtung auch bei Kollision aktualisieren)
        if move != 0:
            self.facing = move
            if not self.solid(self.x + move, self.y):
                self.x += move
                self.check_coin()

        # 2) Block setzen
        if place:
            self.place_block()

        # 3) Springen: nur vom Boden oder von einem Block aus.
        #    Ein kurz vor der Landung gedrueckter Sprung wird gemerkt.
        if jump:
            self.jump_buf = JUMP_BUFFER
        if self.jump_buf > 0:
            if self.on_ground() and self.rise == 0:
                self.rise = JUMP_HEIGHT
                self.jump_buf = 0
            else:
                self.jump_buf -= 1

        # 4) vertikale Geschwindigkeit: steigen -> kurz schweben -> fallen
        if self.rise > 0:
            self.vy = -1
        elif self.vy < 0:
            self.vy = 0
        else:
            self.vy = 1

        # 5) vertikale Kollision
        if self.vy < 0:
            if self.solid(self.x, self.y - 1):   # Kopf stoesst an -> faellt
                self.vy = 0
                self.rise = 0
            else:
                self.y -= 1
                self.rise -= 1
        elif self.vy > 0:
            if self.solid(self.x, self.y + 1):   # gelandet
                self.vy = 0
            else:
                self.y += 1

        self.check_coin()

        # 6) Fall-Regel: wer auf einem Block/Balken stand und wieder auf dem
        #    Boden landet, hat verloren
        if self.on_ground():
            if self.y < FLOOR_Y - 1:
                self.climbed = True
            elif self.climbed and RESET_ON_FALL:
                self.fell = True
        self.follow()

    def draw(self):
        # Display-Zeile sy zeigt Weltreihe cam + sy. Die LED-Reihen der Luma Matrix
        # laufen von unten nach oben, deshalb wird mit FLIP_Y umgerechnet.
        bright = (self.anim // 3) % 2 == 0      # Coin funkelt
        hint = COIN_Y < self.cam                # Coin liegt ueber dem Bild
        for sy in range(H):
            wy = self.cam + sy
            row = (H - 1 - sy) if FLIP_Y else sy
            for x in range(W):
                col = (W - 1 - x) if FLIP_X else x
                if x == self.x and wy == self.y:
                    c = RED                      # Spieler zuerst = oben drauf
                elif x == self.cx and wy == COIN_Y:
                    c = GOLD if bright else GOLD_DIM
                elif wy == FLOOR_Y:
                    c = FLOOR
                elif self.grid[wy][x] == 2:
                    c = OBSTACLE
                elif self.grid[wy][x]:
                    c = GREEN if self.block_visible(wy, x) else BLACK
                elif hint and sy == 0 and x == self.cx and bright:
                    c = GOLD_DIM                 # Hinweis: Coin ist weiter oben
                else:
                    c = BLACK
                np[row * W + col] = c
        np.write()


def flash(color, times):
    """Ganzes Display blinkt: golden beim Coin, rot beim Herunterfallen."""
    for _ in range(times):
        for i in range(W * H):
            np[i] = color
        np.write()
        time.sleep_ms(180)
        for i in range(W * H):
            np[i] = BLACK
        np.write()
        time.sleep_ms(120)


# ------------------------------------------------------------ Hauptschleife
def main():
    game = Game()
    btn = Buttons()
    next_tick = time.ticks_ms()
    next_draw = next_tick
    game.draw()
    try:
        while True:
            now = time.ticks_ms()
            game.now = now
            btn.poll(now)                                # Eingabe lesen + entprellen
            if time.ticks_diff(now, next_tick) >= 0:     # fester Spieltakt
                next_tick = time.ticks_add(now, TICK_MS)
                move, jump, place, reset = btn.consume()
                if reset:
                    game.reset()
                else:
                    game.step(move, jump, place)         # Kollision, Schwerkraft, Sprung
                if game.won or game.fell:                # Coin oder Absturz: neu anfangen
                    flash(CELEBRATE if game.won else FALL_FLASH, 3 if game.won else 2)
                    game.reset()
                    btn.clear()
                    now = time.ticks_ms()
                    game.now = now
                    next_tick = time.ticks_add(now, TICK_MS)
                next_draw = now                          # sofort neu zeichnen
            if time.ticks_diff(now, next_draw) >= 0:     # Bild oefter als der Spieltakt
                game.draw()
                next_draw = time.ticks_add(now, DRAW_MS)
            time.sleep_ms(5)
    finally:
        for i in range(W * H):                           # beim Stoppen (Thonny) LEDs aus
            np[i] = BLACK
        np.write()


if __name__ == "__main__":
    main()
