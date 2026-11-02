"""Chat actions (feed, sleep, ...) and speech input endpointing / transcription."""
import importlib
import json
import os
import sys
import time
import types
import unittest
import wave
from unittest.mock import patch

from companion_pc.conversation import Conversation
from companion_pc.actions import ACTIONS, describe_event, detect_action
from companion_pc.emotions import describe_pet
from companion_pc.listen import find_speech
from pixel_buddy.link import ACTIONS as PICO_ACTIONS, Link
from pixel_buddy.pet import Pet


class NoInput:
    def poll(self, timeout):
        return []


def load_play():
    fake_driver = types.ModuleType("zhaw_led_matrix")
    fake_driver.Button = fake_driver.LedMatrix = object
    with patch.dict(sys.modules, {"zhaw_led_matrix": fake_driver}), \
         patch.object(time, "ticks_ms", lambda: 0, create=True), \
         patch.object(time, "ticks_diff", lambda a, b: a - b, create=True), \
         patch.object(time, "sleep_ms", lambda _: None, create=True):
        sys.modules.pop("pixel_buddy.play", None)
        play = importlib.import_module("pixel_buddy.play")
    sys.modules.pop("pixel_buddy.play", None)
    return play


class PicoActionTests(unittest.TestCase):
    def setUp(self):
        self.play = load_play()
        self.link = Link(object(), NoInput())
        self.pet = Pet()

    def act(self, action, switch_sleep=False):
        reply = self.link.handle(json.dumps({"cmd": "act", "action": action}))
        self.assertEqual(reply, {"ok": "act", "action": action})
        result = self.play.apply_action(self.pet, self.link, switch_sleep)
        self.pet.set_sleep(switch_sleep or self.link.nap)
        return result

    def test_vocabularies_match(self):
        self.assertEqual(set(ACTIONS), set(PICO_ACTIONS))
        self.assertEqual(set(self.play.PET_EVENTS), set(PICO_ACTIONS) - {"sleep", "wake"})

    def test_feed_reuses_joystick_action_and_reports_full(self):
        self.pet.food = 50
        self.assertEqual(self.act("feed"), "ok")
        self.assertEqual((self.pet.food, self.pet.effect), (70, "food"))
        self.assertEqual(self.act("feed"), "busy")  # same 2.2 s cooldown as the joystick
        self.pet.update(2400)
        self.pet.food = 96
        self.assertEqual(self.act("feed"), "full")
        self.assertEqual(self.pet.food, 96)

    def test_pet_rest_play_status(self):
        joy = self.pet.joy
        self.assertEqual(self.act("pet"), "ok")
        self.assertEqual(self.pet.joy, joy + 8)
        self.pet.update(2400)
        self.assertEqual(self.act("rest"), "ok")
        self.assertTrue(self.pet.rest)
        self.assertEqual(self.act("feed"), "resting")
        self.assertEqual(self.act("status"), "ok")
        self.pet.rest = 0
        self.pet.update(2400)
        self.pet.energy = 10
        self.assertEqual(self.act("play"), "tired")
        self.pet.update(2400)
        self.pet.energy = 80
        self.assertEqual(self.act("play"), "ok")
        self.assertTrue(self.pet.game)
        self.assertEqual(self.act("feed"), "playing")

    def test_sleep_and_wake(self):
        self.assertEqual(self.act("sleep"), "ok")
        self.assertTrue(self.link.nap and self.pet.sleeping)
        self.assertEqual(self.act("feed"), "sleeping")
        self.assertEqual(self.act("wake", switch_sleep=True), "switch")
        self.assertEqual(self.act("wake"), "ok")
        self.assertFalse(self.link.nap or self.pet.sleeping)

    def test_unknown_action_rejected(self):
        self.assertEqual(self.link.handle('{"cmd":"act","action":"reboot"}'), {"err": "action"})
        self.assertIsNone(self.link.action)

    def test_listen_indicator(self):
        self.link.handle('{"cmd":"listen"}')
        frames = set()
        for age in range(0, 1200, 100):
            self.link.age = age
            frame = bytearray(192)
            self.play.render_link(self.link, frame)
            self.assertEqual(frame[96:120], bytes(24))
            frames.add(bytes(frame[:3]))
        self.assertGreater(len(frames), 3)  # pulsing corner "ear"
        self.link.update(20000)
        self.assertEqual(self.link.mode, "idle")


DETECT_CASES = (
    ("Buddy, du siehst müde aus. Geh jetzt schlafen.", "sleep"),
    ("Badi! Du siehst müde aus. Geh jetzt schlafen.", "sleep"),
    ("Hey buddy, are you hungry? Here is an apple for you.", "feed"),
    ("Hier, iss einen Keks!", "feed"), ("Buddy, eat this cookie!", "feed"),
    ("Möchtest du einen Apfel?", "feed"), ("Komm her, ich streichle dich.", "pet"),
    ("Gib mir eine Umarmung!", "pet"), ("Can I pet you?", "pet"),
    ("Wach auf, Schlafmütze!", "wake"), ("Guten Morgen Buddy!", "wake"),
    ("Lass uns spielen!", "play"), ("Wollen wir spielen?", "play"), ("Lets play a game", "play"),
    ("Wie geht es dir? Zeig mir deinen Status.", "status"), ("Mach mal kurz Pause.", "rest"),
    ("Ruh dich kurz aus.", "rest"), ("Gute Nacht, Buddy!", "sleep"), ("Schlaf gut!", "sleep"),
    ("Time for bed, little one.", "sleep"),
    # Stories, feelings and negations must not trigger anything.
    ("Ich habe heute Pizza gegessen.", None), ("Ich bin so müde heute.", None),
    ("What's your favourite colour?", None), ("I eat pizza every day.", None),
    ("I want pizza.", None), ("I have a banana.", None), ("Geh nicht schlafen!", None),
    ("Ich kaufe Futter für die Katze.", None), ("Ich habe meine Prüfung bestanden!", None),
    ("Ich gehe jetzt schlafen.", None),
)


class PcActionTests(unittest.TestCase):
    def test_detect_action(self):
        for text, expected in DETECT_CASES:
            self.assertEqual(detect_action(text), expected, text)

    def test_event_lines(self):
        self.assertEqual(describe_event(None), "")
        self.assertIn("ate it", describe_event("feed", "ok"))
        self.assertIn("full", describe_event("feed", "full"))
        self.assertIn("falling asleep", describe_event("sleep", None))  # no Pico

    def test_pet_state_and_event_in_prompt(self):
        self.assertEqual(describe_pet(None), "")
        line = describe_pet((96, 20, 50, False))
        self.assertIn("food 96/100", line)
        self.assertIn("refuse more food", line)
        self.assertIn("very tired", line)

        class Client:
            def chat(self, messages, schema):
                self.messages = messages
                return json.dumps({"reply": "Gute Nacht!", "emotion": "sleepy",
                                   "animation": "sleepy", "intensity": 0.5})
        client = Client()
        Conversation(client).send("Geh schlafen", (50, 20, 60, False), describe_event("sleep", "ok"))
        system = client.messages[0]["content"]
        self.assertIn("energy 20/100", system)
        self.assertTrue(system.endswith("What just happened: You are falling asleep now."))


class EndpointTests(unittest.TestCase):
    def test_speech_then_pause_ends_recording(self):
        levels = [0.002] * 10
        self.assertEqual(find_speech(levels)[0], "more")
        levels += [0.1] * 40  # 1.2 s speech
        self.assertEqual(find_speech(levels)[0], "more")
        levels += [0.002] * 29
        self.assertEqual(find_speech(levels)[0], "more")
        levels += [0.002]  # 900 ms silence reached
        self.assertEqual(find_speech(levels), ("done", len(levels)))

    def test_nobody_speaks_or_clicks(self):
        levels = [0.002] * 10 + [0.2] * 2 + [0.002] * 222  # short click only
        self.assertEqual(find_speech(levels)[0], "silent")

    def test_max_length(self):
        levels = [0.002] * 10 + [0.1] * 490
        self.assertEqual(find_speech(levels)[0], "done")


SAMPLES = os.environ.get("BUDDY_STT_SAMPLES")


@unittest.skipUnless(SAMPLES, "set BUDDY_STT_SAMPLES to a folder with stt_de.wav / stt_en.wav")
class WhisperTests(unittest.TestCase):
    def test_transcribes_german_and_english(self):
        import numpy as np
        from companion_pc.listen import Listener
        listener = Listener.__new__(Listener)  # skip the microphone check
        listener.np, listener.log, listener.model_name, listener.model, listener.error = np, print, "base", None, None
        import threading
        listener.loaded = threading.Event()
        listener._load()
        for name, lang, word in (("stt_de.wav", "de", "schlafen"), ("stt_en.wav", "en", "apple")):
            with wave.open(os.path.join(SAMPLES, name)) as w:
                audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
            text, detected = listener.transcribe(audio)
            self.assertEqual(detected, lang)
            self.assertIn(word, text.lower())


if __name__ == "__main__":
    unittest.main()


class RecordStopTests(unittest.TestCase):
    """Enter during recording ends it at once (and is consumed, not buffered)."""

    def make_listener(self, level):
        import numpy as np
        from companion_pc.listen import Listener

        class Stream:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, n):
                return np.full((n, 1), level, np.float32), False

        listener = Listener.__new__(Listener)
        listener.np = np
        listener.sd = types.SimpleNamespace(InputStream=lambda **kw: Stream(), PortAudioError=OSError)
        return listener

    def test_enter_stops_recording(self):
        calls = []

        def stop():
            calls.append(1)
            return len(calls) >= 40  # "Enter" after 1.2 s of constant speech
        audio = self.make_listener(0.2).record(stop)
        self.assertEqual(len(audio), 40 * 480)

    def test_early_enter_without_audio_returns_none(self):
        self.assertIsNone(self.make_listener(0.2).record(lambda: True))

    def test_without_stop_silence_times_out(self):
        self.assertIsNone(self.make_listener(0.0).record())
