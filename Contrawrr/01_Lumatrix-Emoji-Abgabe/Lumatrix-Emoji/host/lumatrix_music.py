#!/usr/bin/env python3
"""Lumatrix Emoji, laptop side (macOS).

Shows the album cover of whatever Spotify or Apple Music is playing on the
Lumatrix, and sends it each word of the lyrics the moment it is sung. The
word model on the Pico picks a symbol for the important ones (a heart for
"love", a flame for "burning") and shows it. The joystick does
next/previous, volume and play/pause; a double press (or holding the press)
switches the symbols on or off.

    python3 host/lumatrix_music.py

Close Thonny first: only one program can use the Lumatrix's USB port.
The Pico side is pico/main.py; the message format is described there.
"""

import argparse
import bisect
import glob
import io
import json
import os
import queue
import subprocess
import tempfile
import threading
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import serial
from PIL import Image, ImageEnhance
from serial.tools import list_ports

import lyrics

PICO_USB_VENDOR = 0x2E8A  # Raspberry Pi
POLL_SECONDS = 1.0
VOLUME_STEP = 6  # percent per joystick nudge
SATURATION = 1.3  # covers look washed out on LEDs without a boost
HELLO_TIMEOUT = 5.0
WORD_LATE = 1.0  # seconds; words older than this are not sent (after a jump)
NEXT_WORD_S = 2.0  # seconds; a word this soon after another goes along with it
CLOCK_JUMP = 0.5  # seconds off before the song clock jumps instead of drifting
CHEAT_SOUND = "/System/Library/Sounds/Hero.aiff"
SEP = "\x1f"  # field separator in the AppleScript answers

# Each info script answers: state, track id, title, artist, album, artwork URL,
# volume, position (ms), duration (ms).
# Variables get long names: short ones like "st" clash with AppleScript words ("1st").
SPOTIFY_INFO = """
set fieldSep to character id 31
try
    tell application "Spotify"
        set playerState to player state as string
        if playerState is "stopped" then return "stopped"
        set theTrack to current track
        set trackInfo to playerState & fieldSep & (id of theTrack) & fieldSep & (name of theTrack) & fieldSep & (artist of theTrack) & fieldSep & (album of theTrack) & fieldSep & (artwork url of theTrack)
        set playerPosition to player position
        set trackLength to (duration of theTrack) / 1000
    end tell
on error
    return "stopped"
end try
set currentVolume to output volume of (get volume settings)
return trackInfo & fieldSep & (currentVolume as string) & fieldSep & ((round (playerPosition * 1000)) as string) & fieldSep & ((round (trackLength * 1000)) as string)
"""

MUSIC_INFO = """
set fieldSep to character id 31
try
    tell application "Music"
        set playerState to player state as string
        if playerState is "stopped" then return "stopped"
        set theTrack to current track
        set trackInfo to playerState & fieldSep & (persistent ID of theTrack) & fieldSep & (name of theTrack) & fieldSep & (artist of theTrack) & fieldSep & (album of theTrack) & fieldSep & ""
        set playerPosition to player position
        set trackLength to duration of theTrack
    end tell
on error
    return "stopped"
end try
set currentVolume to output volume of (get volume settings)
return trackInfo & fieldSep & (currentVolume as string) & fieldSep & ((round (playerPosition * 1000)) as string) & fieldSep & ((round (trackLength * 1000)) as string)
"""

MUSIC_COVER = """
on run argv
    tell application "Music" to set coverData to raw data of artwork 1 of current track
    set coverFile to open for access (POSIX file (item 1 of argv)) with write permission
    set eof coverFile to 0
    write coverData to coverFile
    close access coverFile
end run
"""

CHANGE_VOLUME = """
on run argv
    set volumeChange to (item 1 of argv) as integer
    set newVolume to (output volume of (get volume settings)) + volumeChange
    if newVolume > 100 then set newVolume to 100
    if newVolume < 0 then set newVolume to 0
    set volume output volume newVolume
    if volumeChange > 0 then set volume output muted false
    return newVolume
end run
"""


class AppleScriptError(Exception):
    pass


def osascript(script, *args):
    try:
        result = subprocess.run(
            ["osascript", "-e", script, *args], capture_output=True, text=True, timeout=10
        )
    except subprocess.TimeoutExpired:
        raise AppleScriptError("no answer (is a macOS permission prompt waiting?)")
    if result.returncode != 0:
        raise AppleScriptError(result.stderr.strip())
    return result.stdout.strip()


def download(url):
    result = subprocess.run(["curl", "-fsSL", "--max-time", "8", url], capture_output=True)
    return result.stdout if result.returncode == 0 and result.stdout else None


def change_volume(delta):
    """Changes the Mac's output volume. Returns the new volume or None."""
    try:
        return int(osascript(CHANGE_VOLUME, str(delta)))
    except (AppleScriptError, ValueError):
        return None


def number(text):
    try:
        return int(text)
    except ValueError:
        return None


@dataclass
class Track:
    player: "Player"
    playing: bool
    track_id: str
    title: str
    artist: str
    album: str
    artwork_url: str
    volume: Optional[int]
    position: Optional[float]  # seconds into the song when it was asked
    duration: Optional[float]  # seconds
    asked_at: float  # time.monotonic() of the answer


class Player:
    app = ""
    info_script = ""

    def running(self):
        found = subprocess.run(["pgrep", "-x", self.app], stdout=subprocess.DEVNULL)
        return found.returncode == 0

    def now_playing(self):
        start = time.monotonic()
        fields = osascript(self.info_script).split(SEP)
        asked_at = (start + time.monotonic()) / 2  # the app answered about then
        if len(fields) != 9:
            return None
        state, track_id, title, artist, album, artwork_url, volume, position, duration = fields
        volume = number(volume)  # None e.g. for an output without volume control
        position = number(position)
        duration = number(duration)
        return Track(
            self,
            state == "playing",
            track_id,
            title,
            artist,
            album,
            artwork_url,
            volume,
            None if position is None else position / 1000,
            duration / 1000 if duration else None,
            asked_at,
        )

    def command(self, action):
        verb = {"next": "next track", "prev": "previous track", "playpause": "playpause"}[action]
        osascript('tell application "%s" to %s' % (self.app, verb))

    def cover(self, track):
        """The cover image file's bytes, or None."""
        return None


class Spotify(Player):
    app = "Spotify"
    info_script = SPOTIFY_INFO

    def cover(self, track):
        return download(track.artwork_url) if track.artwork_url else None


class Music(Player):
    app = "Music"
    info_script = MUSIC_INFO

    def cover(self, track):
        fd, path = tempfile.mkstemp(suffix=".img")
        os.close(fd)
        try:
            osascript(MUSIC_COVER, path)
            with open(path, "rb") as f:
                return f.read() or None
        except AppleScriptError:
            return None  # streamed songs often have no artwork in the app
        finally:
            os.remove(path)


def itunes_cover(track):
    """Looks the cover up in the public iTunes catalogue (no account needed)."""
    searches = [(track.artist + " " + track.album, "album"), (track.artist + " " + track.title, "song")]
    for term, entity in searches:
        if not term.strip():
            continue
        query = urllib.parse.urlencode({"term": term, "entity": entity, "limit": 1})
        data = download("https://itunes.apple.com/search?" + query)
        try:
            results = json.loads(data)["results"] if data else []
        except (ValueError, KeyError):
            results = []
        if results and results[0].get("artworkUrl100"):
            return download(results[0]["artworkUrl100"].replace("100x100bb", "600x600bb"))
    return None


def square(img, zoom=1.0):
    """The middle square of the image; zoom < 1 keeps only the centre."""
    w, h = img.size
    side = min(w, h) * zoom
    left, top = (w - side) / 2, (h - side) / 2
    return img.crop((round(left), round(top), round(left + side), round(top + side)))


def colors_of(img):
    data = img.tobytes()
    return [tuple(data[i : i + 3]) for i in range(0, len(data), 3)]


def patches(img):
    """The 8x8 patches of a 64x64 image, top row first."""
    for y in range(0, 64, 8):
        for x in range(0, 64, 8):
            yield img.crop((x, y, x + 8, y + 8))


TO_LINEAR = [(i / 255) ** 2.2 for i in range(256)]


def light_average(patch):
    """Average that mixes colours like light does, so contrasty patches don't go muddy."""
    colors = colors_of(patch)
    return tuple(
        round(255 * (sum(TO_LINEAR[c[i]] for c in colors) / len(colors)) ** (1 / 2.2))
        for i in range(3)
    )


def main_color(patch):
    """The patch's most common colour instead of its average."""
    reduced = patch.quantize(colors=3, method=Image.Quantize.MEDIANCUT)
    _, index = max(reduced.getcolors())
    return tuple(reduced.getpalette()[3 * index : 3 * index + 3])


def brighten(colors, most=2.5):
    """Stretches dark covers so the brightest pixel is fully lit."""
    top = max(max(c) for c in colors) or 1
    gain = min(255 / top, most)
    return [tuple(min(255, round(v * gain)) for v in c) for c in colors]


def exposure_gain(colors, target=110, most=2.5):
    """How much to brighten a dark cover so its average brightness reaches
    target, letting only the brightest tenth of the pixels clip."""
    mean = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in colors) / len(colors)
    highlights = sorted(max(c) for c in colors)[len(colors) * 9 // 10]
    return max(1.0, min(target / max(mean, 1), 255 / max(highlights, 1), most))


def expose(colors, target=110, most=2.5):
    gain = exposure_gain(colors, target, most)
    return [tuple(min(255, round(v * gain)) for v in c) for c in colors]


SHADOW_LIFT = [round(255 * (i / 255) ** 0.75) for i in range(256)]
BLACK_POINT = 24  # darker pixels would be off on the LEDs; they stay black


def lift_shadows(colors):
    """Raises dark tones, which the LEDs would otherwise round down to off."""
    return [tuple(SHADOW_LIFT[v] for v in c) for c in colors]


def style_smooth(img):
    colors = style_original(img)
    lifted = lift_shadows(expose(colors))
    return [(0, 0, 0) if max(c) < BLACK_POINT else new for c, new in zip(colors, lifted)]


def style_crisp(img):
    return brighten([main_color(p) for p in patches(img.resize((64, 64), Image.Resampling.BOX))])


def style_poster(img):
    reduced = img.resize((64, 64), Image.Resampling.BOX).quantize(
        colors=6, method=Image.Quantize.MEDIANCUT, kmeans=2
    )
    palette = reduced.getpalette()
    indexes = [max(p.getcolors())[1] for p in patches(reduced)]
    return brighten([tuple(palette[3 * i : 3 * i + 3]) for i in indexes])


def style_zoom(img):
    return style_crisp(square(img, 0.65))


def style_bright(img):
    return brighten([light_average(p) for p in patches(img.resize((64, 64), Image.Resampling.BOX))])


def style_original(img):
    return colors_of(img.resize((8, 8), Image.Resampling.BOX))


def oklab(color):
    """A colour in OKLab, where the distance between two colours matches how
    different they look."""
    r, g, b = (TO_LINEAR[v] for v in color)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


FIGURE_SIZE = 128  # working size: fine lines like lettering blur away, shapes stay
BACKGROUND_NEAR = 0.1  # OKLab distance that still counts as background (texture, noise)
BACKGROUND_SHARE = 0.6  # covers at least this much background count as flat
FIGURE_FAR = 0.15  # OKLab distance from the background that counts as figure
FIGURE_FROM = 0.06  # share of a patch where the figure starts to show
FIGURE_FULL = 0.15  # share of a patch where the LED takes the figure's colour


def background_of(img, labs):
    """The colour most of the cover is close to, and how much of it is."""
    reduced = img.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    palette = reduced.getpalette()
    best_share, best = 0.0, None
    # A textured background splits into several shades: try the biggest few
    for _, index in sorted(reduced.getcolors(), reverse=True)[:3]:
        center = oklab(palette[3 * index : 3 * index + 3])
        share = sum(distance(lab, center) < BACKGROUND_NEAR for lab in labs) / len(labs)
        if share > best_share:
            best_share, best = share, center
    return best, best_share


def style_auto(img):
    """smooth, except on covers that are mostly one background colour: there a
    figure that the average would wash out (a dancer, a logo) keeps its colour."""
    colors = style_smooth(img)
    small = img.resize((FIGURE_SIZE, FIGURE_SIZE), Image.Resampling.BOX)
    pixels = colors_of(small)
    labs = [oklab(c) for c in pixels]
    background, share = background_of(small, labs)
    if share < BACKGROUND_SHARE:
        return colors

    side = FIGURE_SIZE // 8
    figures = [[] for _ in range(64)]  # each patch's figure pixels
    for i, (color, lab) in enumerate(zip(pixels, labs)):
        if distance(lab, background) > FIGURE_FAR:
            y, x = divmod(i, FIGURE_SIZE)
            figures[y // side * 8 + x // side].append(color)

    # Brightened like smooth brightens the rest, but without the shadow lift,
    # which would turn a black figure grey
    gain = exposure_gain(style_original(img))
    result = []
    for color, figure in zip(colors, figures):
        strength = (len(figure) / (side * side) - FIGURE_FROM) / (FIGURE_FULL - FIGURE_FROM)
        if strength <= 0:
            result.append(color)
            continue
        strength = min(strength, 1.0)
        mean = [min(255, gain * sum(c[i] for c in figure) / len(figure)) for i in range(3)]
        result.append(tuple(round(v + (f - v) * strength) for v, f in zip(color, mean)))
    return result


# Ways to turn a cover into 8x8 pixels (pick one with --style)
STYLES = {
    "auto": (style_auto, "smooth, but a figure on a plain background keeps its own colour"),
    "smooth": (style_smooth, "average of each patch, with dark covers and shadows brightened"),
    "original": (style_original, "plain average of each patch, the first version"),
    "crisp": (style_crisp, "each pixel takes the most common colour of its patch"),
    "poster": (style_poster, "the whole cover in 6 colours, like pixel art"),
    "zoom": (style_zoom, "crisp, but only the middle of the cover"),
    "bright": (style_bright, "colours mixed like light instead of averaged"),
}


def cover_pixels(data, style):
    """The cover as 8x8 RGB bytes, top row first."""
    with Image.open(io.BytesIO(data)) as img:
        colors = STYLES[style][0](square(img.convert("RGB")))
    small = Image.frombytes("RGB", (8, 8), bytes(v for c in colors for v in c))
    return ImageEnhance.Color(small).enhance(SATURATION).tobytes()


def clean_word(word):
    """A lyric word as the Pico's model spells it: lowercase letters and apostrophes."""
    word = word.lower().replace("\u2019", "'")
    return "".join(c for c in word if c.isalpha() or c == "'")


def title_text(title):
    """The song title as the Pico's font can show it (capitals, ASCII)."""
    return lyrics.display_text(lyrics.search_title(title))[:60] or "?"


def track_key(track):
    return track.player.app + ":" + track.track_id


class Bridge:
    """Keeps the Lumatrix in sync with the music apps over one serial connection.

    Asking the apps what is playing and downloading covers and lyrics is
    slow, so a watcher thread does that. This thread owns the serial port
    and sends the words on time.
    """

    def __init__(self, port, style, lyrics_offset=0.0):
        self.port = port
        self.style = style
        self.lyrics_offset = lyrics_offset
        self.players = [Spotify(), Music()]
        self.active = None  # player that the joystick controls
        self.covers = {}  # cover image files by album
        self.pixels = {}  # 8x8 covers by track key (watcher thread)
        self.songs = {}  # Lyrics by track key, None if there are none (lyrics threads)
        self.updates = queue.Queue()  # (track or None, pixels) from the watcher
        self.poll_at = 0.0  # when the watcher asks the apps next
        self.running = True
        self.track = None  # what plays now, and its key
        self.key = None
        self.clock = None  # (song position, time.monotonic()) it was at
        self.symbols_on = True
        self.reported = None  # track key whose lyrics were reported
        self.next_word = None  # index into the song's words of the next to send
        self.shown = None  # track key on the Lumatrix, "idle", or None = unknown
        self.shown_playing = None
        self.volume = None
        self.ready = False
        self.warned = set()

    def send(self, line):
        self.port.write((line + "\n").encode("ascii"))

    def restart_pico(self):
        """Stops whatever runs on the Pico (Thonny may have left it at the
        prompt) and soft-resets it, so main.py starts fresh and says HELLO."""
        self.port.write(b"\r\x03\x03")  # Ctrl+C: stop the running program
        time.sleep(0.2)
        self.port.write(b"\x02")  # Ctrl+B: leave Thonny's raw mode
        time.sleep(0.1)
        self.port.write(b"\x04")  # Ctrl+D: soft reset, runs main.py

    def run(self):
        self.restart_pico()
        threading.Thread(target=self.watch, daemon=True).start()
        deadline = time.monotonic() + HELLO_TIMEOUT
        buffer = b""
        try:
            while True:
                buffer += self.port.read(4096)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    self.on_line(line.decode("ascii", "replace").strip())
                while not self.updates.empty():
                    track, pixels = self.updates.get()
                    if self.ready:
                        self.on_track(track, pixels)
                if self.ready:
                    self.send_words(time.monotonic())
                elif deadline and time.monotonic() > deadline:
                    print("The Lumatrix doesn't answer. Put the program on it (Ctrl+C first):")
                    print("  mpremote cp pico/main.py pico/wordmodel.py pico/fastdot.py pico/riddle.py pico/font.py pico/model.bin pico/icons.bin : && mpremote reset")
                    deadline = None
                time.sleep(0.01)
        finally:
            self.running = False

    def watch(self):
        """Watcher thread: what's playing, its cover, and its lyrics."""
        while self.running:
            if time.monotonic() < self.poll_at:
                time.sleep(0.05)
                continue
            self.poll_at = time.monotonic() + POLL_SECONDS
            track = self.now_playing()
            pixels = None
            if track is not None:
                key = track_key(track)
                if key not in self.pixels:
                    self.pixels[key] = self.cover_for(track)
                    self.look_up_lyrics(key, track)
                pixels = self.pixels[key]
            self.updates.put((track, pixels))

    def look_up_lyrics(self, key, track):
        def look():
            lrc = lyrics.find_lyrics(track.artist, track.title, track.album, track.duration)
            self.songs[key] = lyrics.Lyrics(lrc) if lrc else None

        threading.Thread(target=look, daemon=True).start()

    def on_line(self, line):
        if line.startswith("HELLO"):
            if not self.ready:
                print("Lumatrix connected.")
            self.ready = True
            self.shown = self.shown_playing = None  # send everything again
            self.poll_at = 0.0
        elif not self.ready:
            pass  # prompt chatter from the restart
        elif line.startswith("BTN "):
            self.on_button(line[4:])
        elif line.startswith("SAW "):
            parts = line.split()
            if len(parts) == 4:
                print("  %s -> %s (%s%%)" % (parts[1], parts[2].replace("_", " "), parts[3]))
        elif line == "NOMODEL":
            print("The word model isn't on the Lumatrix: copy pico/model.bin onto it (see the README).")
        elif line == "CHEAT":
            print("Cheat code!")
            try:
                subprocess.Popen(["afplay", CHEAT_SOUND])
            except OSError:
                pass
        elif line:
            print("Lumatrix:", line)

    def on_button(self, action):
        if action == "mode":
            self.symbols_on = not self.symbols_on
            self.next_word = None
            if self.symbols_on:
                print("Symbols on.")
                if self.key in self.songs and self.songs[self.key] is None:
                    print("  (this song has no synced lyrics, so the cover stays)")
            else:
                print("Symbols off: showing the cover.")
                self.send("NOICON")
            return
        if action in ("volup", "voldown"):
            volume = change_volume(VOLUME_STEP if action == "volup" else -VOLUME_STEP)
            if volume is not None:
                self.volume = volume
                self.send("VOL %d" % volume)
            return
        if action not in ("next", "prev", "playpause"):
            return
        if self.active is None:
            print("Start Spotify or Apple Music first.")
            return
        print("Joystick:", action)
        try:
            self.active.command(action)
        except AppleScriptError as e:
            self.warn("Couldn't control %s: %s" % (self.active.app, e))
        if action == "playpause":
            self.shown_playing = None  # the Lumatrix guessed; confirm it
        self.poll_at = time.monotonic() + 0.3

    def on_track(self, track, pixels):
        if track is None:
            self.track = self.key = self.clock = None
            if self.shown != "idle":
                print("Nothing playing.")
                self.send("IDLE")
                self.shown = "idle"
                self.shown_playing = None
            return

        self.active = track.player
        key = track_key(track)
        if key != self.shown:
            print("Now playing: %s - %s (%s)" % (track.artist, track.title, track.player.app))
            self.send("IMG " + (pixels or bytes(192)).hex())  # no cover: dark, not IDLE (the Pico would start its game)
            self.send("TITLE " + title_text(track.title))  # scrolls when the joystick is pressed
            self.shown = key
        if key != self.key:
            self.clock = None
            self.next_word = None
        if track.playing != self.shown_playing:
            self.send("PLAY 1" if track.playing else "PLAY 0")
            self.shown_playing = track.playing
        if track.volume is not None:
            if self.volume is not None and track.volume != self.volume:
                self.send("VOL %d" % track.volume)  # changed on the Mac itself
            self.volume = track.volume
        self.sync_clock(track)
        self.track, self.key = track, key
        if self.reported != key and key in self.songs:
            self.reported = key
            print("  Lyrics: found." if self.songs[key] else "  Lyrics: none found, showing the cover.")

    def sync_clock(self, track):
        """Follows the song position the app reports. The app answers with a
        little jitter, so small differences are smoothed instead of jumped."""
        if track.position is None:
            self.clock = None
            return
        if self.clock is not None and track.playing and self.track.playing:
            expected = self.song_time(track.asked_at)
            drift = track.position - expected
            if abs(drift) < CLOCK_JUMP:
                self.clock = (expected + 0.3 * drift, track.asked_at)
                return
        self.clock = (track.position, track.asked_at)

    def song_time(self, now):
        position, at = self.clock
        return position + (now - at) if self.track.playing else position

    def send_words(self, now):
        """Sends each word of the lyrics to the Lumatrix just before it is sung."""
        song = self.songs.get(self.key)
        if not (self.symbols_on and song and self.clock and self.track.playing):
            self.next_word = None
            return
        t = self.song_time(now) + self.lyrics_offset
        due = bisect.bisect_right(song.cues, t, key=lambda cue: cue[0])
        if self.next_word is None or due < self.next_word:
            self.next_word = due  # just started, or jumped back: start from here
            return
        cues = song.cues
        for k in range(self.next_word, due):
            start, word = cues[k]
            word = clean_word(word)
            if word and t - start < WORD_LATE:
                # The next word goes along, so the Pico can show a stop sign for "don't cry"
                after = clean_word(cues[k + 1][1]) if k + 1 < len(cues) and cues[k + 1][0] - start < NEXT_WORD_S else ""
                self.send(("WORD %s %s" % (word, after)).rstrip())
        self.next_word = due

    def now_playing(self):
        tracks = []
        for player in self.players:
            if not player.running():
                continue
            try:
                track = player.now_playing()
            except AppleScriptError as e:
                self.warn("Couldn't ask %s what's playing: %s" % (player.app, e))
                continue
            if track:
                tracks.append(track)
        if not tracks:
            return None
        # Prefer a player that is playing, then the one used last
        tracks.sort(key=lambda t: (not t.playing, t.player is not self.active))
        return tracks[0]

    def cover_for(self, track):
        key = (track.player.app, track.artist, track.album or track.track_id)
        if key not in self.covers:
            self.covers[key] = track.player.cover(track) or itunes_cover(track)
        try:
            pixels = cover_pixels(self.covers[key], self.style) if self.covers[key] else None
        except OSError:
            pixels = None  # not an image Pillow understands
        if pixels is None:
            print("  (no cover found)")
        return pixels

    def warn(self, message):
        if message not in self.warned:
            self.warned.add(message)
            print(message)
            if "-1743" in message:
                print("  Allow it in System Settings > Privacy & Security > Automation.")


def find_port():
    for port in list_ports.comports():
        if port.vid == PICO_USB_VENDOR:
            return port.device
    found = sorted(glob.glob("/dev/cu.usbmodem*"))
    return found[0] if found else None


def main():
    parser = argparse.ArgumentParser(description="Show the album cover and symbols for the lyrics on the Lumatrix.")
    parser.add_argument("--port", help="serial port of the Lumatrix (found automatically)")
    parser.add_argument("--style", choices=list(STYLES), default="auto", help="how covers are pixelated")
    parser.add_argument(
        "--lyrics-offset",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="shift the symbols: positive shows them earlier, negative later",
    )
    args = parser.parse_args()

    print("Lumatrix Emoji. Press Ctrl+C to quit.")
    print("Cover style: %s (%s)." % (args.style, STYLES[args.style][1]))
    last_problem = None
    while True:
        name = args.port or find_port()
        if not name:
            if last_problem != "missing":
                print("Waiting for the Lumatrix... (is it plugged in?)")
                last_problem = "missing"
            time.sleep(1)
            continue
        try:
            with serial.Serial(name, 115200, timeout=0, exclusive=True) as port:
                last_problem = None
                bridge = Bridge(port, args.style, args.lyrics_offset)
                try:
                    bridge.run()
                except KeyboardInterrupt:
                    try:
                        bridge.send("IDLE")  # leave the note on the Lumatrix
                    except serial.SerialException:
                        pass
                    raise
        except serial.SerialException as e:
            if last_problem != str(e):
                print("Can't talk to the Lumatrix on %s (%s)." % (name, e))
                print("If Thonny is open, close it. Retrying...")
                last_problem = str(e)
            time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye.")
