# ============================================================================
#                         P C B   R O U T I N G
#                    Ein Lumatrix-Spiel von Sven Forrer
# ============================================================================
# Autor       : Sven Forrer
# Version     : 1.0.0
# Stand       : 22.10.2026
# Plattform   : Raspberry Pi Pico / MicroPython
# Anzeige     : 8 x 8 WS2812B, GPIO 19, LED 0 unten links
# Eingabe     : Digitaler Joystick, aktive LOW-Taster mit Pull-ups
# Grundlage   : Lumatrix-Vorlagen.zip / Tutorial/10_JoystickNavigation.py
#
# Spiel       : Sechs Platinen, gleichfarbige Pins ohne Kreuzungen verbinden.
# Funktionen  : Levelauswahl, Sackgassenpruefung, Zeitmessung, Ergebnisgesichter.
# Bedienung   : Links/rechts waehlen, kurz druecken starten oder Bahn bearbeiten.
#              Im Level lange druecken: zurueck zur Levelauswahl.
# Start       : Diese Datei als main.py auf dem Pico speichern.
#
# ============================================================================

__author__ = "Sven Forrer"
__version__ = "1.0.0"

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms, ticks_ms, ticks_diff

# Hier Tempo, Helligkeit und Farben einstellen.
START_POS = 3 * 8 + 3       # Eines der vier mittleren Felder: x=3, y=3
ZUG_MS = 230
PAUSE_MS = 12
ENTPRELL_MS = 25
NEUSTART_MS = 1200
PRUEF_SCHRITTE = 6            # Sucharbeit pro Schleifendurchgang
CURSOR_SICHTBAR_MS = 500       # Nach jedem Schritt sofort sichtbar
CURSOR_PULS_MS = 2000         # Zwei Sekunden fuer sanftes Ab- und Aufblenden
ERGEBNIS_MS = 3000
ERGEBNIS_PAUSE_MS = 500       # Platine vor Pass/Fail noch kurz zeigen
ZEIT_SCROLL_MS = 100         # Tempo der Zeit-Laufschrift (Minuten:Sekunden)
LINIE_NACHLEUCHTEN_MS = 1000  # Fertige Linie weich auf Ruhehelligkeit dimmen
LINIE_WIEDERHOLUNGEN = 3
BLINK_MS = 300
ERGEBNIS_HELLIGKEIT = 40
HELLIGKEIT = 100              # Prozent der bereits gedaempften Farben
FARBEN = ((3, 8, 48), (36, 36, 0), (42, 24, 0),
          (30, 0, 45), (0, 42, 8))
CURSOR = (35, 35, 35)
WAND = (4, 5, 8)
HINTERGRUND = (0, 1, 1)
FEHLER = (ERGEBNIS_HELLIGKEIT, 0, 0)
ERFOLG = (0, ERGEBNIS_HELLIGKEIT, 0)
AUS = (0, 0, 0)
GESICHT_PASS = ("00111100", "01000010", "10100101", "10000001",
                "10100101", "10011001", "01000010", "00111100")
GESICHT_FAIL = ("00111100", "01000010", "10100101", "10000001",
                "10011001", "10100101", "01000010", "00111100")

# Kleine Bitfelder halten die Suche speichersparend (ein Bit pro LED).
ALLE = (1 << 64) - 1
BITS = tuple(1 << pos for pos in range(64))


def erreichbar(start, ziel, belegt):
    frei = (ALLE & ~belegt) | BITS[start] | BITS[ziel]
    rand = gesehen = BITS[start]
    while rand:
        if rand & BITS[ziel]:
            return True
        rand = ((rand << 8) | (rand >> 8) |
                ((rand & 0x7f7f7f7f7f7f7f7f) << 1) |
                ((rand & 0xfefefefefefefefe) >> 1)) & frei & ~gesehen
        gesehen |= rand
    return False


def rest_suchen(paare, belegt):
    # Erst stoppen, wenn kein einziges offenes Paar mehr erreichbar ist.
    if not paare:
        return True
    for start, ziel in paare:
        yield None
        if erreichbar(start, ziel, belegt):
            return True
    return False


# Gleiche Pins und LED-Anordnung, mit Pull-ups und entprellten Tastern.
np = NeoPixel(Pin(19, Pin.OUT), 64)
rechts = Pin(2, Pin.IN, Pin.PULL_UP)
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
hineindruecken = Pin(8, Pin.IN, Pin.PULL_UP)

# Karten von oben nach unten; LED 0 ist unten links.
# A bis E: je zwei Pins derselben Farbe. # = Sperrfeld, . = frei.
LEVEL = (
    ('Loetkurs', (
        '........', '........', '.B..#.B.', '....#...',
        '..####..', '........', '.A.#..A.', '...#....')),
    ('Umweg', (
        '........', '.B....A.', '..C.....', '..##C.#.',
        '.####...', '........', '.A.#..B.', '........')),
    ('Engstelle', (
        '...#....', '.B.#.B..', '........', '.C.##.A.',
        '.#C###..', '.#......', '.A.#....', '...#....')),
    ('Flechtwerk', (
        'B......A', '.C....#.', '....D.#.', '.#.##...',
        '.#.##...', '.#D##C..', '......B.', 'A.......')),
    ('Datenbus', (
        '........', 'B....C.A', '.D.##E..', '...##...',
        '#..##...', '.D.E....', 'AC.##.B.', '........')),
    ('Meisterplatine', (
        'B.##...A', '.C....#.', '....D...', '..##E.#.',
        '..##..#.', '.DE..C#.', '......B.', 'A.......')),
)
ZAHLEN = (
    ("010", "110", "010", "010", "111"),
    ("110", "001", "010", "100", "111"),
    ("110", "001", "010", "001", "110"),
    ("101", "101", "111", "001", "001"),
    ("111", "100", "110", "001", "110"),
    ("011", "100", "110", "101", "010"),
)


def pixel(pos, farbe):
    faktor = max(10, min(100, HELLIGKEIT))
    np[pos] = tuple(max(0, min(60, int(v))) * faktor // 100 for v in farbe)


def leeren():
    for pos in range(64):
        np[pos] = AUS


class Taste:
    def __init__(self, pin):
        self.pin = pin
        self.roh = self.wert = 1
        self.seit = ticks_ms()

    def lesen(self, jetzt):
        roh = self.pin.value()
        if roh != self.roh:
            self.roh = roh
            self.seit = jetzt
        if ticks_diff(jetzt, self.seit) >= ENTPRELL_MS:
            self.wert = self.roh
        return self.wert == 0


class Spiel:
    def __init__(self, nummer=0):
        self.laden(nummer)

    def laden(self, nummer):
        self.nummer = nummer
        self.waende = set()
        paare = {}
        for zeile, text in enumerate(LEVEL[nummer][1]):
            for x, wert in enumerate(text):
                pos = (7 - zeile) * 8 + x
                if wert == "#":
                    self.waende.add(pos)
                elif wert in "ABCDE":
                    if wert not in paare:
                        paare[wert] = []
                    paare[wert].append(pos)
        self.pins = [paare[farbe] for farbe in sorted(paare)]
        self.pin_farben = {}
        for farbe, paar in enumerate(self.pins):
            for pos in paar:
                self.pin_farben[pos] = farbe
        self.pfade = [[] for paar in self.pins]
        self.fertig = [False for paar in self.pins]
        self.fertig_seit = [None for paar in self.pins]
        self.aktiv = None
        self.cursor = START_POS
        self.cursor_seit = ticks_ms()
        self.fehler = 0
        self.zuege = 0
        self.fehler_pos = self.cursor
        self.start_ms = None
        self.dauer_ms = None

    def zeit_starten(self, jetzt):
        if self.start_ms is None:
            self.start_ms = jetzt

    def besitzer(self, pos):
        if pos in self.pin_farben:
            return self.pin_farben[pos]
        for farbe, pfad in enumerate(self.pfade):
            if pos in pfad:
                return farbe
        return None

    def loesbar_pruefen(self):
        # Fertige Bahnen bleiben fest. Ein einziges noch verbindbares
        # Paar reicht aus, um ohne Fehlermeldung weiterzuspielen.
        belegt = 0
        for pos in self.waende:
            belegt |= BITS[pos]
        for pos in self.pin_farben:
            belegt |= BITS[pos]
        paare = []
        for farbe, paar in enumerate(self.pins):
            if self.fertig[farbe]:
                for pos in self.pfade[farbe]:
                    belegt |= BITS[pos]
            else:
                paare.append(tuple(paar))
        ergebnis = yield from rest_suchen(paare, belegt)
        yield ergebnis

    def klicken(self):
        self.zeit_starten(ticks_ms())
        self.cursor_seit = ticks_ms()
        if self.aktiv is not None:
            self.pfade[self.aktiv] = []
            self.aktiv = None
            return "cancel"
        farbe = self.besitzer(self.cursor)
        if farbe is None:
            return "none"
        self.pfade[farbe] = []
        self.fertig[farbe] = False
        self.fertig_seit[farbe] = None
        if self.cursor in self.pins[farbe]:
            self.aktiv = farbe
            self.pfade[farbe] = [self.cursor]
            return "start"
        return "erase"

    def bewegen(self, richtung):
        dx, dy = richtung
        x, y = self.cursor % 8 + dx, self.cursor // 8 + dy
        neu = y * 8 + x if 0 <= x < 8 and 0 <= y < 8 else None
        if self.aktiv is None:
            if neu is not None:
                if neu != self.cursor:
                    self.zeit_starten(ticks_ms())
                    self.cursor_seit = ticks_ms()
                self.cursor = neu
            return "move"
        pfad = self.pfade[self.aktiv]
        if len(pfad) > 1 and neu == pfad[-2]:
            pfad.pop()
            self.cursor = neu
            self.zeit_starten(ticks_ms())
            self.cursor_seit = ticks_ms()
            self.zuege += 1
            return "undo"
        besitzer = self.besitzer(neu) if neu is not None else None
        if (neu is None or neu in self.waende or neu in pfad or
                (besitzer is not None and besitzer != self.aktiv)):
            self.fehler += 1
            self.fehler_pos = self.cursor if neu is None else neu
            return "block"
        pfad.append(neu)
        self.cursor = neu
        self.zeit_starten(ticks_ms())
        self.cursor_seit = ticks_ms()
        self.zuege += 1
        if neu in self.pins[self.aktiv]:
            self.fertig[self.aktiv] = True
            self.fertig_seit[self.aktiv] = ticks_ms()
            self.aktiv = None
            if all(self.fertig):
                self.dauer_ms = ticks_diff(ticks_ms(), self.start_ms)
                return "win"
            return "connected"
        return "move"


def zeichnen(spiel, jetzt, cursor=True, fehler_seit=None):
    for pos in range(64):
        pixel(pos, HINTERGRUND)
    for pos in spiel.waende:
        pixel(pos, WAND)
    for farbe, pfad in enumerate(spiel.pfade):
        licht = FARBEN[farbe]
        basis = licht if farbe == spiel.aktiv else tuple(v // 3 for v in licht)
        if spiel.fertig[farbe] and spiel.fertig_seit[farbe] is not None:
            # Dreimal weich nachleuchten, danach dauerhaft ruhig bleiben.
            alter = max(0, ticks_diff(jetzt, spiel.fertig_seit[farbe]))
            dauer = max(1, LINIE_NACHLEUCHTEN_MS)
            if alter < dauer * LINIE_WIEDERHOLUNGEN:
                runde, phase = alter // dauer, alter % dauer
                # Erster Impuls beginnt hell; weitere blenden sanft ein/aus.
                t = (phase * 1000 // dauer if runde == 0 else
                     abs(2 * phase - dauer) * 1000 // dauer)
                weich = t * t * (3000 - 2 * t) // 1000000
                basis = tuple(v - (v - v // 3) * weich // 1000 for v in licht)
        for pos in pfad:
            pixel(pos, basis)
    for pos, farbe in spiel.pin_farben.items():
        pixel(pos, FARBEN[farbe])
    alter = ticks_diff(jetzt, spiel.cursor_seit)
    if cursor:
        # Sanfte Kurve; der Cursor verschwindet nie ganz.
        anteil = 1000
        if alter >= CURSOR_SICHTBAR_MS:
            phase = (alter - CURSOR_SICHTBAR_MS) % CURSOR_PULS_MS
            t = abs(2 * phase - CURSOR_PULS_MS) * 1000 // CURSOR_PULS_MS
            weich = t * t * (3000 - 2 * t) // 1000000
            anteil = 250 + weich * 750 // 1000
        basis = np[spiel.cursor]
        pixel(spiel.cursor, CURSOR)
        weiss = np[spiel.cursor]
        np[spiel.cursor] = tuple((b * (1000 - anteil) + w * anteil) // 1000
                                 for b, w in zip(basis, weiss))
    if fehler_seit is not None and ticks_diff(jetzt, fehler_seit) < 180:
        pixel(spiel.fehler_pos, FEHLER)
    np.write()


def level_zeigen(spiel, warten=True):
    leeren()
    for zeile, text in enumerate(ZAHLEN[spiel.nummer]):
        for x, wert in enumerate(text):
            if wert == "1":
                pixel((6 - zeile) * 8 + x + 2, CURSOR)
    for x in range(len(spiel.pins)):
        pixel(x + 1, FARBEN[x])
    np.write()
    if warten:
        sleep_ms(850)


def ergebnis_blinken(gewonnen):
    # Sofort starten; Rot und Gruen haben identische Dauer und Helligkeit.
    farbe = ERFOLG if gewonnen else FEHLER
    gesicht = GESICHT_PASS if gewonnen else GESICHT_FAIL
    for phase in range((ERGEBNIS_MS + BLINK_MS - 1) // BLINK_MS):
        leeren()
        if phase % 2 == 0:
            for zeile, text in enumerate(gesicht):
                for x, wert in enumerate(text):
                    if wert == "1":
                        pixel((7 - zeile) * 8 + x, farbe)
        np.write()
        sleep_ms(min(BLINK_MS, ERGEBNIS_MS - phase * BLINK_MS))


def pruefen(spiel):
    zeichnen(spiel, ticks_ms(), False)
    sleep_ms(ERGEBNIS_PAUSE_MS)
    ergebnis_blinken(True)


def rot_neustarten(spiel):
    zeichnen(spiel, ticks_ms(), False)
    sleep_ms(ERGEBNIS_PAUSE_MS)
    ergebnis_blinken(False)
    nummer = spiel.nummer
    spiel.laden(nummer)
    level_zeigen(spiel)


def ok_zeigen():
    leeren()
    for zeile, text in enumerate(("01100101", "10010110", "10010100",
                                  "10010110", "01100101")):
        for x, wert in enumerate(text):
            if wert == "1":
                pixel((6 - zeile) * 8 + x, ERFOLG)
    np.write()


def zeit_text(dauer_ms):
    sekunden = max(0, dauer_ms) // 1000
    return "%d:%02d" % (sekunden // 60, sekunden % 60)


def zeit_anzeigen(dauer_ms):
    # Kompakte 3x5-Ziffern als Laufschrift, zum Beispiel 1:07.
    schrift = {
        "0": ("111", "101", "101", "101", "111"),
        "1": ("010", "110", "010", "010", "111"),
        "2": ("111", "001", "111", "100", "111"),
        "3": ("111", "001", "111", "001", "111"),
        "4": ("101", "101", "111", "001", "001"),
        "5": ("111", "100", "111", "001", "111"),
        "6": ("111", "100", "111", "101", "111"),
        "7": ("111", "001", "010", "010", "010"),
        "8": ("111", "101", "111", "101", "111"),
        "9": ("111", "101", "111", "001", "111"),
        ":": ("0", "1", "0", "1", "0"),
    }
    spalten = []
    for zeichen in zeit_text(dauer_ms):
        bild = schrift[zeichen]
        for x in range(len(bild[0])):
            spalten.append(sum((1 << y) for y in range(5) if bild[y][x] == "1"))
        spalten.append(0)
    for offset in range(-8, len(spalten) + 1):
        leeren()
        for x in range(8):
            quelle = offset + x
            if 0 <= quelle < len(spalten):
                for y in range(5):
                    if spalten[quelle] & (1 << y):
                        pixel((6 - y) * 8 + x, CURSOR)
        np.write()
        sleep_ms(ZEIT_SCROLL_MS)


def main():
    tasten = [Taste(pin) for pin in (rechts, hoch, runter, links)]
    mitte = Taste(hineindruecken)
    richtungen = ((1, 0), (0, 1), (0, -1), (-1, 0))
    spiel = Spiel()
    vorher = (0, 0)
    letzter_zug = ticks_ms()
    gedrueckt_seit = None
    fehler_seit = None
    lang = False
    auswahl = True
    suche = None
    eingabe_frei = True
    print("PCB ROUTING: Pin anklicken, Bahn ziehen, Gegenpin erreichen.")
    print("Auswahl: links/rechts, Klick = Start. 1,2 s halten = Auswahl.")
    try:
        level_zeigen(spiel, False)
        while True:
            jetzt = ticks_ms()
            werte = [taste.lesen(jetzt) for taste in tasten]
            gedrueckt = mitte.lesen(jetzt)
            if not eingabe_frei:
                if not any(werte) and not gedrueckt:
                    eingabe_frei = True
                werte = [False] * 4
                gedrueckt = False
            richtung = richtungen[werte.index(True)] if sum(werte) == 1 else (0, 0)
            ereignis = "none"
            if gedrueckt:
                if gedrueckt_seit is None:
                    gedrueckt_seit = jetzt
                    lang = False
                    if not auswahl:
                        spiel.zeit_starten(jetzt)
                if not lang and ticks_diff(jetzt, gedrueckt_seit) >= NEUSTART_MS:
                    suche = None
                    auswahl = True
                    fehler_seit = None
                    lang = True
                    eingabe_frei = False
                letzter_zug = ticks_ms()
            elif gedrueckt_seit is not None:
                if not lang:
                    if auswahl:
                        suche = None
                        spiel.laden(spiel.nummer)
                        auswahl = False
                        fehler_seit = None
                        eingabe_frei = False
                    else:
                        ereignis = spiel.klicken()
                gedrueckt_seit = None
                letzter_zug = ticks_ms()
            elif richtung != (0, 0):
                if richtung != vorher or ticks_diff(jetzt, letzter_zug) >= ZUG_MS:
                    if auswahl:
                        if richtung[0]:
                            spiel.laden((spiel.nummer + richtung[0]) % len(LEVEL))
                    else:
                        ereignis = spiel.bewegen(richtung)
                    letzter_zug = jetzt
            vorher = richtung
            if ereignis in ("start", "erase", "cancel"):
                suche = None        # Eine geaenderte Platine macht die Suche alt.
            if ereignis == "block":
                fehler_seit = jetzt
            elif ereignis in ("connected", "win"):
                print("Verbunden:", sum(spiel.fertig), "/", len(spiel.pins))
                suche = spiel.loesbar_pruefen() if ereignis == "connected" else None
            if suche is not None:
                for i in range(PRUEF_SCHRITTE):
                    ergebnis = next(suche)
                    if ergebnis is not None:
                        suche = None
                        if not ergebnis:
                            print("Kein offenes Paar mehr verbindbar: Level", spiel.nummer + 1, "startet neu.")
                            rot_neustarten(spiel)
                            fehler_seit = None
                            gedrueckt_seit = None
                            vorher = (0, 0)
                            letzter_zug = ticks_ms()
                            eingabe_frei = False
                        break
            if ereignis == "win":
                print("Platine", spiel.nummer + 1, "fertig | Schritte:",
                      spiel.zuege, "| Kurzschlussversuche:", spiel.fehler)
                pruefen(spiel)
                print("Zeit:", zeit_text(spiel.dauer_ms), "(Minuten:Sekunden)")
                zeit_anzeigen(spiel.dauer_ms)
                fehler_seit = None
                spiel.laden((spiel.nummer + 1) % len(LEVEL))
                auswahl = True
                eingabe_frei = False
                letzter_zug = ticks_ms()
            if auswahl:
                level_zeigen(spiel, False)
            else:
                zeichnen(spiel, ticks_ms(), True, fehler_seit)
            sleep_ms(PAUSE_MS)
    finally:
        leeren()
        np.write()


if __name__ == "__main__":
    main()
