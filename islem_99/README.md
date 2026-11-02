# Pixel Buddy - kleines Matrix-Haustier

Neu: [Lokaler Ollama-Chat mit LED-Emotionen per USB – Installation und Start](companion_pc/README.md).
Der Pico-Haustiermodus bleibt erhalten und nimmt nebenbei Chat-Emotionen vom PC an.

`main.py` startet jetzt den interaktiven Haustiermodus. Die drei Gesichter
Neutral, Happy und Sad bleiben erhalten. Die Stimmung folgt den Beduerfnissen,
statt automatisch alle acht Sekunden zu wechseln.

## Start in VS Code

1. Pico anschliessen und **MicroPico: Upload Project** ausfuehren.
2. `main.py` mit **MicroPico: Run Current File on Board/Pico** starten.
3. Schlaeft Buddy direkt, den Schiebeschalter in die andere Stellung bewegen.
4. Strg+C im MicroPico-Terminal beendet das Programm und schaltet die LEDs aus.

Auf dem Pico werden `main.py`, `pixel_buddy/` und `zhaw_led_matrix/` benoetigt.
Die Module zuerst hochladen; nur Run Current File reicht bei Aenderungen nicht.

## Bedienung

| Eingabe | Funktion |
| --- | --- |
| Joystick oben | Fuettern: Snack, dann Kauanimation; Saettigung +20, Laune +3 |
| Joystick links | 15 Sekunden Ruhe; Druck auf Joystick beendet sie vorzeitig |
| Joystick rechts | Sternfangspiel starten |
| Joystick unten | Status fuer 3,5 Sekunden anzeigen |
| Joystick druecken | Ohne PC-Chat: Streicheln (Herz, Laune +8). Mit PC-Chat: Mikrofon an/aus |
| Joystick doppelt druecken | Mit PC-Chat: Streicheln |
| Schiebeschalter | Tag/Schlaf; Schlaf bricht ein laufendes Spiel ab |
| Joystick (beliebig) bei Timer-Alarm | Blinkende rote 0 ausschalten (keine Aktion) |

Ein einfacher Druck wird nach 0,4 s ausgewertet, damit ein Doppeldruck erkannt
werden kann. Im Sternfangspiel beendet ein Druck das Spiel sofort wie bisher.
Ob ein PC-Chat laeuft, merkt der Pico an dessen Lebenszeichen (alle 5 s); nach
Beenden des Chats oder 15 s ohne Lebenszeichen gilt wieder: Druck = Streicheln.
Aktionen werden beim Druecken einmal ausgeloest. Zum Wiederholen loslassen und
neu druecken. Die Eingaben sind 40 ms entprellt. Pflegeaktionen haben eine kurze
Sperrzeit von 2,2 Sekunden. Ab 95 Saettigung lehnt Buddy weiteres Futter ab.
Im Schlaf werden Joystickaktionen ignoriert. Zum Aufwecken den Schalter umlegen.

**Timer** (nur ueber den PC-Chat, z. B. "Buddy, stell einen Timer fuer 15
Minuten"): Die Matrix zeigt die Minuten gross in Blau, die untere Reihe laeuft
jede Minute ab. In der letzten Minute zaehlen orange Sekunden. Bei 0 blinkt eine
rote 0 (3 s, dann wieder das Gesicht) und Buddy sagt "Die Zeit ist um!". Der Timer laeuft auf dem Pico weiter,
auch wenn der Chat beendet wird. Details: `companion_pc/README.md`, Abschnitt 9.

**Statusbalken:** oben orange = Saettigung, Mitte blau = Energie,
unten rosa = Laune. Acht helle LEDs entsprechen einem vollen Wert.
Exakte Werte erscheinen bei Aktionen im MicroPico-Terminal.

## Sternfangspiel

Ein goldener Stern faellt nach unten. Mit kurzen Links-/Rechtsbewegungen den
zwei Pixel breiten mintfarbenen Korb verschieben. Jede Bewegung versetzt ihn um
eine Spalte. Fange fuenf Sterne; mit Joystickdruck kannst du jederzeit abbrechen.
Nach fuenf Versuchen geht es automatisch zum Buddy zurueck. Mindestens drei
Treffer zeigen einen goldenen Stern als Belohnung. Auch eine abgeschlossene
Runde mit weniger Treffern hebt die Laune etwas.

Startkosten: 8 Energie und 3 Saettigung. Abschluss: +5 Laune und +4 pro Treffer.
Unter 20 Energie oder 15 Saettigung braucht Buddy zuerst Ruhe oder Futter.
Ein abgebrochenes Spiel gibt keinen Launenbonus; Startkosten bleiben bestehen.

## Stimmung und Zeit

Alle Werte liegen zwischen 0 und 100. Start: Saettigung 75, Energie 75, Laune 65.
Alle zehn Sekunden sinkt die Saettigung um 1. Im Wachzustand sinken auch Energie
und Laune um jeweils 1. Im Schlaf oder waehrend der Ruhepause steigt stattdessen
die Energie um 5, und die Laune bleibt konstant.

- Sad: mindestens einer der drei Werte unter 30.
- Happy: Saettigung und Energie mindestens 50, Laune mindestens 65.
- Neutral: alle anderen Zustaende. Der Mund bewegt sich nur, wenn Buddy ueber
  den PC-Chat spricht (beim Fuettern kaut er).

Kein Tod, keine Bestrafung, keine Cloud. Werte liegen nur im RAM: Nach einem
Neustart beginnt Buddy wieder mit den Startwerten. Ausschaltzeit wird nicht
nachberechnet. Der Schlafmodus ist eine Darstellung und kein Hardware-Tiefschlaf.

## Hardwarebasis und Code

Die Originaldatei `zhaw_led_matrix/button.py` definiert die Eingaben mit Pull-ups:
rechts GPIO2, oben GPIO3, unten GPIO6, links GPIO7, Druck GPIO8, Schalter GPIO9.
Joystickkontakte sind aktiv Low. Beim Schalter nutzt diese Anwendung Low fuer
Schlaf und High fuer Tag; eine physische Links-/Rechtsstellung wird nicht angenommen.

Die Matrix bleibt `LedMatrix(8, 8)` an GPIO19, 20 Prozent Helligkeit und bis zu
25 Bilder/s. RGB-Werte werden durch die unveraenderte Originalbibliothek intern
als GRB ueber `machine.bitstream` gesendet. Die Bildschirmkoordinaten werden mit
`(x, 7-y)` in die Workshop-Koordinaten uebersetzt.

Quelle: https://github.com/InES-HPMM/LED-Matrix-Workshop
Lokale Originalbeispiele: `LED-Matrix-Workshop-main/programme/`.

| Modul | Aufgabe |
| --- | --- |
| `pixel_buddy/controls.py` | Entprelltes Auslesen der originalen Button-Pins |
| `pixel_buddy/pet.py` | Beduerfnisse, Aktionen, Stimmung und Spielzustand |
| `pixel_buddy/play.py` | Hauptschleife, Aktionsbilder und Spielanzeige |
| `pixel_buddy/faces.py` | Die drei einfachen Gesichter |
| `pixel_buddy/animation.py` | Blinzeln, Blicke, Sprechen und Uebergaenge |
| `pixel_buddy/display.py` | Originaltreiber-Anbindung |
| `pixel_buddy/link.py` | USB-Befehle vom PC-Chat (nur gepruefte JSON-Befehle) |

Ueber den PC-Chat (Text oder Mikrofon) kann Buddy auch gefuettert, gestreichelt,
schlafen geschickt oder geweckt werden. Das nutzt dieselben Pflegeaktionen wie
der Joystick; der Schiebeschalter hat beim Schlaf immer Vorrang.
| `pixel_buddy/demo.py` | Vorherige reine Gesichterdemo, weiterhin separat nutzbar |

Die Gesichter haben Punktaugen bei Neutral/Sad und Augenboegen bei Happy.
Zwischen Augen und Mund bleibt eine dunkle Luecke. Aktionssymbole, Status und
Spiel verwenden kurzzeitig die ganze Matrix. Alle Funktionen laufen ohne
blockierende Animationspausen. Es gibt keine Pin-Interrupt-Handler.

## PC-Pruefung

`python -m unittest discover -s tests -v`

Prueft Animationen, Originaltreiber-Daten, Entprellung, Pflege, Grenzen,
Schlaf/Tag, Spielpunkte und Abbruch. Hardwarezugriffe werden simuliert;
ein Test auf der echten Platine steht noch aus.

`python tools/preview.py` erstellt die Gesichtervorschau (Pillow nur auf dem PC).
Der alte Farbtest ist weiterhin als `matrix_test.py` vorhanden.
