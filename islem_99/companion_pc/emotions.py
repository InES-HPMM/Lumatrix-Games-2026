"""AI emotion vocabulary, mapped onto what the Pico can really draw.

Pico faces (pixel_buddy/faces.py): neutral, happy, sad.
Pico animations (pixel_buddy/link.py ANIMS + play.render_link):
  none, wink (happy wink), heart / star (existing icons),
  look (glances left/right), sleepy (existing dim sleep face).
The mouth moves only while the voice speaks ({"cmd": "talk"}), never as animation.
"""
import json
import math

# emotion: (Pico face, default animation)
EMOTIONS = {
    "neutral": ("neutral", "none"),
    "happy": ("happy", "wink"),
    "excited": ("happy", "star"),
    "love": ("happy", "heart"),
    "sad": ("sad", "none"),
    "curious": ("neutral", "look"),
    "sleepy": ("neutral", "sleepy"),
}
ANIMATIONS = ("none", "wink", "heart", "star", "look", "sleepy")
DEFAULT_INTENSITY = 0.6
MAX_REPLY = 1000

# Ollama structured output: the model must return exactly this object.
SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "emotion": {"type": "string", "enum": list(EMOTIONS)},
        "animation": {"type": "string", "enum": list(ANIMATIONS)},
        "intensity": {"type": "number"},
    },
    "required": ["reply", "emotion", "animation", "intensity"],
}


def parse(raw):
    """Validate model output. Never fails on bad emotion data; returns safe defaults.

    Returns a dict with reply, emotion, animation, intensity and a list 'fixed'
    naming the fields that had to be replaced.
    """
    fixed = []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        data = None
    if not isinstance(data, dict):
        # Plain text answer: keep the text, show a neutral face.
        data = {"reply": raw}
        fixed.append("json")
    reply = data.get("reply")
    reply = reply.strip()[:MAX_REPLY] if isinstance(reply, str) else ""
    emotion = data.get("emotion")
    emotion = emotion.strip().lower() if isinstance(emotion, str) else ""
    if emotion not in EMOTIONS:
        fixed.append("emotion")
        emotion = "neutral"
    animation = data.get("animation")
    animation = animation.strip().lower() if isinstance(animation, str) else ""
    if animation not in ANIMATIONS:
        fixed.append("animation")
        animation = EMOTIONS[emotion][1]
    intensity = data.get("intensity")
    if (isinstance(intensity, bool) or not isinstance(intensity, (int, float))
            or not math.isfinite(intensity)):
        fixed.append("intensity")
        intensity = DEFAULT_INTENSITY
    intensity = min(1.0, max(0.0, float(intensity)))
    return {"reply": reply, "emotion": emotion, "animation": animation,
            "intensity": intensity, "fixed": fixed}


def describe_pet(state):
    """One prompt line about Buddy's body from the Pico values [food, energy, joy]."""
    if not state:
        return ""
    food, energy, joy, sleeping = state
    notes = []
    if food >= 95:
        notes.append("completely full, refuse more food")
    elif food < 30:
        notes.append("hungry")
    if energy < 30:
        notes.append("very tired")
    if joy < 30:
        notes.append("a bit lonely")
    return ("Your body right now (mention it only if it matters or you are asked): food {}/100, energy {}/100, mood {}/100, {}{}.".format(
        food, energy, joy, "asleep" if sleeping else "awake",
        " (" + ", ".join(notes) + ")" if notes else ""))


def show_command(emotion, animation=None, intensity=DEFAULT_INTENSITY):
    """Build the whitelisted Pico command for an (already valid) emotion."""
    face, default = EMOTIONS[emotion]
    if animation not in ANIMATIONS:
        animation = default
    # Stronger feelings stay visible longer: 3 to 8 seconds.
    return {"cmd": "show", "face": face, "anim": animation,
            "ms": int(3000 + 5000 * intensity)}
