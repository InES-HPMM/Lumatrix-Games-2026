# Vier gewinnt :)
# Im Menü wählst du zwei Spieler oder eine Computerstufe, das Spiel startet sofort.
# Ein kurzer Druck überspringt das Intro, ein langer öffnet im Spiel das Menü.

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms, ticks_ms, ticks_diff
import random

# ---------- Einstellbare Werte ----------
SPALTEN = 8               # 4 bis 8
SPIELREIHEN = 7           # 4 bis 7
FALLZEIT_MS = 90
BLINKZEIT_MS = 350
ENTPRELLZEIT_MS = 30
MENUE_HALTEZEIT_MS = 1200
PAUSE_MS = 10

INTRO_FALL_MS = 1300
INTRO_WIRBEL_MS = 1400
INTRO_VIER_MS = 1500
INTRO_FALLSCHRITT_MS = 60
INTRO_WIRBELSCHRITT_MS = 40
INTRO_VIER_EINBLEND_MS = 600
INTRO_WIRBEL_AUSBLEND_MS = 400
UEBERBLENDZEIT_MS = 600

KI_BEDENKZEIT_MS = 350
KI_TIEFE = 4
KI_ZEITLIMIT_MS = 1800
KI_PORTION_MS = 5

AUS = (0, 0, 0)
FARBEN = (AUS, (50, 0, 0), (0, 0, 50))
FARBE_VOLL = (12, 12, 12)
FARBE_WEISS = (20, 20, 20)
FARBE_DUNKEL = (2, 2, 2)

# ---------- Hardware ----------
np = NeoPixel(Pin(19, Pin.OUT), 64)

rechts = Pin(2, Pin.IN, Pin.PULL_UP)
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
hineindruecken = Pin(8, Pin.IN, Pin.PULL_UP)

tasten = [links, rechts, hoch, runter, hineindruecken]
rohwerte = [taste.value() for taste in tasten]
stabile_werte = rohwerte[:]
wechselzeiten = [ticks_ms()] * len(tasten)

# ---------- Symbole ----------
FIGUR = ("010", "111", "010", "101", "101")

ZAHLEN = (
    (),
    ("010", "110", "010", "010", "111"),
    ("110", "001", "010", "100", "111"),
    ("110", "001", "010", "001", "110")
)

VIER = (
    "1001",
    "1001",
    "1111",
    "0001",
    "0001",
    "0001"
)

# Die 28 Randpunkte für den Farbwirbel
RAND = (
    [(x, 0) for x in range(8)]
    + [(7, y) for y in range(1, 8)]
    + [(x, 7) for x in range(6, -1, -1)]
    + [(0, y) for y in range(6, 0, -1)]
)

# Mittlere Spalten zuerst prüfen
REIHENFOLGE = sorted(
    range(SPALTEN),
    key=lambda x: abs(2 * x - SPALTEN + 1)
)

# Alle möglichen Viererlinien
VIERER = []
for y in range(SPIELREIHEN):
    for x in range(SPALTEN):
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            if (
                0 <= x + 3 * dx < SPALTEN
                and 0 <= y + 3 * dy < SPIELREIHEN
            ):
                VIERER.append([
                    (x + i * dx, y + i * dy) for i in range(4)
                ])

GEWICHTE = (0, 1, 8, 50, 10000)
UNENDLICH = 1000000
SIEGWERT = 100000


def lese_tasten(jetzt):
    gedrueckt = [False] * len(tasten)

    for i in range(len(tasten)):
        wert = tasten[i].value()

        if wert != rohwerte[i]:
            rohwerte[i] = wert
            wechselzeiten[i] = jetzt

        if (
            wert != stabile_werte[i]
            and ticks_diff(jetzt, wechselzeiten[i]) >= ENTPRELLZEIT_MS
        ):
            stabile_werte[i] = wert
            gedrueckt[i] = wert == 0

    return gedrueckt


def pixel(x, y, farbe):
    # Ursprung unten links
    np[y * 8 + x] = farbe


def freie_reihe(brett, x):
    for y in range(SPIELREIHEN):
        if brett[y][x] == 0:
            return y
    return None


def freie_spalten(brett):
    return [
        x for x in REIHENFOLGE
        if brett[SPIELREIHEN - 1][x] == 0
    ]


def finde_gewinnfelder(brett, x, y):
    farbe = brett[y][x]
    treffer = []

    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        linie = [(x, y)]

        for vorzeichen in (-1, 1):
            nx = x + dx * vorzeichen
            ny = y + dy * vorzeichen

            while 0 <= nx < SPALTEN and 0 <= ny < SPIELREIHEN:
                if brett[ny][nx] != farbe:
                    break

                linie.append((nx, ny))
                nx += dx * vorzeichen
                ny += dy * vorzeichen

        if len(linie) >= 4:
            treffer.extend(linie)

    return treffer


def neues_spiel():
    global feld, spieler, spalte, zuege, zustand
    global gewinnfelder, ende_zeit, fall_x, fall_y, ziel_y
    global letzter_fall, ki_start, ki_job, ki_bester_zug

    feld = [[0] * SPALTEN for _ in range(SPIELREIHEN)]
    spieler = 1
    spalte = SPALTEN // 2
    zuege = 0
    zustand = "spiel"
    gewinnfelder = []
    ende_zeit = ticks_ms()

    fall_x = spalte
    fall_y = SPIELREIHEN - 1
    ziel_y = 0
    letzter_fall = ende_zeit

    ki_start = ende_zeit
    ki_job = None
    ki_bester_zug = None


def starte_fall(jetzt):
    global zustand, fall_x, fall_y, ziel_y, letzter_fall

    y = freie_reihe(feld, spalte)

    if y is not None:
        fall_x = spalte
        fall_y = SPIELREIHEN - 1
        ziel_y = y
        letzter_fall = jetzt
        zustand = "fallen"


def aktualisiere_fall(jetzt):
    global fall_y, letzter_fall, spieler, zuege, zustand
    global gewinnfelder, ende_zeit, ki_start, ki_job

    if ticks_diff(jetzt, letzter_fall) < FALLZEIT_MS:
        return

    letzter_fall = jetzt

    if fall_y > ziel_y:
        fall_y -= 1

    if fall_y != ziel_y:
        return

    # Spielzug nach der Landung abschliessen
    feld[ziel_y][fall_x] = spieler
    zuege += 1
    gewinnfelder = finde_gewinnfelder(feld, fall_x, ziel_y)

    if gewinnfelder:
        zustand = "sieg"
        ende_zeit = jetzt

    elif zuege == SPALTEN * SPIELREIHEN:
        zustand = "unentschieden"
        ende_zeit = jetzt

    else:
        spieler = 3 - spieler

        if spieler == 2 and menue_index > 0:
            zustand = "computer"
            ki_start = jetzt
            ki_job = None
        else:
            zustand = "spiel"


# ---------- Computergegner ----------
def bewerte(brett):
    # Positive Werte sind gut für Blau.
    punkte = 0

    for linie in VIERER:
        rot = 0
        blau = 0

        for x, y in linie:
            if brett[y][x] == 1:
                rot += 1
            elif brett[y][x] == 2:
                blau += 1

        if rot == 0:
            punkte += GEWICHTE[blau]
        elif blau == 0:
            punkte -= GEWICHTE[rot]

    return punkte


def sofortzug(brett, farbe):
    # Sofortigen Gewinn oder notwendige Abwehr finden
    for x in freie_spalten(brett):
        y = freie_reihe(brett, x)
        brett[y][x] = farbe
        sieg = bool(finde_gewinnfelder(brett, x, y))
        brett[y][x] = 0

        if sieg:
            return x

    return None


def stellungszug(brett):
    bester_wert = -UNENDLICH
    beste_spalte = None

    for x in freie_spalten(brett):
        y = freie_reihe(brett, x)
        brett[y][x] = 2
        wert = bewerte(brett)
        brett[y][x] = 0

        if wert > bester_wert:
            bester_wert = wert
            beste_spalte = x

    return beste_spalte


def suche(brett, tiefe, alpha, beta, farbe, letzter_zug):
    # Regelmässig zur Hauptschleife zurückkehren
    yield None

    x, y = letzter_zug

    if finde_gewinnfelder(brett, x, y):
        return -SIEGWERT - tiefe

    moeglich = freie_spalten(brett)

    if not moeglich:
        return 0

    if tiefe == 0:
        wert = bewerte(brett)
        return wert if farbe == 2 else -wert

    bester_wert = -UNENDLICH

    for x in moeglich:
        y = freie_reihe(brett, x)
        brett[y][x] = farbe

        wert = yield from suche(
            brett, tiefe - 1, -beta, -alpha, 3 - farbe, (x, y)
        )

        wert = -wert
        brett[y][x] = 0

        bester_wert = max(bester_wert, wert)
        alpha = max(alpha, wert)

        if alpha >= beta:
            break

    return bester_wert


def suche_computerzug(brett):
    global ki_bester_zug

    # Schrittweise tiefer suchen
    for tiefe in range(1, KI_TIEFE + 1):
        bester_wert = -UNENDLICH
        beste_spalte = ki_bester_zug

        for x in freie_spalten(brett):
            y = freie_reihe(brett, x)
            brett[y][x] = 2

            wert = yield from suche(
                brett, tiefe - 1, -UNENDLICH,
                -bester_wert, 1, (x, y)
            )

            wert = -wert
            brett[y][x] = 0

            if wert > bester_wert:
                bester_wert = wert
                beste_spalte = x

        ki_bester_zug = beste_spalte

    yield ki_bester_zug


def computer_setzt(x, jetzt):
    global spalte, ki_job

    ki_job = None
    spalte = x
    starte_fall(jetzt)


def computer_denkt(jetzt):
    global ki_job, ki_bester_zug, zustand, ende_zeit

    if ticks_diff(jetzt, ki_start) < KI_BEDENKZEIT_MS:
        return

    if ki_job is None:
        moeglich = freie_spalten(feld)

        if not moeglich:
            zustand = "unentschieden"
            ende_zeit = jetzt
            return

        if menue_index == 1:
            # Leicht: zufällige freie Spalte
            x = moeglich[random.randint(0, len(moeglich) - 1)]
            computer_setzt(x, ticks_ms())
            return

        # Auf einer Kopie rechnen
        brett = [reihe[:] for reihe in feld]

        zug = sofortzug(brett, 2)
        if zug is None:
            zug = sofortzug(brett, 1)

        if zug is not None:
            computer_setzt(zug, ticks_ms())
            return

        ki_bester_zug = stellungszug(brett)

        if menue_index == 2:
            computer_setzt(ki_bester_zug, ticks_ms())
            return

        ki_job = suche_computerzug(brett)

    anfang = ticks_ms()

    while ticks_diff(ticks_ms(), anfang) < KI_PORTION_MS:
        jetzt = ticks_ms()

        if (
            ticks_diff(jetzt, ki_start)
            >= KI_BEDENKZEIT_MS + KI_ZEITLIMIT_MS
        ):
            computer_setzt(ki_bester_zug, jetzt)
            return

        ergebnis = next(ki_job)

        if ergebnis is not None:
            computer_setzt(ergebnis, ticks_ms())
            return


# ---------- Anzeige ----------
def symbol_zeichnen(symbol, start_x, farbe):
    for zeile in range(5):
        for x in range(3):
            if symbol[zeile][x] == "1":
                pixel(start_x + x, 6 - zeile, farbe)


def zeichne_vier(alter):
    # Mittige Vier: x = 2 bis 5, y = 1 bis 6
    welle = alter % 800

    if welle > 400:
        welle = 800 - welle

    hell = 20 + welle * 30 // 400

    # Schon während des Wirbels sanft erscheinen
    dauer = max(1, INTRO_VIER_EINBLEND_MS)
    hell = hell * min(dauer, max(0, alter)) // dauer

    for zeile in range(6):
        if zeile < 2:
            farbe = (hell, 0, 0)
        elif zeile == 2:
            farbe = (hell, hell, hell)
        else:
            farbe = (0, 0, hell)

        for x in range(4):
            if VIER[zeile][x] == "1":
                pixel(x + 2, 6 - zeile, farbe)


def zeichne_intro(jetzt):
    alter = ticks_diff(jetzt, intro_start)

    if alter < INTRO_FALL_MS:
        # Zeitversetzt fallende Steine
        for x in range(8):
            zeit = alter - x * 100

            if zeit < 0:
                continue

            y = max(0, 7 - zeit // INTRO_FALLSCHRITT_MS)
            farbe = FARBEN[1 + x % 2]

            if 0 < y < 7:
                spur = tuple(wert // 4 for wert in farbe)
                pixel(x, y + 1, spur)

            pixel(x, y, farbe)

        return

    alter -= INTRO_FALL_MS

    # Die Vier bleibt nach dem Wirbel sichtbar.
    zeichne_vier(alter)

    if alter < INTRO_WIRBEL_MS:
        schritt = alter // INTRO_WIRBELSCHRITT_MS
        dauer = max(1, INTRO_WIRBEL_AUSBLEND_MS)
        rest = min(dauer, INTRO_WIRBEL_MS - alter)

        # Den Wirbel am Ende sanft ausblenden
        for spieler_farbe, versatz in ((FARBEN[1], 0), (FARBEN[2], 14)):
            for spur in range(5, -1, -1):
                x, y = RAND[(schritt + versatz - spur) % len(RAND)]
                faktor = 6 - spur

                farbe = tuple(
                    wert * faktor * rest // (6 * dauer)
                    for wert in spieler_farbe
                )

                pixel(x, y, farbe)


def zeichne_inhalt(jetzt, ansicht):
    if ansicht == "intro":
        zeichne_intro(jetzt)
        return

    if ansicht == "menue":
        symbol_zeichnen(FIGUR, 0, FARBEN[1])

        if menue_index == 0:
            symbol_zeichnen(FIGUR, 5, FARBEN[2])
        else:
            symbol_zeichnen(ZAHLEN[menue_index], 5, FARBEN[2])

        for i in range(4):
            farbe = FARBE_WEISS if i == menue_index else FARBE_DUNKEL
            pixel(i + 2, 0, farbe)

        return

    sichtbar = True

    if ansicht in ("sieg", "unentschieden"):
        sichtbar = (
            ticks_diff(jetzt, ende_zeit) // BLINKZEIT_MS
        ) % 2 == 0

    for y in range(SPIELREIHEN):
        for x in range(SPALTEN):
            farbe = FARBEN[feld[y][x]]

            if (
                ansicht == "sieg"
                and (x, y) in gewinnfelder
                and not sichtbar
            ):
                farbe = AUS

            pixel(x, y, farbe)

    if ansicht == "spiel":
        farbe = FARBEN[spieler]

        if feld[SPIELREIHEN - 1][spalte] != 0:
            farbe = FARBE_VOLL

        pixel(spalte, 7, farbe)

    elif ansicht == "fallen":
        pixel(fall_x, fall_y, FARBEN[spieler])

    elif ansicht == "computer":
        x = (ticks_diff(jetzt, ki_start) // 100) % SPALTEN
        pixel(x, 7, FARBEN[2])

    elif ansicht == "sieg":
        for x in range(SPALTEN):
            pixel(x, 7, FARBEN[spieler])

    elif ansicht == "unentschieden" and sichtbar:
        for x in range(SPALTEN):
            pixel(x, 7, FARBE_WEISS)


def starte_uebergang(ziel, jetzt):
    global zustand, uebergang_ziel, uebergang_start, uebergang_bild

    uebergang_bild = [np[i] for i in range(64)]
    uebergang_ziel = ziel
    uebergang_start = jetzt
    zustand = "uebergang"


def zeichnen(jetzt):
    np.fill(AUS)

    if zustand == "uebergang":
        zeichne_inhalt(jetzt, uebergang_ziel)

        zeit = max(0, ticks_diff(jetzt, uebergang_start))
        anteil = min(256, zeit * 256 // max(1, UEBERBLENDZEIT_MS))

        # Sanft beginnen und sanft auslaufen
        anteil = anteil * anteil * (768 - 2 * anteil) // 65536

        for i in range(64):
            vorher = uebergang_bild[i]
            nachher = np[i]

            np[i] = tuple(
                (vorher[k] * (256 - anteil) + nachher[k] * anteil) // 256
                for k in range(3)
            )

    else:
        zeichne_inhalt(jetzt, zustand)

    np.write()


# ---------- Start und Hauptschleife ----------
menue_index = 0           # 0: zu zweit, 1/2/3: Computerstufe
neues_spiel()

zustand = "intro"
intro_start = ticks_ms()
uebergang_start = intro_start
uebergang_ziel = "menue"
uebergang_bild = [AUS] * 64

druck_start = ticks_ms()
druck_begonnen = False
lang_druck = False

while True:
    jetzt = ticks_ms()
    links_neu, rechts_neu, hoch_neu, runter_neu, druck_neu = lese_tasten(jetzt)

    # Kurzen Druck erst beim Loslassen auslösen
    kurz_druck = False

    if druck_neu:
        druck_start = jetzt
        druck_begonnen = True
        lang_druck = False

    if stabile_werte[4] == 1 and druck_begonnen:
        kurz_druck = not lang_druck
        druck_begonnen = False

    elif (
        druck_begonnen and not lang_druck
        and ticks_diff(jetzt, druck_start) >= MENUE_HALTEZEIT_MS
    ):
        zustand = "menue"
        ki_job = None
        lang_druck = True

    if zustand == "intro":
        dauer = INTRO_FALL_MS + INTRO_WIRBEL_MS + INTRO_VIER_MS

        if kurz_druck or ticks_diff(jetzt, intro_start) >= dauer:
            starte_uebergang("menue", jetzt)

    elif zustand == "uebergang":
        if ticks_diff(jetzt, uebergang_start) >= UEBERBLENDZEIT_MS:
            zustand = uebergang_ziel

    elif zustand == "menue":
        if hoch_neu or links_neu:
            menue_index = (menue_index - 1) % 4
        elif runter_neu or rechts_neu:
            menue_index = (menue_index + 1) % 4

        if kurz_druck:
            # Gewählten Spielmodus sofort starten
            neues_spiel()

    elif zustand == "spiel":
        if links_neu:
            spalte = (spalte - 1) % SPALTEN
        elif rechts_neu:
            spalte = (spalte + 1) % SPALTEN

        if kurz_druck:
            starte_fall(jetzt)

    elif zustand == "fallen":
        aktualisiere_fall(jetzt)

    elif zustand == "computer":
        computer_denkt(jetzt)

    elif kurz_druck:
        neues_spiel()

    zeichnen(ticks_ms())
    sleep_ms(PAUSE_MS)