# Level als Textraster: 8 Zeilen, ein Zeichen pro Pixel, Zeile 0 ist oben.
#
#   .  leer
#   #  Block
#   ^  Spitze  (v ist ebenfalls eine Spitze, nur zur besseren Lesbarkeit für hängende Spitzen)
#   =  Sprungpad
#   o  Sprungring
#   W S P G R  Portal zu Würfel, Schiff, sPider, swinG, Robot
#
# Ein Portal füllt immer die ganze Spalte. Im Raster genügt der Buchstabe in einer Zeile;
# die übrigen Zeilen dieser Spalte müssen leer sein oder denselben Buchstaben tragen.

ZEILEN = 8

LEER = "."
BLOCK = "#"
SPITZE = "^"
SPRUNGPAD = "="
SPRUNGRING = "o"

WUERFEL = "W"
SCHIFF = "S"
SPIDER = "P"
SWING = "G"
ROBOT = "R"
MODI = (WUERFEL, SCHIFF, SPIDER, SWING, ROBOT)

_ZEICHEN = (LEER, BLOCK, SPITZE, SPRUNGPAD, SPRUNGRING) + MODI


class LevelFehler(Exception):
    pass


class Level:
    def __init__(self, name, abschnitte, startmodus, tempo=None):
        self.name = name
        self.startmodus = startmodus
        self.tempo = tempo
        zeilen = [""] * ZEILEN
        for nummer, abschnitt in enumerate(abschnitte):
            teile = [z.strip() for z in abschnitt.strip().split("\n")]
            if len(teile) != ZEILEN:
                raise LevelFehler(
                    "%s, Abschnitt %d: %d statt %d Zeilen" % (name, nummer, len(teile), ZEILEN)
                )
            breite = len(teile[0])
            for zeile in teile:
                if len(zeile) != breite:
                    raise LevelFehler("%s, Abschnitt %d: ungleich lange Zeilen" % (name, nummer))
            for y in range(ZEILEN):
                zeilen[y] += teile[y].replace("v", SPITZE)
        self.laenge = len(zeilen[0])
        self.portale = {}
        for x in range(self.laenge):
            spalte = [zeilen[y][x] for y in range(ZEILEN)]
            for zeichen in spalte:
                if zeichen not in _ZEICHEN:
                    raise LevelFehler("%s, Spalte %d: unbekanntes Zeichen %r" % (name, x, zeichen))
            modi = [z for z in spalte if z in MODI]
            if modi:
                if any(z != modi[0] and z != LEER for z in spalte):
                    raise LevelFehler("%s, Spalte %d: Portal mit anderen Elementen" % (name, x))
                self.portale[x] = modi[0]
        self.zeilen = zeilen

    def feld(self, x, y):
        """Levelelement an (x, y); außerhalb des Levels ist alles leer, Portale füllen die Spalte."""
        if x < 0 or x >= self.laenge or y < 0 or y >= ZEILEN:
            return LEER
        modus = self.portale.get(x)
        if modus:
            return modus
        return self.zeilen[y][x]

    def fest(self, x, y):
        """Block oder Rand: Hier kann die Spielfigur stehen, aber nicht hinein."""
        if y < 0 or y >= ZEILEN:
            return True
        return self.feld(x, y) == BLOCK
