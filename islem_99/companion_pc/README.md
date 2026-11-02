# Pixel Buddy: lokaler Ollama-Chat mit LED-Matrix

Diese Anwendung laeuft auf dem **Windows-PC**, nicht auf dem Pico.
Sie verwendet die Python-Standardbibliothek plus `pyserial` (USB) und fuer das
Mikrofon `faster-whisper` und `sounddevice`: kein API-Key, Abo oder Cloud-Backend. Einmalig werden Ollama und Modelldateien aus dem
Internet heruntergeladen. Danach kann der Chat offline laufen.

## Bestehendes Projekt und Umfang

- `main.py` startet weiterhin den Joystick-Haustiermodus auf dem Pico.
- `pixel_buddy/faces.py`: nur `neutral`, `happy`, `sad`.
- `pixel_buddy/animation.py`: Blinzeln, Blickbewegungen, Happy-Zwinkern,
  Uebergaenge. Der Mund bewegt sich nur, waehrend die Stimme spricht.
- `pixel_buddy/play.py`, `pet.py`, `controls.py`: Spiel und Pflege.
- `zhaw_led_matrix/`: unveraenderter Workshop-Treiber und Pinbelegung.

Die AI laeuft nur auf dem PC. Sie waehlt pro Antwort eine Emotion, der PC
sendet daraus einen geprueften Befehl per USB an den Pico, und der Pico zeigt
ihn mit den vorhandenen Gesichtern und Animationen. `companion_pc/` wird vom
MicroPico-Upload ausgeschlossen. Dauerhafte Erinnerungen folgen spaeter.

## Ergebnis der Umgebungspruefung

- Python 3.13.5 vorhanden; rund 63,4 GiB nutzbarer RAM.
- Ollama inzwischen installiert und unter `127.0.0.1:11434` erreichbar.
- `llama3.2:3b` erfolgreich heruntergeladen und lokal getestet.
- Erste Antwort inklusive Modellstart: 56,42 Sekunden.
- Rueckfrage im selben Gespraech: 0,44 Sekunden.
- Kontexttest bestanden: Buddy erinnerte den Testnamen Mia und die bestandene
  Pruefung korrekt. Die Testdaten wurden nicht dauerhaft gespeichert.
- Ollama `/api/ps` meldet rund 2,56 GB Modellbelegung komplett im GPU-Speicher,
  bei 4096 Tokens Kontext. Zeiten gelten fuer diese beiden Testnachrichten.

Der Verbindungscheck wartet jetzt bis zu 20 Sekunden, damit ein frisch
startender Ollama-Dienst nicht vorschnell als unerreichbar gilt.
Die Installation und der Modelldownload unten sind bereits erledigt.
Zum Chatten direkt mit Abschnitt 3 fortfahren.

## 1. Ollama installieren und rein lokal starten

Ollama fuer Windows von der offiziellen Seite installieren:
https://ollama.com/download/windows

Danach ein neues PowerShell-Terminal oeffnen:

```powershell
ollama --version
```

Fuer einen eindeutig lokalen Server: Falls Ollama bereits im Infobereich der
Windows-Taskleiste laeuft, dort zuerst **Quit/Beenden** waehlen. Dann in einem
eigenen Terminal starten und dieses offen lassen:

```powershell
$env:OLLAMA_NO_CLOUD = "1"
$env:OLLAMA_HOST = "127.0.0.1:11434"
ollama serve
```

`OLLAMA_NO_CLOUD` muss beim Start des **Servers** gesetzt sein, nicht nur beim
Start des Python-Chats. Es deaktiviert laut Ollama-Dokumentation Cloudmodelle
und Websuche. Die Variablen oben gelten fuer dieses Terminal und seine Prozesse.
Die Anwendung selbst akzeptiert nur Loopback und die beiden expliziten
llama3.2-Modellnamen; sie nutzt weder Websuche noch andere externe Dienste.

Falls "address already in use" erscheint, laeuft bereits ein Server. Den
vorhandenen Ollama-Prozess regulaer beenden und mit obigen Einstellungen starten.

## 2. Modell herunterladen

In einem zweiten Terminal:

```powershell
ollama pull llama3.2:3b
ollama list
```

Das ist ein einmaliger Modelldownload, kein kostenpflichtiger API-Aufruf.
Die Python-Anwendung installiert und laedt selbst keine Modelle herunter.

## 3. Chat starten

Im normalen VS-Code-PowerShell-Terminal im Projektordner `Project_1`
(nicht im MicroPico-Terminal):

```powershell
python -m companion_pc --check
python -m companion_pc
```

Der Check prueft API-Erreichbarkeit und das installierte Modell, fuehrt aber
noch keine Inferenz aus. Die erste Antwort kann durch das Laden laenger dauern.

```text
Pixel Buddy is awake!
You: Ich heisse Mia und habe heute eine Pruefung bestanden.
Buddy: ...
You: Wie heisse ich?
Buddy: ...
```

Die zweite Antwort dient als praktischer Kontexttest; konkrete Formulierungen
und Antwortqualitaet haengen vom lokalen Modell ab.

| Befehl | Wirkung |
| --- | --- |
| `/clear` | Aktuellen Sitzungskontext loeschen |
| `/check` | Lokalen Server und Modell erneut pruefen |
| `/exit` oder Strg+C | Chat beenden |

Diagnose und alternatives Modell:

```powershell
python -m companion_pc --debug --timeout 240
ollama pull llama3.2:1b
python -m companion_pc --model llama3.2:1b
```

`--debug` zeigt Antwortdauer und Anzahl der gespeicherten Gespraechspaare.
Es schreibt keine Logs. `ollama ps` zeigt nach einer Antwort die CPU-/GPU-Nutzung
des geladenen Modells. `--port` erlaubt einen anderen lokalen Ollama-Port;
entfernte Serveradressen sind nicht konfigurierbar.

## 4. LED-Matrix verbinden

```powershell
python -m pip install pyserial      # einmalig
```

1. In VS Code **MicroPico: Upload Project** ausfuehren (neu: `pixel_buddy/link.py`,
   geaendert: `pixel_buddy/play.py`).
2. **MicroPico: Disconnect** ausfuehren. Solange MicroPico, Thonny oder ein
   Serial-Monitor verbunden ist, ist der COM-Port fuer andere Programme gesperrt.
3. Pico kurz aus- und wieder einstecken. `main.py` startet dann automatisch und
   wartet nebenbei auf USB-Befehle; der Joystickmodus bleibt voll nutzbar.
4. Erst LEDs ohne AI testen, dann chatten:

```powershell
python -m companion_pc --list-ports          # erkannte Picos (USB-VID 2E8A)
python -m companion_pc --no-ai --debug       # nur /emotion-Tests
python -m companion_pc                       # Chat + LEDs, Port automatisch
python -m companion_pc --pico-port COM7      # Port manuell
python -m companion_pc --no-pico             # nur Chat, kein COM-Port
```

Testablauf mit `--no-ai --debug`: `/pico` muss `COM7 verbunden` melden, dann
nacheinander `/emotion happy`, `/emotion excited`, `/emotion love`,
`/emotion sad`, `/emotion curious`, `/emotion sleepy`, `/emotion neutral`.
Nach 3-8 Sekunden kehrt Buddy jeweils selbst in seine normale Stimmung zurueck.

## 5. Stimme

Buddy liest seine Antworten laut vor. Dafuer nutzt er die in Windows eingebaute
Sprachausgabe (System.Speech): offline, kostenlos, ohne zusaetzliches Paket.
Deutsch spricht **Hedda**, Englisch **Zira** (sonst die erste passende Stimme),
jeweils mit etwas hoeherer Tonlage (+25 %) und leicht schnellerem Tempo.
Die Sprache folgt der Spracherkennung des Chats.

| Befehl | Wirkung |
| --- | --- |
| `--no-voice` | Start ohne Stimme |
| `/voice` | Stimme ein-/ausschalten |
| `/say <text>` | Stimmtest, auch mit `--no-ai` |

Waehrend Buddy spricht, bewegt sich auf der Matrix nur der Mund; die Augen zeigen
weiter die Emotion (z. B. happy-Boegen). Ist er fertig, bleibt die Emotion noch
1,5 s und blendet dann zu Idle ueber. Eine neue Nachricht unterbricht ihn sofort.
Emoji und `*Regieanweisungen*` werden nicht vorgelesen.

Technik (`voice.py`): Ein PowerShell-Hilfsprozess bleibt geoeffnet und erhaelt
pro Satz eine base64-JSON-Zeile mit SSML. Er antwortet `DONE`, sobald der Satz
gesprochen ist; dann sendet der PC `{"cmd":"talk","ms":0}` an den Pico.
Unterbrechen beendet den Hilfsprozess; er startet beim naechsten Satz neu (~0,5 s).
Eine natuerlichere, ebenfalls lokale Alternative waere spaeter Piper TTS.

## 6. Mikrofon und Sprachbefehle

```powershell
python -m pip install faster-whisper sounddevice     # einmalig
```

Im Chat **Enter auf leerer Zeile** druecken oder am Pico **den Joystick einmal
druecken** und sprechen. Eine kurze Pause (0,9 s), nochmals **Enter** oder ein
weiterer **Joystickdruck** beendet die Aufnahme, Strg+C bricht ab.
**Doppelt druecken** = Streicheln. Ein Joystickdruck wird erst nach 0,4 s als
einfacher Druck erkannt (Doppeldruck-Erkennung). Waehrend du tippst, wird der
Joystick ignoriert; Druecke waehrend "Buddy denkt ..." werden verworfen.
Tastendruecke waehrend Aufnahme und Antwort werden danach verworfen, damit
kein uebrig gebliebenes Enter Buddy beim Sprechen unterbricht. Ein Enter,
waehrend er spricht, unterbricht ihn dagegen bewusst (du willst etwas sagen). Waehrend der Aufnahme leuchten
auf der Matrix oben links und rechts zwei blaue "Ohren". Danach zeigt Buddy die
Denk-Animation, und der erkannte Text erscheint als `You (Stimme): ...`.

Erkannt wird lokal mit Whisper (faster-whisper, CPU). Das Modell wird beim
ersten Start einmalig von Hugging Face heruntergeladen (`base` ca. 145 MB) und
im Hintergrund geladen; danach laeuft alles offline. Die Aufnahme wird nicht
gespeichert.

| Option | Wirkung |
| --- | --- |
| `--stt-model base` | Standard, ca. 1,2 s pro Satz; kleine Fehler moeglich ("Badi" statt "Buddy") |
| `--stt-model small` | Genauer, ca. 3,8 s pro Satz, ca. 460 MB |
| `--no-mic` | Ohne Spracheingabe |

Nur Deutsch und Englisch: erkennt Whisper eine andere Sprache, wird mit der
aktuellen Chatsprache neu erkannt. Hat niemand gesprochen, bricht die Aufnahme
nach 7 s ab; laengste Aufnahme 15 s.

### Befehle an Buddy

Ob gesprochen oder getippt, Buddy reagiert auf diese Aufforderungen:

| Aktion | Beispiele | Was passiert auf dem Pico |
| --- | --- | --- |
| feed | "Hier, iss einen Keks!", "Möchtest du einen Apfel?", "Here is an apple for you" | Wie Joystick oben: Snack + Kauen, ab 95 satt |
| pet | "Ich streichle dich", "Gib mir eine Umarmung", "Can I pet you?" | Wie Joystick-Druck: Herz, Laune +8 |
| rest | "Mach mal Pause", "Ruh dich kurz aus", "Take a break" | Wie Joystick links: 15 s Ruhe |
| play | "Lass uns spielen!", "Let's play a game" | Wie Joystick rechts: Sternfangspiel (mit Joystick spielen) |
| status | "Wie geht es dir?", "Zeig mir deinen Status" | Wie Joystick unten: Statusbalken |
| sleep | "Geh jetzt schlafen", "Gute Nacht!", "Time for bed" | Schlaf bis "wach auf", Joystickdruck, Schalter oder volle Energie |
| wake | "Wach auf!", "Guten Morgen!", "Wake up" | Aufwachen (nicht gegen den Schiebeschalter) |

Zum Testen ohne AI: `/act feed`, `/act sleep`, `/act wake` usw.

So funktioniert es:
1. Der PC erkennt die Aufforderung mit festen deutschen/englischen Mustern
   (`actions.py`). Erzaehlungen wie "Ich habe Pizza gegessen", "Ich gehe jetzt
   schlafen" oder Verneinungen ("Geh nicht schlafen") loesen nichts aus.
2. Die Aktion laeuft sofort auf dem Pico; er meldet das Ergebnis zurueck
   (`ok`, `full`, `tired`, `busy`, `playing`, `resting`, `sleeping`, `switch`).
3. Erst dann antwortet die AI. Sie bekommt Buddys aktuelle Werte (Futter,
   Energie, Laune) und das Ergebnis mitgeteilt, damit die Antwort passt:
   satt -> lehnt freundlich ab, zu muede -> will nicht spielen.

Warum feste Muster statt AI? Im Test mit `llama3.2:3b` waehlte das Modell nur
6 von 12 Aktionen richtig (Fuettern als Streicheln, "Ich bin so muede" als
Schlafbefehl). Die Muster erkennen alle 30 Testsaetze richtig, darunter 10
Saetze, die bewusst nichts ausloesen duerfen. Neue Formulierungen lassen sich in
`companion_pc/actions.py` ergaenzen.

Chat-Schlaf auf dem Pico: Buddy zeigt das bekannte Schlafgesicht und erholt sich
wie beim Schiebeschalter (+5 Energie pro 10 s). Der Schiebeschalter hat immer
Vorrang: Umlegen beendet den Chat-Schlaf, und in Schalterstellung "Schlaf" kann
"wach auf" ihn nicht wecken.

## 7. Internet: Wetter und Websuche

Buddy kann Wetter abfragen und im Internet suchen. Kostenlos, ohne API-Key,
ohne zusaetzliches Paket (nur Python-Standardbibliothek):

| Was | Dienst | Hinweis |
| --- | --- | --- |
| Wetter | Open-Meteo (Ortssuche + Vorhersage) | offizielle, freie API |
| Websuche | DuckDuckGo (HTML-Ergebnisseite) | keine offizielle API; kann sich aendern oder drosseln |
| Ersatz | Wikipedia-API (Artikelauszug) | wenn DuckDuckGo nichts liefert |

```powershell
python -m companion_pc --city Zuerich     # Heimatort fuer "Wie ist das Wetter?"
python -m companion_pc --no-web           # nie ins Internet
```

Beispiele (gesprochen oder getippt):

| Du sagst | Buddy macht |
| --- | --- |
| "Wie ist das Wetter?" | Wetter heute am Heimatort (`--city`), sonst fragt er nach dem Ort |
| "Wie wird das Wetter morgen in Bern?" | Wetter morgen in Bern |
| "Und übermorgen?" / "And London?" | Nachfrage zur letzten Wetterfrage |
| "Brauche ich morgen einen Regenschirm?" | Wetter morgen am Heimatort |
| "Such mal im Internet, wer das Matterhorn zuerst bestiegen hat" | Websuche |
| "Kannst du nachschauen, wann ...", "Google mal ...", "Look up ...", "Nachrichten über ..." | Websuche |

Wie es funktioniert:
1. Wie bei den Aktionen erkennt der PC eine Internetfrage mit festen Mustern
   (`web.py`). Ins Internet geht es nur bei Wetterwoertern oder ausdruecklichen
   Suchauftraegen. "Ich suche meine Schluessel", "dein aktueller Status" oder
   "Ich habe Pizza gegessen" bleiben lokal.
2. Der Chat zeigt jede Abfrage an (`🌐 Suche im Internet: ...` und die Quelle).
   Gesendet wird nur der Suchbegriff bzw. der Ortsname, nie der Gespraechsverlauf.
3. Die gefundenen Fakten gehen an die lokale AI, die sie kurz in Buddys Worten
   wiedergibt. Nicht erreichbar -> Buddy sagt, dass er es gerade nicht finden konnte.

Grenzen: Die Websuche liefert nur Titel und Kurztexte der ersten Treffer, keine
ganzen Seiten. Fragen zu aktuellen Ereignissen ohne Suchwort beantwortet das
lokale Modell aus seinem eigenen (veralteten) Wissen, und kleine Modelle erfinden
dann manchmal Dinge; fuer Aktuelles deshalb "such mal ..." sagen. Ohne Wetterwort
erkannte Nachfragen ("Und morgen?") funktionieren nur direkt nach einer
Wetterantwort. Manuell testen: `/wetter Lugano`, `/web Hoehe Mount Everest`.

## 8. Spotify per Sprache

Voraussetzungen: **Spotify Premium** (die Web API steuert die Wiedergabe nur
damit) und eine eigene App unter https://developer.spotify.com/dashboard.

Einmalig verbinden:
1. Im Dashboard deine App oeffnen -> **Settings** -> Redirect URI
   `http://127.0.0.1:8888/callback` eintragen und speichern; bei "APIs used"
   **Web API** anhaken.
2. `python -m companion_pc --spotify-login` ausfuehren, die **Client ID**
   einfuegen und im Browser bestaetigen.

Es wird nur die Client ID gebraucht (Login mit PKCE), **nie das Client Secret**.
Zugangsdaten nicht in Chats oder Dateien im Projekt ablegen. Das Token liegt in
`%LOCALAPPDATA%\PixelBuddy\spotify.json` (nicht im OneDrive-Projektordner) und
wird automatisch erneuert. Abmelden: `python -m companion_pc --spotify-logout`.

| Du sagst | Spotify |
| --- | --- |
| "Spiel Bohemian Rhapsody (von Queen)" | Song suchen und abspielen |
| "Spiel was von Queen" / "Play something by Taylor Swift" | Kuenstler |
| "Spiel meine Workout Playlist" | eigene Playlist (sonst oeffentliche Suche) |
| "Spiel das Album Thriller" | Album |
| "Play some jazz music" | passende Playlist |
| "Pause die Musik", "Mach die Musik aus", "Stop the music" | Pause |
| "Mach die Musik wieder an", "Spiel Musik", "Resume" | Weiter |
| "Nächster Song", "Skip", "Spiel ein anderes Lied" | Naechster Titel |
| "Vorheriger Song", "Go back a song" | Vorheriger Titel |
| "Was läuft gerade?", "What's playing?" | Titel ansagen |
| "Lauter" / "Leiser" | Lautstaerke +/-15 % |

Die Spotify-App muss auf einem Geraet offen sein (PC, Handy, Lautsprecher).
Buddy spielt bevorzugt in der **Spotify-App auf diesem PC** (sie meldet sich mit
dem Computernamen), dann auf anderen Geraeten und nur als letzte Wahl in einem
**Web Player** im Browser: Spotify meldet Browser-Tabs ebenfalls als "Computer",
und ein Hintergrund-Tab bleibt wegen Autoplay-Sperren oft stumm. Laeuft die Musik
woanders, wird sie beim Abspielen/Weiterschalten auf dieses Geraet geholt.
Anderes Geraet erzwingen: `--spotify-device "Wohnzimmer"` (Teil des Namens).
`/spotify` zeigt alle Geraete; `->` markiert das verwendete. Bei Erfolg zeigt die Matrix kurz eine blaue Musiknote, danach Buddys
Gefuehl; Buddy sagt kurz, was jetzt laeuft. `/spotify` zeigt den aktuellen Titel.

Bei Musikbefehlen antwortet Buddy **mit festen Saetzen und den echten Angaben von
Spotify**, nicht mit der AI: Im Test behauptete das kleine Modell nach Fehlern,
die Musik laufe, und erfand Songtitel. So sagt Buddy ehrlich "Oh nein, das hat
nicht geklappt: Nichts gefunden fuer ...", oder dass Spotify noch denselben Song
spielt. Klingt ein Satz nach Musikbefehl, wird aber nicht erkannt, fragt Buddy
nach ("Meintest du Musik? ...") und sendet nichts an Spotify. Songs starten
innerhalb ihres Albums, damit "Nächster Song" einen naechsten Titel hat.

"Mach mal Pause" bleibt die Haustierpause und "Spiel mit mir" das Sternfangspiel:
Musikbefehle brauchen ein Musikwort (Musik, Song, Lied, Spotify ...) oder einen
Satz, der mit "Spiel ..." / "Play ..." und einem Titel beginnt.

### Ablauf im Chat

| Zustand | Was der Pico zeigt |
| --- | --- |
| Idle | Normales Haustiergesicht mit Blinzeln und Blicken (wie bisher) |
| Listening | Mikrofon nimmt auf: zwei pulsierende blaue Punkte oben in den Ecken |
| Thinking | Waehrend Ollama rechnet: Blicke links/rechts, kurzes Blinzeln, Mund ruhig |
| Responding | Gewaehlte Emotion, zuerst die passende Animation, dann das Gesicht |
| Zurueck zu Idle | Nach 3-8 s (je nach `intensity`) sanfte Ueberblendung zur Haustierstimmung |

Der Pico faellt auch ohne PC-Befehl nach spaetestens 120 s Thinking auf Idle
zurueck. Joystickaktionen, Spiel und Schlafschalter haben Vorrang vor dem Chat.
Im Schlaf (Schiebeschalter) meldet der PC: Emotionen erst nach dem Aufwecken.

### Emotionen und Animationen

Die AI kann nur aus dieser Liste waehlen. Alles wird auf das abgebildet, was im
bestehenden Pico-Code wirklich existiert (3 Gesichter, vorhandene Icons und
Effekte). Werte wie `sparkling_eyes` gibt es nicht und werden ersetzt.

| emotion | Gesicht | Standard-Animation |
| --- | --- | --- |
| neutral | neutral | none |
| happy | happy | wink (Zwinkern) |
| excited | happy | star (goldener Stern) |
| love | happy | heart (Herz) |
| sad | sad | none |
| curious | neutral | look (Blicke links/rechts) |
| sleepy | neutral | sleepy (gedimmtes Schlafgesicht) |

Validierung (`emotions.py`): Ollama erhaelt ein JSON-Schema (`format`). Danach
prueft der PC jedes Feld: unbekannte Emotion -> `neutral`, unbekannte
Animation -> Standard der Emotion, `intensity` wird auf 0-1 begrenzt, reiner
Text ohne JSON wird als Antwort mit neutralem Gesicht verwendet. Mit `--debug`
zeigt der Chat, welche Felder ersetzt wurden.

Sprache: Der PC erkennt per einfacher Wortliste, ob die letzte Nachricht deutsch
oder englisch ist, und haengt einen kurzen Sprachhinweis an die gesendete
Nachricht an (nicht im Verlauf gespeichert). Das kleine Modell wechselte ohne
diesen Hinweis oft nicht die Sprache.

### USB-Protokoll

Eine ASCII-JSON-Zeile pro Befehl.

| PC -> Pico | Wirkung |
| --- | --- |
| `{"cmd":"ping"}` | Antwort `{"ok":"ping","faces":[...],"anims":[...]}` |
| `{"cmd":"think"}` | Denk-Animation |
| `{"cmd":"show","face":"happy","anim":"star","ms":7500}` | Emotion zeigen (ms: 1000-15000); anim auch `note` |
| `{"cmd":"idle"}` | Sofort zurueck zum Haustiergesicht |
| `{"cmd":"talk","ms":60000}` | Mund bewegt sich (Stimme laeuft); `ms:0` beendet, max. 60 s |
| `{"cmd":"listen"}` | Zuhoer-Anzeige (max. 20 s) |
| `{"cmd":"act","action":"feed"}` | Haustieraktion: feed, pet, rest, play, status, sleep, wake |
| `{"cmd":"bye"}` | Chat beendet: Joystickdruck ist wieder Streicheln |
| `{"cmd":"timer","s":900}` | Timer starten (1-5940 s), `s:0` abbrechen, ohne `s` nur abfragen; Antwort `left`, `was`, `alarm` |

Der PC sendet alle 5 s `ping` als Lebenszeichen. Pico -> PC zusaetzlich:
`{"event":"mic"}` bei einfachem Joystickdruck, solange ein Chat aktiv ist, und
`{"event":"timer"}`, wenn ein Timer abgelaufen ist.

Jede Antwort des Pico enthaelt `"pet":[Futter,Energie,Laune]`, bei Schlaf
`"note":"switch"` oder `"note":"nap"`, nach `act` zusaetzlich `"result"`.

Der Pico antwortet mit `{"ok":...}` oder `{"err":"json|cmd|face|ms|action|s"}`. Er prueft
alle Werte gegen feste Listen; es gibt kein `eval`/`exec` und keine
Moeglichkeit, Python-Code zu senden. Zeilen ueber 160 Zeichen werden verworfen.
Gelesen wird per `select.poll` ohne Warten, max. 256 Zeichen pro Bild;
die 25 Bilder/s laufen weiter.

Der PC liest in einem Hintergrundthread. Bei Abbruch (Kabel gezogen) meldet er
`Verbindung verloren` und versucht alle 2 s neu zu verbinden; der Chat laeuft
waehrenddessen weiter. Beim Beenden sendet er `idle` und schliesst den Port.

### Fehlersuche

| Meldung | Loesung |
| --- | --- |
| `COM7 ist belegt` | Zweites Chat-Fenster schliessen; MicroPico: Disconnect, Thonny/Serial-Monitor schliessen |
| `kein Pico gefunden` | USB-Datenkabel pruefen, `--list-ports`, sonst `--pico-port` |
| `keine Antwort` | Neuen Code hochladen, MicroPico trennen, Pico neu einstecken |
| `Pico ist im REPL` | main.py laeuft nicht: Pico neu einstecken |
| `Buddy schlaeft gerade` | Schiebeschalter umlegen |

## 9. Timer

Nach Pico-Upload (`link.py`, `play.py`) per Stimme oder Tastatur:

| Sagen oder tippen | Wirkung |
| --- | --- |
| "Buddy, stell einen Timer fuer 15 Minuten" / "Set a timer for 10 minutes" | Timer starten (ersetzt einen laufenden) |
| "Timer fuer eine halbe Stunde", "Timer 1 Stunde und 30 Minuten", "Timer 30 Sekunden" | auch Zahlwoerter, Viertel-/halbe Stunde |
| "Erinnere mich in 20 Minuten" | wie Timer |
| "Wie lange noch?" / "How much time is left?" | Restzeit ansagen |
| "Timer abbrechen", "Stopp den Timer", "Cancel the timer" | jederzeit abbrechen, auch waehrend des Alarms |
| `/timer 15`, `/timer 90s`, `/timer`, `/timer stop` | dasselbe ohne Mikrofon |

Anzeige: Minuten gross in Blau (aufgerundet: 15, 14, ... 2); die unterste Reihe
leert sich waehrend jeder Minute. In der letzten Minute zaehlen die Sekunden in
Orange (60 ... 1). Bei 0 blinkt 3 s lang eine rote 0, danach wieder das Gesicht,
und Buddy sagt "Die Zeit ist um!". Maximal 99 Minuten (zwei Ziffern).

Waehrend Buddy spricht, denkt, zuhoert, spielt oder eine Haustieraktion zeigt,
sieht man sein Gesicht; danach wieder die Zahl. Der Countdown selbst laeuft auf
dem Pico (genaue Zeit, auch ohne PC weiter). Der PC sagt "Die Zeit ist um!" nur,
wenn der Chat in dem Moment laeuft; tippst du gerade etwas, kommt die Ansage
nach Enter. Antworten zum Timer sind feste Saetze wie bei Spotify, damit Buddy
nie einen Timer behauptet, den der Pico nicht gestartet hat.

## Kontext und Fehlerbehandlung

Der Verlauf bleibt nur im RAM der laufenden Anwendung. Kein JSON-/SQLite-Memory
wird in diesem Schritt angelegt. Ende oder `/clear` verwerfen den Kontext.
Es bleiben maximal sechs Gespraechspaare und 6000 Zeichen Verlauf erhalten.
Aeltere Paare werden vollstaendig entfernt. Neue Eingaben sind auf 2000 Zeichen
begrenzt. Ollama bekommt ein Kontextfenster von 4096 Tokens und ein Ausgabelimit
von 256 Tokens. Zeichen und Tokens sind nicht identisch; sehr tokenreiche Inhalte
koennen vom Modell zusaetzlich gekuerzt werden.

Verbindungsabbruch, Timeout, fehlendes Modell, HTTP-Fehler, ungueltiges JSON und
leere Antworten erzeugen lesbare Hinweise. Nach einem Fehler waehrend des Chats
bleibt der bisherige Kontext bestehen; die Nachricht nach Beheben erneut senden.
Beim Startfehler endet das Programm mit Exitcode 1; nach Starten von Ollama erneut
ausfuehren. Es gibt keinen stillen Cloud-Fallback und keine Codeausfuehrung aus
Modellantworten.

## Dateien

| Datei | Aufgabe |
| --- | --- |
| `ollama_client.py` | Lokale HTTP-API, Modellcheck, Limits und Fehler |
| `conversation.py` | Buddy-Prompt, Sprachhinweis, begrenzter Sitzungskontext |
| `emotions.py` | Emotionsliste, JSON-Schema, Validierung, Pico-Befehl |
| `pico_link.py` | pyserial: Auto-Erkennung, Lesethread, Wiederverbindung |
| `voice.py` | Windows-Sprachausgabe ueber PowerShell-Hilfsprozess |
| `listen.py` | Mikrofonaufnahme mit Pausenerkennung, Whisper-Erkennung |
| `actions.py` | Sprachbefehle erkennen, Ergebnis fuer die AI beschreiben |
| `web.py` | Wetter (Open-Meteo), Websuche (DuckDuckGo, Wikipedia), Erkennung |
| `console.py` | Eingabezeile, die auch der Joystick beenden kann (Windows, msvcrt) |
| `spotify.py` | Spotify Web API: PKCE-Login, Token, Abspielen, Suche, Geraete |
| `music.py` | Musikbefehle erkennen und ausfuehren |
| `timer.py` | Timerbefehle erkennen (Zahlwoerter, Einheiten), feste Antworten |
| `__main__.py` | Terminal-Chat, Zustaende und Diagnosebefehle |
| `../pixel_buddy/link.py` | Pico: USB-Befehle nicht-blockierend lesen und pruefen |
| `../pixel_buddy/play.py` | Pico: Hauptschleife inkl. Chat-Overlays (`render_link`) |
| `../tests/test_ollama.py` | HTTP-Integrationstests mit lokalem Testserver |
| `../tests/test_link.py` | Protokoll, Overlays, Stimme, Validierung, Serial mit Fake-Port |
| `../tests/test_actions.py` | Aktionen auf dem Pico, Befehlserkennung, Pausenerkennung, Whisper |
| `../tests/test_web.py` | Internetfragen erkennen, Nachfragen, Parsing, Fallbacks (offline) |
| `../tests/test_joystick.py` | Einfach-/Doppeldruck, PC-Lebenszeichen, Eingabezeile |
| `../tests/test_spotify.py` | Musikbefehle, Login, Token, Geraetewahl, Fehler (simuliertes Spotify) |
| `../tests/test_timer.py` | Timerbefehle, Countdown, Alarm, Ziffernanzeige, PC-Link |

## Tests und aktueller Nachweis

```powershell
python -m unittest discover -s tests -v
```

93 Tests (inkl. 8 Timer-Tests): 13 Buddy-, 9 Ollama-, 14 USB-/Emotions-/Stimm-, 16 Aktions-/
Mikrofon-, 7 Internet- (offline mit simulierten Antworten), 10 Joystick- und
9 Spotify-Tests (simuliertes Spotify; ein echter Test mit deinem Konto steht aus). Der Whisper-Test laeuft nur, wenn `BUDDY_STT_SAMPLES` auf einen
Ordner mit `stt_de.wav` / `stt_en.wav` zeigt (16 kHz mono); er wurde mit von der
Windows-Stimme gesprochenen Saetzen erfolgreich ausgefuehrt.
Der Stimmtest startet die echte Windows-Sprachausgabe stumm (Ausgabe ins Leere)
und prueft Fertigmeldung, Unterbrechen und Neustart.
Getestet sind unter anderem Unicode und Kontextuebertragung, Verbindungsfehler,
Timeouts, kaputte Antworten, Kontextbegrenzung und Wiederaufnahme nach Fehlern.
Die HTTP-Tests verwenden einen simulierten Server auf `127.0.0.1`.
Zusaetzlich wurde ein echtes lokales Gespraech mit zwei Nachrichten erfolgreich
getestet; Details und Laufzeiten stehen oben. Mit dem echten `llama3.2:3b` wurden
zwei Gespraeche mit je 7 Nachrichten (DE/EN gemischt) getestet: alle Antworten
gueltiges JSON, keine ersetzten Felder, Sprache korrekt, ca. 0,6-1,4 s pro
Antwort. Die Emotionswahl passte inhaltlich (sad bei Trauer, curious bei Fragen,
sleepy bei Muedigkeit); bei Erfolgen waehlte das Modell mal `love`, mal
`excited`. Die Stimme wurde hoerbar mit zwei echten Antworten getestet (DE/EN,
2,1 s und 4,1 s Sprechdauer). Der Test auf der echten LED-Matrix steht noch aus.

## Offizielle Quellen

- Windows-Installation: https://docs.ollama.com/windows
- Chat-API: https://docs.ollama.com/api/chat
- Lokaler Betrieb, Cloud deaktivieren, Kontext und GPU: https://docs.ollama.com/faq
- Modell: https://ollama.com/library/llama3.2:3b
