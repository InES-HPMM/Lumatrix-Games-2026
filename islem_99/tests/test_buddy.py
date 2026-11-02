"""Desktop tests: python -m unittest discover -s tests -v"""
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

from pixel_buddy.faces import ORDER, paint
from pixel_buddy.animation import Animator


class AnimationTests(unittest.TestCase):
    def test_all_expressions_are_distinct(self):
        frames = []
        for emotion in ORDER:
            frame = bytearray(192)
            paint(frame, emotion)
            frames.append(bytes(frame))
        self.assertEqual(len(set(frames)), 3)

    def test_transition_starts_without_jump_and_finishes(self):
        buddy = Animator()
        old = bytes(buddy.frame)
        buddy.set_emotion("happy")
        self.assertEqual(bytes(buddy.update(0)), old)
        buddy.update(240)
        self.assertNotEqual(bytes(buddy.frame), old)
        buddy.update(240)
        self.assertEqual(buddy.frame, buddy.target)

    def test_blink_and_gaze(self):
        buddy = Animator()
        buddy.next_blink = 0
        buddy.update(80)
        self.assertEqual(buddy.frame[24:96], bytes(72))
        buddy.update(200)
        self.assertEqual(buddy.blink_age, -1)
        buddy.next_look = 0
        buddy.update(40)
        self.assertIn(buddy.gaze, (-1, 1))
        buddy.update(650)
        self.assertEqual(buddy.gaze, 0)

    def test_long_demo_reuses_buffers(self):
        buddy = Animator()
        identity = id(buddy.frame)
        for cycle in range(3):
            for emotion in ORDER:
                buddy.set_emotion(emotion)
                for _ in range(200):
                    frame = buddy.update(40)
                    self.assertEqual(len(frame), 192)
                    self.assertEqual(id(frame), identity)

    def test_idle_mouth_stays_still_with_dark_gap(self):
        # The mouth only moves while the PC voice speaks, never on its own.
        for emotion in ORDER:
            buddy = Animator()
            buddy.set_emotion(emotion)
            buddy.update(Animator.TRANSITION_MS)  # skip the crossfade
            expected = bytearray(192)
            paint(expected, emotion)
            mouth = tuple(bool(expected[i]) for i in range(120, 168, 3))
            for _ in range(300):  # 12 s
                frame = buddy.update(40)
                self.assertEqual(frame[96:120], bytes(24))
                # Compare lit pixels, independent of the breathing brightness.
                self.assertEqual(tuple(bool(frame[i]) for i in range(120, 168, 3)), mouth)

    def test_invalid_expression(self):
        with self.assertRaises(ValueError):
            Animator().set_emotion("unknown")


class DriverTests(unittest.TestCase):
    def test_original_driver_pin_grb_orientation_and_single_apply(self):
        packets = []
        machine = types.ModuleType("machine")
        class Pin:
            OUT = 1
            def __init__(self, number, mode):
                self.number = number
        machine.Pin = Pin
        machine.bitstream = lambda pin, mode, timing, data: packets.append((pin.number, timing, bytes(data)))
        micro = types.ModuleType("micropython")
        micro.native = lambda fn: fn
        import time
        with patch.dict(sys.modules, {"machine": machine, "micropython": micro}), \
             patch.object(time, "sleep_ms", lambda _: None, create=True), \
             patch.object(time, "ticks_ms", lambda: 0, create=True), \
             patch.object(time, "ticks_us", lambda: 0, create=True):
            spec = importlib.util.spec_from_file_location("original_driver", "zhaw_led_matrix/ledmatrix.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        package = types.ModuleType("zhaw_led_matrix")
        package.LedMatrix = module.LedMatrix
        with patch.dict(sys.modules, {"zhaw_led_matrix": package}):
            from pixel_buddy.display import Display
            display = Display(100)
            frame = bytearray(192)
            frame[:3] = bytes((10, 20, 30))
            display.show(frame)
            self.assertEqual(len(packets), 1)
            pin, timing, data = packets[0]
            self.assertEqual(pin, 19)
            self.assertEqual(timing, (400, 850, 800, 450))
            self.assertEqual(data[168:171], bytes((20, 10, 30)))
            self.assertEqual(sum(data), 60)
            display.clear()
            self.assertEqual(packets[-1][2], bytes(192))


if __name__ == "__main__":
    unittest.main()
