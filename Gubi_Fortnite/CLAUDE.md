# CLAUDE.md — Lumatrix

MicroPython-Projekt für die **ZHAW Lumatrix**: 8×8 RGB-LED-Matrix auf einem
Raspberry Pi Pico (RP2040), MicroPython v1.28.0.

## Hardware

- USB: `/dev/cu.usbmodem101` (VID:PID 2E8A:0005)
- LEDs: 64 × WS2812 an GPIO 19, über `zhaw_led_matrix.LedMatrix(8, 8)`
- Joystick (Pull-up, gedrückt = 0): oben 3, unten 6, links 7, rechts 2, Mitte 8
- Schiebeschalter: GPIO 9
- Helligkeit niedrig halten (≤ 40 %), alle LEDs auf 100 % ziehen zu viel Strom.

## Lumatrix Dash

Geometry Dash für die 8×8-Matrix. Begriffe (Spielfigur, Modus, Levelwahl, Bestmarke …)
stehen in `CONTEXT.md`, Grundsatzentscheidungen in `docs/adr/`. Beides vor Änderungen lesen.

- `dash/` — das Spiel, wird so aufs Board kopiert
  - `physik.py`, `level.py`, `anzeige.py`, `bestmarke.py` — hardwarefrei (laufen auch unter CPython)
  - `geraet.py` — einziges Modul mit Hardwarezugriff (Joystick, Schalter, Matrix)
  - `konfig.py` — Tempo, Helligkeit, Sprungbögen
  - `levels/` — Level als Textraster (Legende in `level.py`)
- `main.py` — startet `dash.geraet.starten()` beim Booten
- `tests/` — pytest auf dem Mac; `werkzeuge/schaffbarkeit.py` prüft, ob Level schaffbar sind
- `backup/2026-10-11_board-original/` — Originalzustand des Boards, schreibgeschützt. Nie verändern.

Spielcode muss MicroPython-tauglich bleiben: kein `dataclasses`, `typing`, `enum`, keine
Umlaute in Bezeichnern. Bildzeile 0 ist oben; die ZHAW-Bibliothek zählt Zeilen von unten
(`geraet.zeige` dreht das um).

## Befehle

- Tests: `.venv/bin/pytest`
- Schaffbarkeit: `.venv/bin/python -m werkzeuge.schaffbarkeit [name]`
- Aufspielen (testet zuerst, schreibt nur `dash/` und `main.py`): `./werkzeuge/aufspielen.sh`
- Originalzustand wiederherstellen: Inhalt von `backup/2026-10-11_board-original/` zurückkopieren und `/dash` löschen
