# ============================================================
# LUMATRIX ZUG-SPIEL
# Zwei Schweizer Züge (RABe 512 der SBB und ABe 4/8 "Diamant"
# der BDWM, nach Fotos als Pixelbild) fahren Wagen für Wagen
# ein; danach wählst du Zug (nur der Vorderteil ist zu sehen)
# und Schwierigkeit. Vier Runden mit Ampel-Countdown:
# Ausweichen, Snake, Rennen und der Endkampf in drei Phasen.
# Am Ende zeigt das Programm deine Zeit und die Bestzeit.
# ============================================================
from neopixel import NeoPixel
from machine import Pin
from utime import sleep_ms, ticks_ms, ticks_diff, ticks_add
import random

# ---------- EINSTELLUNGEN (hier kannst du leicht ändern) ----------
ZUG_TEMPO_MS = 130        # Pause pro Schritt bei der Zugfahrt (kleiner = schneller)
TEXT_TEMPO_MS = 110       # Pause pro Schritt beim Schriftzug
TEXT_TEMPO_LANG_MS = 70   # schnellere Laufschrift für lange Texte
TEXT_Y_OBEN = 6           # Höhe der obersten Textzeile
WAGEN_LUECKE = "."        # Zeichen zwischen den Wagen (. = Lücke, D = dunkle Kupplung)
WAND_TOET = False         # Snake: True = Wand ist tödlich, False = man kommt gegenüber wieder raus

AMPEL_MS = 600            # so lange leuchtet jede Ampelfarbe
EXPLOSION_MS = 80         # Tempo der Explosion (kleiner = schneller)
REKORD_DATEI = "bestzeiten.txt"   # hier speichert der Pico die Bestzeiten

RENNEN_SPIELER_MS = 2000  # Runde 3: so lange braucht dein Zug pro Streckenabschnitt
RENNEN_LAENGE = 8         # Runde 3: Länge der Strecke (höchstens 8)

SCHUSS_MS = 70            # Runde 4: Tempo deiner Schüsse (kleiner = schneller)
MAX_SCHUESSE = 2          # Runde 4: so viele eigene Schüsse gleichzeitig
ENDKAMPF_BEWEGUNG_MS = 110  # Runde 4: Tempo deines Zuges (kleiner = schneller)
TREFFER_PAUSE_MS = 700    # Runde 4: so lange sieht man die übrigen Leben
# Boss-Phasen (Phase 1, 2, 3): Prozent der normalen Pause, kleiner = schneller
PHASEN_TEMPO = (100, 75, 55)    # Bewegung des Gegners
PHASEN_FEUER = (100, 80, 60)    # Schiess-Rhythmus des Gegners

ROT = (60, 0, 0)
WEISS = (40, 40, 40)
BLAU = (0, 6, 48)         # Diamant-Blau (dunkles Navy wie auf dem Foto)
FENSTER = (3, 7, 16)      # dunkle Fenster und Frontscheibe
DUNKEL = (6, 6, 8)        # Dach (RABe), Unterboden, Frontscheibe
DACH_GRAU = (16, 16, 18)  # hellgraues Dach vom Diamant
RAD = (14, 14, 14)
LICHT = (50, 25, 0)       # Scheinwerfer (orange)
ANZEIGE = (30, 40, 0)     # Zielanzeige an der Front (gelbgrün)
SCHIENE = (6, 6, 6)       # Schienen im Spiel
AMPEL_GEHAEUSE = (8, 8, 8)
ORANGE = (60, 20, 0)
GRUEN = (0, 50, 0)
GELB = (50, 50, 0)        # Futter bei Snake, deine Schüsse in Runde 4
TREFFER_FARBE = GELB      # so blinkt ein getroffener Zug
HINDERNIS = ORANGE        # Farbe der Blöcke im Spiel (und der Schüsse des Gegners)
EXPL_FARBEN = (WEISS, GELB, ORANGE, ROT, (20, 0, 0))   # Explosion von innen nach aussen

TEXT_FARBE_1 = (60, 0, 0)       # Schriftzug RABe 512
TEXT_FARBE_2 = (0, 20, 60)      # Schriftzug Diamant
MENUE_TEXT_FARBE = (40, 40, 0)
RUNDE2_FARBE = (60, 40, 0)
RUNDE3_FARBE = (60, 0, 20)      # Spott-Text vom Gegner
RUNDE4_FARBE = (60, 0, 60)
ZEIT_FARBE = (0, 50, 50)

TEXT_1 = "STADLER KISS RABE 512 DER SBB"
TEXT_2 = 'ABE 4/8 "DIAMANT" DER BDWM'
TEXT_MENUE = "WAEHLE ZUG"
TEXT_SCHWER = "WAEHLE SCHWIERIGKEIT"
TEXT_RUNDE2 = "ROUND TWO"
TEXT_RUNDE3 = ("HAHA DU HAST GEDACHT DASS DAS DAS GAME IST NEIN DAS WAR NUR DAS "
               "TUTORIAL DENKST DU SCHAFFST ES MICH NUN ZU BESIEGEN")
TEXT_RUNDE4 = "ROUND FOUR FINAL FIGHT"
TEXT_PHASEN = ("", "PHASE 2", "LETZTE PHASE")   # Texte beim Phasenwechsel des Gegners
TEXT_ENDE = "DU HAST GEWONNEN BESTER LOKFUEHRER"
TEXT_ZEIT = "ZEIT"
TEXT_REKORD = "NEUER REKORD"
TEXT_BEST = "BESTZEIT"

# Schwierigkeitsstufen:
#  farbe = Farbe im Menü
#  ziel / tempo / abstand / max = Runde 1 (Abstand nie unter 4, max. 2 Blöcke gleichzeitig)
#  snake_ziel / snake_tempo = Runde 2 (Futter bis zum Sieg, Pause pro Schritt)
#  rennen_rivale = Runde 3, so viele ms braucht der Gegner pro Abschnitt (grösser = leichter)
#  leben, boss_hp, boss_tempo, boss_feuer, boss_schuss_ms = Runde 4
#    (deine Leben, Leben des Gegners, Pause pro Gegner-Schritt,
#     Pause zwischen seinen Schüssen, Pause pro Schritt seiner Schüsse)
SCHWIERIGKEITEN = [
    {"farbe": GRUEN,  "ziel": 6,  "tempo": 550, "abstand": 5, "max": 2,
     "snake_ziel": 5,  "snake_tempo": 500,
     "rennen_rivale": 3000,
     "leben": 4, "boss_hp": 6,  "boss_tempo": 500, "boss_feuer": 1500, "boss_schuss_ms": 300},   # einfach
    {"farbe": ORANGE, "ziel": 10, "tempo": 450, "abstand": 5, "max": 2,
     "snake_ziel": 8,  "snake_tempo": 380,
     "rennen_rivale": 2500,
     "leben": 3, "boss_hp": 9,  "boss_tempo": 380, "boss_feuer": 1100, "boss_schuss_ms": 240},   # mittel
    {"farbe": ROT,    "ziel": 14, "tempo": 320, "abstand": 4, "max": 2,
     "snake_ziel": 12, "snake_tempo": 260,
     "rennen_rivale": 2300,
     "leben": 2, "boss_hp": 12, "boss_tempo": 260, "boss_feuer": 750,  "boss_schuss_ms": 190},   # schwer
]

# ---------- HARDWARE ----------
np = NeoPixel(Pin(19, Pin.OUT), 64)
rechts = Pin(2, Pin.IN, Pin.PULL_UP)
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
hinein = Pin(8, Pin.IN, Pin.PULL_UP)

# ---------- ZEITMESSUNG ----------
spielzeit = 0     # reine Spielzeit aller Runden in Millisekunden
abzug = 0         # Pausen innerhalb einer Runde (Texte, Leben-Anzeige), zählen nicht mit

# ---------- ZÜGE (Seitenansicht, oberste Zeile zuerst, Front rechts) ----------
# Zeichen: W=weiss R=rot B=blau G=Fenster D=dunkel S=graues Dach
#          K=Rad Y=Scheinwerfer Z=Zielanzeige .=aus
FARBEN = {"W": WEISS, "R": ROT, "B": BLAU, "G": FENSTER, "D": DUNKEL,
          "S": DACH_GRAU, "K": RAD, "Y": LICHT, "Z": ANZEIGE, ".": None}

# --- SBB RABe 512 (Doppelstöcker): weiss, dunkles Dach, rote Türen, rote Front ---
RABE_MITTE = [          # mittlerer Wagen (8 breit, 7 hoch)
    "DDDDDDDD",
    "WGGWGGGW",         # obere Fensterreihe
    "WWWWWWWW",
    "WGGRRGGW",         # untere Fenster und rote Tür
    "WWWRRWWW",
    "WWWRRWWW",
    "DDKDDKDD",         # Unterboden mit Rädern
]
RABE_KOPF = [           # vorderer Wagen mit dunkler Scheibe und roter Nase
    "DDDDDDD.",
    "WGGWGGDD",
    "WWWWWWDD",
    "WGGRGGDR",
    "WWWRWWRR",
    "WWWRWWRR",
    "DKDDDKDD",
]

# --- BDWM ABe 4/8 "Diamant": drei Wagen, Kopfwagen dunkelblau mit weissem AV-Logo ---
DIA_HECK = [            # kurzer Heckwagen (6 breit, 6 hoch), Zugende links
    ".SSSSS",
    "WGGWGW",
    "WGGWGW",
    "WWWWWW",
    "WWWWWW",
    "BKBBKB",
]
DIA_MITTE = [           # weisser Mittelwagen mit Türen (8 breit)
    "SSSSSSSS",
    "WGGWWGGW",
    "WGGWWGGW",
    "WWWWWWWW",
    "WWWWWWWW",
    "BKBBBBKB",
]
DIA_KOPF = [            # Kopfwagen: AV-Logo, Fahrerfenster, Frontscheibe, Scheinwerfer
    "SSSSSSS.",
    "GGBGGBGZ",         # Fenster, Fahrerfenster, Zielanzeige oben an der Front
    "BWBWBWBD",         # AV-Logo oben, Frontscheibe
    "WBWWBWBD",         # AV-Logo Mitte
    "WWWBWBBY",         # AV-Logo unten, Scheinwerfer
    "BKBBBBKD",         # Unterboden mit Rädern
]

def zug_bauen(teile):
    # setzt die Wagen zu einem Zug zusammen (mit Lücke dazwischen)
    zeilen = []
    for r in range(len(teile[0])):
        zeilen.append(WAGEN_LUECKE.join([t[r] for t in teile]))
    return zeilen

# Bild (ganzer Zug), Vorderteil fürs Menü, Höhe über dem Boden,
# Textfarbe, Farben von oben (für Spiel, Rennen und Endkampf)
ZUEGE = [
    {"sprite": zug_bauen([RABE_MITTE, RABE_MITTE, RABE_MITTE, RABE_KOPF]),
     "vorderteil": RABE_KOPF, "unten": 1,
     "text": TEXT_1, "tfarbe": TEXT_FARBE_1, "koerper": WEISS, "front": ROT},
    {"sprite": zug_bauen([DIA_HECK, DIA_MITTE, DIA_KOPF]),
     "vorderteil": DIA_KOPF, "unten": 1,
     "text": TEXT_2, "tfarbe": TEXT_FARBE_2, "koerper": BLAU, "front": WEISS},
]

# ---------- SCHRIFT 3x5 (jede Zeile = 3 Pixel) ----------
FONT = {
    "A": ("010", "101", "111", "101", "101"), "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"), "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"), "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"), "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"), "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"), "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"), "N": ("110", "101", "101", "101", "101"),
    "O": ("010", "101", "101", "101", "010"), "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "110", "011"), "R": ("110", "101", "110", "101", "101"),
    "S": ("011", "100", "010", "001", "110"), "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"), "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"), "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"), "Z": ("111", "001", "010", "100", "111"),
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"), "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "111", "101", "111"), "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "110"),
    "/": ("001", "001", "010", "100", "100"), '"': ("101", "101", "000", "000", "000"),
    "-": ("000", "000", "111", "000", "000"), " ": ("000", "000", "000", "000", "000"),
}

# ---------- GRUNDFUNKTIONEN ----------
def punkt(x, y, farbe):
    # Pixel setzen, nur wenn er auf der Matrix liegt
    if 0 <= x < 8 and 0 <= y < 8:
        np[y * 8 + x] = farbe

def loeschen():
    np.fill((0, 0, 0))

def gedimmt(f):
    # Farbe abdunkeln (für nicht gewählte Auswahl im Menü)
    return (f[0] // 5, f[1] // 5, f[2] // 5)

def blitz(farbe, anzahl):
    # ganze Matrix blinkt in einer Farbe
    for _ in range(anzahl):
        np.fill(farbe)
        np.write()
        sleep_ms(150)
        loeschen()
        np.write()
        sleep_ms(150)

def warte_loslassen():
    # wartet, bis "hineindrücken" losgelassen ist
    while hinein.value() == 0:
        sleep_ms(10)

# ---------- EFFEKTE: AMPEL UND EXPLOSION ----------
def ampel():
    # Signal-Ampel vor jeder Runde: rot, orange, grün
    lampen = ((ROT, 5), (ORANGE, 3), (GRUEN, 1))     # Farbe, unterste Zeile der Lampe
    for aktiv in range(3):
        loeschen()
        for y in range(8):                           # Gehäuse
            punkt(2, y, AMPEL_GEHAEUSE)
            punkt(5, y, AMPEL_GEHAEUSE)
        punkt(3, 7, AMPEL_GEHAEUSE)
        punkt(4, 7, AMPEL_GEHAEUSE)
        punkt(3, 0, AMPEL_GEHAEUSE)
        punkt(4, 0, AMPEL_GEHAEUSE)
        for i in range(3):
            farbe = lampen[i][0]
            y0 = lampen[i][1]
            if i != aktiv:
                farbe = gedimmt(farbe)
            for dy in range(2):                      # jede Lampe 2x2 Pixel
                punkt(3, y0 + dy, farbe)
                punkt(4, y0 + dy, farbe)
        np.write()
        sleep_ms(AMPEL_MS)
    loeschen()
    np.write()

def explosion(cx, cy):
    # Feuerball breitet sich von (cx, cy) aus
    for r in range(5):
        loeschen()
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                d = max(abs(dx), abs(dy))
                if d <= r:
                    punkt(cx + dx, cy + dy, EXPL_FARBEN[min(r - d, 4)])
        np.write()
        sleep_ms(EXPLOSION_MS)
    loeschen()
    np.write()

def grosse_explosion(cx, cy):
    # drei Explosionen hintereinander (für den besiegten Gegner)
    explosion(cx, cy)
    explosion(cx + 2, cy - 1)
    explosion(cx - 1, cy + 1)

# ---------- ANIMATION ----------
def zeichne_zug(sprite, versatz, unten):
    # Zug seitlich zeichnen; versatz = x-Position der linken Zugkante
    hoehe = len(sprite)
    for r in range(hoehe):
        y = unten + (hoehe - 1 - r)
        for i in range(len(sprite[r])):
            f = FARBEN[sprite[r][i]]
            if f:
                punkt(versatz + i, y, f)

def zug_vorbeifahrt(sprite, unten):
    # Zug fährt von links nach rechts in einzelnen Schritten durchs Bild
    breite = len(sprite[0])
    for versatz in range(-breite, 9):
        loeschen()
        zeichne_zug(sprite, versatz, unten)
        np.write()
        sleep_ms(ZUG_TEMPO_MS)

def laufschrift(text, farbe, tempo=TEXT_TEMPO_MS, abbruch=False):
    # Text läuft von rechts nach links durchs Bild
    # abbruch=True: mit Hineindrücken kann man den Text überspringen
    if abbruch:
        warte_loslassen()
    spalten = []
    for c in text.upper():
        muster = FONT.get(c, FONT[" "])
        for sp in range(3):
            spalten.append([1 if muster[r][sp] == "1" else 0 for r in range(5)])
        spalten.append([0, 0, 0, 0, 0])  # Lücke zwischen Buchstaben
    for versatz in range(8, -len(spalten) - 1, -1):
        if abbruch and hinein.value() == 0:
            warte_loslassen()
            return
        loeschen()
        for i in range(len(spalten)):
            x = versatz + i
            if 0 <= x < 8:
                for r in range(5):
                    if spalten[i][r]:
                        punkt(x, TEXT_Y_OBEN - r, farbe)
        np.write()
        sleep_ms(tempo)

def intro():
    # beide Züge mit ihren Schriftzügen
    for z in ZUEGE:
        zug_vorbeifahrt(z["sprite"], z["unten"])
        laufschrift(z["text"], z["tfarbe"])

# ---------- BESTZEITEN ----------
def lade_rekorde():
    # liest die drei Bestzeiten (Sekunden) aus der Datei; 0 = noch keine
    try:
        f = open(REKORD_DATEI)
        text = f.read()
        f.close()
        werte = [int(t) for t in text.strip().split(",")]
        if len(werte) == len(SCHWIERIGKEITEN):
            return werte
    except:
        pass
    return [0] * len(SCHWIERIGKEITEN)

def speichere_rekorde(werte):
    try:
        f = open(REKORD_DATEI, "w")
        f.write(",".join([str(w) for w in werte]))
        f.close()
    except:
        pass     # Speichern klappt nicht? Dann läuft das Spiel einfach weiter

def zeige_zeit(stufe_nr):
    # zeigt die Spielzeit und speichert sie, wenn sie die Bestzeit ist
    sek = spielzeit // 1000
    rekorde = lade_rekorde()
    alt = rekorde[stufe_nr]
    laufschrift(TEXT_ZEIT + " " + str(sek) + " SEK", ZEIT_FARBE)
    if alt == 0 or sek < alt:
        rekorde[stufe_nr] = sek
        speichere_rekorde(rekorde)
        blitz(GELB, 3)
        laufschrift(TEXT_REKORD, GELB)
    else:
        laufschrift(TEXT_BEST + " " + str(alt) + " SEK", ZEIT_FARBE)

def messen(spielfunktion, *args):
    # führt eine Runde aus und zählt nur die reine Spielzeit mit
    global spielzeit, abzug
    abzug = 0
    t0 = ticks_ms()
    ergebnis = spielfunktion(*args)
    spielzeit += ticks_diff(ticks_ms(), t0) - abzug
    return ergebnis

# ---------- MENÜS ----------
def menue():
    # Zug wählen: links/rechts = wechseln, hineindrücken = bestätigen
    laufschrift(TEXT_MENUE, MENUE_TEXT_FARBE)
    warte_loslassen()
    auswahl = 0
    vor_l = vor_r = vor_h = False
    while True:
        l = links.value() == 0
        r = rechts.value() == 0
        h = hinein.value() == 0
        if l and not vor_l:
            auswahl = (auswahl - 1) % len(ZUEGE)
        if r and not vor_r:
            auswahl = (auswahl + 1) % len(ZUEGE)
        if h and not vor_h:
            warte_loslassen()
            return auswahl
        vor_l, vor_r, vor_h = l, r, h

        z = ZUEGE[auswahl]
        loeschen()
        # nur der Vorderteil des Zuges, füllt die ganze Breite
        zeichne_zug(z["vorderteil"], 0, z["unten"])
        punkt(0, 0, (8, 8, 8))   # Pfeil links (unten)
        punkt(7, 0, (8, 8, 8))   # Pfeil rechts (unten)
        for i in range(len(ZUEGE)):   # Punkte unten: welcher Zug ist gewählt
            punkt(3 + i, 0, WEISS if i == auswahl else (4, 4, 4))
        np.write()
        sleep_ms(30)

def schwierigkeit_menue():
    # Schwierigkeit wählen: drei Farbblöcke (grün / orange / rot)
    laufschrift(TEXT_SCHWER, MENUE_TEXT_FARBE)
    warte_loslassen()
    auswahl = 0
    vor_l = vor_r = vor_h = False
    BLOCK_X = (0, 3, 6)       # linke Spalte jedes Farbblocks (2 Pixel breit)
    while True:
        l = links.value() == 0
        r = rechts.value() == 0
        h = hinein.value() == 0
        if l and not vor_l and auswahl > 0:
            auswahl -= 1
        if r and not vor_r and auswahl < len(SCHWIERIGKEITEN) - 1:
            auswahl += 1
        if h and not vor_h:
            warte_loslassen()
            return auswahl
        vor_l, vor_r, vor_h = l, r, h

        loeschen()
        for i in range(len(SCHWIERIGKEITEN)):
            f = SCHWIERIGKEITEN[i]["farbe"]
            if i != auswahl:
                f = gedimmt(f)
            for y in range(3, 7):             # Farbblock 2 breit, 4 hoch
                punkt(BLOCK_X[i], y, f)
                punkt(BLOCK_X[i] + 1, y, f)
            if i == auswahl:                  # weisser Punkt unter dem gewählten Block
                punkt(BLOCK_X[i], 1, WEISS)
                punkt(BLOCK_X[i] + 1, 1, WEISS)
        np.write()
        sleep_ms(30)

# ---------- RUNDE 1: AUSWEICHEN ----------
SPUR_X = (0, 3, 6)    # linke Pixelspalte jeder Spur (Spur ist 2 Pixel breit)
ZUG_LAENGE = 3        # Zug von oben: 3 Pixel lang (unten)

def spiel(zug, stufe):
    # True = gewonnen, False = Zusammenstoss
    tempo = stufe["tempo"]
    abstand = stufe["abstand"]
    max_sichtbar = stufe["max"]
    ziel = stufe["ziel"]
    spur = 1
    hindernisse = []   # jedes Hindernis: [spur, y]
    geschafft = 0
    zaehler = abstand - 2   # erster Block kommt etwas früher
    letzter = ticks_ms()
    vor_l = vor_r = False
    while True:
        # Steuerung: ein Druck = eine Spur weiter
        l = links.value() == 0
        r = rechts.value() == 0
        if l and not vor_l and spur > 0:
            spur -= 1
        if r and not vor_r and spur < 2:
            spur += 1
        vor_l, vor_r = l, r

        # Hindernisse bewegen
        jetzt = ticks_ms()
        if ticks_diff(jetzt, letzter) >= tempo:
            letzter = jetzt
            for h in hindernisse:
                h[1] -= 1
            zaehler += 1
            # neuer Block nur, wenn genug Abstand und nicht zu viele sichtbar
            if zaehler >= abstand and len(hindernisse) < max_sichtbar:
                zaehler = 0
                hindernisse.append([random.randint(0, 2), 7])
            neu = []
            for h in hindernisse:
                if h[1] < 0:
                    geschafft += 1    # Hindernis ist vorbei
                else:
                    neu.append(h)
            hindernisse = neu
            if geschafft >= ziel:
                return True

        # Zusammenstoss prüfen
        for h in hindernisse:
            if h[0] == spur and h[1] <= ZUG_LAENGE - 1:
                explosion(SPUR_X[spur], 1)
                return False

        # Zeichnen
        loeschen()
        for y in range(8):             # Trennlinien zwischen den Spuren
            punkt(2, y, SCHIENE)
            punkt(5, y, SCHIENE)
        for h in hindernisse:
            punkt(SPUR_X[h[0]], h[1], HINDERNIS)
            punkt(SPUR_X[h[0]] + 1, h[1], HINDERNIS)
        for dy in range(ZUG_LAENGE):   # Zug von oben, vorne = andere Farbe
            f = zug["front"] if dy == ZUG_LAENGE - 1 else zug["koerper"]
            punkt(SPUR_X[spur], dy, f)
            punkt(SPUR_X[spur] + 1, dy, f)
        np.write()
        sleep_ms(20)

# ---------- RUNDE 2: SNAKE ----------
def neues_futter(koerper):
    # zufälliges freies Feld für das Futter suchen
    frei = []
    for y in range(8):
        for x in range(8):
            if (x, y) not in koerper:
                frei.append((x, y))
    return frei[random.randint(0, len(frei) - 1)]

def snake(zug, stufe):
    # True = gewonnen, False = verloren
    tempo = stufe["snake_tempo"]
    ziel = stufe["snake_ziel"]
    koerper = [(3, 3), (2, 3), (1, 3)]    # Kopf zuerst
    richtung = (1, 0)                     # fährt zuerst nach rechts
    neue = richtung
    futter = neues_futter(koerper)
    gefressen = 0
    letzter = ticks_ms()
    while True:
        # Richtung lesen (nicht direkt rückwärts)
        if rechts.value() == 0 and richtung != (-1, 0):
            neue = (1, 0)
        elif links.value() == 0 and richtung != (1, 0):
            neue = (-1, 0)
        elif hoch.value() == 0 and richtung != (0, -1):
            neue = (0, 1)
        elif runter.value() == 0 and richtung != (0, 1):
            neue = (0, -1)

        # Einen Schritt fahren
        jetzt = ticks_ms()
        if ticks_diff(jetzt, letzter) >= tempo:
            letzter = jetzt
            richtung = neue
            kx = koerper[0][0] + richtung[0]
            ky = koerper[0][1] + richtung[1]
            if WAND_TOET:
                if kx < 0 or kx > 7 or ky < 0 or ky > 7:
                    explosion(koerper[0][0], koerper[0][1])
                    return False
            else:
                kx = kx % 8
                ky = ky % 8
            frisst = (kx, ky) == futter
            # Schwanzspitze zählt nicht, weil sie gleichzeitig wegrückt
            if frisst:
                pruefen = koerper
            else:
                pruefen = koerper[:-1]
            if (kx, ky) in pruefen:
                explosion(kx, ky)
                return False
            koerper.insert(0, (kx, ky))
            if frisst:
                gefressen += 1
                if gefressen >= ziel:
                    return True
                futter = neues_futter(koerper)
            else:
                koerper.pop()

        # Zeichnen
        loeschen()
        punkt(futter[0], futter[1], GELB)
        for i in range(len(koerper)):
            if i == 0:
                punkt(koerper[i][0], koerper[i][1], zug["front"])
            else:
                punkt(koerper[i][0], koerper[i][1], zug["koerper"])
        np.write()
        sleep_ms(20)

# ---------- RUNDE 3: RENNEN GEGEN DEN ANDEREN ZUG ----------
def rennen(zug, rivale, stufe):
    # Linke Schiene = dein Fortschritt, rechte Schiene = Fortschritt des Gegners
    # True = du bist zuerst oben, False = der Gegner war schneller
    tempo = stufe["tempo"]
    abstand = stufe["abstand"]
    max_sichtbar = stufe["max"]
    rivale_ms = stufe["rennen_rivale"]
    spur = 1
    hindernisse = []
    zaehler = abstand - 2
    ich = 0
    er = 0
    start = ticks_ms()
    t_block = t_ich = t_er = start
    blink_bis = start
    vor_l = vor_r = False
    while True:
        # Steuerung: ein Druck = eine Spur weiter
        l = links.value() == 0
        r = rechts.value() == 0
        if l and not vor_l and spur > 0:
            spur -= 1
        if r and not vor_r and spur < 2:
            spur += 1
        vor_l, vor_r = l, r

        jetzt = ticks_ms()

        # Blöcke bewegen
        if ticks_diff(jetzt, t_block) >= tempo:
            t_block = jetzt
            for h in hindernisse:
                h[1] -= 1
            zaehler += 1
            if zaehler >= abstand and len(hindernisse) < max_sichtbar:
                zaehler = 0
                hindernisse.append([random.randint(0, 2), 7])
            hindernisse = [h for h in hindernisse if h[1] >= 0]

        # Beide Züge kommen voran
        if ticks_diff(jetzt, t_ich) >= RENNEN_SPIELER_MS:
            t_ich = jetzt
            ich += 1
        if ticks_diff(jetzt, t_er) >= rivale_ms:
            t_er = jetzt
            er += 1
        if ich >= RENNEN_LAENGE:
            return True
        if er >= RENNEN_LAENGE:
            return False

        # Zusammenstoss: du verlierst einen Streckenabschnitt
        neu = []
        for h in hindernisse:
            if h[0] == spur and h[1] <= ZUG_LAENGE - 1:
                if ich > 0:
                    ich -= 1
                blink_bis = ticks_add(jetzt, 300)
            else:
                neu.append(h)
        hindernisse = neu

        # Zeichnen
        loeschen()
        for y in range(8):             # Schienen als Fortschrittsbalken
            punkt(2, y, SCHIENE)
            punkt(5, y, SCHIENE)
        for y in range(ich):
            punkt(2, y, zug["koerper"])
        for y in range(er):
            punkt(5, y, rivale["koerper"])
        for h in hindernisse:
            punkt(SPUR_X[h[0]], h[1], HINDERNIS)
            punkt(SPUR_X[h[0]] + 1, h[1], HINDERNIS)
        blinkt = ticks_diff(blink_bis, jetzt) > 0
        for dy in range(ZUG_LAENGE):
            if blinkt:
                f = TREFFER_FARBE
            elif dy == ZUG_LAENGE - 1:
                f = zug["front"]
            else:
                f = zug["koerper"]
            punkt(SPUR_X[spur], dy, f)
            punkt(SPUR_X[spur] + 1, dy, f)
        np.write()
        sleep_ms(20)

# ---------- RUNDE 4: ENDKAMPF DER ZWEI LOKS ----------
def zeige_leben(anzahl):
    # zeigt kurz, wie viele Leben du noch hast (zählt nicht zur Spielzeit)
    global abzug
    loeschen()
    start_x = (8 - anzahl) // 2
    for i in range(anzahl):
        punkt(start_x + i, 3, GRUEN)
    np.write()
    sleep_ms(TREFFER_PAUSE_MS)
    abzug += TREFFER_PAUSE_MS

def pause_text(text, farbe):
    # Text mitten im Kampf; die Zeit dafür zählt nicht zur Spielzeit
    global abzug
    t = ticks_ms()
    blitz(farbe, 2)
    laufschrift(text, farbe, TEXT_TEMPO_LANG_MS)
    abzug += ticks_diff(ticks_ms(), t)

def phase_von(hp, hp_max):
    # Phase 0, 1 oder 2 je nach Leben des Gegners (Drittel)
    if hp * 3 > hp_max * 2:
        return 0
    if hp * 3 > hp_max:
        return 1
    return 2

def endkampf(zug, rivale, stufe):
    # links/rechts = fahren, hineindrücken = schiessen
    # True = Gegner besiegt, False = alle Leben verloren
    leben = stufe["leben"]
    hp_max = stufe["boss_hp"]
    hp = hp_max
    phase = 0
    px = 3                # linke Pixelspalte deines Zuges (0 bis 6)
    bx = 3                # linke Pixelspalte des Gegners (0 bis 6)
    bdir = 1
    schuesse = []         # deine Schüsse: [x, y], fliegen nach oben
    bschuesse = []        # Schüsse des Gegners: [x, y], fliegen nach unten
    jetzt = ticks_ms()
    t_move = t_schuss = t_boss = t_feuer = t_bschuss = jetzt
    blink_bis = jetzt
    vor_h = False
    while True:
        jetzt = ticks_ms()

        # Deinen Zug bewegen
        if ticks_diff(jetzt, t_move) >= ENDKAMPF_BEWEGUNG_MS:
            if links.value() == 0 and px > 0:
                px -= 1
                t_move = jetzt
            elif rechts.value() == 0 and px < 6:
                px += 1
                t_move = jetzt

        # Schiessen (ein Druck = ein Schuss, linke Spalte deines Zuges)
        h = hinein.value() == 0
        if h and not vor_h and len(schuesse) < MAX_SCHUESSE:
            schuesse.append([px, 2])
        vor_h = h

        # Deine Schüsse bewegen und Treffer prüfen
        if ticks_diff(jetzt, t_schuss) >= SCHUSS_MS:
            t_schuss = jetzt
            neu = []
            for s in schuesse:
                s[1] += 1
                if (s[1] == 5 or s[1] == 6) and bx <= s[0] <= bx + 1:
                    hp -= 1
                    blink_bis = ticks_add(jetzt, 150)
                elif s[1] <= 7:
                    neu.append(s)
            schuesse = neu
            if hp <= 0:
                grosse_explosion(bx, 5)
                return True

        # Phasenwechsel des Gegners
        neue_phase = phase_von(hp, hp_max)
        if neue_phase > phase:
            phase = neue_phase
            pause_text(TEXT_PHASEN[phase], RUNDE4_FARBE)
            schuesse = []
            bschuesse = []
            jetzt = ticks_ms()
            t_move = t_schuss = t_boss = t_feuer = t_bschuss = jetzt

        # Gegner bewegen (hin und her, manchmal spontan die Richtung wechseln)
        if ticks_diff(jetzt, t_boss) >= stufe["boss_tempo"] * PHASEN_TEMPO[phase] // 100:
            t_boss = jetzt
            if random.randint(0, 3) == 0:
                bdir = -bdir
            bx += bdir
            if bx < 0:
                bx = 0
                bdir = 1
            if bx > 6:
                bx = 6
                bdir = -1

        # Gegner schiesst (Phase 3: Zangenschuss links und rechts neben sich)
        if ticks_diff(jetzt, t_feuer) >= stufe["boss_feuer"] * PHASEN_FEUER[phase] // 100:
            t_feuer = jetzt
            if phase == 2:
                for sx in (bx - 1, bx + 2):
                    if 0 <= sx <= 7:
                        bschuesse.append([sx, 4])
            else:
                bschuesse.append([bx + random.randint(0, 1), 4])

        # Schüsse des Gegners bewegen
        if ticks_diff(jetzt, t_bschuss) >= stufe["boss_schuss_ms"]:
            t_bschuss = jetzt
            for b in bschuesse:
                b[1] -= 1

        # Schüsse fangen sich gegenseitig ab
        for s in schuesse[:]:
            for b in bschuesse[:]:
                if s[0] == b[0] and s[1] >= b[1] and b[1] >= 2:
                    schuesse.remove(s)
                    bschuesse.remove(b)
                    break

        # Hat der Gegner dich getroffen?
        neu = []
        getroffen = False
        for b in bschuesse:
            if b[1] < 0:
                continue                      # Schuss ist vorbei
            if b[1] <= 1 and px <= b[0] <= px + 1:
                getroffen = True
            else:
                neu.append(b)
        bschuesse = neu
        if getroffen:
            leben -= 1
            if leben <= 0:
                explosion(px, 0)
                return False
            zeige_leben(leben)
            schuesse = []
            bschuesse = []
            jetzt = ticks_ms()
            t_move = t_schuss = t_boss = t_feuer = t_bschuss = jetzt

        # Zeichnen
        loeschen()
        anzeige = (hp * 8 + hp_max - 1) // hp_max      # Leben des Gegners oben
        for x in range(anzeige):
            punkt(x, 7, rivale["koerper"])
        if ticks_diff(blink_bis, jetzt) > 0:
            bk = TREFFER_FARBE
            bf = TREFFER_FARBE
        else:
            bk = rivale["koerper"]
            bf = rivale["front"]
        for dx in range(2):                            # Gegner: 2 breit, 2 hoch
            punkt(bx + dx, 6, bk)
            punkt(bx + dx, 5, bf)
        for s in schuesse:
            punkt(s[0], s[1], GELB)
        for b in bschuesse:
            punkt(b[0], b[1], HINDERNIS)
        punkt(px, 0, zug["koerper"])                   # dein Zug
        punkt(px + 1, 0, zug["koerper"])
        punkt(px, 1, zug["front"])
        punkt(px + 1, 1, zug["koerper"])
        np.write()
        sleep_ms(20)

# ---------- HAUPTPROGRAMM ----------
intro()
while True:
    zug_nr = menue()
    zug = ZUEGE[zug_nr]
    rivale = ZUEGE[(zug_nr + 1) % len(ZUEGE)]       # der andere Zug ist dein Gegner
    stufe_nr = schwierigkeit_menue()
    stufe = SCHWIERIGKEITEN[stufe_nr]
    spielzeit = 0                                   # Zeitmessung startet neu

    # Runde 1: Hindernissen ausweichen
    while True:
        ampel()
        if messen(spiel, zug, stufe):
            blitz(GRUEN, 3)
            break
        sleep_ms(300)                               # (Explosion lief schon)

    # Runde 2: Snake
    laufschrift(TEXT_RUNDE2, RUNDE2_FARBE)
    while True:
        ampel()
        if messen(snake, zug, stufe):
            blitz(GRUEN, 3)
            break
        sleep_ms(300)

    # Runde 3: Rennen (vorher der Spott-Text, Hineindrücken überspringt ihn)
    laufschrift(TEXT_RUNDE3, RUNDE3_FARBE, TEXT_TEMPO_LANG_MS, True)
    while True:
        ampel()
        if messen(rennen, zug, rivale, stufe):
            blitz(GRUEN, 3)
            break
        blitz(ROT, 3)                               # Gegner war schneller
        sleep_ms(300)

    # Runde 4: Endkampf in drei Phasen
    laufschrift(TEXT_RUNDE4, RUNDE4_FARBE)
    while True:
        ampel()
        if messen(endkampf, zug, rivale, stufe):
            blitz(GRUEN, 3)
            laufschrift(TEXT_ENDE, GRUEN)
            zeige_zeit(stufe_nr)                    # Spielzeit und Bestzeit
            break                                   # zurück ins Menü
        sleep_ms(300)