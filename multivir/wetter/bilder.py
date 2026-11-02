# Bilder für die 8×8-Matrix, ohne Hardware.
# Ein Bild ist eine Liste von Zeilen (Zeile 0 oben) mit je 8 Farben (r, g, b).
# Wetter-Icons und Temperaturanzeige sind 7 Zeilen hoch; darunter liegt die Tagesleiste.

from wetter import wetterlage as wl

SCHWARZ = (0, 0, 0)
ORANGE = (255, 90, 0)  # Höchsttemperatur
BLAU = (0, 90, 255)  # Tiefsttemperatur
WEISS = (255, 255, 255)
ROT = (255, 0, 0)

HOEHE_OBEN = 7  # Zeilen über der Tagesleiste

# Farben in den Pixelentwürfen; "." ist dunkel.
PALETTE = {
    "Y": (255, 160, 0),  # Sonne
    "y": (160, 70, 0),  # Sonnenstrahlen
    "W": (190, 190, 200),  # helle Wolke
    "G": (90, 90, 110),  # graue Wolke, Nebel
    "B": (0, 70, 255),  # Regentropfen
    "S": (255, 255, 255),  # Schneeflocke
    "L": (255, 220, 0),  # Blitz
    "R": (255, 0, 0),  # Fragezeichen, Stecknadel
}


def gedimmt(farbe, teiler=6):
    return (farbe[0] // teiler, farbe[1] // teiler, farbe[2] // teiler)


def leeres_bild(hoehe=8):
    return [[SCHWARZ] * 8 for _ in range(hoehe)]


def _aus_text(zeilen):
    return [[PALETTE.get(c, SCHWARZ) for c in z] for z in zeilen]


# --- Wetter-Icons -------------------------------------------------------------------------------
# Jede Wetterlage hat eine Bilddauer in ms und eine Folge von Bildern, die sich wiederholt.

_SONNE_GERADE = (
    "...yy...",
    "........",
    "..YYYY..",
    "y.YYYY.y",
    "..YYYY..",
    "........",
    "...yy...",
)
_SONNE_SCHRAEG = (
    "........",
    ".y....y.",
    "..YYYY..",
    "..YYYY..",
    "..YYYY..",
    ".y....y.",
    "........",
)

_SONNE_WOLKE = (
    ".....y..",
    "....YYY.",
    "...yYYYy",
    "..WWYYY.",
    ".WWWWW..",
    "WWWWWWW.",
    "WWWWWWW.",
)
_SONNE_WOLKE_OHNE_STRAHLEN = (
    "........",
    "....YYY.",
    "....YYY.",
    "..WWYYY.",
    ".WWWWW..",
    "WWWWWWW.",
    "WWWWWWW.",
)

_WOLKE = (
    "........",
    "..WW....",
    ".WWWWW..",
    "WWWWWWW.",
    "WWWWWWW.",
    "........",
    "........",
)


def _verschoben(zeilen, dx):
    """Entwurf um dx Spalten nach rechts verschoben (rechts herausfallende Pixel gehen verloren)."""
    return tuple(("." * dx + z)[:8] for z in zeilen)


_NEBEL_A = (
    "........",
    "GGGGGG..",
    "........",
    "..GGGGGG",
    "........",
    "GGGGGG..",
    "........",
)
_NEBEL_B = (
    "........",
    "..GGGGGG",
    "........",
    "GGGGGG..",
    "........",
    "..GGGGGG",
    "........",
)

_WOLKE_OBEN = (
    "...GG...",
    ".GGGGGG.",
    "GGGGGGGG",
)


def _niederschlag(zeichen, spalten, phasen):
    """Bilder mit Wolke oben und fallenden Tropfen oder Flocken in den Zeilen 3 bis 6."""
    bilder = []
    for i in range(4):
        unten = [["."] * 8 for _ in range(4)]
        for spalte, phase in zip(spalten, phasen):
            unten[(i + phase) % 4][spalte] = zeichen
        bilder.append(_WOLKE_OBEN + tuple("".join(z) for z in unten))
    return bilder


_GEWITTER_MIT = _WOLKE_OBEN + (
    "....L...",
    "...LL...",
    "....L...",
    "...L....",
)
_GEWITTER_OHNE = _WOLKE_OBEN + ("........",) * 4

_FRAGEZEICHEN = (
    "..RRRR..",
    ".RR..RR.",
    ".....RR.",
    "....RR..",
    "...RR...",
    "........",
    "...RR...",
)

_ICONS = {
    wl.SONNE: (600, [_SONNE_GERADE, _SONNE_SCHRAEG]),
    wl.SONNE_WOLKE: (600, [_SONNE_WOLKE, _SONNE_WOLKE_OHNE_STRAHLEN]),
    wl.WOLKE: (1000, [_WOLKE, _verschoben(_WOLKE, 1)]),
    wl.NEBEL: (800, [_NEBEL_A, _NEBEL_B]),
    wl.REGEN: (150, _niederschlag("B", (1, 3, 5, 7), (0, 2, 1, 3))),
    wl.SCHNEE: (350, _niederschlag("S", (0, 2, 4, 6), (0, 2, 3, 1))),
    wl.GEWITTER: (120, [_GEWITTER_MIT, _GEWITTER_OHNE, _GEWITTER_MIT] + [_GEWITTER_OHNE] * 7),
    wl.UNBEKANNT: (1000, [_FRAGEZEICHEN]),
}

# Entwürfe einmal beim Laden in Farben umrechnen.
_ICON_BILDER = {}
for _lage, (_dauer, _entwuerfe) in _ICONS.items():
    _ICON_BILDER[_lage] = (_dauer, [_aus_text(e) for e in _entwuerfe])


def icon(lage, ms):
    """Das Bild des Wetter-Icons einer Wetterlage zum Zeitpunkt ms (7 Zeilen)."""
    dauer, bilder = _ICON_BILDER[lage]
    return bilder[ms // dauer % len(bilder)]


# --- Ziffern und Temperaturanzeige --------------------------------------------------------------

_ZEICHEN = {
    "0": ("###", "#.#", "#.#", "#.#", "###"),
    "1": (".#.", "##.", ".#.", ".#.", "###"),
    "2": ("###", "..#", "###", "#..", "###"),
    "3": ("###", "..#", ".##", "..#", "###"),
    "4": ("#.#", "#.#", "###", "..#", "..#"),
    "5": ("###", "#..", "###", "..#", "###"),
    "6": ("###", "#..", "###", "#.#", "###"),
    "7": ("###", "..#", "..#", ".#.", ".#."),
    "8": ("###", "#.#", "###", "#.#", "###"),
    "9": ("###", "#.#", "###", "..#", "###"),
    "-": ("..", "..", "##", "..", ".."),
}
_ZIFFER_OBEN = 1  # erste Zeile der Ziffern innerhalb der 7 Zeilen


def runden(wert):
    """Auf ganze Grad runden, .5 vom Nullpunkt weg; nie „-0“."""
    if wert >= 0:
        return int(wert + 0.5)
    return -int(-wert + 0.5)


def _spalten(text):
    """Die Spalten des Texts von links nach rechts, je als Menge der leuchtenden Zeilen."""
    spalten = []
    for i, c in enumerate(text):
        if i:
            spalten.append(())
        muster = _ZEICHEN[c]
        for x in range(len(muster[0])):
            spalten.append(tuple(y for y in range(5) if muster[y][x] == "#"))
    return spalten


def temperatur(wert, farbe, verstrichen, dauer):
    """
    Bild der Temperaturanzeige (7 Zeilen), `verstrichen` ms nach ihrem Beginn.

    Passt die Zahl auf die Fläche, steht sie still und mittig; sonst läuft sie während
    `dauer` einmal von rechts nach links durch.
    """
    spalten = _spalten(str(runden(wert)))
    breite = len(spalten)
    if breite <= 8:
        links = (8 - breite) // 2
    else:
        links = 8 - verstrichen * (8 + breite) // dauer
    bild = leeres_bild(HOEHE_OBEN)
    for i, zeilen in enumerate(spalten):
        x = links + i
        if 0 <= x < 8:
            for y in zeilen:
                bild[_ZIFFER_OBEN + y][x] = farbe
    return bild


# --- Tagesleiste und Sonderzustände -------------------------------------------------------------


def tagesleiste(angezeigt, anzahl, veraltet):
    """Unterste Zeile: ein Pixel pro Tag, der angezeigte hell; rot, wenn die Vorhersage veraltet ist."""
    farbe = ROT if veraltet else WEISS
    zeile = [SCHWARZ] * 8
    for i in range(anzahl):
        zeile[i] = farbe if i == angezeigt else gedimmt(farbe)
    return zeile


_STECKNADEL = _aus_text(
    (
        "..RRRR..",
        ".RRRRRR.",
        ".RR..RR.",
        ".RRRRRR.",
        "..RRRR..",
        "...RR...",
        "...RR...",
        "........",
    )
)


def stecknadel(ms):
    """Blinkende Stecknadel: Es ist noch kein Standort gewählt."""
    return _STECKNADEL if ms // 600 % 2 == 0 else leeres_bild()


def wartepunkt(ms):
    """Pulsierender Punkt in der Mitte: Es fehlen noch Wetterdaten oder die Uhrzeit."""
    phase = ms % 2000
    stufe = phase if phase < 1000 else 2000 - phase  # 0 … 1000 … 0
    staerke = 100 + stufe * 900 // 1000  # in Promille, nie ganz dunkel
    farbe = (0, 120 * staerke // 1000, 255 * staerke // 1000)
    bild = leeres_bild()
    for y in (3, 4):
        for x in (3, 4):
            bild[y][x] = farbe
    return bild
