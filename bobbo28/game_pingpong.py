from core import *
import gc
gc.collect()

def make_pingpong_game():
    np = DimNeoPixel(Pin(19, Pin.OUT), 64)
    LEFT = Pin(7, Pin.IN)
    RIGHT = Pin(2, Pin.IN)
    UP = Pin(3, Pin.IN)
    DOWN = Pin(6, Pin.IN)
    CENTER = Pin(8, Pin.IN)
    OFF = (0, 0, 0)
    WHITE = (80, 80, 80)
    PLAYER = (0, 220, 255)
    CPU = (255, 60, 0)
    BALL = (255, 255, 255)
    GREEN = (0, 255, 80)
    YELLOW = (255, 190, 0)
    RED = (255, 0, 0)
    WIN_SCORE = 5
    PADDLE_SIZE = 3
    def xy(x, y):
        return x + y * 8
    def set_xy(x, y, color):
        if 0 <= x < 8 and 0 <= y < 8:
            np[xy(x, y)] = color
    def clear():
        np.fill(OFF)
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
        if CENTER.value() == 0:
            return "center"
        return None
    def release():
        while UP.value() == 0 or DOWN.value() == 0 or CENTER.value() == 0:
            sleep_ms(20)
    def wait_center():
        release()
        while CENTER.value() != 0:
            sleep_ms(20)
        sleep_ms(120)
        release()
    def boot_animation():
        clear()
        for x in range(8):
            set_xy(x, 3, PLAYER)
            set_xy(7 - x, 4, CPU)
            show()
            sleep_ms(40)
            clear()
        for color in (PLAYER, CPU, WHITE):
            fill(color)
            sleep_ms(70)
        clear()
        show()
    def title_animation():
        for x in range(1, 7):
            clear()
            set_xy(0, 2, PLAYER)
            set_xy(0, 3, PLAYER)
            set_xy(0, 4, PLAYER)
            set_xy(7, 3, CPU)
            set_xy(7, 4, CPU)
            set_xy(x, 3 if x % 2 else 4, BALL)
            show()
            sleep_ms(80)
        clear()
        show()
    def score_flash(color):
        for _ in range(2):
            fill(color)
            sleep_ms(80)
            clear()
            show()
            sleep_ms(80)
    def result_screen(won):
        arcade_result_screen(won)
    def draw_game(player_y, cpu_y, ball_x, ball_y,
                  player_score, cpu_score):
        clear()
        for y in range(0, 8, 2):
            set_xy(3, y, (20, 20, 20))
        for dy in range(PADDLE_SIZE):
            set_xy(0, player_y + dy, PLAYER)
            set_xy(7, cpu_y + dy, CPU)
        set_xy(ball_x, ball_y, BALL)
        for i in range(min(player_score, 5)):
            set_xy(i, 0, PLAYER)
        for i in range(min(cpu_score, 5)):
            set_xy(7 - i, 0, CPU)
        show()
    def reset_ball(direction):
        ball_x = 3 if direction > 0 else 4
        ball_y = random.randint(2, 5)
        ball_dx = direction
        ball_dy = random.choice([-1, 1])
        return ball_x, ball_y, ball_dx, ball_dy
    def launch():
        player_y = 2
        cpu_y = 2
        player_score = 0
        cpu_score = 0
        ball_x, ball_y, ball_dx, ball_dy = reset_ball(
            random.choice([-1, 1])
        )
        last_input = ticks_ms()
        last_ball = ticks_ms()
        rally = 0
        paused = False
        cpu_last_move = ticks_ms()
        cpu_last_read = ticks_ms()
        cpu_seen_ball_y = ball_y
        CPU_READ_DELAY = 420  
        while player_score < WIN_SCORE and cpu_score < WIN_SCORE:
            now = ticks_ms()
            if ticks_diff(now, last_input) >= 90:
                inp = read_input()
                if inp == "up":
                    player_y += 1
                    if player_y > 5:
                        player_y = 5
                    last_input = now
                elif inp == "down":
                    player_y -= 1
                    if player_y < 0:
                        player_y = 0
                    last_input = now
                elif inp == "center":
                    release()
                    paused = not paused
                    last_input = now
            if paused:
                clear()
                for y in range(2, 6):
                    set_xy(2, y, YELLOW)
                    set_xy(5, y, YELLOW)
                show()
                sleep_ms(30)
                continue
            ball_delay = max(150, 260 - rally * 2)
            if ticks_diff(now, cpu_last_read) >= CPU_READ_DELAY:
                cpu_seen_ball_y = ball_y
                cpu_last_read = now
            cpu_reaction_delay = max(100 , ball_delay * 80 // 100)
            if ball_dx > 0 and ticks_diff(now, cpu_last_move) >= cpu_reaction_delay:
                target_y = cpu_seen_ball_y
                if target_y < cpu_y:
                    cpu_y -= 1
                elif target_y > cpu_y + PADDLE_SIZE - 1:
                    cpu_y += 1
                cpu_y = max(0, min(8 - PADDLE_SIZE, cpu_y))
                cpu_last_move = now
            if ticks_diff(now, last_ball) >= ball_delay:
                new_x = ball_x + ball_dx
                new_y = ball_y + ball_dy
                if new_y <= 0:
                    new_y = 0
                    ball_dy = 1
                elif new_y >= 7:
                    new_y = 7
                    ball_dy = -1
                if ball_x == 1 and ball_dx < 0 and new_x == 0:
                    if player_y <= new_y <= player_y + PADDLE_SIZE - 1:
                        new_x = 1
                        ball_dx = 1
                        rally += 1
                        hit = new_y - player_y
                        if hit == 0:
                            ball_dy = -1
                        elif hit == PADDLE_SIZE - 1:
                            ball_dy = 1
                        else:
                            ball_dy = random.choice([-1, 1])
                if ball_x == 6 and ball_dx > 0 and new_x == 7:
                    if cpu_y <= new_y <= cpu_y + PADDLE_SIZE - 1:
                        new_x = 6
                        ball_dx = -1
                        rally += 1
                        hit = new_y - cpu_y
                        if hit == 0:
                            ball_dy = -1
                        elif hit == PADDLE_SIZE - 1:
                            ball_dy = 1
                        else:
                            ball_dy = random.choice([-1, 1])
                ball_x = new_x
                ball_y = new_y
                if ball_x < 0:
                    cpu_score += 1
                    rally = 0
                    score_flash(CPU)
                    if cpu_score < WIN_SCORE:
                        ball_x, ball_y, ball_dx, ball_dy = reset_ball(1)
                        cpu_last_move = ticks_ms()
                elif ball_x > 7:
                    player_score += 1
                    rally = 0
                    score_flash(PLAYER)
                    if player_score < WIN_SCORE:
                        ball_x, ball_y, ball_dx, ball_dy = reset_ball(-1)
                        cpu_last_move = ticks_ms()
                last_ball = now
            draw_game(
                player_y,
                cpu_y,
                ball_x,
                ball_y,
                player_score,
                cpu_score
            )
            sleep_ms(10)
        if player_score >= WIN_SCORE:
            result_screen(True)
        else:
            result_screen(False)
        return
    return launch
