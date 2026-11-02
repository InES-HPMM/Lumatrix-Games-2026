#!/bin/sh
# Spielt Lumatrix Dash auf das Board und startet es neu.
# Nur dash/ und main.py werden geschrieben; alles andere auf dem Board bleibt unangetastet.
set -e
cd "$(dirname "$0")/.."

.venv/bin/pytest -q
.venv/bin/python -m werkzeuge.schaffbarkeit

M=".venv/bin/mpremote"
find dash -name __pycache__ -type d -prune -exec rm -rf {} +
$M fs rm -r :dash 2>/dev/null || true
$M fs cp -r dash :
$M fs cp main.py :main.py
$M soft-reset
echo "Aufgespielt."
