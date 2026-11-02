# Was die Matrix zeigt, abhängig von Daten, Uhr und Joystick – ohne Hardware.
# ms ist ein stetig wachsender Millisekundenzähler, jetzt die Uhrzeit (Sekunden seit 1970 UTC) oder None.

from wetter import bilder, konfig
from wetter.kalender import in_nachtruhe
from wetter.wetterlage import UNBEKANNT, aus_code

LINKS = "links"
RECHTS = "rechts"
OBEN = "oben"
UNTEN = "unten"


class Ansicht:
    def __init__(self, daten):
        self.daten = daten
        self.tag = 0  # Abstand des angezeigten Tags von heute
        self._letzte_eingabe = None
        self._temperatur = None  # (OBEN oder UNTEN, Beginn in ms)
        self._wach_bis = None

    def _schlaeft(self, ms, jetzt):
        if jetzt is None:
            return False
        if self._wach_bis is not None and ms < self._wach_bis:
            return False
        beginn, ende = self.daten.nachtruhe
        return in_nachtruhe(jetzt, self.daten.versatz_rechner, beginn, ende)

    def klick(self, richtung, ms, jetzt):
        """Ein Klick auf eine Joystick-Richtung."""
        schlief = self._schlaeft(ms, jetzt)
        self._wach_bis = ms + konfig.WECKEN_MS
        self._letzte_eingabe = ms
        if schlief:
            return  # der weckende Klick bewirkt sonst nichts
        if richtung == LINKS:
            self._blaettern(-1)
        elif richtung == RECHTS:
            self._blaettern(1)
        elif richtung in (OBEN, UNTEN):
            self._temperatur = (richtung, ms)

    def _blaettern(self, schritt):
        self.tag = max(0, min(konfig.TAGE_ANGEZEIGT - 1, self.tag + schritt))
        self._temperatur = None

    def bild(self, ms, jetzt):
        """Das Bild (8 Zeilen), das zum Zeitpunkt ms auf der Matrix stehen soll."""
        d = self.daten
        if d.standort is None:
            return bilder.stecknadel(ms)
        if jetzt is None or not d.tage:
            return bilder.wartepunkt(ms)
        if self._schlaeft(ms, jetzt):
            return bilder.leeres_bild()

        if self._letzte_eingabe is not None and ms - self._letzte_eingabe >= konfig.RUECKSPRUNG_MS:
            self.tag = 0
            self._temperatur = None
            self._letzte_eingabe = None

        tag = d.tag(jetzt, self.tag)
        oben = self._temperaturbild(tag, ms)
        if oben is None:
            lage = aus_code(tag.code) if tag else UNBEKANNT
            oben = bilder.icon(lage, ms)
        leiste = bilder.tagesleiste(self.tag, konfig.TAGE_ANGEZEIGT, d.veraltet(jetzt))
        return oben + [leiste]

    def _temperaturbild(self, tag, ms):
        if self._temperatur is None or tag is None:
            return None
        richtung, beginn = self._temperatur
        verstrichen = ms - beginn
        if verstrichen >= konfig.TEMPERATUR_MS:
            self._temperatur = None
            return None
        if richtung == OBEN:
            wert, farbe = tag.maximum, bilder.ORANGE
        else:
            wert, farbe = tag.minimum, bilder.BLAU
        if wert is None:
            return None
        return bilder.temperatur(wert, farbe, verstrichen, konfig.TEMPERATUR_MS)
