"""Joystick press = microphone (with PC chat), double press = petting."""
import io
import json
import sys
import time
import unittest
from unittest.mock import patch

from companion_pc import console, pico_link
from pixel_buddy.controls import DOUBLE_MS, DoublePress
from pixel_buddy.link import PC_TIMEOUT, Link


def run_frames(presses, schedule, frames=30, dt=40):
    """schedule: {frame: [events]} -> list of (frame, output events)."""
    out = []
    for frame in range(frames):
        events = presses.update(schedule.get(frame, []), dt)
        if events:
            out.append((frame, events))
    return out


class DoublePressTests(unittest.TestCase):
    def test_single_press_becomes_mic_after_wait(self):
        result = run_frames(DoublePress(), {0: ["center"]})
        self.assertEqual(result, [(DOUBLE_MS // 40, ["mic"])])

    def test_double_press_is_petting_without_mic(self):
        self.assertEqual(run_frames(DoublePress(), {0: ["center"], 5: ["center"]}), [(5, ["center"])])

    def test_two_slow_presses_are_two_mic_toggles(self):
        result = run_frames(DoublePress(), {0: ["center"], 15: ["center"]}, frames=40)
        self.assertEqual([events for _, events in result], [["mic"], ["mic"]])

    def test_other_directions_pass_through_immediately(self):
        self.assertEqual(run_frames(DoublePress(), {0: ["up"], 1: ["left"]}), [(0, ["up"]), (1, ["left"])])


class PresenceTests(unittest.TestCase):
    def test_pc_active_after_command_until_timeout_or_bye(self):
        class NoInput:
            def poll(self, timeout):
                return []
        link = Link(object(), NoInput())
        self.assertFalse(link.pc_active)
        link.handle('{"cmd":"ping"}')
        self.assertTrue(link.pc_active)
        link.update(PC_TIMEOUT - 1)
        self.assertTrue(link.pc_active)
        link.update(1)
        self.assertFalse(link.pc_active)
        link.handle('{"cmd":"show","face":"happy"}')
        self.assertEqual(link.handle('{"cmd":"bye"}'), {"ok": "bye"})
        self.assertFalse(link.pc_active)
        self.assertEqual(link.mode, "idle")
        link.handle("not json")
        self.assertFalse(link.pc_active)  # garbage does not count as a chat


@unittest.skipIf(pico_link.serial is None, "pyserial not installed")
class MicEventTests(unittest.TestCase):
    def test_mic_event_counts_once(self):
        link = pico_link.PicoLink(log=lambda line: None)
        self.assertFalse(link.mic_pressed())
        link._handle('{"event": "mic"}')
        link._handle('{"event": "mic"}')
        self.assertTrue(link.mic_pressed())
        self.assertFalse(link.mic_pressed())


class FakeKeys:
    def __init__(self, keys):
        self.keys = list(keys)

    def kbhit(self):
        return bool(self.keys)

    def getwch(self):
        return self.keys.pop(0)


class ReadLineTests(unittest.TestCase):
    def read(self, keys, wake):
        with patch.object(console, "msvcrt", FakeKeys(keys)), \
             patch.object(console, "interactive", lambda: True), \
             patch.object(console.time, "sleep", lambda s: None), \
             patch.object(sys, "stdout", io.StringIO()):
            return console.read_line("You: ", wake)

    def test_typing_with_backspace_umlaut_and_arrow(self):
        self.assertEqual(self.read(["H", "a", "x", "\b", "l", "l", "ö", "\xe0", "K", "\r"], lambda: False), "Hallö")

    def test_joystick_on_empty_line_returns_none(self):
        self.assertIsNone(self.read([], lambda: True))

    def test_joystick_while_typing_is_ignored(self):
        presses = iter([False, True, True, True])
        keys = FakeKeys(["H", "i"])
        later = ["\r"]

        def wake():
            pressed = next(presses, False)
            if not keys.keys and later:
                keys.keys.append(later.pop())
            return pressed
        with patch.object(console, "msvcrt", keys), \
             patch.object(console, "interactive", lambda: True), \
             patch.object(console.time, "sleep", lambda s: None), \
             patch.object(sys, "stdout", io.StringIO()):
            self.assertEqual(console.read_line("You: ", wake), "Hi")

    def test_ctrl_c(self):
        with self.assertRaises(KeyboardInterrupt):
            self.read(["\x03"], lambda: False)


if __name__ == "__main__":
    unittest.main()
