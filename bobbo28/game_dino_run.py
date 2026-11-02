from core import *
import gc
gc.collect()

def launch_dino_run():
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
        def clamp(v,a,b): return max(a,min(b,v))
        def wait_release():
            while any(p.value()==0 for p in (LEFT,RIGHT,UP,DOWN,S1)): sleep_ms(15)
        def flash(c,duration=350):
            draw([(x,y,c) for y in range(8) for x in range(8)])
            sleep_ms(duration)
        dino_x=1; jump=0; obstacle_x=7; obstacle_shape=(1,1); last=ticks_ms(); speed=390
        while True:
            t=ticks_ms(); a=inp()
            if a=='s1' and jump==0: jump=8; wait_release()
            if ticks_diff(t,last)>=speed:
                last=t
                obstacle_x-=1
                if obstacle_x < -1:
                    obstacle_shape=random.choice([(1,1),(1,2),(2,1)])
                    obstacle_x=7; speed=max(170,speed-3)
                if jump>0: jump-=1
            py=1 if jump==0 else (4 if jump>=5 else 3 if jump>=3 else 2)
            w,h=obstacle_shape
            obstacle_cells={(obstacle_x+ox,1+oy) for ox in range(w) for oy in range(h)}
            collision=any(dino_x==ox and py<=oy for ox,oy in obstacle_cells)
            if collision:
                arcade_result_screen(False); break
            pts=[(dino_x,py,GREEN)]
            pts += [(ox,oy,RED) for ox,oy in obstacle_cells]
            pts += [(0,6,WHITE),(1,6,WHITE),(5,7,WHITE),(6,7,WHITE),(7,7,WHITE)]
            pts += [(i,0,(22,22,22)) for i in range(8)]
            draw(pts); sleep_ms(25)
        np.fill(OFF); np.write()
    except SystemExit:
        pass
    arcade_clear()
    return
