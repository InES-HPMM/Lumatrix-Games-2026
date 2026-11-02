from core import *
import gc
gc.collect()

def launch_donkey_kong():
    try:
        from machine import Pin
        from neopixel import NeoPixel
        import random
        from time import sleep_ms, ticks_ms, ticks_diff

        np = NeoPixel(Pin(19, Pin.OUT), 64)
        LEFT, RIGHT, UP, DOWN, S1 = [
            Pin(p, Pin.IN, Pin.PULL_UP) for p in (7, 2, 3, 6, 8)
        ]

        OFF = (0, 0, 0)
        RED = (180, 0, 0)
        GREEN = (0, 180, 0)
        BLUE = (0, 0, 180)
        YELLOW = (180, 120, 0)
        CYAN = (0, 150, 150)
        ORANGE = (180, 45, 0)

        def draw(points):
            np.fill(OFF)
            for px, py, color in points:
                if 0 <= px < 8 and 0 <= py < 8:
                    np[px + py * 8] = color
            np.write()

        def inp():
            if UP.value() == 0: return 'up'
            if DOWN.value() == 0: return 'down'
            if LEFT.value() == 0: return 'left'
            if RIGHT.value() == 0: return 'right'
            if S1.value() == 0: return 's1'
            return None

        def wait_release():
            while any(p.value() == 0 for p in (LEFT, RIGHT, UP, DOWN, S1)):
                sleep_ms(15)

        def clamp(v, a, b):
            return max(a, min(b, v))

        def show_lives(points, lives):
            # Tre vite in basso a sinistra
            for i in range(3):
                points.append((i, 7, RED if i < lives else OFF))

        def hit_effect():
            for _ in range(2):
                draw([(px, py, RED) for py in range(8) for px in range(8)])
                sleep_ms(100)
                np.fill(OFF)
                np.write()
                sleep_ms(100)

        platform_rows = [0, 2, 4, 6, 7]
        ladders = [(1, 0, 2), (5, 2, 4), (2, 4, 6), (6, 6, 7)]

        def on_ladder(px, py):
            return any(px == lx and low <= py <= high
                       for lx, low, high in ladders)

        x, y = 0, 0
        lives = 3

        for level in range(1, 11):
            if lives <= 0:
                break

            show_level_intro(level)
            x, y = 0, 0
            barrels = []

            for i in range(level):
                # I barili partono in alto.
                barrels.append([
                    random.randrange(8), 7,
                    random.choice([-1, 1]),
                    ticks_ms() + random.randrange(400, 1300)
                ])

            last_move = 0
            last_step = ticks_ms()
            speed = max(120, 410 - level * 22)

            while y < 7 and lives > 0:
                t = ticks_ms()
                a = inp()

                # Movimento del giocatore.
                if a and ticks_diff(t, last_move) > 120:
                    if a == 'left' and x > 0 and y in platform_rows:
                        x -= 1
                        last_move = t
                    elif a == 'right' and x < 7 and y in platform_rows:
                        x += 1
                        last_move = t
                    elif a == 'up' and on_ladder(x, y):
                        high = next((h for lx, lo, h in ladders
                                     if lx == x and lo <= y < h), -1)
                        if high >= 0:
                            y += 1
                            last_move = t
                    elif a == 'down' and on_ladder(x, y):
                        low = next((lo for lx, lo, h in ladders
                                    if lx == x and lo < y <= h), 99)
                        if low < 99:
                            y -= 1
                            last_move = t

                # Movimento dei barili.
                if ticks_diff(t, last_step) >= speed:
                    last_step = t
                    for b in barrels:
                        bx, by, d, next_drop = b
                        bx += d

                        if bx < 0 or bx > 7:
                            bx = clamp(bx, 0, 7)
                            d *= -1

                        ladder = next(
                            (l for l in ladders if l[0] == bx and l[2] == by),
                            None
                        )

                        if ladder and ticks_diff(t, next_drop) >= 0:
                            by = ladder[1]
                            d = random.choice([-1, 1])
                            next_drop = t + random.randrange(500, 1000)

                        # Quando il barile raggiunge la prima riga,
                        # ricompare nell'ultima riga.
                        if by == 0:
                            by = 7
                            bx = random.randrange(8)

                        b[0], b[1], b[2], b[3] = bx, by, d, next_drop

                # Collisione: si perde una vita.
                if any(b[0] == x and b[1] == y for b in barrels):
                    lives -= 1
                    hit_effect()

                    if lives <= 0:
                        break

                    x, y = 0, 0
                    wait_release()
                    last_move = ticks_ms()

                # Disegna piattaforme e scale.
                pts = [(i, row, BLUE)
                       for row in platform_rows for i in range(8)]
                pts += [(lx, yy, GREEN)
                        for lx, low, high in ladders
                        for yy in range(low, high + 1)]

                # Traguardo e barili.
                pts.append((7, 7, YELLOW))
                pts += [(bx, by, ORANGE) for bx, by, _, _ in barrels]

                # Giocatore.
                pts.append((x, y, CYAN))

                # Vite in basso a destra, disegnate per ultime.
                show_lives(pts, lives)

                draw(pts)
                sleep_ms(20)

        if lives <= 0:
            arcade_result_screen(False)
        else:
            arcade_result_screen(True)

        np.fill(OFF)
        np.write()

    except SystemExit:
        pass

    arcade_clear()
    return
