"""When each word of a song is sung, for the Lumatrix's emojis.

Synced lyrics come from LRCLIB (lrclib.net, free, no account), or from your
own file lyrics/<title>.lrc. They are timed per line, so within a line the
letters follow each other at the song's singing pace, and whatever time is
left in the line is a pause. Each word is sent to the Lumatrix a moment
before its estimated time (Lyrics.cues).
"""

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_PACE = 0.12  # seconds per character when a song gives no hint
MIN_PACE = 0.04
MAX_PACE = 0.3
# Words go to the Lumatrix a moment before their estimated time: the Pico
# needs ~0.15 s (model + pop), and a symbol a bit early feels on time while a
# late one feels wrong. Estimates drift further off the later in a line, so
# those go a bit earlier still, but never before their line starts.
SEND_AHEAD = 0.45  # seconds
AHEAD_PER_SECOND = 0.1  # extra lead per second into the line
LINE_AHEAD = 0.15  # seconds; the line timestamp is the only exact time

CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'!?,.-() ")
SPELLED = {"Ä": "AE", "Ö": "OE", "Ü": "UE", "–": "-", "—": "-", "’": "'", "‘": "'", "´": "'", "`": "'"}


def display_text(text):
    """The text in capitals, umlauts spelled out, accents dropped, anything
    unusual left out (each character counts for the timing)."""
    out = []
    for ch in text.upper():  # also turns ß into SS
        ch = SPELLED.get(ch, ch)
        ch = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
        out.append("".join(c if c in CHARS else " " if c.isspace() else "" for c in ch))
    return " ".join("".join(out).split())


TIME_TAG = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def parse_lrc(text):
    """[(seconds, text)] of an LRC file, in time order. A line can carry several
    timestamps; a timestamp without text marks a pause."""
    lines = []
    for raw in text.splitlines():
        rest = raw.strip()
        times = []
        while (m := TIME_TAG.match(rest)) is not None:
            times.append(int(m.group(1)) * 60 + float(m.group(2)))
            rest = rest[m.end() :]
        lines.extend((t, rest.strip()) for t in times)
    lines.sort(key=lambda line: line[0])
    return lines


def estimate_pace(lines):
    """Seconds per character the song is sung at. A line's time also holds the
    pause after it, so the quickest lines tell the singing pace."""
    ratios = []
    for (start, text), (end, _) in zip(lines, lines[1:]):
        length = len(text)
        if length >= 4 and 0 < end - start <= 12:
            ratios.append((end - start) / length)
    if not ratios:
        return DEFAULT_PACE
    ratios.sort()
    return min(max(ratios[int(len(ratios) * 0.1)], MIN_PACE), MAX_PACE)


class Lyrics:
    """A song's words: when each is sung (words) and when to send it (cues)."""

    def __init__(self, lrc, pace=None):
        lines = [(t, display_text(text)) for t, text in parse_lrc(lrc)]
        self.pace = pace or estimate_pace(lines)
        self.words = []  # (time, word): when each word starts being sung
        self.cues = []  # (time, word): when to send it to the Lumatrix
        for i, (start, text) in enumerate(lines):
            if not text:
                continue
            step = self.pace
            end = lines[i + 1][0] if i + 1 < len(lines) else None
            if end is not None and len(text) * step > end - start:
                step = (end - start) / len(text)  # sung faster than usual
            k = 0  # characters before the word
            for word in text.split(" "):
                sung = start + k * step
                self.words.append((sung, word))
                ahead = SEND_AHEAD + AHEAD_PER_SECOND * (sung - start)
                self.cues.append((max(start - LINE_AHEAD, sung - ahead), word))
                k += len(word) + 1


# Your own timed lyrics win over LRCLIB: lyrics/<title>.lrc next to host/.
# One word per line gives each word its exact time.
LOCAL_LYRICS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lyrics")
LRCLIB = "https://lrclib.net/api/"
USER_AGENT = "Lumatrix Emoji (personal project)"
VERSION_NOTE = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]|\s+-\s+.*$")


def search_title(title):
    """The title without "(feat. ...)", "[From ...]", "- Remastered" and the like."""
    return VERSION_NOTE.sub("", title).strip() or title


def pick_synced(results, duration, tolerance=3.0):
    """The first search result with synced lyrics for a song of this length;
    another version's timing would be off."""
    for result in results:
        if not result.get("syncedLyrics"):
            continue
        if duration and abs((result.get("duration") or 0) - duration) > tolerance:
            continue
        return result["syncedLyrics"]
    return None


def lrclib(path, params, tries=3):
    url = LRCLIB + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code < 500:
                return None  # 404: not there
        except (OSError, ValueError):
            pass  # offline or a garbled answer: try again
        time.sleep(1 + attempt)  # LRCLIB is sometimes busy (503)
    return None


def find_lyrics(artist, title, album, duration):
    """Synced lyrics (LRC text) for the song, or None. Takes up to a few
    seconds, so call it away from the main loop."""
    try:
        with open(os.path.join(LOCAL_LYRICS, search_title(title) + ".lrc"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        pass
    if duration:
        params = {"artist_name": artist, "track_name": title, "album_name": album, "duration": round(duration)}
        found = lrclib("get", params)
        if found and found.get("syncedLyrics"):
            return found["syncedLyrics"]
    results = lrclib("search", {"artist_name": artist, "track_name": search_title(title)})
    return pick_synced(results or [], duration)
