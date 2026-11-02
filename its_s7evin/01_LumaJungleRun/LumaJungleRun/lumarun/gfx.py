# Farben und Bilder. Die Farbwerte stammen aus den Entwuerfen (Druckvorlage) und werden
# per Gamma-Korrektur fuer die LEDs umgerechnet, damit sie aehnlich wie auf Papier wirken.
from . import hw

GAMMA = 2.2


def _g(hexcolor):
    r = (hexcolor >> 16) & 255
    g = (hexcolor >> 8) & 255
    b = hexcolor & 255
    return (
        int((r / 255) ** GAMMA * 255 + 0.5),
        int((g / 255) ** GAMMA * 255 + 0.5),
        int((b / 255) ** GAMMA * 255 + 0.5),
    )


BLACK = (0, 0, 0)
WHITE = _g(0xFFFFFF)
SKY = _g(0x42AFF5)         # Himmel
STORM = _g(0x004C7F)       # Gewitterhimmel
SEA = _g(0x05A89F)         # Meer / Wellen
RAFT = _g(0x925310)        # Floss
SKIN = _g(0xF3B36A)        # Kopf der Person
SHIRT = _g(0xEE2711)       # Koerper der Person
LEAF = _g(0x5FD93A)        # Palmblaetter
TRUNK = _g(0x6B4B21)       # Baumstaemme, Ast
SAND = _g(0xF7BB04)        # Strand
PATH = _g(0xD6A72E)        # Dschungelweg
GRASS = _g(0x5E9028)       # Wiese (gedaempftes Olivgruen, damit Baeume hervortreten)
BUSH = _g(0x00C46A)        # Baumkronen (kraeftiges Blaugruen)
ROCK = _g(0x919191)        # Felsen und Steine
CAVE = _g(0x666666)        # Hoehle / Felsdecke
SPIDER = _g(0x523A0A)      # Netz-Spinne
WALKER = _g(0x8A2A06)      # entgegenkommende Spinne
SNAKE = _g(0x3E6049)       # Schlange (Waldgruen)
POISON = _g(0x9B1A5E)      # Gift / Schwindel-Strudel
GOLD = _g(0xF7E135)        # goldener Affe
BRONZE = _g(0xC38123)
SUNSET = _g(0xF28C28)

PAL = {
    ".": BLACK, "W": WHITE, "S": SKY, "D": STORM, "T": SEA, "B": RAFT,
    "K": SKIN, "R": SHIRT, "L": LEAF, "P": TRUNK, "Y": SAND, "O": PATH,
    "G": GRASS, "g": BUSH, "r": ROCK, "C": CAVE, "s": SPIDER, "N": SNAKE,
    "V": POISON, "M": GOLD, "m": BRONZE,
}

# ---------------------------------------------------------------- Bilder (y=0 oben)
RAFT_SCENE = (       # Seite 1, Grid 1
    "SSSSSSSS",
    "SSSSSSSS",
    "WWWWWWWW",
    "WWWWWKWW",
    "WWWWWRWW",
    "WWWWBBBW",
    "WTWTWTWT",
    "TTTTTTTT",
)

STORM_SCENE = (      # Seite 1, Grid 2
    "DDDDDDDD",
    "DDDDDWTT",
    "DDKDWTTT",
    "DDRDDWDT",
    "DBBBWDTT",
    "TDTDWTTT",
    "TTTTTTTT",
    "TTTTTTTT",
)

BEACH = (            # Seite 1, Grid 4 / Seite 2, Grid 1 (ohne Person)
    "SLSSSSSS",
    "LLLSSSSS",
    "SPLLSSSS",
    "PWLWWWWW",
    "PWWWWWWW",
    "YYWWWWWW",
    "YYYWWWWW",
    "YYYYBBBT",
)
BEACH_GROUND = (5, 5, 6, 7, 7, 7, 7, 7)   # oberste Bodenzeile je Spalte

CAVE_ROWS = (        # Seite 3, Grid 3 (oberer Teil, ohne Schlange)
    "GGOOOCCC",
    "GGOOO..C",
    "GGOOOCCC",
    "GGOOOGGG",
)
SNAKE_PATH = ((6, 1), (5, 1), (4, 1), (3, 1), (2, 1), (2, 2), (3, 2), (4, 2), (4, 3))

SPIRAL = (           # Seite 3, Grid 4
    "........",
    ".VVVVVV.",
    ".V....V.",
    ".V.VV.V.",
    ".V.VV.V.",
    ".V.V..V.",
    ".V.VVVV.",
    "........",
)

MONKEY = (           # Seite 4, Grid 3
    "........",
    "...MM...",
    "..MmmM..",
    ".MMmmMM.",
    ".MmmmmM.",
    ".MMmmMM.",
    "..MmmM..",
    "..MMMM..",
)

END_BEACH = (        # eigener Entwurf: Strand mit Meer rechts
    "SSSSSSSS",
    "LSSSSSSS",
    "LLSSSSSS",
    "PSSSSSSS",
    "PSSSSSSS",
    "YYYYTTTT",
    "YYYYYTTT",
    "YYYYYYTT",
)


def img(rows):
    return [PAL[ch] for row in rows for ch in row]


def draw(rows):
    hw.blit(img(rows))


def rotate(image):
    """64er-Bild um 90 Grad im Uhrzeigersinn drehen."""
    return [image[(7 - (i % 8)) * 8 + i // 8] for i in range(64)]


def mix(a, b, t):
    """Farbe a nach b ueberblenden, t von 0 bis 100."""
    return (
        a[0] + (b[0] - a[0]) * t // 100,
        a[1] + (b[1] - a[1]) * t // 100,
        a[2] + (b[2] - a[2]) * t // 100,
    )


def person(x, head_y, body=SHIRT):
    hw.set(x, head_y, SKIN)
    hw.set(x, head_y + 1, body)


# ---------------------------------------------------------------- Lauftext (5x7-Schrift)
FONT = {
    "L": ("X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"),
    "U": ("X...X", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."),
    "M": ("X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"),
    "A": (".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"),
    "J": ("..XXX", "...X.", "...X.", "...X.", "...X.", "X..X.", ".XX.."),
    "N": ("X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X", "X...X"),
    "G": (".XXX.", "X...X", "X....", "X.XXX", "X...X", "X...X", ".XXXX"),
    "E": ("XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"),
    "R": ("XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"),
}


def text_columns(parts):
    """Text als Liste von Spalten (je 7 Farben oder None) fuer den Lauftext.
    parts: Liste von (text, farbe)."""
    cols = []
    for text, color in parts:
        for ch in text:
            if ch == " ":
                cols += [[None] * 7] * 2
                continue
            glyph = FONT[ch]
            for x in range(len(glyph[0])):
                cols.append([color if row[x] == "X" else None for row in glyph])
            cols.append([None] * 7)
    return cols
