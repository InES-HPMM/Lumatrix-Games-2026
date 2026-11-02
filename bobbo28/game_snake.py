from core import *
import gc
gc.collect()

def make_snake_game():
    LED_PIN = 19
    LED_COUNT = 64
    np = DimNeoPixel(Pin(LED_PIN, Pin.OUT), LED_COUNT)
    LEFT = Pin(7, Pin.IN)
    RIGHT = Pin(2, Pin.IN)
    UP = Pin(3, Pin.IN)
    DOWN = Pin(6, Pin.IN)
    CENTER = Pin(8, Pin.IN)
    OFF = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 80, 255)
    CYAN = (0, 255, 255)
    YELLOW = (255, 190, 0)
    ORANGE = (255, 70, 0)
    PURPLE = (170, 0, 255)
    BOARD = 8
    START_LENGTH = 3
    START_SPEED = 320
    MIN_SPEED = 175
    SPEED_STEP = 8
    LIVES = 3
    FOOD_SCORE = 10
    BONUS_SCORE = 30
    BONUS_DURATION = 5000
    BONUS_CHANCE = 18       
    DIR_UP = (0, 1)
    DIR_RIGHT = (1, 0)
    DIR_DOWN = (0, -1)
    DIR_LEFT = (-1, 0)
    DIRECTIONS = [
        DIR_UP,
        DIR_RIGHT,
        DIR_DOWN,
        DIR_LEFT,
    ]
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
    def flash(color, times=2, duration=100):
        for _ in range(times):
            fill(color)
            sleep_ms(duration)
            clear()
            sleep_ms(duration)
    def read_input():
        if UP.value() == 0:
            return DIR_UP
        if DOWN.value() == 0:
            return DIR_DOWN
        if LEFT.value() == 0:
            return DIR_LEFT
        if RIGHT.value() == 0:
            return DIR_RIGHT
        if CENTER.value() == 0:
            return "center"
        return None
    def wait_for_release():
        while (
            UP.value() == 0 or
            DOWN.value() == 0 or
            LEFT.value() == 0 or
            RIGHT.value() == 0 or
            CENTER.value() == 0
        ):
            sleep_ms(20)
    def wait_center():
        wait_for_release()
        while CENTER.value() != 0:
            sleep_ms(20)
        sleep_ms(100)
        wait_for_release()
    def boot_animation():
        path = []
        for x in range(8):
            path.append((x, 0))
        for y in range(1, 8):
            path.append((7, y))
        for x in range(6, -1, -1):
            path.append((x, 7))
        for y in range(6, 0, -1):
            path.append((0, y))
        clear()
        for x, y in path:
            set_xy(x, y, GREEN)
            show()
            sleep_ms(35)
        clear()
        show()
    def title_animation():
        pattern = [
            "11111100",
            "11000000",
            "11111100",
            "00000110",
            "00000110",
            "01111110",
            "00000000",
            "00000000",
        ]
        for _ in range(2):
            clear()
            for y in range(8):
                for x in range(8):
                    if pattern[y][x] == "1":
                        set_xy(x, 7 - y, GREEN)
            show()
            sleep_ms(300)
            clear()
            sleep_ms(120)
    def life_animation(lives):
        clear()
        for i in range(lives):
            set_xy(2 + i * 2, 3, RED)
        show()
    def game_over_animation():
        arcade_result_screen(False)
    def level_up_animation():
        clear()
        for size in range(1, 5):
            min_v = 4 - size
            max_v = 3 + size
            for x in range(min_v, max_v + 1):
                if 0 <= x < 8:
                    if 0 <= min_v < 8:
                        set_xy(x, min_v, CYAN)
                    if 0 <= max_v < 8:
                        set_xy(x, max_v, CYAN)
            for y in range(min_v, max_v + 1):
                if 0 <= y < 8:
                    if 0 <= min_v < 8:
                        set_xy(min_v, y, CYAN)
                    if 0 <= max_v < 8:
                        set_xy(max_v, y, CYAN)
            show()
            sleep_ms(80)
        clear()
        show()
    def victory_animation():
        arcade_result_screen(True)
    def opposite(direction):
        return (
            direction[0] * -1,
            direction[1] * -1
        )
    def valid_position(pos):
        return (
            0 <= pos[0] < BOARD and
            0 <= pos[1] < BOARD
        )
    def create_food(snake):
        free = []
        for y in range(BOARD):
            for x in range(BOARD):
                pos = (x, y)
                if pos not in snake:
                    free.append(pos)
        if not free:
            return None
        return random.choice(free)
    def create_bonus_food(snake, normal_food):
        free = []
        for y in range(BOARD):
            for x in range(BOARD):
                pos = (x, y)
                if pos in snake:
                    continue
                if pos == normal_food:
                    continue
                free.append(pos)
        if not free:
            return None
        return random.choice(free)
    def draw_game(snake, food, bonus_food, score, lives):
        clear()
        for i in range(len(snake) - 1, -1, -1):
            x, y = snake[i]
            if i == 0:
                set_xy(x, y, CYAN)
            else:
                set_xy(x, y, GREEN)
        if food is not None:
            set_xy(food[0], food[1], RED)
        if bonus_food is not None:
            set_xy(bonus_food[0], bonus_food[1], YELLOW)
        show()
    def calculate_speed(score):
        speed = START_SPEED - (score // 10) * SPEED_STEP
        if speed < MIN_SPEED:
            speed = MIN_SPEED
        return speed
    def spawn_bonus_if_needed(snake, food):
        if random.randint(1, 100) <= BONUS_CHANCE:
            return create_bonus_food(snake, food)
        return None
    def play_snake():
        snake = [
            (3, 3),
            (2, 3),
            (1, 3),
        ]
        direction = DIR_RIGHT
        pending_direction = DIR_RIGHT
        food = create_food(snake)
        bonus_food = None
        bonus_start = 0
        score = 0
        best_score = 0
        lives = LIVES
        level = 1
        last_move = ticks_ms()
        last_input = ticks_ms()
        life_animation(lives)
        draw_game(snake, food, bonus_food, score, lives)
        while lives > 0:
            now = ticks_ms()
            if ticks_diff(now, last_input) >= 80:
                inp = read_input()
                if inp == "center":
                    wait_for_release()
                    return "quit", score
                if inp in DIRECTIONS:
                    if inp != opposite(direction):
                        pending_direction = inp
                    last_input = now
            if bonus_food is not None:
                if ticks_diff(now, bonus_start) >= BONUS_DURATION:
                    bonus_food = None
            speed = calculate_speed(score)
            if ticks_diff(now, last_move) >= speed:
                direction = pending_direction
                head_x, head_y = snake[0]
                new_head = (
                    head_x + direction[0],
                    head_y + direction[1]
                )
                if not valid_position(new_head):
                    lives -= 1
                    life_animation(lives)
                    if lives <= 0:
                        game_over_animation()
                        return "lose", score
                    snake = [
                        (3, 3),
                        (2, 3),
                        (1, 3),
                    ]
                    direction = DIR_RIGHT
                    pending_direction = DIR_RIGHT
                    food = create_food(snake)
                    bonus_food = None
                    draw_game(
                        snake,
                        food,
                        bonus_food,
                        score,
                        lives
                    )
                    last_move = ticks_ms()
                    continue
                if new_head in snake:
                    lives -= 1
                    life_animation(lives)
                    if lives <= 0:
                        game_over_animation()
                        return "lose", score
                    snake = [
                        (3, 3),
                        (2, 3),
                        (1, 3),
                    ]
                    direction = DIR_RIGHT
                    pending_direction = DIR_RIGHT
                    food = create_food(snake)
                    bonus_food = None
                    draw_game(
                        snake,
                        food,
                        bonus_food,
                        score,
                        lives
                    )
                    last_move = ticks_ms()
                    continue
                snake.insert(0, new_head)
                ate_normal = new_head == food
                ate_bonus = (
                    bonus_food is not None and
                    new_head == bonus_food
                )
                if ate_normal:
                    score += FOOD_SCORE
                    new_level = score // 30 + 1
                    if new_level > level:
                        level = new_level
                        last_move = ticks_ms()
                    food = create_food(snake)
                    bonus_food = spawn_bonus_if_needed(
                        snake,
                        food
                    )
                    if bonus_food is not None:
                        bonus_start = ticks_ms()
                elif ate_bonus:
                    score += BONUS_SCORE
                    bonus_food = None
                    food = create_food(snake)
                else:
                    snake.pop()
                if len(snake) >= 63:
                    victory_animation()
                    return "win", score
                draw_game(
                    snake,
                    food,
                    bonus_food,
                    score,
                    lives
                )
                last_move = now
            sleep_ms(10)
        return "lose", score
    def launch():
        play_snake()
        return
    return launch
