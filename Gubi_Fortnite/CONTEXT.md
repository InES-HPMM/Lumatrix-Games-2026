# Lumatrix Dash

Eine Umsetzung von Geometry Dash für die 8×8-LED-Matrix der ZHAW Lumatrix.

## Language

### Spielfigur

**Spielfigur**:
Das Pixel, das der Spieler durch das Level steuert. Sie hat immer genau einen Modus, und ihre Farbe zeigt an, welcher es ist.
_Avoid_: Player, Icon, Charakter

**Vorausschau**:
Die sechs Spalten rechts der Spielfigur, die zeigen, was als Nächstes kommt. Die Spielfigur steht immer in der zweiten Spalte von links, das Level zieht an ihr vorbei.

**Modus**:
Die Form der Spielfigur, die festlegt, wie sie auf Eingaben reagiert. Es gibt Würfel, Schiff, Spider, Swing und Robot.
_Avoid_: Gamemode, Form, Vehikel

**Würfel**:
Modus, in dem die Spielfigur auf Eingabe springt und sonst auf Blöcken läuft. Ein Sprung ist höchstens 2 Pixel hoch und 4 Spalten lang. Bei gehaltener Eingabe springt der Würfel nach jeder Landung sofort erneut.
_Avoid_: Cube, Block (Block ist ein Levelelement)

**Schiff**:
Modus, in dem die Spielfigur steigt, solange die Eingabe gehalten wird, und sonst sinkt, jeweils ein Pixel pro Spalte und ohne Trägheit. An Blöcken über oder unter ihr gleitet sie gefahrlos entlang.
_Avoid_: Ship, Rakete, Flieger

**Eingabe**:
Die einzige Spieleraktion. Sie ist aktiv, solange irgendeine Joystick-Richtung oder die Mitte gedrückt ist. Im Würfel löst sie einen Sprung aus, im Schiff lässt sie die Spielfigur steigen.
_Avoid_: Klick, Tap, Sprungtaste

**Spider**:
Modus, in dem die Spielfigur auf Blöcken oder am Rand läuft, unten oder kopfüber oben. Jeder neue Druck der Eingabe kehrt ihre Schwerkraft um und versetzt sie in derselben Spalte zum nächsten Block oder Rand in der neuen Richtung. Gehaltene Eingabe bewirkt nichts.
_Avoid_: Spinne

**Swing**:
Modus, in dem die Spielfigur fliegt und jeder neue Druck der Eingabe die Schwerkraft umkehrt. Nach jedem Wechsel fliegt sie eine Spalte geradeaus, bevor sie sich in die neue Richtung bewegt; dieses Pendeln unterscheidet sie vom Schiff. An Blöcken und am Rand gleitet sie gefahrlos entlang, gehaltene Eingabe bewirkt nichts.
_Avoid_: Swingcopter, Schaukel

**Robot**:
Modus, in dem die Spielfigur springt und umso höher steigt, je länger die Eingabe gehalten wird, höchstens 3 Pixel. Jeder Sprung braucht einen neuen Druck, gehaltene Eingabe springt nach der Landung nicht erneut.
_Avoid_: Roboter

**Modusfarbe**:
Die Farbe, die zu einem Modus gehört, wie im Original: Würfel grün, Schiff pink, Spider lila, Swing gelb, Robot weiß. Spielfigur und Portal eines Modus haben immer die Modusfarbe, und kein anderes Levelelement verwendet eine Modusfarbe.

**Portal**:
Levelelement, das eine ganze Spalte in der Modusfarbe des Ziel-Modus füllt und beim Durchqueren den Modus der Spielfigur wechselt. Es ist durchlässig und kann nicht verpasst werden.
_Avoid_: Tor, Gate

### Levelelemente

**Levelelement**:
Ein nicht leeres Pixel des Levels; nur das Portal belegt eine ganze Spalte. Es gibt Block, Spitze, Sprungpad, Sprungring und Portal.
_Avoid_: Objekt, Tile, Hindernis

**Block**:
Levelelement in Blau, auf dem die Spielfigur stehen kann. Wer seitlich dagegen fährt, stirbt.
_Avoid_: Plattform, Wand, Boden

**Rand**:
Die unsichtbare Fläche direkt über der obersten und unter der untersten Zeile der Matrix. Er verhält sich wie ein Block, deshalb werden Boden und Decke nicht gezeichnet und alle 8 Zeilen sind Spielfläche.
_Avoid_: Boden, Decke, Bildschirmrand

**Spitze**:
Levelelement in Rot. Jede Berührung ist tödlich.
_Avoid_: Spike, Stachel, Dorn

**Sprungpad**:
Levelelement in Orange, das beim Darüberfahren ohne Eingabe einen hohen Sprung von 4 Pixeln auslöst. Es wirkt nur auf Würfel und Robot, alle anderen Modi ignorieren es.
_Avoid_: Pad, Trampolin

**Sprungring**:
Levelelement in Cyan, das einen normalen Sprung des Modus von der aktuellen Höhe aus auslöst, wenn ein neuer Druck der Eingabe erfolgt, während die Spielfigur im selben Pixel ist. Es wirkt nur auf Würfel und Robot, alle anderen Modi ignorieren es.
_Avoid_: Orb, Ring, Kugel

### Level

**Level**:
Eine von Hand entworfene, feste Strecke mit Start und Ziel, die bei jedem Versuch genau gleich abläuft.
_Avoid_: Map, Stage, Strecke

**Stereo Madness**:
Das Level in der linken Stellung der Levelwahl. Es ist dem ersten offiziellen Level von Geometry Dash nachempfunden: Die Abschnitte kommen in der Originalreihenfolge vor, sind aber für 8×8 neu gesetzt (kürzer, mehr Abstand, alles in sichtbarer Höhe). Startmodus ist der Würfel; zwei Schiff-Abschnitte liegen wie im Original bei etwa 29–46 % und 85–100 %.

**Skeletal Shenanigans**:
Das Level in der rechten Stellung der Levelwahl, dem gleichnamigen Event-Level aus Geometry Dash 2.2 nachempfunden. Startmodus ist der Spider; danach folgen wie im Original Swing und Robot, die Folge wiederholt sich, und das Level endet im Würfel.

**Startmodus**:
Der Modus, in dem die Spielfigur einen Versuch beginnt. Er ist pro Level festgelegt, und seine Modusfarbe färbt den Fortschrittsbalken dieses Levels.

**Tempo**:
Die Anzahl Spalten pro Sekunde, mit der ein Level an der Spielfigur vorbeizieht. Jedes Level hat ein eigenes, festes Tempo (zu Beginn 7).
_Avoid_: Geschwindigkeit, Speed

**Levelwahl**:
Die Stellung des Schiebeschalters. Sie bestimmt, welches Level gespielt wird.
_Avoid_: Menü, Levelauswahl

### Spielablauf

**Versuch**:
Ein Durchlauf eines Levels von seinem Anfang bis zum Tod oder zum Ziel.
_Avoid_: Attempt, Runde, Leben

**Tod**:
Das Ende eines Versuchs durch Berührung einer Spitze, durch seitliches Auffahren auf einen Block oder, bei Würfel und Robot, durch einen Stoß von unten gegen einen Block. Bei diagonaler Bewegung zählt zuerst die waagrechte, dann die senkrechte Richtung. Die Matrix blitzt rot auf, dann erscheint der Fortschrittsbalken, danach beginnt der nächste Versuch.
_Avoid_: Crash, Game Over

**Fortschritt**:
Der Anteil des Levels, den die Spielfigur im aktuellen Versuch durchquert hat.
_Avoid_: Prozent, Score, Punkte

**Fortschrittsbalken**:
Die Anzeige des Fortschritts nach einem Tod und im Wartezustand. Sie füllt die Matrix zeilenweise, ein Pixel entspricht 1/64 des Levels.

**Bestmarke**:
Der größte Fortschritt, der in einem Level bisher erreicht wurde. Sie bleibt über das Ausschalten hinweg erhalten, bis sie zurückgesetzt wird. Zurückgesetzt wird sie, indem man beim Einschalten die Eingabe hält; das betrifft nur das Level der aktuellen Levelwahl. Sie wird im Fortschrittsbalken als gedimmtes Pixel gezeigt. Es gibt keine Checkpoints, jeder Versuch beginnt am Levelanfang.
_Avoid_: Highscore, Rekord, Best

**Ziel**:
Das Ende eines Levels. Wer es erreicht, sieht ein grünes Feuerwerk und „100%“ als Lauftext. Die Bestmarke steht danach auf 100 %, und die Matrix wartet auf eine Eingabe, bevor der nächste Versuch beginnt.
_Avoid_: Finish, Level Complete, Ende

**Wartezustand**:
Der Zustand zwischen Versuchen, in dem die Matrix den Fortschrittsbalken mit der Bestmarke des gewählten Levels zeigt und auf eine Eingabe wartet. Man gelangt beim Einschalten, beim Umlegen der Levelwahl und nach dem Ziel hinein, nicht aber nach einem Tod. Ein durch die Levelwahl abgebrochener Versuch zählt nicht.
_Avoid_: Menü, Startbildschirm, Pause, Idle
