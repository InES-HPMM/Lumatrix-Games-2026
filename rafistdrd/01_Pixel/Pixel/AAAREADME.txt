Bitte Lies diese Datei voll und ganz durch!
Ich hatte die Idee einen Desktop Assistent(für in den Hintergrund zu bauen. Ist mir meiner meinung nach auch einiger massen gelungen.
Ich habe KI nur für Recherche und fehlbehebung benutzt mein code ist Handgeschriben!
Dass Pixel voll Funktions fähig ist braucht es Folgendes:
- light.txt
- mode.txt
- runden.txt (erstmal sollte auf 0 gesetzt werden)
- Faces(derOrdner) darin sind alle gesichter gespeichert! Muss sein!! 
- in der datei ledmatrix.py linie 248 delay auf 100ms ändern(optional)
- natürlich auch main.py
- im ordner Backups ist alles nochmal gesichert

Anleitung:
1.Pixel startet beim 1.mal stellt er sich vor.
2.Helligkeit kann eingestellt werden(wird in light.txt und mode.txt gespeichert):
    -nach oben heller nach unten dünkler
    -nach Links von dir ausgesehen Modus wechsel.
        -Weiss = standard
        -night = extra dunkel und grau
        -grün = meine Lieblingsfarbe
    -nach Rechts von dir aus Start
3.Pixel läuft selbst ständig:
    -er blinzelt
    -er schaut herum
    -er staunt
    -irgend wann kommt Rainbowcat(inspiration an NYNE CAT) vorbei und sagt dir wie lange pixel bereits an(ungefähr) war:
        -wird aus Runden berechnet
        -global gespeichert in runden.txt
        -sobald stunden erreicht wird von Min zu h gewechselt
4.Pixel ausschalten
    -einfach steckerziehen alles wird alle 2 min gespeichert
    