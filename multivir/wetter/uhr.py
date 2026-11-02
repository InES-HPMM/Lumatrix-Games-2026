# Die Uhr der Lumatrix. Der Pico hat keine gepufferte Uhr: Erst eine Übertragung setzt die Zeit,
# danach zählt die Uhr mit dem Millisekundenzähler des Geräts weiter. Nach einem Neustart ist sie
# wieder unbekannt.


class Uhr:
    def __init__(self):
        self._anker = None  # (Sekunden seit 1970 UTC, Millisekundenzähler) beim Stellen

    def stellen(self, jetzt, ms):
        self._anker = (jetzt, ms)

    def bekannt(self):
        return self._anker is not None

    def jetzt(self, ms):
        """Aktuelle Zeit in Sekunden seit 1970 UTC, oder None, solange die Uhr nie gestellt wurde."""
        if self._anker is None:
            return None
        sekunden, ms_anker = self._anker
        return sekunden + (ms - ms_anker) // 1000
