# CATCH 64 – Start here

**Deine Verbindung. Deine Reserve. Dein perfekter Aufbruch.**

CATCH 64 berechnet aus Schweizer Live-Fahrplandaten, persoenlicher Gehzeit und
Sicherheitsreserve die naechste realistisch erreichbare Verbindung. Auf der
Lumatrix bleibt danach nur die wichtigste Information stehen: die Minuten bis
zum Losgehen.

Die originale Lumatrix-Hardware bleibt unveraendert. Alle Dateien sind
lesbarer Sourcecode; es werden keine kompilierten Programme mitgeliefert.

## 1. Drei Dateien auf die Lumatrix kopieren

In Thonny diese Dateien aus `1_PICO` auf dem Raspberry Pi Pico speichern:

- `config.py`
- `catch_logic.py`
- `main.py`

Die Namen muessen exakt gleich sein. Danach Soft-Reboot ausfuehren und Thonny
schliessen, damit der Computer den USB-Port verwenden kann.

Der Computer-Starter fuehrt beim Verbinden zusaetzlich selbst einen sicheren
Soft-Reboot aus. Auch wenn die Lumatrix zuvor nur `>>>` zeigt, wird `main.py`
dadurch automatisch gestartet.

Ein blaues `C` bedeutet: CATCH 64 wartet auf den Computer. Nach acht Sekunden
startet automatisch ein Offline-Testdatensatz, damit die Hardware immer
vorfuehrbar bleibt.

## 2. Computerprogramm starten

Im Ordner `2_COMPUTER` den passenden Sourcecode-Starter oeffnen:

- Windows: `CATCH64_starten_WINDOWS.bat`
- Ubuntu: `CATCH64_starten_UBUNTU.sh`
- macOS: `CATCH64 starten.command`

Beim ersten Start werden nur die freien Python-Bibliotheken `pyserial` und
`certifi` lokal in `.venv` installiert. Danach oeffnet sich die
Einrichtungsseite im Browser.
Dieser lokale `.venv`-Ordner gehoert nicht in die Einreichung.

## 3. Persoenlich einrichten

Im Browser werden eingestellt:

- Start und Ziel (mit Haltestellensuche)
- Gehzeit bis zur Haltestelle
- persoenliche Sicherheitsreserve
- optional nur Direktverbindungen

Nach dem Speichern wird die Verbindung sofort neu berechnet. Niemand muss eine
Python-Datei bearbeiten.

## 4. Anzeige und Joystick

Die Linie erscheint nach einer Auswahl gut lesbar fuer rund 2,2 Sekunden pro
Zweiergruppe. Anschliessend bleibt die Aufbruchzeit ruhig stehen.

- **rechts:** eine spaetere Verbindung
- **links:** ohne Funktion
- **Mitte:** naechste noch erreichbare Verbindung
- **oben:** Abfahrt in Minuten
- **unten:** Gleis

Abfahrtszeit und Gleis bleiben jeweils fuenf Sekunden sichtbar. Danach kehrt
CATCH 64 automatisch zur ruhigen Aufbruchzeit zurueck.

Farben der Aufbruchzeit:

- gruen: mehr als 5 Minuten
- orange: 2 bis 5 Minuten
- rot: jetzt oder in einer Minute losgehen

Verspaetung, Gleiswechsel und Ausfall werden nur bei einer echten Aenderung
kurz eingeblendet. Danach kehrt CATCH 64 zur ruhigen Hauptinformation zurueck.

Beim Minutenwechsel rollt nur die veraenderte Ziffer langsam nach unten; die
neue Ziffer kommt von oben. In der letzten Minute wechselt CATCH 64 auf einen
exakten roten Sekundencountdown von `60` bis `01`. Bei `00` erscheint ein
ruhiger roter Aufbruchspfeil. Er bedeutet ausschliesslich "jetzt los" und gibt
keine reale Gehrichtung vor. Gehzeit und Reserve sind zu diesem Zeitpunkt
bereits vollstaendig abgezogen. Der Pfeil bleibt nur acht Sekunden als klares
Aktionssignal sichtbar; er schenkt keine zusaetzliche Zeit. Danach waehlt
CATCH 64 automatisch die naechste erreichbare Verbindung. `XX` bleibt
ausschliesslich das eindeutige Signal fuer einen gemeldeten Ausfall.

Die Berechnung ist immer dieselbe:

```text
Zeit bis Abfahrt - Gehzeit - persoenliche Reserve = Zeit bis Aufbruch
```

## Jury-Demomodus

Ohne Live-Daten kann auf allen Systemen derselbe Ablauf gezeigt werden:

```text
python catch64.py --demo
```

Die Demo zeigt Normalbetrieb, Verspaetung, Gleiswechsel und Ausfall. Der
normale Starter verwendet immer echte Live-Daten.

## Tests

Aus `CATCH64_FINAL` starten:

```text
python3 -m unittest discover -s tests -v
python3 check_submission.py
```

Live-Fahrplandaten: transport.opendata.ch / Schweizer OeV-Open-Data.

## Abgabe bei den Lumatrix Games

Fuer die Jury wird der komplette Ordner als `.zip` eingereicht. Er enthaelt
nur lesbaren Python-, MicroPython-, HTML- und Dokumentations-Sourcecode. Nicht
mitliefern: `.venv`, `__pycache__`, `.pyc` oder andere erzeugte Dateien.

Zur gueltigen Wettbewerbseinreichung gehoeren zusaetzlich:

- ein Hochformatvideo von 15 bis 60 Sekunden auf der echten Lumatrix,
- ein Discord-Beitrag in `#challenge-arena` mit Projektnamen und einem Satz,
- das vollstaendig ausgefuellte Einreichungsformular.

Die Jury kann den Live-Modus auf Windows oder Ubuntu mit den dortigen Startern
ausfuehren. Der reproduzierbare `--demo`-Modus bleibt als Offline-Rueckfallebene
vorhanden; beide Modi verwenden denselben MicroPython-Renderer auf der
unveraenderten Lumatrix.
