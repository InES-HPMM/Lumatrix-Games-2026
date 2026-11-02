# Lumatrix Emoji 🌞❤️🔥

**Eine Mini-KI direkt auf dem Pico der Lumatrix versteht Wörter und zeigt sie als animierte Emojis.** Ein schlagendes Herz für „love“, eine flackernde Flamme für „burning“, Regen aus einer Wolke für „storm“. Sie kennt 107 animierte Emojis und rund 4000 englische Wörter – und sie **lernt dazu**: Korrigiere sie mit dem Joystick, und sie merkt es sich, auch für ähnliche Wörter.

- 🎵 **Emoji-Lyrics:** Zum Song, der auf dem Mac läuft, erscheint zu jedem wichtigen Wort ein Emoji – kurz bevor es gesungen wird.
- 🧩 **Emoji-Rätsel:** Ohne Laptop macht die Lumatrix aus Sprichwörtern und Songtiteln Emojis. Du rätst.
- ⌨️ **Eigene Sätze:** In der Thonny-Shell einen Satz tippen – die KI macht daraus ein Rätsel für deine Freunde.
- 🧠 **Alles auf dem Pico:** Der Laptop schickt nur Wörter. Welches Emoji passt, entscheidet die KI auf dem Pico, in 10–15 ms pro Wort.

## Schnellstart für die Jury (2 Minuten, ohne Mac)

1. Thonny öffnen, **Ansicht → Dateien**.
2. Aus dem Ordner `pico/` diese **7 Dateien** auf den Pico hochladen (Rechtsklick → *Upload to /*):
   `main.py`, `wordmodel.py`, `fastdot.py`, `riddle.py`, `font.py`, `model.bin`, `icons.bin`
   (`icons.py` braucht es auf dem Pico nicht – das ist nur die Quelle für `icons.bin`.)
3. Lumatrix aus- und wieder einstecken.
4. Nach 3 Sekunden erscheint eine grosse grüne **2**, und das **Emoji-Rätsel** startet. Raten, dann **drücken** = Lösung.

Zusammen rund 400 KB der 1.4 MB des Pico. Der Schiebeschalter darf beim Start in jeder Stellung sein.

## Die drei Arten zu spielen

| | 1 · Emoji-Lyrics | 2 · Emoji-Rätsel | Interaktiv · Eigene Sätze |
|---|---|---|---|
| **Was passiert** | Zuerst das Albumcover, dann zu jedem wichtigen Wort im Songtext ein animiertes Emoji, kurz bevor es gesungen wird. Es bleibt, bis das nächste passende Wort kommt | Die Lumatrix macht aus einem Sprichwort oder Songtitel Emojis („time is money“ → 🕐 💰). Du rätst, Drücken zeigt die Lösung | Du tippst einen englischen Satz, die KI macht daraus ein Emoji-Rätsel („I love pizza and the sun“ → ❤️ ☀️) |
| **Was du brauchst** | Mac mit Spotify oder Apple Music und dem Laptop-Programm `host/lumatrix_music.py` | Nur die Lumatrix an irgendeinem USB-Netzteil | Thonny, auf jedem Computer |
| **So startest du es** | Programm starten, Song abspielen (siehe unten) | Einstecken – startet nach 3 s von selbst. Oder mit ↑ / ↓ zur **2** | `main.py` in Thonny ausführen, Satz in die Shell tippen |
| **Im Video** | ✅ „What a Wonderful World“ (Song stumm wegen Urheberrecht, mit meiner Stimme) | ✅ „It's raining cats and dogs“ | – |

Mit **↑ / ↓** wechselst du jederzeit zwischen Modus 1 und 2; zuerst erscheint kurz die Nummer (gelbe **1**, grüne **2**).

## Joystick: alle Funktionen

| Eingabe | 1 · Emoji-Lyrics | 2 · Emoji-Rätsel |
|---|---|---|
| **↑ / ↓** | Modus wechseln (grosse Nummer) | Modus wechseln (grosse Nummer) |
| **← / →** | Vorheriger / nächster Song (das Cover schiebt sich weg) | Vorheriges / nächstes der 37 Rätsel |
| **Drücken** | Der Songtitel läuft durch, in der buntesten Farbe des Covers | Die Lösung läuft in Gelb durch |
| **Doppelklick** | Play / Pause | „Falsches Emoji?“ – der nächste Tipp der KI für dieses Wort (oranger Rahmen) |
| **Halten (0.7 s)** | – | „Richtig, merk dir das!“ – die KI lernt das Wort (grüner Rahmen) |
| **Halten (3 s)** | – | Alles Gelernte vergessen (roter Rahmen) |
| **Schalter umlegen + ↑ / ↓** | Helligkeit in 5-%-Schritten (5–60 %, wird gespeichert); nochmals umlegen = fertig | dasselbe |
| **↑ ↑ ↓ ↓ ← → ← → Drücken** | 🥚 Easter Egg: Das Bild explodiert in Pixel und setzt sich wieder zusammen | 🥚 dasselbe |

Was von selbst passiert:

- Nichts vom Laptop während 3 s → das Emoji-Rätsel startet. Fängt ein Song an zu spielen → zurück zu den Emoji-Lyrics (ausser du hast das Rätsel selbst gewählt).
- Song pausiert → das Bild wird dunkel und atmet. Nichts läuft → eine atmende Musiknote.
- „don't“, „can't“, „never“ … vor einem Wort mit Emoji → zuerst ein pulsierendes ⛔ Stoppschild: „boys don't cry“ → ⛔ 😢.
- In schnellen Zeilen ersetzt ein neues Emoji das alte innerhalb von 1.2 s nur, wenn die KI sicherer ist. So flackert nichts.

## 1 · Emoji-Lyrics (Mac)

Einmal einrichten – Thonny schliessen, im Terminal im entpackten Ordner:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r host/requirements.txt
```

Jedes Mal:

```sh
source .venv/bin/activate
python host/lumatrix_music.py
```

Dann einen Song in Spotify oder Apple Music abspielen. Beim ersten Mal fragt macOS, ob das Terminal Spotify/Musik steuern darf: **OK**. Das Terminal zeigt, was die KI gesehen hat und wie sicher sie ist, zum Beispiel `trees -> tree (100%)`:

| Anzeige | Bedeutung |
|---|---|
| **100 %** | so sicher wie bei den eigenen Stichwörtern des Emojis („sun“ → ☀️) |
| **50 %** | genau an der Schwelle dieses Emojis – das Wenigste, was noch angezeigt wird |
| **unter 50 %** | wird nicht angezeigt |

- **Emojis kommen kurz vor dem Wort.** Synchronisierte Songtexte von [LRCLIB](https://lrclib.net) haben nur eine Zeit pro Zeile. Der Laptop schätzt, wann jedes Wort gesungen wird, und schickt es etwas früher: Der Pico braucht rund 0.1 s zum Nachschlagen und Einblenden, und ein Emoji etwas zu früh fühlt sich pünktlich an, eines zu spät falsch. Gemessen an 20 Songs mit von Hand markierten Wortzeiten sind 82 % der Emojis auf dem Bildschirm, wenn ihr Wort beginnt (vorher 12 %).
- **Eigene Songtexte gehen vor:** Eine Datei `lyrics/<Songtitel>.lrc` wird statt LRCLIB verwendet. Mit einem Wort pro Zeile bekommt jedes Wort seine genaue Zeit (Beispiel: `lyrics/Like The Sun.lrc`, ein CC-lizenzierter Song von Explosive Ear Candy, Wortzeiten aus dem JamendoLyrics-Datensatz).
- **Feinjustieren:** `--lyrics-offset 0.2` zeigt die Emojis 0.2 s früher, `-0.2` später. Mit Bluetooth-Kopfhörern etwa `-0.2`.
- **Crossfade in Spotify** verschiebt die Songposition nach einem automatischen Songwechsel um Sekunden: ausschalten oder einmal Pause/Play.

## 2 · Emoji-Rätsel

- **37 eingebaute Rätsel**, Sprichwörter und Songtitel („time is money“, „heaven and hell“, „boys don't cry“ …). Nichts ist von Hand gezeichnet: Die KI schlägt jedes Wort live nach und zeigt das passendste Emoji. Wörter ohne Emoji („is“, „to“, „the“) werden übersprungen. Jedes Rätsel ergibt mindestens 2 Emojis – ein Test prüft das.
- **Ablauf:** Jedes Emoji 1.5 s (animiert), 0.25 s dunkel dazwischen, 1.5 s Pause, dann von vorn. Die Lösung läuft mit 16 Pixeln pro Sekunde durch.
- **Die KI korrigieren:** Während ein Emoji leuchtet, zeigt ein Doppelklick ihren nächsten Tipp (ihre Top 5 der Reihe nach). Halten bestätigt das gezeigte Emoji: Der Vektor des Wortes und die Emoji-Nummer kommen in `taught.bin` (65 Bytes pro Wort: 64 + 1) und gelten ab sofort in jedem Rätsel und bei den Emoji-Lyrics, auch nach dem Ausstecken.
  Beispiel: Bei „fly me to the moon“ zweimal Doppelklick (Vogel → Schmetterling → Flugzeug), dann halten. Jetzt zeigt „time flies“ 🕐 ✈️.
- **Ähnliche Wörter lernen mit:** Ein gelerntes Wort gilt auch für jedes Wort mit einer Ähnlichkeit (Kosinus) von mindestens 0.62. Lerne „light“ → Sonne, und „lights“, „bright“, „lamp“ folgen. Die eigenen Stichwörter eines Emojis teilen sich seinen Prototyp; lernst du eines davon um, ziehen alle mit („rich“ → Krone, dann auch money, cash, dollar), ihre Nachbarn aber nicht. Neu lernen überschreibt; 3 s halten vergisst alles.

## Interaktiv · Eigene Sätze in der Thonny-Shell

1. `main.py` in Thonny öffnen (Datei → Öffnen → Raspberry Pi Pico).
2. **Ausführen (F5).** In der Shell erscheint `HELLO lumatrix-music`.
3. Unten in die Shell einen englischen Satz tippen, zum Beispiel `I love pizza and the sun`, dann Enter.
4. Die Lumatrix zeigt die grüne **2** und dann deinen Satz als Emojis: ❤️ ☀️. **Drücken** zeigt den Satz. Findet die KI kein einziges Emoji, läuft der Satz gleich durch.
5. **← / →** führt zurück zu den eingebauten Rätseln. Zum Schluss in Thonny **Stopp** drücken.

So kann jede und jeder die KI mit eigenen Wörtern testen – ohne Mac.

## So funktioniert die KI auf dem Pico

```
Mac, einmal:  Apples Wort-Embedding ──▶ model/build_model.py ──▶ pico/model.bin (rund 320 KB)
              (57 000 Wörter × 300 Zahlen)   Nachbarn, PCA, int8, Schwelle pro Emoji

Auf dem Pico: "burning" ──▶ binäre Suche ──▶ 64 Zahlen ──▶ Vergleich mit 107 Emojis ──▶ 🔥
                            in model.bin      (int8)        (viper-Skalarprodukte, 10–15 ms)
```

macOS hat ein eingebautes englisches Wort-Embedding: Jedes Wort ist eine Liste von 300 Zahlen, und Wörter mit ähnlicher Bedeutung haben ähnliche Zahlen („storm“ liegt neben „rain“, „burning“ neben „fire“). Für einen Pico ist das viel zu gross. `model/build_model.py` schrumpft es:

1. **Behalten, was zählt.** Jedes Emoji in `pico/icons.py` hat 4 bis 12 Stichwörter, zusammen rund 770. Das Modell behält diese und ihre nächsten Nachbarn – so findet es rund 800 weitere Wörter selbst (rattlesnake → Schlange, streetcar → Zug, bawling → Weinen). Häufige Füllwörter fliegen raus (`model/stopwords.txt`). Dazu kommen rund 2500 stille Wörter ohne eigenes Emoji – denen kannst du eines beibringen.
2. **PCA** presst jedes Wort von 300 auf 64 Zahlen, und jede Zahl wird als ein Byte gespeichert (int8).
3. **Prototypen.** Der Prototyp eines Emojis ist der Durchschnitt seiner Stichwörter.
4. **Jedes Emoji lernt seine eigene Schwelle.** Ein enges Emoji (Rose: roses, petals, bouquet) braucht ein näheres Wort als ein lockeres (Sturm: thunder, lightning). Die Schwelle liegt bei 85 % der durchschnittlichen Ähnlichkeit seiner 5 ähnlichsten Wörter. Mit einer einzigen Schwelle für alle kamen vage Wörter durch („feel“ zeigte traurig, „sky“ Regen); auf von Hand bewerteten Songtexten stieg der Anteil richtiger Emojis von 68 % auf 98 %.

Auf dem Pico sucht `pico/wordmodel.py` das Wort per binärer Suche direkt im Flash (`model.bin` ist grösser als der ganze RAM), probiert andere Formen („flames“ → „flame“, „burnin'“ → „burning“, „cried“ → „cry“) und vergleicht die 64 Zahlen mit allen 107 Prototypen. Die Skalarprodukte laufen als Maschinencode (`pico/fastdot.py`, MicroPythons viper-Compiler, nur Ganzzahlen): **10–15 ms pro Wort auf der Lumatrix** statt rund 55 ms in normalem Python.

**Lernen auf dem Pico.** `teach(wort, emoji)` speichert den Vektor des Wortes in `taught.bin`. Ab dann zeigen dieses Wort und alle Wörter mit einer Ähnlichkeit von mindestens 0.62 das gelernte Emoji – ein „Few-Shot-Gedächtnis“ neben den Prototypen.

Emojis oder Stichwörter ändern: `pico/icons.py` bearbeiten, dann `pip install numpy`, `python model/build_icons.py` und `python model/build_model.py`, und die Dateien neu auf den Pico kopieren.

## Animierte Emojis

`pico/icons.py` enthält 107 Emojis mit zusammen 380 Bildern, gezeichnet als 8×8-Pixel-Art mit 22 Farben: ein schlagendes Herz, eine flackernde Flamme, ein funkelnder Mond, eine Sonne, die im Meer versinkt, ein pulsierendes Stoppschild. Jedes hat eine Bildzeit und einen Ablauf (Schleife, hin und her oder einmal). `model/build_icons.py` packt sie in `icons.bin` (25 KB, ein Byte pro Pixel), denn 107 animierte Emojis als Python-Text würden den RAM des Pico sprengen. `docs/emoji-set.png` zeigt alle auf einen Blick.

## Code-Tour

Der clevere Teil sind rund 280 Zeilen (`wordmodel.py` und `fastdot.py`):

| Datei | Was drin ist |
|---|---|
| `pico/wordmodel.py` | `TinyBrain`: Wort im Flash nachschlagen, nächster Prototyp, Schwelle pro Emoji, Lernen und Vergessen |
| `pico/fastdot.py` | der viper-Kern für die Skalarprodukte (rund 30 Zeilen, die zu Maschinencode werden) |
| `pico/riddle.py` | `QuizMaster`: das Emoji-Rätsel und deine eigenen Sätze |
| `pico/main.py` | `Lumatrix`, die Show: `EmojiZoo` (die Bilder), `LedWall` (die 64 LEDs mit Gamma und Stromlimit), `Joystick`, und für das Easter Egg `Konami` und `Kaboom` |
| `model/build_model.py` | Apple-Embedding → PCA → int8, Schwellen aus den Daten gelernt |
| `host/lumatrix_music.py`, `host/lyrics.py` | das Laptop-Programm: Song, Cover, Songtext, Timing |

In `wordmodel.py` und `riddle.py` heisst ein Emoji *symbol*, in `main.py` heissen die animierten Bilder *icons*.

## Wenn etwas nicht klappt

| Du siehst | Lösung |
|---|---|
| `If Thonny is open, close it` | Thonny belegt noch die USB-Verbindung. Thonny schliessen. |
| `The Lumatrix doesn't answer` | Das Programm ist noch nicht auf dem Pico: die 7 Dateien kopieren (siehe Schnellstart). |
| Nur eine atmende Note, kein Rätsel | `model.bin` oder `icons.bin` fehlt auf dem Pico (er meldet `NOMODEL` / `NOICONS`). |
| `Couldn't ask Spotify …` (-1743) | **Systemeinstellungen → Datenschutz & Sicherheit → Automation**: dem Terminal erlauben, Spotify/Musik zu steuern. |
| Keine Emojis zum Song | Läuft das Laptop-Programm? Ist Modus **1** gewählt (↑ / ↓)? Hat der Song synchronisierte Songtexte (das Terminal meldet `Lyrics: found.`)? |
| Emojis Sekunden daneben | Crossfade in Spotify ausschalten oder einmal Pause/Play. |
| Zu hell / zu dunkel | Schalter umlegen und ↑ / ↓ (5 bis 60 %). |

## Tests

52 Tests, ganz ohne Lumatrix – sie spielen auch das Pico-Programm mit simulierter Hardware durch. Zuerst die venv aus Abschnitt 1 aktivieren, sonst fehlt pyserial:

```sh
source .venv/bin/activate
python -m unittest discover -s host
```
