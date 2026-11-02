
from machine import Pin
import neopixel
import sys
import time
import uselect
import ubinascii


# ---------- Einstellungen ----------

LED_PIN = 19
NUM_LEDS = 64

JOYSTICK_UP_PIN = 3
JOYSTICK_DOWN_PIN = 6
JOYSTICK_RIGHT_PIN = 2
JOYSTICK_LEFT_PIN = 7

DEBOUNCE_MS = 50


# ---------- NeoPixel ----------

pixels = neopixel.NeoPixel(
    Pin(LED_PIN),
    NUM_LEDS,
)

pixels.fill((0, 0, 0))
pixels.write()


# ---------- Joystick ----------

# Beide Pins sind normalerweise HIGH.
# Der Joystick zieht den jeweiligen Pin auf LOW.
joystick_up = Pin(JOYSTICK_UP_PIN, Pin.IN, Pin.PULL_UP)
joystick_down = Pin(JOYSTICK_DOWN_PIN, Pin.IN, Pin.PULL_UP)
joystick_right = Pin(JOYSTICK_RIGHT_PIN, Pin.IN, Pin.PULL_UP)
joystick_left = Pin(JOYSTICK_LEFT_PIN, Pin.IN, Pin.PULL_UP)


# Entprellung: Anfangszustände einlesen.
up_raw = joystick_up.value()
up_stable = up_raw
up_changed_at = time.ticks_ms()

down_raw = joystick_down.value()
down_stable = down_raw
down_changed_at = time.ticks_ms()

# ---------- Helligkeits-Joystick initialisieren ----------

right_raw = joystick_right.value()
right_stable = right_raw
right_changed_at = time.ticks_ms()

left_raw = joystick_left.value()
left_stable = left_raw
left_changed_at = time.ticks_ms()

def send_message(message):
    print(message)



def check_joystick():
    global up_raw, up_stable, up_changed_at
    global down_raw, down_stable, down_changed_at
    global right_raw, right_stable, right_changed_at
    global left_raw, left_stable, left_changed_at

    now = time.ticks_ms()

    # ---------- Nach oben: Pixelgrösse erhöhen ----------
    value = joystick_up.value()

    if value != up_raw:
        up_raw = value
        up_changed_at = now

    elif (
        value != up_stable
        and time.ticks_diff(now, up_changed_at) >= DEBOUNCE_MS
    ):
        up_stable = value

        if up_stable == 0:
            send_message("UP")

    # ---------- Nach unten: Pixelgrösse verringern ----------
    value = joystick_down.value()

    if value != down_raw:
        down_raw = value
        down_changed_at = now

    elif (
        value != down_stable
        and time.ticks_diff(now, down_changed_at) >= DEBOUNCE_MS
    ):
        down_stable = value

        if down_stable == 0:
            send_message("DOWN")

    # ---------- Nach rechts: Helligkeit erhöhen ----------
    value = joystick_right.value()

    if value != right_raw:
        right_raw = value
        right_changed_at = now

    elif (
        value != right_stable
        and time.ticks_diff(now, right_changed_at) >= DEBOUNCE_MS
    ):
        right_stable = value

        if right_stable == 0:
            send_message("RIGHT")

    # ---------- Nach links: Helligkeit verringern ----------
    value = joystick_left.value()

    if value != left_raw:
        left_raw = value
        left_changed_at = now

    elif (
        value != left_stable
        and time.ticks_diff(now, left_changed_at) >= DEBOUNCE_MS
    ):
        left_stable = value

        if left_stable == 0:
            send_message("LEFT")



# ---------- Empfangene Pixel ----------

def receive_pixels(line):
    line = line.strip()

    if len(line) != NUM_LEDS * 6:
        return

    try:
        raw = ubinascii.unhexlify(line)
    except Exception:
        return

    if len(raw) != NUM_LEDS * 3:
        return

    for i in range(NUM_LEDS):
        r = raw[i * 3]
        g = raw[i * 3 + 1]
        b = raw[i * 3 + 2]

        pixels[i] = (r, g, b)

    pixels.write()


# ---------- USB-Empfang ----------

poller = uselect.poll()
poller.register(sys.stdin, uselect.POLLIN)

rx_buffer = ""

send_message("Lumatrix bereit")

while True:
    check_joystick()

    # USB-Eingaben nur lesen, wenn Daten verfügbar sind.
    while poller.poll(0):
        char = sys.stdin.read(1)

        if not char:
            break

        if char == "\n":
            receive_pixels(rx_buffer)
            rx_buffer = ""

        elif char != "\r":
            if len(rx_buffer) < 400:
                rx_buffer += char
            else:
                rx_buffer = ""

    time.sleep_ms(5)
