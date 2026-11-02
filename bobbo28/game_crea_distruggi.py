from core import *
import gc
gc.collect()

def launch_crea_distruggi():
    try:
        from machine import Pin
        from neopixel import NeoPixel
        import random
        from time import sleep_ms, ticks_ms, ticks_diff
        np = NeoPixel(Pin(19, Pin.OUT), 64)
        LEFT, RIGHT, UP, DOWN, S1 = [Pin(p, Pin.IN, Pin.PULL_UP) for p in (7, 2, 3, 6, 8)]
        OFF=(0,0,0); RED=(180,0,0); GREEN=(0,180,0)
        YELLOW=(180,120,0); CYAN=(0,150,150); PURPLE=(100,0,150)
        def put(x,y,c):
            if 0 <= x < 8 and 0 <= y < 8: np[x+y*8]=c
        def draw(points):
            np.fill(OFF)
            for x,y,c in points:
                if 0 <= x < 8 and 0 <= y < 8: np[x+y*8]=c
            np.write()
        def inp():
            if UP.value()==0: return 'up'
            if DOWN.value()==0: return 'down'
            if LEFT.value()==0: return 'left'
            if RIGHT.value()==0: return 'right'
            if S1.value()==0: return 's1'
            return None
        def wait_release():
            while any(p.value()==0 for p in (LEFT,RIGHT,UP,DOWN,S1)): sleep_ms(15)
        def flash(c,duration=300):
            draw([(x,y,c) for y in range(8) for x in range(8)])
            sleep_ms(duration)
        def cross_at(x,y):
            return {(x,y),(x-1,y),(x+1,y),(x,y-1),(x,y+1)}
        def toggle_cross(board,x,y):
            for cell in cross_at(x,y):
                if 0 <= cell[0] < 8 and 0 <= cell[1] < 8:
                    if cell in board: board.remove(cell)
                    else: board.add(cell)
        for level in range(1,11):
            show_level_intro(level)
            board=set()
            number_of_crosses=level+2
            for _ in range(number_of_crosses):
                cx=random.randrange(1,7)
                cy=random.randrange(1,7)
                toggle_cross(board,cx,cy)
            if not board:
                toggle_cross(board,3,3)
            x,y=3,3
            last_move=0
            previous=None
            while board:
                now=ticks_ms()
                action=inp()
                if action and action!=previous and ticks_diff(now,last_move)>=180:
                    if action=='left': x=max(0,x-1); last_move=now
                    elif action=='right': x=min(7,x+1); last_move=now
                    elif action=='up': y=min(7,y+1); last_move=now
                    elif action=='down': y=max(0,y-1); last_move=now
                    elif action=='s1':
                        toggle_cross(board,x,y)
                        last_move=now
                        wait_release()
                previous=action
                draw([(bx,by,YELLOW) for bx,by in board]+[(x,y,CYAN)])
                sleep_ms(25)
            flash(GREEN,180)
        arcade_result_screen(True)
    except SystemExit:
        pass
    arcade_clear()
    return
