"""Recognise pet commands in what the user said (German / English).

Rule based on purpose: the small local model picked wrong actions in about half
of the tests, and an unwanted "sleep" is worse than a missed command. The AI is
only told what happened, so its reply matches the action and its result.
"""
import re

# Pet actions on the Pico (pixel_buddy/link.py ACTIONS, play.apply_action).
ACTIONS = ("feed", "pet", "rest", "play", "status", "sleep", "wake")

FOOD = (r"(essen|futter|snack|keks\w*|kuchen|apfel|äpfel|banane|karotte|rüebli|leckerli\w*|pizza"
        r"|schokolade|brot|food|snack|cookie|apple|banana|carrot|treat|cake|pizza|chocolate|bread)")

PATTERNS = (
    ("wake", r"\bwach\w* (doch |mal |endlich )?auf\b|\baufwachen\b|\bsteh (doch |mal )?auf\b"
             r"|\bguten morgen\b|\bwake (up|up now)\b|\bgood morning\b|\brise and shine\b"),
    ("sleep", r"\bgeh (jetzt |doch |mal |bitte )*(schlafen|ins bett|pennen)\b|\bab ins bett\b"
              r"|\bschlaf (jetzt |gut|schön|ein)"
              r"|\bleg dich (hin|schlafen)\b|\bgute nacht\b|\bzeit (zum|fürs) (schlafen|bett)\b"
              r"|\bgo (to )?(sleep|bed)\b|\bgood ?night\b|\btime (for|to) (bed|sleep)\b|\bsleep (now|tight|well)\b"),
    # Only requests and offers, never stories like "Ich habe Pizza gegessen".
    ("feed", r"\b(iss|friss|füttern|fütter|essenszeit)\b|\bzeit (zum|fürs) essen\b"
             r"|(^|[,:])\s*(please )?(eat|have)\b|\bfeed (you|buddy)\b|\btime to eat\b|\b(dinner|lunch|snack) ?time\b"
             r"|\b(hier|nimm|für dich|bitte ?schön|ich (geb|gebe) dir|magst du|willst du|möchtest du)\b.*" + FOOD
             + r"|\b(here|take|for you|do you want|would you like)\b.*" + FOOD),
    ("pet", r"streiche?l|\bkraul|knuddel|kuschel|umarm|t[äa]tschel|\bschmus"
            r"|\bpet you\b|\bpat\b|cuddle|\bhugs?\b|\bstroke\b|\bscratch"),
    ("play", r"\blass uns (was |etwas )?spielen\b|\bspielen wir\b|\b(willst|wollen|magst) (du|wir) spielen\b"
             r"|\bspiel(e)? mit mir\b|\blet'?s play\b|\b(wanna|want to) play\b|\bplay (a game|with me)\b"),
    ("rest", r"\bmach (mal |doch |kurz |eine |mal eine |mal kurz )*pause\b|\bruh dich (kurz |mal )?aus\b"
             r"|\bausruhen\b|\btake a (short |little )?break\b|\b(have|take) a rest\b|\brest a (bit|little)\b"),
    ("status", r"\bzeig (mir )?(deinen|den|mal deinen) status\b|\bstatus\b|\bwie geht'?s dir\b"
               r"|\bwie geht es dir\b|\bhow are you( feeling| doing)?\b|\bshow (me )?(your )?status\b"),
)
COMPILED = tuple((action, re.compile(pattern, re.IGNORECASE)) for action, pattern in PATTERNS)
NEGATION = re.compile(r"\b(nicht|kein|keine|nie|don'?t|do not|never|no)\b", re.IGNORECASE)

# What the AI is told after the Pico ran the action. Missing result = no Pico.
EVENTS = {
    "feed": "The user just fed you and you ate it happily.",
    "pet": "The user just petted and cuddled you.",
    "rest": "You are now taking a short 15 second rest.",
    "play": "Your star-catching game just started; the user plays with the joystick.",
    "status": "Your status bars are now shown on your face.",
    "sleep": "You are falling asleep now.",
    "wake": "You just woke up.",
}
FAILED = {
    "full": "You were offered food but you are completely full, so you politely refused.",
    "tired": "The user wants to play, but you are too tired or hungry to play right now.",
    "busy": "You are still busy with the last thing and could not do it yet.",
    "playing": "You are in the middle of your game and could not do that.",
    "resting": "You are resting right now and could not do that.",
    "sleeping": "You are asleep and only mumble sleepily; you did not do it.",
    "switch": "Your sleep switch is on, you cannot wake up until the user moves the switch.",
}


def detect_action(text):
    """Return the first matching action or None. Negated sentences are ignored."""
    for sentence in re.split(r"[.!?;\n]+", text):
        for action, pattern in COMPILED:
            match = pattern.search(sentence)
            if match and not NEGATION.search(sentence[:match.start()]):
                return action
    return None


def describe_event(action, result=None):
    """One line for the prompt about what just happened to Buddy."""
    if not action:
        return ""
    if result in FAILED:
        return "What just happened: " + FAILED[result]
    return "What just happened: " + EVENTS[action]
