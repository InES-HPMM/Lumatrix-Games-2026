"""Timer: voice commands on the PC, countdown and display on the Pico."""
import json
import unittest

from companion_pc import timer
from companion_pc.music import detect_music
from companion_pc.actions import detect_action
from pixel_buddy.link import ALARM_MS, MAX_TIMER_S, Link
from test_actions import NoInput, load_play


class DetectTests(unittest.TestCase):
    def test_start_phrases(self):
        cases = (("Buddy, stell einen Timer für 15 Minuten.", 900),
                 ("Stell einen Timer auf fünf Minuten", 300),
                 ("Timer fünfundzwanzig Minuten", 1500),
                 ("Timer für eine halbe Stunde", 1800),
                 ("Mach einen Timer für eine Viertelstunde", 900),
                 ("Timer 1 Stunde und 30 Minuten", 5400),
                 ("Timer für anderthalb Stunden", 5400),
                 ("Timer für 2,5 Minuten", 150),
                 ("Stell einen 10-Minuten-Timer", 600),
                 ("Timer 30 Sekunden", 30),
                 ("Timer für eine Minute", 60),
                 ("Timer 15", 900),
                 ("Erinnere mich in 20 Minuten", 1200),
                 ("Set a timer for 10 minutes", 600),
                 ("Set a timer for twenty five minutes", 1500),
                 ("Timer for a minute and 30 seconds", 90),
                 ("Set a timer for half an hour", 1800))
        for text, seconds in cases:
            self.assertEqual(timer.detect_timer(text), ("start", seconds), text)

    def test_cancel_left_and_ask(self):
        for text in ("Timer abbrechen", "Brich den Timer ab", "Stopp den Timer!", "Timer aus",
                     "Lösche den Timer", "Cancel the timer", "Stop the timer", "Timer off"):
            self.assertEqual(timer.detect_timer(text), ("cancel",), text)
        for text in ("Wie lange läuft der Timer noch?", "Wie lange noch?", "How much time is left?",
                     "How long is left on the timer?"):
            self.assertEqual(timer.detect_timer(text), ("left",), text)
        self.assertEqual(timer.detect_timer("Kannst du einen Timer stellen?"), ("ask",))
        for text in ("Wie geht es dir?", "Spiel Thriller", "Ich habe 5 Minuten gewartet",
                     "Wie lange noch bis Weihnachten, und was schenkst du mir dazu?"):
            self.assertIsNone(timer.detect_timer(text), text)

    def test_timer_words_are_not_music_or_pet_actions(self):
        # __main__ checks the timer first; these must not be mistaken by the other rules either way.
        self.assertIsNone(detect_music("Stell einen Timer für 15 Minuten"))
        self.assertIsNone(detect_action("Stell einen Timer für 15 Minuten"))

    def test_replies(self):
        self.assertEqual(timer.say_duration(900), "15 Minuten")
        self.assertEqual(timer.say_duration(61), "1 Minute und 1 Sekunde")
        self.assertEqual(timer.say_duration(30, "en"), "30 seconds")
        self.assertIn("15 Minuten", timer.reply("start", "de", 900)[0])
        self.assertEqual(timer.reply("done", "de")[0], "Die Zeit ist um!")
        self.assertIn("2 minutes", timer.reply("left", "en", 120)[0])
        for lang in ("de", "en"):
            for kind in timer.LOOKS:
                self.assertTrue(timer.reply(kind, lang, 60)[0])


class FakeLink:
    ready = True

    def __init__(self):
        self.pico = Link(object(), NoInput())
        self.timer_total = None

    def call(self, msg):
        return self.pico.handle(json.dumps(msg))


class ControlTests(unittest.TestCase):
    def test_start_left_replace_cancel(self):
        link = FakeLink()
        self.assertEqual(timer.control(link, ("left",)), ("no_timer", None))
        self.assertEqual(timer.control(link, ("start", 900)), ("start", 900))
        self.assertEqual(link.timer_total, 900)
        link.pico.update(60000)
        self.assertEqual(timer.control(link, ("left",)), ("left", 840))
        self.assertEqual(timer.control(link, ("start", 300)), ("replaced", 300))
        self.assertEqual(timer.control(link, ("cancel",)), ("cancel", None))
        self.assertEqual(link.pico.timer_ms, 0)
        self.assertEqual(timer.control(link, ("cancel",)), ("no_timer", None))

    def test_limits_and_missing_pico(self):
        link = FakeLink()
        self.assertEqual(timer.control(link, ("start", 100 * 60)), ("too_long", None))
        self.assertEqual(timer.control(link, ("start", 0)), ("too_short", None))
        self.assertEqual(timer.control(None, ("start", 60)), ("no_pico", None))
        self.assertEqual(timer.control(None, ("ask",)), ("ask", None))


class PcLinkTests(unittest.TestCase):
    def test_timer_event_and_call_reply(self):
        from companion_pc.pico_link import PicoLink
        link = PicoLink(log=lambda *_: None)
        link._handle('{"event":"timer"}')
        self.assertTrue(link.timer_pending())
        self.assertTrue(link.timer_rang())
        self.assertFalse(link.timer_rang())
        link.send = lambda msg: link._handle('{"ok":"timer","left":900,"was":0,"alarm":false}') or True
        self.assertEqual(link.call({"cmd": "timer", "s": 900})["left"], 900)
        link.send = lambda msg: link._handle('{"err":"s"}') or True
        self.assertEqual(link.call({"cmd": "timer", "s": 9999}), {"err": "s"})
        link.send = lambda msg: False
        self.assertIsNone(link.call({"cmd": "timer"}))


class PicoTimerTests(unittest.TestCase):
    def setUp(self):
        self.play = load_play()
        self.link = Link(object(), NoInput())

    def lit(self, frame, x, y):
        return any(frame[(y * 8 + x) * 3 + c] for c in range(3))

    def test_countdown_alarm_and_cancel(self):
        link = self.link
        self.assertEqual(link.handle('{"cmd":"timer","s":5941}'), {"err": "s"})
        self.assertEqual(link.handle('{"cmd":"timer","s":"9"}'), {"err": "s"})
        self.assertEqual(link.handle(json.dumps({"cmd": "timer", "s": MAX_TIMER_S}))["left"], MAX_TIMER_S)
        reply = link.handle('{"cmd":"timer","s":2}')
        self.assertEqual((reply["left"], reply["was"]), (2, MAX_TIMER_S))
        link.handle('{"cmd":"bye"}')  # The timer keeps running without the PC.
        link.update(1999)
        self.assertEqual((link.timer_left(), link.rang), (1, False))
        link.update(1)
        self.assertTrue(link.rang)
        self.assertEqual(link.alarm_ms, ALARM_MS)
        reply = link.handle('{"cmd":"timer","s":0}')
        self.assertEqual((reply["was"], reply["alarm"], link.alarm_ms), (0, True, 0))
        link.handle('{"cmd":"timer","s":60}')
        link.update(60000)
        link.update(ALARM_MS)
        self.assertEqual(link.alarm_ms, 0)  # The alarm stops by itself.

    def test_display(self):
        link, frame = self.link, bytearray(192)
        link.handle('{"cmd":"timer","s":900}')
        self.play.render_timer(link, frame, busy=False)
        one = [(x, y) for y in range(7) for x in range(3) if self.lit(frame, x, y)]
        self.assertEqual(one, [(1, 0), (0, 1), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (0, 6), (1, 6), (2, 6)])
        self.assertTrue(self.lit(frame, 5, 0) and self.lit(frame, 4, 1) and not self.lit(frame, 6, 1))  # "5"
        self.assertEqual(sum(self.lit(frame, x, 7) for x in range(8)), 8)  # full minute
        link.update(30000)
        frame = bytearray(192)
        self.play.render_timer(link, frame, busy=False)
        self.assertEqual(sum(self.lit(frame, x, 7) for x in range(8)), 4)
        link.update(14 * 60000 - 30000 - 1)  # 60.001 s left: still "2" minutes
        frame = bytearray(192)
        self.play.render_timer(link, frame, busy=False)
        self.assertEqual(frame[2 * 3:3 * 3], bytes(self.play.MINUTES_COLOR))  # single digit, centred
        link.update(1)  # last minute: seconds in orange
        self.play.render_timer(link, frame, busy=False)
        self.assertEqual(frame[0:3], bytes(self.play.SECONDS_COLOR))
        busy = bytearray(b"\x07" * 192)
        self.play.render_timer(link, busy, busy=True)
        self.assertEqual(busy, bytearray(b"\x07" * 192))  # Face, speech and pet actions win.
        link.update(60000)
        self.play.render_timer(link, busy, busy=True)
        self.assertEqual(busy[2 * 3:3 * 3], bytes(self.play.ALARM_COLOR))  # Alarm wins over everything.


if __name__ == "__main__":
    unittest.main()
