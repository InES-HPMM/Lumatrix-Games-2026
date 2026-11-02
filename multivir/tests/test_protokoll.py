import json

import pytest

from tests.hilfen import SOMMERZEIT, tage, zeitpunkt
from wetter.daten import Daten
from wetter.protokoll import verarbeiten
from wetter.uhr import Uhr

STANS = {"name": "Stans", "lat": 46.96, "lon": 8.37}


@pytest.fixture
def datei(tmp_path):
    return str(tmp_path / "wetter.json")


def senden(daten, uhr, nachricht, ms=0):
    return verarbeiten(json.dumps(nachricht), daten, uhr, ms)


def test_neue_lumatrix_meldet_leeren_zustand(datei):
    antwort = senden(Daten(datei), Uhr(), {"befehl": "status"})
    assert antwort["ok"] and antwort["standort"] is None and antwort["tage"] == 0
    assert antwort["uhr"] is False
    assert antwort["nachtruhe"] == [22 * 60, 7 * 60]


def test_uebertragung_stellt_uhr_und_speichert_dauerhaft(datei):
    daten, uhr = Daten(datei), Uhr()
    jetzt = zeitpunkt(10)
    antwort = senden(
        daten,
        uhr,
        {
            "befehl": "setzen",
            "jetzt": jetzt,
            "versatz_rechner": SOMMERZEIT,
            "standort": STANS,
            "versatz_standort": SOMMERZEIT,
            "tage": tage(),
        },
        ms=5000,
    )
    assert antwort["ok"] and antwort["uhr"] and antwort["tage"] == 16
    assert uhr.jetzt(8000) == jetzt + 3

    neu = Daten(datei)  # nach einem Neustart
    assert neu.standort == STANS
    assert neu.wetter_zeit == jetzt
    assert neu.tag(jetzt, 0).datum == "2026-10-16"
    assert neu.tag(jetzt, 7).datum == "2026-10-23"


def test_mehr_als_16_tage_werden_abgeschnitten(datei):
    daten = Daten(datei)
    senden(daten, Uhr(), {"befehl": "setzen", "jetzt": zeitpunkt(10), "tage": tage(20)})
    assert len(daten.tage) == 16


def test_neuer_standort_ohne_wetter_loescht_altes_wetter(datei):
    daten, uhr = Daten(datei), Uhr()
    senden(daten, uhr, {"befehl": "setzen", "jetzt": zeitpunkt(10), "standort": STANS, "tage": tage()})
    senden(daten, uhr, {"befehl": "setzen", "standort": {"name": "Tokio", "lat": 35.7, "lon": 139.7}})
    assert daten.standort["name"] == "Tokio"
    assert daten.tage == [] and daten.wetter_zeit is None


def test_gleicher_standort_behaelt_wetter(datei):
    daten, uhr = Daten(datei), Uhr()
    senden(daten, uhr, {"befehl": "setzen", "jetzt": zeitpunkt(10), "standort": STANS, "tage": tage()})
    senden(daten, uhr, {"befehl": "setzen", "standort": dict(STANS)})
    assert len(daten.tage) == 16


def test_fehlerhafte_nachricht_aendert_nichts(datei):
    daten, uhr = Daten(datei), Uhr()
    antwort = senden(daten, uhr, {"befehl": "setzen", "jetzt": zeitpunkt(10), "standort": STANS, "tage": [["kaputt"]]})
    assert antwort["ok"] is False
    assert daten.standort is None and not uhr.bekannt()


@pytest.mark.parametrize(
    "zeile",
    [
        "kein json",
        "[1, 2]",
        '{"befehl": "loeschen"}',
        '{"befehl": "setzen", "tage": []}',
        '{"befehl": "setzen", "nachtruhe": [0, 1440]}',
        '{"befehl": "setzen", "jetzt": "gestern"}',
    ],
)
def test_ungueltige_zeilen_werden_abgelehnt(datei, zeile):
    antwort = verarbeiten(zeile, Daten(datei), Uhr(), 0)
    assert antwort["ok"] is False and antwort["fehler"]


def test_kaputte_datei_ergibt_neue_lumatrix(datei):
    with open(datei, "w") as f:
        f.write("{nicht json")
    assert Daten(datei).standort is None


def test_nachtruhe_setzen(datei):
    daten = Daten(datei)
    antwort = senden(daten, Uhr(), {"befehl": "setzen", "nachtruhe": [23 * 60, 6 * 60]})
    assert antwort["nachtruhe"] == [23 * 60, 6 * 60]
    assert Daten(datei).nachtruhe == (23 * 60, 6 * 60)
