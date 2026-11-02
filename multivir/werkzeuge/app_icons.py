# Erzeugt die App-Icons der Konfigurationsseite aus dem Sonnen-Icon der Matrix (ohne Pillow).
#   .venv/bin/python -m werkzeuge.app_icons

import struct
import zlib
from pathlib import Path

from wetter import bilder
from wetter import wetterlage as wl

HINTERGRUND = (20, 22, 28)
ZIEL = Path(__file__).resolve().parent.parent / "web" / "icons"


def png(breite, hoehe, pixel):
    def block(art, daten):
        roh = art + daten
        return struct.pack(">I", len(daten)) + roh + struct.pack(">I", zlib.crc32(roh) & 0xFFFFFFFF)

    zeilen = b"".join(b"\x00" + bytes(c for p in zeile for c in p) for zeile in pixel)
    kopf = struct.pack(">IIBBBBB", breite, hoehe, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + block(b"IHDR", kopf) + block(b"IDAT", zlib.compress(zeilen, 9)) + block(b"IEND", b"")


def icon(groesse):
    raster = bilder.icon(wl.SONNE_WOLKE, 0) + [[bilder.SCHWARZ] * 8]
    rand = groesse // 8  # Sicherheitsabstand für runde Masken
    zelle = (groesse - 2 * rand) // 8
    versatz = (groesse - 8 * zelle) // 2
    luecke = max(1, zelle // 8)
    pixel = []
    for y in range(groesse):
        zeile = []
        for x in range(groesse):
            gx, gy = (x - versatz) // zelle, (y - versatz) // zelle
            innen = 0 <= gx < 8 and 0 <= gy < 8
            in_zelle = (x - versatz) % zelle >= luecke and (y - versatz) % zelle >= luecke
            farbe = raster[gy][gx] if innen and in_zelle else bilder.SCHWARZ
            zeile.append(farbe if farbe != bilder.SCHWARZ else HINTERGRUND)
        pixel.append(zeile)
    return png(groesse, groesse, pixel)


if __name__ == "__main__":
    ZIEL.mkdir(parents=True, exist_ok=True)
    for g in (192, 512):
        (ZIEL / f"icon-{g}.png").write_bytes(icon(g))
        print(f"icon-{g}.png")
