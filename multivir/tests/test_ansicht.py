import pytest

from tests.hilfen import SOMMERZEIT, tage, zeitpunkt
from wetter import bilder, konfig
from wetter.ansicht import LINKS, OBEN, RECHTS, UNTEN, Ansicht
from wetter.daten import Daten, Tag
from wetter.wetterlage import REGEN, SONNE, UNBEKANNT, WOLKE

MITTAG = zeitpunkt(12)


@pytest.fixture
def daten(tmp_path):
    d = Daten(str(tmp_path / "wetter.json"))
    d.standort = {"name": "Stans", "lat": 46.96, "lon": 8.37}
    d.versatz_standort = d.versatz_rechner = SOMMERZEIT
    d.tage = [Tag(*t) for t in tage()]
    d.tage[0].code = 0  # heute Sonne
    d.tage[2].code = 61  # übermorgen Regen
    d.wetter_zeit = MITTAG - 3600
    return d


def leiste(bild):
    return bild[7]


def hell(zeile):
    return [i for i, f in enumerate(zeile) if f in (bilder.WEISS, bilder.ROT)]


def test_ohne_standort_blinkt_die_stecknadel(daten):
    daten.standort = None
    a = Ansicht(daten)
    assert a.bild(0, MITTAG) == bilder.stecknadel(0)
    assert a.bild(600, MITTAG) == bilder.leeres_bild()


def test_ohne_uhr_oder_ohne_wetter_pulsiert_der_punkt(daten):
    a = Ansicht(daten)
    assert a.bild(0, None) == bilder.wartepunkt(0)
    daten.tage = []
    assert a.bild(0, MITTAG) == bilder.wartepunkt(0)


def test_heute_zeigt_icon_und_tagesleiste(daten):
    a = Ansicht(daten)
    bild = a.bild(0, MITTAG)
    assert bild[:7] == bilder.icon(SONNE, 0)
    assert hell(leiste(bild)) == [0]
    assert len([f for f in leiste(bild) if f != bilder.SCHWARZ]) == 8


def test_blaettern_mit_anschlag(daten):
    a = Ansicht(daten)
    a.klick(LINKS, 0, MITTAG)
    assert a.tag == 0
    a.klick(RECHTS, 10, MITTAG)
    a.klick(RECHTS, 20, MITTAG)
    assert a.bild(30, MITTAG)[:7] == bilder.icon(REGEN, 30)
    for i in range(10):
        a.klick(RECHTS, 40 + i, MITTAG)
    assert a.tag == 7
    assert hell(leiste(a.bild(100, MITTAG))) == [7]


def test_ruecksprung_auf_heute_nach_30_sekunden(daten):
    a = Ansicht(daten)
    a.klick(RECHTS, 0, MITTAG)
    a.bild(konfig.RUECKSPRUNG_MS - 1, MITTAG)
    assert a.tag == 1
    a.bild(konfig.RUECKSPRUNG_MS, MITTAG)
    assert a.tag == 0


def test_heute_wechselt_um_mitternacht_am_standort(daten):
    kurz_nach_mitternacht = zeitpunkt(0, 5, tag=17)
    assert daten.tag(kurz_nach_mitternacht, 0).datum == "2026-10-17"


def test_tage_ohne_daten_zeigen_fragezeichen(daten):
    a = Ansicht(daten)
    eine_woche_spaeter = zeitpunkt(12, tag=28)  # nur noch 4 Tage vorhanden
    for _ in range(5):
        a.klick(RECHTS, 0, eine_woche_spaeter)
    assert a.bild(10, eine_woche_spaeter)[:7] == bilder.icon(UNBEKANNT, 10)


def test_veraltete_vorhersage_faerbt_tagesleiste_rot(daten):
    a = Ansicht(daten)
    assert bilder.ROT not in leiste(a.bild(0, MITTAG))
    spaeter = daten.wetter_zeit + konfig.VERALTET_S + 1
    assert leiste(a.bild(0, spaeter))[0] == bilder.ROT


def test_temperatur_oben_maximum_unten_minimum(daten):
    a = Ansicht(daten)
    a.klick(OBEN, 0, MITTAG)
    bild = a.bild(100, MITTAG)
    assert bild[:7] == bilder.temperatur(18.4, bilder.ORANGE, 100, konfig.TEMPERATUR_MS)
    assert hell(leiste(bild)) == [0]  # Tagesleiste bleibt sichtbar
    a.klick(UNTEN, 200, MITTAG)
    assert a.bild(300, MITTAG)[:7] == bilder.temperatur(9.5, bilder.BLAU, 100, konfig.TEMPERATUR_MS)
    assert a.bild(200 + konfig.TEMPERATUR_MS, MITTAG)[:7] == bilder.icon(SONNE, 200 + konfig.TEMPERATUR_MS)


def test_blaettern_bricht_temperatur_ab(daten):
    a = Ansicht(daten)
    a.klick(OBEN, 0, MITTAG)
    a.klick(RECHTS, 100, MITTAG)
    assert a.bild(200, MITTAG)[:7] == bilder.icon(WOLKE, 200)


def test_nachtruhe_dunkel_und_weckender_klick_bewirkt_nichts(daten):
    a = Ansicht(daten)
    nacht = zeitpunkt(23)
    assert a.bild(0, nacht) == bilder.leeres_bild()
    a.klick(RECHTS, 1000, nacht)
    assert a.tag == 0
    assert a.bild(1100, nacht) != bilder.leeres_bild()
    a.klick(RECHTS, 2000, nacht)  # jetzt wach: blättert
    assert a.tag == 1
    assert a.bild(2000 + konfig.WECKEN_MS, nacht) == bilder.leeres_bild()


def test_nachtruhe_gilt_in_der_zeit_des_rechners(daten):
    daten.versatz_standort = 9 * 3600  # Standort Tokio, dort ist es schon Morgen
    a = Ansicht(daten)
    assert a.bild(0, zeitpunkt(23)) == bilder.leeres_bild()
