"""Packs the animated symbols of pico/icons.py into pico/icons.bin for the Pico.

    python model/build_icons.py

The Pico could import icons.py directly, but ~100 animated icons as Python
strings would take far more RAM than these ~25 KB of bytes.

File layout (little-endian):
  "LMI1", colours (u8), icons (u16), colours x 3 bytes RGB (colour 1 first;
  0 means off), then per icon: name length (u8), name, ms per frame (u16),
  mode (u8: 0 loop, 1 pingpong, 2 once), frames (u8), and per frame 64
  colour numbers, bottom row first (the order of the LED buffer).
"""

import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pico"))
from icons import ICONS, PALETTE  # noqa: E402

OUT = os.path.join(ROOT, "pico", "icons.bin")
MODES = {"loop": 0, "pingpong": 1, "once": 2}


def pack():
    letters = list(PALETTE)
    number = {c: i + 1 for i, c in enumerate(letters)}
    number["."] = 0
    out = bytearray(struct.pack("<4sBH", b"LMI1", len(letters), len(ICONS)))
    for c in letters:
        out += bytes(PALETTE[c])
    for name, (_, ms, mode, frames) in ICONS.items():
        key = name.encode()
        out += struct.pack("<B", len(key)) + key + struct.pack("<HBB", ms, MODES[mode], len(frames))
        for frame in frames:
            assert len(frame) == 8 and all(len(row) == 8 for row in frame), name
            for row in reversed(frame):  # bottom row first
                out += bytes(number[c] for c in row)
    return bytes(out)


def main():
    data = pack()
    with open(OUT, "wb") as f:
        f.write(data)
    frames = sum(len(entry[3]) for entry in ICONS.values())
    print("Wrote %s: %d icons, %d frames, %.1f KB" % (os.path.relpath(OUT, ROOT), len(ICONS), frames, len(data) / 1024))


if __name__ == "__main__":
    main()
