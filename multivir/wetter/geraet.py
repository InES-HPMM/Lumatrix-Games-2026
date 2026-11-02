# Das einzige Modul mit Hardwarezugriff: Joystick, LED-Matrix und USB-Schnittstelle.
# Läuft nur auf dem Board; die Logik liegt hardwarefrei in ansicht, bilder, daten und protokoll.

import json
import select
import sys

from machine import Pin
from time import sleep_ms, ticks_diff, ticks_ms

from zhaw_led_matrix import LedMatrix

from wetter import konfig, protokoll
from wetter.ansicht import LINKS, OBEN, RECHTS, UNTEN, Ansicht
from wetter.daten import Daten
from wetter.uhr import Uhr

# Joystick (Pull-up, gedrückt = 0); die Mitte bleibt ungenutzt.
PINS_RICHTUNG = ((OBEN, 3), (UNTEN, 6), (LINKS, 7), (RECHTS, 2))

TAKT_MS = 10
ZEILE_MAX = 8192  # längere Zeilen sind kaputt und werden verworfen


class Joystick:
    """Meldet Klicks; ein Druck zählt erst, wenn er zwei Abtastungen lang anhält."""

    def __init__(self):
        self._tasten = [(r, Pin(p, Pin.IN, Pin.PULL_UP)) for r, p in PINS_RICHTUNG]
        n = len(self._tasten)
        self._roh_vorher = [False] * n
        self._aktiv = [True] * n  # beim Start gehaltene Richtungen erst nach dem Loslassen zählen

    def klicks(self):
        ergebnis = []
        for i, (richtung, pin) in enumerate(self._tasten):
            roh = pin.value() == 0
            if roh == self._roh_vorher[i] and roh != self._aktiv[i]:
                self._aktiv[i] = roh
                if roh:
                    ergebnis.append(richtung)
            self._roh_vorher[i] = roh
        return ergebnis


class Schnittstelle:
    """Liest Zeilen von der USB-Schnittstelle, ohne zu blockieren, und schreibt Antworten."""

    def __init__(self):
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)
        self._puffer = []
        self._laenge = 0

    def zeilen(self):
        fertig = []
        while self._poll.poll(0):
            c = sys.stdin.read(1)
            if not c:
                break
            if c == "\n":
                fertig.append("".join(self._puffer))
                self._puffer = []
                self._laenge = 0
            elif c != "\r":
                self._puffer.append(c)
                self._laenge += 1
                if self._laenge > ZEILE_MAX:
                    self._puffer = []
                    self._laenge = 0
        return fertig

    def senden(self, d):
        sys.stdout.write(json.dumps(d) + "\n")


class Matrix:
    def __init__(self):
        self._m = LedMatrix(8, 8)
        self._m.set_brightness(konfig.HELLIGKEIT)
        self._vorher = None

    def zeige(self, bild):
        """Bild mit Zeile 0 oben; die Bibliothek zählt Zeilen von unten. Unverändertes wird nicht neu geschrieben."""
        if bild == self._vorher:
            return
        m = self._m
        for y in range(8):
            zeile = bild[y]
            for x in range(8):
                m[x, 7 - y] = zeile[x]
        m.apply()
        self._vorher = bild


def starten():
    daten = Daten(konfig.DATEI)
    uhr = Uhr()
    ansicht = Ansicht(daten)
    joystick = Joystick()
    schnittstelle = Schnittstelle()
    matrix = Matrix()

    # Stetig wachsender Millisekundenzähler; ticks_ms selbst läuft nach rund 12 Tagen über.
    ms = 0
    vorher = ticks_ms()

    meldung = protokoll.zustand(daten, uhr)
    meldung["hallo"] = True
    schnittstelle.senden(meldung)

    while True:
        t = ticks_ms()
        ms += ticks_diff(t, vorher)
        vorher = t

        for zeile in schnittstelle.zeilen():
            schnittstelle.senden(protokoll.verarbeiten(zeile, daten, uhr, ms))

        jetzt = uhr.jetzt(ms)
        for richtung in joystick.klicks():
            ansicht.klick(richtung, ms, jetzt)

        matrix.zeige(ansicht.bild(ms, jetzt))
        sleep_ms(TAKT_MS)
