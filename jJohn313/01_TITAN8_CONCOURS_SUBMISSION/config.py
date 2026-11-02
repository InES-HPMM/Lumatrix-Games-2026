"""
TITAN 8 Configuration & Hardware Constants (config.py)
Target: Raspberry Pi Pico (RP2040) / Lumatrix 8x8 LED Matrix
"""

# -------------------------------------------------------------
# Matrix Display Configuration
# -------------------------------------------------------------
LED_PIN = 19
NUM_LEDS = 64
GRID_WIDTH = 8
GRID_HEIGHT = 8

# Global Brightness (0-100% scaling, kept modest for USB power stability)
DEFAULT_BRIGHTNESS = 40

# -------------------------------------------------------------
# Color Palette (RGB tuples 0-255)
# -------------------------------------------------------------
COLOR_BLACK          = (0, 0, 0)
COLOR_GRID_BG        = (0, 0, 0)
COLOR_WALL           = (160, 90, 20)      # Earthy bronze mountain (1 HP)
COLOR_PLAYER_CYAN    = (0, 220, 255)      # Steady saturated Cyan (2 HP)
COLOR_PLAYER_ALERT   = (255, 60, 0)       # Warning Amber (1 HP Emergency Strobe)
COLOR_PLAYER_FULL    = COLOR_PLAYER_CYAN
COLOR_PLAYER_LOW     = COLOR_PLAYER_ALERT

# Enemy Unit Colors
COLOR_ENEMY_DASHER   = (255, 20, 0)       # Dasher: Solid saturated Crimson (1 HP)
COLOR_ENEMY_MORTAR   = (220, 0, 220)      # Mortar: Vivid Magenta (1 HP)
COLOR_ENEMY_STRIKER  = (255, 130, 0)      # Striker: Amber (1 HP)

# Threat Telegraph Traces (De-noised, bleed reduction)
COLOR_TELEGRAPH_D_MIN = (6, 0, 0)         # Breathing Dasher trace min
COLOR_TELEGRAPH_D_MAX = (16, 0, 0)        # Breathing Dasher trace max
COLOR_TELEGRAPH_D     = (10, 0, 0)        # Nominal Dasher trace
COLOR_TELEGRAPH_M_MIN = (30, 0, 30)       # Pulsing Mortar marker min
COLOR_TELEGRAPH_M_MAX = (70, 0, 70)       # Pulsing Mortar marker max
COLOR_TELEGRAPH_M     = (50, 0, 50)       # Nominal Mortar marker
COLOR_TELEGRAPH_S_MIN = (12, 6, 0)        # Striker trace min
COLOR_TELEGRAPH_S_MAX = (26, 13, 0)       # Striker trace max
COLOR_TELEGRAPH_S     = (18, 9, 0)

COLOR_IMPACT         = (255, 255, 255)    # Flash white on hit/collision
COLOR_SHOCKWAVE      = (12, 0, 0)         # Faint red screen shake shockwave
COLOR_CURSOR         = (180, 180, 180)    # Flash white/grey on undo
COLOR_PORTAL         = (0, 80, 255)       # Blue portal / level reset flash
COLOR_GAME_OVER      = (255, 0, 0)        # Red game over
COLOR_VICTORY        = (0, 255, 60)       # Green level clear

# Mortar Ballistic Colors
COLOR_MORTAR_LOB_START = (80, 0, 60)
COLOR_MORTAR_LOB_APEX  = (255, 120, 255)
COLOR_MORTAR_LOB_END   = (180, 0, 140)
COLOR_MORTAR_CROSS     = (55, 0, 45)      # 30% brightness magenta cross

# Kinetic & Feedback Timing Constants (ms)
STEP_DELAY_MS   = 30    # Dasher charge step / Mortar flight step
HITSTOP_MS      = 45    # White hit-stop flash duration on collision
SHAKE_MS        = 25    # Faint red micro-shake duration
SLIDE_DELAY_MS  = 40    # Intermediate frame for shoved entity slide
DETONATION_MS   = 40    # Mortar impact detonation flash duration
CROSS_EXPAND_MS = 40    # Mortar cross expansion duration

# -------------------------------------------------------------
# Input Pinout (Lumatrix 5-way Navigation Switch + Extra)
# Active LOW (Internal PULL_UP required)
# -------------------------------------------------------------
PIN_BTN_RIGHT  = 2
PIN_BTN_UP     = 3
PIN_BTN_DOWN   = 6
PIN_BTN_LEFT   = 7
PIN_BTN_CENTER = 8    # Push / Pass / Wait (Short) | Reset (Hold)
PIN_BTN_SWITCH = 9    # Extra Switch: Undo move

# Fallback ADC Analog Thumbstick Pins
PIN_ADC_X = 26
PIN_ADC_Y = 27
PIN_ADC_BTN = 28

ADC_DEADZONE_LOW  = 18000
ADC_DEADZONE_HIGH = 47000
ADC_MIDPOINT      = 32768

# Input timing
DEBOUNCE_MS     = 180   # Discrete edge debounce interval
ACTION_HOLD_MS  = 800   # Long-press reset trigger
