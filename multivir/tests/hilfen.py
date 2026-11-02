from wetter.kalender import TAG_S, tagesnummer

# 2026-10-16 00:00 UTC
MITTERNACHT_UTC = tagesnummer(2026, 10, 16) * TAG_S
SOMMERZEIT = 2 * 3600


def zeitpunkt(stunde, minute=0, tag=16, versatz=SOMMERZEIT):
    """Sekunden seit 1970 UTC für eine Ortszeit im Oktober 2026 mit dem gegebenen Versatz."""
    return tagesnummer(2026, 10, tag) * TAG_S + stunde * 3600 + minute * 60 - versatz


def tage(anzahl=16, ab=16, code=3):
    return [["2026-10-%02d" % (ab + i) if ab + i <= 31 else "2026-11-%02d" % (ab + i - 31), code, 18.4, 9.5] for i in range(anzahl)]
