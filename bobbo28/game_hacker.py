from core import *
import gc
gc.collect()

def make_hacker_game():
    LED_PIN = 19
    LED_COUNT = 64
    np = DimNeoPixel(Pin(LED_PIN, Pin.OUT), LED_COUNT)
    LEFT = Pin(7, Pin.IN)
    RIGHT = Pin(2, Pin.IN)
    UP = Pin(3, Pin.IN)
    DOWN = Pin(6, Pin.IN)
    CENTER = Pin(8, Pin.IN)
    BOARD = 8
    OFF = (0, 0, 0)
    WHITE = (255, 255, 255)
    CYAN = (0, 255, 255)
    BLUE = (0, 80, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    YELLOW = (255, 190, 0)
    ORANGE = (255, 70, 0)
    PURPLE = (170, 0, 255)
    LEVELS = 8
    START_LIVES = 3
    START_TIME = 35
    MIN_TIME = 18
    PLAYER_COLOR = CYAN
    DATA_COLOR = GREEN
    CORE_COLOR = PURPLE
    FIREWALL_COLOR = BLUE
    ICE_COLOR = RED
    def xy(x, y):
        return x + y * 8
    def set_xy(x, y, color):
        if 0 <= x < BOARD and 0 <= y < BOARD:
            np[xy(x, y)] = color
    def clear():
        np.fill(OFF)
        np.write()
    def show():
        np.write()
    def fill(color):
        np.fill(color)
        np.write()
    def read_input():
        if UP.value() == 0:
            return "up"
        if DOWN.value() == 0:
            return "down"
        if LEFT.value() == 0:
            return "left"
        if RIGHT.value() == 0:
            return "right"
        if CENTER.value() == 0:
            return "center"
        return None
    def wait_release():
        while (
            UP.value() == 0 or
            DOWN.value() == 0 or
            LEFT.value() == 0 or
            RIGHT.value() == 0 or
            CENTER.value() == 0
        ):
            sleep_ms(20)
    def wait_center():
        wait_release()
        while CENTER.value() != 0:
            sleep_ms(20)
        sleep_ms(100)
        wait_release()
    def boot_animation():
        for _ in range(2):
            for x in range(8):
                clear()
                for y in range(8):
                    if random.randint(0, 100) < 45:
                        set_xy(x, y, CYAN)
                show()
                sleep_ms(45)
        clear()
        show()
    def hacker_title():
        frames = [
            [
                "10001001",
                "10001001",
                "11111001",
                "10001001",
                "10001001",
                "00000000",
                "01110111",
                "00000000",
            ],
            [
                "11111111",
                "10000001",
                "10111101",
                "10100101",
                "10111101",
                "10000001",
                "11111111",
                "00000000",
            ],
        ]
        for frame in frames:
            clear()
            for y in range(8):
                for x in range(8):
                    if frame[y][x] == "1":
                        set_xy(x, 7 - y, GREEN)
            show()
            sleep_ms(300)
    def success_animation():
        for color in (GREEN, CYAN, BLUE):
            fill(color)
            sleep_ms(90)
        clear()
        show()
    def alarm_animation():
        for _ in range(3):
            fill(RED)
            sleep_ms(90)
            clear()
            sleep_ms(90)
    def level_complete_animation():
        heist_level_animation(set_xy, clear, show, sleep_ms, GREEN, CYAN)
    def game_over_animation():
        arcade_result_screen(False)
    def neighbors(pos):
        x, y = pos
        return [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]
    def reachable(start, target, walls):
        queue = [start]
        visited = [start]
        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            for pos in neighbors(current):
                x, y = pos
                if x < 0 or x > 7:
                    continue
                if y < 0 or y > 7:
                    continue
                if pos in walls:
                    continue
                if pos in visited:
                    continue
                visited.append(pos)
                queue.append(pos)
        return False
    def generate_level(level):
        start = (0, 0)
        core = (7, 7)
        wall_count = min(2 + level, 12)
        candidates = []
        for y in range(8):
            for x in range(8):
                pos = (x, y)
                if pos != start and pos != core:
                    candidates.append(pos)
        for _ in range(300):
            shuffle_list(candidates)
            walls = candidates[:wall_count]
            if reachable(start, core, walls):
                break
        data_count = min(2 + level // 2, 5)
        free = [
            p for p in candidates
            if p not in walls
        ]
        shuffle_list(free)
        data = []
        for pos in free:
            if pos == start or pos == core:
                continue
            if abs(pos[0]) + abs(pos[1]) < 2:
                continue
            data.append(pos)
            if len(data) >= data_count:
                break
        ice_count = 1 if level < 3 else 2 if level < 6 else 3
        ice = []
        for pos in free:
            if pos in walls or pos in data:
                continue
            if abs(pos[0]) + abs(pos[1]) < 4:
                continue
            if pos == core:
                continue
            ice.append({
                "x": pos[0],
                "y": pos[1],
                "dir": random.choice([-1, 1]),
                "axis": random.choice(["x", "y"]),
            })
            if len(ice) >= ice_count:
                break
        return {
            "start": start,
            "core": core,
            "walls": walls,
            "data": data,
            "ice": ice,
            "time": max(MIN_TIME, START_TIME - level * 2),
        }
    def draw_level(player, level_data, score, data_collected, alarm):
        clear()
        for x, y in level_data["walls"]:
            set_xy(x, y, FIREWALL_COLOR)
        for x, y in level_data["data"]:
            set_xy(x, y, DATA_COLOR)
        set_xy(
            level_data["core"][0],
            level_data["core"][1],
            CORE_COLOR
        )
        for guard in level_data["ice"]:
            set_xy(
                guard["x"],
                guard["y"],
                ICE_COLOR
            )
        set_xy(player[0], player[1], PLAYER_COLOR)
        if alarm:
            set_xy(7, 0, RED)
        show()
    def move_ice(level_data):
        for guard in level_data["ice"]:
            x = guard["x"]
            y = guard["y"]
            nx = x
            ny = y
            if guard["axis"] == "x":
                nx += guard["dir"]
                if nx < 0 or nx > 7:
                    guard["dir"] *= -1
                    nx = x + guard["dir"]
            else:
                ny += guard["dir"]
                if ny < 0 or ny > 7:
                    guard["dir"] *= -1
                    ny = y + guard["dir"]
            pos = (nx, ny)
            if pos in level_data["walls"]:
                guard["dir"] *= -1
                continue
            if pos == level_data["core"]:
                guard["dir"] *= -1
                continue
            guard["x"] = nx
            guard["y"] = ny
    def ice_hits_player(player, level_data):
        for guard in level_data["ice"]:
            if (
                guard["x"] == player[0] and
                guard["y"] == player[1]
            ):
                return True
        return False
    def move_player(player, direction, walls):
        x, y = player
        if direction == "up":
            y += 1
        elif direction == "down":
            y -= 1
        elif direction == "left":
            x -= 1
        elif direction == "right":
            x += 1
        new_pos = (x, y)
        if x < 0 or x > 7:
            return player
        if y < 0 or y > 7:
            return player
        if new_pos in walls:
            return player
        return new_pos
    def show_lives(lives):
        clear()
        for i in range(max(0, lives)):
            set_xy(2 + i * 2, 3, GREEN)
        show()
        sleep_ms(450)
    def play_level(level_number, lives):
        level_data = generate_level(level_number)
        player = level_data["start"]
        data_left = list(level_data["data"])
        data_collected = 0
        score = 0
        alarm = False
        start_time = ticks_ms()
        last_input = ticks_ms()
        last_ice_move = ticks_ms()
        ice_speed = max(
            160,
            430 - level_number * 28
        )
        draw_level(
            player,
            level_data,
            score,
            data_collected,
            alarm
        )
        while True:
            now = ticks_ms()
            elapsed = ticks_diff(now, start_time)
            if elapsed >= level_data["time"] * 1000:
                alarm_animation()
                lives -= 1
                show_lives(lives)
                return False, score, lives, False
            if ticks_diff(now, last_input) >= 100:
                inp = read_input()
                if inp == "center":
                    wait_release()
                    return False, score, lives, True
                if inp in ("up", "down", "left", "right"):
                    new_player = move_player(
                        player,
                        inp,
                        level_data["walls"]
                    )
                    if new_player != player:
                        player = new_player
                    last_input = now
            if player in data_left:
                data_left.remove(player)
                data_collected += 1
                score += 25 + data_collected * 5
            if ticks_diff(now, last_ice_move) >= ice_speed:
                move_ice(level_data)
                last_ice_move = now
                if ice_hits_player(player, level_data):
                    alarm = True
                    alarm_animation()
                    lives -= 1
                    show_lives(lives)
                    if lives <= 0:
                        return False, score, lives, False
                    player = level_data["start"]
                    score = max(0, score - 15)
                    alarm = False
            if player == level_data["core"]:
                if len(data_left) == 0:
                    remaining = max(
                        0,
                        level_data["time"] * 1000 - elapsed
                    )
                    score += 50 + remaining // 100
                    return True, score, lives, False
                else:
                    set_xy(7, 7, PURPLE)
                    show()
                    sleep_ms(80)
            draw_level(
                player,
                {
                    "walls": level_data["walls"],
                    "data": data_left,
                    "core": level_data["core"],
                    "ice": level_data["ice"],
                },
                score,
                data_collected,
                alarm
            )
            sleep_ms(15)
    def victory_animation():
        arcade_result_screen(True)
    def play_hacker():
        total_score = 0
        completed = 0
        lives = START_LIVES
        show_lives(lives)
        for level in range(1, LEVELS + 1):
            show_level_intro(level)
            while True:
                success, score, lives, quit_requested = play_level(level, lives)
                total_score += score
                if success:
                    break
                if quit_requested:
                    game_over_animation()
                    return "quit", total_score
                if lives <= 0:
                    game_over_animation()
                    return "lose", total_score
                sleep_ms(250)
            completed += 1
            sleep_ms(250)
        victory_animation()
        total_score += 500
        return "win", total_score
    def launch():
        play_hacker()
        return
    return launch
GAME_NAMES = ["HEIST", "SNAKE", "PING PONG", "CYBER VIRUS"]
