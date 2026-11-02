from core import *
import gc
gc.collect()

def make_heist_game():
    np = DimNeoPixel(Pin(19, Pin.OUT), 64)
    js_right = Pin(2, Pin.IN)
    js_left  = Pin(7, Pin.IN)
    js_up    = Pin(3, Pin.IN)
    js_down  = Pin(6, Pin.IN)
    js_center = Pin(8, Pin.IN)
    OFF     = (0, 0, 0)
    WHITE   = (80, 80, 80)
    BLUE    = (0, 0, 150)
    CYAN    = (0, 130, 170)
    GREEN   = (0, 150, 0)
    YELLOW  = (150, 100, 0)
    RED     = (180, 0, 0)
    PURPLE  = (90, 0, 150)
    ORANGE  = (180, 50, 0)
    GREY    = (35, 35, 35)
    LEVEL_COUNT = 10
    LEVEL_TIMES = [
        30, 32, 35, 38, 42,
        46, 50, 54, 58, 65
    ]
    LEVEL_OBJECTIVES = [
        ((0, 0), (5, 5), (7, 7)),
        ((0, 0), (6, 5), (7, 7)),
        ((0, 0), (4, 6), (7, 7)),
        ((0, 0), (5, 6), (7, 7)),
        ((0, 0), (6, 4), (7, 7)),
        ((0, 0), (4, 6), (7, 7)),
        ((0, 0), (6, 5), (7, 7)),
        ((0, 0), (5, 6), (7, 7)),
        ((0, 0), (6, 6), (7, 7)),
        ((0, 0), (6, 6), (7, 7)),
    ]
    LEVELS = []
    def _neighbors(x, y):
        return [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]
    def _path_exists(start, target, blocked):
        queue = [start]
        visited = [start]
        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            for nx, ny in _neighbors(current[0], current[1]):
                if nx < 0 or nx > 7 or ny < 0 or ny > 7:
                    continue
                pos = (nx, ny)
                if pos in blocked:
                    continue
                if pos in visited:
                    continue
                visited.append(pos)
                queue.append(pos)
        return False
    def _generate_walls(start, key_pos, vault_pos, count):
        forbidden = [start, key_pos, vault_pos]
        candidates = []
        for y in range(8):
            for x in range(8):
                pos = (x, y)
                if pos in forbidden:
                    continue
                candidates.append(pos)
        for _ in range(500):
            shuffle_list(candidates)
            selected = candidates[:count]
            blocked = set(selected)
            if _path_exists(start, key_pos, blocked) and \
               _path_exists(key_pos, vault_pos, blocked):
                return selected
        selected = []
        for pos in candidates:
            test = selected + [pos]
            blocked = set(test)
            if _path_exists(start, key_pos, blocked) and \
               _path_exists(key_pos, vault_pos, blocked):
                selected.append(pos)
            if len(selected) == count:
                return selected
        return selected
    def _guard_count(level_index):
        if level_index <= 2:
            return 1
        elif level_index <= 5:
            return 2
        else:
            return 3
    def _spawn_guards(start, key_pos, vault_pos, walls, count):
        forbidden = set(walls)
        forbidden.add(start)
        forbidden.add(key_pos)
        forbidden.add(vault_pos)
        candidates = []
        for y in range(8):
            for x in range(8):
                pos = (x, y)
                if pos not in forbidden:
                    candidates.append(pos)
        shuffle_list(candidates)
        guards = []
        for pos in candidates:
            distance_from_start = abs(pos[0] - start[0]) + abs(pos[1] - start[1])
            if distance_from_start < 3 and len(candidates) > count + 5:
                continue
            directions = [0, 1, 2, 3]
            shuffle_list(directions)
            direction = directions[0]
            if direction in (1, 3):
                row = pos[1]
                min_x = 0
                max_x = 7
                while min_x < pos[0] and (min_x, row) in forbidden:
                    min_x += 1
                while max_x > pos[0] and (max_x, row) in forbidden:
                    max_x -= 1
                if max_x - min_x < 2:
                    continue
                guards.append({
                    "pos": [pos[0], pos[1]],
                    "dir": direction,
                    "min": min_x,
                    "max": max_x,
                })
            else:
                col = pos[0]
                min_y = 0
                max_y = 7
                while min_y < pos[1] and (col, min_y) in forbidden:
                    min_y += 1
                while max_y > pos[1] and (col, max_y) in forbidden:
                    max_y -= 1
                if max_y - min_y < 2:
                    continue
                guards.append({
                    "pos": [pos[0], pos[1]],
                    "dir": direction,
                    "min": min_y,
                    "max": max_y,
                })
            if len(guards) == count:
                break
        if len(guards) < count:
            for pos in candidates:
                if any(g["pos"][0] == pos[0] and g["pos"][1] == pos[1]
                       for g in guards):
                    continue
                if len(guards) >= count:
                    break
                guards.append({
                    "pos": [pos[0], pos[1]],
                    "dir": random.randint(0, 3),
                    "min": 0,
                    "max": 7,
                })
        return guards
    def generate_level(level_index):
        start, key_pos, vault_pos = LEVEL_OBJECTIVES[level_index]
        wall_count = level_index + 1
        wall_list = _generate_walls(
            start,
            key_pos,
            vault_pos,
            wall_count
        )
        guard_count = _guard_count(level_index)
        guard_list = _spawn_guards(
            start,
            key_pos,
            vault_pos,
            wall_list,
            guard_count
        )
        if len(wall_list) < wall_count:
            candidates = []
            forbidden = set([start, key_pos, vault_pos])
            for yy in range(8):
                for xx in range(8):
                    pos = (xx, yy)
                    if pos not in forbidden and pos not in wall_list:
                        candidates.append(pos)
            shuffle_list(candidates)
            for pos in candidates:
                if len(wall_list) >= wall_count:
                    break
                test = wall_list + [pos]
                blocked = set(test)
                if _path_exists(start, key_pos, blocked) and _path_exists(key_pos, vault_pos, blocked):
                    wall_list.append(pos)
        if len(guard_list) < guard_count:
            forbidden = set(wall_list)
            forbidden.add(start)
            forbidden.add(key_pos)
            forbidden.add(vault_pos)
            used = set((g["pos"][0], g["pos"][1]) for g in guard_list)
            candidates = []
            for yy in range(8):
                for xx in range(8):
                    pos = (xx, yy)
                    if pos not in forbidden and pos not in used:
                        candidates.append(pos)
            shuffle_list(candidates)
            for pos in candidates:
                if len(guard_list) >= guard_count:
                    break
                guard_list.append({
                    "pos": [pos[0], pos[1]],
                    "dir": random.randint(0, 3),
                    "min": 0,
                    "max": 7,
                })
        return {
            "start": start,
            "key": key_pos,
            "vault": vault_pos,
            "walls": wall_list,
            "guards": guard_list,
            "time": LEVEL_TIMES[level_index],
        }
    def create_all_levels():
        nonlocal LEVELS
        LEVELS = []
        for i in range(LEVEL_COUNT):
            LEVELS.append(generate_level(i))
    create_all_levels()
    def clear():
        for i in range(64):
            np[i] = OFF
    def show():
        np.write()
    def set_xy(x, y, color):
        if 0 <= x <= 7 and 0 <= y <= 7:
            np[x + y * 8] = color
    def fill(color):
        for i in range(64):
            np[i] = color
        show()
    def flash(color, count=2, delay=100):
        for _ in range(count):
            fill(color)
            sleep_ms(delay)
            fill(OFF)
            sleep_ms(delay)
    def boot_animation():
        clear()
        for y in range(8):
            for x in range(8):
                set_xy(x, y, BLUE)
            show()
            sleep_ms(45)
        border = []
        for x in range(8):
            border.append((x, 0))
            border.append((x, 7))
        for y in range(1, 7):
            border.append((0, y))
            border.append((7, y))
        for _ in range(2):
            clear()
            for x, y in border:
                set_xy(x, y, CYAN)
            show()
            sleep_ms(120)
            clear()
            show()
            sleep_ms(80)
    def menu_animation():
        for shift in range(8):
            clear()
            for y in range(2, 6):
                set_xy(0, y, PURPLE)
            for x in range(0, 3):
                set_xy(x, 3, PURPLE)
            for y in range(2, 6):
                set_xy(2, y, PURPLE)
            for x in range(4, 7):
                set_xy(x, 2, BLUE)
                set_xy(x, 3, BLUE)
                set_xy(x, 4, BLUE)
                set_xy(x, 5, BLUE)
            show()
            sleep_ms(100)
        flash(PURPLE, 1, 180)
    player = [0, 0]
    key = [0, 0]
    vault = [0, 0]
    walls = []
    guards = []
    level_number = 0
    has_key = False
    alarm_count = 0
    level_start_time = 0
    guard_last_move = 0
    last_input = 0
    caught_count = 0
    def reset_level(number):
        nonlocal player, key, vault, walls, guards
        nonlocal has_key, level_start_time, guard_last_move
        nonlocal LEVELS
        LEVELS[number] = generate_level(number)
        data = LEVELS[number]
        player = [data["start"][0], data["start"][1]]
        key = [data["key"][0], data["key"][1]]
        vault = [data["vault"][0], data["vault"][1]]
        walls = []
        for w in data["walls"]:
            walls.append((w[0], w[1]))
        guards = []
        for g in data["guards"]:
            guards.append({
                "pos": [g["pos"][0], g["pos"][1]],
                "dir": g["dir"],
                "min": g["min"],
                "max": g["max"],
            })
        has_key = False
        level_start_time = ticks_ms()
        guard_last_move = ticks_ms()
    def is_wall(x, y):
        return (x, y) in walls
    def read_joystick():
        if js_right.value() == 0:
            return "right"
        if js_left.value() == 0:
            return "left"
        if js_up.value() == 0:
            return "up"
        if js_down.value() == 0:
            return "down"
        if js_center.value() == 0:
            return "center"
        return None
    def move_player(direction):
        x = player[0]
        y = player[1]
        nx = x
        ny = y
        if direction == "right":
            nx += 1
        elif direction == "left":
            nx -= 1
        elif direction == "up":
            ny += 1
        elif direction == "down":
            ny -= 1
        if nx < 0 or nx > 7 or ny < 0 or ny > 7:
            return
        if is_wall(nx, ny):
            set_xy(x, y, ORANGE)
            show()
            sleep_ms(35)
            return
        player[0] = nx
        player[1] = ny
    def guard_step(guard):
        x = guard["pos"][0]
        y = guard["pos"][1]
        direction = guard["dir"]
        nx = x
        ny = y
        if direction == 0:
            ny += 1
        elif direction == 1:
            nx += 1
        elif direction == 2:
            ny -= 1
        elif direction == 3:
            nx -= 1
        if direction in (1, 3):
            if nx < guard["min"] or nx > guard["max"] or is_wall(nx, y):
                if direction == 1:
                    guard["dir"] = 3
                else:
                    guard["dir"] = 1
                return
        if direction in (0, 2):
            if ny < guard["min"] or ny > guard["max"] or is_wall(x, ny):
                if direction == 0:
                    guard["dir"] = 2
                else:
                    guard["dir"] = 0
                return
        if not is_wall(nx, ny):
            guard["pos"][0] = nx
            guard["pos"][1] = ny
    def update_guards():
        nonlocal guard_last_move
        now = ticks_ms()
        speed = 650 - level_number * 50
        if ticks_diff(now, guard_last_move) >= speed:
            for guard in guards:
                guard_step(guard)
            guard_last_move = now
    def direction_vector(direction):
        if direction == 0:
            return (0, 1)
        if direction == 1:
            return (1, 0)
        if direction == 2:
            return (0, -1)
        return (-1, 0)
    def _vision_directions(direction):
        return [direction]
    def _direction_vector(direction):
        if direction == 0:
            return (0, 1)
        if direction == 1:
            return (1, 0)
        if direction == 2:
            return (0, -1)
        return (-1, 0)
    def guard_sees_player(guard):
        gx = guard["pos"][0]
        gy = guard["pos"][1]
        px = player[0]
        py = player[1]
        vision_dirs = _vision_directions(guard["dir"])
        max_distance = 3 if level_number >= 4 else 2
        for direction in vision_dirs:
            dx, dy = _direction_vector(direction)
            x = gx + dx
            y = gy + dy
            for _ in range(max_distance):
                if x < 0 or x > 7 or y < 0 or y > 7:
                    break
                if is_wall(x, y):
                    break
                if x == px and y == py:
                    return True
                x += dx
                y += dy
        return False
    def player_detected():
        for guard in guards:
            if guard["pos"][0] == player[0] and guard["pos"][1] == player[1]:
                return True
            if guard_sees_player(guard):
                return True
        return False
    def draw_game():
        clear()
        for x, y in walls:
            set_xy(x, y, GREY)
        for guard in guards:
            gx = guard["pos"][0]
            gy = guard["pos"][1]
            vision_dirs = _vision_directions(guard["dir"])
            max_distance = 3 if level_number >= 4 else 2
            for direction in vision_dirs:
                dx, dy = _direction_vector(direction)
                x = gx + dx
                y = gy + dy
                for _ in range(max_distance):
                    if x < 0 or x > 7 or y < 0 or y > 7:
                        break
                    if is_wall(x, y):
                        break
                    if level_number >= 4:
                        set_xy(x, y, (65, 20, 0))
                    else:
                        set_xy(x, y, (45, 15, 0))
                    x += dx
                    y += dy
        if not has_key:
            set_xy(key[0], key[1], YELLOW)
        if has_key:
            set_xy(vault[0], vault[1], GREEN)
        else:
            set_xy(vault[0], vault[1], BLUE)
        for guard in guards:
            set_xy(guard["pos"][0], guard["pos"][1], RED)
        set_xy(player[0], player[1], CYAN)
        show()
    def alarm_animation():
        nonlocal alarm_count
        alarm_count += 1
        for _ in range(2):
            clear()
            for x in range(8):
                set_xy(x, 0, RED)
                set_xy(x, 7, RED)
            for y in range(8):
                set_xy(0, y, RED)
                set_xy(7, y, RED)
            show()
            sleep_ms(100)
            clear()
            show()
            sleep_ms(80)
        data = LEVELS[level_number]
        player[0] = data["start"][0]
        player[1] = data["start"][1]
    def level_complete_animation():
        for radius in range(1, 5):
            clear()
            left = 4 - radius
            right = 3 + radius
            bottom = 4 - radius
            top = 3 + radius
            for x in range(max(0, left), min(8, right + 1)):
                for y in range(max(0, bottom), min(8, top + 1)):
                    if (x + y + radius) % 2 == 0:
                        set_xy(x, y, GREEN)
                    else:
                        set_xy(x, y, CYAN)
            show()
            sleep_ms(120)
        fill(GREEN)
        sleep_ms(250)
        clear()
        show()
    def game_over_animation():
        arcade_result_screen(False)
    def show_heist_lives(lives):
        clear()
        for i in range(max(0, lives)):
            set_xy(2 + i * 2, 3, GREEN)
        show()
        sleep_ms(500)
    def final_win_animation():
        arcade_result_screen(True)
    def time_left():
        elapsed = ticks_diff(ticks_ms(), level_start_time) // 1000
        limit = LEVELS[level_number]["time"]
        remaining = limit - elapsed
        if remaining < 0:
            remaining = 0
        return remaining
    def wait_for_center():
        while True:
            if js_center.value() == 0:
                sleep_ms(250)
                return
            sleep_ms(20)
    def play_level():
        nonlocal has_key, last_input, caught_count
        reset_level(level_number)
        last_input = ticks_ms()
        safe_until = ticks_ms() + 900
        while True:
            now = ticks_ms()
            if time_left() <= 0:
                game_over_animation()
                return False
            if ticks_diff(now, last_input) >= 120:
                direction = read_joystick()
                if direction in ("right", "left", "up", "down"):
                    move_player(direction)
                    if player[0] == key[0] and player[1] == key[1]:
                        has_key = True
                    if has_key and player[0] == vault[0] and player[1] == vault[1]:
                        return True
                    last_input = now
            update_guards()
            if ticks_diff(now, safe_until) >= 0 and player_detected():
                alarm_animation()
                caught_count += 1
                show_heist_lives(3 - caught_count)
                if caught_count >= 3:
                    game_over_animation()
                    return "lost"
                player[0] = LEVELS[level_number]["start"][0]
                player[1] = LEVELS[level_number]["start"][1]
                safe_until = ticks_ms() + 900
            draw_game()
            sleep_ms(20)
    def launch():
        nonlocal level_number, alarm_count, caught_count
        level_number = 0
        alarm_count = 0
        caught_count = 0
        show_heist_lives(3)
        while level_number < LEVEL_COUNT:
            show_level_intro(level_number + 1)
            result = play_level()
            if result == "lost":
                return
            if not result:
                return
            level_number += 1
            if level_number < len(LEVELS):
                sleep_ms(300)
        final_win_animation()
        return
    return launch

