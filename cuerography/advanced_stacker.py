import time
from zhaw_led_matrix import LedMatrix, ColorTable, Button

# Hardware-Setup
matrix = LedMatrix(8, 8)
btn = Button()

# Anzeige war auf Kopf. Drehe ich hier
def draw_pixel(x, y, color):
    matrix[7 - x, 7 - y] = color

def choose_difficulty():
    selected = 0
    confirmed = False
    last_press = time.ticks_ms()
    
    def on_nav(pin):
        nonlocal selected, last_press
        if time.ticks_ms() - last_press > 200:
            selected = (selected + 1) % 3
            last_press = time.ticks_ms()
            
    def on_confirm(pin):
        nonlocal confirmed, last_press
        if time.ticks_ms() - last_press > 200:
            confirmed = True
            last_press = time.ticks_ms()

    btn.set_left_handler(on_nav)
    btn.set_right_handler(on_nav)
    btn.set_center_handler(on_confirm)
    btn.set_down_handler(on_confirm)
    btn.set_up_handler(on_confirm)
    
    matrix.set_brightness(30)
    
    while not confirmed:
        matrix.clear()
        
        blink = (time.ticks_ms() // 200) % 2 == 0
        
        heights = [2, 4, 6]
        colors = [ColorTable.GREEN, ColorTable.YELLOW, ColorTable.RED]
        
        for i in range(3):
            x = i * 3
            if i == selected and not blink:
                continue
                
            for y in range(8 - heights[i], 8):
                draw_pixel(x, y, colors[i])
                if x + 1 < 8:
                    draw_pixel(x + 1, y, colors[i])
                
        matrix.apply()
        time.sleep(0.05)
        
    btn.set_left_handler(lambda p: None)
    btn.set_right_handler(lambda p: None)
    
    matrix.clear()
    matrix.apply()
    time.sleep(0.3)
    return selected

def play_stacker(difficulty):
    matrix.set_brightness(30)
    
    tower = [[] for _ in range(8)]
    current_y = 7
    block_width = 3
    current_x = 0
    direction = 1
    speed = 0.2
    
    button_pressed = False
    last_press_time = time.ticks_ms()
    
    def on_press(pin):
        nonlocal button_pressed, last_press_time
        if time.ticks_ms() - last_press_time > 200:
            button_pressed = True
            last_press_time = time.ticks_ms()
            
    btn.set_center_handler(on_press)
    btn.set_down_handler(on_press)
    btn.set_up_handler(on_press)
    matrix.clear()
    
    while True:
        current_x += direction
        max_x = 8 - block_width
        
        if current_x >= max_x:
            current_x = max_x
            direction = -1
        elif current_x <= 0:
            current_x = 0
            direction = 1
            
        matrix.clear()
        
        for y in range(8):
            for x in tower[y]:
                draw_pixel(x, y, ColorTable.BLUE)
                
        is_visible = True
        if difficulty == 2: 
            is_visible = (time.ticks_ms() // 150) % 2 == 0
            
        if is_visible:
            for x in range(current_x, current_x + block_width):
                draw_pixel(x, current_y, ColorTable.RED)
                
        matrix.apply()
        
        if button_pressed:
            button_pressed = False
            
            current_pixels = set(range(current_x, current_x + block_width))
            
            if current_y < 7:
                prev_pixels = set(tower[current_y + 1])
                kept_pixels = current_pixels.intersection(prev_pixels)
                dropped_pixels = current_pixels - prev_pixels
            else:
                kept_pixels = current_pixels
                dropped_pixels = set()
                
            tower[current_y] = list(kept_pixels)
            block_width = len(kept_pixels)
            
            if dropped_pixels:
                for drop_y in range(current_y + 1, 9):
                    matrix.clear()
                    for y in range(8):
                        for x in tower[y]:
                            draw_pixel(x, y, ColorTable.BLUE)
                    for x in dropped_pixels:
                        if drop_y < 8: 
                            draw_pixel(x, drop_y, ColorTable.RED)
                    matrix.apply()
                    time.sleep(0.12) 
                    
            button_pressed = False 
            last_press_time = time.ticks_ms()
            
            if block_width == 0:
                print("Game Over!")
                for _ in range(2):
                    matrix.fill(ColorTable.RED)
                    matrix.apply()
                    time.sleep(0.2)
                    matrix.clear()
                    matrix.apply()
                    time.sleep(0.2)
                return 
                
            else:
                current_y -= 1
                speed *= 0.85 
                
                if difficulty == 1:
                    if current_y in [4, 3, 2] and block_width > 2:
                        block_width = 2
                    elif current_y in [1, 0] and block_width > 1:
                        block_width = 1
                
                if current_y < 0:
                    print("Gewonnen!")
                    for _ in range(3):
                        matrix.fill(ColorTable.GREEN)
                        matrix.apply()
                        time.sleep(0.2)
                        matrix.clear()
                        matrix.apply()
                        time.sleep(0.2)
                    return 
                    
        time.sleep(speed)

print("Programm gestartet.")
while True:
    print("Menü: Wähle eine Schwierigkeit (Links/Rechts) und bestätige (Mitte/Unten).")
    gewaehlte_stufe = choose_difficulty()
    print(f"Starte Stacker auf Stufe {gewaehlte_stufe + 1}...")
    play_stacker(gewaehlte_stufe)
    time.sleep(1)