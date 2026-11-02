# Zentrale Stellschrauben der Wetteranzeige.
# Jeder Wert hier lässt sich ändern, ohne den restlichen Code anzufassen.

# Helligkeit der Matrix in Prozent (die Bibliothek rechnet alle Farben damit herunter).
HELLIGKEIT = 20

# Anzahl Tage der Vorhersage auf der Matrix (ein Pixel der Tagesleiste pro Tag).
TAGE_ANGEZEIGT = 8

# Höchstens so viele Tage bewahrt die Lumatrix aus einer Übertragung auf.
TAGE_GESPEICHERT = 16

# Ohne Joystick-Bewegung springt die Anzeige nach dieser Zeit zurück auf heute.
RUECKSPRUNG_MS = 30000

# So lange steht die Temperaturanzeige anstelle des Wetter-Icons.
TEMPERATUR_MS = 3000

# So lange bleibt die Matrix während der Nachtruhe nach einem Klick wach.
WECKEN_MS = 30000

# Nach so vielen Sekunden seit der letzten Übertragung gilt die Vorhersage als veraltet.
VERALTET_S = 24 * 3600

# Vorgabe für die Nachtruhe in Minuten nach Mitternacht (Beginn, Ende).
NACHTRUHE = (22 * 60, 7 * 60)

# Datei auf dem Board, in der Standort, Nachtruhe und Wetterdaten liegen.
DATEI = "/wetter.json"
