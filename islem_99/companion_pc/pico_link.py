"""USB serial link to the Pico via pyserial, with auto-detect and reconnect.

Protocol: one ASCII JSON object per line in both directions.
PC -> Pico: {"cmd": "ping" | "think" | "idle"}, {"cmd": "talk", "ms": ...} or
            {"cmd": "show", "face": ..., "anim": ..., "ms": ...}, {"cmd": "timer", "s": ...}
Pico -> PC: {"ok": ...} / {"err": ...}, {"event": "mic" | "timer"}; other lines are normal Pico prints.
"""
import json
import threading
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # Chat still works without LEDs.
    serial = None

PICO_VID = 0x2E8A  # Raspberry Pi (RP2040 / MicroPython USB CDC)
RETRY_S = 2.0
PING_WAIT_S = 3.0
HEARTBEAT_S = 5.0  # Tells the Pico a chat is running (joystick press = microphone).


RESULTS = {
    "full": "Buddy ist satt.",
    "tired": "Buddy hat zu wenig Energie oder Futter zum Spielen.",
    "busy": "Buddy ist noch mit der letzten Aktion beschaeftigt.",
    "playing": "Buddy spielt gerade (Joystick links/rechts, Druck beendet).",
    "resting": "Buddy macht gerade Pause.",
    "sleeping": "Buddy schlaeft - zuerst 'wach auf' sagen.",
    "switch": "Der Schiebeschalter steht auf Schlaf - zum Aufwecken umlegen.",
}


class PicoUnavailable(Exception):
    pass


def find_pico_ports():
    if serial is None:
        return []
    return sorted(p.device for p in list_ports.comports() if p.vid == PICO_VID)


class PicoLink:
    def __init__(self, port=None, debug=False, log=print):
        if serial is None:
            raise PicoUnavailable("pyserial fehlt. Installieren: python -m pip install pyserial")
        self.port_arg = port
        self.debug = debug
        self.log = log
        self.port = None
        self.ser = None
        self.ready = False  # True once the Pico answered a ping.
        self.sleeping = False
        self.pet = None  # Latest (food, energy, joy, sleeping) reported by the Pico.
        self.act_result = None
        self.act_done = threading.Event()
        self.mic_events = 0  # Joystick presses not yet handled by the chat.
        self.timer_events = 0  # Timers that ended on the Pico, not yet announced.
        self.timer_total = None  # Length of the last timer started in this session.
        self.waiting = None  # Command whose reply call() waits for.
        self.reply = None
        self.reply_done = threading.Event()
        self.lock = threading.Lock()
        self.write_lock = threading.Lock()  # chat and voice thread both send
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._run, name="pico-link", daemon=True)
        self._last_problem = None

    def start(self):
        self.thread.start()
        return self

    def mic_pressed(self):
        """True once per joystick press (Pico event {"event": "mic"})."""
        with self.lock:
            pressed, self.mic_events = self.mic_events > 0, 0
        return pressed

    def timer_pending(self):
        return self.timer_events > 0

    def timer_rang(self):
        """True once per ended timer (Pico event {"event": "timer"})."""
        with self.lock:
            rang, self.timer_events = self.timer_events > 0, 0
        return rang

    def call(self, msg, timeout=1.0):
        """Send a command and wait for its {"ok": <cmd>} or {"err": ...} reply; None if none."""
        with self.lock:
            self.waiting, self.reply = msg["cmd"], None
            self.reply_done.clear()
        if not self.send(msg):
            return None
        self.reply_done.wait(timeout)
        with self.lock:
            self.waiting = None
            return self.reply

    def close(self):
        self.send({"cmd": "bye"})  # Joystick press is petting again without the chat.
        self.stopping.set()
        self._drop(None)
        self.thread.join(timeout=2)

    def wait_ready(self, timeout):
        end = time.monotonic() + timeout
        while not self.ready and time.monotonic() < end:
            time.sleep(0.05)
        return self.ready

    def act(self, action, timeout=1.0):
        """Run a pet action and wait briefly for its result ('ok', 'full', ...)."""
        self.act_done.clear()
        self.act_result = None
        if not self.send({"cmd": "act", "action": action}):
            return None
        self.act_done.wait(timeout)
        return self.act_result

    def status(self):
        if self.ser is None:
            return "nicht verbunden" + (" ({})".format(self._last_problem) if self._last_problem else "")
        if not self.ready:
            return "{} offen, aber keine Antwort vom Pico".format(self.port)
        return "{} verbunden{}".format(self.port, ", Buddy schlaeft (Schalter)" if self.sleeping else "")

    def send(self, msg):
        """Send one command; returns False instead of raising when disconnected."""
        data = (json.dumps(msg, separators=(",", ":")) + "\n").encode("ascii")
        with self.lock:
            ser = self.ser
        if ser is None:
            return False
        try:
            with self.write_lock:
                ser.write(data)
                ser.flush()
        except (serial.SerialException, OSError) as exc:
            self._drop("Schreibfehler: {}".format(exc))
            return False
        if self.debug and msg.get("cmd") != "ping":
            self.log("[Pico <-] " + data.decode().strip())
        return True

    # Background thread -------------------------------------------------

    def _problem(self, text):
        # Report each distinct problem once instead of spamming every retry.
        if text != self._last_problem:
            self._last_problem = text
            self.log("[Pico] " + text)

    def _choose_port(self):
        if self.port_arg:
            return self.port_arg
        ports = find_pico_ports()
        if not ports:
            raise PicoUnavailable("kein Pico gefunden (USB-Kabel? --pico-port COMx)")
        if len(ports) > 1:
            raise PicoUnavailable("mehrere Picos gefunden: {} -> --pico-port waehlen".format(", ".join(ports)))
        return ports[0]

    def _open(self):
        port = self._choose_port()
        try:
            ser = serial.Serial(port, 115200, timeout=0.2, write_timeout=1)
        except serial.SerialException as exc:
            text = str(exc)
            if "Access is denied" in text or "PermissionError" in text or "Zugriff verweigert" in text:
                raise PicoUnavailable(port + " ist belegt. Laeuft python -m companion_pc schon in einem "
                                      "anderen Terminal? Sonst MicroPico (Disconnect), Thonny oder "
                                      "Serial-Monitor schliessen.") from exc
            raise PicoUnavailable("{} nicht zu oeffnen: {}".format(port, text)) from exc
        with self.lock:
            self.ser = ser
            self.port = port
            self.ready = False
        self._last_problem = None
        self.log("[Pico] verbunden mit " + port)

    def _drop(self, reason):
        with self.lock:
            ser, self.ser, self.ready = self.ser, None, False
        if ser is not None:
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass
            if reason and not self.stopping.is_set():
                self.log("[Pico] Verbindung verloren ({}). Neuer Versuch ...".format(reason))

    def _run(self):
        ping_at = 0.0
        heartbeat_at = 0.0
        warned = False
        while not self.stopping.is_set():
            if self.ser is None:
                try:
                    self._open()
                except PicoUnavailable as exc:
                    self._problem(str(exc))
                    self.stopping.wait(RETRY_S)
                    continue
                self.send({"cmd": "ping"})
                ping_at = time.monotonic()
                warned = False
            if self.ready and time.monotonic() - heartbeat_at > HEARTBEAT_S:
                heartbeat_at = time.monotonic()
                self.send({"cmd": "ping"})
            ser = self.ser
            try:
                raw = ser.readline() if ser is not None else b""
            except (serial.SerialException, OSError, TypeError, AttributeError) as exc:
                self._drop(str(exc) or type(exc).__name__)
                continue
            if raw:
                self._handle(raw.decode("utf-8", errors="replace").strip())
            elif not self.ready and not warned and time.monotonic() - ping_at > PING_WAIT_S:
                warned = True
                self.log("[Pico] keine Antwort. Laeuft der neue Code? Projekt hochladen, "
                         "MicroPico trennen und Pico neu einstecken (main.py startet dann automatisch).")

    def _handle(self, line):
        if not line:
            return
        if line.startswith(">>>") or line.startswith("MicroPython"):
            self._problem("Pico ist im REPL, main.py laeuft nicht. Pico neu einstecken.")
            return
        try:
            msg = json.loads(line)
        except ValueError:
            msg = None
        if not isinstance(msg, dict):
            if self.debug:
                self.log("[Pico] " + line)
            return
        if msg.get("event") in ("mic", "timer"):
            with self.lock:
                if msg["event"] == "mic":
                    self.mic_events += 1
                else:
                    self.timer_events += 1
            if self.debug:
                self.log("[Pico ->] " + line)
            return
        if "ok" in msg:
            if not self.ready:
                self.ready = True
                self.log("[Pico] bereit." + (" Gesichter: " + ", ".join(msg["faces"])
                                             if isinstance(msg.get("faces"), list) else ""))
            was_sleeping = self.sleeping
            self.sleeping = msg.get("note") in ("switch", "nap")
            if msg.get("note") == "switch" and not was_sleeping:
                self.log("[Pico] Buddy schlaeft gerade (Schiebeschalter) - Emotionen erst nach dem Aufwecken sichtbar.")
            pet = msg.get("pet")
            if isinstance(pet, list) and len(pet) == 3 and all(isinstance(v, int) for v in pet):
                self.pet = (pet[0], pet[1], pet[2], self.sleeping)
            with self.lock:
                if self.waiting and msg.get("ok") == self.waiting:
                    self.reply = msg
                    self.reply_done.set()
            if msg.get("ok") == "act":
                self.act_result = msg.get("result")
                self.act_done.set()
            if self.debug and msg.get("ok") != "ping":
                self.log("[Pico ->] " + line)
        elif "err" in msg:
            with self.lock:
                if self.waiting:
                    self.reply = msg
                    self.reply_done.set()
            self.log("[Pico] Befehl abgelehnt: " + str(msg["err"]))
