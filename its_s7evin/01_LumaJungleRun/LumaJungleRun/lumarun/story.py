# Zwischensequenzen der Geschichte (nicht ueberspringbar)
import random
from . import hw, gfx, fx, jungle


def _waves(t):
    """Wellenreihe des Floss-Bildes animieren."""
    shift = (t // 400) % 2
    for x in range(8):
        hw.set(x, 6, gfx.SEA if (x + shift) % 2 else gfx.WHITE)


# Floss schaukelt: (dx, dy) je Schritt; auf und ab im Wechsel, langsam vor und zurueck
RAFT_BOB = ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0), (0, 1), (-1, 1), (-1, 0))
RAFT_BOB_MS = 450
_raft_t = 0          # laeuft weiter, damit das Schaukeln nahtlos in den Sturm uebergeht


def _raft(dt):
    """Floss-Bild mit Wellen und schaukelndem Floss zeichnen."""
    global _raft_t
    _raft_t += dt
    t = _raft_t
    gfx.draw(gfx.RAFT_SCENE)
    for x, y in ((5, 3), (5, 4), (4, 5), (5, 5), (6, 5)):
        hw.set(x, y, gfx.WHITE)
    _waves(t)
    dx, dy = RAFT_BOB[(t // RAFT_BOB_MS) % len(RAFT_BOB)]
    for x in (4, 5, 6):
        hw.set(x + dx, 5 + dy, gfx.RAFT)
    gfx.person(5 + dx, 3 + dy)


TITLE = (("LUMA ", gfx.SKY), ("JUNGLE ", gfx.LEAF), ("RUN", gfx.SHIRT))
TITLE_Y = 1          # oberste Zeile der Schrift
TITLE_MS = 85        # ms pro Spalte


def _title_text():
    """Lauftext "LUMA JUNGLE RUN". Gibt True zurueck, sobald die Mitte gedrueckt wird."""
    cols = gfx.text_columns(TITLE)
    for start in range(-8, len(cols)):
        hw.clear()
        for x in range(8):
            i = start + x
            if 0 <= i < len(cols):
                col = cols[i]
                for y in range(7):
                    if col[y]:
                        hw.set(x, TITLE_Y + y, col[y])
        hw.show()
        t = 0
        while t < TITLE_MS:
            t += hw.tick()
            if "center" in hw.poll():
                return True
    return False


def title():
    """Startbild: Lauftext einmal, danach das schaukelnde Floss, bis Joystick-Mitte gedrueckt wird."""
    pressed = _title_text()
    t = 0
    while True:
        dt = hw.tick()
        t += dt
        _raft(dt)
        hw.show(min(100, t * 100 // 600))   # weich einblenden
        if "center" in hw.poll():
            pressed = True
        if pressed and t >= 600:            # Einblenden immer zu Ende zeigen
            break
    random.seed(hw.now())


def storm():
    # Himmel verdunkelt sich, das Floss schaukelt weiter
    for s in range(0, 101, 5):
        for k in range(2):
            _raft(hw.tick())
            hw.poll()
            dark = list(hw.fb)
            for i in range(64):
                if dark[i] in (gfx.SKY, gfx.WHITE):
                    hw.fb[i] = gfx.mix(dark[i], gfx.STORM, s)
            hw.show()
    for i in range(64):
        if dark[i] in (gfx.SKY, gfx.WHITE):
            dark[i] = gfx.STORM
    # Blitze
    scene = gfx.img(gfx.STORM_SCENE)
    for flash in range(2):
        hw.clear(gfx.WHITE)
        hw.pause(70)
        hw.blit(dark)
        hw.pause(250)
    hw.clear(gfx.WHITE)
    hw.pause(70)
    hw.blit(scene)
    hw.pause(900)
    # die Welle verschluckt das Floss (von rechts nach links)
    for x in range(7, -1, -1):
        for y in range(8):
            hw.set(x, y, gfx.SEA)
        hw.pause(110)
    hw.pause(300)
    hw.fade(500, 100, 0)
    # alles wird schwarz: Rauschen, das langsam verschwindet
    for density in range(50, -1, -3):
        for i in range(64):
            hw.fb[i] = gfx.WHITE if random.randint(0, 99) < density else gfx.BLACK
        hw.pause(110, 60)
    hw.clear()
    hw.pause(1200)


def _beach(person_x, head_y, lying=False):
    gfx.draw(gfx.BEACH)
    if lying:
        hw.set(person_x, head_y, gfx.SKIN)
        hw.set(person_x + 1, head_y, gfx.SHIRT)
    else:
        gfx.person(person_x, head_y)


def beach():
    """Aufwachen am Strand, aufstehen und in den Dschungel gehen."""
    _beach(5, 6, lying=True)
    hw.fade(2000)
    hw.pause(1200)
    for i in range(2):          # blinzeln / regt sich
        _beach(5, 6, lying=True)
        hw.set(6, 6, gfx.mix(gfx.SHIRT, gfx.WHITE, 40))
        hw.pause(200)
        _beach(5, 6, lying=True)
        hw.pause(400)
    _beach(5, 5)                # steht auf
    hw.pause(1000)
    for x in range(4, -2, -1):  # geht nach links in den Dschungel
        head = gfx.BEACH_GROUND[max(x, 0)] - 2
        _beach(x, head)
        hw.pause(380)
    hw.fade(500, 100, 0)


def dizzy():
    """Schwindel-Strudel nach der Beruehrung mit der Schlange."""
    image = gfx.img(gfx.SPIRAL)
    ms = 260
    for i in range(14):
        hw.blit(image)
        hw.pause(ms)
        image = gfx.rotate(image)
        ms = max(90, ms - 20)
    hw.blit(image)
    hw.fade(900, 100, 0)
    hw.clear()
    hw.pause(1500)


def victory(scene):
    """Siegesfeuerwerk und der goldene Affe."""
    fx.fireworks(scene)
    hw.fade(500, 100, 0)
    gfx.draw(gfx.MONKEY)
    hw.fade(1000)
    monkey = gfx.img(gfx.MONKEY)
    for i in range(40):          # funkeln
        hw.blit(monkey)
        for k in range(2):
            x, y = random.randint(0, 7), random.randint(0, 7)
            if monkey[y * 8 + x] == gfx.BLACK:
                hw.set(x, y, gfx.WHITE)
            else:
                hw.set(x, y, gfx.mix(monkey[y * 8 + x], gfx.WHITE, 70))
        hw.pause(90)
    hw.blit(monkey)
    hw.pause(800)
    hw.fade(600, 100, 0)


def _ship(x, deck=None):
    """Schiff mit Rumpf ab Spalte x (3 breit), Segel und Flagge."""
    hw.set(x + 1, 1, gfx.SHIRT)
    hw.set(x + 1, 2, gfx.WHITE)
    hw.set(x + 1, 3, gfx.WHITE)
    hw.set(x + 2, 3, gfx.WHITE)
    for i in range(3):
        hw.set(x + i, 4, gfx.RAFT)
    if deck:
        hw.set(x, 2, gfx.SKIN)
        hw.set(x, 3, gfx.SHIRT)
        hw.set(x + 2, 2, gfx.GOLD)


def ending():
    """Zurueck durch den Dschungel zum Strand, ein Schiff holt die Person ab."""
    # 1. Rueckweg: der Dschungel scrollt nach oben, die Person traegt den goldenen Affen
    decor = jungle.new_decor()
    rows = [jungle.make_row(decor) for _ in range(8)]
    for step in range(28):
        rows.pop(0)
        rows.append(jungle.make_row(decor))
        for y in range(8):
            for x in range(8):
                hw.fb[y * 8 + x] = rows[y][x]
        gfx.person(3, 1)
        hw.set(4, 2, gfx.GOLD)
        hw.pause(200, 100 if step > 2 else 50 + step * 20)
    hw.fade(500, 100, 0)

    # 2. Strand: die Person kommt aus dem Dschungel und geht zum Wasser
    def beach(px, ship_x=None, wave=False, deck=False, sky=None):
        gfx.draw(gfx.END_BEACH)
        if sky:
            for i in range(64):
                if hw.fb[i] == gfx.SKY:
                    hw.fb[i] = sky
        if ship_x is not None:
            _ship(ship_x, deck)
        if px is not None:
            gfx.person(px, 3)
            hw.set(px + 1, 4, gfx.GOLD)
            if wave:
                hw.set(px - 1, 2, gfx.SKIN)

    beach(0)
    hw.fade(600)
    for px in (1, 2, 3):
        beach(px)
        hw.pause(380)
    hw.pause(500)
    # 3. ein Schiff erscheint und haelt an
    for sx in range(8, 4, -1):
        beach(3, sx)
        hw.pause(450)
    for i in range(6):           # winken
        beach(3, 5, wave=i % 2 == 0)
        hw.pause(250)
    # 4. an Bord gehen und davonsegeln
    beach(4, 5)
    hw.pause(400)
    beach(None, 5, deck=True)
    hw.pause(900)
    for sx in range(5, 9):
        beach(None, sx, deck=True)
        hw.pause(450)
    # 5. Sonnenuntergang
    for s in range(0, 101, 10):
        beach(None, sky=gfx.mix(gfx.SKY, gfx.SUNSET, s))
        hw.pause(120)
    hw.pause(800)
    hw.fade(1200, 100, 0)


def the_end():
    """Schlussbild mit Feuerwerk; Joystick-Mitte startet ein neues Spiel."""
    monkey = gfx.img(gfx.MONKEY)
    hw.blit(monkey)
    hw.fade(800)
    fx.fireworks(monkey, spots=((1, 1), (6, 2), (3, 0)), rounds=1)
    hw.blit(monkey)
    hw.show()
    while "center" not in hw.poll():
        hw.tick()
    hw.fade(600, 100, 0)
