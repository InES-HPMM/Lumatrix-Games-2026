# Was die Lumatrix dauerhaft weiss: Standort, Nachtruhe und die Wetterdaten der letzten Übertragung.
# Liegt als kleine JSON-Datei auf dem Board; geschrieben wird nur, wenn sich etwas ändert.

import json

from wetter import konfig
from wetter.kalender import datum_nummer, heute_nummer


class Tag:
    """Wetter eines Kalendertags: WMO-Code, Höchst- und Tiefsttemperatur in °C (je auch None)."""

    def __init__(self, datum, code, maximum, minimum):
        self.datum = datum
        self.nummer = datum_nummer(datum)
        self.code = code
        self.maximum = maximum
        self.minimum = minimum

    def als_liste(self):
        return [self.datum, self.code, self.maximum, self.minimum]


class Daten:
    def __init__(self, datei):
        self._datei = datei
        self.standort = None  # {"name": ..., "lat": ..., "lon": ...}
        self.nachtruhe = konfig.NACHTRUHE
        self.versatz_standort = 0
        self.versatz_rechner = 0
        self.wetter_zeit = None  # Zeitpunkt der letzten Übertragung mit Wetterdaten
        self.tage = []
        try:
            with open(datei) as f:
                self._laden(json.load(f))
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            pass  # fehlende oder kaputte Datei: Lumatrix startet wie neu

    def _laden(self, d):
        self.standort = d.get("standort")
        self.nachtruhe = tuple(d.get("nachtruhe", konfig.NACHTRUHE))
        self.versatz_standort = d.get("versatz_standort", 0)
        self.versatz_rechner = d.get("versatz_rechner", 0)
        self.wetter_zeit = d.get("wetter_zeit")
        self.tage = [Tag(*t) for t in d.get("tage", [])]

    def speichern(self):
        d = {
            "standort": self.standort,
            "nachtruhe": list(self.nachtruhe),
            "versatz_standort": self.versatz_standort,
            "versatz_rechner": self.versatz_rechner,
            "wetter_zeit": self.wetter_zeit,
            "tage": [t.als_liste() for t in self.tage],
        }
        with open(self._datei, "w") as f:
            json.dump(d, f)

    def tag(self, jetzt, abstand):
        """Der Tag `abstand` Tage nach heute (Ortszeit des Standorts), oder None ohne Daten."""
        ziel = heute_nummer(jetzt, self.versatz_standort) + abstand
        for t in self.tage:
            if t.nummer == ziel:
                return t
        return None

    def veraltet(self, jetzt):
        return self.wetter_zeit is None or jetzt - self.wetter_zeit > konfig.VERALTET_S
