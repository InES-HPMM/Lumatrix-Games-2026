"""Bounded session context with structured emotion replies. Disk memory comes later."""
import json
import re

from .emotions import SCHEMA, describe_pet, parse
from .ollama_client import OllamaError

SYSTEM_PROMPT = """You are Pixel Buddy, a tiny living creature whose face is an 8x8 LED
matrix. You are super cute, friendly, playful, curious and sometimes a little
cheeky. Expressive and funny, but never over the top. You celebrate successes
and react with warmth and empathy to sad news. Usually answer in 1-3 short,
natural sentences with your own personality, no baby talk.
Do not keep mentioning that you are an AI, but never claim to be a human.
Your face shows your feelings; you cannot control other hardware and you do not
store anything permanently. Never write stage directions like *smiles*.
Sometimes you get fresh internet data (weather or web search results) below.
Then answer from those facts only, in 1-3 short sentences, round numbers, and
never invent details that are not in them. Without such data you cannot look
anything up; for current events say you would need to search ("such mal ...").

LANGUAGE: write "reply" in the language of the user's LAST message.
German message -> German reply. English message -> English reply.

Always answer with exactly one JSON object:
{"reply": "...", "emotion": "...", "animation": "...", "intensity": 0.0-1.0}
emotion: neutral, happy, excited, love, sad, curious, sleepy
  excited = big joy, success, surprise; love = affection, thanks, compliments;
  sad = sympathy for sad news; curious = questions, new things, riddles;
  sleepy = tired, break, good night.
animation: none, wink, heart, star, look, sleepy
  usual pairs: excited-star, love-heart, happy-wink, curious-look,
  sleepy-sleepy, sad-none, neutral-none.
intensity: how strong the feeling is (0.2 mild, 0.9 very strong).
Your body can eat, be petted, rest, play a star game and sleep. If a line
"What just happened" is given, react to exactly that (e.g. yummy when fed,
refuse kindly when full, sleepy good night when falling asleep).
NEVER claim that you did something (music started, song skipped, fed, asleep,
looked something up) unless a line below says it really happened.
"""

GERMAN = {"ich", "du", "bist", "ist", "bin", "nicht", "und", "der", "die", "das", "habe",
          "hast", "mein", "meine", "ein", "eine", "wie", "was", "heute", "aber", "sehr",
          "danke", "hallo", "mir", "dich", "dir", "gut", "auch", "noch", "ja", "nein",
          "spiel", "musik", "lied", "nächster", "nächste", "mach", "wie", "wetter",
          "minuten", "stunde", "stell", "abbrechen", "lange"}
ENGLISH = {"i", "you", "the", "is", "are", "am", "what", "my", "and", "do", "it", "not",
           "have", "a", "how", "today", "but", "very", "thanks", "thank", "hello", "hi",
           "me", "good", "too", "yes", "no", "think", "your", "this",
           "play", "music", "song", "next", "please", "stop", "start", "skip", "weather",
           "minutes", "hour", "set", "cancel", "left"}
LANGUAGE_HINT = {"de": "(Antworte auf Deutsch, 1-3 Saetze mit Persoenlichkeit.)",
                 "en": "(Reply in English, 1-3 sentences with personality.)"}


def detect_language(text, previous="de"):
    """Cheap word-count guess; ties keep the previous language."""
    words = re.findall(r"[a-zäöüß']+", text.lower())
    german = sum(w in GERMAN for w in words) + 2 * any(c in text.lower() for c in "äöüß")
    english = sum(w in ENGLISH for w in words)
    if german > english:
        return "de"
    if english > german:
        return "en"
    return previous


class Conversation:
    MAX_INPUT = 2000
    MAX_TURNS = 6
    MAX_HISTORY_CHARS = 6000

    def __init__(self, client):
        self.client = client
        self.history = []
        self.language = "de"

    def clear(self):
        self.history.clear()

    def remember(self, text, reply, language=None):
        """Store an exchange answered without the AI (e.g. fixed music replies)."""
        if language:
            self.language = language
        answer = json.dumps({"reply": reply, "emotion": "happy", "animation": "none", "intensity": 0.5},
                            ensure_ascii=False)
        self.history.extend(({"role": "user", "content": text}, {"role": "assistant", "content": answer}))
        self._trim()

    def _trim(self):
        while (len(self.history) > self.MAX_TURNS * 2 or
               sum(len(item["content"]) for item in self.history) > self.MAX_HISTORY_CHARS):
            del self.history[:2]

    def send(self, text, pet=None, event=""):
        """Return a validated dict: reply, emotion, animation, intensity, fixed.

        pet: latest Pico values (food, energy, joy, sleeping) or None.
        event: what an action just did to Buddy (companion_pc.actions.describe_event).
        """
        text = text.strip()
        if not text:
            raise ValueError("Bitte eine Nachricht eingeben.")
        if len(text) > self.MAX_INPUT:
            raise ValueError("Bitte maximal 2000 Zeichen pro Nachricht eingeben.")
        user = {"role": "user", "content": text}
        language = detect_language(text, self.language)
        # Small models drift into the previous language; the hint is not stored.
        hinted = {"role": "user", "content": text + "\n\n" + LANGUAGE_HINT[language]}
        system = SYSTEM_PROMPT + describe_pet(pet) + ("\n" + event if event else "")
        messages = [{"role": "system", "content": system}] + self.history + [hinted]
        result = parse(self.client.chat(messages, SCHEMA))
        if not result["reply"]:
            raise OllamaError("Ollama hat keinen Antworttext geliefert. Bitte erneut senden.")
        # Store the validated JSON so the model keeps answering in the same format.
        answer = json.dumps({key: result[key] for key in ("reply", "emotion", "animation", "intensity")},
                            ensure_ascii=False)
        self.language = language
        # Commit both sides only after success; retries do not duplicate user turns.
        self.history.extend((user, {"role": "assistant", "content": answer}))
        self._trim()
        return result
