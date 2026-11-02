"""
Hardware Drivers & Abstractions for Lumatrix RP2040 (hardware.py)
Supports:
- WS2812B 8x8 NeoPixel Matrix (GPIO 19)
- Lumatrix 5-way digital navigation switch (Pins 2, 3, 6, 7, 8)
- Extra digital switch on GPIO 9 (ACTION_UNDO)
- Fallback/dual ADC analog thumbstick (Pins 26, 27, 28)
"""

import time
import config

try:
    from machine import Pin, ADC
    from neopixel import NeoPixel
    ON_HARDWARE = True
except ImportError:
    ON_HARDWARE = False
    if not hasattr(time, "sleep_ms"):
        time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)

# Action Commands
CMD_NONE       = 0
CMD_UP         = 1
CMD_DOWN       = 2
CMD_LEFT       = 3
CMD_RIGHT      = 4
CMD_PASS       = 5   # Center tap: Pass / Wait
CMD_RESET_LVL  = 6   # Center hold ~1s: Restart current level
CMD_RESET_GAME = 7   # Center hold >2s OR GPIO 9 hold >1.2s: Restart from Level 1
CMD_UNDO       = 8   # GPIO 9 tap: Undo move

# Aliases
CMD_RESET  = CMD_RESET_LVL
CMD_ACTION = CMD_PASS


class Display:
    """Manages 8x8 WS2812B LED Matrix framebuffer and hardware output."""
    def __init__(self, pin=config.LED_PIN, num_leds=config.NUM_LEDS, brightness=config.DEFAULT_BRIGHTNESS):
        self.width = config.GRID_WIDTH
        self.height = config.GRID_HEIGHT
        self.num_leds = num_leds
        self.brightness = brightness
        self.buffer = [(0, 0, 0)] * num_leds

        if ON_HARDWARE:
            self._np = NeoPixel(Pin(pin, Pin.OUT), num_leds)
        else:
            self._np = None

    def set_brightness(self, brightness):
        self.brightness = max(0, min(100, brightness))

    def clear(self):
        for i in range(self.num_leds):
            self.buffer[i] = (0, 0, 0)

    def fill(self, color):
        for i in range(self.num_leds):
            self.buffer[i] = color

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            idx = x + y * self.width
            self.buffer[idx] = color

    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.buffer[x + y * self.width]
        return (0, 0, 0)

    def blend_pixel(self, x, y, color):
        """Blends incoming color with existing pixel in buffer."""
        if 0 <= x < self.width and 0 <= y < self.height:
            idx = x + y * self.width
            cur = self.buffer[idx]
            self.buffer[idx] = (
                min(255, cur[0] + color[0]),
                min(255, cur[1] + color[1]),
                min(255, cur[2] + color[2]),
            )

    def show(self):
        """Scale brightness and write to NeoPixel strip."""
        if not ON_HARDWARE or not self._np:
            return

        scale = self.brightness / 100.0
        for i in range(self.num_leds):
            r, g, b = self.buffer[i]
            scaled = (int(r * scale), int(g * scale), int(b * scale))
            self._np[i] = scaled
        self._np.write()

    def flash(self, color, duration_ms=120):
        """Flashes all LEDs briefly with a color."""
        saved_buffer = list(self.buffer)
        self.fill(color)
        self.show()
        time.sleep_ms(duration_ms)
        self.buffer = saved_buffer
        self.show()

    def flash_cells(self, coords, color, duration_ms=45):
        """Paints given coordinates with color for duration_ms, then restores them."""
        if not coords:
            return
        saved = {}
        for (x, y) in coords:
            if 0 <= x < self.width and 0 <= y < self.height:
                saved[(x, y)] = self.get_pixel(x, y)
                self.set_pixel(x, y, color)
        self.show()
        time.sleep_ms(duration_ms)
        for (x, y), c in saved.items():
            self.set_pixel(x, y, c)
        self.show()

    def screen_shockwave(self, color=None, duration_ms=25):
        """Strobes all unlit (black) LEDs to a faint shockwave color for duration_ms."""
        if color is None:
            color = config.COLOR_SHOCKWAVE
        unlit = [i for i in range(self.num_leds) if self.buffer[i] == (0, 0, 0)]
        if not unlit:
            return
        for i in unlit:
            self.buffer[i] = color
        self.show()
        time.sleep_ms(duration_ms)
        for i in unlit:
            self.buffer[i] = (0, 0, 0)
        self.show()


class InputHandler:
    """
    Unified input controller supporting:
    - 5-Way Digital Navigation Switch
    - Extra GPIO 9 Switch (Undo)
    - Center Button (Pass on short-press, Reset on hold)
    - ADC Analog Stick (with presence calibration)
    """
    def __init__(self):
        self.last_cmd = CMD_NONE
        self.last_press_time = 0
        self.center_press_start = 0
        self.center_triggered_game = False
        self.last_sw_val = None

        if ON_HARDWARE:
            # Digital pins (PULL_UP, active LOW)
            self.btn_up    = Pin(config.PIN_BTN_UP, Pin.IN, Pin.PULL_UP)
            self.btn_down  = Pin(config.PIN_BTN_DOWN, Pin.IN, Pin.PULL_UP)
            self.btn_left  = Pin(config.PIN_BTN_LEFT, Pin.IN, Pin.PULL_UP)
            self.btn_right = Pin(config.PIN_BTN_RIGHT, Pin.IN, Pin.PULL_UP)
            self.btn_ctr   = Pin(config.PIN_BTN_CENTER, Pin.IN, Pin.PULL_UP)
            self.btn_sw    = Pin(config.PIN_BTN_SWITCH, Pin.IN, Pin.PULL_UP)
            self.last_sw_val = self.btn_sw.value()

            # ADC stick auto-detection: only enable if centered around ~32k (floating pins read < 3000)
            self.has_adc = False
            try:
                self.adc_x = ADC(Pin(config.PIN_ADC_X))
                self.adc_y = ADC(Pin(config.PIN_ADC_Y))
                vx = self.adc_x.read_u16()
                vy = self.adc_y.read_u16()
                if 22000 < vx < 44000 and 22000 < vy < 44000:
                    self.has_adc = True
            except Exception:
                self.adc_x = None
                self.adc_y = None
                self.has_adc = False
        else:
            self.btn_up = self.btn_down = self.btn_left = None
            self.btn_right = self.btn_ctr = self.btn_sw = None
            self.adc_x = self.adc_y = None
            self.has_adc = False

    def poll(self):
        """
        Polls inputs and returns a single discrete command if triggered.
        Edge-triggered on initial press with a deliberate repeat delay for holds.
        """
        if not ON_HARDWARE:
            return CMD_NONE

        now = time.ticks_ms()

        # 1. Read Digital States (0 = Pressed, 1 = Idle)
        is_up    = self.btn_up.value() == 0
        is_down  = self.btn_down.value() == 0
        is_left  = self.btn_left.value() == 0
        is_right = self.btn_right.value() == 0
        is_ctr   = self.btn_ctr.value() == 0
        sw_val   = self.btn_sw.value()

        # 2. Check GPIO 9 Toggle Switch (bistable lever on the back)
        if self.last_sw_val is None:
            self.last_sw_val = sw_val
        elif sw_val != self.last_sw_val:
            self.last_sw_val = sw_val
            return CMD_UNDO

        # 3. Check ADC stick ONLY if physical hardware analog stick was verified present
        if self.has_adc and not (is_up or is_down or is_left or is_right):
            try:
                vx = self.adc_x.read_u16()
                vy = self.adc_y.read_u16()
                if vx > config.ADC_DEADZONE_HIGH:
                    is_right = True
                elif vx < config.ADC_DEADZONE_LOW:
                    is_left = True
                if vy > config.ADC_DEADZONE_HIGH:
                    is_up = True
                elif vy < config.ADC_DEADZONE_LOW:
                    is_down = True
            except Exception:
                pass

        # 4. Handle Center Button:
        # Tap (< 700ms) -> PASS / WAIT
        # Hold (700ms - 2000ms) -> RESET CURRENT LEVEL
        # Super-Hold (> 2000ms) -> RESET BACK TO LEVEL 1
        if is_ctr:
            if self.center_press_start == 0:
                self.center_press_start = now
            elif not self.center_triggered_game and time.ticks_diff(now, self.center_press_start) > 2000:
                self.center_triggered_game = True
                return CMD_RESET_GAME
        else:
            if self.center_press_start > 0:
                held_ms = time.ticks_diff(now, self.center_press_start)
                self.center_press_start = 0
                if not self.center_triggered_game:
                    if held_ms >= 700:
                        return CMD_RESET_LVL
                    elif held_ms > 30:
                        return CMD_PASS
                self.center_triggered_game = False

        # 5. Directional edge detection (Discrete single-step per tap)
        raw_cmd = CMD_NONE
        if is_up:
            raw_cmd = CMD_UP
        elif is_down:
            raw_cmd = CMD_DOWN
        elif is_left:
            raw_cmd = CMD_LEFT
        elif is_right:
            raw_cmd = CMD_RIGHT

        if raw_cmd != CMD_NONE:
            if self.last_cmd == CMD_NONE:
                # Brand new press -> trigger immediately!
                self.last_cmd = raw_cmd
                self.last_press_time = now
                return raw_cmd
            elif raw_cmd == self.last_cmd:
                # Held down -> repeat only after generous hold delay (350ms)
                if time.ticks_diff(now, self.last_press_time) > 350:
                    self.last_press_time = now - 150
                    return raw_cmd
            else:
                self.last_cmd = raw_cmd
                self.last_press_time = now
                return raw_cmd
        else:
            self.last_cmd = CMD_NONE

        return CMD_NONE
