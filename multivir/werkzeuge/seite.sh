#!/bin/sh
# Liefert die Konfigurationsseite lokal aus: http://localhost:8765
# Immer diese Adresse und diesen Port verwenden – für Chrome ist sonst jede Variante eine andere App.
# Einmal öffnen und als App installieren; danach startet die App auch ohne diesen Server.
cd "$(dirname "$0")/../web"
echo "Konfigurationsseite: http://localhost:8765  (beenden mit Ctrl-C)"
exec python3 -m http.server 8765 --bind 127.0.0.1
