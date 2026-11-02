# Das einzige Modul mit Hardwarezugriff: Joystick, Schiebeschalter und LED-Matrix.
# Läuft nur auf dem Board; die Spiellogik liegt hardwarefrei in physik, anzeige und level.

from machine import Pin
from time import sleep_ms, ticks_add, ticks_diff, ticks_ms

from zhaw_led_matrix import CharacterTable, LedMatrix

from dash import konfig
from dash.anzeige import (
    MODUSFARBE,
    ROT,
    fortschrittsbild,
    feuerwerk,
    gedimmt,
    spielbild,
    volles_bild,
)
from dash.bestmarke import Bestmarken
from dash.levels import SKELETAL_SHENANIGANS, STEREO_MADNESS
from dash.physik import LAEUFT, ZIEL, fortschritt_pixel, schritt, startzustand

# Joystick: oben, unten, links, rechts, Mitte (gedrückt = 0)
PINS_EINGABE = (3, 6, 7, 2, 8)
PIN_LEVELWAHL = 9
LEVEL_PRO_STELLUNG = (STEREO_MADNESS, SKELETAL_SHENANIGANS)  # links, rechts

ABTASTUNG_MS = 4


class Geraet:
    def __init__(self):
        self._tasten = [Pin(p, Pin.IN, Pin.PULL_UP) for p in PINS_EINGABE]
        self._schalter = Pin(PIN_LEVELWAHL, Pin.IN, Pin.PULL_UP)
        self.matrix = LedMatrix(8, 8)
        self.matrix.set_brightness(konfig.HELLIGKEIT)
        # entprellter Zustand der Eingabe
        self._aktiv = self._roh()
        self._roh_vorher = self._aktiv
        self.gedrueckt = False

    def _roh(self):
        for t in self._tasten:
            if t.value() == 0:
                return True
        return False

    def abtasten(self):
        """Eingabe einmal abtasten; ein Wechsel zählt erst, wenn er zwei Abtastungen lang anhält."""
        roh = self._roh()
        if roh == self._roh_vorher and roh != self._aktiv:
            self._aktiv = roh
            if roh:
                self.gedrueckt = True
        self._roh_vorher = roh
        return self._aktiv

    def eingabe_aktiv(self):
        return self._aktiv

    def levelwahl(self):
        return LEVEL_PRO_STELLUNG[self._schalter.value()]

    def zeige(self, bild):
        """Bild mit Zeile 0 oben; die Bibliothek zählt Zeilen von unten."""
        m = self.matrix
        for y in range(8):
            zeile = bild[y]
            for x in range(8):
                m[x, 7 - y] = zeile[x]
        m.apply()

    def warten(self, ms, level=None):
        """Wartet und tastet dabei ab; gibt False zurück, wenn die Levelwahl umgelegt wurde."""
        ende = ticks_add(ticks_ms(), ms)
        while ticks_diff(ende, ticks_ms()) > 0:
            self.abtasten()
            if level is not None and self.levelwahl() is not level:
                return False
            sleep_ms(ABTASTUNG_MS)
        return True

    def lauftext(self, text, farbe):
        zeichen, laenge = CharacterTable.convert_str(text)
        self.matrix.move_across(zeichen, laenge, colors=farbe)


def _farbe(level):
    return MODUSFARBE[level.startmodus]


def wartezustand(g, marken):
    """Zeigt die Bestmarke des gewählten Levels, bis ein neuer Druck erfolgt."""
    level = g.levelwahl()
    g.gedrueckt = False
    blinken = 0
    while True:
        if g.levelwahl() is not level:
            level = g.levelwahl()
            g.gedrueckt = False
        if g.gedrueckt:
            return level
        farbe = _farbe(level)
        if blinken % 2:
            farbe = gedimmt(farbe)
        bestmarke = marken.lesen(level)
        g.zeige(fortschrittsbild(max(1, bestmarke), 0, farbe))
        g.warten(400)
        blinken += 1


def versuch(g, level):
    """Ein Versuch; gibt (Ergebnis, Fortschritt in Pixeln) zurück, Ergebnis None bei Levelwechsel."""
    z = startzustand(level)
    takt = 1000 // (level.tempo or konfig.TEMPO)
    naechster = ticks_ms()
    g.gedrueckt = False
    while True:
        g.zeige(spielbild(level, z))
        naechster = ticks_add(naechster, takt)
        gehalten_zwischendurch = False
        while ticks_diff(naechster, ticks_ms()) > 0:
            if g.abtasten():
                gehalten_zwischendurch = True
            if g.levelwahl() is not level:
                return None, 0
            sleep_ms(ABTASTUNG_MS)
        # Ein kurzer Tipp zwischen zwei Takten zählt als gehalten.
        gehalten = g.eingabe_aktiv() or gehalten_zwischendurch
        ergebnis, z = schritt(level, z, gehalten, g.gedrueckt)
        g.gedrueckt = False
        if ergebnis != LAEUFT:
            return ergebnis, fortschritt_pixel(level, z, ergebnis)


def ziel(g, level):
    farbe = MODUSFARBE[level.startmodus]
    for bild in feuerwerk(MODUSFARBE["W"]):
        g.zeige(bild)
        g.warten(90)
    g.lauftext("100%", MODUSFARBE["W"])
    g.zeige(fortschrittsbild(64, 0, farbe))


def starten():
    g = Geraet()
    marken = Bestmarken(konfig.BESTMARKEN_DATEI)

    # Eingabe beim Einschalten gehalten: Bestmarke des gewählten Levels zurücksetzen
    if g.eingabe_aktiv():
        marken.zuruecksetzen(g.levelwahl())
        for _ in range(3):
            g.zeige(volles_bild(ROT))
            g.warten(150)
            g.zeige(volles_bild((0, 0, 0)))
            g.warten(150)

    while True:
        level = wartezustand(g, marken)
        while True:
            ergebnis, pixel = versuch(g, level)
            if ergebnis is None:
                break  # Levelwahl umgelegt: zurück in den Wartezustand
            marken.melden(level, pixel)
            if ergebnis == ZIEL:
                ziel(g, level)
                break
            g.zeige(volles_bild(ROT))
            if not g.warten(konfig.TOD_BLITZ_MS, level):
                break
            g.zeige(fortschrittsbild(pixel, marken.lesen(level), _farbe(level)))
            if not g.warten(konfig.FORTSCHRITT_MS, level):
                break
