"""USB protocol tests: Pico command parser, chat overlays and the PC serial link."""
import importlib
import json
import queue
import sys
import time
import types
import unittest
from unittest.mock import patch

from companion_pc import pico_link
from companion_pc.conversation import detect_language
from companion_pc.emotions import EMOTIONS, parse, show_command
from pixel_buddy.faces import FACES
from pixel_buddy.link import ANIMS, Link


class FakeStream:
    def __init__(self, text=""):
        self.data = text

    def read(self, n):
        ch, self.data = self.data[:n], self.data[n:]
        return ch


class FakePoller:
    def __init__(self, stream):
        self.stream = stream

    def poll(self, timeout):
        return [1] if self.stream.data else []


def make_link(text=""):
    stream = FakeStream(text)
    return Link(stream, FakePoller(stream)), stream


class PicoProtocolTests(unittest.TestCase):
    def test_lines_are_split_and_bounded(self):
        link, stream = make_link('{"cmd":"ping"}\r\n' + "x" * 400 + '\n{"cmd":"idle"}\npartial')
        lines = []
        for _ in range(5):
            lines += link.read_lines()
        self.assertEqual(lines, ['{"cmd":"ping"}', '{"cmd":"idle"}'])
        self.assertEqual(link.buf, "partial")

    def test_show_think_idle_and_timeout(self):
        link, _ = make_link()
        self.assertEqual(link.handle('{"cmd":"think"}'), {"ok": "think"})
        self.assertEqual((link.mode, link.face), ("think", "neutral"))
        reply = link.handle('{"cmd":"show","face":"happy","anim":"star","ms":3000}')
        self.assertEqual(reply["ok"], "show")
        self.assertEqual((link.face, link.anim), ("happy", "star"))
        link.update(2999)
        self.assertEqual(link.face, "happy")
        link.update(1)
        self.assertEqual((link.mode, link.face), ("idle", None))
        link.handle('{"cmd":"think"}')
        link.handle('{"cmd":"idle"}')
        self.assertIsNone(link.face)

    def test_rejects_unknown_or_unsafe_input(self):
        link, _ = make_link()
        self.assertEqual(link.handle("import os"), {"err": "json"})
        self.assertEqual(link.handle("[1,2]"), {"err": "json"})
        self.assertEqual(link.handle('{"cmd":"exec","code":"print(1)"}'), {"err": "cmd"})
        self.assertEqual(link.handle('{"cmd":"show","face":"angry"}'), {"err": "face"})
        link.handle('{"cmd":"show","face":"sad","anim":"explode","ms":999999}')
        self.assertEqual((link.anim, link.hold), ("none", 15000))
        link.handle('{"cmd":"show","face":"sad","ms":"5"}')
        self.assertEqual(link.hold, 5000)
        self.assertEqual(link.mode, "show")

    def test_pc_vocabulary_matches_pico(self):
        for emotion in EMOTIONS:
            command = show_command(emotion)
            self.assertIn(command["face"], FACES)
            self.assertIn(command["anim"], ANIMS)
            link, _ = make_link()
            self.assertEqual(link.handle(json.dumps(command))["ok"], "show")


class OverlayTests(unittest.TestCase):
    def setUp(self):
        fake_driver = types.ModuleType("zhaw_led_matrix")
        fake_driver.Button = fake_driver.LedMatrix = object
        with patch.dict(sys.modules, {"zhaw_led_matrix": fake_driver}), \
             patch.object(time, "ticks_ms", lambda: 0, create=True), \
             patch.object(time, "ticks_diff", lambda a, b: a - b, create=True), \
             patch.object(time, "sleep_ms", lambda _: None, create=True):
            sys.modules.pop("pixel_buddy.play", None)
            self.play = importlib.import_module("pixel_buddy.play")
        sys.modules.pop("pixel_buddy.play", None)

    def frame_at(self, link, age):
        link.age = age
        frame = bytearray(192)
        self.play.render_link(link, frame)
        return bytes(frame)

    def test_thinking_moves_and_keeps_gap_dark(self):
        link, _ = make_link()
        link.handle('{"cmd":"think"}')
        frames = {self.frame_at(link, age) for age in range(0, 3200, 110)}
        self.assertGreater(len(frames), 2)  # gaze left/centre/right and blink
        for frame in frames:
            self.assertEqual(frame[96:120], bytes(24))
        self.assertEqual(len({frame[120:] for frame in frames}), 1)  # mouth never moves

    def test_animations_draw_then_hand_back_to_face(self):
        link, _ = make_link()
        for anim, during, after in (("heart", 100, 1700), ("star", 100, 1700),
                                    ("look", 100, 2500),
                                    ("wink", 600, 900)):
            link.handle(json.dumps({"cmd": "show", "face": "happy", "anim": anim}))
            self.assertNotEqual(self.frame_at(link, during), bytes(192), anim)
            self.assertEqual(self.frame_at(link, after), bytes(192), anim)
        link.handle('{"cmd":"show","face":"neutral","anim":"sleepy"}')
        self.assertNotEqual(self.frame_at(link, 4000), bytes(192))
        link.handle('{"cmd":"idle"}')
        self.assertEqual(self.frame_at(link, 0), bytes(192))


class LanguageTests(unittest.TestCase):
    def test_detect_language_keeps_previous_on_tie(self):
        self.assertEqual(detect_language("Ich bin müde"), "de")
        self.assertEqual(detect_language("What do you think?", "de"), "en")
        self.assertEqual(detect_language("haha ok", "en"), "en")
        self.assertEqual(detect_language("Prüfung!", "en"), "de")


class EmotionParseTests(unittest.TestCase):
    def test_defaults_for_broken_values(self):
        result = parse('{"reply":" Hi ","emotion":42,"animation":null,"intensity":true}')
        self.assertEqual(result["reply"], "Hi")
        self.assertEqual((result["emotion"], result["animation"], result["intensity"]),
                         ("neutral", "none", 0.6))
        self.assertEqual(result["fixed"], ["emotion", "animation", "intensity"])
        self.assertEqual(parse('{"reply":"x","emotion":"sad","animation":"none","intensity":-3}')["intensity"], 0.0)
        self.assertEqual(parse("Hallo du")["reply"], "Hallo du")


class FakeSerial:
    instances = []

    def __init__(self, port, baud, timeout, write_timeout):
        self.port = port
        self.written = []
        self.incoming = queue.Queue()
        self.fail = False
        FakeSerial.instances.append(self)

    def write(self, data):
        self.written.append(data)
        msg = json.loads(data)
        if msg["cmd"] == "ping":
            self.incoming.put(b'{"ok":"ping","faces":["happy","neutral","sad"]}\r\n')

    def flush(self):
        pass

    def readline(self):
        if self.fail:
            raise pico_link.serial.SerialException("device disconnected")
        try:
            return self.incoming.get(timeout=0.02)
        except queue.Empty:
            return b""

    def close(self):
        pass


def wait_for(condition):
    end = time.monotonic() + 2
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


@unittest.skipIf(pico_link.serial is None, "pyserial not installed")
class PicoLinkTests(unittest.TestCase):
    def test_connect_send_and_reconnect(self):
        FakeSerial.instances = []
        logs = []
        with patch.object(pico_link.serial, "Serial", FakeSerial), \
             patch.object(pico_link, "find_pico_ports", lambda: ["COM9"]), \
             patch.object(pico_link, "RETRY_S", 0.05):
            link = pico_link.PicoLink(log=logs.append).start()
            try:
                self.assertTrue(wait_for(lambda: link.ready))
                self.assertIn("COM9 verbunden", link.status())
                self.assertTrue(link.send({"cmd": "think"}))
                self.assertEqual(FakeSerial.instances[0].written[-1], b'{"cmd":"think"}\n')
                FakeSerial.instances[0].incoming.put(
                    b'{"ok":"act","action":"feed","result":"full","note":"nap","pet":[96,40,70]}\n')
                self.assertTrue(wait_for(lambda: link.sleeping))
                self.assertEqual(link.pet, (96, 40, 70, True))
                self.assertEqual(link.act_result, "full")
                FakeSerial.instances[0].fail = True
                self.assertTrue(wait_for(lambda: len(FakeSerial.instances) == 2 and link.ready))
                self.assertTrue(any("Verbindung verloren" in line for line in logs))
            finally:
                link.close()
        self.assertEqual(FakeSerial.instances[-1].written[-1], b'{"cmd":"bye"}\n')
        self.assertFalse(link.send({"cmd": "idle"}))

    def test_missing_and_busy_port_are_reported(self):
        def busy(*args, **kwargs):
            raise pico_link.serial.SerialException("could not open port 'COM9': PermissionError(13, 'Access is denied.')")
        logs = []
        with patch.object(pico_link, "find_pico_ports", lambda: []):
            link = pico_link.PicoLink(log=logs.append)
            with self.assertRaisesRegex(pico_link.PicoUnavailable, "kein Pico"):
                link._open()
        with patch.object(pico_link.serial, "Serial", busy):
            link = pico_link.PicoLink(port="COM9", log=logs.append)
            with self.assertRaisesRegex(pico_link.PicoUnavailable, "belegt"):
                link._open()


if __name__ == "__main__":
    unittest.main()


class TalkTests(unittest.TestCase):
    def test_talk_keeps_emotion_until_voice_is_done(self):
        link, _ = make_link()
        link.handle('{"cmd":"show","face":"happy","anim":"none","ms":3000}')
        self.assertEqual(link.handle('{"cmd":"talk","ms":60000}'), {"ok": "talk"})
        for _ in range(250):  # 10 s of speech, longer than the 3 s hold
            link.update(40)
        self.assertEqual((link.mode, link.face), ("show", "happy"))
        link.handle('{"cmd":"talk","ms":0}')
        link.update(1400)
        self.assertEqual(link.face, "happy")
        link.update(200)
        self.assertEqual(link.mode, "idle")
        self.assertEqual(link.handle('{"cmd":"talk","ms":"x"}'), {"err": "ms"})
        link.handle('{"cmd":"talk","ms":999999}')
        self.assertEqual(link.talk_ms, 60000)
        link.handle('{"cmd":"think"}')
        self.assertEqual(link.talk_ms, 0)


class TalkOverlayTests(unittest.TestCase):
    setUp = OverlayTests.setUp

    def test_mouth_moves_and_eyes_keep_emotion(self):
        link, _ = make_link()
        link.handle('{"cmd":"show","face":"happy","anim":"none"}')
        link.handle('{"cmd":"talk","ms":5000}')
        base = bytearray(192)
        from pixel_buddy.faces import paint
        paint(base, "happy")
        mouths = set()
        for step in range(8):
            link.talk_age = step * 150
            frame = bytearray(base)
            self.play.render_link(link, frame)
            self.assertEqual(frame[:120], base[:120])  # eyes and dark gap unchanged
            mouths.add(bytes(frame[120:168]))
        self.assertEqual(len(mouths), 4)
        link.handle('{"cmd":"talk","ms":0}')
        frame = bytearray(base)
        self.play.render_link(link, frame)
        self.assertEqual(frame, base)


class VoiceTextTests(unittest.TestCase):
    def test_clean_text_and_ssml(self):
        from companion_pc.voice import build_ssml, clean_text, pick_voice
        self.assertEqual(clean_text("Yaaay! \U0001F389✨ *hüpft* Du bist toll ❤️"), "Yaaay! Du bist toll")
        ssml = build_ssml("Tom & Jerry <3", "de-DE")
        self.assertIn("Tom &amp; Jerry &lt;3", ssml)
        self.assertIn('xml:lang="de-DE"', ssml)
        voices = {"Microsoft David Desktop": "en-US", "Microsoft Zira Desktop": "en-US",
                  "Microsoft Hedda Desktop": "de-DE"}
        self.assertEqual(pick_voice(voices, "en")[0], "Microsoft Zira Desktop")
        self.assertEqual(pick_voice(voices, "de"), ("Microsoft Hedda Desktop", "de-DE"))
        self.assertEqual(pick_voice({"X": "fr-FR"}, "de")[0], "X")


@unittest.skipUnless(sys.platform == "win32", "Windows speech only")
class VoiceHelperTests(unittest.TestCase):
    def test_real_helper_speaks_silently_and_reports_done(self):
        from companion_pc.voice import Voice
        import threading
        logs = []
        voice = Voice(log=logs.append, silent=True)
        try:
            self.assertTrue(voice.voices)
            done = threading.Event()
            voice.say("Hallo, ich bin Pixel Buddy!", "de", done.set)
            self.assertTrue(voice.speaking)
            self.assertTrue(done.wait(20))
            self.assertFalse(voice.speaking)
            stopped = threading.Event()
            voice.say("Das ist ein langer Satz, der gleich unterbrochen wird. " * 5, "en", stopped.set)
            voice.stop()
            self.assertTrue(stopped.is_set())
            again = threading.Event()
            voice.say("Weiter geht's.", "de", again.set)  # helper restarts after stop
            self.assertTrue(again.wait(20))
            self.assertEqual(logs, [])
        finally:
            voice.close()
