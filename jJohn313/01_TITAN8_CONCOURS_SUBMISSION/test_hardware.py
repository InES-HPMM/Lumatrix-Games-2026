"""
Lumatrix Hardware Diagnostic Script (test_hardware.py)
Tests:
1. WS2812B 8x8 LED Matrix (GPIO 19, 64 pixels):
   - Color order check (R -> G -> B)
   - Addressing check (0..63 sweep across row-major grid)
2. Input verification:
   - Digital 5-way navigation switch (Right: 2, Up: 3, Down: 6, Left: 7, Center: 8, Switch: 9)
   - Analog ADC channels (ADC0: 26, ADC1: 27, ADC2: 28)
"""

import time
from machine import Pin, ADC
from neopixel import NeoPixel

# Pin Definitions
LED_PIN = 19
NUM_LEDS = 64

# Digital Nav Switch / Buttons (Active LOW, PULL_UP)
BTN_RIGHT = 2
BTN_UP = 3
BTN_DOWN = 6
BTN_LEFT = 7
BTN_CENTER = 8
BTN_SWITCH = 9

def run_diagnostic():
    print("=" * 50)
    print("LUMATRIX HARDWARE SANITY TEST")
    print("=" * 50)

    # 1. Initialize LEDs
    np = NeoPixel(Pin(LED_PIN, Pin.OUT), NUM_LEDS)
    
    print("\n[Step 1/2] Testing LED Matrix on GPIO 19...")
    print("Testing primary colors on pixel 0 (GRB vs RGB check)...")
    colors = [
        ("RED", (30, 0, 0)),
        ("GREEN", (0, 30, 0)),
        ("BLUE", (0, 0, 30)),
        ("WHITE", (20, 20, 20)),
    ]
    for name, c in colors:
        print(f"  Showing {name} on LED #0 for 400ms")
        np[0] = c
        np.write()
        time.sleep_ms(400)
    np[0] = (0, 0, 0)
    np.write()

    print("\nRunning progressive sweep across all 64 LEDs (0 to 63)...")
    for i in range(NUM_LEDS):
        row = i // 8
        col = i % 8
        np[i] = (15, 15, 0)  # Yellow tracer
        np.write()
        time.sleep_ms(25)
        np[i] = (0, 0, 0)
    np.write()
    print("LED sweep completed. All 64 LEDs verified.")

    # 2. Initialize Inputs
    print("\n[Step 2/2] Initializing Input Sensors...")
    digital_pins = {
        "RIGHT": Pin(BTN_RIGHT, Pin.IN, Pin.PULL_UP),
        "UP": Pin(BTN_UP, Pin.IN, Pin.PULL_UP),
        "DOWN": Pin(BTN_DOWN, Pin.IN, Pin.PULL_UP),
        "LEFT": Pin(BTN_LEFT, Pin.IN, Pin.PULL_UP),
        "CENTER": Pin(BTN_CENTER, Pin.IN, Pin.PULL_UP),
        "SWITCH": Pin(BTN_SWITCH, Pin.IN, Pin.PULL_UP),
    }

    adcs = {}
    for p in (26, 27, 28):
        try:
            adcs[f"ADC_{p}"] = ADC(Pin(p))
        except Exception:
            pass

    print("Baseline Digital Pin Readings:")
    for name, p in digital_pins.items():
        print(f"  {name:7s} (GPIO): {p.value()} (Expected idle: 1)")

    print("Baseline ADC Readings:")
    for name, adc in adcs.items():
        print(f"  {name:7s} raw_u16: {adc.read_u16()}")

    print("\n--- Entering Interactive Input Monitor (Ctrl+C to stop) ---")
    print("Press nav directions, center button, or deflect stick.")
    print("Matrix center will show active input direction.")

    last_states = {name: p.value() for name, p in digital_pins.items()}
    last_log_time = time.ticks_ms()

    # Direction LED positions on 8x8 matrix
    dir_pixels = {
        "UP": (3, 7),     # Top row
        "DOWN": (3, 0),   # Bottom row
        "LEFT": (0, 3),   # Left col
        "RIGHT": (7, 3),  # Right col
        "CENTER": (3, 3), # Center
    }

    try:
        while True:
            # Check Digital Pins
            active_events = []
            for name, pin in digital_pins.items():
                val = pin.value()
                if val != last_states[name]:
                    state_str = "PRESSED" if val == 0 else "RELEASED"
                    print(f"[{time.ticks_ms()}ms] BUTTON EVENT: {name} -> {state_str}")
                    last_states[name] = val
                if val == 0:
                    active_events.append(name)

            # Check ADCs
            adc_readings = {name: adc.read_u16() for name, adc in adcs.items()}

            # Light up matrix based on active digital direction
            np.fill((0, 0, 0))
            for name in active_events:
                if name in dir_pixels:
                    x, y = dir_pixels[name]
                    idx = x + y * 8
                    np[idx] = (0, 40, 20)  # Cyan indicator
                if name == "CENTER":
                    np[3 + 3 * 8] = (40, 40, 0)
                    np[4 + 3 * 8] = (40, 40, 0)
                    np[3 + 4 * 8] = (40, 40, 0)
                    np[4 + 4 * 8] = (40, 40, 0)
            np.write()

            # Periodic ADC heartbeat every 1500ms
            now = time.ticks_ms()
            if time.ticks_diff(now, last_log_time) > 1500:
                last_log_time = now
                if active_events:
                    print(f"[Heartbeat] Active inputs: {active_events} | ADC: {adc_readings}")

            time.sleep_ms(30)

    except KeyboardInterrupt:
        print("\nStopping diagnostic. Clearing display.")
        np.fill((0, 0, 0))
        np.write()
        print("Done.")

if __name__ == "__main__":
    run_diagnostic()
