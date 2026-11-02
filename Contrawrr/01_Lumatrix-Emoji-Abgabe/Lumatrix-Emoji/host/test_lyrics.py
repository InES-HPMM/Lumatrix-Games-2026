"""Tests for the timed lyrics: when each word is sung and sent.

    python -m unittest discover -s host

Lyrics are timed per line; within a line the letters follow each other at
the song's singing pace, and whatever time is left in the line is a pause.
"""

import unittest

from lyrics import Lyrics, display_text, parse_lrc, pick_synced, search_title


def rounded(pairs):
    return [(round(t, 3), w) for t, w in pairs]


class ParseLrc(unittest.TestCase):
    def test_reads_timed_lines_and_skips_tags(self):
        text = "[ar:Someone]\n[length: 03:20]\n[00:01.50]First line\n[00:04.00][01:10.25]Chorus\n[00:06.00]\n"
        self.assertEqual(
            parse_lrc(text),
            [(1.5, "First line"), (4.0, "Chorus"), (6.0, ""), (70.25, "Chorus")],
        )


class DisplayText(unittest.TestCase):
    def test_capitals_with_german_and_accents_spelled_out(self):
        self.assertEqual(display_text("Ich fahr'  ohne Benzin – süß! ♪ Café"), "ICH FAHR' OHNE BENZIN - SUESS! CAFE")


class Timing(unittest.TestCase):
    def test_words_are_listed_with_when_they_start(self):
        lyrics = Lyrics("[00:00.00]My heart\n[00:01.00]Fire!\n[00:01.50]", pace=0.1)
        self.assertEqual(rounded(lyrics.words), [(0.0, "MY"), (0.3, "HEART"), (1.0, "FIRE!")])

    def test_words_go_out_a_moment_before_they_are_sung(self):
        # INTO is sung at 10.0 s, THE at 10.5 s, FIRE at 10.9 s
        lyrics = Lyrics("[00:10.00]Into the fire\n[00:20.00]", pace=0.1)
        self.assertEqual(rounded(lyrics.cues), [(9.85, "INTO"), (10.0, "THE"), (10.36, "FIRE")])

    def test_rushed_line_squeezes_its_words_into_its_time(self):
        # 8 characters at 0.1 s would take 0.8 s, but the next line starts at 0.4 s
        lyrics = Lyrics("[00:00.00]AB CD EF\n[00:00.40]NEXT", pace=0.1)
        self.assertEqual(rounded(lyrics.words[:3]), [(0.0, "AB"), (0.15, "CD"), (0.3, "EF")])

    def test_pace_is_estimated_from_the_song(self):
        # 10 characters per line. Most lines last 2 s (0.2 s per character),
        # one has a pause after it (10 s) and one is rushed (0.5 s)
        starts = ["00:%02d.00" % s for s in range(0, 20, 2)] + ["00:28.00", "00:28.50"]
        lrc = "".join("[%s]ABCDE FGHI\n" % t for t in starts) + "[00:30.50]"
        lyrics = Lyrics(lrc)
        self.assertAlmostEqual(lyrics.pace, 0.2, places=2)


class FindLyrics(unittest.TestCase):
    def test_search_title_drops_versions_and_features(self):
        cases = {
            "Can't Take My Eyes off You (Original Extended Version)": "Can't Take My Eyes off You",
            "Lose My Mind (feat. Doja Cat) [From F1® The Movie]": "Lose My Mind",
            "Hope (feat. Winona Oak)": "Hope",
            "Come Together - Remastered 2009": "Come Together",
            "Hello": "Hello",
        }
        for title, expected in cases.items():
            self.assertEqual(search_title(title), expected)

    def test_picks_synced_lyrics_of_the_same_length(self):
        results = [
            {"duration": 241.0, "syncedLyrics": None},
            {"duration": 200.0, "syncedLyrics": "[00:01.00]radio edit"},
            {"duration": 239.5, "syncedLyrics": "[00:01.00]album version"},
        ]
        self.assertEqual(pick_synced(results, 241.0), "[00:01.00]album version")
        self.assertIsNone(pick_synced(results, 300.0))


if __name__ == "__main__":
    unittest.main()
