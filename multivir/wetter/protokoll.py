# Das Zeilenprotokoll zwischen Konfigurationsseite und Lumatrix (siehe docs/adr/0002).
#
# Jede Nachricht ist eine JSON-Zeile. Die Seite schickt
#   {"befehl": "status"}                      – nur den Zustand abfragen
#   {"befehl": "setzen", ...}                 – Felder setzen, alle freiwillig:
#       "jetzt": Sekunden seit 1970 UTC        stellt die Uhr
#       "versatz_rechner": Sekunden            Zeitverschiebung am Rechner (für die Nachtruhe)
#       "standort": {"name", "lat", "lon"}     ein neuer Standort ohne "tage" löscht die alten Wetterdaten
#       "versatz_standort": Sekunden           Zeitverschiebung am Standort (für „heute“)
#       "tage": [[datum, code, max, min], ...] Wetterdaten, braucht "jetzt"
#       "nachtruhe": [beginn, ende]            Minuten nach Mitternacht
# Die Lumatrix antwortet immer mit einer Zeile: {"ok": true, ...Zustand} oder {"ok": false, "fehler": ...}.
# Beim Start meldet sie sich ungefragt mit {"hallo": true, "ok": true, ...Zustand}.

import json

from wetter import konfig
from wetter.daten import Tag

VERSION = 1


class Fehler(Exception):
    pass


def zustand(daten, uhr):
    return {
        "ok": True,
        "version": VERSION,
        "standort": daten.standort,
        "nachtruhe": list(daten.nachtruhe),
        "wetter_zeit": daten.wetter_zeit,
        "tage": len(daten.tage),
        "uhr": uhr.bekannt(),
    }


def verarbeiten(zeile, daten, uhr, ms):
    """Verarbeitet eine empfangene Zeile und gibt die Antwort als Dictionary zurück."""
    try:
        nachricht = json.loads(zeile)
        if not isinstance(nachricht, dict):
            raise Fehler("Nachricht ist kein Objekt")
        befehl = nachricht.get("befehl")
        if befehl == "setzen":
            _setzen(nachricht, daten, uhr, ms)
        elif befehl != "status":
            raise Fehler("unbekannter Befehl")
    except (Fehler, ValueError, TypeError, KeyError, IndexError) as e:
        return {"ok": False, "fehler": str(e) or type(e).__name__}
    return zustand(daten, uhr)


def _zahl(wert):
    if wert is None:
        return None
    if isinstance(wert, bool) or not isinstance(wert, (int, float)):
        raise Fehler("Zahl erwartet")
    return wert


def _ganzzahl(wert):
    if isinstance(wert, bool) or not isinstance(wert, int):
        raise Fehler("Ganzzahl erwartet")
    return wert


def _standort(s):
    if not isinstance(s, dict) or not isinstance(s.get("name"), str):
        raise Fehler("Standort ungültig")
    return {"name": s["name"], "lat": _zahl(s["lat"]), "lon": _zahl(s["lon"])}


def _tage(liste):
    if not isinstance(liste, list):
        raise Fehler("tage ist keine Liste")
    tage = []
    for t in liste[: konfig.TAGE_GESPEICHERT]:
        datum, code, maximum, minimum = t
        if not isinstance(datum, str) or len(datum) != 10:
            raise Fehler("Datum ungültig")
        if code is not None:
            _ganzzahl(code)
        tage.append(Tag(datum, code, _zahl(maximum), _zahl(minimum)))
    return tage


def _nachtruhe(n):
    beginn, ende = n
    for m in (beginn, ende):
        if _ganzzahl(m) < 0 or m >= 24 * 60:
            raise Fehler("Nachtruhe ungültig")
    return (beginn, ende)


def _setzen(n, daten, uhr, ms):
    # Erst alles prüfen, dann übernehmen: eine fehlerhafte Nachricht ändert nichts.
    jetzt = _ganzzahl(n["jetzt"]) if "jetzt" in n else None
    standort = _standort(n["standort"]) if "standort" in n else None
    tage = _tage(n["tage"]) if "tage" in n else None
    nachtruhe = _nachtruhe(n["nachtruhe"]) if "nachtruhe" in n else None
    versatz_rechner = _ganzzahl(n["versatz_rechner"]) if "versatz_rechner" in n else None
    versatz_standort = _ganzzahl(n["versatz_standort"]) if "versatz_standort" in n else None
    if tage is not None and jetzt is None:
        raise Fehler("tage ohne jetzt")

    if jetzt is not None:
        uhr.stellen(jetzt, ms)
    if versatz_rechner is not None:
        daten.versatz_rechner = versatz_rechner
    if standort is not None and standort != daten.standort:
        daten.standort = standort
        daten.tage = []  # Wetter des alten Standorts gilt nicht mehr
        daten.wetter_zeit = None
    if versatz_standort is not None:
        daten.versatz_standort = versatz_standort
    if tage is not None:
        daten.tage = tage
        daten.wetter_zeit = jetzt
    if nachtruhe is not None:
        daten.nachtruhe = nachtruhe
    if standort or tage is not None or nachtruhe or versatz_rechner is not None or versatz_standort is not None:
        daten.speichern()
