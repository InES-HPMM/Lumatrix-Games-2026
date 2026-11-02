"""
Schaffbarkeitsprüfung: Gibt es eine Folge von Eingaben, mit der ein Level bis zum Ziel kommt?

Läuft nur auf dem Mac. Durchsucht Spalte für Spalte alle Zustände, die mit „halten“ oder
„loslassen“ erreichbar sind, mit genau derselben Physik wie auf dem Board.

    .venv/bin/python -m werkzeuge.schaffbarkeit            # alle Level
    .venv/bin/python -m werkzeuge.schaffbarkeit stereo     # nur Level, deren Name passt
"""

import sys

from dash.physik import LAEUFT, ZIEL, schritt, startzustand


class Ergebnis:
    def __init__(self, schaffbar, weiteste_spalte, eingaben):
        self.schaffbar = schaffbar
        # weiteste Spalte, die überhaupt erreichbar ist
        self.weiteste_spalte = weiteste_spalte
        # eine Eingabefolge (True = halten) bis zum Ziel bzw. bis zur weitesten Spalte
        self.eingaben = eingaben


def pruefen(level):
    start = startzustand(level)
    front = {start.schluessel(): start}
    herkunft = {start.schluessel(): None}
    letzter = start.schluessel()
    while front:
        naechste = {}
        for schluessel, z in front.items():
            for gehalten in (False, True):
                ergebnis, neu = schritt(level, z, gehalten)
                if ergebnis == ZIEL:
                    eingaben = _rueckweg(herkunft, schluessel) + [gehalten]
                    return Ergebnis(True, level.laenge, eingaben)
                if ergebnis != LAEUFT:
                    continue
                k = neu.schluessel()
                if k not in herkunft:
                    herkunft[k] = (schluessel, gehalten)
                    naechste[k] = neu
        if naechste:
            letzter = next(iter(naechste))
        front = naechste
    return Ergebnis(False, letzter[0], _rueckweg(herkunft, letzter))


def _rueckweg(herkunft, schluessel):
    eingaben = []
    while herkunft[schluessel] is not None:
        schluessel, gehalten = herkunft[schluessel]
        eingaben.append(gehalten)
    eingaben.reverse()
    return eingaben


def ausschnitt(level, spalte, breite=24):
    """Levelraster rund um eine Spalte, mit Markierung darüber."""
    von = max(0, spalte - breite // 2)
    bis = min(level.laenge, von + breite)
    marke = " " * (spalte - von) + "v Spalte %d" % spalte
    zeilen = [marke] + [level.zeilen[y][von:bis] for y in range(len(level.zeilen))]
    return "\n".join(zeilen)


def main(argv):
    from dash.levels import LEVEL

    filter_ = argv[1].lower() if len(argv) > 1 else ""
    alle_ok = True
    for level in LEVEL:
        if filter_ not in level.name.lower():
            continue
        e = pruefen(level)
        if e.schaffbar:
            print("%-22s schaffbar (%d Spalten)" % (level.name, level.laenge))
        else:
            alle_ok = False
            print("%-22s NICHT schaffbar, weiter als Spalte %d kommt man nicht:" % (
                level.name, e.weiteste_spalte))
            print(ausschnitt(level, e.weiteste_spalte))
    return 0 if alle_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
