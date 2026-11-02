"""Hardware-Konfiguration fuer die originale Lumatrix."""

LED_PIN = 19
BUTTON_PIN = 8

# An der echten Lumatrix getestet.
JOY_UP_PIN = 3
JOY_DOWN_PIN = 6
JOY_LEFT_PIN = 2
JOY_RIGHT_PIN = 7

SERPENTINE = False
ROTATION = 0
MIRROR_X = False
MIRROR_Y = True

# Die Anzeige bleibt ruhig. Nur nach einer bewussten Auswahl wird die Linie
# kurz eingeblendet. Danach bleibt die wichtigste Zahl stehen.
LINE_CHUNK_MS = 2200
ALERT_MS = 2200
INFO_MS = 5000
DIGIT_STEP_MS = 165
LINE_REPEAT_MS = 60000
DEMO_AFTER_SECONDS = 8
DATA_STALE_MINUTES = 5
