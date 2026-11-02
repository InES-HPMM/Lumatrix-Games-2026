# ============================================================
#  KIPPWELT – Schwerkraft-Puzzle für das ZHAW Luma Matrix Shield
#  Board: Raspberry Pi Pico / Pico W / Pico 2 mit MicroPython
#  Installation: MicroPython-Firmware flashen, diese Datei als
#  main.py auf den Pico kopieren (z.B. mit Thonny). Fertig.
#
#  Spielregeln
#   - Du (blau) musst auf dem Ziel (grün) zum Stehen kommen.
#   - Wände (grau) sind fix, Blöcke (orange) fallen mit der Schwerkraft.
#   - Du fällst ebenfalls, sobald unter dir nichts ist.
#
#  Steuerung
#   - Klick kurz:  Modus wechseln  LAUFEN (blau) <-> KIPPEN (lila)
#       LAUFEN: quer zur Schwerkraft gehen, 1 Stufe hochklettern
#       KIPPEN: Joystick-Richtung wird zum neuen "unten"
#   - Klick lang (>0.8 s): Level neu starten
#   - Dip-Switch EIN: Levelwahl (Joystick wählt, Klick startet)
#   - 45 s nichts gedrückt: Demo-Modus spielt die Lösung vor
#     (perfekt für den Ausstellungsstand), jede Taste beendet ihn.
# ============================================================

import time

try:
    from machine import Pin
    import neopixel
    AUF_PICO = True
except ImportError:          # auf dem PC: nur Spiellogik (zum Testen)
    AUF_PICO = False

# ---------- Pins laut Zephyr-Overlay des Shields (pico_header N = GPIO N) ----------
PIN_LEDS = 19
PIN_HOCH = 3
PIN_RUNTER = 6
PIN_LINKS = 7
PIN_RECHTS = 2
PIN_MITTE = 8
PIN_SCHALTER = 9

# Falls Bild oder Joystick verdreht sind: hier korrigieren
SPIEGELN_X = False
SPIEGELN_Y = True
ACHSEN_TAUSCHEN = False
ZICKZACK = False             # True, falls jede zweite LED-Zeile rückwärts läuft
HELLIGKEIT = 0.35            # 0..1 – 64 LEDs voll weiss ziehen fast 4 A!
DEMO_NACH_MS = 45000

# ---------- Farben (R, G, B) ----------
FARBE_WAND = (45, 45, 55)
FARBE_BLOCK = (255, 80, 0)
FARBE_LAUFEN = (0, 70, 255)
FARBE_KIPPEN = (100, 0, 150)
FARBE_ZIEL = (0, 255, 40)
FARBE_SCHWERKRAFT = (0, 80, 80)   # Farbe des Kipp-Blitzes

# Schwerkraft-Anzeige: Reihen an der Seite, die gerade "unten" ist.
# Normale RGB-Farben wie alle anderen oben – entweder (R, G, B) oder '#RRGGBB'.
# HELLIGKEIT wird wie bei allen Farben angewendet. (0, 0, 0) = Reihe aus.
SCHWERKRAFT_REIHE_1 = (2, 6, 7)   # ganz aussen an der Kante
SCHWERKRAFT_REIHE_2 = (3, 5, 6)   # eine Reihe weiter innen
SCHWERKRAFT_REIHE_3 = (2, 5, 6)   # noch eine Reihe weiter innen
KIPP_BLITZ = True                    # Reihen nach dem Kippen kurz aufleuchten
FARBE_FEHLER = (255, 0, 0)
FARBE_ZAHL = (255, 190, 0)
FARBE_DEMO = (0, 200, 255)
 
HOCH = (0, -1)
RUNTER = (0, 1)
LINKS = (-1, 0)
RECHTS = (1, 0)
ZEICHEN_RICHTUNG = {'^': HOCH, 'v': RUNTER, '<': LINKS, '>': RECHTS}
 
# ---------- Level ----------
# '#' Wand  'o' Block  'P' Spieler  'Z' Ziel  '.' leer – Start-Schwerkraft: runter
# Zweiter Eintrag = geprüfte Lösung (L = laufen, K = kippen) für den Demo-Modus.
# Alle Level wurden mit einem Löser auf Lösbarkeit geprüft; ab Level 3 ist
# jeder Block nötig und ohne Kippen keines lösbar.
LEVEL = [
    (['........', '........', '........', '........', '........', '......Z.', '.....###', 'P...o###'],
     'L> L> L> L> L> L>'),
    (['.Z......', '##.#####', '........', '........', '........', '........', '........', 'P.......'],
     'L> L> K^ L<'),
    (['.P......', '........', '.o.o....', '........', '........', '..Z.....', '........', '.###....'],
     'L> K< Kv L>'),
    (['..#.....', 'o......o', '##.#....', 'P.......', '........', '#.....Z.', '.....#..', '........'],
     'K> Kv K> L^'),
    (['.....o.#', '....o..#', '......#.', '.....Z..', '.##...#.', '#.......', '........', '.....#P.'],
     'K^ L< K< Kv K> L^'),
    (['........', '.....#..', '.Z......', '.....#.o', 'P#..#...', '.....###', '.#......', '........'],
     'K^ K< K^ L> Kv K< L^'),
    (['........', '........', '.###...#', '........', '........', '.Zo.####', '........', 'P..o....'],
     'K^ K> K^ L< K< Kv K< L^'),
    (['.......#', '.....o..', '#......o', '........', '.....###', '..Z....#', '...P....', '.#......'],
     'K^ K< Kv K> Lv Lv Kv K> L^ K< Kv L>'),
    (['..#o.#..', '...o###.', '........', '..Z.....', 'P......#', '....o..#', '........', '......#.'],
     'K> Kv K< K^ L> L> K< Kv K< L^ L^ K> K^ K< Lv'),
    (['.....##.', '........', '.#....o.', '........', '....Z..#', 'P..o....', '....#...', '....##..'],
     'L> K^ K> Kv K< Kv K< Kv L> K^ K< Lv K> K^ L< L< Kv L> L<'),
    (['......#.', '##......', '.#..oo.#', '...#....', '.......#', '....Z...', '..#.....', '...P....'],
     'K^ L> K< L^ K> Kv K> K^ L< L> Kv L< K^ K< Lv K> Lv Kv K> L^ K< K^ L< L> Kv L>'),
]
 
 
# ============================================================
#  Spiellogik
# ============================================================
 
class Spiel:
    def __init__(self, karte):
        self.waende = set()
        self.bloecke = set()
        self.spieler = None
        self.ziel = None
        for y, zeile in enumerate(karte):
            for x, z in enumerate(zeile):
                if z == '#':
                    self.waende.add((x, y))
                elif z == 'o':
                    self.bloecke.add((x, y))
                elif z == 'P':
                    self.spieler = (x, y)
                elif z == 'Z':
                    self.ziel = (x, y)
        self.schwerkraft = RUNTER
        self.zuege = 0
 
    def ist_frei(self, p):
        x, y = p
        if x < 0 or x > 7 or y < 0 or y > 7:
            return False
        return not (p in self.waende or p in self.bloecke or p == self.spieler)
 
    def fall_schritt(self):
        """Alles Bewegliche fällt genau ein Feld. True, wenn sich etwas bewegt hat."""
        gx, gy = self.schwerkraft
        dinge = list(self.bloecke) + [self.spieler]
        dinge.sort(key=lambda p: -(p[0] * gx + p[1] * gy))   # Unterstes zuerst
        bewegt = False
        for p in dinge:
            neu = (p[0] + gx, p[1] + gy)
            if self.ist_frei(neu):
                if p == self.spieler:
                    self.spieler = neu
                else:
                    self.bloecke.remove(p)
                    self.bloecke.add(neu)
                bewegt = True
        return bewegt
 
    def setzen(self, bild=None):
        while self.fall_schritt():
            if bild:
                bild()
 
    def kippen(self, richtung, bild=None):
        if richtung == self.schwerkraft:
            return False
        self.schwerkraft = richtung
        self.zuege += 1
        self.setzen(bild)
        return True
 
    def laufen(self, richtung, bild=None):
        gx, gy = self.schwerkraft
        dx, dy = richtung
        if dx * gx + dy * gy != 0:
            return False                       # nur quer zur Schwerkraft
        sx, sy = self.spieler
        vorne = (sx + dx, sy + dy)
        if self.ist_frei(vorne):
            self.spieler = vorne
        else:                                  # eine Stufe hochklettern
            ueber_mir = (sx - gx, sy - gy)
            stufe = (vorne[0] - gx, vorne[1] - gy)
            if self.ist_frei(ueber_mir) and self.ist_frei(stufe):
                self.spieler = stufe
            else:
                return False
        self.zuege += 1
        if bild:
            bild()
        self.setzen(bild)
        return True
 
    def zug(self, kuerzel, bild=None):
        """Führt einen Zug wie 'K^' oder 'L>' aus (für Demo und Tests)."""
        r = ZEICHEN_RICHTUNG[kuerzel[1]]
        if kuerzel[0] == 'K':
            return self.kippen(r, bild)
        return self.laufen(r, bild)
 
    def gewonnen(self):
        return self.spieler == self.ziel
 
 
# ============================================================
#  Hardware: LEDs und Tasten
# ============================================================
 
ZIFFERN = {  # 3x5-Schrift
    '0': (7, 5, 5, 5, 7), '1': (2, 6, 2, 2, 7), '2': (7, 1, 7, 4, 7),
    '3': (7, 1, 7, 1, 7), '4': (5, 5, 7, 1, 1), '5': (7, 4, 7, 1, 7),
    '6': (7, 4, 7, 5, 7), '7': (7, 1, 2, 2, 2), '8': (7, 5, 7, 5, 7),
    '9': (7, 5, 7, 1, 7),
}
 
 
class Hardware:
    def __init__(self):
        self.np = neopixel.NeoPixel(Pin(PIN_LEDS, Pin.OUT), 64)
 
        def taste(nr):
            return Pin(nr, Pin.IN, Pin.PULL_UP)
 
        self.richtungen = [(HOCH, taste(PIN_HOCH)), (RUNTER, taste(PIN_RUNTER)),
                           (LINKS, taste(PIN_LINKS)), (RECHTS, taste(PIN_RECHTS))]
        self.mitte = taste(PIN_MITTE)
        self.schalter = taste(PIN_SCHALTER)
        self.vorher = {}
        self.mitte_seit = None
        self.lang_gemeldet = False
        self.letzte_eingabe = time.ticks_ms()
 
    def index(self, x, y):
        """Spielfeld-Koordinate -> LED-Nummer (berücksichtigt Drehung/Spiegelung)."""
        if ACHSEN_TAUSCHEN:
            x, y = y, x
        if SPIEGELN_X:
            x = 7 - x
        if SPIEGELN_Y:
            y = 7 - y
        if ZICKZACK and y % 2 == 1:
            x = 7 - x
        return y * 8 + x
 
    def pixel(self, x, y, farbe, faktor=1.0):
        f = HELLIGKEIT * faktor
        self.np[self.index(x, y)] = (int(farbe[0] * f), int(farbe[1] * f), int(farbe[2] * f))
 
    def pixel_absolut(self, x, y, farbe, anteil):
        """Helligkeit als Anteil von voll – für sehr schwache Anzeigen.
        Jeder Farbkanal > 0 bleibt mindestens 1, damit nichts ganz verschwindet."""
        werte = []
        for kanal in farbe:
            werte.append(max(1, int(kanal * anteil + 0.5)) if kanal > 0 else 0)
        self.np[self.index(x, y)] = tuple(werte)
 
    def leeren(self):
        self.np.fill((0, 0, 0))
 
    def zeigen(self):
        self.np.write()
 
    def richtung_gedrueckt(self):
        """Jede Richtung genau einmal pro Druck (Flanke, aktiv LOW)."""
        ergebnis = None
        for r, pin in self.richtungen:
            jetzt = pin.value() == 0
            if jetzt and not self.vorher.get(r, False) and ergebnis is None:
                ergebnis = r
            self.vorher[r] = jetzt
        if ergebnis:
            self.letzte_eingabe = time.ticks_ms()
        return ergebnis
 
    def mitte_ereignis(self):
        """'kurz', 'lang' oder None."""
        gedrueckt = self.mitte.value() == 0
        jetzt = time.ticks_ms()
        if gedrueckt:
            self.letzte_eingabe = jetzt
            if self.mitte_seit is None:
                self.mitte_seit = jetzt
                self.lang_gemeldet = False
            elif not self.lang_gemeldet and time.ticks_diff(jetzt, self.mitte_seit) > 800:
                self.lang_gemeldet = True
                return 'lang'
        elif self.mitte_seit is not None:
            war_lang = self.lang_gemeldet
            self.mitte_seit = None
            if not war_lang:
                return 'kurz'
        return None
 
    def irgendwas_gedrueckt(self):
        if self.mitte.value() == 0:
            return True
        for _, pin in self.richtungen:
            if pin.value() == 0:
                return True
        return False
 
    def levelwahl_aktiv(self):
        return self.schalter.value() == 0
 
    def untaetig_ms(self):
        return time.ticks_diff(time.ticks_ms(), self.letzte_eingabe)
 
 
def als_rgb(farbe):
    """Akzeptiert (R, G, B) oder '#RRGGBB' und gibt immer (R, G, B) zurück."""
    if isinstance(farbe, str):
        h = farbe.lstrip('#')
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return farbe


def puls(t, minimum=0.35):
    """Dreieckswelle zwischen minimum und 1, Periode 1 s."""
    p = (t % 1000) / 500
    w = p if p < 1 else 2 - p
    return minimum + (1 - minimum) * w
 
 
# ============================================================
#  Programm
# ============================================================
 
class Programm:
    def __init__(self):
        self.hw = Hardware()
        self.level_nr = 0
        self.modus_kippen = False
        self.kipp_zeit = time.ticks_ms() - 10000
        self.neu_starten()
 
    def neu_starten(self):
        self.spiel = Spiel(LEVEL[self.level_nr][0])
        self.spiel.setzen()
        self.modus_kippen = False
 
    # ---------- Zeichnen ----------
    def zeichne(self, spieler_farbe=None):
        s = self.spiel
        hw = self.hw
        t = time.ticks_ms()
        hw.leeren()
        self.zeichne_schwerkraft(t)
        for (x, y) in s.waende:
            hw.pixel(x, y, FARBE_WAND)
        hw.pixel(s.ziel[0], s.ziel[1], FARBE_ZIEL, puls(t))
        for (x, y) in s.bloecke:
            hw.pixel(x, y, FARBE_BLOCK)
        if spieler_farbe is None:
            spieler_farbe = FARBE_KIPPEN if self.modus_kippen else FARBE_LAUFEN
        hw.pixel(s.spieler[0], s.spieler[1], spieler_farbe, puls(t * 2, 0.6))
        hw.zeigen()
 
    def feld(self, spur, tiefe):
        """Wandelt (Spur quer zur Schwerkraft, Tiefe 0=oben..7=unten) in (x, y) um."""
        gx, gy = self.spiel.schwerkraft
        if gy == 1:
            return spur, tiefe
        if gy == -1:
            return spur, 7 - tiefe
        if gx == 1:
            return tiefe, spur
        return 7 - tiefe, spur
 
    def zeichne_schwerkraft(self, t):
        """Zeigt, wo gerade 'unten' ist. Wird von Wänden, Blöcken usw. übermalt."""
        hw = self.hw
        # Nach einem Kippen leuchtet die neue Unterkante kurz hell auf
        seit_kippen = time.ticks_diff(t, self.kipp_zeit)
        blitz = 1.0 - seit_kippen / 600 if seit_kippen < 600 else 0.0
 
        if not KIPP_BLITZ:
            blitz = 0.0
        reihen = (SCHWERKRAFT_REIHE_1, SCHWERKRAFT_REIHE_2, SCHWERKRAFT_REIHE_3)
        blitz_stufen = (1.0, 0.6, 0.3)
        for reihe in range(3):
            tiefe = 7 - reihe                    # 7 = Kante, dann nach innen
            for spur in range(8):
                x, y = self.feld(spur, tiefe)
                if blitz > 0:
                    hw.pixel(x, y, FARBE_SCHWERKRAFT, 0.8 * blitz * blitz_stufen[reihe])
                else:
                    hw.pixel(x, y, als_rgb(reihen[reihe]))
 
    def fallbild(self):
        self.zeichne()
        time.sleep_ms(60)
 
    def zahl_zeigen(self, n, farbe=FARBE_ZAHL):
        hw = self.hw
        hw.leeren()
        text = str(n)
        if len(text) == 1:
            stellen = [(3, text)]
        else:
            stellen = [(0, text[0]), (4, text[1])]
        for (x0, ziffer) in stellen:
            muster = ZIFFERN[ziffer]
            for y in range(5):
                for x in range(3):
                    if muster[y] & (4 >> x):
                        hw.pixel(x0 + x, y + 1, farbe)
        # Fortschrittsbalken: geschaffte Level in der untersten Zeile
        anteil = int(8 * self.level_nr / len(LEVEL))
        for x in range(anteil):
            hw.pixel(x, 7, FARBE_ZIEL, 0.4)
        hw.zeigen()
 
    # ---------- Effekte ----------
    def fehler(self):
        self.zeichne(spieler_farbe=FARBE_FEHLER)
        time.sleep_ms(120)
 
    def sieg_animation(self):
        sx, sy = self.spiel.spieler
        for r in range(14):
            self.hw.leeren()
            for y in range(8):
                for x in range(8):
                    d = abs(x - sx) + abs(y - sy)
                    if r - 1 <= d <= r:
                        self.hw.pixel(x, y, FARBE_ZIEL)
                    elif d < r - 1:
                        self.hw.pixel(x, y, FARBE_ZIEL, 0.12)
            self.hw.zeigen()
            time.sleep_ms(50)
        time.sleep_ms(200)
 
    def ende_animation(self):
        farben = [(255, 0, 0), (255, 120, 0), (255, 255, 0),
                  (0, 255, 0), (0, 120, 255), (160, 0, 255)]
        for runde in range(60):
            for y in range(8):
                for x in range(8):
                    self.hw.pixel(x, y, farben[(x + y + runde) % len(farben)])
            self.hw.zeigen()
            time.sleep_ms(50)
 
    def level_einblenden(self):
        self.zahl_zeigen(self.level_nr + 1)
        time.sleep_ms(800)
        self.hw.letzte_eingabe = time.ticks_ms()
 
    # ---------- Ablauf ----------
    def geschafft(self):
        self.zeichne()
        time.sleep_ms(250)
        self.sieg_animation()
        self.level_nr += 1
        if self.level_nr >= len(LEVEL):
            self.ende_animation()
            self.level_nr = 0
        self.neu_starten()
        self.level_einblenden()
 
    def levelwahl(self):
        while self.hw.levelwahl_aktiv():
            self.zahl_zeigen(self.level_nr + 1)
            r = self.hw.richtung_gedrueckt()
            if r in (RECHTS, HOCH):
                self.level_nr = (self.level_nr + 1) % len(LEVEL)
            elif r in (LINKS, RUNTER):
                self.level_nr = (self.level_nr - 1) % len(LEVEL)
            if self.hw.mitte_ereignis() == 'kurz':
                self.neu_starten()
                # Spielen geht auch mit Schalter EIN weiter, sobald geklickt wurde
                return
            time.sleep_ms(20)
        self.neu_starten()
        self.level_einblenden()
 
    def demo(self):
        """Spielt die gespeicherte Lösung des aktuellen Levels vor."""
        self.neu_starten()
        for kuerzel in LEVEL[self.level_nr][1].split():
            self.modus_kippen = kuerzel[0] == 'K'
            for _ in range(25):                  # kurz zeigen, welcher Modus kommt
                if self.hw.irgendwas_gedrueckt():
                    return self.demo_abbrechen()
                self.zeichne(spieler_farbe=FARBE_DEMO if not self.modus_kippen else FARBE_KIPPEN)
                time.sleep_ms(20)
            if self.modus_kippen:
                self.kipp_zeit = time.ticks_ms()
            self.spiel.zug(kuerzel, self.fallbild)
        self.zeichne()
        time.sleep_ms(300)
        self.sieg_animation()
        self.neu_starten()
        self.hw.letzte_eingabe = time.ticks_ms() - DEMO_NACH_MS + 4000   # bald wieder Demo
 
    def demo_abbrechen(self):
        while self.hw.irgendwas_gedrueckt():     # warten bis losgelassen
            time.sleep_ms(10)
        self.hw.vorher = {}
        self.hw.mitte_seit = None
        self.neu_starten()
        self.level_einblenden()
 
    def los(self):
        self.level_einblenden()
        schalter_vorher = self.hw.levelwahl_aktiv()
        while True:
            schalter = self.hw.levelwahl_aktiv()
            if schalter and not schalter_vorher:
                self.levelwahl()
            schalter_vorher = schalter
 
            m = self.hw.mitte_ereignis()
            if m == 'kurz':
                self.modus_kippen = not self.modus_kippen
            elif m == 'lang':
                self.fehler()
                self.neu_starten()
 
            r = self.hw.richtung_gedrueckt()
            if r:
                if self.modus_kippen:
                    if r != self.spiel.schwerkraft:
                        self.kipp_zeit = time.ticks_ms()
                    ok = self.spiel.kippen(r, self.fallbild)
                else:
                    ok = self.spiel.laufen(r, self.fallbild)
                if not ok:
                    self.fehler()
                elif self.spiel.gewonnen():
                    self.geschafft()
 
            if self.hw.untaetig_ms() > DEMO_NACH_MS:
                self.demo()
 
            self.zeichne()
            time.sleep_ms(15)
 
 
if AUF_PICO:
    Programm().los()