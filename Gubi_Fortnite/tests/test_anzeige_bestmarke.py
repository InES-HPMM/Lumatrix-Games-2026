from dash.anzeige import (
    ELEMENTFARBE,
    MODUSFARBE,
    SCHWARZ,
    fortschrittsbild,
    gedimmt,
    spielbild,
)
from dash.bestmarke import Bestmarken
from dash.level import BLOCK, SCHIFF, WUERFEL, Level
from dash.physik import Zustand

LEER = ("........",) * 8


def test_spielbild_zeigt_spielfigur_in_spalte_1_in_modusfarbe():
    lv = Level("t", ["\n".join(LEER[:7] + ("....#...",))], WUERFEL)
    bild = spielbild(lv, Zustand(2, 7, WUERFEL))
    assert bild[7][1] == MODUSFARBE[WUERFEL]
    # Block in Levelspalte 4 erscheint 2 Spalten rechts der Spielfigur
    assert bild[7][3] == ELEMENTFARBE[BLOCK]
    assert bild[7][4] == SCHWARZ


def test_spielbild_zeigt_portal_als_ganze_spalte():
    lv = Level("t", ["\n".join(("..S.....",) + LEER[1:])], WUERFEL)
    bild = spielbild(lv, Zustand(0, 7, WUERFEL))
    assert all(bild[y][3] == MODUSFARBE[SCHIFF] for y in range(8))


def test_fortschrittsbild_fuellt_zeilenweise_und_zeigt_bestmarke_gedimmt():
    gruen = MODUSFARBE[WUERFEL]
    bild = fortschrittsbild(10, 20, gruen)
    assert bild[0] == [gruen] * 8
    assert bild[1][:2] == [gruen] * 2 and bild[1][2] == SCHWARZ
    assert bild[2][3] == gedimmt(gruen)


def test_bestmarke_wird_dauerhaft_gespeichert(tmp_path):
    datei = str(tmp_path / "bestmarken.json")
    lv = Level("Stereo Madness", ["\n".join(LEER)], WUERFEL)
    b = Bestmarken(datei)
    assert b.lesen(lv) == 0
    assert b.melden(lv, 20)
    assert not b.melden(lv, 10)
    assert Bestmarken(datei).lesen(lv) == 20


def test_bestmarke_zuruecksetzen_betrifft_nur_ein_level(tmp_path):
    datei = str(tmp_path / "bestmarken.json")
    a = Level("A", ["\n".join(LEER)], WUERFEL)
    b = Level("B", ["\n".join(LEER)], WUERFEL)
    marken = Bestmarken(datei)
    marken.melden(a, 30)
    marken.melden(b, 40)
    marken.zuruecksetzen(a)
    neu = Bestmarken(datei)
    assert neu.lesen(a) == 0 and neu.lesen(b) == 40
