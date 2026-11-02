# Bilder für die 8×8-Matrix, ohne Hardware.
# Ein Bild ist eine Liste von 8 Zeilen (Zeile 0 oben) mit je 8 Farben (r, g, b).

from dash import konfig
from dash.level import (
    BLOCK,
    ROBOT,
    SCHIFF,
    SPIDER,
    SPITZE,
    SPRUNGPAD,
    SPRUNGRING,
    SWING,
    WUERFEL,
    ZEILEN,
)

SCHWARZ = (0, 0, 0)
ROT = (255, 0, 0)

MODUSFARBE = {
    WUERFEL: (0, 255, 0),
    SCHIFF: (255, 0, 140),
    SPIDER: (140, 0, 255),
    SWING: (255, 200, 0),
    ROBOT: (255, 255, 255),
}

ELEMENTFARBE = {
    BLOCK: (0, 0, 255),
    SPITZE: ROT,
    SPRUNGPAD: (255, 70, 0),
    SPRUNGRING: (0, 255, 255),
}
ELEMENTFARBE.update(MODUSFARBE)  # Portale leuchten in der Modusfarbe


def gedimmt(farbe, teiler=4):
    return (farbe[0] // teiler, farbe[1] // teiler, farbe[2] // teiler)


def leeres_bild():
    return [[SCHWARZ] * 8 for _ in range(ZEILEN)]


def volles_bild(farbe):
    return [[farbe] * 8 for _ in range(ZEILEN)]


def spielbild(level, z):
    """Ausschnitt des Levels um die Spielfigur, die Spielfigur in ihrer Modusfarbe."""
    bild = leeres_bild()
    links = z.x - konfig.SPALTE_SPIELFIGUR
    for y in range(ZEILEN):
        zeile = bild[y]
        for spalte in range(8):
            farbe = ELEMENTFARBE.get(level.feld(links + spalte, y))
            if farbe:
                zeile[spalte] = farbe
    if 0 <= z.y < ZEILEN:
        bild[z.y][konfig.SPALTE_SPIELFIGUR] = MODUSFARBE[z.modus]
    return bild


def fortschrittsbild(pixel, bestmarke, farbe):
    """
    Fortschrittsbalken: füllt die Matrix zeilenweise von oben links.

    :param pixel: Fortschritt (0 bis 64 Pixel), in voller Farbe
    :param bestmarke: Bestmarke (0 bis 64 Pixel); liegt sie weiter, leuchtet ihr Pixel gedimmt
    """
    bild = leeres_bild()
    for i in range(pixel):
        bild[i // 8][i % 8] = farbe
    if bestmarke > pixel:
        i = bestmarke - 1
        bild[i // 8][i % 8] = gedimmt(farbe)
    return bild


def feuerwerk(farbe):
    """Bilder eines Rings, der sich von der Mitte bis an den Rand ausbreitet."""
    bilder = []
    for radius in range(6):
        bild = leeres_bild()
        for y in range(ZEILEN):
            for x in range(8):
                # Abstand von der Mitte (3,5 / 3,5), doppelt gezählt, damit er ganzzahlig bleibt
                d = max(abs(2 * x - 7), abs(2 * y - 7)) // 2
                if d == radius:
                    bild[y][x] = farbe
                elif d == radius - 1:
                    bild[y][x] = gedimmt(farbe)
        bilder.append(bild)
    bilder.append(leeres_bild())
    return bilder
