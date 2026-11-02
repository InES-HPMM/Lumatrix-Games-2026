# TinyBrain: the Lumatrix's word model, which symbol a sung word means.
#
# model.bin (made on the Mac by model/build_model.py) holds a shrunk word
# embedding: every word that can mean a symbol, as DIMS small numbers
# (int8), sorted for binary search, plus one "prototype" vector per symbol.
# A word means the symbol whose prototype points the most the same way
# (cosine similarity), if that reaches the symbol's own bar: each symbol
# learned its bar from the data when the model was built.
#
# It also learns on the Pico: teach(word, symbol) stores the word's vector
# in taught.bin, and from then on that word, and words close to it, show
# the taught symbol (a few-shot memory next to the prototypes).
#
# Runs in MicroPython on the Pico, and in Python on the Mac for the tests.
#
# File layout (little-endian):
#   "LMX2", dims (u8), symbols (u8), word bytes (u8), pickiness x100 (u8),
#   words (u32), names length (u16), symbol names joined by "\n",
#   per symbol its bar x100 (u8), symbols x dims int8 prototypes, then per
#   word: the word padded with zero bytes, dims int8.

import struct
from array import array

try:
    from fastdot import dots  # machine code on the Pico
except Exception:  # Python on the Mac, or a MicroPython without viper

    def dots(v, blob, n, dims, out):
        for k in range(n):
            base = k * dims
            s = 0
            for i in range(dims):
                a = v[i]
                b = blob[base + i]
                s += (a - 256 if a > 127 else a) * (b - 256 if b > 127 else b)
            out[k] = s


RECORD_WORD = 12  # bytes for the word in each record; longer words are left out
# Negations, the words that turn the next word around ("don't cry"): a stop
# sign shows before the next word's symbol, but only if that word has one
# ("I don't know" shows nothing). The party poopers of every song.
NOPE_WORDS = (
    "don't", "dont", "not", "never", "no", "can't", "cant", "won't", "wont", "ain't", "aint",
    "didn't", "didnt", "doesn't", "doesnt", "isn't", "isnt", "wasn't", "wasnt",
)
TAUGHT_FILE = "taught.bin"
TAUGHT_CLOSE_ENOUGH = 0.62  # a taught word also counts for words at least this similar
NO_SYMBOL = 255  # taught label: this word shows nothing


# ── Spelling ── (lyrics are sloppy, the brain is not)
def normal(word):
    """The word as the model spells it: lowercase letters and apostrophes."""
    return "".join(c for c in word.lower() if "a" <= c <= "z" or c == "'")


# Other forms of a word, tried in turn when the model doesn't know it:
# (ending, replacement). Song lyrics drop the g ("burnin'"), and the model
# mostly stores one form of each word.
ENDINGS = (
    ("in'", "ing"),
    ("ied", "y"),
    ("ies", "y"),
    ("es", ""),
    ("s", ""),
    ("ing", ""),
    ("ing", "e"),
    ("ed", ""),
    ("ed", "e"),
)


def forms(word):
    """The word, then its other forms ("burnin'" -> "burning", "skies" -> "sky")."""
    yield word
    for ending, replacement in ENDINGS:
        if word.endswith(ending):
            form = word[: -len(ending)] + replacement
            if len(form) >= 3:  # "skies" -> "sky", but not "his" -> "hi"
                yield form


def norm_of(v, dims):
    """The length of an int8 vector."""
    out = array("i", [0])
    dots(v, v, 1, dims, out)
    return out[0] ** 0.5


# ── The brain ── (about 310 KB of flash, 10-15 ms of thinking per word)
class TinyBrain:
    """Guesses a word's symbol from model.bin, and learns from corrections.
    4000 words, 64 numbers each, and still smaller than one cat photo."""

    def __init__(self, path="model.bin", taught=TAUGHT_FILE):
        f = open(path, "rb")
        magic, self.dims, symbols, word_bytes, _, self.words = struct.unpack("<4sBBBBI", f.read(12))
        if magic != b"LMX2" or word_bytes != RECORD_WORD:
            raise ValueError("not a Lumatrix word model")
        size = struct.unpack("<H", f.read(2))[0]
        self.names = f.read(size).decode().split("\n")
        self.bars = [t / 100 for t in f.read(symbols)]
        self.protos = f.read(symbols * self.dims)  # one blob: symbol k at k * dims
        self.norms = [norm_of(self.protos[k * self.dims : (k + 1) * self.dims], self.dims) for k in range(symbols)]
        self.scores = array("i", [0] * symbols)
        self.record = RECORD_WORD + self.dims
        self.start = f.tell()
        self.file = f
        self.taught_path = taught
        self.taught = bytearray()  # taught vectors, one after the other
        self.labels = bytearray()  # their symbol index, or NO_SYMBOL
        try:
            with open(taught, "rb") as t:
                data = t.read()
            n = len(data) // (1 + self.dims)
            for k in range(n):
                rec = data[k * (1 + self.dims) : (k + 1) * (1 + self.dims)]
                self.labels.append(rec[0])
                self.taught += rec[1:]
        except OSError:
            pass

    def vector(self, word):
        """The numbers (dims bytes) of the word or another form of it, or None
        if the model doesn't know it."""
        for form in forms(normal(word)):
            found = self.lookup(form)
            if found is not None:
                return found
        return None

    def lookup(self, word):
        """The word's numbers, by binary search in model.bin, or None."""
        key = word.encode()
        if not key or len(key) > RECORD_WORD:
            return None
        key += b"\0" * (RECORD_WORD - len(key))
        f = self.file
        low, high = 0, self.words
        while low < high:
            middle = (low + high) // 2
            f.seek(self.start + middle * self.record)
            found = f.read(RECORD_WORD)
            if found == key:
                return f.read(self.dims)
            if found < key:
                low = middle + 1
            else:
                high = middle
        return None

    def ranked(self, v):
        """[(similarity, symbol index)] for a word vector, most similar first."""
        n = len(self.names)
        dots(v, self.protos, n, self.dims, self.scores)
        norm = norm_of(v, self.dims) or 1.0
        found = [(self.scores[k] / (norm * self.norms[k]), k) for k in range(n)]
        found.sort(reverse=True)
        return found

    def guess(self, word):
        """(symbol name or None, confidence) for a sung word. Confidence is the
        similarity relative to the symbol's own bar: 1.0 or more shows it."""
        v = self.vector(word)
        if v is None:
            return None, 0.0
        similarity, best = self.ranked(v)[0]
        confidence = similarity / self.bars[best]
        name = self.names[best] if confidence >= 1.0 else None
        taught = self.recall(v)
        if taught is not None and taught[0] >= similarity:  # a taught word at least as close wins
            closeness, label = taught
            name = None if label == NO_SYMBOL else self.names[label]
            return name, max(1.0, closeness / TAUGHT_CLOSE_ENOUGH)
        return name, confidence

    def percent(self, name, confidence):
        """How sure, from 0 to 100: 50 = exactly at the emoji's own bar (the
        least that shows), 100 = as close as the emoji's own keywords."""
        bar = self.bars[self.names.index(name)]
        if confidence < 1.0:
            p = 50 * confidence
        else:
            p = 50 + 50 * bar * (confidence - 1) / (1 - bar)
        return max(0, min(100, int(p + 0.5)))

    def negates(self, word, after):
        """True if word is a negation and the word after it has a symbol."""
        return bool(after) and normal(word) in NOPE_WORDS and self.guess(after)[0] is not None

    def recall(self, v):
        """(similarity, label) of the closest taught word, if close enough."""
        n = len(self.labels)
        if not n:
            return None
        out = array("i", [0] * n)
        dots(v, self.taught, n, self.dims, out)
        norm = norm_of(v, self.dims) or 1.0
        best = None
        for k in range(n):
            t = self.taught[k * self.dims : (k + 1) * self.dims]
            s = out[k] / (norm * (norm_of(t, self.dims) or 1.0))
            # A keyword's vector is its symbol's prototype, so a taught keyword
            # counts for the symbol's keywords, but not for the words near them
            need = 0.999 if self.is_prototype(t) else TAUGHT_CLOSE_ENOUGH
            if s >= need and (best is None or s >= best[0]):
                best = (s, self.labels[k])
        return best

    def is_prototype(self, v):
        """True if v is one of the symbols' prototypes (that is, a keyword's vector)."""
        at = self.protos.find(v)
        while at >= 0:
            if at % self.dims == 0:
                return True
            at = self.protos.find(v, at + 1)
        return False

    def teach(self, word, name):
        """Remember that word means the symbol name (None = no symbol).
        Returns False if the model doesn't know the word."""
        v = self.vector(word)
        if v is None:
            return False
        label = NO_SYMBOL if name is None else self.names.index(name)
        self.labels.append(label)
        self.taught += v
        try:
            with open(self.taught_path, "ab") as f:
                f.write(bytes([label]) + v)
        except OSError:
            pass
        return True

    def forget(self):
        """Forgets everything taught, taught.bin included. Like a goldfish, but on purpose."""
        self.taught = bytearray()
        self.labels = bytearray()
        try:
            import os

            os.remove(self.taught_path)
        except OSError:
            pass
