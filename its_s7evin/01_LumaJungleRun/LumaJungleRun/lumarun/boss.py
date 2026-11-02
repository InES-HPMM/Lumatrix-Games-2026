# Level 2: Endboss in der Hoehle. Die Schlange sitzt auf einem Ast und spuckt Gift.
# Von der Felsdecke fallen Steine; aufsammeln und mit Joystick-Mitte nach oben werfen,
# jeder Treffer bricht ein Aststueck ab. Ist der ganze Ast weg, faellt die Schlange herunter.
import random
from . import hw, gfx, fx

HEAD_Y = 6
BRANCH_Y = 2
SNAKE_LEN = 4

S = None   # aktueller Spielzustand (wird auch vom Simulator gelesen)


class State:
    pass


def _settings(hard):
    st = State()
    st.hard = hard
    st.poison_min = 1300 if hard else 2000   # Abstand zwischen Giftschuessen (ms)
    st.poison_max = 2000 if hard else 3200
    st.poison_step = 150 if hard else 220    # ms pro Zeile, die das Gift faellt
    st.stone_every = 2600 if hard else 2000  # neuer Stein alle ... ms
    st.stone_step = 240
    st.snake_every = 600 if hard else 900    # Schlange bewegt sich alle ... ms
    return st


def _reset(st):
    st.branch = [1] * 8                    # 1 = Aststueck da, 0 = abgebrochen
    st.snake_x = 2                         # linkes Ende der Schlange
    st.snake_y = 1
    st.snake_dir = 1
    st.px = 3
    st.lives = 3
    st.invuln = 0
    st.flash = 0
    st.hud = 1500
    st.carry = False
    st.warn = None     # [x, restzeit]: Stein loest sich gleich von der Decke
    st.falling = []    # [x, y, t] fallende Steine
    st.floor = []      # [x, restzeit] Steine am Boden
    st.poison = []     # [x, y, t]
    st.debris = []     # [x, y, t] abgebrochene Aststuecke
    st.thrown = None   # [x, y, t] geworfener Stein
    st.spit = 0
    st.t_snake = 0
    st.t_poison = 1500
    st.t_stone = 800
    st.won = False


def _fall(items, step, dt, dy=1):
    """Bewegt [x, y, t]-Objekte alle step ms um dy Zeilen."""
    for it in items:
        it[2] += dt
        if it[2] >= step:
            it[2] = 0
            it[1] += dy


def _update(st, dt):
    # Schlange wandert auf dem Ast
    st.t_snake += dt
    if st.t_snake >= st.snake_every:
        st.t_snake = 0
        mid = st.snake_x + 1
        if st.hard and random.random() < 0.7:
            d = 1 if st.px > mid else (-1 if st.px < mid else 0)
        else:
            d = random.choice((-1, 0, 0, 1))
        if d:
            st.snake_dir = d
        st.snake_x = max(0, min(8 - SNAKE_LEN, st.snake_x + d))

    # Gift spucken
    st.t_poison -= dt
    st.spit -= dt
    if st.t_poison <= 0:
        st.t_poison = random.randint(st.poison_min, st.poison_max)
        head = st.snake_x + (SNAKE_LEN - 1 if st.snake_dir > 0 else 0)
        st.poison.append([head, BRANCH_Y, 0])
        st.spit = 200
    _fall(st.poison, st.poison_step, dt)
    st.poison = [p for p in st.poison if p[1] < 8]

    # Steine von der Decke
    if st.warn:
        st.warn[1] -= dt
        if st.warn[1] <= 0:
            st.falling.append([st.warn[0], 1, 0])
            st.warn = None
    st.t_stone -= dt
    if st.t_stone <= 0 and st.warn is None:
        st.t_stone = st.stone_every
        st.warn = [random.randint(0, 7), 700]
    _fall(st.falling, st.stone_step, dt)
    for s in st.falling[:]:
        if s[1] >= 7:
            st.falling.remove(s)
            st.floor.append([s[0], 5000])
    for f in st.floor[:]:
        f[1] -= dt
        if f[1] <= 0:
            st.floor.remove(f)

    _fall(st.debris, 110, dt)
    st.debris = [d for d in st.debris if d[1] < 8]

    # geworfener Stein fliegt nach oben
    if st.thrown:
        th = st.thrown
        _fall([th], 50, dt, -1)
        x = th[0]
        if th[1] == BRANCH_Y and st.branch[x]:
            st.branch[x] = 0
            st.debris.append([x, BRANCH_Y, 0])
            st.thrown = None
            if sum(st.branch) == 0:
                st.won = True
        elif th[1] < 0:
            st.thrown = None


def _hit(st):
    if st.invuln > 0:
        return
    st.lives -= 1
    st.invuln = 1500
    st.flash = 150
    st.hud = 1000


def _collide(st):
    px = st.px
    for p in st.poison[:]:
        if p[0] == px and p[1] in (HEAD_Y, HEAD_Y + 1):
            st.poison.remove(p)
            _hit(st)
    if not st.carry:
        for s in st.falling:
            if s[0] == px and s[1] in (HEAD_Y, HEAD_Y + 1):
                st.falling.remove(s)
                st.carry = True
                break
    if not st.carry:
        for f in st.floor:
            if f[0] == px:
                st.floor.remove(f)
                st.carry = True
                break


def _draw(st, t, player=True):
    hw.clear(gfx.WHITE)
    for x in range(8):
        hw.set(x, 0, gfx.CAVE)
    if st.warn and (t // 100) % 2:
        hw.set(st.warn[0], 0, gfx.ROCK)
    for x in range(8):
        if st.branch[x]:
            hw.set(x, BRANCH_Y, gfx.TRUNK)
    for i in range(SNAKE_LEN):
        hw.set(st.snake_x + i, st.snake_y, gfx.SNAKE)
    if st.spit > 0:
        head = st.snake_x + (SNAKE_LEN - 1 if st.snake_dir > 0 else 0)
        hw.set(head, st.snake_y, gfx.POISON)
    for d in st.debris:
        hw.set(d[0], d[1], gfx.TRUNK)
    for f in st.floor:
        if f[1] > 1500 or (t // 120) % 2:
            hw.set(f[0], 7, gfx.ROCK)
    for s in st.falling:
        hw.set(s[0], s[1], gfx.ROCK)
    for p in st.poison:
        hw.set(p[0], p[1], gfx.POISON)
    if st.thrown:
        hw.set(st.thrown[0], st.thrown[1], gfx.ROCK)
    if player and (st.invuln <= 0 or (t // 100) % 2):
        gfx.person(st.px, HEAD_Y)
        if st.carry:
            hw.set(st.px, HEAD_Y - 1, gfx.ROCK)
    if st.flash > 0:
        fx.tint(gfx.SHIRT, 60)
    if st.hud > 0:
        fx.lives(st.lives)


def _input(st):
    for ev in hw.poll():
        if ev == "left" and st.px > 0:
            st.px -= 1
        elif ev == "right" and st.px < 7:
            st.px += 1
        elif ev == "center" and st.carry and st.thrown is None:
            st.carry = False
            st.thrown = [st.px, HEAD_Y - 1, 0]


def _run(st):
    _reset(st)
    t = 0
    _draw(st, t)
    hw.fade(1500)          # die Person wacht in der Hoehle auf
    while True:
        dt = hw.tick()
        t += dt
        _input(st)
        _update(st, dt)
        _collide(st)
        st.invuln -= dt
        st.flash -= dt
        st.hud -= dt
        _draw(st, t)
        hw.show()
        if st.won:
            return True
        if st.lives <= 0:
            hw.pause(400)
            return False


def _victory(st):
    """Ast ist zerstoert: die Schlange faellt zu Boden. Gibt das Schlussbild zurueck."""
    st.poison, st.falling, st.floor, st.debris = [], [], [], []
    st.thrown = st.warn = None
    st.invuln = st.flash = st.hud = st.spit = 0
    st.carry = False
    _draw(st, 0)
    hw.pause(500)
    # Person geht zur naechsten Spalte, in die die Schlange nicht faellt
    free = [x for x in range(8) if not st.snake_x <= x < st.snake_x + SNAKE_LEN]
    target = min(free, key=lambda x: abs(x - st.px))
    while st.px != target:
        st.px += 1 if st.px < target else -1
        _draw(st, 0)
        hw.pause(130)
    while st.snake_y < 7:
        st.snake_y += 1
        _draw(st, 0)
        hw.pause(110)
    _draw(st, 0)
    hw.pause(700)
    return hw.snapshot()


def play():
    global S
    while True:
        st = _settings(hw.hard())   # DIP-Schalter gilt ab jedem (Neu-)Start des Levels
        S = st
        if _run(st):
            break
        fx.game_over()
    return _victory(st)
