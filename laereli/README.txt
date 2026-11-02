LUMABEAT - LIED-VISUALISIERUNG FÜR DIE LUMATRIX
================================================

Zeigt Lieder auf einer 8x8-LED-Matrix (WS2812B) am Raspberry Pi Pico in 8 Szenen (Equalizer, Kreis, Farbmischer, Ringe, Peak-Hold, Sonne, Spirale, Feuerwerk). Der Ton läuft separat auf Handy oder Lautsprecher.


DATEIEN
-------

lied_visu.py      Hauptprogramm
lieder_index.py   Liste der Lieder: (Name, Datei, Farbe, BPM)
lieder/           Ordner mit den .lum-Dateien (auf dem Pico)

lied_visu.py importiert LIEDER aus lieder_index.py. Jeder Eintrag verweist auf eine .lum-Datei im Ordner /lieder auf dem Pico:

    ("get_lucky", "/lieder/get_lucky.lum", (0, 10, 60), 116),


HARDWARE (GPIO-NUMMERN)
-----------------------

LED-Matrix (Daten):                                       GPIO 19
Joystick rechts / hoch / runter / links / hineindrücken:  GPIO 2 / 3 / 6 / 7 / 8
Schalter (Playlist):                                      GPIO 9

Taster und Schalter liegen mit der anderen Seite an GND (interne Pull-ups, keine Widerstände nötig). Die Matrix ist zeilenweise verdrahtet, LED 0 sitzt unten links. Ausreichende 5V-Stromversorgung verwenden und GND gemeinsam verbinden.


EINRICHTUNG (THONNY, MICROPYTHON AUF DEM PICO)
----------------------------------------------

1. lied_visu.py und lieder_index.py auf den Pico speichern (Hauptverzeichnis). Für Autostart lied_visu.py zusätzlich als main.py speichern.
2. Auf dem Pico den Ordner "lieder" anlegen.
3. Die .lum-Dateien in /lieder hochladen. Die Dateinamen müssen genau zu lieder_index.py passen.
4. lied_visu.py mit F5 starten.


BEDIENUNG
---------

- links / rechts: Lied wählen
- hineindrücken: Lied starten (3 Countdown-Blitze, beim vierten das Lied auf Handy/Lautsprecher starten) bzw. stoppen
- hoch / runter: Szene wechseln
- Schalter: Playlist-Modus. Der Text PLAYLIST läuft durch, danach startet am Liedende automatisch das nächste Lied. Zurücklegen: SINGLE.

Alle leicht änderbaren Werte (Farben, Tempo, Schalter-Logik, AUDIO_VERSATZ_MS bei Bluetooth) stehen oben in lied_visu.py.


HÄUFIGE PROBLEME
----------------

- "Datei nicht gefunden": Ordner "lieder" oder .lum-Datei fehlt bzw. Name stimmt nicht.
- ImportError lieder_index: lieder_index.py liegt nicht auf dem Pico.
- Playlist-Modus umgekehrt: SCHALTER_AN_WERT umstellen (0 oder 1).


DIE LIEDER IM PROJEKT
---------------------

1. get_lucky                    116 BPM
2. another_one_bites_the_dust   110 BPM
3. hello                        158 BPM
4. blinding_lights               86 BPM
5. uptown_funk                  115 BPM
6. billie_jean                  117 BPM
7. thunderstruck                134 BPM
8. bohemian_rhapsody            142 BPM

Spotify-Playlist mit allen acht Liedern zum Mitspielen:
https://open.spotify.com/playlist/0MCe8sxESCT35BUNHii5Z3?si=b7eaee4b1a9b4d6a

Eigene Lieder hinzufügen: MP3 mit dem Konverter umwandeln, die .lum-Datei nach /lieder auf dem Pico laden und einen Eintrag in lieder_index.py ergänzen (Name, Pfad, Farbe, BPM). Die Reihenfolge der Liste bestimmt die Reihenfolge in der Auswahl.


DAS .LUM-FORMAT
---------------

Jede .lum-Datei ist eine Binärdatei:

- Kopf (2 Bytes): Bilder pro Sekunde (fps) und Bytes pro Bild.
- Danach pro Bild: 8 Bytes für die Stärke der 8 Frequenzbereiche (tief bis hoch, Wert 0 bis 255) und 1 Byte für die Beat-Stärke (0 bis 255).

Das Programm liest anhand der aktuellen Zeit immer genau bis zum passenden Bild und holt Rückstand automatisch auf. Die Dateien enthalten nur diese Pegel-Daten, keinen Ton.
