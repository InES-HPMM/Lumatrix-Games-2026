# ************************************************************************
#  BOMBERMAN for the ZHAW Lumatrix
#  "Zwei Generationen, ein Spielfeld":
#  Der Arcade-Klassiker von 1983, wiedergeboren auf Maker-Hardware 2026.
#
#------Please remove before releasing thanks -----------------------------
#  Concept, game design, Basic's :   Marc Ackermann
#  Enemy AI & engine:                co-developed with Lumo (Proton AI)
#
# ************************************************************************

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms, ticks_ms, ticks_diff
from random import randint
from zhaw_led_matrix import Lumatrix
from OwnLibrary import LED_Color
import math

# ----------------------- Controlpanel -------------------------------
# Finetune the Game from here:

BOMB_FUSE_MS     = 2000   # how long until a bomb explodes
BLINK_MS         = 200    # blink speed of the ticking bomb
EXPLOSION_MS     = 500    # how long the flames stay visible
PLAYER_MOVE_MS   = 200    # player movement speed (lower = faster)
ENEMY_MOVE_MS    = 800    # enemy movement speed (lower = harder)
BOMB_RANGE       = 2      # flame length in cells
NR_ENEMIES       = 3      # enemies per round (max 3, they spawn far away)
SOFT_WALL_PCT    = 90     # % of free cells filled with breakable bricks

# Colors
# Options: WHITE, RED, BLUE, GREEN, YELLOW, BLACK, DARK_AMBER, PURPLE, PURPLE_LOW, ORANGE
COLOR_WALL_HARD  = LED_Color.WHITE                 # unbreakable walls / border
COLOR_WALL_SOFT  = LED_Color.DARK_AMBER            # breakable bricks (dark amber)
COLOR_PLAYER     = LED_Color.BLUE                  # the hero
COLOR_ENEMY      = LED_Color.RED                   # the Monsters
COLOR_BOMB       = LED_Color.PURPLE                # bombe
COLOR_BOMB_DIM   = LED_Color.PURPLE_LOW            # bombe (for blinking)
COLOR_FLAME      = LED_Color.ORANGE                # explosion
COLOR_BLACK      = LED_Color.BLACK                 # background

# ----------------------- Hardware -----------------------------------

pin_js_r = Pin(2, Pin.IN)   # Joystick right
pin_js_l = Pin(7, Pin.IN)   # Joystick left
pin_js_u = Pin(3, Pin.IN)   # Joystick up
pin_js_d = Pin(6, Pin.IN)   # Joystick down
pin_js_c = Pin(8, Pin.IN)   # Joystick center

matrix   = NeoPixel(Pin(19, Pin.OUT), 64)
lumatrix = Lumatrix()

# ----------------------- small helpers ------------------------------

def manhattan(a, b):
    """Walking distance between two LED indices. No diagonal movement"""
    return abs(a // 8 - b // 8) + abs(a % 8 - b % 8)

def neighbours(pos):
    """All neighbour cells (up/down/left/right), without wrapping."""
    result = []
    if pos % 8 != 0:       result.append(pos - 1)   # left
    if pos % 8 != 7:       result.append(pos + 1)   # right
    if pos + 8 < 64:       result.append(pos + 8)   # up
    if pos - 8 >= 0:       result.append(pos - 8)   # down
    return result

def is_free(pos, hard, soft, blocked_extra):
    """Can someone walk onto this cell?"""
    return (pos not in hard
            and pos not in soft
            and pos not in blocked_extra)

# ----------------------- level generator ----------------------------

def build_level():
    """Creates walls, bricks, player and enemy spawns."""
    hard = set()
    # Outer border (classic Bomberman arena frame)
    for pos in range(64):
        if pos < 8 or pos >= 56 or pos % 8 == 0 or pos % 8 == 7:
            hard.add(pos)
    # Classic pillars on even/even crossings
    for y in (2, 4):
        for x in (2, 4):
            hard.add(y * 8 + x)

    player = 9                                # spawn: top-left interior
    enemy_spawns = [54, 46, 53]               # far bottom-right corner
    enemies = enemy_spawns[:NR_ENEMIES]

    # Safe zone around the spawns: no bricks directly in the face
    safe = set()
    for pos in range(64):
        if manhattan(pos, player) <= 2:
            safe.add(pos)
        for e in enemies:
            if manhattan(pos, e) <= 1:
                safe.add(pos)

    # Randomly place breakable bricks on the free cells
    soft = set()
    for pos in range(64):
        if pos in hard or pos in safe or pos in enemies:
            continue
        if randint(1, 100) <= SOFT_WALL_PCT:
            soft.add(pos)

    return hard, soft, player, enemies

# ----------------------- bomb logic ---------------------------------

def explosion_cells(pos, hard, soft):
    """Cross-shaped explosion around the bomb, stopped by walls."""
    cells = [pos]
    for d in (-1, 1, -8, 8):                  # left, right, up, down
        p = pos
        for _ in range(BOMB_RANGE):
            n = p + d
            if n < 0 or n >= 64:
                break
            if d in (-1, 1) and abs((n % 8) - (p % 8)) != 1:
                break                          # row wrap protection
            if n in hard:
                break                          # flame stops at walls
            cells.append(n)
            if n in soft:
                break                          # brick burns, flame ends
            p = n
    return cells

# ----------------------- enemy brain ---------------------------------

def enemy_step(pos, player, hard, soft, blocked_extra):
    """Greedy chase with a bit of randomness, so they are beatable."""
    options = [n for n in neighbours(pos)
               if is_free(n, hard, soft, blocked_extra)]
    if not options:
        return pos
    if randint(1, 10) <= 7:                   # 70%: move towards player
        options.sort(key=lambda n: manhattan(n, player))
        return options[0]
    return options[randint(0, len(options) - 1)]   # 30%: random stumble

# ----------------------- drawing -------------------------------------

def draw_everything(player, enemies, bombs, flames, hard, soft, now):
    """Full redraw of the whole arena, one frame."""
    for pos in range(64):
        if pos in hard:
            matrix[pos] = COLOR_WALL_HARD
        elif pos in soft:
            matrix[pos] = COLOR_WALL_SOFT
        elif pos in flames:
            matrix[pos] = COLOR_FLAME
        else:
            matrix[pos] = COLOR_BLACK
    for b in bombs:
        phase = (ticks_diff(now, b["planted"]) // BLINK_MS) % 2
        matrix[b["pos"]] = COLOR_BOMB if phase == 0 else COLOR_BOMB_DIM
    for e in enemies:
        matrix[e] = COLOR_ENEMY
    matrix[player] = COLOR_PLAYER             # hero always on top
    matrix.write()

# ----------------------- end screens --------------------------------
# Ring wave endscreen

def ring_wave(color_line, color_bg, start=27):
    sy, sx = start // 8, start % 8
    rings = {}
    for pos in range(64):
        py, px = pos // 8, pos % 8
        dist = round(math.sqrt((py - sy) ** 2 + (px - sx) ** 2))
        rings.setdefault(dist, []).append(pos)
    for dist in sorted(rings.keys()):
        for pos in rings[dist]:
            matrix[pos] = color_line
        matrix.write()
        sleep_ms(120)
        for pos in rings[dist]:
            matrix[pos] = color_bg
    matrix.write()
    sleep_ms(1500)

def wait_for_restart():
    """Shows a blinking hint until the player presses the stick."""
    while pin_js_c.value() == 1:
        sleep_ms(20)
    sleep_ms(300)                              # debounce
    while pin_js_c.value() == 0:
        sleep_ms(20)

# ----------------------- the game loop -------------------------------

def game_round():
    hard, soft, player, enemies = build_level()

    bombs = []          # each bomb: {"pos": index, "planted": timestamp}
    flames = {}         # cell index -> timestamp when flame dies out

    game_over = False
    won = False
    last_move = ticks_ms()
    last_enemy_move = ticks_ms()
    c_held = False

    while not game_over:
        now = ticks_ms()

        # --- 1) Player movement (hold the stick to keep walking) ---
        if ticks_diff(now, last_move) >= PLAYER_MOVE_MS:
            target = None
            if pin_js_l.value() == 0 and player % 8 != 0:
                target = player - 1            # left
            elif pin_js_r.value() == 0 and player % 8 != 7:
                target = player + 1            # right
            elif pin_js_u.value() == 0 and player + 8 < 64:
                target = player + 8            # up
            elif pin_js_d.value() == 0 and player - 8 >= 0:
                target = player - 8            # down

            bomb_cells = {b["pos"] for b in bombs}
            if target is not None and is_free(target, hard, soft, bomb_cells):
                player = target
                last_move = now

        # --- 2) Place a bomb (center press, one bomb at a time) ---
        if pin_js_c.value() == 0:
            if not c_held and len(bombs) < 1:
                bombs.append({"pos": player, "planted": now})
            c_held = True
        else:
            c_held = False

        # --- 3) Bombs: check the fuse ---
        for b in bombs[:]:
            if ticks_diff(now, b["planted"]) >= BOMB_FUSE_MS:
                bombs.remove(b)
                cells = explosion_cells(b["pos"], hard, soft)
                for c in cells:
                    soft.discard(c)                       # bricks burn away
                    flames[c] = now + EXPLOSION_MS
                for e in enemies[:]:
                    if e in cells:
                        enemies.remove(e)                  # enemy dies
                if player in cells:
                    game_over = True                       # you blew up!

        # --- 4) Flames burn out ---
        for c in list(flames.keys()):
            if ticks_diff(now, flames[c]) >= 0:
                del flames[c]

        # --- 5) Enemies take their turn ---
        if ticks_diff(now, last_enemy_move) >= ENEMY_MOVE_MS:
            last_enemy_move = now
            bomb_cells = {b["pos"] for b in bombs}
            occupied = set(enemies)                        # don't stack
            for i in range(len(enemies)):
                enemies[i] = enemy_step(enemies[i], player,
                                        hard, soft, bomb_cells | occupied)
                occupied.discard(enemies[i])
                occupied.add(enemies[i])
            for e in enemies[:]:                           # walked into fire?
                if e in flames:
                    enemies.remove(e)
            if player in enemies:                          # caught!
                game_over = True

        # --- 6) Did we win? ---
        if not enemies:
            won = True
            game_over = True

        # --- 7) Show the current frame ---
        draw_everything(player, enemies, bombs, flames, hard, soft, now)
        sleep_ms(20)

    return won

# ----------------------- main program --------------------------------

lumatrix.writeText("BOMBERMAN! 1983 meets 2026. Ready?", LED_Color.TEXT_YELLOW)
lumatrix.writeText("Destroy all monsters - Don't blow yourself up!", LED_Color.TEXT_GREEN)

while True:
    won = game_round()

    if won:
        ring_wave(LED_Color.WINN_GREEN_FRAME, LED_Color.WINN_GREEN_BG)
        lumatrix.writeText("YOU WIN! Legend of two generations!", LED_Color.TEXT_GREEN)
    else:
        ring_wave(LED_Color.LOOSE_RED_LINE, LED_Color.LOOSE_RED_BG, start=36)
        lumatrix.writeText("GAME OVER... 1983 sends its regards!", LED_Color.TEXT_RED)

    wait_for_restart()
