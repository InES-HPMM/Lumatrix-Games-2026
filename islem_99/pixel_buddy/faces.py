"""Minimal 8x8 features: eyes in rows 1-3, mouth in rows 5-6.
Row 4 always stays black. Coordinates start at the top left.
"""

COLOR = (210, 244, 218)

ORDER = ("neutral", "happy", "sad")

# Eye masks and mouth coordinates. One colour, no decoration.
FACES = {
    "neutral": (("000", "010", "000"), ("000", "010", "000"), ((2,5),(3,5),(4,5),(5,5))),
    "happy":   (("010", "101", "000"), ("010", "101", "000"), ((2,5),(5,5),(3,6),(4,6))),
    "sad":     (("000", "010", "000"), ("000", "010", "000"), ((3,5),(4,5),(2,6),(5,6))),
}


# Closed, narrow, open and wide syllable shapes, all below the dark gap.
TALK_MOUTHS = (
    FACES["neutral"][2],
    ((3,5),(3,6)),
    ((3,5),(4,5),(3,6),(4,6)),
    ((2,5),(3,5),(4,5),(5,5),(2,6),(5,6)),
)


def paint(out, emotion, lid=0, gaze=0, breath=100, wink=False, talk=0):
    """Draw into a reusable RGB frame; keep the eye/mouth gap completely dark."""
    color = COLOR

    def pixel(x, y, scale=100):
        offset = (y * 8 + x) * 3
        for channel in range(3):
            out[offset + channel] = color[channel] * scale // 100

    for i in range(len(out)):
        out[i] = 0

    left, right, mouth = FACES[emotion]
    for eye, pattern in enumerate((left, right)):
        eye_lid = 2 if wink and eye == 1 else lid
        if emotion in ("neutral", "sad"):
            # Single LEDs blink by briefly dimming and going dark.
            shift = gaze if emotion == "neutral" else 0
            if eye_lid < 2:
                pixel(eye * 5 + 1 + shift, 2, 40 if eye_lid == 1 else 100)
            continue
        if eye_lid == 2:
            pattern = ("000", "111", "000")
        elif eye_lid == 1:
            pattern = ("000", "010", "000")
        for y, row in enumerate(pattern):
            for x, value in enumerate(row):
                if value == "1":
                    pixel(eye * 5 + x, 1 + y)

    if emotion == "neutral":
        mouth = TALK_MOUTHS[talk]
    for x, y in mouth:
        pixel(x, y, breath)
