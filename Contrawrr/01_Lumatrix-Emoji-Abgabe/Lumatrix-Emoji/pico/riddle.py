# Emoji-Rätsel: the game the Lumatrix plays without a laptop.
#
# The brain (wordmodel.py) turns a saying or a title into symbols, live,
# word by word. You guess it aloud, then press to see the answer.
# When the brain picks a wrong symbol you can correct it: a double press
# shows its next guess, holding the press confirms the one showing, and the
# brain remembers it (TinyBrain.teach) for this word and for words close to
# it, in every later riddle and in the music mode.
#
# Joystick: right/left = next/previous riddle, press = show the answer,
# double press = "wrong symbol" (the brain's next guess), hold the press =
# "right, remember it", hold it 3 s = forget everything taught.

from time import ticks_add, ticks_diff

from font import SCROLL_PX_PER_S, text_columns

# 37 riddles, from "easy" to "wait, what?".
RIDDLES = (
    "time is money",
    "fire and ice",
    "heaven and hell",
    "it's raining cats and dogs",
    "singing in the rain",
    "fly me to the moon",
    "sun moon and stars",
    "ring of fire",
    "highway to hell",
    "money can't buy love",
    "kiss from a rose",
    "island in the sun",
    "key to my heart",
    "king of the world",
    "dancing queen",
    "drive me crazy",
    "love at first sight",
    "ghost in the machine",
    "walking on sunshine",
    "dancing in the dark",
    "snake in the grass",
    "fish out of water",
    "rocket to the moon",
    "happy birthday",
    "stars in your eyes",
    "eye of the storm",
    "tears in heaven",
    "heart on fire",
    "smoke on the water",
    "candle in the wind",
    "time flies",
    "crying in the rain",
    "boys don't cry",
    "butterfly kisses",
    "earth wind and fire",
    "brain freeze",
    "peace and love",
)
SYMBOL_MS = 1500  # each clue
GAP_MS = 250  # dark between two clues, so two equal symbols read as two
LOOP_PAUSE_MS = 1500  # before the clues start over
MAX_TYPED = 60  # characters of a typed sentence
GUESSES = 5  # a double press steps through this many of the brain's guesses
FEEDBACK_MS = 600


class QuizMaster:
    """Hosts the Emoji-Rätsel: shows a saying's clues, reveals it, takes corrections."""

    def __init__(self, brain, icons, now):
        self.brain = brain
        self.icons = icons  # names the Pico has pictures for
        self.index = 0
        self.typed = None  # your own sentence (typed in Thonny's shell), instead of RIDDLES
        self.feedback = None  # (what, when): "taught", "next" or "forgot"
        self.load(now)

    def text(self):
        """The riddle on stage: your typed sentence, or one of RIDDLES."""
        return self.typed or RIDDLES[self.index]

    def ask(self, sentence, now):
        """Your own riddle: the brain turns your sentence into emojis for your
        friends to guess. If no word has an emoji, the sentence just scrolls by."""
        self.typed = sentence[:MAX_TYPED]
        self.load(now)
        if not self.clues:
            self.reveal(now)

    def load(self, now):
        """Asks the brain for the clues: [word, its guesses best first, choice]."""
        self.clues = []
        words = self.text().split()
        for k, word in enumerate(words):
            if "stop" in self.icons and self.brain.negates(word, " ".join(words[k + 1 : k + 2])):
                self.clues.append([word, ["stop"], 0])  # "can't buy" -> stop sign
                continue
            name, _ = self.brain.guess(word)  # taught words count too
            if name is None:
                continue
            v = self.brain.vector(word)
            guesses = [self.brain.names[i] for _, i in self.brain.ranked(v)[:GUESSES]]
            if name not in guesses:
                guesses.insert(0, name)
            self.clues.append([word, guesses, guesses.index(name)])
        self.start = now
        self.reveal_at = None

    def move(self, step, now):
        """The next (step 1) or previous (step -1) riddle."""
        self.index = (self.index + step) % len(RIDDLES)
        self.typed = None
        self.load(now)

    def reveal(self, now):
        """Scrolls the answer by."""
        self.reveal_at = now

    def on_stage(self, now):
        """(clue whose turn it is or None, ms since its turn began) in the clue loop."""
        per = SYMBOL_MS + GAP_MS
        t = ticks_diff(now, self.start) % (per * len(self.clues) + LOOP_PAUSE_MS)
        k = t // per
        return (self.clues[k] if k < len(self.clues) else None), t % per

    def current(self, now):
        """What to show: ("symbol", (name, since)), ("gap", None) or
        ("text", 8 columns)."""
        if self.reveal_at is not None:
            cols = text_columns(self.text())
            off = ticks_diff(now, self.reveal_at) * SCROLL_PX_PER_S // 1000
            if off + 8 < len(cols):
                return "text", cols[off : off + 8]
            self.reveal_at = None
            self.start = now
        clue, into = self.on_stage(now)
        if clue is None or into >= SYMBOL_MS or clue[1][clue[2]] not in self.icons:
            return "gap", None  # between clues, before the loop starts over, or no picture
        return "symbol", (clue[1][clue[2]], ticks_add(now, -into))

    def clue_at(self, now):
        """The clue showing (or in the gap after it), or None."""
        return None if self.reveal_at is not None else self.on_stage(now)[0]

    def wrong(self, now):
        """Double press: the brain's next guess for the showing word (after
        the last guess it starts over)."""
        clue = self.clue_at(now)
        if clue is None:
            return
        clue[2] = (clue[2] + 1) % len(clue[1])
        self.feedback = ("next", now)

    def right(self, now):
        """Hold: the brain remembers that this word means the symbol showing."""
        clue = self.clue_at(now)
        if clue is None:
            return
        name = clue[1][clue[2]]
        if self.brain.guess(clue[0])[0] != name:
            self.brain.teach(clue[0], name)
        self.feedback = ("taught", now)

    def forget(self, now):
        """Hold 3 s: the brain forgets everything it was taught."""
        self.brain.forget()
        self.load(now)
        self.feedback = ("forgot", now)

    def feedback_at(self, now):
        """Why the border flashes right now ("taught", "next", "forgot"), or None."""
        if self.feedback is None or ticks_diff(now, self.feedback[1]) > FEEDBACK_MS:
            return None
        return self.feedback[0]
