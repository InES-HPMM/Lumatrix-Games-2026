"""Spotify: voice command detection and Web API flow against a fake Spotify."""
import json
import os
import tempfile
import threading
import time
import unittest
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
from unittest.mock import patch

from companion_pc import music, spotify
from companion_pc.actions import detect_action

CASES = (
    ("Spiel Bohemian Rhapsody", ("play", ("track", "Bohemian Rhapsody"))),
    ("Buddy, spiel mal Bohemian Rhapsody von Queen", ("play", ("track", "Bohemian Rhapsody Queen"))),
    ("Spiel meine Workout Playlist", ("play", ("playlist", "Workout"))),
    ("Play my chill playlist on Spotify", ("play", ("playlist", "chill"))),
    ("Spiel was von Queen", ("play", ("artist", "Queen"))),
    ("Play something by Taylor Swift", ("play", ("artist", "Taylor Swift"))),
    ("Spiel das Album Thriller", ("play", ("album", "Thriller"))),
    ("Play some jazz music", ("play", ("genre", "jazz"))),
    ("Pause die Musik", ("pause",)), ("Mach die Musik aus", ("pause",)), ("Stop the music", ("pause",)),
    ("Nächster Song", ("next",)), ("Skip this song", ("next",)), ("Spiel ein anderes Lied", ("next",)),
    ("Vorheriger Song", ("previous",)), ("Go back a song", ("previous",)),
    ("Mach die Musik wieder an", ("resume",)), ("Spiel Musik", ("resume",)), ("Resume", ("resume",)),
    ("Was läuft gerade?", ("now",)), ("What's playing?", ("now",)),
    ("Lauter bitte", ("volume_up",)), ("Turn it down", ("volume_down",)),
    # Real Whisper transcripts from a test session:
    ("I play Michael Jackson Thriller.", ("play", ("track", "Michael Jackson Thriller"))),
    ("Rest Play.", ("resume",)), ("Start the music.", ("resume",)), ("Those are the next ones.", ("next",)),
    ("Next song please.", ("next",)), ("Start this song.", ("resume",)), ("Resumes the song.", ("resume",)),
    ("Press Play.", ("resume",)), ("Rest Play on Spotify.", ("resume",)),
    ("Play.", ("resume",)), ("Pause.", ("pause",)), ("Stop!", ("pause",)), ("Next.", ("next",)),
    # Pet commands and normal talk stay untouched:
    ("I play football every week.", None), ("Lets play.", None),
    ("Mach mal Pause.", None), ("Lass uns spielen!", None), ("Spiel mit mir!", None),
    ("Let's play a game", None), ("Play with me", None), ("Ich höre gerne Musik.", None),
    ("Wie ist das Wetter?", None),
)


class DetectTests(unittest.TestCase):
    def test_commands(self):
        for text, expected in CASES:
            self.assertEqual(music.detect_music(text), expected, text)

    def test_pet_commands_still_work(self):
        self.assertEqual(detect_action("Mach mal Pause."), "rest")
        self.assertEqual(detect_action("Spiel mit mir!"), "play")


class FakeSpotify:
    """Routes spotify.http calls; records them."""

    def __init__(self):
        self.calls = []
        self.devices = [{"id": "web", "name": "Web Player (Microsoft Edge)", "type": "Computer", "is_active": True},
                        {"id": "pc1", "name": "MYPC", "type": "Computer", "is_active": False},
                        {"id": "phone", "name": "Pixel 8", "type": "Smartphone", "is_active": False}]
        self.active = False
        self.premium = True
        self.expired_token = None

    def __call__(self, method, url, params=None, form=None, body=None, token=None):
        path = urlparse(url).path
        query = parse_qs(urlparse(url).query)
        self.calls.append((method, path, params, body, query))
        if url == spotify.TOKEN_URL:
            if form["grant_type"] == "refresh_token" and form["refresh_token"] != "R1":
                return 400, {"error": "invalid_grant"}
            return 200, {"access_token": "A2", "expires_in": 3600, "refresh_token": "R1"}
        if token == self.expired_token:
            return 401, {"error": {"status": 401, "message": "expired"}}
        if path.endswith("/search"):
            kind = params["type"]
            return 200, {kind + "s": {"items": [{"uri": "spotify:{}:1".format(kind), "name": "Bohemian Rhapsody",
                                                 "artists": [{"name": "Queen"}],
                                                 "album": {"uri": "spotify:album:opera"}}]}}
        if path.endswith("/me/playlists"):
            return 200, {"items": [None, {"uri": "spotify:playlist:w", "name": "My Workout Mix"}]}
        if path.endswith("/devices"):
            return 200, {"devices": self.devices}
        if method == "PUT" and path.endswith("/me/player"):  # transfer playback
            self.active = True
            self.transferred = body
            return 204, None
        if path.endswith("/currently-playing"):
            return 200, {"is_playing": True, "item": {"name": "Song", "artists": [{"name": "Band"}]}}
        if not self.premium:
            return 403, {"error": {"status": 403, "message": "Player command failed: Premium required",
                                   "reason": "PREMIUM_REQUIRED"}}
        if not self.active and "device_id" not in query:
            return 404, {"error": {"status": 404, "message": "No active device found", "reason": "NO_ACTIVE_DEVICE"}}
        return 204, None


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "spotify.json")
        with open(self.path, "w") as f:
            json.dump({"client_id": "c" * 32, "refresh_token": "R1", "access_token": "A1",
                       "expires_at": time.time() + 600}, f)
        self.fake = FakeSpotify()
        patcher = patch.object(spotify, "http", self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        sleep = patch.object(spotify.time, "sleep", lambda s: None)
        sleep.start()
        self.addCleanup(sleep.stop)
        env = patch.dict(os.environ, {"COMPUTERNAME": "MYPC"})
        env.start()
        self.addCleanup(env.stop)
        self.sp = spotify.Spotify(self.path)

    def test_not_configured(self):
        empty = spotify.Spotify(os.path.join(self.tmp.name, "none.json"))
        self.assertFalse(empty.configured)
        with self.assertRaisesRegex(spotify.SpotifyError, "spotify-login"):
            empty.pause()

    def test_play_track_on_this_pc_not_web_player(self):
        facts = music.run(self.sp, ("play", ("track", "Bohemian Rhapsody Queen")))
        self.assertEqual(facts, {"what": "'Bohemian Rhapsody' by Queen"})
        plays = [c for c in self.fake.calls if c[1].endswith("/me/player/play")]
        self.assertEqual(len(plays), 1)
        self.assertEqual(plays[0][4]["device_id"], ["pc1"])
        # Started inside its album, so "next song" has a following track.
        self.assertEqual(plays[0][3], {"context_uri": "spotify:album:opera", "offset": {"uri": "spotify:track:1"}})

    def test_device_choice(self):
        pick = lambda: self.sp._target()["id"]
        self.assertEqual(pick(), "pc1")  # COMPUTERNAME match beats the active web player
        self.sp.device = "pixel"
        self.assertEqual(pick(), "phone")  # explicit preference wins
        self.sp.device = None
        self.fake.devices = [d for d in self.fake.devices if d["id"] != "pc1"]
        self.assertEqual(pick(), "phone")  # another app before the web player
        self.fake.devices = self.fake.devices[:1]
        self.assertEqual(pick(), "web")  # web player only as last resort

    def test_skip_moves_playback_to_this_pc_first(self):
        music.run(self.sp, ("next",))
        self.assertEqual(self.fake.transferred, {"device_ids": ["pc1"], "play": True})

    def test_own_playlist_preferred(self):
        self.fake.active = True
        self.assertEqual(music.run(self.sp, ("play", ("playlist", "workout"))), {"what": "'My Workout Mix'"})
        play = [c for c in self.fake.calls if c[1].endswith("/play")][-1]
        self.assertEqual(play[3], {"context_uri": "spotify:playlist:w"})

    def test_next_reports_song_and_pause_without_device_is_ok(self):
        self.fake.active = True
        self.assertEqual(music.run(self.sp, ("next",))["what"], "'Song' by Band")
        self.fake.active = False
        self.assertEqual(music.run(self.sp, ("pause",)), {"what": None})

    def test_errors(self):
        self.fake.devices = []
        with self.assertRaisesRegex(spotify.SpotifyError, "Spotify-App starten"):
            music.run(self.sp, ("resume",))
        self.fake.devices = [{"id": "pc1", "name": "MYPC", "type": "Computer", "is_active": True}]
        self.fake.active, self.fake.premium = True, False
        with self.assertRaisesRegex(spotify.SpotifyError, "Premium"):
            music.run(self.sp, ("next",))

    def test_expired_token_is_refreshed_and_saved(self):
        self.fake.active = True
        self.fake.expired_token = "A1"
        music.run(self.sp, ("next",))
        with open(self.path) as f:
            self.assertEqual(json.load(f)["access_token"], "A2")

    def test_login_with_pkce_callback(self):
        os.remove(self.path)
        sp = spotify.Spotify(self.path)
        urls = []

        def browser():
            while not urls:
                time.sleep(0.01)
            query = parse_qs(urlparse(urls[0]).query)
            self.assertEqual(query["code_challenge_method"], ["S256"])
            self.assertNotIn("client_secret", query)
            urlopen("{}?code=CODE&state={}".format(spotify.REDIRECT_URI, query["state"][0]), timeout=5).read()
        thread = threading.Thread(target=browser)
        thread.start()
        sp.login("a" * 32, open_browser=False, timeout=10,
                 log=lambda line: urls.append(line) if line.startswith("https://") else None)
        thread.join()
        self.assertTrue(sp.configured)
        with open(self.path) as f:
            saved = json.load(f)
        self.assertEqual((saved["client_id"], saved["refresh_token"]), ("a" * 32, "R1"))
        with self.assertRaisesRegex(spotify.SpotifyError, "Client-ID"):
            sp.login("not-an-id", open_browser=False)


if __name__ == "__main__":
    unittest.main()


class HonestyTests(unittest.TestCase):
    def test_unclear_command_is_flagged(self):
        self.assertTrue(music.maybe_music("Ich bin der Nächste."))
        self.assertFalse(music.maybe_music("Ich höre gerne Musik."))
        self.assertFalse(music.maybe_music("Erzähl mir bitte eine lange Geschichte über Drachen und Ritter heute"))

    def test_skip_waits_for_new_title(self):
        sp = spotify.Spotify.__new__(spotify.Spotify)
        answers = iter([{"item": {"id": "a", "name": "Old"}}, None, {"item": {"id": "a", "name": "Old"}},
                        {"item": {"id": "a", "name": "Old"}}, {"item": {"id": "b", "name": "New"}}])
        sp.api = lambda method, path, **kw: next(answers)
        sp._with_device = lambda method, path, body=None: None
        with patch.object(spotify.time, "sleep", lambda s: None):
            facts = sp.next()
        self.assertEqual((facts["what"], facts["changed"]), ("'New'", True))
        answers = iter([{"item": {"id": "a", "name": "Beat It", "artists": [{"name": "Michael Jackson"}]},
                         "is_playing": True}] * 7)
        with patch.object(spotify.time, "sleep", lambda s: None):
            facts = sp.next()
        self.assertFalse(facts["changed"])
        self.assertEqual(music.outcome(("next",), facts), "same")  # honest: still the same song
        self.assertIn("immer noch 'Beat It' von Michael Jackson", music.reply("same", "de", **facts)[0])


class ReplyTests(unittest.TestCase):
    def test_replies_use_only_real_facts(self):
        text, face, anim = music.reply("play", "en", what="'Thriller' by Michael Jackson")
        self.assertIn("'Thriller' by Michael Jackson", text)
        self.assertEqual((face, anim), ("happy", "note"))
        text, face, _ = music.reply("failed", "de", reason="Nichts gefunden fuer 'Repkovier'")
        self.assertTrue(text.startswith("Oh nein, das hat nicht geklappt."))
        self.assertIn("Repkovier", text)
        self.assertEqual(face, "sad")
        self.assertEqual(music.outcome(("resume",), {"what": None}), "resume_plain")
        self.assertEqual(music.outcome(("now",), {"what": "'X'", "playing": False}), "now_paused")
        self.assertEqual(music.outcome(("volume_up",), {"volume": 60}), "volume_up")
        for lang in ("de", "en"):
            for kind in music.LOOKS:
                self.assertTrue(music.reply(kind, lang, what="'X'", volume=50, reason="r")[0])

    def test_session_transcripts(self):
        cases = (("Play House, Music.", ("play", ("genre", "House"))),
                 ("Play, Drake, God's Plan.", ("play", ("track", "Drake God's Plan"))),
                 ("Start the playlist, Repkovier.", ("play", ("playlist", "Repkovier"))),
                 ("Start the game", None))
        for text, expected in cases:
            self.assertEqual(music.detect_music(text), expected, text)
