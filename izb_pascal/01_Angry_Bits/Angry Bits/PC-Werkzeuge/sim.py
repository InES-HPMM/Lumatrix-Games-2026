# Lumatrix-Simulator fuer den PC
#
# Fuehrt main.py unveraendert aus und ersetzt dabei die Pico-Module
# machine, neopixel und time.sleep_ms durch Attrappen.
#
# Starten:  sim.py in Thonny oeffnen und mit F5 ausfuehren
#           (Interpreter: "Lokales Python 3", nicht der Pico!)
#           oder:  python sim.py [anderes_programm.py]
#
# Tasten:   Pfeiltasten  -> Joystick
#           Leertaste / Enter -> Joystick Mitte
#           P            -> Schiebeschalter umlegen
#           I            -> LED-Nummern ein/aus
#           M            -> Ton ein/aus

import os
import sys
import queue
import threading
import time
import traceback
import types
import runpy
import tkinter as tk

try:
    import winsound
except ImportError:
    winsound = None

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)    # das Spiel liegt eine Ebene hoeher
PROGRAM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GAME_DIR,
                                                             "main.py")

# ---------------------------------------------------------------
# Zustand, den Spiel-Thread und Fenster teilen
# ---------------------------------------------------------------
pin_values = {}             # GPIO -> 0/1 (1 = nicht gedrueckt, Pull-up)
leds = [(0, 0, 0)] * 64     # zuletzt mit np.write() gesendete Farben
lock = threading.Lock()


# ---------------------------------------------------------------
# Attrappe: machine
# ---------------------------------------------------------------
class Pin:
    IN = 0
    OUT = 1
    PULL_UP = 1
    PULL_DOWN = 2

    def __init__(self, id, mode=IN, pull=None, value=None):
        self.id = id
        with lock:
            pin_values.setdefault(id, 1)
            if value is not None:
                pin_values[id] = value

    def value(self, v=None):
        with lock:
            if v is None:
                return pin_values.get(self.id, 1)
            pin_values[self.id] = 1 if v else 0

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    def __call__(self, v=None):
        return self.value(v)


sound_on = [True]
sound_queue = queue.Queue()


class PWM:
    # Summer: Ein Ton wird nach dem Ausschalten mit seiner Laenge gespielt
    def __init__(self, pin, freq=1000, duty_u16=0):
        self._freq = freq
        self._duty = 0
        self._start = None

    def freq(self, f=None):
        if f is None:
            return self._freq
        self._freq = int(f)

    def duty_u16(self, d=None):
        if d is None:
            return self._duty
        self._duty = d
        if d > 0 and self._start is None:
            self._start = time.monotonic()
        elif d == 0 and self._start is not None:
            ms = int((time.monotonic() - self._start) * 1000)
            self._start = None
            if sound_on[0]:
                sound_queue.put((self._freq, max(ms, 20)))

    def deinit(self):
        pass


def sound_worker():
    while True:
        f, ms = sound_queue.get()
        if winsound and 37 <= f <= 32767:
            try:
                winsound.Beep(f, ms)
            except RuntimeError:
                pass


threading.Thread(target=sound_worker, daemon=True).start()

machine = types.ModuleType("machine")
machine.Pin = Pin
machine.PWM = PWM
machine.SIMULATED = True


# ---------------------------------------------------------------
# Attrappe: neopixel
# ---------------------------------------------------------------
class NeoPixel:
    def __init__(self, pin, n, bpp=3, timing=1):
        self.n = n
        self.buf = [(0, 0, 0)] * n

    def __setitem__(self, i, color):
        self.buf[i] = tuple(int(c) for c in color[:3])

    def __getitem__(self, i):
        return self.buf[i]

    def __len__(self):
        return self.n

    def fill(self, color):
        for i in range(self.n):
            self[i] = color

    def write(self):
        global leds
        with lock:
            leds = list(self.buf[:64]) + [(0, 0, 0)] * (64 - min(self.n, 64))


neopixel = types.ModuleType("neopixel")
neopixel.NeoPixel = NeoPixel

sys.modules["machine"] = machine
sys.modules["neopixel"] = neopixel
time.sleep_ms = lambda ms: time.sleep(ms / 1000)
time.sleep_us = lambda us: time.sleep(us / 1000000)
time.ticks_ms = lambda: int(time.monotonic() * 1000)
time.ticks_diff = lambda a, b: a - b
time.ticks_add = lambda a, b: a + b


# ---------------------------------------------------------------
# Fenster
# ---------------------------------------------------------------
CELL = 56
PAD = 20
KEYS = {"Up": 3, "Down": 6, "Left": 7, "Right": 2,
        "space": 8, "Return": 8}
SWITCH_PIN = 9


def to_screen(c):
    # Echte LEDs leuchten schon bei kleinen Werten hell -> aufhellen
    r, g, b = (int(255 * (max(0, min(v, 255)) / 255) ** 0.4) if v else 0
               for v in c)
    return "#%02x%02x%02x" % (r, g, b)


root = tk.Tk()
root.title("Lumatrix-Simulator - " + os.path.basename(PROGRAM))
root.configure(bg="#111")
size = 8 * CELL + 2 * PAD
canvas = tk.Canvas(root, width=size, height=size, bg="#0b0b0b",
                   highlightthickness=0)
canvas.pack()
status = tk.Label(root, bg="#111", fg="#aaa", font=("Segoe UI", 10),
                  text="Pfeile = Joystick   Leertaste = Mitte   "
                       "P = Schalter   I = Nummern   M = Ton")
status.pack(pady=6)

dots, labels = [], []
for i in range(64):
    x, y = i % 8, i // 8
    sx = PAD + x * CELL
    sy = PAD + (7 - y) * CELL       # Index 0 ist unten links
    dots.append(canvas.create_oval(sx + 6, sy + 6, sx + CELL - 6,
                                   sy + CELL - 6, fill="#1a1a1a",
                                   outline="#262626"))
    labels.append(canvas.create_text(sx + CELL / 2, sy + CELL / 2,
                                     text=str(i), fill="#666",
                                     font=("Segoe UI", 8), state="hidden"))

show_numbers = [False]
error = [None]


def key_down(e):
    if e.keysym in KEYS:
        with lock:
            pin_values[KEYS[e.keysym]] = 0
    elif e.keysym.lower() == "p":
        with lock:
            pin_values[SWITCH_PIN] = 1 - pin_values.get(SWITCH_PIN, 1)
    elif e.keysym.lower() == "m":
        sound_on[0] = not sound_on[0]
    elif e.keysym.lower() == "i":
        show_numbers[0] = not show_numbers[0]
        for t in labels:
            canvas.itemconfigure(t, state="normal" if show_numbers[0]
                                 else "hidden")


def key_up(e):
    if e.keysym in KEYS:
        with lock:
            pin_values[KEYS[e.keysym]] = 1


root.bind("<KeyPress>", key_down)
root.bind("<KeyRelease>", key_up)

last = [None] * 64


def refresh():
    with lock:
        current = list(leds)
        sw = pin_values.get(SWITCH_PIN, 1)
    for i, c in enumerate(current):
        if c != last[i]:
            last[i] = c
            canvas.itemconfigure(dots[i],
                                 fill=to_screen(c) if any(c) else "#1a1a1a")
    if error[0]:
        status.configure(text=error[0], fg="#f66")
    root.title("Lumatrix-Simulator - %s   [Schalter: %s]"
               % (os.path.basename(PROGRAM), sw))
    root.after(16, refresh)


def run_program():
    try:
        folder = os.path.dirname(os.path.abspath(PROGRAM))
        sys.path.insert(0, folder)
        os.chdir(folder)            # save.txt landet im Spielordner
        runpy.run_path(PROGRAM, run_name="__main__")
        error[0] = "Programm beendet."
    except Exception as ex:
        traceback.print_exc()
        error[0] = "Fehler: %s: %s" % (type(ex).__name__, ex)


threading.Thread(target=run_program, daemon=True).start()
root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))
refresh()
root.mainloop()
