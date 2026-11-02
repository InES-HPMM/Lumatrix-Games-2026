# Hardware-Schicht der ZHAW Lumatrix: Bildpuffer, Helligkeit, Joystick, DIP-Schalter
from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms, ticks_ms, ticks_diff, ticks_add

try:
    from micropython import native
except ImportError:  # Simulator am Mac
    def native(f):
        return f

BRIGHTNESS = 35          # Helligkeit in Prozent
POWER_BUDGET_MA = 800    # maximaler LED-Strom; bei viel Weiss wird automatisch gedimmt
MA_PER_CHANNEL = 12      # ca. Strom eines Farbkanals bei Wert 255 (WS2812B)
HARD_SWITCH_VALUE = 0    # DIP-Schalter-Stellung fuer den schweren Modus
FRAME_MS = 30            # Dauer eines Bildes (ca. 33 Bilder pro Sekunde)
REPEAT_DELAY = 260       # Joystick gehalten: erste Wiederholung nach ... ms
REPEAT_RATE = 130        # danach alle ... ms

BLACK = (0, 0, 0)

_np = NeoPixel(Pin(19, Pin.OUT), 64)
fb = [BLACK] * 64        # Bildpuffer, Index y*8+x, y=0 ist die oberste Zeile

_pins = (
    ("up", Pin(3, Pin.IN, Pin.PULL_UP)),
    ("down", Pin(6, Pin.IN, Pin.PULL_UP)),
    ("left", Pin(7, Pin.IN, Pin.PULL_UP)),
    ("right", Pin(2, Pin.IN, Pin.PULL_UP)),
    ("center", Pin(8, Pin.IN, Pin.PULL_UP)),
)
_switch = Pin(9, Pin.IN, Pin.PULL_UP)
_down = {}
_next = {}
_last_tick = ticks_ms()


# ---------------------------------------------------------------- Zeichnen
def clear(color=BLACK):
    for i in range(64):
        fb[i] = color


def set(x, y, color):
    if 0 <= x < 8 and 0 <= y < 8:
        fb[y * 8 + x] = color


def get(x, y):
    return fb[y * 8 + x]


def blit(img):
    for i in range(64):
        fb[i] = img[i]


def snapshot():
    return list(fb)


@native
def show(level=100):
    """Bildpuffer mit Helligkeit (und optionalem Ueberblend-Level 0..100) ausgeben."""
    scale = BRIGHTNESS * level  # in 1/10000
    total = 0
    for c in fb:
        total += c[0] + c[1] + c[2]
    ma = total * scale * MA_PER_CHANNEL // 2550000
    if ma > POWER_BUDGET_MA:
        scale = scale * POWER_BUDGET_MA // ma
    buf = _np.buf  # Reihenfolge Gruen, Rot, Blau
    for y in range(8):
        src = y * 8
        dst = (7 - y) * 24  # LED 0 liegt unten links
        for x in range(8):
            c = fb[src + x]
            buf[dst] = c[1] * scale // 10000
            buf[dst + 1] = c[0] * scale // 10000
            buf[dst + 2] = c[2] * scale // 10000
            dst += 3
    _np.write()


# ---------------------------------------------------------------- Zeit
def now():
    return ticks_ms()


def tick(ms=FRAME_MS):
    """Wartet bis zum naechsten Bild und gibt die vergangene Zeit in ms zurueck."""
    global _last_tick
    elapsed = ticks_diff(ticks_ms(), _last_tick)
    if elapsed < ms:
        sleep_ms(ms - elapsed)
    t = ticks_ms()
    dt = ticks_diff(t, _last_tick)
    _last_tick = t
    return min(dt, 100)


def pause(ms, level=100):
    """Aktuelles Bild zeigen und warten (Eingaben werden verworfen)."""
    show(level)
    end = ticks_add(ticks_ms(), ms)
    while ticks_diff(end, ticks_ms()) > 0:
        tick()
        poll()


def fade(ms, start=0, end=100):
    """Aktuelles Bild ein- oder ausblenden."""
    steps = max(1, ms // FRAME_MS)
    for i in range(steps + 1):
        show(start + (end - start) * i // steps)
        tick()
        poll()


# ---------------------------------------------------------------- Eingabe
def poll(repeat=True):
    """Liest den Joystick. Gibt neu gedrueckte Richtungen zurueck
    ('up', 'down', 'left', 'right', 'center'); gehaltene Richtungen wiederholen sich."""
    events = []
    t = ticks_ms()
    for name, pin in _pins:
        pressed = pin.value() == 0
        if pressed and not _down.get(name):
            events.append(name)
            _next[name] = ticks_add(t, REPEAT_DELAY)
        elif pressed and repeat and name != "center" and ticks_diff(t, _next[name]) >= 0:
            events.append(name)
            _next[name] = ticks_add(t, REPEAT_RATE)
        _down[name] = pressed
    return events


def held(name):
    return bool(_down.get(name))


def hard():
    return _switch.value() == HARD_SWITCH_VALUE
