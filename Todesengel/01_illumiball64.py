# iLLUM!BALL64 – ein Kugellabyrinth für das Lumatrix (8x8 LED-Matrix, Raspberry Pi Pico, MicroPython)
#
# Autorin:  Angela Maillard
# Version:  v1.0.0
#
# Du kippst ein Brett mit zwei unsichtbaren Drehknöpfen und rollst die Kugel ins grüne Ziel.
# Schwarze Felder sind Löcher: Wer hineinrollt, startet wieder beim letzten Checkpoint.
# Es gibt 64 Levels in acht Regionen, eines für jede LED der Matrix.
#
# Steuerung
#   Joystick links/rechts  Brett seitlich kippen: pro Druck eine Raste, Halten dreht weiter
#   Joystick hoch/runter   Brett nach hinten oder vorne kippen
#   Joystick Mitte         Brett gerade stellen; gedrückt halten: Pause und Kamerafahrt zum Ziel;
#                          drei Sekunden halten: zurück zur Levelwahl
#   Schiebeschalter        legt Brücken und Schaltbänder um: entweder Orange ist aktiv oder Blau
#
#   Die Neigung bleibt stehen, bis du zurückdrehst. Die tiefere Seite des Bretts ist dunkler:
#   Die Kugel rollt immer ins Dunkle.
#
# Levelwahl
#   Jede LED ist ein Level, jede Zeile eine Region mit eigener Farbe, geschaffte leuchten hell.
#   Der Joystick bewegt die blinkende Marke, die Mitte startet das Level. Der Fortschritt wird
#   auf dem Pico gespeichert. Löschen: die Mitte gedrückt halten. Nach einer Sekunde zählt eine
#   rote Zahl herunter; wer bis zum Ende hält, löscht alles (Laufschrift "RESET"), Loslassen
#   bricht ab.
#
# Beim Einschalten läuft ein Vorspann mit dem Namen des Spiels; jede Taste überspringt ihn.
#
# Was am Code besonders ist
#   - Die Kugel rollt stufenlos. Ihre Position ist eine Kommazahl, gezeichnet wird sie anteilig
#     auf bis zu vier LEDs (Spiel._zeichne_kugel).
#   - Die Neigung des Bretts ist als Helligkeitsverlauf sichtbar. Er kommt aus einer Tabelle und
#     wird nur mit ganzen Zahlen berechnet, ohne Grenzprüfung pro LED (Spiel._zeichne_brett).
#   - Die Kugel fällt erst, wenn rund um ihre Mitte kein Boden mehr ist. Darum lässt sich der
#     Schiebeschalter genau auf der Kante zwischen zwei Brücken umlegen (Spiel._rolle).
#   - Levels sind lesbarer Text und dürfen grösser sein als die Matrix, eine Kamera folgt der
#     Kugel (Teil 3 ganz unten, Spiel.lade_level, Spiel._kamera).
#   - Der ganze Spielstand ist eine einzige Zahl mit einem Bit pro Level
#     (Spiel._lade_fortschritt).
#   - Jeder Spielzustand hat seine eigene Methode, eine Tabelle wählt pro Bild die passende
#     (Spiel.schritt).
#   - Das Spiel braucht nur Module, die MicroPython mitbringt (machine, neopixel, time, math,
#     random), und keine weitere Bibliothek.
#
# Aufbau der Datei: 1. Einstellungen, 2. Spielmechanik, 3. Levels.

import gc
from math import sin, cos
from random import randint, random
from machine import Pin
from neopixel import NeoPixel
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms

__author__ = "Angela Maillard"
__version__ = "1.0.0"

# ====================================================================== 1. Einstellungen

# Hardware-Einstellungen
PIN_LEDS = 19
PIN_RECHTS = 2
PIN_HOCH = 3
PIN_RUNTER = 6
PIN_LINKS = 7
PIN_MITTE = 8
PIN_SCHALTER = 9

# Spielgefühl – hier darfst du schrauben
RASTEN = 3               # Stufen pro Kipprichtung
HALTEN_START = 0.35      # Sekunden, bis ein gehaltener Joystick von selbst eine Raste weiterdreht
HALTEN_TAKT = 0.16       # ... und danach alle so viele Sekunden eine weitere
BESCHLEUNIGUNG = 9.0     # Felder/s² bei voller Neigung (grösser = schwerer)
ROLLWIDERSTAND = 1.65    # grösser = Kugel rollt schneller aus (kleiner = schwerer)
EIS_WIDERSTAND = 0.3     # Rollwiderstand auf Eis: fast keiner
SAND_WIDERSTAND = 9.0    # Rollwiderstand im Sand
BAND_SCHUB = 5.0         # Felder/s², so stark schiebt ein Förderband (voll gekippt hält man knapp dagegen)
MAX_TEMPO = 16.0         # Felder/s, schneller wird die Kugel nie
PRALL = 0.65             # Anteil des Tempos, der beim Abprallen an einer Wand bleibt
KUGEL_RADIUS = 0.35      # in Feldern
LOCH_RAND = 0.2          # so weit darf die Kugelmitte über eine Lochkante ragen (kleiner = schwerer)
VORSCHAU = 0.3           # Kamera schaut so viele Sekunden in Rollrichtung voraus

# Start und Spielstand
START_LEVEL = 0          # 0 = Levelwahl beim Einschalten; zum Testen eine Levelnummer eintragen
SPEICHER_DATEI = "illumiball64.sav"     # in dieser Datei liegt der Fortschritt auf dem Pico

# Farben (Rot, Grün, Blau) – bewusst dunkel, volle Helligkeit braucht viel Strom
SCHWARZ = (0, 0, 0)
FARBE_KUGEL = (99, 99, 99)
# Der Boden ist reines Weiss, nur seine Helligkeit folgt der Neigung. Angaben in Prozent der Kugel:
BODEN_UNTEN = 4          # tiefste Stelle des voll gekippten Bretts
BODEN_FLACH = 11       # gerades Brett
BODEN_OBEN = 18          # höchste Stelle des voll gekippten Bretts
FARBE_EIS = (6, 10, 14)  # bei Eis und Sand nur der Farbton, die Helligkeit folgt derselben Skala
FARBE_SAND = (12, 11, 0)
FARBE_LOCH = (0, 0, 0)
FARBE_CHECK = (10, 0, 6)         # Checkpoint, noch nicht berührt
FARBE_CHECK_AN = (40, 0, 25)     # ... und der zuletzt berührte
FARBE_A = (45, 16, 0)            # Brücke A, wenn sie trägt; Schaltbänder bei Schalter 1
FARBE_A_AUS = (4, 1, 0)          # Brücke A, wenn sie nicht trägt
FARBE_B = (0, 14, 45)            # Brücke B, wenn sie trägt; Schaltbänder bei Schalter 0
FARBE_B_AUS = (0, 1, 5)          # Brücke B, wenn sie nicht trägt
FARBE_BAND = (22, 0, 40)         # Förderbänder
FARBE_RING = (0, 50, 8)          # Welle, die sich vom erreichten Ziel ausbreitet
FARBE_LOS = (0, 60, 8)           # "GO" vor dem Level
FARBE_HAKEN = (0, 60, 8)         # Haken nach dem Level
FARBE_KREUZ = (60, 0, 0)         # Kreuz nach einem Sturz
FARBE_RESET = (40, 0, 0)         # Countdown und Laufschrift beim Löschen des Fortschritts
FARBE_RAKETE = (60, 45, 20)      # aufsteigende Rakete im Feuerwerk
FEUERWERK_FARBEN = ((90, 20, 0), (90, 70, 0), (0, 90, 20), (0, 60, 90),   # Funken: jede Rakete
                    (70, 0, 90), (90, 0, 40), (80, 80, 80))               # platzt in einer davon

# Regionen und Texte
REGION = 8               # so viele Levels bilden eine Region (eine Zeile der Levelwahl)
REGIONSFARBEN = ((40, 0, 0), (40, 14, 0), (30, 26, 0), (0, 36, 0),
                 (0, 28, 24), (0, 10, 40), (22, 0, 38), (36, 0, 18))
SPIELNAME = "iLLUM!BALL64"     # läuft im Vorspann beim Einschalten durch; leer = kein Vorspann
REGION_TEXT = "AREA CLEARED"   # läuft durch den Regenbogen, sobald alle Levels einer Region geschafft sind
SCHLUSS_TEXT = "ALL CLEARED"   # ... und das, sobald alle Levels des Spiels geschafft sind
RESET_TEXT = "RESET"           # ... und das auf rotem Grund, wenn der Fortschritt gelöscht wurde
RESET_SEKUNDEN = 5             # so lange zählt die rote Zahl herunter, bevor gelöscht wird

# ====================================================================== 2. Spielmechanik

# ---------------------------------------------------------------------- Takt und Dauern

BILD_MS = 20                             # 50 Bilder pro Sekunde
DT = BILD_MS / 1000                      # Dauer eines Bildes in Sekunden
SEKUNDE = 1000 // BILD_MS                # Bilder pro Sekunde
DAEMPFUNG = 1 - ROLLWIDERSTAND * DT      # so viel Tempo bleibt der Kugel nach einem Bild
EIS_DAEMPFUNG = 1 - EIS_WIDERSTAND * DT
SAND_DAEMPFUNG = 1 - SAND_WIDERSTAND * DT

# Dauer der einzelnen Abschnitte in Bildern
ZAHL_BILDER = 60                         # Levelnummer vor dem Level
LOS_BILDER = 65                          # "GO"
STURZ_BILDER = 18                        # die Kugel verschwindet im Loch
KREUZ_BILDER = 25                        # rotes Kreuz nach dem Sturz
GEWONNEN_BILDER = 30                     # grüne Welle am Ziel
HAKEN_BILDER = 35                        # grüner Haken nach dem Level
FEIER_TEMPO = 6                          # Bilder pro Spalte einer Laufschrift (grösser = langsamer)
FAHRT_TEMPO = 6                          # Bilder pro Feld bei der Kamerafahrt zum Ziel
BLICK_NACH = 20                          # Mitte so lange halten, bis die Kamera zum Ziel fährt
MENUE_NACH = 150                         # ... und so lange, bis die Levelwahl erscheint
HALTEN_START_BILDER = max(1, int(HALTEN_START * SEKUNDE))
HALTEN_TAKT_BILDER = max(1, int(HALTEN_TAKT * SEKUNDE))
TITEL_WELLE = 30                         # Vorspann: so lange breitet sich der Regenbogenring aus
TITEL_KIPPEN = 70                        # ... und so lange taumelt das Brett einmal im Kreis
FEUERWERK_BILDER = 250                   # so lange steigen einzelne Raketen, dann folgt das Finale
RAKETEN_TAKT = 25                        # alle so viele Bilder startet eine Rakete
FUNKEN_LEBEN = 28                        # so viele Bilder glüht ein Funke

# ---------------------------------------------------------------------- Felder und Zustände

# Feldtypen. Die Reihenfolge zählt: bis BRUECKE_B feste Farbe, dann Felder mit Helligkeitsverlauf,
# dann die Bänder.
(LEER, WAND, LOCH, ZIEL, CHECK, CHECK_AN, BRUECKE_A, BRUECKE_B, BODEN, EIS, SAND,
 BAND_R, BAND_L, BAND_O, BAND_U, SCHALT_H, SCHALT_V) = range(17)
ZEICHEN = {" ": LEER, ".": BODEN, "S": BODEN, "#": WAND, "O": LOCH, "Z": ZIEL, "C": CHECK,
           "A": BRUECKE_A, "B": BRUECKE_B, "~": EIS, ":": SAND,
           ">": BAND_R, "<": BAND_L, "^": BAND_O, "v": BAND_U, "=": SCHALT_H, "!": SCHALT_V}

# Spielzustände. Die Reihenfolge muss zur Tabelle Spiel._schritte passen.
MENUE, ZAHL, LOS, SPIEL, STURZ, KREUZ, GEWONNEN, HAKEN, FEIER, TITEL, FEUERWERK = range(11)

# ---------------------------------------------------------------------- Schrift und Bilder

# Ziffern und Buchstaben als 3x5-Punktmuster: je Zeile eine Zahl, deren drei Bits die Pixel von
# links nach rechts sind. Einzelne Zeichen haben eine andere Breite (siehe BREITEN): Das M braucht
# fünf Pixel, um klar lesbar zu sein, das kleine i und das Ausrufezeichen nur einen.
ZIFFERN = ((7, 5, 5, 5, 7), (2, 6, 2, 2, 7), (7, 1, 7, 4, 7), (7, 1, 7, 1, 7), (5, 5, 7, 1, 1),
           (7, 4, 7, 1, 7), (7, 4, 7, 5, 7), (7, 1, 2, 2, 2), (7, 5, 7, 5, 7), (7, 5, 7, 1, 7))
BUCHSTABEN = {
    "A": (2, 5, 7, 5, 5), "B": (6, 5, 6, 5, 6), "C": (3, 4, 4, 4, 3), "D": (6, 5, 5, 5, 6),
    "E": (7, 4, 6, 4, 7), "F": (7, 4, 6, 4, 4), "G": (7, 4, 5, 5, 7), "H": (5, 5, 7, 5, 5),
    "I": (7, 2, 2, 2, 7), "J": (1, 1, 1, 5, 2), "K": (5, 5, 6, 5, 5), "L": (4, 4, 4, 4, 7),
    "M": (17, 27, 21, 17, 17), "N": (6, 5, 5, 5, 5), "O": (7, 5, 5, 5, 7), "P": (6, 5, 6, 4, 4),
    "Q": (2, 5, 5, 6, 3), "R": (6, 5, 6, 5, 5), "S": (3, 4, 2, 1, 6), "T": (7, 2, 2, 2, 2),
    "U": (5, 5, 5, 5, 7), "V": (5, 5, 5, 5, 2), "W": (5, 5, 7, 7, 5), "X": (5, 5, 2, 5, 5),
    "Y": (5, 5, 2, 2, 2), "Z": (7, 1, 2, 4, 7), "i": (1, 0, 1, 1, 1), "!": (1, 1, 1, 0, 1)}
BREITEN = {"M": 5, "i": 1, "!": 1}

# Ganze 8x8-Bilder: je Zeile eine Zahl, deren acht Bits die Pixel von links nach rechts sind
BILD_HAKEN = (0x00, 0x01, 0x03, 0x86, 0xCC, 0x78, 0x30, 0x00)
BILD_KREUZ = (0xC3, 0xE7, 0x7E, 0x3C, 0x3C, 0x7E, 0xE7, 0xC3)

# ---------------------------------------------------------------------- Farbtabellen
# Alle Farben werden einmal beim Start berechnet. Beim Zeichnen wird nur noch nachgeschlagen.


def _verlauf(farbe):
    """Die Helligkeitsstufen aus _hell für einen Farbton."""
    spitze = max(farbe)
    return tuple(tuple(int(kanal * h / spitze + 0.5) for kanal in farbe) for h in _hell)


def _welle(farbe):
    """Vier Helligkeiten einer Farbe: aus ihnen entsteht die Lichtwelle auf einem Band."""
    return tuple(tuple(int(kanal * f) for kanal in farbe) for f in (1.0, 0.4, 0.12, 0.12))


def _regenbogen(pos):
    """Eine Regenbogenfarbe; nach 96 Schritten ist der Farbkreis einmal durchlaufen."""
    pos %= 96
    if pos < 32:
        return ((32 - pos) * 3 // 2, pos * 3 // 2, 0)
    if pos < 64:
        return (0, (64 - pos) * 3 // 2, (pos - 32) * 3 // 2)
    return ((pos - 64) * 3 // 2, 0, (96 - pos) * 3 // 2)


# Boden, Eis und Sand haben 15 Helligkeitsstufen: gleichmässig von BODEN_UNTEN über BODEN_FLACH
# (die mittlere Stufe, das gerade Brett) bis BODEN_OBEN. Welche Stufe eine LED bekommt, hängt von
# der Neigung und vom Abstand der LED zur Bildmitte ab (siehe Spiel._zeichne_brett).
#   KIPP_FAKTOR   Das voll gekippte Brett soll innerhalb des Wandrahmens die ganze Skala zeigen,
#                 also 7 Stufen auf 2.5 Pixel Abstand. Gerechnet wird in halben Pixeln und in
#                 Sechzehntelstufen: 7 * 16 / 5 ergibt 22.
#   VERLAUF_RAND  Sind beide Achsen voll gekippt, liegt die äusserste LED 12 Stufen ausserhalb
#                 der Skala. Darum hängen vorne und hinten je 13 Kopien der Randstufe an der
#                 Tabelle, und beim Zeichnen muss niemand die Grenzen prüfen.
#   VERLAUF_NULL  Tabellenplatz der mittleren Stufe in Sechzehnteln, plus 8 zum Runden.
KIPP_FAKTOR = 22
VERLAUF_RAND = 13
VERLAUF_NULL = (VERLAUF_RAND + 7) * 16 + 8
_hell = ([BODEN_UNTEN + (BODEN_FLACH - BODEN_UNTEN) * i / 7 for i in range(7)]
         + [BODEN_FLACH + (BODEN_OBEN - BODEN_FLACH) * i / 7 for i in range(8)])
_hell = [prozent * max(FARBE_KUGEL) / 100 for prozent in _hell]
_hell = [_hell[0]] * VERLAUF_RAND + _hell + [_hell[14]] * VERLAUF_RAND
VERLAUF = (_verlauf((1, 1, 1)), _verlauf(FARBE_EIS), _verlauf(FARBE_SAND))

# Das Ziel pulsiert durch 16 Grüntöne
ZIEL_PAL = tuple((0, 12 + 3 * i, i // 3) for i in range(16))
# 32 Farben einmal um den Farbkreis
REGENBOGEN_PAL = tuple(_regenbogen(i * 3) for i in range(32))
# Levelwahl: je Region ein Paar aus dunkler Farbe (noch offen) und heller (geschafft)
MENUE_PAL = tuple(((max(f[0] // 8, 1 if f[0] else 0), max(f[1] // 8, 1 if f[1] else 0),
                    max(f[2] // 8, 1 if f[2] else 0)), f) for f in REGIONSFARBEN)

# Bänder: Auf ihnen läuft eine Lichtwelle in Schubrichtung. Je Bandtyp steht hier, ob die Welle
# waagrecht läuft, in welche Richtung und in welcher Farbe. Die zwei Schaltbänder am Schluss
# hängen vom Schiebeschalter ab.
_lila = _welle(FARBE_BAND)
_orange = _welle(FARBE_A)
_blau = _welle(FARBE_B)
BAND_FEST = ((True, -1, _lila), (True, 1, _lila), (False, -1, _lila), (False, 1, _lila))
BAND_BEI_1 = ((True, -1, _orange), (False, -1, _orange))
BAND_BEI_0 = ((True, 1, _blau), (False, 1, _blau))
# Schub der vier festen Bänder auf die Kugel (rechts, links, oben, unten) in Feldern/s²
SCHUB_FEST = ((BAND_SCHUB, 0.0), (-BAND_SCHUB, 0.0), (0.0, BAND_SCHUB), (0.0, -BAND_SCHUB))

# Für den Vorspann: ein leeres Brett aus 8x8 Bodenfeldern, das die normale Zeichenroutine kippt
TITEL_KARTE = [bytearray([BODEN] * 8)] * 8

# ---------------------------------------------------------------------- Das Spiel


class Spiel:
    """Das ganze Spiel: schritt() rechnet ein Bild weiter, zeichne() bringt es auf die Matrix."""

    def __init__(self, np):
        self.np = np

        # Zustand und Zeit
        self.zustand = MENUE
        self.bild = 0                    # Bilder seit dem Einschalten (für Blinken und Pulsieren)
        self.zaehler = 0                 # Bilder seit Beginn des aktuellen Zustands
        # Die Methode für jeden Spielzustand, in der Reihenfolge der Zustandsnummern
        self._schritte = (self._in_menue, self._in_zahl, self._in_los, self._in_spiel,
                          self._in_sturz, self._in_kreuz, self._in_gewonnen, self._in_haken,
                          self._in_feier, self._in_titel, self._in_feuerwerk)

        # Eingabe: was in diesem Bild gedrückt ist (schritt füllt diese Werte)
        self.joy_x = self.joy_y = 0      # Joystick-Richtung je Achse: -1, 0 oder 1
        self.mitte = False               # ist die Mitte gedrückt?
        self.mitte_frisch = False        # ... und zwar erst seit diesem Bild?
        self.neuer_druck = False         # wurde in diesem Bild irgendeine Taste neu gedrückt?
        # Eingabe: was vorher war
        self.richtung = [0, 0]           # die schon verarbeitete Richtung je Achse
        self.warte = [0, 0]              # Bilder, bis ein gehaltener Joystick weiterdreht
        self.druck_alt = False           # war im letzten Bild irgendeine Taste gedrückt?
        self.mitte_war = False           # war im letzten Bild die Mitte gedrückt?
        self.mitte_alt = False           # wird die Mitte seit einem Druck im Spiel gehalten?
        self.mitte_zeit = 0              # ... und seit wie vielen Bildern
        self.halte = 0                   # Levelwahl: so viele Bilder wird die Mitte schon gehalten

        # Level und Kugel (lade_level und _setze_kugel füllen diese Werte)
        self.level = 0
        self.karte = None                # die Felder des Levels: eine Liste von Zeilen
        self.breite = self.hoehe = 0
        self.ziel = self.check = (0.0, 0.0)   # Mitte des Ziels und des letzten Checkpoints
        self.check_feld = None           # Feld des zuletzt berührten Checkpoints
        self.x = self.y = 0.0            # Kugelmitte in Feldern
        self.vx = self.vy = 0.0          # Tempo in Feldern/s
        self.raste_x = self.raste_y = 0  # Stellung der beiden Drehknöpfe
        self.neig_x = self.neig_y = 0.0  # Neigung des Bretts von -1 bis 1, folgt den Knöpfen
        self.kamera_x = self.kamera_y = 0     # das Feld, das unten links im Bild liegt
        self.blick_von = (0, 0)          # Kamerastand vor dem Blick zum Ziel
        self.sog_x = self.sog_y = 0.0    # dorthin zieht es die Kugel bei Sturz und Ziel
        self.stuerze = 0
        self.zeit = 0                    # Spielzeit im Level, in Bildern

        # Schiebeschalter, Brücken und Bänder
        self.palette = [FARBE_LOCH] * BODEN            # Farbe je Feldtyp mit fester Farbe
        self.palette[CHECK] = FARBE_CHECK
        self.palette[CHECK_AN] = FARBE_CHECK_AN
        self.band = list(BAND_FEST) + [None, None]     # Lichtwelle je Bandtyp
        self.schub = list(SCHUB_FEST) + [None, None]   # Schub je Bandtyp
        self.offen = ()                  # Feldtypen, durch die die Kugel gerade fällt
        self.schalter = None
        self._setze_schalter(False)

        # Levelwahl, Laufschrift und Vorspann
        self.wahl = 0                    # das markierte Level
        self.laufschrift = []            # Pixelspalten des laufenden Texts
        self.feier_grund = None          # Hintergrundfarbe der Laufschrift, None = Regenbogen
        self.feier_danach = None         # Level nach der Laufschrift, None = Levelwahl
        self.akt = 0                     # Akt des Vorspanns
        self.lauf = 0                    # Vorspann: so viele Bilder läuft der Name schon
        self.landungen = []              # Vorspann: in diesen Bildern landet die Kugel
        self.hopser = 0
        self.sprung_g = self.sprung_v = 0.0
        self.raketen = []                # Feuerwerk, je Rakete: [x, y, Höhe des Platzens, Farbe]
        self.funken = []                 # je Funke: [x, y, Tempo x, Tempo y, Leben, Farbe]

        self.geloest = self._lade_fortschritt()   # ein Bit für jedes geschaffte Level
        if START_LEVEL:
            self.lade_level(min(START_LEVEL, len(LEVELS)) - 1)
        elif SPIELNAME:
            self._beginne_titel()
        else:
            self._oeffne_menue(self._erstes_offenes())

    # -------------------------------------------------------------- Fortschritt und Levelwahl

    def _lade_fortschritt(self):
        """Der Fortschritt ist eine Zahl, in der jedes geschaffte Level ein Bit setzt.

        Davor steht die Anzahl Levels: passt sie nicht mehr, stammt der Stand von einer anderen
        Levelliste und wird verworfen.
        """
        if not SPEICHER_DATEI:
            return 0
        try:
            with open(SPEICHER_DATEI) as datei:
                anzahl, geloest = datei.read().split()
            if int(anzahl) != len(LEVELS):
                return 0
            return int(geloest) & ((1 << len(LEVELS)) - 1)
        except (OSError, ValueError):
            return 0

    def _speichere_fortschritt(self):
        """Schreibt den Fortschritt auf den Pico. Geht das nicht, läuft das Spiel trotzdem weiter."""
        if not SPEICHER_DATEI:
            return
        try:
            with open(SPEICHER_DATEI, "w") as datei:
                datei.write(str(len(LEVELS)) + " " + str(self.geloest))
        except OSError:
            pass

    def _erstes_offenes(self):
        """Das erste Level, das noch nicht geschafft ist."""
        for nr in range(len(LEVELS)):
            if not self.geloest >> nr & 1:
                return nr
        return 0

    def _oeffne_menue(self, wahl):
        """Zeigt die Levelwahl mit der Marke auf dem Level `wahl`."""
        self.zustand = MENUE
        self.wahl = wahl
        self.halte = 0
        self.richtung[0] = self.richtung[1] = 0

    # -------------------------------------------------------------- Level laden

    def lade_level(self, nr):
        """Wandelt den Text eines Levels in die Karte um und setzt die Kugel auf den Start."""
        name, wandfarbe, text = LEVELS[nr]
        self.level = nr
        self.karte = None                # die alte Karte freigeben, bevor die neue entsteht
        gc.collect()
        zeilen = text.split("\n")
        if not zeilen[0]:
            zeilen = zeilen[1:]
        # Ein Rand aus Leere rundherum: so fällt die Kugel, bevor sie die Karte verlässt
        breite = max(max(len(z) for z in zeilen), 8) + 2
        hoehe = max(len(zeilen), 8) + 2
        karte = [bytearray(breite) for _ in range(hoehe)]
        start = ziel = None
        for reihe, zeile in enumerate(zeilen):
            ty = hoehe - 2 - reihe
            for spalte, zeichen in enumerate(zeile):
                karte[ty][spalte + 1] = ZEICHEN.get(zeichen, LEER)
                if zeichen == "S":
                    start = (spalte + 1.5, ty + 0.5)
                elif zeichen == "Z":
                    ziel = (spalte + 1.5, ty + 0.5)
        if start is None or ziel is None:
            raise ValueError("Level " + name + " braucht ein S und ein Z")
        self.karte = karte
        self.breite = breite
        self.hoehe = hoehe
        self.palette[WAND] = wandfarbe
        self.ziel = ziel

        self.check = start
        self.check_feld = None
        self.stuerze = 0
        self.zeit = 0
        self._setze_kugel(start)

        # Vorspann: Levelnummer, dann "GO" – das Level selbst ist erst danach zu sehen
        self._beginne(ZAHL)
        print("Level", nr + 1, "-", name)

    def _setze_kugel(self, punkt):
        """Legt die Kugel ruhig auf einen Punkt und stellt das Brett gerade."""
        self.x, self.y = punkt
        self.vx = self.vy = 0.0
        self.raste_x = self.raste_y = 0
        self.neig_x = self.neig_y = 0.0
        self.richtung[0] = self.richtung[1] = 0
        self.mitte_alt = False
        self.kamera_x, self.kamera_y = self._kamera_fuer(punkt)

    def _kamera_fuer(self, punkt):
        """Der Bildausschnitt mit dem Punkt möglichst in der Mitte, ohne über den Levelrand zu ragen."""
        return (min(max(int(punkt[0] - 3.5), 1), self.breite - 9),
                min(max(int(punkt[1] - 3.5), 1), self.hoehe - 9))

    def _setze_schalter(self, schalter):
        """Übernimmt die Stellung des Schiebeschalters für Brücken und Schaltbänder."""
        self.schalter = schalter
        # Die Brücke, die gerade nicht trägt, zählt als Loch; die Schaltbänder drehen um
        if schalter:
            self.offen = (LEER, LOCH, BRUECKE_B)
            self.palette[BRUECKE_A] = FARBE_A
            self.palette[BRUECKE_B] = FARBE_B_AUS
            self.band[4], self.band[5] = BAND_BEI_1
            self.schub[4], self.schub[5] = SCHUB_FEST[0], SCHUB_FEST[2]
        else:
            self.offen = (LEER, LOCH, BRUECKE_A)
            self.palette[BRUECKE_A] = FARBE_A_AUS
            self.palette[BRUECKE_B] = FARBE_B
            self.band[4], self.band[5] = BAND_BEI_0
            self.schub[4], self.schub[5] = SCHUB_FEST[1], SCHUB_FEST[3]

    def _beginne(self, zustand):
        """Wechselt den Spielzustand und zählt seine Bilder wieder von null."""
        self.zustand = zustand
        self.zaehler = 0

    # -------------------------------------------------------------- Spielablauf, einmal pro Bild

    def schritt(self, rechts, links, hoch, runter, mitte, schalter):
        """Rechnet ein Bild weiter. Die Eingaben sagen, was gerade gedrückt ist."""
        self.bild += 1
        self.zaehler += 1
        if schalter != self.schalter:
            self._setze_schalter(schalter)
        druck = rechts or links or hoch or runter or mitte
        self.neuer_druck = druck and not self.druck_alt
        self.druck_alt = druck
        self.mitte_frisch = mitte and not self.mitte_war
        self.mitte_war = self.mitte = mitte
        self.joy_x = rechts - links
        self.joy_y = hoch - runter
        # Jeder Zustand hat seine eigene Methode; die Tabelle liefert die passende
        self._schritte[self.zustand]()

    def _in_spiel(self):
        if self.mitte:
            if not self.mitte_alt:
                # Ein Druck stellt das Brett gerade, das Spiel läuft dabei weiter
                self.mitte_alt = True
                self.mitte_zeit = 0
                self.raste_x = self.raste_y = 0
            self.mitte_zeit += 1
            if self.mitte_zeit > MENUE_NACH:
                self._oeffne_menue(self.level)
                return
            if self.mitte_zeit > BLICK_NACH:
                # Länger gehalten: Pause, und die Kamera fährt zum Ziel
                if self.mitte_zeit == BLICK_NACH + 1:
                    self.blick_von = (self.kamera_x, self.kamera_y)
                self._fahre(self.blick_von, self._kamera_fuer(self.ziel), self.mitte_zeit - BLICK_NACH)
                return
        elif self.mitte_alt:
            self.mitte_alt = False
            if self.mitte_zeit > BLICK_NACH:
                self.kamera_x, self.kamera_y = self.blick_von
        self._steuere(self.joy_x, self.joy_y)
        self._rolle()
        self._kamera()
        self.zeit += 1

    def _in_menue(self):
        self._waehle(self.joy_x, self.joy_y)
        if self.mitte:
            if self.mitte_frisch:
                self.halte = 1
            elif self.halte:
                # Gehalten: nach einer Sekunde läuft der rote Countdown, an dessen Ende der
                # Fortschritt gelöscht wird
                self.halte += 1
                if self.halte >= (1 + RESET_SEKUNDEN) * SEKUNDE:
                    self.geloest = 0
                    self._speichere_fortschritt()
                    self._beginne_feier(RESET_TEXT, FARBE_RESET, None)
        elif self.halte:
            # Losgelassen: ein kurzer Druck startet das Level, ein langer bricht nur ab
            kurz = self.halte < SEKUNDE
            self.halte = 0
            if kurz:
                self.lade_level(self.wahl)

    def _in_zahl(self):
        if self.zaehler >= ZAHL_BILDER or self.neuer_druck:
            self._beginne(LOS)

    def _in_los(self):
        if self.zaehler >= LOS_BILDER or self.neuer_druck:
            self.zustand = SPIEL

    def _in_sturz(self):
        self._ziehe_zur_mitte()
        if self.zaehler >= STURZ_BILDER:
            self._beginne(KREUZ)

    def _in_kreuz(self):
        if self.zaehler >= KREUZ_BILDER:
            # Nach dem Kreuz geht es ohne Vorspann beim letzten Checkpoint weiter
            self.stuerze += 1
            self._setze_kugel(self.check)
            self.zustand = SPIEL

    def _in_gewonnen(self):
        self._ziehe_zur_mitte()
        if self.zaehler >= GEWONNEN_BILDER:
            self._beginne(HAKEN)

    def _in_haken(self):
        if self.zaehler < HAKEN_BILDER:
            return
        print("  geschafft in", self.zeit * BILD_MS // 100 / 10, "s,", self.stuerze, "Stürze")
        neu = not self.geloest >> self.level & 1
        if neu:
            self.geloest |= 1 << self.level
            self._speichere_fortschritt()
        weiter = self.level + 1 if self.level + 1 < len(LEVELS) else None
        # Gefeiert wird nur, wenn genau dieses Level das letzte war, das noch gefehlt hat:
        # im ganzen Spiel oder in seiner Region, egal an welcher Stelle der Region es steht
        if neu and self.geloest == (1 << len(LEVELS)) - 1:
            self._beginne_feuerwerk()    # danach läuft SCHLUSS_TEXT
        elif neu and self._region_geschafft(self.level):
            if weiter is not None and self.geloest >> weiter & 1:
                weiter = None            # das nächste Level ist schon geschafft: zur Levelwahl
            self._beginne_feier(REGION_TEXT, None, weiter)
        elif weiter is None:
            self._oeffne_menue(self._erstes_offenes())
        else:
            self.lade_level(weiter)

    def _region_geschafft(self, level):
        """Sind alle Levels der Region geschafft, zu der dieses Level gehört?"""
        erstes = level // REGION * REGION
        anzahl = min(REGION, len(LEVELS) - erstes)
        maske = ((1 << anzahl) - 1) << erstes
        return (self.geloest & maske) == maske

    def _in_feier(self):
        if self.zaehler >= (len(self.laufschrift) + 8) * FEIER_TEMPO:
            if self.feier_danach is None:
                self._oeffne_menue(self._erstes_offenes())
            else:
                self.lade_level(self.feier_danach)

    def _in_titel(self):
        if self.neuer_druck:
            # Übersprungen: die noch gehaltene Taste soll in der Levelwahl nichts auslösen
            self._oeffne_menue(self._erstes_offenes())
            self.richtung[0] = self.joy_x
            self.richtung[1] = self.joy_y
        else:
            self._titel()

    # -------------------------------------------------------------- Eingabe und Physik

    def _waehle(self, dx, dy):
        """Levelwahl: links/rechts ein Level weiter, hoch/runter eine ganze Zeile (acht Levels)."""
        wahl = self.wahl
        if dx != self.richtung[0]:
            self.richtung[0] = dx
            wahl += dx
        if dy != self.richtung[1]:
            self.richtung[1] = dy
            wahl -= 8 * dy
        if 0 <= wahl < len(LEVELS):
            self.wahl = wahl

    def _steuere(self, dx, dy):
        """Dreht die beiden Knöpfe nach dem Joystick und lässt das Brett ihnen folgen."""
        self.raste_x = self._drehe(0, dx, self.raste_x)
        self.raste_y = self._drehe(1, dy, self.raste_y)
        # Das Brett kippt nicht schlagartig, sondern folgt dem Knopf über ein paar Bilder
        self.neig_x += min(max(self.raste_x / RASTEN - self.neig_x, -0.12), 0.12)
        self.neig_y += min(max(self.raste_y / RASTEN - self.neig_y, -0.12), 0.12)

    def _drehe(self, achse, richtung, raste):
        """Ein neuer Druck dreht den Knopf eine Raste weiter; wer hält, dreht nach einer Pause weiter."""
        if richtung != self.richtung[achse]:
            self.richtung[achse] = richtung
            self.warte[achse] = HALTEN_START_BILDER
        elif richtung:
            self.warte[achse] -= 1
            if self.warte[achse] > 0:
                return raste
            self.warte[achse] = HALTEN_TAKT_BILDER
        return min(max(raste + richtung, -RASTEN), RASTEN)

    def _rolle(self):
        """Bewegt die Kugel um ein Bild: beschleunigen, an Wänden abprallen, Feld unter ihr prüfen."""
        karte = self.karte
        r = KUGEL_RADIUS
        # Der Untergrund bestimmt, wie stark die Kugel gebremst oder geschoben wird
        ax = self.neig_x * BESCHLEUNIGUNG
        ay = self.neig_y * BESCHLEUNIGUNG
        daempfung = DAEMPFUNG
        feld = karte[int(self.y)][int(self.x)]
        if feld > BODEN:
            if feld == EIS:
                daempfung = EIS_DAEMPFUNG
            elif feld == SAND:
                daempfung = SAND_DAEMPFUNG
            else:
                schub = self.schub[feld - BAND_R]
                ax += schub[0]
                ay += schub[1]
        vx = min(max((self.vx + ax * DT) * daempfung, -MAX_TEMPO), MAX_TEMPO)
        vy = min(max((self.vy + ay * DT) * daempfung, -MAX_TEMPO), MAX_TEMPO)

        # Erst waagrecht, dann senkrecht bewegen: so wird jede Wand für sich geprüft
        x = self.x + vx * DT
        y = self.y
        if vx:
            tx = int(x + r) if vx > 0 else int(x - r)
            if karte[int(y - r)][tx] == WAND or karte[int(y + r)][tx] == WAND:
                x = tx - r - 0.001 if vx > 0 else tx + 1 + r + 0.001
                vx = -vx * PRALL
        y += vy * DT
        if vy:
            ty = int(y + r) if vy > 0 else int(y - r)
            if karte[ty][int(x - r)] == WAND or karte[ty][int(x + r)] == WAND:
                y = ty - r - 0.001 if vy > 0 else ty + 1 + r + 0.001
                vy = -vy * PRALL
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

        tx = int(x)
        ty = int(y)
        feld = karte[ty][tx]
        if feld == ZIEL:
            self._sog(GEWONNEN, tx, ty)
        elif feld == CHECK:
            if self.check_feld:
                karte[self.check_feld[1]][self.check_feld[0]] = CHECK
            karte[ty][tx] = CHECK_AN
            self.check_feld = (tx, ty)
            self.check = (tx + 0.5, ty + 0.5)
        elif feld in self.offen:
            # Die Kugel fällt erst, wenn rund um ihre Mitte kein fester Boden mehr ist
            offen = self.offen
            m = LOCH_RAND
            if (karte[int(y - m)][int(x - m)] in offen and karte[int(y - m)][int(x + m)] in offen
                    and karte[int(y + m)][int(x - m)] in offen and karte[int(y + m)][int(x + m)] in offen):
                self._sog(STURZ, tx, ty)

    def _sog(self, zustand, tx, ty):
        """Sturz oder Ziel: Von nun an zieht es die Kugel in die Mitte des Feldes (tx, ty)."""
        self._beginne(zustand)
        self.sog_x = tx + 0.5
        self.sog_y = ty + 0.5

    def _ziehe_zur_mitte(self):
        self.x += (self.sog_x - self.x) * 0.3
        self.y += (self.sog_y - self.y) * 0.3

    def _fahre(self, von, nach, t):
        """Kamerafahrt zwischen zwei Ausschnitten, t = Bilder seit Beginn. True, sobald sie ankommt."""
        dx = nach[0] - von[0]
        dy = nach[1] - von[1]
        dauer = FAHRT_TEMPO * max(abs(dx), abs(dy))
        if t >= dauer:
            self.kamera_x, self.kamera_y = nach
            return True
        if t > 0:
            self.kamera_x = von[0] + dx * t // dauer
            self.kamera_y = von[1] + dy * t // dauer
        return False

    def _kamera(self):
        """Lässt die Kamera der Kugel folgen und etwas in Rollrichtung vorausschauen."""
        # Die Kamera springt pixelweise, erst wenn die Kugel deutlich aus der Mitte läuft
        wunsch = self.x - 4.0 + min(max(self.vx * VORSCHAU, -1.5), 1.5)
        if wunsch - self.kamera_x > 0.7:
            self.kamera_x = min(self.kamera_x + 1, self.breite - 9)
        elif wunsch - self.kamera_x < -0.7:
            self.kamera_x = max(self.kamera_x - 1, 1)
        wunsch = self.y - 4.0 + min(max(self.vy * VORSCHAU, -1.5), 1.5)
        if wunsch - self.kamera_y > 0.7:
            self.kamera_y = min(self.kamera_y + 1, self.hoehe - 9)
        elif wunsch - self.kamera_y < -0.7:
            self.kamera_y = max(self.kamera_y - 1, 1)

    # -------------------------------------------------------------- Zeichnen

    def zeichne(self):
        """Zeichnet das Bild zum aktuellen Zustand und schickt es an die LEDs."""
        zustand = self.zustand
        if zustand == MENUE:
            if self.halte >= SEKUNDE:
                self._zeichne_zahl(RESET_SEKUNDEN - (self.halte - SEKUNDE) // SEKUNDE, FARBE_RESET)
            else:
                self._zeichne_menue()
        elif zustand == ZAHL:
            self._zeichne_zahl(self.level + 1, REGIONSFARBEN[self.level // REGION % len(REGIONSFARBEN)])
        elif zustand == TITEL:
            self._zeichne_titel()
        elif zustand == LOS:
            self._zeichne_bild(self._text(BUCHSTABEN["G"], BUCHSTABEN["O"]), FARBE_LOS)
        elif zustand == KREUZ:
            self._zeichne_bild(BILD_KREUZ, FARBE_KREUZ)
        elif zustand == HAKEN:
            self._zeichne_bild(BILD_HAKEN, FARBE_HAKEN)
        elif zustand == FEIER:
            self._zeichne_feier()
        elif zustand == FEUERWERK:
            self._zeichne_feuerwerk()
        else:
            self._zeichne_brett()
            if zustand == STURZ:
                self._zeichne_kugel(16 - 16 * self.zaehler // STURZ_BILDER)
            else:
                self._zeichne_kugel(16)
            if zustand == GEWONNEN:
                self._zeichne_ring()
        self.np.write()

    def _zeichne_brett(self):
        """Zeichnet den Ausschnitt des Levels, den die Kamera gerade zeigt."""
        np = self.np
        palette = self.palette
        puls = (self.bild >> 1) & 31
        palette[ZIEL] = ZIEL_PAL[puls if puls < 16 else 31 - puls]
        band = self.band
        welle = self.bild >> 3
        # Neigung als Helligkeitsverlauf: die tiefere Seite wird dunkler, die höhere heller.
        # Jede LED bekommt die Stufe "Neigung mal Abstand zur Bildmitte". Gerechnet wird mit
        # ganzen Zahlen in Sechzehntelstufen und halben Pixeln (2 * sx - 7), das ist schneller.
        kipp_x = -int(self.neig_x * KIPP_FAKTOR)
        kipp_y = -int(self.neig_y * KIPP_FAKTOR)
        kamera_x = self.kamera_x
        kamera_y = self.kamera_y
        i = 0
        for sy in range(8):
            zeile = self.karte[kamera_y + sy]
            verlauf = kipp_y * (2 * sy - 7) + VERLAUF_NULL
            for sx in range(8):
                feld = zeile[kamera_x + sx]
                if feld < BODEN:
                    np[i] = palette[feld]
                elif feld < BAND_R:
                    np[i] = VERLAUF[feld - BODEN][(verlauf + kipp_x * (2 * sx - 7)) >> 4]
                else:
                    # Die Lichtwelle hängt am Ort im Level, nicht am Bildschirm: so springt sie
                    # nicht, wenn die Kamera weiterrückt
                    waagrecht, richtung, farben = band[feld - BAND_R]
                    ort = kamera_x + sx if waagrecht else kamera_y + sy
                    np[i] = farben[(ort * richtung + welle) & 3]
                i += 1

    def _zeichne_kugel(self, hell):
        """Verteilt die Kugel je nach Position auf bis zu vier Pixel – so rollt sie stufenlos.

        hell geht von 0 (unsichtbar) bis 16 (voll). Jedes der vier Pixel bekommt den Anteil der
        Kugel, der auf ihm liegt, in Zweihundertsechsundfünfzigsteln.
        """
        fx = self.x - self.kamera_x - 0.5
        fy = self.y - self.kamera_y - 0.5
        ix = int(fx + 8) - 8
        iy = int(fy + 8) - 8
        ax = int((fx - ix) * 16)
        ay = int((fy - iy) * 16)
        self._tupfer(ix, iy, (16 - ax) * (16 - ay) * hell >> 4)
        self._tupfer(ix + 1, iy, ax * (16 - ay) * hell >> 4)
        self._tupfer(ix, iy + 1, (16 - ax) * ay * hell >> 4)
        self._tupfer(ix + 1, iy + 1, ax * ay * hell >> 4)

    def _tupfer(self, px, py, anteil):
        """Mischt die Kugelfarbe mit dem angegebenen Anteil (0 bis 256) in ein Pixel."""
        if anteil and 0 <= px < 8 and 0 <= py < 8:
            i = py * 8 + px
            r, g, b = self.np[i]
            self.np[i] = (r + ((FARBE_KUGEL[0] - r) * anteil >> 8),
                          g + ((FARBE_KUGEL[1] - g) * anteil >> 8),
                          b + ((FARBE_KUGEL[2] - b) * anteil >> 8))

    def _zeichne_ring(self):
        """Grüne Welle, die sich vom Ziel ausbreitet und das Level wegwischt."""
        np = self.np
        gx = int(self.sog_x) - self.kamera_x
        gy = int(self.sog_y) - self.kamera_y
        radius = self.zaehler // 2
        aussen = radius * radius
        innen = (radius - 2) * (radius - 2) if radius > 2 else -1
        i = 0
        for sy in range(8):
            for sx in range(8):
                abstand = (sx - gx) * (sx - gx) + (sy - gy) * (sy - gy)
                if abstand <= innen:
                    np[i] = SCHWARZ
                elif abstand <= aussen:
                    np[i] = FARBE_RING
                i += 1

    def _text(self, links, rechts):
        """Setzt zwei 3x5-Zeichen nebeneinander (oder eines in die Mitte) zu einem 8x8-Bild zusammen."""
        if links is None:
            return [0] + [zeile << 3 for zeile in rechts] + [0, 0]
        return [0] + [links[i] << 5 | rechts[i] << 1 for i in range(5)] + [0, 0]

    def _zeichne_bild(self, zeilen, farbe):
        """Zeichnet ein einfarbiges 8x8-Bild: je Zeile eine Zahl, jedes gesetzte Bit ein Pixel."""
        np = self.np
        for reihe in range(8):
            bits = zeilen[reihe]
            i = (7 - reihe) * 8
            for sx in range(8):
                np[i + sx] = farbe if bits & (0x80 >> sx) else SCHWARZ

    def _zeichne_zahl(self, zahl, farbe):
        """Zeigt eine Zahl von 0 bis 99."""
        zehner = ZIFFERN[zahl // 10 % 10] if zahl > 9 else None
        self._zeichne_bild(self._text(zehner, ZIFFERN[zahl % 10]), farbe)

    def _zeichne_menue(self):
        """Levelwahl: jede LED ein Level in der Farbe seiner Region, das markierte blinkt weiss."""
        np = self.np
        anzahl = len(LEVELS)
        geloest = self.geloest
        for i in range(64):
            nr = (7 - i // 8) * 8 + i % 8       # LED oben links ist Level 1
            if nr < anzahl:
                np[i] = MENUE_PAL[nr // REGION % len(MENUE_PAL)][geloest >> nr & 1]
            else:
                np[i] = SCHWARZ
        if self.bild & 8:
            np[(7 - self.wahl // 8) * 8 + self.wahl % 8] = FARBE_KUGEL

    # -------------------------------------------------------------- Laufschrift

    def _beginne_feier(self, text, grund, danach):
        """Startet eine Laufschrift, die dunkel aus dem Regenbogen (grund=None) oder einer Farbe
        ausgespart ist. Danach folgt das Level mit der Nummer `danach` oder die Levelwahl (None).
        """
        self.feier_grund = grund
        self.feier_danach = danach
        self.laufschrift = self._spalten(text)
        self._beginne(FEIER)

    def _spalten(self, text, mitten=None):
        """Zerlegt einen Text in Pixelspalten für die Laufschrift: je Zeichen seine Spalten und eine
        Lücke. In jeder Spalte steht ein Bit pro Zeile, Bit 0 ist die oberste.

        Wer eine Liste `mitten` mitgibt, bekommt darin die mittlere Spalte jedes Zeichens.
        """
        spalten = []
        for zeichen in text:
            muster = BUCHSTABEN.get(zeichen)
            if muster is None and "0" <= zeichen <= "9":
                muster = ZIFFERN[ord(zeichen) - 48]
            breite = BREITEN.get(zeichen, 3)
            if muster and mitten is not None:
                mitten.append(len(spalten) + breite // 2)
            for nr in range(breite - 1, -1, -1):
                spalte = 0
                if muster:
                    for reihe in range(5):
                        if muster[reihe] >> nr & 1:
                            spalte |= 1 << reihe
                spalten.append(spalte)
            spalten.append(0)
        return spalten

    def _zeichne_feier(self):
        """Zeichnet die Laufschrift dunkel ausgespart auf ihrem Grund. Ohne Grundfarbe ist das der
        Regenbogen: Jede LED läuft schnell durch alle Farben, leicht versetzt zu ihren Nachbarn."""
        np = self.np
        grund = self.feier_grund
        farbe = self.zaehler * 2
        schrift = self.laufschrift
        laenge = len(schrift)
        links = self.zaehler // FEIER_TEMPO - 8        # diese Textspalte steht gerade am linken Rand
        i = 0
        for sy in range(8):
            reihe = 1 << (6 - sy) if 2 <= sy <= 6 else 0    # der Text ist fünf Zeilen hoch
            for sx in range(8):
                spalte = links + sx
                if reihe and 0 <= spalte < laenge and schrift[spalte] & reihe:
                    np[i] = SCHWARZ
                elif grund:
                    np[i] = grund
                else:
                    np[i] = REGENBOGEN_PAL[(sx + sy + farbe) & 31]
                i += 1

    # -------------------------------------------------------------- Feuerwerk

    def _beginne_feuerwerk(self):
        """Wenn das letzte offene Level des Spiels geschafft ist: Raketen steigen und platzen in
        farbige Funken, zum Schluss drei auf einmal. Danach läuft die Laufschrift SCHLUSS_TEXT."""
        self.raketen = []
        self.funken = []
        self._beginne(FEUERWERK)

    def _starte_rakete(self, x):
        """Eine Rakete in Spalte x: Sie platzt in zufälliger Höhe und in einer zufälligen Farbe."""
        farbe = FEUERWERK_FARBEN[randint(0, len(FEUERWERK_FARBEN) - 1)]
        self.raketen.append([x, 0.0, 3.5 + 3.0 * random(), farbe])

    def _in_feuerwerk(self):
        t = self.zaehler
        if t < FEUERWERK_BILDER:
            if t % RAKETEN_TAKT == 1:
                self._starte_rakete(randint(1, 6) + 0.5)
        elif t == FEUERWERK_BILDER:
            for x in (1.5, 4.0, 6.5):    # das Finale
                self._starte_rakete(x)
        elif not self.raketen and not self.funken:
            self._beginne_feier(SCHLUSS_TEXT, None, None)
            return

        # Raketen steigen gleichmässig; in ihrer Höhe platzen sie zu einem Kranz aus zehn Funken
        for rakete in self.raketen:
            rakete[1] += 10 * DT
            if rakete[1] >= rakete[2]:
                for nr in range(10):
                    winkel = 0.6283 * nr
                    tempo = 3.0 + 2.0 * random()
                    self.funken.append([rakete[0], rakete[1], tempo * cos(winkel), tempo * sin(winkel),
                                        FUNKEN_LEBEN, rakete[3]])
        self.raketen = [rakete for rakete in self.raketen if rakete[1] < rakete[2]]

        # Funken fliegen auseinander, werden von der Luft gebremst, sinken und verglühen
        for funke in self.funken:
            funke[2] *= 0.96
            funke[3] = (funke[3] - 5 * DT) * 0.96
            funke[0] += funke[2] * DT
            funke[1] += funke[3] * DT
            funke[4] -= 1
        self.funken = [funke for funke in self.funken if funke[4] > 0]

    def _zeichne_feuerwerk(self):
        """Das vorige Bild verblasst nur um ein Viertel: so ziehen Raketen und Funken Schweife."""
        np = self.np
        for i in range(64):
            r, g, b = np[i]
            np[i] = (r * 3 >> 2, g * 3 >> 2, b * 3 >> 2)
        for rakete in self.raketen:
            np[int(rakete[1]) * 8 + int(rakete[0])] = FARBE_RAKETE
        for funke in self.funken:
            if 0 <= funke[0] < 8 and 0 <= funke[1] < 8:
                hell = funke[4]
                farbe = funke[5]
                np[int(funke[1]) * 8 + int(funke[0])] = (farbe[0] * hell // FUNKEN_LEBEN,
                                                         farbe[1] * hell // FUNKEN_LEBEN,
                                                         farbe[2] * hell // FUNKEN_LEBEN)

    # -------------------------------------------------------------- Vorspann beim Einschalten

    def _beginne_titel(self):
        """Sechs Akte: Die Kugel fällt ins Bild, ihr Aufprall schickt einen Regenbogenring über das
        Brett, das Brett taumelt einmal im Kreis, der Name läuft durch und die Kugel hüpft von
        Buchstabe zu Buchstabe, sie springt ab und hüpft in die Ecke unten rechts, und von dort baut
        sich die Levelwahl auf."""
        self.zustand = TITEL
        self.akt = 0
        self.zaehler = 0
        mitten = []
        self.laufschrift = self._spalten(SPIELNAME, mitten)
        self.lauf = 0                    # so viele Bilder läuft der Name schon
        # In diesen Bildern steht die Mitte eines Buchstabens genau unter der Kugel: dann landet sie
        self.landungen = [(mitte + 5) * FEIER_TEMPO for mitte in mitten] or [6 * FEIER_TEMPO]
        self.hopser = 0
        self.karte = TITEL_KARTE
        self.kamera_x = self.kamera_y = 0
        self.neig_x = self.neig_y = 0.0
        self.x = 3.5
        self.y = 9.0
        self.vx = self.vy = 0.0
        # Der erste Sprung führt vom Brett (Höhe 3.5) über einen Scheitel bei 7.3 auf die
        # Buchstabenhöhe 5.5 und soll genau dann landen, wenn der erste Buchstabe unter der Kugel
        # ankommt. Daraus ergeben sich Schwerkraft und Absprungtempo.
        self.sprung_g = (4.654 / (self.landungen[0] * DT)) ** 2
        self.sprung_v = (7.6 * self.sprung_g) ** 0.5

    def _naechster_akt(self):
        self.akt += 1
        self.zaehler = 0

    def _titel(self):
        """Bewegt die Kugel durch den Vorspann und schaltet von Akt zu Akt weiter."""
        t = self.zaehler
        akt = self.akt
        if akt == 0:
            # Freier Fall mit Schwerkraft; bei jedem Aufprall bleibt die Hälfte des Tempos
            self.vy -= 60 * DT
            self.y += self.vy * DT
            if self.y < 3.5:
                self.y = 3.5
                if self.vy > -6:
                    self._naechster_akt()
                else:
                    self.vy = -self.vy * 0.5
        elif akt == 1:
            if t >= TITEL_WELLE:
                self._naechster_akt()
        elif akt == 2:
            # Die Kipprichtung dreht sich einmal im Kreis, die Kugel läuft auf der tiefen Seite mit
            staerke = min(1.0, t / 12, (TITEL_KIPPEN - t) / 12)
            winkel = 6.2832 * t / TITEL_KIPPEN
            self.neig_x = staerke * cos(winkel)
            self.neig_y = staerke * sin(winkel)
            self.x = 3.5 + 0.5 * staerke + 2.6 * self.neig_x
            self.y = 3.5 + 0.5 * staerke + 2.6 * self.neig_y
            if t >= TITEL_KIPPEN:
                self.neig_x = self.neig_y = 0.0
                self._naechster_akt()
        elif akt == 3:
            self.lauf = t
            self.x = 3.5
            landungen = self.landungen
            if t < landungen[0]:
                # Anlauf: ein hoher Sprung, bis der erste Buchstabe da ist
                zeit = t * DT
                self.y = 3.5 + self.sprung_v * zeit - self.sprung_g * zeit * zeit / 2
            elif t >= landungen[-1]:
                # Sie steht auf dem letzten Buchstaben: Absprung nach rechts
                self.y = 5.5
                self.vx = 2.5
                self.vy = 9.0
                self._naechster_akt()
            else:
                # Die Kugel hüpft von Buchstabe zu Buchstabe: Sie landet genau dann, wenn die Mitte
                # des nächsten unter ihr steht (breite Buchstaben geben einen längeren Hüpfer)
                nr = self.hopser
                while t >= landungen[nr + 1]:
                    nr += 1
                self.hopser = nr
                von = landungen[nr]
                self.y = 5.5 + 2.0 * sin(3.1416 * (t - von) / (landungen[nr + 1] - von))
        elif akt == 4:
            # Wurf mit Schwerkraft auf den Boden; jeder Aufprall halbiert das Tempo, bis die Kugel
            # in der Ecke unten rechts liegt. Der Name läuft währenddessen aus dem Bild.
            self.lauf += 1
            self.vy -= 40 * DT
            self.x = min(self.x + self.vx * DT, 7.5)
            self.y += self.vy * DT
            if self.y < 0.5:
                self.y = 0.5
                self.vy = -self.vy * 0.5 if self.vy < -3 else 0.0
                if self.vy == 0.0 and self.x == 7.5:
                    self._naechster_akt()
        elif t >= len(LEVELS) + 15:
            # Die Marke springt zum ersten Level, das noch nicht geschafft ist
            self._oeffne_menue(self._erstes_offenes())

    def _zeichne_titel(self):
        """Zeichnet das Bild zum aktuellen Akt des Vorspanns."""
        np = self.np
        akt = self.akt
        t = self.zaehler
        if akt == 0:
            # Das vorige Bild verblasst nur zur Hälfte: so zieht die Kugel einen Schweif
            for i in range(64):
                r, g, b = np[i]
                np[i] = (r >> 1, g >> 1, b >> 1)
            self._zeichne_kugel(16)
        elif akt == 1:
            # Abstände im Quadrat und in halben Pixeln, damit der Ring ohne Wurzel auskommt
            radius = t // 2 + 1
            aussen = radius * radius
            innen = (radius - 2) * (radius - 2) if radius > 2 else -1
            boden = VERLAUF[0][VERLAUF_RAND + 7]      # die Farbe des geraden Bretts
            i = 0
            for sy in range(8):
                for sx in range(8):
                    abstand = 4 * ((sx - 3) * (sx - 3) + (sy - 3) * (sy - 3))
                    if abstand <= innen:
                        np[i] = boden
                    elif abstand <= aussen:
                        np[i] = REGENBOGEN_PAL[(abstand + t * 3) & 31]
                    else:
                        np[i] = SCHWARZ
                    i += 1
            self._zeichne_kugel(16)
        elif akt == 2:
            self._zeichne_brett()
            self._zeichne_kugel(16)
        elif akt < 5:
            schrift = self.laufschrift
            laenge = len(schrift)
            links = self.lauf // FEIER_TEMPO - 8
            farbe = self.lauf >> 1
            i = 0
            for sy in range(8):
                reihe = 1 << (4 - sy) if sy < 5 else 0      # der Name steht in den unteren fünf Zeilen
                for sx in range(8):
                    spalte = links + sx
                    if reihe and 0 <= spalte < laenge and schrift[spalte] & reihe:
                        np[i] = REGENBOGEN_PAL[(spalte * 2 + farbe) & 31]
                    else:
                        np[i] = SCHWARZ
                    i += 1
            self._zeichne_kugel(16)
        else:
            # Die Levelwahl baut sich vom letzten Level (unten rechts, wo die Kugel liegt) zum
            # ersten auf. Ein weisser Funke läuft voraus und bleibt zum Schluss auf Level 1 stehen.
            anzahl = len(LEVELS)
            geloest = self.geloest
            neuestes = max(anzahl - 1 - t, 0)
            for i in range(64):
                nr = (7 - i // 8) * 8 + i % 8
                if nr >= anzahl or nr < neuestes:
                    np[i] = SCHWARZ
                elif nr <= neuestes + 1 and (nr == 0 or t < anzahl):
                    np[i] = FARBE_KUGEL
                else:
                    np[i] = MENUE_PAL[nr // REGION % len(MENUE_PAL)][geloest >> nr & 1]


def main():
    """Liest in jedem Bild Joystick und Schalter, rechnet das Spiel weiter und zeichnet es."""
    np = NeoPixel(Pin(PIN_LEDS, Pin.OUT), 64)
    rechts = Pin(PIN_RECHTS, Pin.IN, Pin.PULL_UP)
    links = Pin(PIN_LINKS, Pin.IN, Pin.PULL_UP)
    hoch = Pin(PIN_HOCH, Pin.IN, Pin.PULL_UP)
    runter = Pin(PIN_RUNTER, Pin.IN, Pin.PULL_UP)
    mitte = Pin(PIN_MITTE, Pin.IN, Pin.PULL_UP)
    schalter = Pin(PIN_SCHALTER, Pin.IN, Pin.PULL_UP)

    try:
        spiel = Spiel(np)
        naechstes_bild = ticks_ms()
        while True:
            # Der Joystick schaltet gegen Masse: gedrückt = 0
            spiel.schritt(not rechts.value(), not links.value(), not hoch.value(),
                          not runter.value(), not mitte.value(), schalter.value() == 1)
            spiel.zeichne()

            # Festes Zeitraster, damit die Kugel immer gleich schnell rollt
            naechstes_bild = ticks_add(naechstes_bild, BILD_MS)
            warten = ticks_diff(naechstes_bild, ticks_ms())
            if warten > 0:
                sleep_ms(warten)
            else:
                naechstes_bild = ticks_ms()
    finally:
        # Wird das Programm gestoppt oder bricht es mit einem Fehler ab, gehen die LEDs aus
        np.fill(SCHWARZ)
        np.write()


# ====================================================================== 3. Levels
#
# Jedes Level hat einen Namen, eine Wandfarbe und die Karte als Text. Die oberste Zeile der Karte
# ist oben auf der Matrix.
#   #  Wand           .  Boden          O  Loch (auch ein Leerzeichen ist ein Loch)
#   S  Start          Z  Ziel           C  Checkpoint
#   A  Brücke, trägt bei Schalter 1     B  Brücke, trägt bei Schalter 0
#   ~  Eis: die Kugel rollt kaum aus    :  Sand: die Kugel bleibt fast stecken
#   > < ^ v  Förderband, schiebt die Kugel in Pfeilrichtung
#   =  Schaltband: schiebt bei Schalter 1 nach rechts, bei 0 nach links
#   !  Schaltband: schiebt bei Schalter 1 nach oben, bei 0 nach unten
# Ein Level darf grösser als 8x8 sein, die Matrix zeigt dann einen Ausschnitt um die Kugel.
# Je acht Levels bilden eine Region. Sind alle acht geschafft, in welcher Reihenfolge auch immer,
# läuft "AREA CLEARED" durch den Regenbogen.
#
# Die Schwierigkeit steigt von Region zu Region. Für die Brücken gilt: Regionen 1 und 2 haben
# keine, in 3 und 4 stehen sie einzeln, in 5 und 6 höchstens zwei hintereinander (Umlegen im
# Rollen), in 7 und 8 bis zu vier.

# Wandfarben
BLAU = (0, 12, 45)
TUERKIS = (0, 28, 22)
VIOLETT = (22, 0, 40)

LEVELS = (
    # ------------------------------------------------ Region 1 (1-8): das klassische Kugellabyrinth
    ("Anrollen", BLAU, """
########
#S.....#
#......#
#..OO..#
#..OO..#
#......#
#.....Z#
########"""),
    ("Zielen", TUERKIS, """
########
#S.....#
#.O..O.#
#......#
#..OZ..#
#......#
#.O..O.#
########"""),
    ("Bremsen", VIOLETT, """
########
#S....O#
####...#
#O.....#
#...####
#......#
#OOOO.Z#
########"""),
    ("Türen", BLAU, """
########
#S.....#
####.O##
#......#
##O.####
#......#
#.....Z#
########"""),
    ("Kurven", TUERKIS, """
########
#S...O.#
####.#.#
#....#.#
#.####.#
#......#
#O####Z#
########"""),
    ("Löcherfeld", VIOLETT, """
########
#S...O.#
#.OO...#
#....O.#
#.O.O..#
#...O.O#
#O.O..Z#
########"""),
    ("Zickzack", BLAU, """
########
#S.....#
#OOOO.O#
#......#
#O.OOOO#
#......#
#OOOO.Z#
########"""),
    ("Kranz", TUERKIS, """
########
#S.....#
#.OOOO.#
#.O..O.#
#.OZ.O.#
#.O.OO.#
#......#
########"""),

    # ------------------------------------------------ Region 2 (9-16): grosse klassische Bretter
    ("Slalom", VIOLETT, """
########
#..Z...#
#O....O#
#OO.OOO#
#......#
#.O....#
#OOOO.O#
#......#
#...O..#
#O.OOOO#
#......#
#..O...#
#OOO.OO#
#......#
#...S..#
########"""),
    ("Kammweg", BLAU, """
############
#S.#..C..#Z#
#..#O.#..#.#
#.O#..#.O#.#
#..#..#..#.#
#..#.O#..#.#
#O.#..#O.#.#
#..#..#..#.#
#.O#O.#..#.#
#..#..#.O#.#
#..C..#..C.#
############"""),
    ("Sieb", TUERKIS, """
############
#S..O......#
#.O...O.OO.#
#...O.O....#
#OO.O...O.O#
#....O.O...#
#.O.O..O.O.#
#.O...O....#
#...O.O..OO#
#O.O...O...#
#....O...OZ#
############"""),
    ("Burggraben", VIOLETT, """
############
#S.........#
#......O...#
#..OOOOOO..#
#..O....O..#
#O.O.Z..O..#
#..O....O.O#
#..O....O..#
#..OOO.OO..#
#...O......#
#..........#
############"""),
    ("Grat", BLAU, """
  ...
  .S.....
  ...   .
        .
   C.....
   ..
   .
   .     ...
   .......Z.
         ..."""),
    ("Löcherteppich", TUERKIS, """
############
#S.........#
#.O.O.O.O.O#
#.....O....#
#.O.O.O.O.O#
#...O......#
#.O.O.O.O.O#
#.......O..#
#.O.O.O.O.O#
#..O......Z#
#.O.O.O.O.O#
############"""),
    ("Treppe", BLAU, """
S..
 ...
  ...
   ...
    .C.
     ...
      ...
       ...
        ...
         ..Z"""),
    ("Hindernislauf", VIOLETT, """
########
#..Z...#
#.OOOO.#
#......#
#OOO.OO#
#......#
#..C...#
###.####
#......#
#.O..O.#
#O..O..#
#......#
####.###
#......#
#..C...#
#OOOO.O#
#......#
#..O.O.#
#O.OOOO#
#......#
#...S..#
########"""),

    # ------------------------------------------------ Region 3 (17-24): einzelne Brücken
    ("Erste Brücke", TUERKIS, """
########
#..Z...#
#OOBOOO#
#......#
#OOOAOO#
#......#
#...S..#
########"""),
    ("Wahl", VIOLETT, """
########
#Z..#..#
#...#..#
#OAOOOB#
#......#
#OBOOAO#
#......#
#...S..#
########"""),
    ("Vier Brücken", TUERKIS, """
########
#..Z...#
#......#
#OOAOOO#
#......#
#OOOOBO#
#......#
#OAOOOO#
#......#
#OOOBOO#
#......#
#..S...#
########"""),
    ("Kammern", VIOLETT, """
###########
#S...O....#
#....A....#
#.O..O..O.#
#....O....#
#OBOOOOOBO#
#....O....#
#..O.O.O..#
#....A....#
#....O...Z#
###########"""),
    ("Falltüren", TUERKIS, """
########
#S.A..O#
#.##B#.#
#.#..#.#
#.#.##.#
#B#.##A#
#.A...Z#
########"""),
    ("Trittsteine", VIOLETT, """
########
#ZB..A.#
######.#
#.A..B.#
#.######
#.B..A.#
######.#
#S.A...#
########"""),
    ("Doppelgraben", TUERKIS, """
############
#S.........#
#.OOOAOOOO.#
#.O......O.#
#.O.OOOO.O.#
#.O.OZ.O.O.#
#.O.O..O.O.#
#.O.OOBO.O.#
#.O......O.#
#.OOOOOOOO.#
#..........#
############"""),
    ("Schaltturm", VIOLETT, """
########
#..Z...#
#OOOAOO#
#......#
#..O.O.#
#OBOOOO#
#......#
#..C...#
#OOOO.O#
#......#
#OAOOBO#
#......#
#.O..O.#
#OOO.OO#
#......#
#...S..#
########"""),

    # ------------------------------------------------ Region 4 (25-32): Eis und Sand
    ("Glatteis", VIOLETT, """
########
#S~~~~.#
#~~~~~~#
#~~OO~~#
#::::::#
#OOOOAO#
#.....Z#
########"""),
    ("Sandbremse", TUERKIS, """
########
#S~~~:O#
####..##
#O:~~~.#
##B#####
#.~~~~:#
#OOOO.Z#
########"""),
    ("Eisbahn", VIOLETT, """
########
#Z~~~~:#
#OOOOOB#
#:~~~~:#
#AOOOOO#
#:~~~~:#
#OOOOO~#
#S~~~~:#
########"""),
    ("Rutschpartie", TUERKIS, """
########
#..Z...#
#~~~~~~#
#OO~OOO#
#~~~~~~#
#::::::#
#OOOOAO#
#~~~~~~#
#::::::#
#O~OOOO#
#~~~~~~#
#...S..#
########"""),
    ("Sandkasten", VIOLETT, """
########
#S:::.O#
#OOOOBO#
#O.:::.#
#OAOOOO#
#..:::.#
#OOOO.Z#
########"""),
    ("Eisbrücke", BLAU, """
:::    :::
:S:~A~~:C:
:::    :::
        ~
        B
        ~
:::    :::
:Z:~~~~:C:
:::    :::"""),
    ("Eiskunstlauf", TUERKIS, """
##########
#S~~~~~~~#
#~~O~~~O~#
#~~~~:~~~#
#~O~~~~~~#
#~~~~O~~:#
#~~:~~~~O#
#O~~~~~~A#
#~~~~O~OZ#
##########"""),
    ("Eispalast", VIOLETT, """
##########
#Z~~~~~~~#
#O~~~~:~~#
#~~~~~~~O#
#~:~~O~~~#
#~~~~~~:~#
#OOOOOOBO#
#~~~~~C:~#
#~O~~~~~~#
#~~~:~~O~#
#~~~~~~~~#
#O~~~:~~~#
#S~~~~~O~#
##########"""),

    # ------------------------------------------------ Region 5 (33-40): zwei Brücken hintereinander
    ("Doppelschritt", TUERKIS, """
########
#..Z...#
#......#
#OOOBOO#
#OOOAOO#
#......#
#...S..#
########"""),
    ("Brückenschlag", VIOLETT, """
########
#..Z...#
#......#
#OOBOOO#
#OOAOOO#
#......#
#OOOOBO#
#......#
#OAOOOO#
#......#
#OOOBOO#
#......#
#..S...#
########"""),
    ("Quergang", TUERKIS, """
########
#S.....#
#OOOOAO#
#OOOOBO#
#......#
######.#
#Z.AB..#
########"""),
    ("Treibsand", VIOLETT, """
########
#..Z...#
#OOBOOO#
#OOAOOO#
#::::::#
#~~~~~~#
#OOOOBO#
#OOOOAO#
#~~~~~~#
#~~~~~~#
#...S..#
########"""),
    ("Löcherdoppel", TUERKIS, """
########
#..Z...#
#OOBOOO#
#OOAOOO#
#......#
#..C...#
#OOOO.O#
#......#
#O.OOOO#
#......#
#OOOBOO#
#OOOAOO#
#......#
#...S..#
########"""),
    ("Eisdoppel", VIOLETT, """
########
#..Z...#
#::::::#
#OOOBOO#
#OOOAOO#
#~~~~~~#
#OOO~OO#
#~~~~~~#
#::::::#
#...S..#
########"""),
    ("Doppelinsel", BLAU, """
...AB...
.S.  .C.
...  ...
      B
      A
...  ...
.Z.BA...
...  ..."""),
    ("Doppelturm", TUERKIS, """
########
#..Z...#
#OOAOOO#
#OOBOOO#
#::::::#
#~~~~~~#
#OOOO~O#
#~~~~~~#
#..C...#
#OBOOOO#
#OAOOOO#
#......#
#.O..O.#
#OOO.OO#
#......#
#...S..#
########"""),

    # ------------------------------------------------ Region 6 (41-48): Förderbänder und Schaltbänder
    ("Rolltreppe", BLAU, """
########
#S>>>>.#
######.#
#.<<<<.#
#.######
#.>>>>.#
######Z#
########"""),
    ("Achterbahn", TUERKIS, """
########
#S>>>>v#
######v#
#v<<<<<#
#v######
#>>>>>v#
######v#
#Z:::<<#
########"""),
    ("Flussquerung", BLAU, """
########
#..Z...#
#......#
#>>>>>O#
#......#
#>>>>>>#
#......#
#O<<<<<#
#......#
#...S..#
########"""),
    ("Schleuse", TUERKIS, """
########
#..Z...#
#......#
#O.OOOO#
#^^^^^^#
#^^^^^^#
#......#
#OOOO.O#
#^^^^^^#
#^^^^^^#
#......#
#..S...#
########"""),
    ("Umschalter", TUERKIS, """
########
#S.....#
#......#
###.####
#O====.#
######.#
#Z====.#
########"""),
    ("Stellwerk", VIOLETT, """
########
#S.....#
#......#
#O====.#
#.====O#
#O====.#
#Z====O#
########"""),
    ("Wechselstrom", VIOLETT, """
########
#S.....#
#......#
#.######
#.===B.#
######.#
#ZA===.#
########"""),
    ("Fabrik", TUERKIS, """
##########
#Z.:<<<<<#
#OOOOOOO^#
#.......^#
#OOOAOOOO#
#OOOBOOOO#
#~~~~~~~~#
#~O~~~O~~#
#~~~C~~~~#
#>>>>>>>O#
#........#
#S.......#
##########"""),

    # ------------------------------------------------ Region 7 (49-56): Ketten aus drei und vier Brücken
    ("Dreisprung", TUERKIS, """
########
#..Z...#
#......#
#OOOAOO#
#OOOBOO#
#OOOAOO#
#......#
#...S..#
########"""),
    ("Zebrasteg", VIOLETT, """
########
#..Z...#
#......#
#OOOAOO#
#OOOBOO#
#OOOAOO#
#OOOBOO#
#...C..#
#OBOOOO#
#OAOOOO#
#......#
#...S..#
########"""),
    ("Schachbrett", TUERKIS, """
########
#S.....#
#......#
#OABABO#
#OBABAO#
#OABABO#
#OBABAO#
#......#
#.....Z#
########"""),
    ("Eiszebra", VIOLETT, """
########
#..Z...#
#::::::#
#OOOBOO#
#OOOAOO#
#OOOBOO#
#OOOAOO#
#~~~~~~#
#~~~~~~#
#...S..#
########"""),
    ("Doppelschalter", TUERKIS, """
########
#..Z...#
#OOAOOO#
#OOBOOO#
#OO!OOO#
#OO!OOO#
#......#
#..S...#
########"""),
    ("Rückstrom", VIOLETT, """
########
#..Z...#
#OOOO.O#
#O====O#
#......#
#O====O#
#......#
#..S...#
########"""),
    ("Schaltzentrale", TUERKIS, """
########
#..Z...#
#......#
#OOBOOO#
#OO!OOO#
#..C...#
#......#
#OOOO.O#
#O====O#
#..C...#
#......#
#OOOAOO#
#OOOBOO#
#......#
#...S..#
########"""),
    ("Kraftwerk", TUERKIS, """
########
#..Z...#
#::::::#
#OOOBOO#
#OOOAOO#
#OOOBOO#
#~~~~~~#
#..C...#
#O====.#
#.====O#
#O====.#
#......#
#..C...#
#>>>>>O#
#......#
#S.....#
########"""),

    # ------------------------------------------------ Region 8 (57-64): Meisterklasse
    ("Wildwasser", TUERKIS, """
########
#..Z...#
#OOO.OO#
#<<<<<<#
#>>>>>O#
#......#
#..C...#
#O<<<<<#
#O<<#<<#
#......#
#OO.OOO#
#>>>>>>#
#O<<<<<#
#......#
#...S..#
########"""),
    ("Strudelfeld", TUERKIS, """
############
#S.........#
#.>v<...>v<#
#.>O<...>O<#
#.>^<...>^<#
#....>v<...#
#....>O<...#
#....>^<...#
#>v<....>v<#
#>O<....>O<#
#>^<......Z#
############"""),
    ("Schaltwerk", VIOLETT, """
########
#..Z...#
#O.OOOO#
#O====O#
#......#
#..C...#
#OOOO.O#
#O====O#
#......#
#..C...#
#OO.OOO#
#O====O#
#......#
#...S..#
########"""),
    ("Eiswüste", VIOLETT, """
############
#S~~~~~O~~~#
#~~O~~~~~O~#
#~~~~:~~~~~#
#O~~~~~O~~~#
#~~~O~~~~:~#
#~:~~~~O~~~#
#~~~~O~~~~O#
#~O~~~~~:~~#
#~~~~~O~~~~#
#~~~O~~~~OZ#
############"""),
    ("Gletscher", TUERKIS, """
########
#..Z...#
#::::::#
#~O~~O~#
#~~~~~~#
#^^^^^^#
#......#
#..C...#
#OOOAOO#
#OOOBOO#
#~~~~~~#
#~~~~~~#
#OO.OOO#
#......#
#...S..#
########"""),
    ("Labor", TUERKIS, """
############
#S....#~~~~#
#..O..#~O~~#
#.....~~~~O#
#.O...#~~O~#
#.....#~~~~#
#######!####
#......C...#
#OOOABABOOO#
#OOOBABAOOO#
#Z.........#
############"""),
    ("Marathon", TUERKIS, """
########
#..Z...#
#::::::#
#OOBOOO#
#OO!OOO#
#......#
#..C...#
#OOOAOO#
#OOOBOO#
#OOOAOO#
#~~~~~~#
#OOO~OO#
#~~~~~~#
#::::::#
#..C...#
#O<<<<<#
#>>>>>O#
#......#
#..C...#
#OOOO.O#
#......#
#..O..O#
#O.OOOO#
#......#
#...S..#
########"""),
    ("Gipfel", TUERKIS, """
########
#Z:<<<<#
######^#
#>>>>>^#
#^######
#^.....#
#OOOOBO#
#OOOOAO#
#OOOOBO#
#OOOOAO#
#......#
#..C...#
#O.OOOO#
#O====O#
#......#
#..C...#
#OOO.OO#
#^^^^^^#
#^^^^^^#
#......#
#::::::#
#~~O~~~#
#~~~~O~#
#O~~~~~#
#..C...#
#O<<<<<#
#>>>>>O#
#......#
#OO.OOO#
#......#
#...S..#
########"""),
)


if __name__ == "__main__":
    main()


