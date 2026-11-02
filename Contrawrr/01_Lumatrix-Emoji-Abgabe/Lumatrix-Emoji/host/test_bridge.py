"""Tests for when the laptop sends the sung words to the Lumatrix.

    python -m unittest discover -s host
"""

import unittest
from types import SimpleNamespace

from lumatrix_music import Bridge
from lyrics import Lyrics


class FakePort:
    def __init__(self):
        self.lines = []

    def write(self, data):
        self.lines += data.decode().splitlines()


def bridge_playing(lrc):
    """A Bridge whose song is at 0 s when time.monotonic() is 100."""
    bridge = Bridge(FakePort(), "auto")
    bridge.ready = True
    bridge.key = "song"
    bridge.songs["song"] = Lyrics(lrc, pace=0.1)
    bridge.track = SimpleNamespace(playing=True)
    bridge.clock = (0.0, 100.0)
    return bridge


class SendWords(unittest.TestCase):
    def test_each_word_is_sent_once_when_it_is_sung(self):
        bridge = bridge_playing("[00:00.50]My heart\n[00:01.50]Fire!\n[00:02.00]")
        for now in (100.0, 100.55, 100.6, 100.85, 101.6, 101.7):
            bridge.send_words(now)
        self.assertEqual(bridge.port.lines, ["WORD my heart", "WORD heart fire", "WORD fire"])

    def test_words_skipped_by_a_jump_ahead_are_not_sent(self):
        bridge = bridge_playing("[00:00.50]My heart\n[00:01.50]Fire!\n[00:20.00]Rain\n[00:21.00]")
        bridge.send_words(100.0)
        bridge.send_words(120.05)  # the clock jumped from 0 s to 20.05 s
        self.assertEqual(bridge.port.lines, ["WORD rain"])

    def test_the_next_word_goes_along_for_negations(self):
        bridge = bridge_playing("[00:00.50]Boys don't cry\n[00:02.00]")
        for now in (100.0, 100.4, 100.6, 101.1):
            bridge.send_words(now)
        self.assertEqual(bridge.port.lines, ["WORD boys don't", "WORD don't cry", "WORD cry"])

    def test_jumping_back_does_not_replay_words(self):
        bridge = bridge_playing("[00:00.50]My heart\n[00:01.50]Fire!\n[00:02.00]")
        for now in (100.0, 100.55, 100.85, 101.6):
            bridge.send_words(now)
        bridge.clock = (0.0, 101.6)  # the song was moved back to the start
        bridge.send_words(101.7)
        self.assertEqual(bridge.port.lines, ["WORD my heart", "WORD heart fire", "WORD fire"])


if __name__ == "__main__":
    unittest.main()
