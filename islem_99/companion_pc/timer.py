"""Timer voice commands (German / English); the countdown itself runs on the Pico.

Rule based like music.py: "Stell einen Timer fuer 15 Minuten", "Timer abbrechen",
"Wie lange noch?". Replies are fixed sentences, so Buddy never claims a timer
that the Pico did not really start.
"""
import random
import re

I = re.IGNORECASE
MAX_S = 99 * 60  # Two digits on the matrix (pixel_buddy/link.MAX_TIMER_S).
TIMER = r"\b(timer|countdown|kurzzeitwecker|eieruhr)\b"
REMIND = r"\b(erinnere|erinner|weck|wecke|remind|wake) (mich|me|me up) in\b"
START_VERB = re.compile(r"\b(stell\w*|setz\w*|start\w*|mach \w+ timer|set|new|neue[rn]?)\b", I)
CANCEL = re.compile(TIMER + r".*\b(ab|abbrechen|stopp?\w*|aus\w*|löschen|loeschen|beenden|weg|"
                    r"cancel\w*|stop\w*|delete|end|off|clear)\b"
                    r"|\b(brich|stopp?e?|stop|cancel|lösch\w*|loesch\w*|beende|clear|end|delete|kill)\b.*" + TIMER, I)
LEFT = re.compile(TIMER + r".*\b(noch|übrig|uebrig|left|remaining|status)\b"
                  r"|\bwie (lange|viel zeit)\b.*\b(noch|übrig|uebrig)\b|\bhow (long|much time)\b.*\b(left|remaining)\b", I)

NUMBERS = {
    "null": 0, "zero": 0, "ein": 1, "eine": 1, "einen": 1, "einer": 1, "eins": 1, "one": 1, "a": 1, "an": 1,
    "zwei": 2, "two": 2, "drei": 3, "three": 3, "vier": 4, "four": 4, "fünf": 5, "fuenf": 5, "five": 5,
    "sechs": 6, "six": 6, "sieben": 7, "seven": 7, "acht": 8, "eight": 8, "neun": 9, "nine": 9,
    "zehn": 10, "ten": 10, "elf": 11, "eleven": 11, "zwölf": 12, "zwoelf": 12, "twelve": 12,
    "dreizehn": 13, "thirteen": 13, "vierzehn": 14, "fourteen": 14, "fünfzehn": 15, "fuenfzehn": 15,
    "fifteen": 15, "sechzehn": 16, "sixteen": 16, "siebzehn": 17, "seventeen": 17, "achtzehn": 18,
    "eighteen": 18, "neunzehn": 19, "nineteen": 19, "zwanzig": 20, "twenty": 20, "dreißig": 30,
    "dreissig": 30, "thirty": 30, "vierzig": 40, "forty": 40, "fünfzig": 50, "fuenfzig": 50, "fifty": 50,
    "sechzig": 60, "sixty": 60, "siebzig": 70, "seventy": 70, "achtzig": 80, "eighty": 80,
    "neunzig": 90, "ninety": 90,
}
UNITS = ((3600, r"stunden?|std|hours?|hrs?|h"), (60, r"minuten?|minutes?|mins?"),
         (1, r"sekunden?|seconds?|sek|secs?"))
UNIT = "|".join(pattern for _, pattern in UNITS)
WORD = "|".join(sorted(NUMBERS, key=len, reverse=True))
PHRASES = (
    (r"\b(eine )?halbe stunde\b|\b(a )?half (an )?hour\b", "30 minuten"),
    (r"\b(eine )?dreiviertel ?stunde\b|\bthree quarters of an hour\b", "45 minuten"),
    (r"\b(eine )?viertel ?stunde\b|\b(a )?quarter (of an )?hour\b", "15 minuten"),
    (r"\b(an|one) hour and a half\b|\b(anderthalb|eineinhalb) stunden?\b|\bone and a half hours?\b", "90 minuten"),
)


def _digits(text):
    """'fünfundzwanzig Minuten' -> '25 minuten', 'zweieinhalb Stunden' -> '2.5 stunden'."""
    text = text.lower().replace("-", " ")
    for pattern, value in PHRASES:
        text = re.sub(pattern, value, text)

    def compound(match):
        unit, tens = match.group(1), match.group(2)
        if unit in NUMBERS and tens in NUMBERS:
            return str(NUMBERS[unit] + NUMBERS[tens])
        return match.group(0)
    text = re.sub(r"\b(\w+?)und(zwanzig|dreißig|dreissig|vierzig|fünfzig|fuenfzig|sechzig|siebzig|achtzig|neunzig)\b",
                  compound, text)
    text = re.sub(r"\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety) (one|two|three|four|five|six|seven|"
                  r"eight|nine)\b", lambda m: str(NUMBERS[m.group(1)] + NUMBERS[m.group(2)]), text)
    text = re.sub(r"\b(" + WORD + r")einhalb\b", lambda m: str(NUMBERS[m.group(1)]) + ".5", text)
    text = re.sub(r"\b(" + WORD + r")\b(?=\s+(" + UNIT + r")\b)", lambda m: str(NUMBERS[m.group(1)]), text)
    return re.sub(r"\b(\d+) and a half\b", r"\1.5", text)


def parse_duration(text, bare_minutes=False):
    """Seconds in the sentence (sum of all parts), or None. 'Timer 15' -> 15 minutes."""
    text = _digits(text)
    total = 0.0
    found = False
    for factor, pattern in UNITS:
        for match in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(?:" + pattern + r")\b", text):
            total += float(match.group(1).replace(",", ".")) * factor
            found = True
    if not found and bare_minutes:
        match = re.search(r"\b(\d+)\b", text)
        if match:
            return int(match.group(1)) * 60
    return int(round(total)) if found else None


def detect_timer(text):
    """Return ("start", seconds) / ("cancel",) / ("left",) / ("ask",) or None."""
    has_timer = re.search(TIMER, text, I) is not None
    if not has_timer and not re.search(REMIND, text, I):
        return ("left",) if LEFT.search(text) and len(text.split()) <= 6 else None
    if CANCEL.search(text) and not START_VERB.search(text):
        return ("cancel",)
    seconds = parse_duration(text, bare_minutes=has_timer)
    if seconds is not None:
        return ("start", seconds)
    if LEFT.search(text):
        return ("left",)
    return ("ask",) if len(text.split()) <= 8 else None


def say_duration(seconds, lang="de"):
    """150 -> '2 Minuten und 30 Sekunden' / '2 minutes and 30 seconds'."""
    minutes, rest = divmod(int(seconds), 60)
    names = (("Minute", "Minuten", "Sekunde", "Sekunden", " und ") if lang == "de"
             else ("minute", "minutes", "second", "seconds", " and "))
    parts = []
    if minutes:
        parts.append("{} {}".format(minutes, names[0] if minutes == 1 else names[1]))
    if rest or not minutes:
        parts.append("{} {}".format(rest, names[2] if rest == 1 else names[3]))
    return names[4].join(parts)


REPLIES = {
    "de": {
        "start": ("Okay! Der Timer für {d} läuft.", "Alles klar, ich zähle {d} runter!"),
        "replaced": ("Okay, neuer Timer: {d}. Der alte ist gelöscht.",),
        "cancel": ("Okay, Timer abgebrochen.", "Timer gestoppt!"),
        "alarm_off": ("Okay, Alarm aus.",),
        "no_timer": ("Es läuft gerade kein Timer.",),
        "left": ("Noch {d}.", "Es bleiben noch {d}."),
        "done": ("Die Zeit ist um!",),
        "done_total": ("Die Zeit ist um! Dein Timer über {d} ist abgelaufen.",),
        "ask": ("Wie lange soll der Timer laufen? Sag zum Beispiel: Timer für 15 Minuten.",),
        "too_long": ("So lange kann ich nicht zählen, höchstens 99 Minuten.",),
        "too_short": ("Das ist zu kurz für einen Timer, mindestens eine Sekunde.",),
        "no_pico": ("Für den Timer brauche ich meine LED-Matrix, die ist gerade nicht verbunden.",),
    },
    "en": {
        "start": ("Okay! The timer for {d} is running.", "Got it, counting down {d}!"),
        "replaced": ("Okay, new timer: {d}. The old one is gone.",),
        "cancel": ("Okay, timer cancelled.", "Timer stopped!"),
        "alarm_off": ("Okay, alarm off.",),
        "no_timer": ("There is no timer running right now.",),
        "left": ("{d} left.", "Still {d} to go."),
        "done": ("Time's up!",),
        "done_total": ("Time's up! Your timer for {d} is done.",),
        "ask": ("How long should the timer run? Say for example: Timer for 15 minutes.",),
        "too_long": ("I can't count that long, 99 minutes at most.",),
        "too_short": ("That is too short for a timer, at least one second please.",),
        "no_pico": ("I need my LED matrix for the timer, and it is not connected right now.",),
    },
}
LOOKS = {"start": ("happy", "wink"), "replaced": ("happy", "wink"), "cancel": ("neutral", "none"),
         "alarm_off": ("happy", "none"), "no_timer": ("neutral", "look"), "left": ("neutral", "none"),
         "done": ("happy", "star"), "done_total": ("happy", "star"), "ask": ("neutral", "look"),
         "too_long": ("sad", "none"), "too_short": ("neutral", "look"), "no_pico": ("sad", "none")}


def reply(kind, lang="de", seconds=None):
    """Fixed sentence: (text, face, animation)."""
    lang = "en" if lang == "en" else "de"
    text = random.choice(REPLIES[lang][kind]).format(d=say_duration(seconds or 0, lang))
    return text[0].upper() + text[1:], LOOKS[kind][0], LOOKS[kind][1]


def control(link, command):
    """Send the command to the Pico; returns (reply kind, seconds) for reply()."""
    name = command[0]
    if name == "ask":
        return "ask", None
    if name == "start" and command[1] > MAX_S:
        return "too_long", None
    if name == "start" and command[1] < 1:
        return "too_short", None
    if not (link and link.ready):
        return "no_pico", None
    msg = {"cmd": "timer"}
    if name == "start":
        msg["s"] = command[1]
    elif name == "cancel":
        msg["s"] = 0
    answer = link.call(msg)
    if not answer or answer.get("ok") != "timer":
        return "no_pico", None
    if name == "start":
        link.timer_total = command[1]
        return ("replaced" if answer.get("was") else "start"), command[1]
    if name == "cancel":
        if answer.get("was"):
            return "cancel", None
        return ("alarm_off" if answer.get("alarm") else "no_timer"), None
    return ("left", answer["left"]) if answer.get("left") else ("no_timer", None)
