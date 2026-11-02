# A hand-drawn 7-row pixel font for everything that scrolls by (song titles,
# cover styles, the Emoji-Rätsel's answer) and the mode's big number.
# Each character is a tuple of columns; bit 0 = top row.
FONT = {
    'A': (126, 9, 9, 126),
    'B': (127, 73, 73, 54),
    'C': (62, 65, 65, 34),
    'D': (127, 65, 65, 62),
    'E': (127, 73, 73, 65),
    'F': (127, 9, 9, 1),
    'G': (62, 65, 73, 122),
    'H': (127, 8, 8, 127),
    'I': (65, 127, 65),
    'J': (32, 64, 65, 63),
    'K': (127, 8, 20, 99),
    'L': (127, 64, 64, 64),
    'M': (127, 2, 12, 2, 127),
    'N': (127, 2, 4, 8, 127),
    'O': (62, 65, 65, 62),
    'P': (127, 9, 9, 6),
    'Q': (62, 65, 81, 33, 94),
    'R': (127, 9, 25, 102),
    'S': (70, 73, 73, 49),
    'T': (1, 1, 127, 1, 1),
    'U': (63, 64, 64, 63),
    'V': (15, 48, 64, 48, 15),
    'W': (127, 32, 24, 32, 127),
    'X': (99, 20, 8, 20, 99),
    'Y': (3, 4, 120, 4, 3),
    'Z': (97, 81, 77, 67),
    '0': (62, 73, 69, 62),
    '1': (66, 127, 64),
    '2': (98, 81, 73, 70),
    '3': (65, 73, 73, 54),
    '4': (28, 18, 127, 16),
    '5': (39, 69, 69, 57),
    '6': (62, 73, 73, 48),
    '7': (1, 113, 13, 3),
    '8': (54, 73, 73, 54),
    '9': (6, 73, 73, 62),
    "'": (3,),
    '!': (95,),
    '?': (2, 81, 9, 6),
    ',': (64, 32),
    '.': (64,),
    '-': (8, 8, 8),
    '(': (62, 65),
    ')': (65, 62),
    ' ': (0, 0),
}

SCROLL_PX_PER_S = 16  # how fast text scrolls by


def text_columns(text, margin=8):
    """The text as a strip of 7-row columns (bit 0 = top row), with margin
    empty columns before and after, so it scrolls in and out."""
    cols = [0] * margin
    for ch in text.upper():
        cols += list(FONT.get(ch, FONT[" "])) + [0]
    return cols + [0] * margin
