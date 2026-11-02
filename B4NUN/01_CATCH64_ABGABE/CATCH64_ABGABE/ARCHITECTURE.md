# Architektur

CATCH 64 besitzt bewusst nur zwei klar getrennte Teile.

## Computer

1. `transport_api.py` kombiniert den Fahrplaner mit dem Abfahrtsmonitor. So
   erscheinen sowohl die schnellsten Routen als auch langsamere direkte
   Verbindungen, die der Fahrplaner sonst ausblendet. Benachbarte Bahn- und
   Bushaltestellen eines Bahnhofsknotens werden gemeinsam beruecksichtigt.
2. `catch_core.py` normalisiert die Antwort und berechnet die Empfehlung.
3. `serial_link.py` sendet ein kleines validiertes JSON-Paket per USB.
4. `setup_server.py` stellt nur die lokale Browser-Einrichtung bereit.
5. `catch64.py` verbindet die Komponenten und behandelt Fehler.

## Lumatrix

1. `catch_logic.py` validiert Daten und berechnet Countdown und Dringlichkeit.
2. `main.py` zeichnet LEDs und verarbeitet den Joystick.
3. `config.py` enthaelt ausschliesslich die getestete Hardwarebelegung.

Die Logikdateien besitzen keine Hardwareabhaengigkeit und werden deshalb mit
normalem Python automatisiert getestet. Netzwerk- oder USB-Fehler beenden das
Programm nicht; die letzte gueltige Anzeige bleibt erhalten.

Die Reserve wird zusammen mit der Gehzeit bereits auf dem Computer von der
Live-Abfahrtszeit abgezogen. Deshalb bedeutet `00` ohne weitere Karenz:
jetzt losgehen. Die Lumatrix zeigt den ruhigen roten Aufbruchspfeil acht
Sekunden lang nur als sichtbares Aktionssignal; der Pfeil ist keine
Gehrichtung und keine zusaetzliche Reserve. Danach folgt die naechste noch
erreichbare Verbindung.
