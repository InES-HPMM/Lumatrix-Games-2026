"""Builds the Pico's word model, pico/model.bin, from Apple's word embedding.

    python model/build_model.py

1. model/export_vectors.swift gets 300-number vectors for every symbol's
   keywords and their nearest neighbours (macOS's built-in English model).
2. Common words (model/stopwords.txt) are dropped: they never get a symbol.
3. PCA squeezes each vector from 300 to DIMS numbers, and each number is
   stored as one byte (int8), so the model fits on the Pico.
4. Each symbol gets a "prototype": the average of its keywords' vectors.
5. Each symbol learns its own bar from the data: PICKY times the average
   similarity of its CLOSEST most similar words. A tight symbol (rose) needs
   a closer word than a loose one (storm). A symbol's own keywords always
   show it. Words below STORE of the bar are dropped; the ones in between
   show nothing but are kept so they can be taught on the Pico.

On the Pico, pico/wordmodel.py looks a sung word up and picks the symbol
whose prototype is most similar. Needs numpy (pip install numpy).
"""

import os
import struct
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pico"))
from icons import ICONS  # noqa: E402
from wordmodel import RECORD_WORD, normal  # noqa: E402

DIMS = 64  # numbers per word on the Pico
NEIGHBOURS = 40  # related words taken per keyword (Apple returns at most 50)
PICKY = 0.85  # a word must be this close to a symbol, relative to the symbol's own closest words
CLOSEST = 5  # ...namely the average similarity of its CLOSEST most similar words
STORE = 0.7  # words this close are stored too (silent), so they can be taught on the Pico
OUT = os.path.join(ROOT, "pico", "model.bin")


def export_vectors(keywords):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(keywords))
        path = f.name
    try:
        result = subprocess.run(
            ["swift", os.path.join(HERE, "export_vectors.swift"), path, str(NEIGHBOURS)],
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        os.remove(path)
    words, vectors = [], []
    for line in result.stdout.splitlines():
        word, numbers = line.split("\t")
        words.append(word)
        vectors.append([float(v) for v in numbers.split()])
    return words, np.array(vectors)


def unit(rows):
    return rows / np.linalg.norm(rows, axis=-1, keepdims=True)


def quantize(rows):
    return np.clip(np.round(unit(rows) * 127), -127, 127).astype(np.int8)


def main():
    keywords = {name: entry[0].split() for name, entry in ICONS.items()}
    every_keyword = sorted({k for ks in keywords.values() for k in ks})
    print("Asking Apple's word embedding about %d keywords..." % len(every_keyword))
    words, vectors = export_vectors(every_keyword)
    vectors = unit(vectors)
    index = {w: i for i, w in enumerate(words)}
    missing = [k for k in every_keyword if k not in index]
    if missing:
        print("  not in the embedding:", " ".join(missing))

    # Symbol prototypes: the average of their keywords
    names = list(ICONS)
    full_protos = unit(np.array([vectors[[index[k] for k in keywords[n] if k in index]].mean(axis=0) for n in names]))

    stop = set(open(os.path.join(HERE, "stopwords.txt")).read().split())
    keep = [i for i, w in enumerate(words) if normal(w) == w and w not in stop and len(w) <= RECORD_WORD]
    print("  %d words, %d after dropping common words and odd spellings" % (len(words), len(keep)))
    x = vectors[keep]
    kept = [words[i] for i in keep]

    # PCA from 300 to DIMS numbers
    mean = x.mean(axis=0)
    _, singular, components = np.linalg.svd(x - mean, full_matrices=False)
    basis = components[:DIMS]
    explained = (singular[:DIMS] ** 2).sum() / (singular**2).sum()
    small = quantize((x - mean) @ basis.T)
    protos = quantize((full_protos - mean) @ basis.T)

    # What the Pico will compute, integer for integer
    sims = (small.astype(np.int32) @ protos.astype(np.int32).T) / (
        np.linalg.norm(small.astype(float), axis=1, keepdims=True) * np.linalg.norm(protos.astype(float), axis=1)
    )
    # Each symbol gets its own bar: tight symbols (rose: roses, petals, bouquet)
    # need a higher similarity than loose ones (storm: thunder, lightning).
    # This keeps vague words like "feel" (sad) or "sky" (rain) from showing.
    closest = np.sort(sims, axis=0)[-CLOSEST:].mean(axis=0)
    thresholds = np.round(PICKY * closest, 2)  # rounded so the Pico agrees exactly

    # A symbol's own keywords always show it: they get its prototype as vector
    owner = {}
    for n, name in enumerate(names):
        for k in keywords[name]:
            owner.setdefault(k, n)
    is_keyword = np.array([w in owner for w in kept])
    for i in np.flatnonzero(is_keyword):
        small[i] = protos[owner[kept[i]]]
        sims[i] = 0.0
        sims[i, owner[kept[i]]] = 1.0

    best, score = sims.argmax(axis=1), sims.max(axis=1)
    full_best = (x @ full_protos.T).argmax(axis=1)
    shows = (score >= thresholds[best]) | is_keyword
    stored = (score >= STORE * closest[best]) | is_keyword
    agree = (best == full_best)[shows].mean()
    print("  PCA keeps %.0f%% of the information in %d of 300 numbers" % (100 * explained, DIMS))
    print("  %d words reach a symbol; the small model picks the same symbol as the full one for %.0f%% of them"
          % (shows.sum(), 100 * agree))

    # Words that show a symbol, or come close, go onto the Pico, sorted for binary search
    chosen = sorted((kept[i].encode(), small[i]) for i in np.flatnonzero(stored))
    names_blob = "\n".join(names).encode()
    with open(OUT, "wb") as f:
        f.write(struct.pack("<4sBBBBI", b"LMX2", DIMS, len(names), RECORD_WORD, round(PICKY * 100), len(chosen)))
        f.write(struct.pack("<H", len(names_blob)) + names_blob)
        f.write(bytes(int(round(t * 100)) for t in thresholds))
        f.write(protos.tobytes())
        for word, vector in chosen:
            f.write(word.ljust(RECORD_WORD, b"\0") + vector.tobytes())
    print("Wrote %s: %d words, %.0f KB" % (os.path.relpath(OUT, ROOT), len(chosen), os.path.getsize(OUT) / 1024))

    per_symbol = {}
    for i in np.flatnonzero(shows):
        per_symbol.setdefault(names[best[i]], []).append((score[i], kept[i]))
    for name in names:
        found = sorted(per_symbol.get(name, []), reverse=True)
        print("  %-13s %3d words, bar %.2f, e.g. %s" % (name, len(found), thresholds[names.index(name)], ", ".join(w for _, w in found[:8])))


if __name__ == "__main__":
    main()
