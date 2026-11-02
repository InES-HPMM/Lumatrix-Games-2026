# Level 1: Lauf durch den Dschungel. Der Weg scrollt nach unten, die Person wechselt
# mit links/rechts zwischen den drei Spuren und weicht Felsen und Spinnen aus.
import random
from . import hw, gfx, fx

LANES = (2, 3, 4)
SIDES = (0, 1, 5, 6, 7)
HEAD_Y = 6

S = None   # aktueller Spielzustand (wird auch vom Simulator gelesen)


class State:
    pass


class Spider:
    def __init__(self, kind, x, dx=0):
        self.kind = kind   # "web" legt Netze, "walk" kommt entgegen
        self.x = x
        self.y = 0
        self.dx = dx
        self.webs = 0
        self.t = 0


def new_decor():
    return [[] for _ in range(8)]


def make_row(decor):
    """Neue Dschungelzeile: Weg in der Mitte, Wiese mit Baeumen am Rand.
    Neue Zeilen kommen oben dazu, darum zuerst der Stamm, danach die Krone."""
    row = [gfx.GRASS] * 8
    for x in SIDES:
        q = decor[x]
        if not q and random.random() < 0.09:
            q.extend([gfx.BUSH] * random.randint(1, 2) + [gfx.TRUNK] * random.randint(1, 2))
        if q:
            row[x] = q.pop()
    for x in LANES:
        row[x] = gfx.PATH
    return row


def _settings(hard):
    st = State()
    st.hard = hard
    st.total = 200 if hard else 170            # Laenge des Laufs in Zeilen
    st.step_start = 270 if hard else 340       # ms pro Zeile am Anfang
    st.step_end = 175 if hard else 240         # ms pro Zeile am Ende
    st.min_gap = 4 if hard else 5              # Mindestabstand zwischen Hindernissen
    st.chance = 0.6 if hard else 0.45
    st.shakes = 8 if hard else 5               # Ruetteln, um aus dem Netz zu kommen
    st.walk_ms = 450 if hard else 600          # Tempo der entgegenkommenden Spinnen
    return st


def _reset(st):
    st.decor = new_decor()
    st.rows = [make_row(st.decor) for _ in range(8)]
    st.obs = [[None] * 8 for _ in range(8)]    # "r" Felsen, "w" Netz
    st.spiders = []
    st.px = 3
    st.lives = 3
    st.invuln = 0
    st.flash = 0
    st.hud = 1500
    st.caught = 0
    st.last_shake = None
    st.progress = 0
    st.gap = -4
    st.scroll_t = 0
    st.cave_left = len(gfx.CAVE_ROWS)
    st.done = False


def _spawn(st):
    st.gap += 1
    if st.progress >= st.total or st.gap < st.min_gap or random.random() > st.chance:
        return
    r = random.random()
    late = st.progress > st.total // 4
    if r < 0.38:
        st.obs[0][random.choice(LANES)] = "r"
        st.gap = 0
    elif r < 0.52 and late:
        free = random.choice(LANES)
        for x in LANES:
            if x != free:
                st.obs[0][x] = "r"
        st.gap = -1
    elif r < 0.78:
        if random.random() < 0.5:
            st.spiders.append(Spider("web", 1, 1))
        else:
            st.spiders.append(Spider("web", 5, -1))
        st.gap = -1
    else:
        st.spiders.append(Spider("walk", random.choice(LANES)))
        st.gap = -2


def _scroll(st):
    st.progress += 1
    if st.progress >= st.total + 8 and st.cave_left > 0:
        st.cave_left -= 1
        row = gfx.img((gfx.CAVE_ROWS[st.cave_left],))
        if st.cave_left == 0:
            st.done = True
    else:
        row = make_row(st.decor)
    st.rows.insert(0, row)
    st.rows.pop()
    st.obs.insert(0, [None] * 8)
    st.obs.pop()
    for sp in st.spiders:
        sp.y += 1
    st.spiders = [sp for sp in st.spiders if sp.y < 8]
    _spawn(st)


def _update_spiders(st, dt):
    for sp in st.spiders[:]:
        sp.t += dt
        if sp.kind == "web" and sp.t >= 200:
            sp.t = 0
            if sp.x in LANES:
                st.obs[sp.y][sp.x] = "w"
                sp.webs += 1
            if sp.webs >= 2:
                st.spiders.remove(sp)    # klettert an ihrem Faden davon
            else:
                sp.x += sp.dx
        elif sp.kind == "walk" and sp.t >= st.walk_ms:
            sp.t = 0
            sp.y += 1
            if sp.y > 7:
                st.spiders.remove(sp)


def _hit(st):
    if st.invuln > 0:
        return
    st.lives -= 1
    st.invuln = 1500
    st.flash = 150
    st.hud = 1000


def _collide(st):
    px = st.px
    for y in (HEAD_Y, HEAD_Y + 1):
        o = st.obs[y][px]
        if o == "r":
            st.obs[y][px] = None
            _hit(st)
        elif o == "w":
            st.obs[y][px] = None
            if not st.caught:
                st.caught = st.shakes
                st.last_shake = None
    for sp in st.spiders[:]:
        if sp.x == px and sp.y in (HEAD_Y, HEAD_Y + 1):
            st.spiders.remove(sp)
            _hit(st)


def _draw(st, t, player=True):
    fb = hw.fb
    for y in range(8):
        row = st.rows[y]
        obs = st.obs[y]
        for x in range(8):
            o = obs[x]
            if o == "r":
                fb[y * 8 + x] = gfx.ROCK
            elif o == "w":
                fb[y * 8 + x] = gfx.WHITE
            else:
                fb[y * 8 + x] = row[x]
    for sp in st.spiders:
        hw.set(sp.x, sp.y, gfx.SPIDER if sp.kind == "web" else gfx.WALKER)
    if not player:
        pass
    elif st.caught:
        body = gfx.WHITE if (t // 150) % 2 else gfx.SHIRT
        hw.set(st.px - 1, HEAD_Y + 1, gfx.WHITE)
        hw.set(st.px + 1, HEAD_Y + 1, gfx.WHITE)
        gfx.person(st.px, HEAD_Y, body)
    elif st.invuln <= 0 or (t // 100) % 2:
        gfx.person(st.px, HEAD_Y)
    if st.flash > 0:
        fx.tint(gfx.SHIRT, 60)
    if st.hud > 0:
        fx.lives(st.lives)


def _input(st):
    for ev in hw.poll():
        if st.caught:
            if ev in ("left", "right") and ev != st.last_shake:
                st.last_shake = ev
                st.caught -= 1
        elif ev == "left" and st.px > LANES[0]:
            st.px -= 1
        elif ev == "right" and st.px < LANES[-1]:
            st.px += 1


def _run(st):
    _reset(st)
    t = 0
    _draw(st, t)
    hw.fade(600)
    while not st.done:
        dt = hw.tick()
        t += dt
        _input(st)
        if not st.caught:
            st.scroll_t += dt
            p = min(st.progress, st.total)
            step = st.step_start - (st.step_start - st.step_end) * p // st.total
            if st.scroll_t >= step:
                st.scroll_t = 0
                _scroll(st)
        _update_spiders(st, dt)
        _collide(st)
        st.invuln -= dt
        st.flash -= dt
        st.hud -= dt
        _draw(st, t)
        hw.show()
        if st.lives <= 0:
            hw.pause(400)
            return False
    return True


def _snake_cutscene(st):
    """Die Schlange kriecht aus der Hoehle und versperrt den Weg. Kein Ausweichen moeglich."""
    st.spiders = []
    st.obs = [[None] * 8 for _ in range(8)]
    st.invuln = st.flash = st.hud = st.caught = 0
    snake = []
    state = {"head": HEAD_Y, "tongue": False}

    def frame(ms):
        _draw(st, 0, player=False)
        for x, y in snake:
            hw.set(x, y, gfx.SNAKE)
        if state["tongue"]:
            hw.set(4, 4, gfx.SHIRT)
        gfx.person(st.px, state["head"])
        hw.pause(ms)

    frame(500)
    while st.px != 3:
        st.px += 1 if st.px < 3 else -1
        frame(200)
    for p in gfx.SNAKE_PATH:
        snake.append(p)
        frame(180)
    for i in range(4):
        state["tongue"] = not state["tongue"]
        frame(250)
    # die Person laeuft weiter und beruehrt die Schlange
    for head in (5, 4, 3):
        state["head"] = head
        frame(350)
    fx.tint(gfx.POISON, 70)
    hw.pause(250)


def play():
    global S
    while True:
        st = _settings(hw.hard())   # DIP-Schalter gilt ab jedem (Neu-)Start des Levels
        S = st
        if _run(st):
            break
        fx.game_over()
    _snake_cutscene(st)
