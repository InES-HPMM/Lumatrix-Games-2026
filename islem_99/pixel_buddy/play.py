"""Interactive runtime. All drawing uses complete frames and the ZHAW driver."""
import json
from time import ticks_ms, ticks_diff, sleep_ms
from zhaw_led_matrix import Button
from .animation import Animator
from .controls import Controls, DoublePress
from .display import Display
from .faces import COLOR, TALK_MOUTHS, paint
from .link import ALARM_MS, Link
from .pet import Pet

ICONS = {
    "food": ("00001000", "00010000", "00111100", "01111110", "01111110", "01111110", "00111100", "00000000"),
    "heart": ("00000000", "01100110", "11111111", "11111111", "01111110", "00111100", "00011000", "00000000"),
    "win": ("00011000", "00011000", "11111111", "01111110", "00111100", "01100110", "01000010", "00000000"),
    "note": ("00011110", "00010010", "00010010", "00010010", "01110010", "11110110", "01100110", "00000000"),
}
ICON_COLORS = {"heart": (255, 90, 120), "note": (80, 200, 255)}

# Timer digits, 3 columns x 7 rows each; row 7 shows the running minute.
DIGITS = (
    ("111", "101", "101", "101", "101", "101", "111"),
    ("010", "110", "010", "010", "010", "010", "111"),
    ("111", "001", "001", "111", "100", "100", "111"),
    ("111", "001", "001", "111", "001", "001", "111"),
    ("101", "101", "101", "111", "001", "001", "001"),
    ("111", "100", "100", "111", "001", "001", "111"),
    ("111", "100", "100", "111", "101", "101", "111"),
    ("111", "001", "001", "001", "010", "010", "010"),
    ("111", "101", "101", "111", "101", "101", "111"),
    ("111", "101", "101", "111", "001", "001", "111"),
)
MINUTES_COLOR = (80, 200, 255)
SECONDS_COLOR = (255, 150, 40)  # Last minute: seconds instead of minutes.
ALARM_COLOR = (255, 40, 40)

# Chat actions that reuse the joystick actions of the pet.
PET_EVENTS = {"feed": "up", "pet": "center", "rest": "left", "play": "right", "status": "down"}

# Mouth shapes while the PC voice speaks: syllables with short closed pauses.
TALK_SHAPES = (1, 2, 0, 3, 1, 2, 3, 0)


def dot(frame, x, y, color):
    i = (y * 8 + x) * 3
    for c in range(3):
        frame[i + c] = color[c]


def draw_sleep(frame, elapsed):
    for i in range(192):
        frame[i] = 0
    level = 40 + abs(1800 - elapsed % 3600) * 30 // 1800
    for x in (0, 1, 2, 5, 6, 7):
        dot(frame, x, 2, (level, level, level))
    dot(frame, 3, 5, (level, level, level))
    dot(frame, 4, 5, (level, level, level))


def draw_icon(frame, effect):
    color = ICON_COLORS.get(effect, (255, 180, 60))
    for y, row in enumerate(ICONS[effect]):
        for x, value in enumerate(row):
            dot(frame, x, y, color if value == "1" else (0, 0, 0))


def render_link(link, frame):
    """PC chat states on top of the animated face; pet actions still win."""
    age = link.age
    if link.mode == "think":
        # Curious glances left/right and short blinks; the mouth stays still.
        phase = age % 2400
        gaze = -1 if phase < 800 else (1 if 1200 <= phase < 2000 else 0)
        paint(frame, "neutral", lid=2 if age % 3100 < 150 else 0, gaze=gaze)
        return
    if link.mode == "listen":
        # Attentive face with softly pulsing blue "ears" in the top corners.
        paint(frame, "neutral", lid=2 if age % 3400 < 150 else 0)
        level = 40 + abs(600 - age % 1200) * 120 // 600
        dot(frame, 0, 0, (0, level // 2, level))
        dot(frame, 7, 0, (0, level // 2, level))
        return
    if link.mode == "show":
        anim = link.anim
        if anim == "sleepy":
            draw_sleep(frame, age % 3600)
            return
        if anim in ("heart", "star", "note") and age < 1600:
            draw_icon(frame, "win" if anim == "star" else anim)
            return
        if anim == "wink" and link.face == "happy" and 500 <= age < 800:
            paint(frame, "happy", wink=True)
        elif anim == "look" and age < 2400:
            paint(frame, "neutral", gaze=-1 if age % 1200 < 600 else 1)
    if link.talk_ms:
        # PC voice is speaking: keep the eyes, move only the mouth.
        for i in range(120, 168):
            frame[i] = 0
        for x, y in TALK_MOUTHS[TALK_SHAPES[(link.talk_age // 150) % len(TALK_SHAPES)]]:
            dot(frame, x, y, COLOR)


def draw_number(frame, value, color):
    for i in range(192):
        frame[i] = 0
    text = str(value)
    left = 2 if len(text) == 1 else 0
    for n, ch in enumerate(text):
        for y, row in enumerate(DIGITS[int(ch)]):
            for x, bit in enumerate(row):
                if bit == "1":
                    dot(frame, left + n * 4 + x, y, color)


def render_timer(link, frame, busy):
    """Big countdown when Buddy is otherwise idle; the alarm blinks over everything."""
    if link.alarm_ms:
        if (ALARM_MS - link.alarm_ms) % 600 < 400:
            draw_number(frame, 0, ALARM_COLOR)
        else:
            for i in range(192):
                frame[i] = 0
        return
    left = link.timer_ms
    if not left or busy:
        return
    if left <= 60000:
        draw_number(frame, (left + 999) // 1000, SECONDS_COLOR)
        return
    draw_number(frame, (left + 59999) // 60000, MINUTES_COLOR)
    # Dots in the bottom row run out during each minute.
    rest = (left - 1) % 60000 + 1
    for x in range((rest * 8 + 59999) // 60000):
        dot(frame, x, 7, (20, 50, 64))


def apply_action(pet, link, switch_sleep):
    """Run a chat action like the matching joystick press; return a short result."""
    action, link.action = link.action, None
    if action == "sleep":
        link.nap = True
        return "ok"
    if action == "wake":
        if switch_sleep:
            return "switch"
        link.nap = False
        return "ok"
    if pet.sleeping:
        return "sleeping"
    if action != "status":
        if pet.game:
            return "playing"
        if pet.rest and action != "pet":
            return "resting"
        if pet.cooldown:
            return "busy"
    pet.action(PET_EVENTS[action])
    if pet.effect_ms and pet.effect in ("full", "tired"):
        return pet.effect
    return "ok"


def render(pet, frame, elapsed):
    """Override the face only during actions, sleep or gameplay."""
    if pet.sleeping or pet.rest:
        draw_sleep(frame, elapsed)
        return
    if pet.game:
        for i in range(192):
            frame[i] = 0
        dot(frame, pet.star, pet.row, (255, 190, 50))
        dot(frame, pet.basket, 7, (80, 220, 160))
        dot(frame, pet.basket + 1, 7, (80, 220, 160))
        return
    if not pet.effect_ms:
        return
    effect = pet.effect
    if effect == "food" and pet.effect_ms < 1200:
        paint(frame, "neutral", talk=1 + (pet.effect_ms // 180) % 3)
    elif effect in ICONS:
        draw_icon(frame, effect)
    elif effect == "status":
        for i in range(192):
            frame[i] = 0
        for y, value, color in ((1, pet.food, (255, 160, 50)),
                                (3, pet.energy, (80, 170, 255)),
                                (5, pet.joy, (255, 90, 150))):
            for x in range(8):
                dot(frame, x, y, color if x < (value * 8 + 99) // 100 else (8, 8, 8))
    elif effect in ("full", "tired", "played"):
        paint(frame, "sad" if effect == "tired" else "neutral")


def run():
    controls = Controls(Button())
    pet = Pet()
    buddy = Animator()
    display = Display(20)
    link = Link()
    presses = DoublePress()
    switch_sleep = controls.sleeping
    frame = bytearray(192)
    previous = ticks_ms()
    elapsed = 0
    print("Pixel Buddy: oben=Futter, links=Pause, rechts=Spiel, unten=Status, Druck=Streicheln")
    print("Mit PC-Chat: Druck=Mikrofon an/aus, Doppeldruck=Streicheln.")
    print("Schiebeschalter: GPIO9 low=Schlaf, high=Tag. Im Spiel: links/rechts, Druck=Ende.")
    print("Timer laeuft ueber den Chat (\"Timer fuer 15 Minuten\"); Joystick stoppt den Alarm.")
    print("USB-Chat bereit: auf dem PC python -m companion_pc starten.")
    try:
        while True:
            start = ticks_ms()
            dt = max(0, ticks_diff(start, previous))
            previous = start
            elapsed = (elapsed + dt) % 3600
            events = controls.update(dt)
            if link.alarm_ms and events:
                link.alarm_ms = 0  # A joystick press ends the timer alarm; it is not an action.
                events = []
            if controls.sleeping != switch_sleep:
                switch_sleep = controls.sleeping
                link.nap = False  # Moving the switch always wins over chat sleep.
            if link.nap and events and not switch_sleep:
                link.nap = False  # Any joystick press wakes Buddy; the press is not an action.
                events = []
            if link.nap and pet.energy >= 100:
                link.nap = False  # Fully rested.
            if pet.game:
                presses.wait = 0  # In the game a press ends it at once, as before.
            else:
                events = presses.update(events, dt)
            if "mic" in events:
                events.remove("mic")
                if link.pc_active:
                    print(json.dumps({"event": "mic"}))
                else:
                    events.append("center")  # No PC chat: single press pets like before.
            pet.set_sleep(switch_sleep or link.nap)
            pet.update(dt)
            for event in events:
                pet.action(event)
                print("Buddy:", event, "| Futter", pet.food,
                      "Energie", pet.energy, "Laune", pet.joy,
                      "|", "Schlaf" if pet.sleeping else pet.mood)
            link.update(dt)
            if link.rang:
                link.rang = False
                print(json.dumps({"event": "timer"}))
            for line in link.read_lines():
                reply = link.handle(line)
                if link.action:
                    reply["result"] = apply_action(pet, link, switch_sleep)
                    pet.set_sleep(switch_sleep or link.nap)
                if pet.sleeping:
                    reply["note"] = "switch" if switch_sleep else "nap"
                reply["pet"] = [pet.food, pet.energy, pet.joy]
                print(json.dumps(reply))
            wanted = link.face or pet.mood
            if buddy.emotion != wanted:
                buddy.set_emotion(wanted)
            frame[:] = buddy.update(dt)
            render_link(link, frame)
            render(pet, frame, elapsed)
            render_timer(link, frame, link.mode != "idle" or link.talk_ms or pet.game or pet.effect_ms)
            display.show(frame)
            sleep_ms(max(0, 40 - ticks_diff(ticks_ms(), start)))
    except KeyboardInterrupt:
        print("Pixel Buddy beendet.")
    finally:
        display.clear()
