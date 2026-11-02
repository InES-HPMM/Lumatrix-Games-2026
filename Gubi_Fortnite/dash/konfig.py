# Zentrale Stellschrauben von Lumatrix Dash.
# Jeder Wert hier lässt sich ändern, ohne den restlichen Code anzufassen.

# Spalten pro Sekunde, mit denen ein Level vorbeizieht (Level können es überschreiben).
TEMPO = 7

# Helligkeit der Matrix in Prozent (die Bibliothek rechnet alle Farben damit herunter).
HELLIGKEIT = 15

# Spalte der Spielfigur auf der Matrix (0 = ganz links); rechts davon liegt die Vorausschau.
SPALTE_SPIELFIGUR = 1

# Sprungbögen als senkrechte Bewegung pro Spalte (negativ = nach oben).
WUERFEL_SPRUNG = (-1, -1, 0, 1, 1)
SPRUNGPAD_SPRUNG = (-1, -1, -1, -1, 0, 1, 1, 1, 1)

# Maximale Sprunghöhe des Robot in Pixeln.
ROBOT_MAX_HOEHE = 3

# Dauer der Anzeigen nach einem Tod in Millisekunden.
TOD_BLITZ_MS = 300
FORTSCHRITT_MS = 700

# Datei auf dem Board, in der die Bestmarken liegen.
BESTMARKEN_DATEI = "/bestmarken.json"
