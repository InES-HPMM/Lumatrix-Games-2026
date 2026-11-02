#!/bin/sh
# Spielt die Wetteranzeige auf das Board und startet sie neu.
# Nur wetter/ und main.py werden geschrieben; alles andere auf dem Board (dash/, /bestmarken.json,
# /wetter.json mit Standort und Wetterdaten) bleibt unangetastet.
# Die Konfigurationsseite muss dafür getrennt sein, sonst ist die USB-Schnittstelle belegt.
set -e
cd "$(dirname "$0")/.."

.venv/bin/pytest -q
node --test 'tests/web/*.test.mjs'

M=".venv/bin/mpremote"
find wetter -name __pycache__ -type d -prune -exec rm -rf {} +
$M fs rm -r :wetter 2>/dev/null || true
$M fs cp -r wetter :
$M fs cp main.py :main.py
$M reset  # soft-reset aus mpremote würde main.py nicht starten
echo "Aufgespielt."
