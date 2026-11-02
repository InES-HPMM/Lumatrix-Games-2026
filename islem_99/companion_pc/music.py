"""Recognise music voice commands (German / English) for Spotify.

Like actions.py rule based: a music word or a sentence starting with
"spiel"/"play" is needed, so "Mach mal Pause" (pet rest) and "Lass uns spielen"
(star game) keep working.
"""
import random
import re

MUSIC = r"(musik|music|song|songs|lied|lieder|track|titel|spotify)"
I = re.IGNORECASE

COMMANDS = (
    ("now", re.compile(r"\bwas (läuft|laeuft|spielt|hören wir|ist das für ein)\b.*\b(gerade|da|jetzt|song|lied)?"
                       r"|\bwelche[rsn]? (song|lied|titel)\b|\bwhat('?s| is) (playing|this song)\b"
                       r"|\bwhich song\b|\bwho sings\b|\bwer singt\b", I)),
    ("next", re.compile(r"\b(nächste[rns]?|naechste[rns]?|andere[rns]?|neue[rns]?) " + MUSIC + r"\b"
                        r"|\b" + MUSIC + r" (überspringen|ueberspringen|wechseln)\b|\bskip\w*\b|\bnext (song|track)\b"
                        r"|\b(another|different) (song|track)\b|\bthe next (one|ones)\b|^\W*next( one)?\W*$"
                        r"|^\W*(nächste[rns]?|weiter)\W*$", I)),
    ("previous", re.compile(r"\b(vorherige[rns]?|letzte[rns]?) " + MUSIC + r"\b|\b" + MUSIC + r" zurück\b"
                            r"|\bzurück zum (letzten|vorherigen) " + MUSIC + r"\b"
                            r"|\b(previous|last) (song|track)\b|\bgo back a (song|track)\b", I)),
    ("pause", re.compile(r"\b(pause|pausier\w*|stopp?|halt|aus|leise aus)\b.*\b" + MUSIC + r"\b"
                         r"|\b" + MUSIC + r"\b.*\b(pausieren|pause|stoppen|stopp?|anhalten|aus|ausmachen)\b"
                         r"|\b(pause|stop) (the )?(music|song|spotify)\b"
                         r"|^\W*(pause|stop|stopp|halt)( (it|please|bitte))?\W*$", I)),
    ("volume_up", re.compile(r"\blauter\b|\bvolume up\b|\bturn it up\b|\blouder\b", I)),
    ("volume_down", re.compile(r"\bleiser\b|\bvolume down\b|\bturn it down\b|\bquieter\b", I)),
    ("resume", re.compile(r"\b" + MUSIC + r" (an|weiter|fortsetzen)\b|\b(mach|schalt|spiel) (die )?" + MUSIC
                          + r" (wieder )?(an|weiter)\b|\bweiter ?spielen\b|\bresum\w*\b|\bunpause\b"
                          r"|\b(play|start|turn on) (the )?music\b|\b(press|hit|push) play\b"
                          r"|\bstart (this|the) (song|track)\b|\b(continue|keep) (playing|the music)\b"
                          r"|^\W*(?!(lets|let|we|wanna|i|you|to) )(\w+ )?play( on spotify| spotify| it| again)?\W*$"
                          r"|^\W*spotify( play)?\W*$"
                          r"|\bspiel(e)? (mal |doch |bitte )?(etwas |ein bisschen )?musik\b|\bmusik bitte\b", I)),
)

# "I play ..." is a common Whisper mishearing of "Play ..."; only accepted before a name.
PLAY_START = re.compile(r"^\W*(?:(?:hey |hi |hallo )?(?:buddy|badi|pixel buddy)\W+)?(?:kannst du |could you |can you )?"
                        r"(?P<i>i |and |ok |okay )?(?P<verb>spiel|spiele|play|start|starte|put on)[\s,]+"
                        r"(?:mal |doch |bitte |please |me |mir )*(?P<target>.+)", I)
MEDIA_WORD = re.compile(r"\b(playlist|play list|wiedergabeliste|album|song|lied|track|musik|music)\b", I)
# Command-like words: if one appears but nothing was recognised, tell the user instead of pretending.
MAYBE_MUSIC = re.compile(r"\b(play\w*|spotify|resum\w*|skip\w*|next|nächste\w*|pause|stopp?|press|start)\b", I)
NOT_MUSIC = re.compile(r"^(mit mir|mit uns|ein spiel|was mit mir|wir|zusammen|fangen|verstecken|a game|with me|"
                       r"with us|together|games?|tag|hide)\b", I)
FILLER = re.compile(r"\b(auf|on|in|bei|via) spotify\b|\bbitte\b|\bplease\b|[.!?]+$", I)


def parse_play(query):
    """'meine Workout Playlist' -> ("playlist", "workout"); 'was von Queen' -> ("artist", "Queen")."""
    # Whisper often adds commas ("Play House, Music."); they must not end up in the search.
    query = re.sub(r"\s+", " ", FILLER.sub(" ", query.replace(",", " "))).strip(" ,")
    match = re.match(r"^(?:(?:meine|meinen|my|die|the|eine|a) )?(.+?) ?(playlist|play list|wiedergabeliste)$", query, I) \
        or re.match(r"^(?:(?:meine|my|die|the) )?(?:playlist|wiedergabeliste) (.+)$", query, I)
    if match:
        return ("playlist", match.group(1).strip())
    match = re.match(r"^(?:das |the )?album (.+)$", query, I)
    if match:
        return ("album", match.group(1).strip())
    match = re.match(r"^(?:etwas|was|irgendwas|ein lied|einen song|musik|lieder|songs|something|anything|"
                     r"some music|music|a song|songs) (?:von|by) (.+)$", query, I)
    if match:
        return ("artist", match.group(1).strip())
    match = re.match(r"^(?:etwas|was|ein bisschen|some|a bit of)?\s*(.+?) ?(musik|music)$", query, I)
    if match and match.group(1):
        return ("genre", match.group(1).strip())
    return ("track", re.sub(r"\s+", " ", re.sub(r"\b(von|by)\b", " ", query, flags=I)).strip())


def detect_music(text):
    """Return ("pause",) / ("next",) / ("play", (kind, query)) / ... or None."""
    for name, pattern in COMMANDS:
        if pattern.search(text):
            return (name,)
    match = PLAY_START.search(text)
    if match:
        target = match.group("target").strip()
        if match.group("i") and not target[:1].isupper():
            return None  # "I play football" is not a request
        if match.group("verb").lower() in ("start", "starte") and not MEDIA_WORD.search(target):
            return None  # "Start the game" is not music
        if target and not NOT_MUSIC.match(target):
            return ("play", parse_play(target))
    return None


def maybe_music(text):
    """Short command-like sentence that was not understood (e.g. Whisper heard 'Rest play')."""
    return len(text.split()) <= 7 and bool(MAYBE_MUSIC.search(text))


REPLIES = {
    "de": {
        "play": ("Juhu, jetzt läuft {what}!", "Los geht's: {what}!", "Gute Wahl! {what} läuft."),
        "resume": ("Musik läuft wieder: {what}!", "Weiter geht's mit {what}!"),
        "pause": ("Okay, Musik ist pausiert.", "Pssst, Pause!"),
        "resume_plain": ("Die Musik läuft wieder!",),
        "skipped_plain": ("Erledigt, Song gewechselt!",),
        "next": ("Nächster Song: {what}!", "Weiter! Jetzt läuft {what}."),
        "previous": ("Zurück zu {what}!",),
        "same": ("Hmm, Spotify spielt immer noch {what}. Danach kommt wohl kein anderer Song.",),
        "now": ("Gerade läuft {what}.",),
        "now_paused": ("{what} ist gerade pausiert.",),
        "nothing": ("Gerade läuft nichts auf Spotify.",),
        "volume_up": ("Lauter! Jetzt {volume} Prozent.",),
        "volume_down": ("Etwas leiser, {volume} Prozent.",),
        "failed": ("Oh nein, das hat nicht geklappt. {reason}",),
        "not_connected": ("Spotify ist noch nicht mit mir verbunden.",),
        "unclear": ("Meintest du Musik? Das habe ich nicht verstanden. Sag zum Beispiel: "
                    "Spiel Thriller, Pause oder nächster Song.",),
    },
    "en": {
        "play": ("Yay, now playing {what}!", "Here we go: {what}!", "Great pick! {what} is on."),
        "resume": ("Music is back on: {what}!", "And we continue with {what}!"),
        "pause": ("Okay, music paused.", "Shhh, pause!"),
        "resume_plain": ("The music is back on!",),
        "skipped_plain": ("Done, song changed!",),
        "next": ("Next song: {what}!", "Skipped! Now playing {what}."),
        "previous": ("Back to {what}!",),
        "same": ("Hmm, Spotify is still playing {what}. There seems to be no other song after it.",),
        "now": ("Now playing {what}.",),
        "now_paused": ("{what} is paused right now.",),
        "nothing": ("Nothing is playing on Spotify right now.",),
        "volume_up": ("Louder! Now at {volume} percent.",),
        "volume_down": ("A bit quieter, {volume} percent.",),
        "failed": ("Oh no, that didn't work. {reason}",),
        "not_connected": ("Spotify is not connected to me yet.",),
        "unclear": ("Did you mean music? I didn't get that. Try for example: Play Thriller, Pause or Next song.",),
    },
}
# Face and animation for each kind of reply (Pico faces / link.ANIMS).
LOOKS = {"play": ("happy", "note"), "resume": ("happy", "note"), "next": ("happy", "note"),
         "previous": ("happy", "note"), "now": ("happy", "note"), "pause": ("neutral", "none"), "resume_plain": ("happy", "note"), "skipped_plain": ("happy", "note"),
         "volume_up": ("happy", "none"), "volume_down": ("neutral", "none"), "same": ("neutral", "look"),
         "now_paused": ("neutral", "none"), "nothing": ("neutral", "look"), "failed": ("sad", "none"),
         "not_connected": ("sad", "none"), "unclear": ("neutral", "look")}


def reply(kind, lang="de", **facts):
    """Fixed sentence with real Spotify facts: (text, face, animation). No AI, nothing invented."""
    lang = "en" if lang == "en" else "de"
    what = facts.get("what") or ""
    if lang == "de":
        what = what.replace("' by ", "' von ")
    text = random.choice(REPLIES[lang][kind]).format(what=what, volume=facts.get("volume"),
                                                     reason=facts.get("reason", ""))
    return text.strip(), LOOKS[kind][0], LOOKS[kind][1]


def outcome(command, result):
    """Which reply fits a successful command result."""
    name = command[0]
    if name in ("volume_up", "volume_down"):
        return name
    if name == "pause":
        return "pause"
    if not result.get("what"):  # Spotify did not report a song
        return {"resume": "resume_plain", "next": "skipped_plain", "previous": "skipped_plain"}.get(name, "nothing")
    if name in ("next", "previous") and not result.get("changed"):
        return "same"
    if name == "now" and not result.get("playing"):
        return "now_paused"
    return name


def run(spotify, command):
    """Execute a detected command; returns Spotify facts (see Spotify._now)."""
    name = command[0]
    if name == "play":
        return spotify.play(command[1])
    if name == "volume_up":
        return spotify.volume(15)
    if name == "volume_down":
        return spotify.volume(-15)
    return {"pause": spotify.pause, "resume": spotify.resume, "next": spotify.next,
            "previous": spotify.previous, "now": spotify.now_playing}[name]()
