"""Automatic showcase only; no sensors, AI, mood or energy simulation."""
from time import ticks_ms, ticks_diff, sleep_ms
from .animation import Animator
from .display import Display
from .faces import ORDER

BRIGHTNESS = 20
FRAME_MS = 40
EMOTION_MS = 8000


def run():
    display = Display(BRIGHTNESS)
    buddy = Animator()
    index = 0
    elapsed = 0
    previous = ticks_ms()
    print("Pixel Buddy: neutral (Ctrl+C beendet die Demo)")
    try:
        while True:
            start = ticks_ms()
            dt = max(0, ticks_diff(start, previous))
            previous = start
            elapsed += dt
            if elapsed >= EMOTION_MS:
                elapsed %= EMOTION_MS
                index = (index + 1) % len(ORDER)
                buddy.set_emotion(ORDER[index])
                print("Pixel Buddy:", ORDER[index])
            display.show(buddy.update(dt))
            sleep_ms(max(0, FRAME_MS - ticks_diff(ticks_ms(), start)))
    except KeyboardInterrupt:
        print("Pixel Buddy: Demo beendet.")
    finally:
        display.clear()
