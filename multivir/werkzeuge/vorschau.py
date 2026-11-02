# Zeigt die Bilder der Wetteranzeige farbig im Terminal, ohne Board.
#   .venv/bin/python -m werkzeuge.vorschau            alle Wetter-Icons mit allen Bildern
#   .venv/bin/python -m werkzeuge.vorschau -12 18     Temperaturanzeigen

import sys

from wetter import bilder, konfig
from wetter import wetterlage as wl


def pixel(farbe):
    r, g, b = farbe
    if farbe == bilder.SCHWARZ:
        return "\x1b[48;2;20;20;20m  \x1b[0m"
    return "\x1b[48;2;%d;%d;%dm  \x1b[0m" % (r, g, b)


def nebeneinander(bildfolge):
    for y in range(len(bildfolge[0])):
        print("  ".join("".join(pixel(f) for f in b[y]) for b in bildfolge))
    print()


def main(argumente):
    if argumente:
        for wert in argumente:
            print(wert)
            dauer = konfig.TEMPERATUR_MS
            folge = [bilder.temperatur(float(wert), bilder.ORANGE, t, dauer) for t in range(0, dauer, 300)]
            nebeneinander([b + [bilder.tagesleiste(0, 8, False)] for b in folge])
        return
    lagen = (wl.SONNE, wl.SONNE_WOLKE, wl.WOLKE, wl.NEBEL, wl.REGEN, wl.SCHNEE, wl.GEWITTER, wl.UNBEKANNT)
    for lage in lagen:
        dauer, folge = bilder._ICON_BILDER[lage]
        print(lage)
        nebeneinander([b + [bilder.tagesleiste(0, 8, False)] for b in folge[:6]])
    print("stecknadel, wartepunkt")
    nebeneinander([bilder.stecknadel(0), bilder.wartepunkt(1000)])


if __name__ == "__main__":
    main(sys.argv[1:])
