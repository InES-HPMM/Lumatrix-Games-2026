# Physik der Spielfigur: ein Schritt pro Spalte.
#
# Koordinaten wie im Levelraster: x ist die Spalte im Level, y die Zeile (0 = oben).
# Schwerkraft +1 zieht nach unten, -1 nach oben. Pro Schritt rückt die Spielfigur eine
# Spalte vor und bewegt sich höchstens ein Pixel senkrecht. Bei diagonaler Bewegung
# wird zuerst die waagrechte, dann die senkrechte Richtung geprüft.

from dash import konfig
from dash.level import (
    ROBOT,
    SCHIFF,
    SPIDER,
    SPITZE,
    SPRUNGPAD,
    SPRUNGRING,
    SWING,
    WUERFEL,
    ZEILEN,
)

LAEUFT = 0
TOD = 1
ZIEL = 2

_SPRINGENDE_MODI = (WUERFEL, ROBOT)


class Zustand:
    def __init__(self, x, y, modus, schwerkraft=1):
        self.x = x
        self.y = y
        self.modus = modus
        self.schwerkraft = schwerkraft
        # verbleibender Sprungbogen (Würfelsprung oder Sprungpad)
        self.bogen = ()
        # Anzahl Pixel, die der Robot im laufenden Sprung gestiegen ist; -1 = steigt nicht
        self.robot_steigt = -1
        # Swing fliegt nach einem Wechsel eine Spalte geradeaus
        self.wende = False
        # war die Eingabe im vorigen Schritt aktiv?
        self.gehalten = False

    def kopie(self):
        z = Zustand(self.x, self.y, self.modus, self.schwerkraft)
        z.bogen = self.bogen
        z.robot_steigt = self.robot_steigt
        z.wende = self.wende
        z.gehalten = self.gehalten
        return z

    def schluessel(self):
        return (
            self.x,
            self.y,
            self.modus,
            self.schwerkraft,
            self.bogen,
            self.robot_steigt,
            self.wende,
            self.gehalten,
        )


def startzustand(level):
    return Zustand(0, ZEILEN - 1, level.startmodus)


def _modus_wechseln(z, modus):
    z.modus = modus
    z.schwerkraft = 1
    z.bogen = ()
    z.robot_steigt = -1
    z.wende = False


def _springen(z):
    if z.modus == WUERFEL:
        z.bogen = konfig.WUERFEL_SPRUNG
    else:
        z.bogen = ()
        z.robot_steigt = 0


def schritt(level, alt, gehalten, gedrueckt=None):
    """
    Ein Schritt um eine Spalte nach rechts.

    :param gehalten: ist die Eingabe in diesem Schritt aktiv?
    :param gedrueckt: gab es seit dem letzten Schritt einen neuen Druck?
        Ohne Angabe gilt: gehalten, aber im vorigen Schritt nicht.
    :return: (LAEUFT | TOD | ZIEL, neuer Zustand)
    """
    if gedrueckt is None:
        gedrueckt = gehalten and not alt.gehalten
    z = alt.kopie()
    z.gehalten = gehalten
    m = z.modus
    feld_hier = level.feld(z.x, z.y)
    steht = level.fest(z.x, z.y + z.schwerkraft)

    # 1. Aktionen am aktuellen Ort
    if m in _SPRINGENDE_MODI:
        frei = not z.bogen and z.robot_steigt < 0
        if feld_hier == SPRUNGPAD and steht and frei:
            z.bogen = konfig.SPRUNGPAD_SPRUNG
        elif feld_hier == SPRUNGRING and gedrueckt:
            _springen(z)
        elif steht and frei:
            if (m == WUERFEL and gehalten) or (m == ROBOT and gedrueckt):
                _springen(z)
    elif m == SPIDER:
        if gedrueckt:
            z.schwerkraft = -z.schwerkraft
            while not level.fest(z.x, z.y + z.schwerkraft):
                z.y += z.schwerkraft
            if level.feld(z.x, z.y) == SPITZE:
                return TOD, z
            steht = True
    elif m == SWING:
        if gedrueckt:
            z.schwerkraft = -z.schwerkraft
            z.wende = True

    # 2. senkrechte Bewegung in diesem Schritt
    if m in _SPRINGENDE_MODI:
        if z.robot_steigt >= 0:
            if gehalten and z.robot_steigt < konfig.ROBOT_MAX_HOEHE:
                dy = -1
                z.robot_steigt += 1
            else:
                dy = 0
                z.robot_steigt = -1
        elif z.bogen:
            dy = z.bogen[0]
            z.bogen = z.bogen[1:]
        elif steht:
            dy = 0
        else:
            dy = 1
    elif m == SCHIFF:
        dy = -1 if gehalten else 1
    elif m == SPIDER:
        dy = 0 if steht else z.schwerkraft
    else:  # SWING
        if z.wende:
            dy = 0
            z.wende = False
        else:
            dy = z.schwerkraft
    schwerkraft = z.schwerkraft

    # 3. waagrecht
    z.x += 1
    if z.x >= level.laenge:
        return ZIEL, z
    if level.fest(z.x, z.y) or level.feld(z.x, z.y) == SPITZE:
        return TOD, z
    portal = level.portale.get(z.x)
    if portal and portal != m:
        _modus_wechseln(z, portal)

    # 4. senkrecht
    if dy:
        if level.fest(z.x, z.y + dy):
            if dy != schwerkraft and m in _SPRINGENDE_MODI:
                return TOD, z  # Stoß von unten gegen einen Block
            # Landung oder Gleiten: Die Spielfigur bleibt auf ihrer Zeile.
            if dy == schwerkraft:
                z.bogen = ()
                z.robot_steigt = -1
        else:
            z.y += dy
            if level.feld(z.x, z.y) == SPITZE:
                return TOD, z
    return LAEUFT, z


def fortschritt_pixel(level, z, ergebnis=LAEUFT):
    """Fortschritt als Anzahl Pixel des Fortschrittsbalkens (0 bis 64)."""
    if ergebnis == ZIEL:
        return 64
    return min(63, z.x * 64 // level.laenge)
