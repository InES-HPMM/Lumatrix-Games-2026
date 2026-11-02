"""
TRON - Lichtmotorrad-Duell auf der 8x8-Matrix

Steuerung
    Joystick   Richtung ändern (Rückwärts ist nicht möglich)
    Mitte      Spiel starten
    Schalter   Schwierigkeit (wird beim Start eines Matches gelesen)
               Titelbild: Mitte leuchtet GRÜN = leicht, ROT = schwer

Regeln
    Du (Cyan) und die KI (Orange) starten an zufälligen Orten und fahren gleichzeitig los und ziehen eine Lichtspur.
    Wer gegen Wand oder Spur fährt, verliert die Runde. Wer zuerst 3 Runden
    gewinnt, gewinnt das Match. Das Spiel wird nach jedem Schritt schneller.

Ohne Eingabe startet nach einigen Sekunden ein Demo (Attract-Mode).
Jeder Tastendruck beendet das Demo.

"""

import random
from time import sleep_ms, ticks_ms, ticks_diff

from zhaw_led_matrix import Button, CharacterTable, ColorTable, LedMatrix

# ---------------------------------------------------------------- Einstellungen
BRIGHTNESS = 20  # 0..100 (Prozent); niedrig halten, sonst belastet es USB
HARD_WHEN_SWITCH = 0  # 0: Schalter zieht Pin auf GND = schwer. Auf 1 setzen, falls vertauscht
WINS_NEEDED = 3  # Maximal 3 (das Punktebild hat 3 Felder pro Seite)
STEP_MS_EASY = 380  # Startgeschwindigkeit: Millisekunden pro Schritt
STEP_MS_HARD = 300
MIN_STEP_MS = 160  # So schnell wird es höchstens
SPEED_UP_MS = 5  # So viel schneller pro Schritt
HARD_MISTAKE = 0.04  # Schwer: Wahrscheinlichkeit für einen Zufallszug (macht die KI schlagbar)
IDLE_TO_DEMO_MS = 15000  # Leerlauf bis zum Demo

# Farben (vor der Helligkeitsstufe)
P_HEAD = (0, 255, 255)
P_TRAIL = (0, 70, 200)
A_HEAD = (255, 140, 0)
A_TRAIL = (190, 30, 0)
EMPTY = (60, 60, 60)

# ---------------------------------------------------------------- Spielfeld
# Spielfeld-Index i = y*8 + x mit y=0 OBEN. Die Matrix hat y=0 UNTEN (siehe px()).
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3
DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)

ABORT, PLAYER_WIN, AI_WIN, DRAW = 0, 1, 2, 3


# Startpunkte: (x, y, Richtung), alle fahren nach innen
SPAWNS = (
    (1, 6, UP), (6, 1, DOWN), (1, 1, DOWN), (6, 6, UP),
    (1, 3, RIGHT), (6, 4, LEFT), (3, 6, UP), (4, 1, DOWN),
)


def random_spawn():
    """Zwei verschiedene Startpunkte, nie in derselben Spalte oder Zeile."""
    while True:
        s1 = random.choice(SPAWNS)
        s2 = random.choice(SPAWNS)
        if s1[0] != s2[0] and s1[1] != s2[1]:
            return ((s1[1] * 8 + s1[0], s1[2]), (s2[1] * 8 + s2[0], s2[2]))


def _build_neighbours():
    result = []
    for i in range(64):
        x, y = i & 7, i >> 3
        near = []
        for d in range(4):
            nx, ny = x + DX[d], y + DY[d]
            if 0 <= nx < 8 and 0 <= ny < 8:
                near.append(ny * 8 + nx)
        result.append(tuple(near))
    return tuple(result)


NEIGH = _build_neighbours()


def step(i, d):
    """Feld in Richtung d neben Feld i, oder -1 außerhalb des Spielfelds."""
    x = (i & 7) + DX[d]
    y = (i >> 3) + DY[d]
    if 0 <= x < 8 and 0 <= y < 8:
        return y * 8 + x
    return -1


# ---------------------------------------------------------------- Eingabe
class Pad:
    """Joystick mit Flankenerkennung (meldet nur neue Betätigungen)."""

    def __init__(self):
        self._pins = (Button.up, Button.right, Button.down, Button.left)
        self._prev = [False, False, False, False]
        self._prev_center = False

    def poll(self):
        """Gibt (Richtung oder -1, Mitte neu gedrückt) zurück."""
        direction = -1
        for d in range(4):
            now = self._pins[d].value() == 0
            if now and not self._prev[d] and direction < 0:
                direction = d
            self._prev[d] = now
        c = Button.center.value() == 0
        center = c and not self._prev_center
        self._prev_center = c
        return direction, center


def is_hard():
    return Button.switch.value() == HARD_WHEN_SWITCH


# ---------------------------------------------------------------- Anzeige
def px(m, i, color):
    """Spielfeldzelle i zeichnen (y spiegeln, damit oben auch oben ist)."""
    m[i & 7, 7 - (i >> 3)] = color


def scale(color, f):
    return (int(color[0] * f), int(color[1] * f), int(color[2] * f))


def render(m, grid, p, a):
    m.clear()
    for i in range(64):
        v = grid[i]
        if v:
            px(m, i, P_TRAIL if v == 1 else A_TRAIL)
    px(m, p, P_HEAD)
    px(m, a, A_HEAD)
    m.apply()


def crash_anim(m, grid, p_crashed, a_crashed):
    """Die Spur des Verlierers blinkt weiß/rot."""
    for k in range(6):
        m.clear()
        for i in range(64):
            v = grid[i]
            if not v:
                continue
            if (v == 1 and p_crashed) or (v == 2 and a_crashed):
                px(m, i, ColorTable.WHITE if k % 2 == 0 else (120, 0, 0))
            else:
                px(m, i, P_TRAIL if v == 1 else A_TRAIL)
        m.apply()
        sleep_ms(130)


def countdown(m):
    for glyph in (CharacterTable.THREE, CharacterTable.TWO, CharacterTable.ONE):
        m.clear()
        m.draw_list(glyph, ColorTable.WHITE, offset=(1, 0))
        m.apply()
        sleep_ms(500)


def show_score(m, player_score, ai_score):
    m.clear()
    for k in range(WINS_NEEDED):
        x0 = k * 3
        pc = P_HEAD if k < player_score else EMPTY
        ac = A_HEAD if k < ai_score else EMPTY
        for dx in (0, 1):
            for y in (5, 6):  # Spieler oben
                m[x0 + dx, y] = pc
            for y in (1, 2):  # KI unten
                m[x0 + dx, y] = ac
    m.apply()


def scroll(m, text, color):
    glyphs, length = CharacterTable.convert_str(text)
    m.move_across(glyphs, length, colors=color, delay_ms=55)


# ---------------------------------------------------------------- KI
def voronoi(grid, a, b):
    """
    Wie viele freie Felder erreicht a vor b (minus umgekehrt)?
    Gleichzeitig von beiden Köpfen aus Ring für Ring ausbreiten.
    Felder, die beide gleichzeitig erreichen, zählen für niemanden.
    """
    owner = bytearray(64)
    owner[a] = 1
    owner[b] = 2
    fa = [a]
    fb = [b]
    score = 0
    while fa or fb:
        ca = set()
        cb = set()
        for i in fa:
            for j in NEIGH[i]:
                if grid[j] == 0 and owner[j] == 0:
                    ca.add(j)
        for i in fb:
            for j in NEIGH[i]:
                if grid[j] == 0 and owner[j] == 0:
                    cb.add(j)
        both = ca & cb
        for j in both:
            owner[j] = 3
        fa = []
        for j in ca:
            if j not in both:
                owner[j] = 1
                score += 1
                fa.append(j)
        fb = []
        for j in cb:
            if j not in both:
                owner[j] = 2
                score -= 1
                fb.append(j)
    return score


def ai_move(grid, me, my_dir, opp, hard, mistake=HARD_MISTAKE):
    """Richtung wählen. Leicht: meist geradeaus. Schwer: größtes eigenes Revier."""
    options = []
    for d in range(4):
        if d == (my_dir + 2) % 4:
            continue
        n = step(me, d)
        if n >= 0 and grid[n] == 0:
            options.append((d, n))

    if not options:
        return my_dir  # kein Ausweg

    # Felder meiden, die der Gegner im selben Schritt auch betreten könnte
    # (sonst gibt es zu viele Frontal-Remis), sofern es Alternativen gibt
    safe = [o for o in options if o[1] not in NEIGH[opp]]
    if safe:
        options = safe
    if len(options) == 1:
        return options[0][0]

    if hard and random.random() > mistake:
        best_dir = options[0][0]
        best_score = -1000.0
        for d, n in options:
            s = voronoi(grid, n, opp)
            if d == my_dir:
                s += 0.3  # geradeaus leicht bevorzugen
            s += random.random() * 0.2  # Gleichstand zufällig auflösen
            if s > best_score:
                best_score = s
                best_dir = d
        return best_dir

    for d, n in options:
        if d == my_dir and random.random() < 0.8:
            return d
    return options[random.randrange(len(options))][0]


# ---------------------------------------------------------------- Runde / Match
def play_round(m, pad, hard, demo=False, spawn=None, p_hard=True, p_mistake=HARD_MISTAKE,
               a_mistake=HARD_MISTAKE):
    """
    Eine Runde. Gibt PLAYER_WIN, AI_WIN, DRAW oder ABORT (nur im Demo) zurück.
    Ohne spawn werden zufällige Startpunkte gewählt. p_hard, p_mistake und
    a_mistake gelten nur im Demo.
    """
    grid = bytearray(64)
    (p, pd), (a, ad) = spawn or random_spawn()
    grid[p] = 1
    grid[a] = 2
    queue = []  # vorgemerkte Richtungen (maximal 2) für schnelle Doppelwechsel
    base_ms = STEP_MS_HARD if hard else STEP_MS_EASY
    step_ms = base_ms
    moves = 0

    render(m, grid, p, a)
    last = ticks_ms()

    while True:
        # Auf den nächsten Schritt warten und dabei Eingaben sammeln
        while ticks_diff(ticks_ms(), last) < step_ms:
            d, c = pad.poll()
            if demo:
                if d >= 0 or c:
                    return ABORT
            elif d >= 0:
                ref = queue[-1] if queue else pd
                if d != ref and d != (ref + 2) % 4 and len(queue) < 2:
                    queue.append(d)
            sleep_ms(3)

        # Beide entscheiden gleichzeitig
        if demo:
            pd = ai_move(grid, p, pd, a, p_hard, p_mistake)
        elif queue:
            pd = queue.pop(0)
        ad = ai_move(grid, a, ad, p, hard, a_mistake)

        np_ = step(p, pd)
        na = step(a, ad)
        p_crash = np_ < 0 or grid[np_] != 0
        a_crash = na < 0 or grid[na] != 0
        if not p_crash and not a_crash and np_ == na:
            p_crash = a_crash = True  # Frontalzusammenstoß

        if p_crash or a_crash:
            crash_anim(m, grid, p_crash, a_crash)
            if p_crash and a_crash:
                return DRAW
            return AI_WIN if p_crash else PLAYER_WIN

        p, a = np_, na
        grid[p] = 1
        grid[a] = 2
        render(m, grid, p, a)
        moves += 1
        step_ms = max(MIN_STEP_MS, base_ms - moves * SPEED_UP_MS)
        last = ticks_ms()


def play_match(m, pad):
    hard = is_hard()
    player_score = 0
    ai_score = 0
    show_score(m, 0, 0)
    sleep_ms(900)
    while player_score < WINS_NEEDED and ai_score < WINS_NEEDED:
        countdown(m)
        result = play_round(m, pad, hard)
        if result == PLAYER_WIN:
            player_score += 1
        elif result == AI_WIN:
            ai_score += 1
        show_score(m, player_score, ai_score)
        sleep_ms(1200)

    if player_score > ai_score:
        scroll(m, "YOU WIN", ColorTable.LIME)
    else:
        scroll(m, "GAME OVER", ColorTable.RED)


# ---------------------------------------------------------------- Titelbild
def _build_ring():
    ring = []
    for x in range(8):
        ring.append((x, 7))
    for y in range(6, -1, -1):
        ring.append((7, y))
    for x in range(6, -1, -1):
        ring.append((x, 0))
    for y in range(1, 7):
        ring.append((0, y))
    return tuple(ring)


RING = _build_ring()  # 28 Randfelder im Uhrzeigersinn
TAIL = 6


def title(m, pad):
    """
    Zwei Lichtmotorräder jagen sich um den Rand. Die Mitte zeigt die Schwierigkeit.
    Gibt True zurück, wenn die Mitte gedrückt wurde, und False nach Leerlauf (Demo).
    """
    t = 0
    idle_since = ticks_ms()
    while True:
        d, c = pad.poll()
        if c:
            return True
        if d >= 0:
            idle_since = ticks_ms()
        if ticks_diff(ticks_ms(), idle_since) > IDLE_TO_DEMO_MS:
            return False

        m.clear()
        for k in range(TAIL):
            f = (TAIL - k) / TAIL
            m[RING[(t - k) % 28]] = scale(P_HEAD, f)
            m[RING[(t + 14 - k) % 28]] = scale(A_HEAD, f)

        phase = abs((ticks_ms() // 6) % 200 - 100) / 100  # 0..1 pulsierend
        base = (255, 0, 0) if is_hard() else (0, 255, 0)
        color = scale(base, 0.3 + 0.7 * phase)
        for pos in ((3, 3), (4, 3), (3, 4), (4, 4)):
            m[pos] = color
        m.apply()

        t = (t + 1) % 28
        sleep_ms(70)


def demo(m, pad):
    """
    KI gegen KI, jeder Tastendruck bricht ab.
    Zufällige Startpunkte und unterschiedlich fehleranfällige Fahrer, damit es
    nicht gespiegelt aussieht und meist einer klar gewinnt.
    """
    spawn = random_spawn()
    p_mistake = 0.05 + random.random() * 0.2
    a_mistake = 0.05 + random.random() * 0.2
    play_round(
        m, pad, random.random() < 0.8, demo=True, spawn=spawn,
        p_hard=random.random() < 0.8, p_mistake=p_mistake, a_mistake=a_mistake,
    )
    sleep_ms(500)


def main():
    m = LedMatrix(8, 8)
    m.set_brightness(BRIGHTNESS)
    pad = Pad()
    while True:
        if title(m, pad):
            play_match(m, pad)
        else:
            demo(m, pad)


if __name__ == "__main__":
    main()