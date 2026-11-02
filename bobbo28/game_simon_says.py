from core import *
import gc
gc.collect()

def launch_simon_says():
    try:
        from machine import Pin
        from neopixel import NeoPixel
        import random
        from time import sleep_ms, ticks_ms, ticks_diff
        np = NeoPixel(Pin(19, Pin.OUT), 64)
        LEFT, RIGHT, UP, DOWN, S1 = [Pin(p, Pin.IN, Pin.PULL_UP) for p in (7, 2, 3, 6, 8)]
        OFF=(0,0,0); WHITE=(35,35,35); RED=(180,0,0); GREEN=(0,180,0)
        BLUE=(0,0,180); YELLOW=(180,120,0); CYAN=(0,150,150); PURPLE=(100,0,150)
        ORANGE=(180,45,0); BROWN=(90,35,5); PINK=(180,0,80)
        COLORS=[RED,GREEN,BLUE,YELLOW,PURPLE,CYAN,ORANGE,PINK]
        def put(x,y,c):
            if 0 <= x < 8 and 0 <= y < 8: np[x+y*8]=c
        def clear(): np.fill(OFF)
        def show(): np.write()
        def draw(points):
            clear()
            for x,y,c in points: put(x,y,c)
            show()
        def inp():
            if UP.value()==0: return 'up'
            if DOWN.value()==0: return 'down'
            if LEFT.value()==0: return 'left'
            if RIGHT.value()==0: return 'right'
            if S1.value()==0: return 's1'
            return None
        def clamp(v,a,b): return max(a,min(b,v))
        def wait_release():
            while any(p.value()==0 for p in (LEFT,RIGHT,UP,DOWN,S1)): sleep_ms(15)
        def flash(c,duration=350):
            draw([(x,y,c) for y in range(8) for x in range(8)])
            sleep_ms(duration); clear(); show()
        zones={
         'up':[(x,y,RED) for y in (4,5,6,7) for x in (2,3,4,5)],
         'left':[(x,y,BLUE) for y in (2,3,4,5) for x in (0,1,2,3)],
         'right':[(x,y,GREEN) for y in (2,3,4,5) for x in (4,5,6,7)],
         'down':[(x,y,YELLOW) for y in (0,1,2,3) for x in (2,3,4,5)]
        }
        directions=['up','left','right','down']; seq=[]
        def show_board(active=None):
            if active: draw(zones[active])
            else:
                pts=[]
                pts += [(x,y,RED) for y in (5,6,7) for x in (3,4)]
                pts += [(x,y,BLUE) for y in (3,4) for x in (0,1,2)]
                pts += [(x,y,GREEN) for y in (3,4) for x in (5,6,7)]
                pts += [(x,y,YELLOW) for y in (0,1,2) for x in (3,4)]
                draw(pts)
        for level in range(1,11):
            show_level_intro(level)
            seq.append(random.choice(directions))
            for d in seq:
                show_board(); sleep_ms(250)
                show_board(d); sleep_ms(900)
                show_board(); sleep_ms(350)
            for expected in seq:
                while True:
                    a=inp()
                    if a:
                        wait_release()
                        if a in directions: break
                    sleep_ms(10)
                if a!=expected:
                    arcade_result_screen(False); raise SystemExit
                show_board(a); sleep_ms(400); show_board(); sleep_ms(300)
        arcade_result_screen(True)
    except SystemExit:
        pass
    arcade_clear()
    return
