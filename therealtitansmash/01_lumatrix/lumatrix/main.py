import utime
import sys
import select
from zhaw_led_matrix import LedMatrix, ColorTable, CharacterTable

matrix = LedMatrix(8, 8)
matrix.set_brightness(15)

# --- TIMING CONFIGURATION ---
SCROLL_DURATION_MS = 5000
STATIC_DURATION_MS = 4000
PAUSE_DURATION_MS = 500
SCROLL_CHAR_SPACING = 6

# --- CUSTOM FONT ENGINE (For Compact Numbers) ---
# 3x5 pixel grids so two or three digit transit lines fit on an 8x8 matrix.
RAW_DIGITS = {
    '0': ["XXX", "X X", "X X", "X X", "XXX"],
    '1': [" X ", "XX ", " X ", " X ", "XXX"],
    '2': ["XXX", "  X", "XXX", "X  ", "XXX"],
    '3': ["XXX", "  X", "XXX", "  X", "XXX"],
    '4': ["X X", "X X", "XXX", "  X", "  X"],
    '5': ["XXX", "X  ", "XXX", "  X", "XXX"],
    '6': ["XXX", "X  ", "XXX", "X X", "XXX"],
    '7': ["XXX", "  X", "  X", "  X", "  X"],
    '8': ["XXX", "X X", "XXX", "X X", "XXX"],
    '9': ["XXX", "X X", "XXX", "  X", "XXX"],
    "'": ["   ", "   ", "   ", "   ", "  X"] # Minute mark: physical top-right
}

def parse_font(raw_dict):
    """Converts the text grid into (x,y) tuple lists."""
    parsed = {}
    for char, grid in raw_dict.items():
        pixels = []
        for y, row in enumerate(grid):
            for x, val in enumerate(row):
                if val == 'X':
                    pixels.append((x, 6 - y)) # CharacterTable uses higher y values as the physical top.
        parsed[char] = pixels
    return parsed

CUSTOM_FONT = parse_font(RAW_DIGITS)
CUSTOM_FONT["'"] = [(2, 5), (2, 6)]

# --- CORE GRAPHICS ENGINE ---
def get_char_pixels(char):
    if char == ' ': return []
    # Check custom numbers first
    if char in CUSTOM_FONT:
        return CUSTOM_FONT[char]
    # Fallback to ZHAW letters
    try:
        return getattr(CharacterTable, char.upper())
    except AttributeError:
        return [] 

def generate_wide_buffer(text, char_spacing):
    wide_pixels = []
    for i, char in enumerate(text):
        char_pixels = get_char_pixels(char)
        x_offset = i * char_spacing
        for x, y in char_pixels:
            wide_pixels.append((x + x_offset, y))
    return wide_pixels, len(text) * char_spacing

def scroll_text(text, duration_ms, color):
    wide_pixels, total_width = generate_wide_buffer(text, SCROLL_CHAR_SPACING)
    start_offset = -8
    end_offset = total_width
    total_frames = end_offset - start_offset
    
    if total_frames <= 0: return
    frame_delay = max(1, duration_ms // total_frames)
    
    for offset in range(start_offset, end_offset):
        matrix.clear()
        current_frame = [(x - offset, y) for x, y in wide_pixels if 0 <= (x - offset) < 8]
        matrix.draw_list(current_frame, color)
        matrix.apply()
        utime.sleep_ms(frame_delay)

def show_static_text(text, duration_ms, color):
    matrix.clear()
    char_spacing = 3 if len(text) >= 3 else 4
    wide_pixels, _ = generate_wide_buffer(text, char_spacing=char_spacing)
    current_frame = [(x, y) for x, y in wide_pixels if 0 <= x < 8]
    matrix.draw_list(current_frame, color)
    matrix.apply()
    utime.sleep_ms(duration_ms)

def show_line_number(line_number, duration_ms):
    text = str(line_number)
    if len(text) > 2:
        scroll_text(text, duration_ms, ColorTable.WHITE)
    else:
        show_static_text(text, duration_ms, ColorTable.WHITE)

# --- SEQUENCE MANAGER ---
def run_display_cycle(station_name, line_number, minutes, color):
    # 1. Scroll station (5s)
    scroll_text(station_name, SCROLL_DURATION_MS, color)
    
    # 2. Break (0.5s)
    matrix.clear()
    matrix.apply()
    utime.sleep_ms(PAUSE_DURATION_MS)
    
    # 3. Line number (4s)
    show_line_number(line_number, STATIC_DURATION_MS)

    # 4. Break (0.5s)
    matrix.clear()
    matrix.apply()
    utime.sleep_ms(PAUSE_DURATION_MS)

    # 5. Static Minutes (4s) - Add apostrophe if single digit to fit on screen
    display_mins = str(minutes) if len(str(minutes)) >= 2 else f"{minutes}'"
    show_static_text(display_mins, STATIC_DURATION_MS, color)
        
    # 6. Break (0.5s)
    matrix.clear()
    matrix.apply()
    utime.sleep_ms(PAUSE_DURATION_MS)

# --- SERIAL LISTENER ---
poll_obj = select.poll()
poll_obj.register(sys.stdin, select.POLLIN)

def set_debug_pixel(color):
    """Overrides top-left pixel for immediate status feedback."""
    matrix.clear()
    matrix[0,0] = color
    matrix.apply()

# Boot status
set_debug_pixel(ColorTable.YELLOW) 
print("ACK:Pico Booted and Polling") # Send boot confirmation to host

while True:
    poll_results = poll_obj.poll(1) 
    if poll_results:
        # We got something in the buffer! Turn pixel GREEN.
        set_debug_pixel(ColorTable.GREEN)
        
        data = sys.stdin.readline().strip()
        
        # --- SEND HANDSHAKE BACK TO PC ---
        print(f"ACK:Received '{data}'") 
        
        if not data:
            continue
            
        try:
            station, line_number, mins = data.split(',')
            color = ColorTable.BLUE if "ZEHNTEN" in station else ColorTable.ORANGE
            
            # Start actual sequence
            run_display_cycle(station, line_number, mins, color)
            
            # Reset to waiting
            set_debug_pixel(ColorTable.YELLOW)
            
        except ValueError:
            # Payload was corrupted or missing a comma
            set_debug_pixel(ColorTable.RED)
            print(f"ERR:Failed to parse '{data}'")
            utime.sleep_ms(2000)
            set_debug_pixel(ColorTable.YELLOW)
            
    # CRITICAL: Prevent USB Lockup
    utime.sleep_ms(10)
