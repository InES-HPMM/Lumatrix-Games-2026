"""USB serial commands from the PC companion: one JSON object per line.

Only whitelisted commands and values are accepted; nothing is executed.
Reading is polled without blocking, so animations keep running.
"""
import json
import sys
from .faces import FACES

ANIMS = ("none", "wink", "heart", "star", "look", "sleepy", "note")
MAX_LINE = 160
MAX_CHARS_PER_FRAME = 256
THINK_MS = 120000  # Fallback to idle if the PC disappears while thinking.
MAX_TALK_MS = 60000  # Same fallback while the PC speaks.
LISTEN_MS = 20000  # Microphone indicator; the PC normally ends it sooner.
PC_TIMEOUT = 15000  # The PC pings every 5 s; without it the joystick works as before.
# Pet actions the PC may request; play.apply_action maps them to Pet.action.
ACTIONS = ("feed", "pet", "rest", "play", "status", "sleep", "wake")
MAX_TIMER_S = 99 * 60  # Two digits on the matrix.
ALARM_MS = 3000  # Blinking "0" when the timer ends, then back to the face.


class Link:
    def __init__(self, stream=None, poller=None):
        self.stream = stream or sys.stdin
        if poller is None:
            import select
            poller = select.poll()
            poller.register(self.stream, select.POLLIN)
        self.poller = poller
        self.buf = ""
        self.overflow = False
        self.mode = "idle"  # idle, listen, think or show
        self.face = None
        self.anim = "none"
        self.age = 0
        self.hold = 0
        self.talk_ms = 0  # >0 while the PC voice is speaking.
        self.talk_age = 0
        self.action = None  # Pending pet action, applied by the main loop.
        self.nap = False  # Sleep requested by chat; switch and joystick can end it.
        self.pc_age = PC_TIMEOUT  # ms since the last valid command from the PC.
        self.timer_ms = 0  # Countdown, keeps running without the PC.
        self.alarm_ms = 0
        self.rang = False  # Timer just ended; the main loop tells the PC.

    def read_lines(self):
        """Return complete lines received so far; bounded work per frame."""
        lines = []
        for _ in range(MAX_CHARS_PER_FRAME):
            if not self.poller.poll(0):
                break
            ch = self.stream.read(1)
            if not ch:
                break
            if ch in "\r\n":
                if self.buf and not self.overflow:
                    lines.append(self.buf)
                self.buf = ""
                self.overflow = False
            elif len(self.buf) < MAX_LINE:
                self.buf += ch
            else:
                self.overflow = True
        return lines

    def _start(self, mode, face, anim, hold):
        self.mode = mode
        self.face = face
        self.anim = anim
        self.age = 0
        self.hold = hold

    def handle(self, line):
        """Apply one command line and return a small JSON-serialisable reply."""
        try:
            msg = json.loads(line)
        except ValueError:
            return {"err": "json"}
        if not isinstance(msg, dict):
            return {"err": "json"}
        cmd = msg.get("cmd")
        self.pc_age = 0
        if cmd == "bye":
            self.pc_age = PC_TIMEOUT
            self.mode = "idle"
            self.face = None
            self.talk_ms = 0
            return {"ok": "bye"}
        if cmd == "ping":
            return {"ok": "ping", "faces": sorted(FACES), "anims": ANIMS}
        if cmd == "listen":
            self._start("listen", "neutral", "none", LISTEN_MS)
            self.talk_ms = 0
            return {"ok": "listen"}
        if cmd == "act":
            action = msg.get("action")
            if action not in ACTIONS:
                return {"err": "action"}
            self.action = action
            return {"ok": "act", "action": action}
        if cmd == "think":
            self._start("think", "neutral", "none", THINK_MS)
            self.talk_ms = 0
            return {"ok": "think"}
        if cmd == "idle":
            self.mode = "idle"
            self.face = None
            self.talk_ms = 0
            return {"ok": "idle"}
        if cmd == "talk":
            ms = msg.get("ms", 0)
            if not isinstance(ms, int):
                return {"err": "ms"}
            self.talk_ms = min(MAX_TALK_MS, max(0, ms))
            self.talk_age = 0
            return {"ok": "talk"}
        if cmd == "show":
            face = msg.get("face")
            if face not in FACES:
                return {"err": "face"}
            anim = msg.get("anim", "none")
            if anim not in ANIMS:
                anim = "none"
            ms = msg.get("ms", 5000)
            if not isinstance(ms, int):
                ms = 5000
            self._start("show", face, anim, min(15000, max(1000, ms)))
            return {"ok": "show", "face": face, "anim": anim}
        if cmd == "timer":
            # {"s": 900} starts (replaces), {"s": 0} cancels, no "s" only asks.
            was, ringing = self.timer_left(), self.alarm_ms > 0
            s = msg.get("s")
            if s is not None:
                if not isinstance(s, int) or not 0 <= s <= MAX_TIMER_S:
                    return {"err": "s"}
                self.timer_ms = s * 1000
                self.alarm_ms = 0
            return {"ok": "timer", "left": self.timer_left(), "was": was, "alarm": ringing}
        return {"err": "cmd"}

    def timer_left(self):
        return (self.timer_ms + 999) // 1000

    @property
    def pc_active(self):
        return self.pc_age < PC_TIMEOUT

    def update(self, dt):
        self.pc_age = min(PC_TIMEOUT, self.pc_age + dt)
        if self.talk_ms:
            self.talk_ms = max(0, self.talk_ms - dt)
            self.talk_age += dt
        if self.timer_ms:
            self.timer_ms = max(0, self.timer_ms - dt)
            if not self.timer_ms:
                self.alarm_ms = ALARM_MS
                self.rang = True
        elif self.alarm_ms:
            self.alarm_ms = max(0, self.alarm_ms - dt)
        if self.mode == "idle":
            return
        self.age += dt
        if self.talk_ms and self.mode == "show":
            # Keep the emotion while speaking, then 1.5 s more.
            self.hold = max(self.hold, self.age + 1500)
        if self.age >= self.hold:
            self.mode = "idle"
            self.face = None
