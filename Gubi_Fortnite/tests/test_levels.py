import pytest

from dash.levels import LEVEL
from dash.physik import LAEUFT, ZIEL, schritt, startzustand
from werkzeuge.schaffbarkeit import pruefen


@pytest.mark.parametrize("level", LEVEL, ids=lambda lv: lv.name)
def test_level_ist_schaffbar(level):
    e = pruefen(level)
    assert e.schaffbar, "weiter als Spalte %d kommt man nicht" % e.weiteste_spalte


@pytest.mark.parametrize("level", LEVEL, ids=lambda lv: lv.name)
def test_gefundene_eingaben_fuehren_ins_ziel(level):
    z = startzustand(level)
    ergebnis = LAEUFT
    for gehalten in pruefen(level).eingaben:
        ergebnis, z = schritt(level, z, gehalten)
    assert ergebnis == ZIEL
