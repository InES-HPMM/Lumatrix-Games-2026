# Bestmarken pro Level, dauerhaft in einer kleinen JSON-Datei.
# Geschrieben wird nur, wenn sich eine Bestmarke ändert, um den Flash zu schonen.

import json


class Bestmarken:
    def __init__(self, datei):
        self._datei = datei
        try:
            with open(datei) as f:
                self._werte = json.load(f)
        except (OSError, ValueError):
            self._werte = {}

    def lesen(self, level):
        return self._werte.get(level.name, 0)

    def melden(self, level, pixel):
        """Neuen Fortschritt melden; gibt True zurück, wenn er die Bestmarke verbessert."""
        if pixel <= self.lesen(level):
            return False
        self._werte[level.name] = pixel
        self._speichern()
        return True

    def zuruecksetzen(self, level):
        if level.name in self._werte:
            del self._werte[level.name]
            self._speichern()

    def _speichern(self):
        with open(self._datei, "w") as f:
            json.dump(self._werte, f)
