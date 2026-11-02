"""CATCH 64 – persoenliche Live-Aufbruchzeit auf 64 LEDs.

Die Lumatrix zeigt dauerhaft nur die wichtigste Information. Zusatzdaten
erscheinen ausschliesslich nach einer eindeutigen Joystick-Aktion.
"""

import sys
from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms, ticks_diff, ticks_ms

import catch_logic
import config

try:
    import uselect as select
except ImportError:
    import select

try:
    import ujson as json
except ImportError:
    import json


WIDTH = 8
HEIGHT = 8
NUM_LEDS = 64

OFF = (0, 0, 0)
WHITE = (10, 10, 9)
BLUE = (0, 4, 13)
GREEN = (0, 12, 4)
AMBER = (14, 7, 0)
RED = (14, 0, 1)
WAITING = (1, 2, 5)

COLORS = {
    "WHITE": WHITE,
    "BLUE": BLUE,
    "GREEN": GREEN,
    "AMBER": AMBER,
    "RED": RED,
}

FONT = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("111", "100", "100", "100", "111"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "G": ("111", "100", "101", "101", "111"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "L": ("100", "100", "100", "100", "111"),
    "N": ("101", "111", "111", "111", "101"),
    "P": ("110", "101", "110", "100", "100"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
    "X": ("101", "101", "010", "101", "101"),
    "+": ("000", "010", "111", "010", "000"),
    "-": ("000", "000", "111", "000", "000"),
    "?": ("111", "001", "011", "000", "010"),
}

# Universelles Aufbruchssymbol. Es bedeutet "jetzt los" und bildet bewusst
# keine reale Gehrichtung ab.
DUE_ARROW = (
    "00010000",
    "00011000",
    "11111100",
    "11111110",
    "11111100",
    "00011000",
    "00010000",
    "00000000",
)

np = NeoPixel(Pin(config.LED_PIN, Pin.OUT), NUM_LEDS)
button = Pin(config.BUTTON_PIN, Pin.IN, Pin.PULL_UP)
joy_up = Pin(config.JOY_UP_PIN, Pin.IN, Pin.PULL_UP)
joy_down = Pin(config.JOY_DOWN_PIN, Pin.IN, Pin.PULL_UP)
joy_right = Pin(config.JOY_RIGHT_PIN, Pin.IN, Pin.PULL_UP)


def transform_xy(x, y):
    if config.MIRROR_X:
        x = 7 - x
    if config.MIRROR_Y:
        y = 7 - y
    rotation = config.ROTATION % 360
    if rotation == 90:
        x, y = 7 - y, x
    elif rotation == 180:
        x, y = 7 - x, 7 - y
    elif rotation == 270:
        x, y = y, 7 - x
    return x, y


def led_index(x, y):
    x, y = transform_xy(x, y)
    if config.SERPENTINE and y % 2:
        x = 7 - x
    return y * WIDTH + x


def pixel(x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        np[led_index(x, y)] = color


def clear():
    for index in range(NUM_LEDS):
        np[index] = OFF


def show():
    np.write()


def draw_glyph(character, x_start, color, y_start=1):
    glyph = FONT.get(character, FONT["?"])
    for y, row in enumerate(glyph):
        for x, bit in enumerate(row):
            if bit == "1":
                pixel(x_start + x, y_start + y, color)


def draw_pair(text, color):
    text = str(text).upper()[:2]
    if len(text) == 1:
        draw_glyph(text, 2, color)
    else:
        draw_glyph(text[0], 0, color)
        draw_glyph(text[1], 4, color)


def draw_number(value, color):
    draw_pair("{:02d}".format(max(0, min(99, int(value)))), color)


def draw_due_arrow(color=RED):
    for y, row in enumerate(DUE_ARROW):
        for x, bit in enumerate(row):
            if bit == "1":
                pixel(x, y, color)


def draw_number_transition(old_value, new_value, step, color):
    """Nur veraenderte Ziffern rollen: alt nach unten, neu von oben."""
    old_text = "{:02d}".format(max(0, min(99, int(old_value))))
    new_text = "{:02d}".format(max(0, min(99, int(new_value))))
    for index in range(2):
        x_start = index * 4
        if old_text[index] == new_text[index]:
            draw_glyph(old_text[index], x_start, color)
        else:
            draw_glyph(old_text[index], x_start, color, 1 + step)
            draw_glyph(new_text[index], x_start, color, -4 + step)


def waiting_display():
    clear()
    # Ruhiges C als Bereitschaftszeichen.
    draw_glyph("C", 2, WAITING)
    show()


def error_display():
    clear()
    draw_pair("ER", RED)
    show()


def pressed(pin):
    return pin.value() == 0


def wait_release(pin):
    sleep_ms(25)
    while pressed(pin):
        sleep_ms(15)
    sleep_ms(25)


def make_serial_poller():
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)
    return poller


def read_packet(poller):
    if not poller.poll(0):
        return None
    line = sys.stdin.readline()
    if not line:
        return None
    return catch_logic.validate_packet(json.loads(line))


def connection_cancelled(connection):
    return bool(connection[5] & catch_logic.FLAG_CANCELLED)


def render_line(connection, elapsed_ms):
    chunks = catch_logic.line_chunks(connection[0])
    chunk_index = min(len(chunks) - 1, elapsed_ms // config.LINE_CHUNK_MS)
    clear()
    draw_pair(chunks[chunk_index], WHITE)
    show()
    return elapsed_ms >= len(chunks) * config.LINE_CHUNK_MS


def render_leave(connection, packet_age_ms, packet):
    minutes = catch_logic.minutes_remaining(connection[1], packet_age_ms)
    seconds = catch_logic.seconds_remaining(connection[1], packet_age_ms)
    phase = catch_logic.leave_phase(connection[1], packet_age_ms)
    clear()
    if connection_cancelled(connection):
        draw_pair("XX", RED)
    elif phase == "DUE":
        draw_due_arrow()
    elif phase == "MISSED":
        draw_pair("XX", RED)
    elif seconds <= 60:
        draw_number(seconds, RED)
    else:
        color = COLORS[catch_logic.urgency(minutes)]
        draw_number(minutes, color)
    show()


def render_departure(connection, packet_age_ms):
    minutes = catch_logic.minutes_remaining(connection[2], packet_age_ms)
    clear()
    draw_number(minutes, BLUE)
    show()


def platform_chunks(platform):
    clean = catch_logic.clean_alnum(platform)
    if not clean:
        return ("--",)
    if len(clean) == 1:
        return ("G" + clean,)
    return ("G",) + catch_logic.line_chunks(clean)


def render_platform(connection, elapsed_ms):
    chunks = platform_chunks(connection[4])
    index = min(len(chunks) - 1, elapsed_ms // config.LINE_CHUNK_MS)
    clear()
    draw_pair(chunks[index], BLUE if index else WHITE)
    show()


def render_event(event):
    code, value = event
    clear()
    if code == "D":
        text = "+" + str(max(0, min(9, int(value))))
        draw_pair(text, AMBER)
    elif code == "P":
        platform = str(value)
        draw_pair("G" + platform[-1], AMBER)
    else:
        draw_pair("XX", RED)
    show()


def render_roll(old_value, new_value, step):
    clear()
    draw_number_transition(old_value, new_value, step, COLORS[catch_logic.urgency(new_value)])
    show()


def read_action():
    if pressed(joy_up):
        wait_release(joy_up)
        return "UP"
    if pressed(joy_down):
        wait_release(joy_down)
        return "DOWN"
    if pressed(joy_right):
        wait_release(joy_right)
        return "RIGHT"
    if pressed(button):
        wait_release(button)
        return "CENTER"
    return None


def main():
    poller = make_serial_poller()
    packet = None
    packet_received_at = ticks_ms()
    program_started = packet_received_at
    selected = 0
    page = catch_logic.PAGE_LEAVE
    state = "WAITING"
    state_started = packet_received_at
    active_event = None
    demo_active = False
    last_render_key = None
    stale_reported = False
    last_line_at = program_started
    last_leave_minutes = None
    last_leave_selected = None
    last_leave_phase = None
    roll_from = 0
    roll_to = 0

    waiting_display()
    print("CATCH64_READY")

    while True:
        changed = False
        try:
            received = read_packet(poller)
            if received is not None:
                first_packet = packet is None or demo_active
                was_recommended = packet is not None and selected == packet["r"]
                old_line = packet["c"][selected][0] if packet is not None else None
                packet = received
                packet_received_at = ticks_ms()
                demo_active = False
                stale_reported = False
                active_event = packet.get("e")
                last_leave_phase = None
                if first_packet or state == "MISSED_HOLD":
                    selected = packet["r"]
                    page = catch_logic.PAGE_LEAVE
                    state = "LINE"
                    state_started = packet_received_at
                elif active_event:
                    selected = packet["r"]
                    page = catch_logic.PAGE_LEAVE
                    state = "ALERT"
                    state_started = packet_received_at
                elif was_recommended:
                    selected = packet["r"]
                    if old_line != packet["c"][selected][0]:
                        page = catch_logic.PAGE_LEAVE
                        state = "LINE"
                        state_started = packet_received_at
                else:
                    selected = min(selected, len(packet["c"]) - 1)
                last_leave_minutes = None
                last_leave_selected = None
                changed = True
                print("CATCH64_DATA_OK")
        except Exception as exc:
            print("CATCH64_PACKET_ERROR", exc)

        now = ticks_ms()
        if packet is None and ticks_diff(now, program_started) >= config.DEMO_AFTER_SECONDS * 1000:
            packet = catch_logic.demo_packet()
            packet_received_at = now
            selected = packet["r"]
            page = catch_logic.PAGE_LEAVE
            state = "LINE"
            state_started = now
            demo_active = True
            last_leave_minutes = None
            last_leave_selected = None
            last_leave_phase = None
            changed = True
            print("CATCH64_DEMO")

        action = read_action()
        if action and packet is not None:
            if action == "RIGHT":
                selected = min(
                    len(packet["c"]) - 1,
                    max(selected, packet["r"]) + 1,
                )
                page = catch_logic.PAGE_LEAVE
                state = "LINE"
            elif action == "CENTER":
                selected = packet["r"]
                page = catch_logic.PAGE_LEAVE
                state = "LINE"
            elif action == "UP":
                page = catch_logic.PAGE_DEPARTURE
                state = "INFO"
            else:
                page = catch_logic.PAGE_PLATFORM
                state = "INFO"
            active_event = None
            state_started = ticks_ms()
            last_leave_minutes = None
            last_leave_selected = None
            last_leave_phase = None
            changed = True

        now = ticks_ms()
        elapsed_state = ticks_diff(now, state_started)
        if state == "ALERT" and elapsed_state >= config.ALERT_MS:
            # Nach einem Ausfall muss die neue Linie einmal genannt werden.
            # Verspaetung und Gleiswechsel kehren direkt zur ruhigen Zahl zurueck.
            state = "LINE" if active_event and active_event[0] == "X" else "VALUE"
            active_event = None
            state_started = now
            changed = True
        elif state == "INFO" and elapsed_state >= config.INFO_MS:
            page = catch_logic.PAGE_LEAVE
            state = "VALUE"
            state_started = now
            changed = True
        elif state == "ROLL" and elapsed_state >= config.DIGIT_STEP_MS * 6:
            state = "VALUE"
            state_started = now
            changed = True

        if packet is not None:
            connection = packet["c"][selected]
            packet_age_ms = ticks_diff(now, packet_received_at)

            # Die ruhige Hauptanzeige reagiert nur auf echte Zustandswechsel.
            if state == "VALUE" and page == catch_logic.PAGE_LEAVE:
                phase_now = catch_logic.leave_phase(
                    connection[1], packet_age_ms
                )
                if not connection_cancelled(connection) and phase_now == "MISSED":
                    next_index = catch_logic.next_reachable_index(
                        packet["c"], packet_age_ms, selected + 1
                    )
                    if next_index is None:
                        state = "MISSED_HOLD"
                    else:
                        selected = next_index
                        page = catch_logic.PAGE_LEAVE
                        state = "LINE"
                        last_line_at = now
                    last_leave_minutes = None
                    last_leave_selected = None
                    last_leave_phase = None
                    state_started = now
                    changed = True
                elif not connection_cancelled(connection) and phase_now == "DUE":
                    last_leave_minutes = 0
                    last_leave_selected = selected
                    last_leave_phase = "DUE"
                elif phase_now == "COUNTDOWN":
                    current_minutes = catch_logic.minutes_remaining(
                        connection[1], packet_age_ms
                    )
                    if (
                        last_leave_selected == selected
                        and last_leave_minutes is not None
                        and current_minutes == last_leave_minutes - 1
                        and catch_logic.seconds_remaining(
                            connection[1], packet_age_ms
                        ) > 60
                    ):
                        roll_from = last_leave_minutes
                        roll_to = current_minutes
                        state = "ROLL"
                        state_started = now
                        changed = True
                    last_leave_minutes = current_minutes
                    last_leave_selected = selected
                    last_leave_phase = "COUNTDOWN"
                    if ticks_diff(now, last_line_at) >= config.LINE_REPEAT_MS:
                        state = "LINE"
                        state_started = now
                        last_line_at = now
                        changed = True

            elapsed_state = ticks_diff(now, state_started)
            if state in ("ALERT", "LINE", "INFO", "ROLL"):
                time_key = elapsed_state // 100
            elif page == catch_logic.PAGE_LEAVE:
                phase_key = catch_logic.leave_phase(
                    connection[1], packet_age_ms
                )
                time_key = (
                    phase_key,
                    catch_logic.minutes_remaining(connection[1], packet_age_ms),
                    catch_logic.seconds_remaining(connection[1], packet_age_ms)
                    if phase_key == "COUNTDOWN"
                    and catch_logic.seconds_remaining(connection[1], packet_age_ms) <= 60
                    else 0,
                )
            elif page == catch_logic.PAGE_DEPARTURE:
                time_key = catch_logic.minutes_remaining(connection[2], packet_age_ms)
            else:
                time_key = elapsed_state // config.LINE_CHUNK_MS
            render_key = (state, page, selected, time_key)
            if changed or render_key != last_render_key:
                last_render_key = render_key
                if state == "ALERT":
                    render_event(active_event)
                elif state == "LINE":
                    if render_line(connection, elapsed_state):
                        state = "VALUE"
                        state_started = now
                        last_line_at = now
                elif state == "INFO":
                    if page == catch_logic.PAGE_DEPARTURE:
                        render_departure(connection, packet_age_ms)
                    else:
                        render_platform(connection, elapsed_state)
                elif state == "ROLL":
                    step = min(5, elapsed_state // config.DIGIT_STEP_MS)
                    render_roll(roll_from, roll_to, step)
                elif state == "MISSED_HOLD":
                    clear()
                    draw_pair("--", AMBER)
                    show()
                elif page == catch_logic.PAGE_LEAVE:
                    render_leave(connection, packet_age_ms, packet)
                elif page == catch_logic.PAGE_DEPARTURE:
                    render_departure(connection, packet_age_ms)
                else:
                    render_platform(connection, elapsed_state)

        # Datenaltern wird bewusst nur im Terminal gemeldet. Die letzte sichere
        # Anzeige bleibt stehen, statt den Nutzer mit einem neuen Symbol zu stoeren.
        stale_now = (
            packet is not None
            and not demo_active
            and ticks_diff(now, packet_received_at) >= config.DATA_STALE_MINUTES * 60 * 1000
        )
        if stale_now and not stale_reported:
            stale_reported = True
            print("CATCH64_DATA_STALE")
        sleep_ms(35)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("CATCH 64 Fehler:", exc)
        error_display()
        raise
