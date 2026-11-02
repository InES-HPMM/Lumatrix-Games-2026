"""Animation with reusable frames; caller supplies elapsed milliseconds."""
from random import getrandbits
from .faces import paint, FACES


class Animator:
    TRANSITION_MS = 480

    def __init__(self):
        self.frame = bytearray(192)
        self.source = bytearray(192)
        self.target = bytearray(192)
        self.emotion = "neutral"
        self.age = 0
        self.transition = self.TRANSITION_MS
        self.next_blink = 2300
        self.blink_age = -1
        self.next_look = 1500
        self.look_age = -1
        self.gaze = 0
        paint(self.frame, "neutral")

    def set_emotion(self, emotion):
        if emotion not in FACES:
            raise ValueError("Unknown emotion: " + str(emotion))
        self.source[:] = self.frame
        self.emotion = emotion
        self.age = 0
        self.transition = 0
        self.blink_age = -1
        self.next_blink = 1800 + getrandbits(12) % 2500
        self.next_look = 1200
        self.look_age = -1
        self.gaze = 0

    def update(self, dt):
        self.age += dt
        self.transition = min(self.TRANSITION_MS, self.transition + dt)
        self.next_blink -= dt
        if self.blink_age < 0 and self.next_blink <= 0:
            self.blink_age = 0
            self.next_blink = 2600 + getrandbits(12)
        lid = 0
        if self.blink_age >= 0:
            self.blink_age += dt
            if self.blink_age < 55:
                lid = 1
            elif self.blink_age < 155:
                lid = 2
            elif self.blink_age < 230:
                lid = 1
            else:
                self.blink_age = -1

        self.next_look -= dt
        if self.next_look <= 0:
            self.gaze = -1 if getrandbits(1) else 1
            self.look_age = 0
            self.next_look = 2200 + getrandbits(11)
        if self.look_age >= 0:
            self.look_age += dt
            if self.look_age >= 650:
                self.gaze = 0
                self.look_age = -1

        phase = self.age % 3600
        breath = 88 + (phase if phase < 1800 else 3600 - phase) * 12 // 1800
        wink = self.emotion == "happy" and 5200 <= self.age < 5450
        # The mouth stays still; it only moves while the PC voice speaks (play.render_link).
        paint(self.target, self.emotion, lid, self.gaze, breath, wink)

        # Smoothstep crossfade; never clear the LEDs between drawing operations.
        t = self.transition * 256 // self.TRANSITION_MS
        mix = t * t * (768 - 2 * t) // 65536
        for i in range(192):
            self.frame[i] = (self.source[i] * (256 - mix) + self.target[i] * mix) // 256
        return self.frame
