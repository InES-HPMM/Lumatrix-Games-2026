# ============================================================================
# PROJEKT: LUMATRIX WARIOWARE OS (4-in-1 Retro Arcade & "Windows Crash" Bug)
# AUTOR:   Leo Pavlovic
# ============================================================================
# HINWEIS:
# - Stirbt man in einem Spiel, wechselt die Lumatrix nach einem kurzen
#   Countdown sofort in ein anderes Zufallsspiel.
# - Legt man den hinteren Schalter um, aktiviert sich ein "Overclock-Bug" (God-Mode).
# - EASTER EGG included
# ============================================================================

import gc
import random
from utime import sleep_ms
from zhaw_led_matrix import LedMatrix, Button, ColorTable

# Hardware-Initialisierung
lm = LedMatrix(8, 8)
lm.set_brightness(12)
btn = Button()

RAINBOW = [
    ColorTable.RED,
    ColorTable.ORANGE,
    ColorTable.YELLOW,
    ColorTable.LIME,
    ColorTable.AQUA,
    ColorTable.PINK
]

DIGITS = [
    ([(2,6),(3,6),(4,6),(5,6),(5,5),(3,4),(4,4),(5,4),(5,3),(2,2),(3,2),(4,2),(5,2)], ColorTable.RED),
    ([(2,6),(3,6),(4,6),(5,6),(5,5),(2,4),(3,4),(4,4),(5,4),(2,3),(2,2),(3,2),(4,2),(5,2)], ColorTable.YELLOW),
    ([(3,6),(4,6),(4,5),(4,4),(4,3),(2,2),(3,2),(4,2),(5,2)], ColorTable.LIME)
]


# ============================================================================
# SYSTEM-FUNKTIONEN (Bootloader, Countdown & Bug-Abfrage)
# ============================================================================

def boot_loading_bar():
    """Zeigt beim Starten (und nach dem Windows-Reboot) den 1.5s Ladebalken."""
    lm.clear()
    for x in range(8):
        lm.draw_list([(x, 2), (x, 5)], (15, 20, 35))
    lm.apply()

    for step in range(8):
        if step < 3:
            bar_color = ColorTable.RED
        elif step < 6:
            bar_color = ColorTable.YELLOW
        else:
            bar_color = ColorTable.LIME

        lm.draw_list([(step, 3), (step, 4)], bar_color)
        lm.apply()
        sleep_ms(180)

    sleep_ms(100)
    lm.clear()
    lm.apply()


def play_countdown():
    """Schneller 3-2-1 Countdown (1.35s) vor jedem Spielwechsel."""
    for points, color in DIGITS:
        lm.clear()
        lm.draw_list(points, color)
        lm.apply()
        sleep_ms(450)
    lm.clear()
    lm.apply()


def is_cheat_bug_active(allow_center_button=True):
    """Prueft, ob der God-Mode-Bug ueber Schalter oder Stick-Klick aktiv ist."""
    if btn.switch.value() == 1:
        return True
    if allow_center_button and btn.center.value() == 0:
        return True
    return False


# ============================================================================
# Easter Egg
# ============================================================================

def trigger_bsod_reboot_sequence():

    # 1. Kurze Raum-Zeit-Implosion (Spielfeld kollabiert)
    for offset in range(4):
        low, high = offset, 7 - offset
        ring = []
        for i in range(low, high + 1):
            ring.extend([(i, low), (i, high), (low, i), (high, i)])
        lm.clear()
        lm.draw_list(ring, RAINBOW[offset])
        lm.apply()
        sleep_ms(85)

    # 2. ORIGINAL SEITLICHER WINDOWS BLUESCREEN of Death
    # Links Doppelpunkt ":" (x=2) und rechts daneben der traurige Bogen "(" (x=4,5)
    bsod_sideways_smiley = [
        (2, 6),                          # Oberes Auge "."
        (2, 3),                          # Unteres Auge "."
        (5, 7), (4, 6), (4, 5), (4, 4), (4, 3), (5, 2)  # Klammer "("
    ]

    # 6 Sekunden Ladebalken unten (y=0) von LINKS (x=0) nach RECHTS (x=7)
    # 8 Schritte à 750ms = exakt 6.0 Sekunden
    for step in range(8):
        lm.fill((0, 25, 190))  # Klassisches Windows-Bluescreen-Blau
        lm.draw_list(bsod_sideways_smiley, ColorTable.WHITE)

        # Untere Zeile (y=0): Dunkelblauer Hintergrund für den Balken
        lm.draw_list([(x, 0) for x in range(8)], (0, 10, 80))
        # Weisser Fortschrittsbalken wächst langsam von links nach rechts
        progress_bar = [(x, 0) for x in range(step + 1)]
        lm.draw_list(progress_bar, ColorTable.WHITE)

        lm.apply()
        sleep_ms(750)

    # 3. BLACK SCREEN (Monitore schalten kurz ab)
    lm.clear()
    lm.apply()
    sleep_ms(900)

    # 4. MINIMALISTISCHES 4-PIXEL WINDOWS-LOGO EXAKT IN DER MITTE
    lm.clear()
    lm.draw_list([(3, 4)], ColorTable.RED)     # Oben links: Rot
    lm.draw_list([(4, 4)], ColorTable.LIME)    # Oben rechts: Grün
    lm.draw_list([(3, 3)], ColorTable.AQUA)    # Unten links: Blau
    lm.draw_list([(4, 3)], ColorTable.YELLOW)  # Unten rechts: Gelb
    lm.apply()
    sleep_ms(1600)

    # 5. Zurück zum ursprünglichen Lumatrix Boot-Ladebalken!
    boot_loading_bar()


# ============================================================================
# MINISPIEL 1: DOODLE JUMP
# ============================================================================

def run_doodle():
    player_x = 3.5
    player_y = 1.0
    velocity_y = 0.58

    platforms = [[0.0, 0, 8]]
    current_y = 2.2
    while current_y < 7.0:
        width = random.choice([2, 3, 4])
        max_x = 7 if width == 1 else (6 if width == 2 else (5 if width == 3 else 4))
        platforms.append([current_y, random.randint(0, max_x), width])
        current_y += random.choice([2.1, 2.3, 2.5])

    frame = 0
    while True:
        if frame % 25 == 0:
            gc.collect()

        bug_mode = is_cheat_bug_active(allow_center_button=True)

        if btn.left.value() == 0:
            player_x = (player_x - 0.44) % 8.0
        elif btn.right.value() == 0:
            player_x = (player_x + 0.44) % 8.0

        old_y = player_y
        velocity_y -= 0.045
        player_y += velocity_y

        # Landung auf Plattform-Oberkante
        if velocity_y <= 0:
            for plat in platforms:
                plat_y, plat_x, plat_w = plat[0], plat[1], plat[2]
                if old_y >= plat_y + 0.8 and (plat_y + 0.55 <= player_y <= plat_y + 1.25):
                    if plat_x <= int(round(player_x)) % 8 < plat_x + plat_w:
                        player_y = plat_y + 1.0
                        velocity_y = 0.85 if bug_mode else 0.58
                        break

        # BUG-FEATURE: Boden wird zum Super-Trampolin
        if bug_mode and player_y < 0.5:
            player_y = 0.5
            velocity_y = 0.95

        # Kamera scrollt hoch
        if player_y > 3.8:
            scroll = player_y - 3.8
            player_y = 3.8
            for plat in platforms:
                plat[0] -= scroll

            platforms = [p for p in platforms if p[0] >= -0.5]
            highest_y = max(p[0] for p in platforms)
            while highest_y < 7.2:
                highest_y += random.choice([2.1, 2.3, 2.5])
                width = random.choice([2, 3])
                max_x = 6 if width == 2 else 5
                platforms.append([highest_y, random.randint(0, max_x), width])

        if player_y < -0.2:
            return "LOSE"

        lm.clear()
        if bug_mode:
            lm.draw_list([(x, 0) for x in range(8)], RAINBOW[frame % 6])

        for plat in platforms:
            ry = int(round(plat[0]))
            if 0 <= ry < 8:
                pts = [(plat[1] + i, ry) for i in range(plat[2]) if 0 <= plat[1] + i < 8]
                lm.draw_list(pts, ColorTable.GREEN)

        player_color = RAINBOW[frame % 6] if bug_mode else ColorTable.YELLOW
        draw_y = int(round(player_y))
        if 0 <= draw_y < 8:
            lm.draw_list([(int(round(player_x)) % 8, draw_y)], player_color)

        lm.apply()
        sleep_ms(35)
        frame += 1


# ============================================================================
# MINISPIEL 2: SPACE DEFENDER
# ============================================================================

def run_space():
    ship_x = 3
    lasers = []
    aliens = []
    explosions = []

    shoot_cooldown = 0
    move_cooldown = 0
    frame = 0

    alien_speed = random.choice([5, 6, 7])
    spawn_rate = random.choice([11, 13, 15])

    while True:
        if frame % 25 == 0:
            gc.collect()

        bug_mode = is_cheat_bug_active(allow_center_button=False)

        if move_cooldown > 0:
            move_cooldown -= 1
        elif btn.left.value() == 0 and ship_x > 0:
            ship_x -= 1
            move_cooldown = 2
        elif btn.right.value() == 0 and ship_x < 7:
            ship_x += 1
            move_cooldown = 2

        if shoot_cooldown > 0:
            shoot_cooldown -= 1
        elif bug_mode:
            for offset in (-1, 0, 1):
                laser_x = max(0, min(7, ship_x + offset))
                lasers.append([laser_x, 1])
            shoot_cooldown = 2
        elif btn.center.value() == 0 or btn.up.value() == 0:
            lasers.append([ship_x, 1])
            shoot_cooldown = 3

        for laser in lasers:
            laser[1] += 1
        lasers = [l for l in lasers if l[1] <= 7]

        if frame % spawn_rate == 0:
            aliens.append([random.randint(0, 7), 7])
        if frame % alien_speed == 0:
            for alien in aliens:
                alien[1] -= 1

        hit_lasers = []
        hit_aliens = []
        for li, laser in enumerate(lasers):
            for ai, alien in enumerate(aliens):
                if laser[0] == alien[0] and laser[1] >= alien[1]:
                    hit_lasers.append(li)
                    hit_aliens.append(ai)
                    explosions.append([alien[0], alien[1], 2])
                    break

        lasers = [l for i, l in enumerate(lasers) if i not in hit_lasers]
        aliens = [a for i, a in enumerate(aliens) if i not in hit_aliens]

        for alien in aliens:
            if alien[1] <= 0 and alien[0] == ship_x and not bug_mode:
                return "LOSE"
        aliens = [a for a in aliens if a[1] > 0]

        lm.clear()
        laser_color = RAINBOW[frame % 6] if bug_mode else ColorTable.LIME
        for laser in lasers:
            lm.draw_list([(laser[0], laser[1])], laser_color)
        for alien in aliens:
            lm.draw_list([(alien[0], alien[1])], ColorTable.PURPLE)
        for exp in explosions:
            lm.draw_list([(exp[0], exp[1])], ColorTable.YELLOW)
            exp[2] -= 1
        explosions = [e for e in explosions if e[2] > 0]

        if ship_x > 0:
            lm.draw_list([(ship_x - 1, 0)], (0, 30, 80))
        if ship_x < 7:
            lm.draw_list([(ship_x + 1, 0)], (0, 30, 80))
        lm.draw_list([(ship_x, 0)], ColorTable.AQUA)

        lm.apply()
        sleep_ms(35)
        frame += 1


# ============================================================================
# MINISPIEL 3: CROSSY ROAD
# ============================================================================

def build_random_crossy_level():
    car_colors = [ColorTable.RED, ColorTable.YELLOW, ColorTable.PINK, ColorTable.ORANGE, ColorTable.AQUA]
    safe_island_y = random.choice([2, 3, 4, 5])
    lanes = []
    cars = {}

    for y in range(8):
        if y in (0, 7, safe_island_y):
            lanes.append((0.0, None, 0))
        else:
            direction = random.choice([-1, 1])
            speed = direction * random.choice([0.12, 0.16, 0.20])
            color = random.choice(car_colors)
            length = random.choice([1, 2])
            lanes.append((speed, color, length))

            start_x = random.uniform(0.0, 3.5)
            cars[y] = [start_x, (start_x + 4.0) % 8.0]

    return lanes, cars, safe_island_y


def run_crossy():
    player_x = 3
    player_y = 0
    move_cooldown = 0
    frame = 0

    lanes, cars, safe_mid = build_random_crossy_level()
    sparks = []

    while True:
        if frame % 25 == 0:
            gc.collect()

        bug_mode = is_cheat_bug_active(allow_center_button=True)
        step_delay = 1 if bug_mode else 3

        if move_cooldown > 0:
            move_cooldown -= 1
        elif btn.up.value() == 0 and player_y < 7:
            player_y += 1
            move_cooldown = step_delay
        elif btn.down.value() == 0 and player_y > 0:
            player_y -= 1
            move_cooldown = step_delay
        elif btn.left.value() == 0 and player_x > 0:
            player_x -= 1
            move_cooldown = step_delay
        elif btn.right.value() == 0 and player_x < 7:
            player_x += 1
            move_cooldown = step_delay

        for y, cfg in enumerate(lanes):
            if cfg[0] != 0:
                cars[y] = [(c + cfg[0]) % 8.0 for c in cars[y]]

        if player_y in cars:
            surviving_cars = []
            for cx in cars[player_y]:
                hit = False
                for part in range(lanes[player_y][2]):
                    car_x = int(round(cx + part)) % 8
                    if car_x == player_x or (bug_mode and abs(car_x - player_x) <= 1):
                        hit = True
                        break

                if hit:
                    if bug_mode:
                        sparks.append([player_x, player_y, 3])
                    else:
                        return "LOSE"
                else:
                    surviving_cars.append(cx)

            cars[player_y] = surviving_cars

            # GEHEIMES EASTER EGG: Alle Autos aufgefressen -> 6s BSOD & Windows-Reboot!
            remaining_cars = sum(len(car_list) for car_list in cars.values())
            if remaining_cars == 0 and bug_mode:
                trigger_bsod_reboot_sequence()
                return "REBOOTED"

        # Oberes Zielufer erreicht -> Neues Zufalls-Level!
        if player_y == 7 and not bug_mode:
            lm.fill(ColorTable.LIME)
            lm.apply()
            sleep_ms(150)
            player_y = 0
            lanes, cars, safe_mid = build_random_crossy_level()

        lm.clear()
        lm.draw_list([(x, 0) for x in range(8)], (0, 35, 10))
        lm.draw_list([(x, safe_mid) for x in range(8)], (20, 25, 25))
        lm.draw_list([(x, 7) for x in range(8)], (0, 60, 20))

        for y, car_list in cars.items():
            for cx in car_list:
                for part in range(lanes[y][2]):
                    lm.draw_list([(int(round(cx + part)) % 8, y)], lanes[y][1])

        for sp in sparks:
            lm.draw_list([(sp[0], sp[1])], ColorTable.YELLOW)
            sp[2] -= 1
        sparks = [s for s in sparks if s[2] > 0]

        player_color = RAINBOW[frame % 6] if bug_mode else ColorTable.WHITE
        lm.draw_list([(player_x, player_y)], player_color)

        lm.apply()
        sleep_ms(35)
        frame += 1


# ============================================================================
# MINISPIEL 4: STADLER EXPRESS
# ============================================================================

def run_stadler():
    TRACK_LANES = [1, 3, 5]
    current_lane = 1
    obstacles = []
    sparks = []
    move_cooldown = 0
    frame = 0

    spawn_interval = random.choice([6, 7, 8])

    while True:
        if frame % 25 == 0:
            gc.collect()

        bug_mode = is_cheat_bug_active(allow_center_button=True)

        if move_cooldown > 0:
            move_cooldown -= 1
        elif btn.left.value() == 0 and current_lane > 0:
            current_lane -= 1
            move_cooldown = 3
        elif btn.right.value() == 0 and current_lane < 2:
            current_lane += 1
            move_cooldown = 3

        if frame % spawn_interval == 0:
            obstacles.append([random.choice([0, 1, 2]), 7])
            if random.randint(0, 3) == 0:
                obstacles.append([random.choice([0, 1, 2]), 7])

        if frame % 2 == 0:
            for obs in obstacles:
                obs[1] -= 1

        obstacles = [o for o in obstacles if o[1] >= 0]
        train_x = TRACK_LANES[current_lane]

        surviving_obstacles = []
        for obs in obstacles:
            if obs[0] == current_lane and obs[1] in (0, 1, 2):
                if bug_mode:
                    sparks.append([train_x, obs[1], 3])
                elif obs[1] in (0, 1):
                    return "LOSE"
                else:
                    surviving_obstacles.append(obs)
            else:
                surviving_obstacles.append(obs)
        obstacles = surviving_obstacles

        lm.clear()
        for y in range(8):
            if (y + frame % 2) % 2 == 0:
                lm.draw_list([(0, y), (7, y)], (15, 15, 20))

        for obs in obstacles:
            lm.draw_list([(TRACK_LANES[obs[0]], obs[1])], ColorTable.ORANGE)

        for sp in sparks:
            lm.draw_list([(sp[0], sp[1])], ColorTable.YELLOW)
            sp[2] -= 1
        sparks = [s for s in sparks if s[2] > 0]

        if bug_mode:
            lm.draw_list([(train_x, 0), (train_x, 1), (train_x, 2)], RAINBOW[frame % 6])
        else:
            lm.draw_list([(train_x, 0)], ColorTable.RED)
            lm.draw_list([(train_x, 1)], ColorTable.WHITE)

        lm.apply()
        sleep_ms(42)
        frame += 1


# ============================================================================
# HAUPTSCHLEIFE (WARIOWARE RANDOMIZER ENGINE)
# ============================================================================

boot_loading_bar()

ALL_MINIGAMES = [run_doodle, run_space, run_crossy, run_stadler]
last_played_game = None

while True:
    gc.collect()
    play_countdown()

    available_games = [game for game in ALL_MINIGAMES if game != last_played_game]
    next_game = random.choice(available_games)
    last_played_game = next_game

    result = next_game()

    # Nur bei regulärem Tod kurz rot aufblitzen
    if result == "LOSE":
        lm.fill(ColorTable.RED)
        lm.apply()
        sleep_ms(120)