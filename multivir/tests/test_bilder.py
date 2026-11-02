import pytest

from wetter import bilder
from wetter import wetterlage as wl


def leuchtende_spalten(bild):
    return sorted({x for zeile in bild for x, f in enumerate(zeile) if f != bilder.SCHWARZ})


@pytest.mark.parametrize("code,lage", [(0, wl.SONNE), (2, wl.SONNE_WOLKE), (48, wl.NEBEL), (63, wl.REGEN), (82, wl.REGEN), (86, wl.SCHNEE), (99, wl.GEWITTER), (None, wl.UNBEKANNT), (4, wl.UNBEKANNT)])
def test_wetterlage_aus_code(code, lage):
    assert wl.aus_code(code) == lage


@pytest.mark.parametrize("lage", [wl.SONNE, wl.SONNE_WOLKE, wl.WOLKE, wl.NEBEL, wl.REGEN, wl.SCHNEE, wl.GEWITTER, wl.UNBEKANNT])
def test_icons_haben_7_mal_8_pixel_und_leuchten(lage):
    for ms in range(0, 3000, 50):
        bild = bilder.icon(lage, ms)
        assert len(bild) == 7 and all(len(z) == 8 for z in bild)
        assert leuchtende_spalten(bild)


@pytest.mark.parametrize("lage", [wl.SONNE, wl.REGEN, wl.SCHNEE, wl.GEWITTER, wl.NEBEL])
def test_icons_sind_animiert(lage):
    assert len({str(bilder.icon(lage, ms)) for ms in range(0, 3000, 50)}) > 1


@pytest.mark.parametrize("wert,text", [(18.4, 18), (18.5, 19), (-0.4, 0), (-2.5, -3), (-12.2, -12)])
def test_runden(wert, text):
    assert bilder.runden(wert) == text


@pytest.mark.parametrize("wert,breite", [(7, 3), (18, 7), (-3, 6), (0.2, 3)])
def test_passende_temperatur_steht_mittig_still(wert, breite):
    a = bilder.temperatur(wert, bilder.ORANGE, 0, 3000)
    b = bilder.temperatur(wert, bilder.ORANGE, 2900, 3000)
    assert a == b
    spalten = leuchtende_spalten(a)
    assert spalten[-1] - spalten[0] + 1 == breite
    links = spalten[0]
    rechts = 7 - spalten[-1]
    assert abs(links - rechts) <= 1


def test_zu_breite_temperatur_laeuft_durch():
    dauer = 3000
    bilder_folge = [bilder.temperatur(-12, bilder.BLAU, t, dauer) for t in range(0, dauer, 100)]
    assert len({str(b) for b in bilder_folge}) > 10
    # beginnt rechts herein und ist am Ende hinausgelaufen
    assert leuchtende_spalten(bilder.temperatur(-12, bilder.BLAU, 200, dauer))[0] >= 5
    assert leuchtende_spalten(bilder.temperatur(-12, bilder.BLAU, dauer - 1, dauer)) in ([], [0])
    assert leuchtende_spalten(bilder.temperatur(-12, bilder.BLAU, dauer, dauer)) == []


def test_temperatur_in_den_zeilen_1_bis_5():
    bild = bilder.temperatur(88, bilder.ORANGE, 0, 3000)
    zeilen = [y for y, z in enumerate(bild) if any(f != bilder.SCHWARZ for f in z)]
    assert zeilen == [1, 2, 3, 4, 5]


def test_tagesleiste():
    zeile = bilder.tagesleiste(2, 8, False)
    assert zeile[2] == bilder.WEISS
    assert zeile[0] == bilder.gedimmt(bilder.WEISS)
    assert bilder.tagesleiste(0, 8, True)[0] == bilder.ROT


def test_wartepunkt_pulsiert_und_wird_nie_dunkel():
    helligkeiten = {bilder.wartepunkt(ms)[3][3] for ms in range(0, 2000, 100)}
    assert len(helligkeiten) > 5
    assert all(f != bilder.SCHWARZ for f in helligkeiten)
