# Levels fuer Angry Birds auf der Lumatrix
#
# Diese Datei kann von editor.py neu geschrieben werden.
#
# birds: Reihenfolge der Voegel
#   R = Rot, Y = Gelb (durchschlaegt 2 Bloecke), B = Bombe (3x3)
# objs:  (x, y, Typ), x=0 links, y=0 unten, Spalten 0-2 frei lassen
#   W = Holz, S = Stein (2 Treffer), G = Glas (zerbricht beim Fallen
#   oder wenn etwas darauf landet), T = TNT (explodiert 3x3),
#   F = Plattform (schwebt, unzerstoerbar), P = Schwein
# par:   kleinste Anzahl Voegel fuer den Sieg (= 3 Sterne),
#        wird von check_levels.py berechnet und geprueft

LEVELS = [
    {"birds": "RRR", "par": 1,
     "objs": [(5, 0, "W"), (5, 1, "W"), (5, 2, "P"),
              (6, 0, "W"), (6, 1, "W"), (6, 2, "W"), (6, 3, "W")]},
    {"birds": "RRR", "par": 2,
     "objs": [(5, 0, "G"), (5, 1, "G"), (5, 2, "P"),
              (7, 0, "W"), (7, 1, "G"), (7, 2, "P")]},
    {"birds": "RRR", "par": 1,
     "objs": [(4, 0, "W"), (4, 1, "W"),
              (5, 0, "S"), (6, 0, "S"), (7, 0, "S"),
              (5, 1, "P"), (6, 1, "T"), (7, 1, "P")]},
    {"birds": "RYB", "par": 3,
     "objs": [(4, 0, "S"), (4, 1, "S"),
              (5, 0, "S"), (6, 0, "S"), (7, 0, "S"),
              (5, 1, "W"), (6, 1, "P"), (7, 1, "W"),
              (5, 2, "S"), (6, 2, "S"), (7, 2, "S"),
              (6, 3, "P")]},
    {"birds": "RYR", "par": 2,
     "objs": [(4, 0, "W"),
              (6, 0, "W"), (6, 1, "P"),
              (7, 0, "W"), (7, 1, "W"), (7, 2, "P")]},
    {"birds": "RYB", "par": 2,
     "objs": [(4, 0, "S"), (4, 1, "S"),
              (6, 0, "W"), (6, 1, "W"), (6, 2, "W"), (6, 3, "W"),
              (6, 4, "W"), (6, 5, "P"),
              (7, 0, "P")]},
    {"birds": "RYBR", "par": 2,
     "objs": [(5, 4, "F"), (6, 4, "F"), (5, 5, "W"), (6, 5, "P"),
              (6, 0, "W"), (6, 1, "P"), (7, 0, "S"), (7, 1, "S")]},
    {"birds": "BYRR", "par": 2,
     "objs": [(4, 0, "S"), (4, 1, "S"), (4, 2, "S"),
              (5, 0, "G"), (6, 0, "P"), (7, 0, "G"),
              (5, 1, "W"), (6, 1, "W"), (7, 1, "W"),
              (6, 2, "P"),
              (5, 3, "S"), (6, 3, "T"), (7, 3, "S"),
              (7, 4, "P")]},
]
