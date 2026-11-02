# Datumsrechnung ohne das time-Modul, damit sie auf dem Board und auf dem Mac gleich rechnet.
# Zeitpunkte sind Sekunden seit 1970-01-01 UTC, ein Versatz ist die Zeitverschiebung in Sekunden.

TAG_S = 86400


def tagesnummer(jahr, monat, tag):
    """Tage seit 1970-01-01 (Algorithmus „days from civil“ von Howard Hinnant)."""
    if monat <= 2:
        jahr -= 1
    era = jahr // 400
    yoe = jahr - era * 400
    mp = (monat + 9) % 12
    doy = (153 * mp + 2) // 5 + tag - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def datum_nummer(text):
    """Tagesnummer eines Datums im Format JJJJ-MM-TT."""
    return tagesnummer(int(text[0:4]), int(text[5:7]), int(text[8:10]))


def heute_nummer(jetzt, versatz):
    """Tagesnummer des Kalendertags, der zum Zeitpunkt jetzt am Ort mit diesem Versatz gilt."""
    return (jetzt + versatz) // TAG_S


def minute_des_tages(jetzt, versatz):
    return (jetzt + versatz) % TAG_S // 60


def in_nachtruhe(jetzt, versatz, beginn, ende):
    """True, wenn die Ortszeit in [beginn, ende) liegt; die Spanne darf über Mitternacht gehen."""
    if beginn == ende:
        return False
    m = minute_des_tages(jetzt, versatz)
    if beginn < ende:
        return beginn <= m < ende
    return m >= beginn or m < ende
