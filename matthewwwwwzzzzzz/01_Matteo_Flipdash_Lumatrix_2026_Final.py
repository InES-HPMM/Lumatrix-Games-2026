# FLIPDASH  -  lumatrix games 2026
# basically geometry dash but the slide switch flips gravity
#
# joystick up/down/middle = jump (you can hold it)
# slide switch = flip gravity (only when you're standing on something)
# hold right = faster
#
# menu: left/right = level, press = start
# crashed: press = try again, left = back to menu

from machine import Pin
from neopixel import NeoPixel
from time import sleep_ms
import random

BRIGHTNESS = 10      # % (more is way too bright)
TEXT_SPEED = 90      # ms
SLIDER_FLOOR = 1     # if gravity is the wrong way round put 0 here
CUBE_X = 1           # cube column on screen
INTRO_TEXT = "LUMATRIX GAMES 2026  FLIPDASH"

# level = (ms per step, colour, map)
# 6 rows, first one is right under the ceiling, last one is on the floor
#   .  air
#   #  block, you can stand on it
#   x  spike
# all rows must be the same length!!
LEVELS = (
    # 1 - jump
    (150, (0, 200, 80), (
        "..........xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx......",
        "..................................................................................................................................................",
        "..................................................................................................................................................",
        "..................................................................................................................................................",
        "...............................................####............................................................####...................####........",
        "............x......x......####.....xx......########......####xx####......x....x......####xx####xx####......############.....x...x.....####........",
    )),
    # 2 - flip
    (140, (0, 120, 255), (
        "..........xxxxxxxxxxxxxxxxxxxxxx..............x.....####....xx..............................xxxxxxxxxxxxxxxxxxxxxxxxxxx.............x.....####........",
        "......................................................................................................................................................",
        "......................................................................................................................................................",
        "......................................................................................................................................................",
        "......................................................................................................................................................",
        "..............x.....####...xx...........xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.............x.....xx....####.............xxxxxxxxxxxxxxxxxxxxxxx.........",
    )),
    # 3 - fast mix
    (125, (200, 0, 255), (
        "..........xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx....########....x....x...x.......xxxxxxxxxxxxxxxxxxxxxxxxxxxx....x....####xx####.......xxxxxxxxxxxxxxxxxxxxxxxxxxx....####xx####....x.........",
        "..................................................####..................................................................................................................................",
        "........................................................................................................................................................................................",
        "........................................................................................................................................................................................",
        "...............................................................................####........................................................####.........................................",
        "...........x....xx....####xx####xx####.......xxxxxxxxxxxxxxxxxxxxxxxxxxx.......####......####xx####.......xxxxxxxxxxxxxxxxxxxx....x....############....xx......xxxxxxxxxxxxxxxxxxx......",
    )),
    # 4 - stairs
    (130, (255, 140, 0), (
        "........................................########.....####xx####.....................................x....########.......xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx......",
        "............................................####.........................................................####...............................................",
        "............................................................................................................................................................",
        "....................####................................................####................................................................................",
        "................########................................................########..............................................####....####..................",
        "............############.....x........xxxxxxxxxxxxxxxxxxxxxxxxxxxxx.....############.....xx.......xxxxxxxxxxxxxxxxxxx.....########....########....x.........",
    )),
    # 5 - ping pong
    (125, (0, 220, 220), (
        "..........xxxxxx.....x......xxxxxxxxx.....xx......xxxxxxxxxx.....####......xxxxxxx.....x...x......xxxxxxxxx.....####xx####.........",
        "...................................................................................................................................",
        "...................................................................................................................................",
        "...................................................................................................................................",
        "....................................................................................................####...........................",
        "............x......xxxxxx.....####......xxxxxxx.....x...x......xxxxxxxxx.....xx......xxxxxxxxxx.....####......xxxxxxxxxxxxxxx......",
    )),
    # 6 - tunnel
    (125, (255, 220, 0), (
        "............################....######....#######.........x....####.........############...........#####.........####xx####.......xxxxxxxxxxxxx......",
        "............################....######....#######...........................############...........#####.............................................",
        "................................######...............................................................................................................",
        ".....................................................................................................................................................",
        ".....................................................................................................................................................",
        "................x......x.....................x..........xxxxxxxxxxxxxxx........x....x......####......x.........xxxxxxxxxxxxxxxx.....x....xx..........",
    )),
    # 7 - spike pits
    (120, (255, 0, 120), (
        "..........xxxxxxxxxxxxxxxxxxxxxxxx.....###xx###xx###...................................###xx###xx###.......xxxxxxxxxxxxxxxxxxxxxxxx......",
        ".........................................................................................................................................",
        ".........................................................................................................................................",
        ".........................................................................................................................................",
        ".............................................................###..###..###...............................................................",
        "............###xx###xx###xx###.......xxxxxxxxxxxxxxxxxxx.....###xx###xx###....x......xxxxxxxxxxxxxxxxxxx.....###xx###xx###xx###..........",
    )),
    # 8
    (115, (120, 255, 0), (
        "..........xxxxxxxxxxxxxxxxxxxxxx....###xx###...x........#######...........................xx...####......xxxxxxxxxxxxxxxxx....x...x......xxxxxxxxxxxxx......",
        "........................................................#######................................####.........................................................",
        "............................................................................................................................................................",
        "..........................................................................####..............................................................................",
        "........................####..........................................########............................................................####..............",
        "...........x...xx...########.......xxxxxxxxxxxxxxxx........x......############....x......xxxxxxxxxxxxx....###xx###xx###......xxxxxxxxx....####...xx.........",
    )),
    # 9
    (110, (255, 255, 255), (
        "..........xxxxxxxxxxxxxx....###xx###xx###.................................xx...x........###########.......####...###xx###......xxxxxxxxxxxxxxxxxxxxxxxxxxxxx....x...xx..................................",
        "........................................................................................###########.....................................................................................................",
        "........................................................................................................................................................................................................",
        ".......................................................................................................................................................................................####.............",
        "....................................................####...###..###................................................................................................................########.............",
        "...........x...x...xx......xxxxxxxxxxxxxxxxx....########...###xx###......xxxxxxxxxx........x...x.........xxxxxxxxxxxxxxxxxxx......xx.....####xx####xx####......xxxxxxxxxx......############...x.........",
    )),
)

# one row too short and the level breaks, so check them at the start
for i, lvl in enumerate(LEVELS):
    if len(set(len(r) for r in lvl[2])) > 1:
        print("level", i + 1, "- rows are not the same length!")

DOWN = -1
UP = 1
BOTTOM = 1   # y=0 is the floor, y=7 the ceiling -> playing field is 1 to 6
TOP = 6

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (40, 40, 40)
BLUE = (0, 0, 150)
RED = (255, 0, 0)
SPARKS = (WHITE, (255, 230, 0), (255, 140, 0), (255, 50, 0), (120, 0, 0))

# start screen cube, # = rainbow  o = white
CUBE = ("#####",
        "#o.o#",
        "#...#",
        "#ooo#",
        "#####")

# 3x5 font (5 rows of 3, from the top)
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011",
    "D": "110101101101110", "E": "111100110100111", "F": "111100110100100",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111",
    "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010",
    "P": "110101110100100", "Q": "010101101110011", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111",
    "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111",
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111",
    "3": "111001111001111", "4": "101101111001001", "5": "111100111001111",
    "6": "111100111101111", "7": "111001010010010", "8": "111101111101111",
    "9": "111101111001111",
    " ": "000000000000000", "-": "000000111000000", "!": "010010010000010",
}

np = NeoPixel(Pin(19, Pin.OUT), 64)
switch = Pin(9, Pin.IN, Pin.PULL_UP)
buttons = [
    ("left", Pin(7, Pin.IN, Pin.PULL_UP)),
    ("right", Pin(2, Pin.IN, Pin.PULL_UP)),
    ("jump", Pin(3, Pin.IN, Pin.PULL_UP)),   # up
    ("jump", Pin(6, Pin.IN, Pin.PULL_UP)),   # down
    ("jump", Pin(8, Pin.IN, Pin.PULL_UP)),   # middle
]


def led(x, y, c):
    # 0,0 = bottom left, stuff outside the screen is just ignored
    if 0 <= x < 8 and 0 <= y < 8:
        np[y * 8 + x] = (c[0] * BRIGHTNESS // 100,
                         c[1] * BRIGHTNESS // 100,
                         c[2] * BRIGHTNESS // 100)


def clear():
    np.fill(BLACK)


def show():
    np.write()


def rainbow(i):
    # red -> green -> blue -> red in 48 steps
    i %= 48
    if i < 16:
        return (255 - i * 16, i * 16, 0)
    if i < 32:
        return (0, 511 - i * 16, i * 16 - 256)
    return (i * 16 - 512, 0, 767 - i * 16)


def letter(ch, x, c):
    bits = FONT.get(ch, FONT[" "])
    for i in range(15):
        if bits[i] == "1":
            led(x + i % 3, 6 - i // 3, c)


def number(n, c):
    # only up to 99
    s = str(n)
    x = 4 - 2 * len(s)
    for d in s:
        letter(d, x, c)
        x += 4


def scroll(text):
    # any button skips
    text = text.upper()
    for shift in range(-8, len(text) * 4):
        clear()
        for i in range(len(text)):
            x = i * 4 - shift
            if -4 < x < 8:
                letter(text[i], x, rainbow(i * 4))
        show()
        sleep_ms(TEXT_SPEED)
        if pressed():
            return True
    return False


def pressed():
    for name, pin in buttons:
        if pin.value() == 0:
            return name
    return ""


def wait_release():
    while pressed():
        sleep_ms(20)


def wait_button():
    wait_release()
    while not pressed():
        sleep_ms(20)
    return pressed()


def wait_step(ms):
    # check every 10ms, otherwise short taps get lost
    # holding right = time runs out faster (dash)
    jump = False
    while ms > 0:
        b = pressed()
        if b == "jump":
            jump = True
        sleep_ms(10)
        if b == "right":
            ms -= 15
        else:
            ms -= 10
    return jump


def switch_gravity():
    if switch.value() == SLIDER_FLOOR:
        return DOWN
    return UP


def tile(rows, col, y):
    if y < BOTTOM or y > TOP:
        return "#"   # floor and ceiling count as blocks
    if col >= len(rows[0]):
        return "."   # level is over, just air
    return rows[TOP - y][col]


def move_cube(rows, col, y, speed, gravity, jump):
    # returns y, speed, gravity, crashed

    # on the ground -> jump and/or check the switch
    if tile(rows, col, y + gravity) == "#":
        if jump:
            speed = -2 * gravity   # away from what you're standing on
        else:
            speed = 0
        gravity = switch_gravity()   # after the jump, so jump + flip = boost to the other side

    # falling, gets faster (max 3)
    if tile(rows, col, y + gravity) != "#":
        speed = max(-3, min(3, speed + gravity))

    # move 1 cell at a time, if not you glitch through blocks when you're fast
    step = 1 if speed > 0 else -1
    for _ in range(abs(speed)):
        hit = tile(rows, col, y + step)
        if hit == "#":
            return y, 0, gravity, False
        y += step
        if hit == "x":
            return y, speed, gravity, True
    return y, speed, gravity, False


def draw_world(rows, color, x, gravity):
    clear()
    for col in range(8):
        # blue line = the side you fall to
        if gravity == DOWN:
            led(col, 0, BLUE)
            led(col, 7, GREY)
        else:
            led(col, 0, GREY)
            led(col, 7, BLUE)
        for y in range(BOTTOM, TOP + 1):
            t = tile(rows, x + col, y)
            if t == "#":
                led(col, y, color)
            if t == "x":
                led(col, y, RED)


def loading_bar():
    clear()
    for x in range(8):
        led(x, 3, rainbow(x * 5))
        led(x, 4, rainbow(x * 5))
        show()
        sleep_ms(120)


def start_screen():
    # cube jumping, stars flying past, runs until you press something
    stars = [[1, 6], [4, 7], [6, 1], [3, 0]]
    hops = (0, 0, 1, 2, 2, 1)
    frame = 0
    wait_release()
    while not pressed():
        clear()
        for s in stars:
            led(s[0], s[1], GREY)

        h = 1 + hops[frame % len(hops)]
        for row in range(5):
            for col in range(5):
                p = CUBE[4 - row][col]
                if p == "#":
                    led(2 + col, h + row, rainbow(frame))
                if p == "o":
                    led(2 + col, h + row, WHITE)

        if frame % 10 < 5:   # blinking floor
            for x in range(8):
                led(x, 0, BLUE)

        show()
        sleep_ms(70)
        frame += 1

        for s in stars:
            s[0] -= 1
            if s[0] < 0:   # back to the right side
                s[0] = 7
                s[1] = random.choice((0, 1, 6, 7))


def intro():
    loading_bar()
    scroll(INTRO_TEXT)
    start_screen()


def menu(n):
    while True:
        color = LEVELS[n][1]
        clear()
        number(n + 1, color)
        led(0, 4, GREY)   # little arrows left/right
        led(7, 4, GREY)
        # bottom line shows your best %, white = done
        for x in range(best[n] * 8 // 100):
            if best[n] == 100:
                led(x, 0, WHITE)
            else:
                led(x, 0, BLUE)
        show()

        b = wait_button()
        if b == "jump":
            return n
        if b == "right":
            n = (n + 1) % len(LEVELS)
        if b == "left":
            n = (n - 1) % len(LEVELS)


def explode(rows, color, x, y, gravity):
    dirs = ((1, 0), (1, 1), (0, 1), (-1, 1),
            (-1, 0), (-1, -1), (0, -1), (1, -1))
    for d in range(len(SPARKS)):
        draw_world(rows, color, x, gravity)
        for dx, dy in dirs:
            led(CUBE_X + dx * d, y + dy * d, SPARKS[d])
        show()
        sleep_ms(80)
    sleep_ms(400)


def show_percent(p):
    clear()
    number(p, WHITE)
    show()


def level_complete(color):
    # rings from the middle
    for frame in range(16):
        clear()
        for y in range(8):
            for x in range(8):
                ring = max(abs(2 * x - 7), abs(2 * y - 7)) // 2   # 0 middle .. 3 edge
                if (ring - frame) % 4 == 0:
                    led(x, y, color)
        show()
        sleep_ms(70)

    for _ in range(3):   # flash
        for i in range(64):
            led(i % 8, i // 8, WHITE)
        show()
        sleep_ms(60)
        clear()
        show()
        sleep_ms(120)

    scroll("LEVEL COMPLETE!")


def play(n):
    # returns how far you got in %
    step_ms, color, rows = LEVELS[n]
    length = len(rows[0])
    gravity = switch_gravity()
    y = BOTTOM if gravity == DOWN else TOP
    x = 0
    speed = 0
    jump = False

    while x + CUBE_X < length:
        old_y = y
        y, speed, gravity, crashed = move_cube(rows, x + CUBE_X, y, speed, gravity, jump)
        if not crashed:
            x += 1
            if tile(rows, x + CUBE_X, y) != ".":   # hit something from the side
                crashed = True

        if crashed:
            explode(rows, color, x, y, gravity)
            return (x + CUBE_X) * 100 // length

        draw_world(rows, color, x, gravity)
        led(CUBE_X - 1, old_y, GREY)   # trail
        led(CUBE_X, y, WHITE)
        show()
        # print(x, y, speed, gravity)
        jump = wait_step(step_ms)

    return 100


best = [0] * len(LEVELS)

intro()
level = 0
while True:
    level = menu(level)
    while True:
        p = play(level)
        if p > best[level]:
            best[level] = p
        if p == 100:
            level_complete(LEVELS[level][1])
            break
        show_percent(p)
        if wait_button() == "left":
            break