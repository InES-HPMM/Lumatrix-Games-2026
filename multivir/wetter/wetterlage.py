# Wetterlagen und ihre Zuordnung zu den WMO-Wettercodes von Open-Meteo.

SONNE = "sonne"
SONNE_WOLKE = "sonne_wolke"
WOLKE = "wolke"
NEBEL = "nebel"
REGEN = "regen"
SCHNEE = "schnee"
GEWITTER = "gewitter"
UNBEKANNT = "unbekannt"

_CODES = (
    ((0, 1), SONNE),
    ((2,), SONNE_WOLKE),
    ((3,), WOLKE),
    ((45, 48), NEBEL),
    ((51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82), REGEN),
    ((71, 73, 75, 77, 85, 86), SCHNEE),
    ((95, 96, 99), GEWITTER),
)


def aus_code(code):
    """Wetterlage zu einem WMO-Code; None und unbekannte Codes ergeben UNBEKANNT."""
    for codes, lage in _CODES:
        if code in codes:
            return lage
    return UNBEKANNT
