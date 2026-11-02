"""Farbtest und Smiley fuer die LED-Matrix des ZHAW-Workshops.

Den gesamten Ordner programme/zhaw_led_matrix aus dem Repository
ins Hauptverzeichnis des Pico kopieren:
https://github.com/InES-HPMM/LED-Matrix-Workshop
"""

from utime import sleep
from zhaw_led_matrix import ColorTable, LedMatrix


# 8 x 8 wie im Repository-Beispiel democode_matrix.py.
# LedMatrix verwendet intern GPIO 19 (PIN_NP in ledmatrix.py).
matrix = LedMatrix(8, 8)
matrix.set_brightness(20)

for color in (ColorTable.RED, ColorTable.GREEN, ColorTable.BLUE):
    matrix.fill(color)
    matrix.apply()
    sleep(2)

# Eigenes Smiley-Motiv, Zeilen von oben nach unten.
smiley = (
    "00111100",
    "01000010",
    "10100101",
    "10000001",
    "10100101",
    "10011001",
    "01000010",
    "00111100",
)

matrix.clear()
for row, pixels in enumerate(smiley):
    for x, pixel in enumerate(pixels):
        if pixel == "1":
            # Repository-Zeichen verwenden y=0 unten.
            matrix[x, 7 - row] = ColorTable.YELLOW
matrix.apply()
# Das zuletzt uebertragene Bild bleibt auf den LEDs sichtbar.
