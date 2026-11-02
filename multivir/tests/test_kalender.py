import calendar
import datetime

from tests.hilfen import SOMMERZEIT, zeitpunkt
from wetter.kalender import datum_nummer, heute_nummer, in_nachtruhe, tagesnummer


def test_tagesnummer_stimmt_mit_der_standardbibliothek_ueberein():
    for d in (datetime.date(1970, 1, 1), datetime.date(2024, 2, 29), datetime.date(2026, 10, 16), datetime.date(2100, 3, 1)):
        erwartet = calendar.timegm(d.timetuple()) // 86400
        assert tagesnummer(d.year, d.month, d.day) == erwartet


def test_datum_nummer_liest_iso_datum():
    assert datum_nummer("2026-10-16") == tagesnummer(2026, 10, 16)


def test_heute_haengt_vom_versatz_ab():
    # Montag 20:00 in der Schweiz ist Dienstag 03:00 in Tokio
    jetzt = zeitpunkt(20, tag=19)
    assert heute_nummer(jetzt, SOMMERZEIT) == tagesnummer(2026, 10, 19)
    assert heute_nummer(jetzt, 9 * 3600) == tagesnummer(2026, 10, 20)


def test_nachtruhe_ueber_mitternacht():
    beginn, ende = 22 * 60, 7 * 60
    assert not in_nachtruhe(zeitpunkt(21, 59), SOMMERZEIT, beginn, ende)
    assert in_nachtruhe(zeitpunkt(22, 0), SOMMERZEIT, beginn, ende)
    assert in_nachtruhe(zeitpunkt(3, 0), SOMMERZEIT, beginn, ende)
    assert not in_nachtruhe(zeitpunkt(7, 0), SOMMERZEIT, beginn, ende)


def test_nachtruhe_am_tag_und_ausgeschaltet():
    assert in_nachtruhe(zeitpunkt(13, 0), SOMMERZEIT, 12 * 60, 14 * 60)
    assert not in_nachtruhe(zeitpunkt(14, 0), SOMMERZEIT, 12 * 60, 14 * 60)
    assert not in_nachtruhe(zeitpunkt(3, 0), SOMMERZEIT, 0, 0)
