# Lied-Visualisierung mit 8 Szenen für die Lumatrix (8x8 WS2812B am Raspberry Pi Pico)
# Das Programm liest die .lum-Dateien, die dein Laptop aus MP3s erzeugt hat, und zeigt das Lied in 8 Szenen:
# Equalizer, Kreis, Farbmischer, Ringe, Peak-Hold, Sonne, Spirale und Feuerwerk. Alle Farben, Tempi und Größen stehen oben in den Einstellungen.
# Joystick: links/rechts = Lied wählen, hineindrücken = starten (nach dem Countdown das Lied abspielen) oder stoppen,
# hoch/runter = nächste/vorherige Szene.
# Schalter: Ist er beim Ende eines Liedes umgelegt, startet automatisch das nächste Lied der Liste.
# Beim Umlegen läuft außerdem ein Text über die Matrix: "PLAYLIST" für den Playlist-Modus, "SINGLE" für einzelne Lieder.

from machine import Pin
from neopixel import NeoPixel
import utime
import math
import random
from lieder_index import LIEDER   # vom Laptop erzeugt: (Name, Datei, Farbe, BPM)

# ---------- Einstellungen (hier kannst du leicht etwas ändern) ----------
SZENEN = ("Equalizer", "Kreis", "Farbmischer", "Ringe", "Peak-Hold", "Sonne", "Spirale", "Feuerwerk")
START_SZENE = 0               # 0 = Equalizer, 1 = Kreis, 2 = Farbmischer, 3 = Ringe, 4 = Peak-Hold, 5 = Sonne,
                              # 6 = Spirale, 7 = Feuerwerk
SZENEN_ANZEIGE_MS = 800       # so lange (ms) zeigen die unteren Zeilen nach dem Wechsel die Szenen-Nummer
MAX_WERT = 60                 # größter Farbwert pro Farbkanal (nicht zu hell)

# Allgemein (Equalizer, Kreis, Farbmischer, Peak-Hold, Sonne, Spirale)
GRUNDHELL = 0.45              # Helligkeit ohne Beat (0 bis 1), beim Beat springt sie auf 1
BEAT_SCHWELLE = 0.3           # Beat-Stärke (0 bis 1), ab der ein Beat zählt; höher = nur starke Schläge
BEAT_ABKLINGEN = 0.75         # kleiner = Beat-Blitz klingt schneller ab
ABFALL = 40                   # wie schnell Balken pro Bild fallen (0 bis 255)

# Equalizer und Peak-Hold
BALKEN_UNTEN = (0, 45, 5)     # Farbe der untersten Zeile (grün)
BALKEN_OBEN = (60, 0, 0)      # Farbe der obersten Zeile (rot)

# Kreis (und Palette für Ringe, Spirale, Feuerwerk):
# Farbe der 8 Frequenzbereiche, tief bis hoch (beim Kreis im Uhrzeigersinn, oben links beginnend)
KREIS_FARBEN = [(60, 0, 0), (60, 25, 0), (50, 50, 0), (0, 60, 0),
                (0, 50, 40), (0, 20, 60), (25, 0, 60), (55, 0, 35)]
KREIS_RADIUS = 4.2            # Größe des Kreises (Pixel); kleiner = Ecken bleiben dunkel
FUELL_EMPFINDLICHKEIT = 1.3   # größer = die Diagonalen füllen sich schneller
FUELL_HELL = 0.6              # Helligkeit der Füllung im Verhältnis zu den Strahlen

# Farbmischer: Farbe für tiefe, mittlere und hohe Töne
FARBE_BASS = (60, 0, 0)       # rot
FARBE_MITTE = (0, 60, 0)      # grün
FARBE_HOEHE = (0, 0, 60)      # blau
MISCH_KONTRAST = 2            # 1 = weich, 2 = deutlicher, 3 = nur starke Töne zeigen Farbe
BEAT_ANTEIL = 0.5             # wie stark die Fläche beim Beat aufblitzt (0 bis 1)

# Ringe
RING_TEMPO = 9                # wie schnell ein Ring nach außen läuft (Pixel pro Sekunde)
RING_DICKE = 1.0              # Dicke des Rings
RING_MAX_RADIUS = 6.0         # ab dieser Größe verschwindet der Ring
RING_ABSTAND_MS = 150         # kleinster Abstand zwischen zwei Ringen
MAX_RINGE = 4                 # so viele Ringe gleichzeitig

# Peak-Hold: der Punkt über jedem Balken
PEAK_FARBE = (60, 60, 60)     # Farbe des Punktes (weiß)
PEAK_HALTEN_MS = 400          # so lange (ms) bleibt der Punkt oben stehen
PEAK_SINKEN = 6               # danach sinkt er so schnell (Pixel pro Sekunde)

# Sonne: drei Scheiben ineinander
SONNE_FARBEN = ((60, 50, 0), (60, 20, 0), (45, 0, 15))   # innen (Bass), Mitte (Mitten), außen (Höhen)
SONNE_RADIEN = (1.8, 3.0, 4.2)    # größte Radien von innen nach außen (Pixel)
SONNE_MIN = 0.4               # Anteil der Größe, der bei Stille übrig bleibt (0 bis 1)
SONNE_VERSTAERKUNG = 1.5      # größer = die Scheiben wachsen schon bei leiseren Tönen
SONNE_BEAT_SCHWELLEN = 0.25   # wie stark alles beim Beat anschwillt (0.25 = ein Viertel größer)

# Spirale: 8 Arme drehen sich
SPIRALE_LAENGE = 4.5          # Länge eines Arms bei voller Lautstärke (Pixel)
SPIRALE_KRUMM = 0.25          # Krümmung der Arme (0 = gerade Strahlen)
SPIRALE_TEMPO_LEISE = 0.4     # Drehtempo bei leiser Musik (Radiant pro Sekunde)
SPIRALE_TEMPO_LAUT = 4.0      # Drehtempo bei lauter Musik
SPIRALE_VERSTAERKUNG = 2.0    # größer = dreht schon bei leiserer Musik schnell

# Feuerwerk
FEUER_TEMPO = 16              # Steiggeschwindigkeit der Rakete (Zeilen pro Sekunde)
FEUER_RING_RADIUS = 2.0       # Größe des Rings nach der Explosion (Pixel)
FEUER_EXPLOSION_MS = 500      # so lange (ms) leuchtet die Explosion
FEUER_ABSTAND_MS = 200        # kleinster Abstand zwischen zwei Raketen
MAX_RAKETEN = 3               # so viele Raketen gleichzeitig unterwegs

# Ablauf
MIN_HELL = 0.03               # Grundhelligkeit in der Liedauswahl und im Countdown
AUDIO_VERSATZ_MS = 0          # Kommt der Ton später (z. B. Bluetooth-Lautsprecher)? Dann hier ms eintragen
COUNTDOWN_ZEIT_MS = 1000      # Abstand zwischen den drei Countdown-Blitzen
PAUSE_MS = 5                  # Pause pro Schleifendurchgang

# Automatik-Schalter (Lieder nacheinander abspielen)
SCHALTER_PIN = 9              # GPIO, an dem der Schalter hängt (andere Seite des Schalters an GND)
SCHALTER_AN_WERT = 0          # 0 = Automatik an, wenn der Schalter geschlossen ist; 1 = umgekehrt
AUTO_PAUSE_MS = 1500          # Pause (ms) zwischen zwei Liedern, bevor das nächste startet
AUTO_ENDLOS = False           # False = nach dem letzten Lied Schluss, True = wieder beim ersten anfangen
LAUFTEXT = "PLAYLIST"         # Text, der beim Umlegen auf Playlist-Modus durchläuft (nur Buchstaben aus BUCHSTABEN)
LAUFTEXT_FARBE = (0, 40, 40)  # Farbe des Lauftextes PLAYLIST
LAUFTEXT_EINZEL = "SINGLE"    # Text, der beim Zurücklegen auf einzelne Lieder durchläuft
LAUFTEXT_EINZEL_FARBE = (45, 25, 0)   # Farbe des Lauftextes SINGLE (orange)
LAUFTEXT_TEMPO = 10           # so viele Spalten läuft der Text pro Sekunde

# ---------- Hardware ----------
np = NeoPixel(Pin(19, Pin.OUT), 64)
rechts = Pin(2, Pin.IN, Pin.PULL_UP)
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
hineindruecken = Pin(8, Pin.IN, Pin.PULL_UP)
schalter = Pin(SCHALTER_PIN, Pin.IN, Pin.PULL_UP)

# Zustand der Taster im letzten Durchgang (1 = nicht gedrückt)
alt = [1, 1, 1, 1, 1]

def neu_gedrueckt(taster, nr):
    # Gibt nur im Moment des Drückens True zurück (Wechsel 1 -> 0)
    wert = taster.value()
    war = alt[nr]
    alt[nr] = wert
    return wert == 0 and war == 1

def zeige(farbe, hell):
    # Ganze Matrix in einer Farbe mit Helligkeit 0 bis 1
    r, g, b = farbe
    np.fill((int(r * hell), int(g * hell), int(b * hell)))

def addiere(x, y, farbe, w):
    # Farbe mit Gewicht w (0 bis 1) zu einem Pixel dazumischen
    if w <= 0:
        return
    if w > 1:
        w = 1
    r, g, b = np[y * 8 + x]
    np[y * 8 + x] = (min(MAX_WERT, r + int(farbe[0] * w)),
                     min(MAX_WERT, g + int(farbe[1] * w)),
                     min(MAX_WERT, b + int(farbe[2] * w)))

def punkt(x, y, farbe, w):
    # Wie addiere, aber Pixel außerhalb der Matrix werden ignoriert
    if 0 <= x < 8 and 0 <= y < 8:
        addiere(x, y, farbe, w)

def mische(i, farbe, w):
    # Pixel i (Nummer 0 bis 63) zum Anteil w in Richtung Farbe überblenden (überdeckt, was dahinter war)
    if w <= 0:
        return
    if w > 1:
        w = 1
    r, g, b = np[i]
    np[i] = (int(r + (farbe[0] - r) * w), int(g + (farbe[1] - g) * w), int(b + (farbe[2] - b) * w))

def pegel(glatt):
    # Lautstärke (0 bis 1) von Bass (Bänder 0+1), Mitten (2 bis 4), Höhen (5 bis 7) und insgesamt
    bass = (glatt[0] + glatt[1]) / 510
    mitte = (glatt[2] + glatt[3] + glatt[4]) / 765
    hoehe = (glatt[5] + glatt[6] + glatt[7]) / 765
    gesamt = sum(glatt) / 2040
    return bass, mitte, hoehe, gesamt

# Abstand jedes Pixels zur Mitte der Matrix (Index = y * 8 + x)
DIST = [math.sqrt((x - 3.5) ** 2 + (y - 3.5) ** 2) for y in range(8) for x in range(8)]

# Farbe jeder Zeile für den Equalizer vorberechnen (Verlauf von unten nach oben)
ZEILENFARBEN = []
for y in range(8):
    f = y / 7
    ZEILENFARBEN.append(tuple(BALKEN_UNTEN[k] + (BALKEN_OBEN[k] - BALKEN_UNTEN[k]) * f for k in range(3)))

# Die vier Viertel des Kreises:
# (Eckpixel x, Eckpixel y, Richtung x, Richtung y, Band des senkrechten Strahls, Band des waagerechten Strahls)
# Die Bänder 0 bis 7 laufen im Uhrzeigersinn: oben 0+1, rechts 2+3, unten 4+5, links 6+7
VIERTEL = (
    (3, 4, -1, 1, 0, 7),    # oben links
    (4, 4, 1, 1, 1, 2),     # oben rechts
    (4, 3, 1, -1, 4, 3),    # unten rechts
    (3, 3, -1, -1, 5, 6),   # unten links
)

# Schrift für den Lauftext: jeder Buchstabe 5 Spalten breit und 7 Zeilen hoch (# = leuchtet)
# Eigene Buchstaben kannst du hier ergänzen, sieben Zeilen pro Buchstabe.
BUCHSTABEN = {
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
}

def baue_text(text):
    # Text in eine Liste von Spalten umwandeln (Bit 0 = oberste Zeile, Bit 6 = unterste Textzeile)
    spalten = []
    for z in text:
        zeilen = BUCHSTABEN.get(z)
        if zeilen is None:
            spalten += [0, 0, 0]            # unbekanntes Zeichen = Lücke
            continue
        for x in range(len(zeilen[0])):
            wert = 0
            for y in range(7):
                if zeilen[y][x] == "#":
                    wert = wert | (1 << y)
            spalten.append(wert)
        spalten.append(0)                   # eine leere Spalte zwischen den Buchstaben
    return spalten

LAUFTEXT_SPALTEN = baue_text(LAUFTEXT)
LAUFTEXT_EINZEL_SPALTEN = baue_text(LAUFTEXT_EINZEL)

# ---------- Zustand der Szenen (wird beim Szenenwechsel und beim Start zurückgesetzt) ----------
ringe = []                          # Ringe: (Startzeit, Farbe)
peak = [0.0] * 8                    # Peak-Hold: Höhe des Punktes pro Spalte (in Pixeln)
peak_zeit = [0] * 8                 # Peak-Hold: wann der Punkt zuletzt nach oben gesprungen ist
spirale = [0.0]                     # Spirale: [aktueller Drehwinkel]
raketen = []                        # Feuerwerk: [Spalte, Höhe, Zielhöhe, Band]
explosionen = []                    # Feuerwerk: [Spalte, Höhe, Startzeit, Band]
feuer_letzte = [0]                  # Feuerwerk: Zeit der letzten Rakete

def reset_szenen(jetzt):
    # Alle Szenen auf Anfang setzen
    ringe.clear()
    for i in range(8):
        peak[i] = 0.0
        peak_zeit[i] = jetzt
    spirale[0] = 0.0
    raketen.clear()
    explosionen.clear()
    feuer_letzte[0] = jetzt

# ---------- Szenen ----------
def zeige_equalizer(glatt, beat_hell):
    # Jede Spalte ist ein Frequenzbereich, die Höhe zeigt die Lautstärke
    np.fill((0, 0, 0))
    faktor = GRUNDHELL + (1 - GRUNDHELL) * beat_hell
    for x in range(8):
        h = glatt[x] * 8 / 255
        for y in range(8):
            if h >= y + 1:
                hell = 1.0
            elif h > y:
                hell = h - y       # oberste Zeile leuchtet nur teilweise
            else:
                break
            r, g, b = ZEILENFARBEN[y]
            hell = hell * faktor
            np[y * 8 + x] = (int(r * hell), int(g * hell), int(b * hell))

def zeige_kreis(glatt, beat_hell):
    # 8 Strahlen von der Mitte nach außen; die Diagonalen füllen sich, wenn beide Nachbarbänder laut sind
    np.fill((0, 0, 0))
    faktor = GRUNDHELL + (1 - GRUNDHELL) * beat_hell
    for cx, cy, dx, dy, bv, bh in VIERTEL:
        lv = glatt[bv] / 255
        lh = glatt[bh] / 255
        fv = KREIS_FARBEN[bv]
        fh = KREIS_FARBEN[bh]
        # Strahlen: je 4 Pixel lang (der Eckpixel gehört zu beiden Strahlen und mischt ihre Farben)
        for d in range(4):
            addiere(cx, cy + dy * d, fv, (lv * 4 - d) * faktor)
            addiere(cx + dx * d, cy, fh, (lh * 4 - d) * faktor)
        # Füllung der Diagonale: wächst kreisförmig, je lauter das leisere der beiden Bänder ist
        reichweite = min(lv, lh) * FUELL_EMPFINDLICHKEIT * KREIS_RADIUS
        farbe = ((fv[0] + fh[0]) // 2, (fv[1] + fh[1]) // 2, (fv[2] + fh[2]) // 2)
        for i in range(1, 4):
            for j in range(1, 4):
                x = cx + dx * i
                y = cy + dy * j
                abstand = DIST[y * 8 + x]
                if abstand <= KREIS_RADIUS:
                    addiere(x, y, farbe, (reichweite - abstand + 1) * FUELL_HELL * faktor)

def zeige_farbmischer(glatt, beat_hell):
    # Ganze Fläche: Farbe aus tiefen (rot), mittleren (grün) und hohen Tönen (blau), Blitz bei Beats
    bass = ((glatt[0] + glatt[1]) / 510) ** MISCH_KONTRAST
    mitte = ((glatt[2] + glatt[3] + glatt[4]) / 765) ** MISCH_KONTRAST
    hoehe = ((glatt[5] + glatt[6] + glatt[7]) / 765) ** MISCH_KONTRAST
    faktor = (1 - BEAT_ANTEIL) + BEAT_ANTEIL * beat_hell
    kanal = []
    for k in range(3):
        wert = FARBE_BASS[k] * bass + FARBE_MITTE[k] * mitte + FARBE_HOEHE[k] * hoehe
        kanal.append(min(MAX_WERT, int(wert * faktor)))
    np.fill((kanal[0], kanal[1], kanal[2]))

def zeige_ringe(jetzt):
    # Jeder Beat startet einen Ring in der Mitte, der nach außen läuft und verblasst
    np.fill((0, 0, 0))
    for startzeit, farbe in ringe:
        radius = utime.ticks_diff(jetzt, startzeit) * RING_TEMPO / 1000
        hell = 1 - radius / RING_MAX_RADIUS
        if hell <= 0:
            continue
        for i in range(64):
            abstand = abs(DIST[i] - radius)
            if abstand < RING_DICKE:
                w = (1 - abstand / RING_DICKE) * hell
                r, g, b = np[i]
                np[i] = (min(MAX_WERT, r + int(farbe[0] * w)),
                         min(MAX_WERT, g + int(farbe[1] * w)),
                         min(MAX_WERT, b + int(farbe[2] * w)))

def zeige_peak(glatt, beat_hell, dt, jetzt):
    # Equalizer, aber über jedem Balken bleibt ein Punkt kurz am höchsten Wert stehen und sinkt dann langsam
    zeige_equalizer(glatt, beat_hell)
    for x in range(8):
        h = glatt[x] * 8 / 255
        if h >= peak[x]:
            peak[x] = h                       # Balken hat den Punkt eingeholt: Punkt springt mit nach oben
            peak_zeit[x] = jetzt
        elif utime.ticks_diff(jetzt, peak_zeit[x]) > PEAK_HALTEN_MS:
            peak[x] = max(h, peak[x] - PEAK_SINKEN * dt)    # nach der Haltezeit langsam sinken
        if peak[x] >= 0.5:
            y = int(peak[x])
            if y > 7:
                y = 7
            np[y * 8 + x] = PEAK_FARBE

def zeige_sonne(glatt, beat_hell):
    # Drei Scheiben ineinander: innen Bass, Mitte Mitten, außen Höhen; ein Beat lässt alles anschwellen
    bass, mitte, hoehe, gesamt = pegel(glatt)
    faktor = GRUNDHELL + (1 - GRUNDHELL) * beat_hell
    schwell = 1 + SONNE_BEAT_SCHWELLEN * beat_hell
    np.fill((0, 0, 0))
    # außen zuerst zeichnen, die inneren Scheiben liegen dann darüber
    for wert, k in ((hoehe, 2), (mitte, 1), (bass, 0)):
        pw = min(1.0, wert * SONNE_VERSTAERKUNG)
        radius = SONNE_RADIEN[k] * (SONNE_MIN + (1 - SONNE_MIN) * pw) * schwell
        f = SONNE_FARBEN[k]
        farbe = (int(f[0] * faktor), int(f[1] * faktor), int(f[2] * faktor))
        for i in range(64):
            mische(i, farbe, radius - DIST[i] + 0.5)    # weicher Rand

def zeige_spirale(glatt, beat_hell, dt):
    # 8 Arme (ein Arm pro Frequenzbereich) drehen sich; Länge = Lautstärke, Drehtempo = Gesamtlautstärke
    bass, mitte, hoehe, gesamt = pegel(glatt)
    pw = min(1.0, gesamt * SPIRALE_VERSTAERKUNG)
    tempo = SPIRALE_TEMPO_LEISE + (SPIRALE_TEMPO_LAUT - SPIRALE_TEMPO_LEISE) * pw
    spirale[0] = (spirale[0] + tempo * dt) % (2 * math.pi)
    faktor = GRUNDHELL + (1 - GRUNDHELL) * beat_hell
    np.fill((0, 0, 0))
    for arm in range(8):
        laenge = 0.8 + glatt[arm] / 255 * SPIRALE_LAENGE
        f = KREIS_FARBEN[arm]
        farbe = (int(f[0] * faktor), int(f[1] * faktor), int(f[2] * faktor))
        winkel0 = spirale[0] + arm * math.pi / 4
        s = 0.5
        while s <= laenge:
            a = winkel0 + s * SPIRALE_KRUMM       # nach außen dreht sich der Arm weiter: Spirale
            x = math.floor(4 + math.cos(a) * s)
            y = math.floor(4 + math.sin(a) * s)
            if 0 <= x < 8 and 0 <= y < 8:
                np[y * 8 + x] = farbe
            s += 0.5

def zeige_feuerwerk(glatt, dt, jetzt, neuer_beat):
    # Ein Beat schießt eine Rakete in der Spalte des lautesten Bereichs nach oben; oben explodiert sie zu einem Ring
    if neuer_beat and len(raketen) < MAX_RAKETEN and utime.ticks_diff(jetzt, feuer_letzte[0]) > FEUER_ABSTAND_MS:
        band = glatt.index(max(glatt))
        raketen.append([band, 0.0, random.randint(4, 6), band])
        feuer_letzte[0] = jetzt
    np.fill((0, 0, 0))
    nr = 0
    while nr < len(raketen):
        ra = raketen[nr]
        ra[1] += FEUER_TEMPO * dt
        if ra[1] >= ra[2]:
            explosionen.append([ra[0], ra[2], jetzt, ra[3]])
            raketen.pop(nr)
        else:
            farbe = KREIS_FARBEN[ra[3]]
            y = int(ra[1])
            punkt(ra[0], y, farbe, 1)
            punkt(ra[0], y - 1, farbe, 0.35)           # kurzer Schweif
            nr += 1
    nr = 0
    while nr < len(explosionen):
        ex = explosionen[nr]
        t = utime.ticks_diff(jetzt, ex[2]) / FEUER_EXPLOSION_MS
        if t >= 1:
            explosionen.pop(nr)
        else:
            radius = FEUER_RING_RADIUS * (0.3 + 0.7 * t)    # Ring wächst und verblasst
            farbe = KREIS_FARBEN[ex[3]]
            for x in range(ex[0] - 3, ex[0] + 4):
                for y in range(ex[1] - 3, ex[1] + 4):
                    if 0 <= x < 8 and 0 <= y < 8:
                        abstand = math.sqrt((x - ex[0]) ** 2 + (y - ex[1]) ** 2)
                        d = abs(abstand - radius)
                        if d < 0.8:
                            addiere(x, y, farbe, (1 - d / 0.8) * (1 - t))
            nr += 1

# ---------- Startwerte ----------
modus = "wahl"        # "wahl", "lauftext", "countdown" oder "spielen"
lied_nr = 0
szene = START_SZENE
szene_anzeige_bis = utime.ticks_ms()
datei = None          # geöffnete .lum-Datei
start = utime.ticks_ms()
fps = 25
bytes_pro_bild = 9
gelesen = 0           # Anzahl bisher gelesener Bilder
glatt = [0.0] * 8     # geglättete Balkenhöhen
beat_hell = 0.0
vorher_b = 0.0        # Beat-Stärke im vorigen Bild (um den Beginn eines Beats zu erkennen)
letzter_ring = utime.ticks_ms()
vorige_zeit = utime.ticks_ms()          # für die Zeit zwischen zwei Durchgängen (dt)
vorlauf = 3 * COUNTDOWN_ZEIT_MS         # Dauer bis zum Start des Liedes (Countdown oder Pause bei der Automatik)
blitze = True                           # True = Countdown mit Blitzen, False = Pause zwischen Liedern
schalter_alt = schalter.value()         # Stellung des Schalters im letzten Durchgang
lauf_pos = 0.0                          # Lauftext: wie weit der Text schon gelaufen ist (in Spalten)
lauf_spalten = LAUFTEXT_SPALTEN         # Lauftext: der gerade laufende Text
lauf_farbe = LAUFTEXT_FARBE             # Lauftext: seine Farbe
reset_szenen(utime.ticks_ms())
print("Lied:", LIEDER[lied_nr][0], "-", LIEDER[lied_nr][3], "BPM | Szene:", SZENEN[szene])

while True:
    jetzt = utime.ticks_ms()
    dt = utime.ticks_diff(jetzt, vorige_zeit) / 1000   # Sekunden seit dem letzten Durchgang
    vorige_zeit = jetzt
    if dt > 0.1:
        dt = 0.1

    # Taster einlesen (jeden Taster genau einmal pro Durchgang)
    k_rechts = neu_gedrueckt(rechts, 0)
    k_hoch = neu_gedrueckt(hoch, 1)
    k_runter = neu_gedrueckt(runter, 2)
    k_links = neu_gedrueckt(links, 3)
    k_mitte = neu_gedrueckt(hineindruecken, 4)

    # Szene wechseln (hoch = nächste, runter = vorherige)
    if k_hoch or k_runter:
        if k_hoch:
            szene = (szene + 1) % len(SZENEN)
        else:
            szene = (szene - 1) % len(SZENEN)
        szene_anzeige_bis = utime.ticks_add(jetzt, SZENEN_ANZEIGE_MS)
        reset_szenen(jetzt)
        print("Szene:", SZENEN[szene])

    # Schalter beobachten: beim Umlegen (in der Liedauswahl) läuft PLAYLIST bzw. SINGLE durch
    schalter_neu = schalter.value()
    if schalter_neu != schalter_alt:
        if modus == "wahl":
            if schalter_neu == SCHALTER_AN_WERT:
                lauf_spalten = LAUFTEXT_SPALTEN
                lauf_farbe = LAUFTEXT_FARBE
            else:
                lauf_spalten = LAUFTEXT_EINZEL_SPALTEN
                lauf_farbe = LAUFTEXT_EINZEL_FARBE
            modus = "lauftext"
            lauf_pos = -8.0                 # Text beginnt rechts außerhalb der Matrix
        schalter_alt = schalter_neu

    name, pfad, farbe, bpm = LIEDER[lied_nr]

    if modus == "wahl":
        if k_rechts:
            lied_nr = (lied_nr + 1) % len(LIEDER)
            print("Lied:", LIEDER[lied_nr][0], "-", LIEDER[lied_nr][3], "BPM")
        if k_links:
            lied_nr = (lied_nr - 1) % len(LIEDER)
            print("Lied:", LIEDER[lied_nr][0], "-", LIEDER[lied_nr][3], "BPM")
        if k_mitte:
            modus = "countdown"
            start = jetzt
            vorlauf = 3 * COUNTDOWN_ZEIT_MS
            blitze = True

        # Anzeige: dunkle Farbe des Liedes, obere Zeile zeigt die Position (bei mehr als 8 Liedern wiederholt)
        zeige(farbe, MIN_HELL)
        for i in range(8):
            if i == lied_nr % 8:
                np[7 * 8 + i] = (60, 60, 60)
            else:
                np[7 * 8 + i] = (4, 4, 4)
        if schalter.value() == SCHALTER_AN_WERT:
            np[0] = (0, 40, 0)                # grüner Punkt unten links: Automatik ist an

    elif modus == "lauftext":
        # Text läuft von rechts nach links; ein Druck auf den Joystick bricht ihn ab
        lauf_pos = lauf_pos + LAUFTEXT_TEMPO * dt
        erste = math.floor(lauf_pos)        # welche Textspalte gerade ganz links steht
        if k_mitte or erste >= len(lauf_spalten):
            modus = "wahl"
        else:
            np.fill((0, 0, 0))
            for sx in range(8):
                idx = erste + sx
                if 0 <= idx < len(lauf_spalten):
                    wert = lauf_spalten[idx]
                    for zeile in range(7):
                        if wert & (1 << zeile):
                            np[(7 - zeile) * 8 + sx] = lauf_farbe    # Zeile 0 ist oben

    elif modus == "countdown":
        # Drei weiße Blitze. Beim vierten (= Start) startest du das Lied auf Handy oder Lautsprecher.
        t = utime.ticks_diff(jetzt, start)
        if k_mitte and not blitze:
            modus = "wahl"                    # Automatik während der Pause abbrechen
        elif t >= vorlauf:
            try:
                datei = open(pfad, "rb")
                kopf = datei.read(2)          # Dateikopf: Bilder pro Sekunde, Bytes pro Bild
                fps = kopf[0]
                bytes_pro_bild = kopf[1]
                start = utime.ticks_add(start, vorlauf)  # exakter Startzeitpunkt
                gelesen = 0
                glatt = [0.0] * 8
                beat_hell = 0.0
                vorher_b = 0.0
                reset_szenen(jetzt)
                modus = "spielen"
                print("Los:", name)
            except OSError:
                print("Datei nicht gefunden:", pfad)
                modus = "wahl"
        else:
            if blitze:
                seit = t % COUNTDOWN_ZEIT_MS
                hell = 1 - seit / 250
                if hell < MIN_HELL:
                    hell = MIN_HELL
                zeige((40, 40, 40), hell)
            else:
                zeige(farbe, MIN_HELL)        # Pause zwischen zwei Liedern: dunkle Farbe des nächsten Liedes

    elif modus == "spielen":
        t = utime.ticks_diff(jetzt, start) - AUDIO_VERSATZ_MS
        if t < 0:
            bild_nr = -1
        else:
            bild_nr = t * fps // 1000      # welches Bild gehört zur aktuellen Zeit?

        # Alle Bilder bis zur aktuellen Zeit einlesen (holt auch Rückstand auf)
        ende = False
        neuer_beat = False
        while gelesen <= bild_nr:
            bild = datei.read(bytes_pro_bild)
            gelesen = gelesen + 1
            if len(bild) < bytes_pro_bild:
                ende = True
                break
            for i in range(8):
                v = bild[i]
                if v > glatt[i]:
                    glatt[i] = v                         # Balken springt sofort nach oben
                else:
                    glatt[i] = max(v, glatt[i] - ABFALL)  # und fällt langsam
            b = bild[8] / 255
            if b >= BEAT_SCHWELLE and vorher_b < BEAT_SCHWELLE:
                neuer_beat = True                        # ein neuer Beat beginnt
            vorher_b = b
            if b < BEAT_SCHWELLE:
                b = 0
            beat_hell = max(b, beat_hell * BEAT_ABKLINGEN)

        # Ringe: bei neuem Beat einen Ring starten, alte entfernen
        if neuer_beat and szene == 3 and utime.ticks_diff(jetzt, letzter_ring) > RING_ABSTAND_MS:
            ringe.append((jetzt, KREIS_FARBEN[glatt.index(max(glatt))]))
            letzter_ring = jetzt
            if len(ringe) > MAX_RINGE:
                ringe.pop(0)
        while ringe and utime.ticks_diff(jetzt, ringe[0][0]) * RING_TEMPO / 1000 > RING_MAX_RADIUS:
            ringe.pop(0)

        if ende or k_mitte:
            datei.close()
            modus = "wahl"
            print("Lied:", name)
            # Automatik: nur wenn das Lied zu Ende lief (nicht beim Stoppen per Druck) und der Schalter an ist
            if ende and schalter.value() == SCHALTER_AN_WERT:
                if lied_nr + 1 < len(LIEDER) or AUTO_ENDLOS:
                    lied_nr = (lied_nr + 1) % len(LIEDER)
                    modus = "countdown"
                    start = jetzt
                    vorlauf = AUTO_PAUSE_MS
                    blitze = False
                    print("Automatik, nächstes Lied:", LIEDER[lied_nr][0])
        else:
            if szene == 0:
                zeige_equalizer(glatt, beat_hell)
            elif szene == 1:
                zeige_kreis(glatt, beat_hell)
            elif szene == 2:
                zeige_farbmischer(glatt, beat_hell)
            elif szene == 3:
                zeige_ringe(jetzt)
            elif szene == 4:
                zeige_peak(glatt, beat_hell, dt, jetzt)
            elif szene == 5:
                zeige_sonne(glatt, beat_hell)
            elif szene == 6:
                zeige_spirale(glatt, beat_hell, dt)
            else:
                zeige_feuerwerk(glatt, dt, jetzt, neuer_beat)
            # Nach dem Wechsel kurz die Szenen-Nummer unten zeigen (1 Punkt = Szene 1)
            if utime.ticks_diff(szene_anzeige_bis, jetzt) > 0:
                for i in range(szene + 1):
                    np[i] = (40, 40, 40)

    np.write()
    utime.sleep_ms(PAUSE_MS)