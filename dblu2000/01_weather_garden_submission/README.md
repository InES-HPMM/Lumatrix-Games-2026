# Weather Garden - Lumatrix Games 2026

A plant you tend with the weather. It grows from a single seed, blooms into big red flowers when it gets sun,
shrinks when you ignore it and never dies. No text, no meters: everything is readable from the 64 LEDs.

Runs on the original Lumatrix: stock MicroPython and the official `zhaw_led_matrix` library. One file, `main.py`.

## Controls (the joystick really plays it)

| Input | What happens |
|---|---|
| UP (hold) | Rain. Blue drops fall and water the plant. A thirsty plant blinks two blue dots at its base. |
| LEFT / RIGHT | Wind gust. It pushes the clouds, bends the plant and the plant keeps growing toward the wind. |
| CENTER | Sunshine. The stem tips open into red blooms with a yellow centre and the clouds blow away. |
| DOWN | Prune. Removes the top cell, so a bloom disappears. |
| Slide switch | Night. The plant glows softly, stars twinkle, blooms close. |
| Breathe on the chip (optional) | The Pico's own temperature sensor warms the garden. The sun glows hotter and it grows faster. |
| Leave it alone for 30 s | Auto-mode. The garden rains, gusts, sunshines and prunes by itself. Any press takes over. |

## Cheat code

| Cheat | Presses | Effect |
|---|---|---|
| Mega bloom | UP UP DOWN DOWN LEFT RIGHT LEFT RIGHT | Every tall enough stem tip opens at once, with a rainbow shimmer for 3 s. The blooms stay open for about 30 s. |

It is meant to be found: the code has a hint next to `CHEATS` and in the header. The normal action of each press still happens
while you type the code, and auto-mode sometimes plays it by itself.

## Settings

All in the block at the top of `main.py` (`weather_garden.py` in the project), each with a comment. Edit it, save to the board, restart.

| Setting | Default | Range | What it does |
|---|---|---|---|
| `BRIGHTNESS` | 15 | 0-100 | LED brightness. Around 10-40 looks good on a phone. |
| `TICK_MS` | 350 | 100-1500 | Milliseconds per growth step. Higher = the whole garden grows and dries slower. |
| `TIME_LAPSE` | 1 | 1-4 (whole numbers) | Multiplies growth and drying speed (2-3 for a short video). |
| `FRAME_MS` | 40 | 20-100 | Frame time, about 25 fps. The Pico needs about 30 ms, so values below that change little. |
| `MAX_CELLS` | 40 | 10-40 | Size limit of the plant. |
| `TOP` | 6 | 3-6 | Highest stem row. Row 7 stays free for the flower heads. |
| `DRAIN` | 0.003 | 0-0.02 | Water lost per growth step. 0 = never gets thirsty. |
| `GROW_COST` | 0.02 | 0-0.1 | Water used by every new cell. |
| `WITHER` | 0.04 | 0-0.2 | How fast a thirsty cell fades once the plant has run dry. |
| `RAIN_EVERY` | 0.09 | 0.03-0.3 | Seconds between drops while UP is held. |
| `RAIN_WATER` | 0.04 | 0.01-0.15 | Water added by every drop that lands. |
| `WIND_LEAN` | 0.25 | 0-0.5 | How far each LEFT/RIGHT bends future growth (the total is capped at 1). |
| `WIND_SWAY` | 0.9 | 0-2 | How far a gust bends the plant, in pixels at the top. |
| `GUST_DECAY` | 0.96 | 0.8-0.99 | Per frame, must stay below 1. Closer to 1 = a gust lasts longer. |
| `WARM_FLOOR` | 0.35 | 0-0.6 | Daylight warmth without touching the chip. Above 0.6 it buds without sun. |
| `WARM_RANGE` | 4.0 | 1-10 | Degrees above the start-up temperature that count as full warmth. |
| `BUD_WARMTH` | 0.6 | 0-1 | Warmth needed to form a bud. |
| `OPEN_WARMTH` | 0.7 | 0-1 | Warmth needed to open a bloom. |
| `CLOSE_WARMTH` | 0.4 | 0-1 | Below this warmth, blooms close again. Keep it below the other two. |
| `BUD_MIN_Y` | 2 | 2-5 | Lowest row a bloom can open on. 2 keeps one green row under the head. |
| `BUD_CHANCE` | 0.25 | 0-1 | Chance per growth step that a stem tip forms a bud. |
| `OPEN_CHANCE` | 0.3 | 0-1 | Chance per growth step that a bud opens. |
| `SUN_BLOOM` | 25 | 0-60 | Seconds CENTER keeps the plant warm and the blooms open (0 = off). |
| `BLOOM_HUE` | 0.01 | 0-1 | Bloom colour on the colour wheel: 0 red, 0.07 orange, 0.15 yellow, 0.6 blue, 0.8 purple, 0.9 pink. |
| `AUTO_AFTER` | 30 | 0 or 5-600 | Seconds without a joystick press before auto-mode starts. 0 = never. |
| `NIGHT_LOW` | True | True / False | True = slide switch LOW is night. Flip it if your switch works the other way round. |

Ranges are safe suggestions. I tested the defaults and the values I used for the video, not every extreme.

## How it was made

The idea and the design decisions are mine. The code was written with AI (Claude Code), which the rules allow.
It was checked in a desktop simulation and on a real Lumatrix with MicroPython v1.29.0.
