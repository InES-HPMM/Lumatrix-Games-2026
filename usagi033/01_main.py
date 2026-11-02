
from zhaw_led_matrix import LedMatrix, Button
from time import sleep_ms
import time
import math

NUM_ROWS = 8
NUM_COLS = 8

MAX_BRIGHTNESS = 60
SECONDS_PER_VIRTUAL_MINUTE = 1

WAVE_SPEED = 2.5
WAVE_STRENGTH = 0.85
MIN_WAVE_FACTOR = 0.12

FORM_MOVEMENT = 0.5
FORM_SPEED = 0.65

SEASON_NAMES = ["Fruehling", "Sommer", "Herbst", "Winter"]
WEATHER_NAMES = ["Sonne", "Bewoelkt", "Regen", "Sturm"]

SEASON_COLORS = [
    [(15, 100, 35), (35, 220, 100), (100, 160, 35)],
    [(150, 65, 0), (255, 180, 10), (220, 55, 0)],
    [(160, 45, 0), (255, 85, 0), (180, 15, 0)],
    [(15, 35, 130), (50, 160, 255), (100, 35, 160)]
]

SEASON_PATTERNS = [
    [
        "...##...", "..###...", ".####.#.", ".######.",
        "..#####.", ".######.", "..###...", "...#...."
    ],
    [
        "...##...", "..####..", ".######.", "########",
        "########", ".######.", "..####..", "...##..."
    ],
    [
        "######..", ".....##.", "#####.#.", "#...#.#.",
        "#.###.#.", "#.....#.", "#######.", "........"
    ],
    [
        "...#....", "..###...", ".#.#.#..", "########",
        ".#.#.#..", "..###...", "...#....", "........"
    ]
]

BRIGHTNESS_POINTS = [
    (6, 10), (8, 25), (10, 50), (12, 80),
    (14, 100), (16, 80), (18, 50), (20, 25), (22, 0)
]

STORM_SPEEDS = [1.35, 1.65, 1.90, 2.10]
STORM_STRENGTHS = [0.70, 0.82, 0.90, 0.92]

DEMO_TIMES = [0, 180, 420, 720, 1080, 1380]

matrix = LedMatrix(NUM_ROWS, NUM_COLS)
matrix.set_brightness(MAX_BRIGHTNESS)
matrix.clear()
matrix.apply()

btn = Button()

current_season = 0
current_weather = 0

demo_index = 0
virtual_start_minutes = DEMO_TIMES[demo_index]

real_start_ticks = time.ticks_ms()
animation_start_ticks = time.ticks_ms()
last_printed_minute = -1

# Schiebeschalter-Zustand auslesen
lamp_on = bool(btn.switch.value())


def format_time(minutes):
    minutes = int(minutes) % 1440
    hour = minutes // 60
    minute = minutes % 60
    return "{:02d}:{:02d}".format(hour, minute)


def get_virtual_minutes():
    elapsed_ms = time.ticks_diff(
        time.ticks_ms(), real_start_ticks
    )
    elapsed_seconds = elapsed_ms // 1000
    elapsed_minutes = elapsed_seconds // SECONDS_PER_VIRTUAL_MINUTE

    return (virtual_start_minutes + elapsed_minutes) % 1440


def get_day_brightness(hour):
    if hour < 6 or hour >= 22:
        return 0

    for i in range(len(BRIGHTNESS_POINTS) - 1):
        h1, b1 = BRIGHTNESS_POINTS[i]
        h2, b2 = BRIGHTNESS_POINTS[i + 1]

        if h1 <= hour <= h2:
            t = (hour - h1) / (h2 - h1)
            t = t * t * (3 - 2 * t)

            percent = b1 + (b2 - b1) * t

            return min(
                int(percent * MAX_BRIGHTNESS / 100),
                MAX_BRIGHTNESS
            )

    return 0


# Joystick hoch: nächste Demo-Zeit
def button_up(*args):
    global demo_index, virtual_start_minutes
    global real_start_ticks, last_printed_minute

    demo_index = (demo_index + 1) % len(DEMO_TIMES)
    virtual_start_minutes = DEMO_TIMES[demo_index]
    real_start_ticks = time.ticks_ms()
    last_printed_minute = -1

    print("Demo-Zeit:", format_time(virtual_start_minutes))


# Joystick rechts: nächste Jahreszeit
def button_right(*args):
    global current_season

    current_season = (current_season + 1) % len(SEASON_NAMES)
    print("Jahreszeit:", SEASON_NAMES[current_season])


# Joystick runter: nächstes Wetter
def button_down(*args):
    global current_weather

    current_weather = (current_weather + 1) % len(WEATHER_NAMES)
    print("Wetter:", WEATHER_NAMES[current_weather])


# Joystick links: Reset
def button_left(*args):
    global current_season, current_weather
    global demo_index, virtual_start_minutes
    global real_start_ticks, animation_start_ticks
    global last_printed_minute

    current_season = 0
    current_weather = 0

    demo_index = 0
    virtual_start_minutes = 0

    real_start_ticks = time.ticks_ms()
    animation_start_ticks = time.ticks_ms()
    last_printed_minute = -1

    print("RESET: 00:00, Fruehling, Sonne")


# Schiebeschalter: Lampe ein/aus
def switch_handler(*args):
    global lamp_on

    lamp_on = bool(btn.switch.value())

    if lamp_on:
        print("Mood-Lampe EIN")
    else:
        print("Mood-Lampe AUS")
        matrix.clear()
        matrix.set_brightness(0)
        matrix.apply()


btn.set_up_handler(button_up)
btn.set_right_handler(button_right)
btn.set_down_handler(button_down)
btn.set_left_handler(button_left)
btn.set_switch_handler(switch_handler)


def pixel_is_active(x, y, elapsed_seconds):
    pattern = SEASON_PATTERNS[current_season]

    if pattern[y][x] == "#":
        return True

    movement = math.sin(
        elapsed_seconds * FORM_SPEED + x * 0.8 + y * 0.6
    ) * FORM_MOVEMENT

    if current_weather == 3:
        movement *= 1.8

    if movement > 0.65:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx = x + dx
            ny = y + dy

            if 0 <= nx < NUM_COLS and 0 <= ny < NUM_ROWS:
                if pattern[ny][nx] == "#":
                    return True

    return False


def is_rain_pixel(x, y, elapsed_seconds):
    if current_weather != 2:
        return False

    rain_position = int(
        (elapsed_seconds * 2 + x * 3) % (NUM_ROWS + 3)
    )

    return y == rain_position


def get_wave_phase(x, y, elapsed_seconds):
    if current_weather == 0:
        speed = WAVE_SPEED
    elif current_weather == 1:
        speed = WAVE_SPEED * 0.30
    elif current_weather == 2:
        speed = WAVE_SPEED * 0.85
    else:
        speed = WAVE_SPEED * STORM_SPEEDS[current_season]

    if current_season == 0:
        phase = x * 0.7 + y * 0.4
    elif current_season == 1:
        phase = math.sqrt(
            (x - 3.5) ** 2 + (y - 3.5) ** 2
        )
    elif current_season == 2:
        phase = math.atan2(y - 3.5, x - 3.5) * 2
    else:
        phase = y * 0.9 + math.sin(x * 0.8)

    return elapsed_seconds * speed - phase


def get_moving_color(base_color, x, y, elapsed_seconds):
    phase = get_wave_phase(x, y, elapsed_seconds)
    wave = (math.sin(phase) + 1) / 2

    if current_weather == 0:
        strength = 0.85
    elif current_weather == 1:
        strength = 0.28
    elif current_weather == 2:
        strength = 0.70
    else:
        strength = STORM_STRENGTHS[current_season]

    factor = MIN_WAVE_FACTOR + wave * strength

    if current_weather == 3:
        gust = (math.sin(elapsed_seconds * 4 + x + y) + 1) / 2
        factor *= 0.6 + gust * 0.8

    factor = min(factor, 1.0)

    return (
        int(base_color[0] * factor),
        int(base_color[1] * factor),
        int(base_color[2] * factor)
    )


def get_weather_pixel(x, y, elapsed_seconds):
    if pixel_is_active(x, y, elapsed_seconds):
        return True

    if is_rain_pixel(x, y, elapsed_seconds):
        return True

    return False


def draw_season(minutes):
    hour = minutes / 60
    brightness = get_day_brightness(hour)

    matrix.clear()

    if brightness <= 0:
        matrix.set_brightness(0)
        matrix.apply()
        return

    elapsed_seconds = time.ticks_diff(
        time.ticks_ms(), animation_start_ticks
    ) / 1000

    colors = SEASON_COLORS[current_season]

    for y in range(NUM_ROWS):
        for x in range(NUM_COLS):
            if get_weather_pixel(x, y, elapsed_seconds):
                base_color = colors[(x + y) % len(colors)]

                color = get_moving_color(
                    base_color, x, y, elapsed_seconds
                )

                if current_weather == 3:
                    edge_factor = 0.7 + 0.3 * math.sin(
                        elapsed_seconds * 5 + x * 2 + y
                    )
                    color = (
                        int(color[0] * edge_factor),
                        int(color[1] * edge_factor),
                        int(color[2] * edge_factor)
                    )

                matrix.draw_list([[x, y]], color)

    matrix.set_brightness(min(int(brightness), MAX_BRIGHTNESS))
    matrix.apply()


print("Mood-Lampe gestartet.")
print("Virtuelle Zeit:", format_time(virtual_start_minutes))
print("Jahreszeit:", SEASON_NAMES[current_season])
print("Wetter:", WEATHER_NAMES[current_weather])
print("Schalter:", "EIN" if lamp_on else "AUS")

while True:
    if lamp_on:
        minutes = get_virtual_minutes()
        hour = minutes / 60
        brightness = get_day_brightness(hour)

        if minutes != last_printed_minute:
            brightness_percent = int(
                brightness / MAX_BRIGHTNESS * 100
            ) if MAX_BRIGHTNESS > 0 else 0

            print(
                "Virtuelle Zeit:", format_time(minutes),
                "| Brightness:", brightness_percent, "%",
                "| Matrix-Wert:", brightness
            )

            last_printed_minute = minutes

        draw_season(minutes)
    else:
        # Sicherstellen, dass die Matrix ausgeschaltet bleibt
        matrix.clear()
        matrix.set_brightness(0)
        matrix.apply()

    sleep_ms(100)