from core import *
import gc
gc.collect()

def launch_evita_travi():
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
        x=3; beams=[]; start=ticks_ms(); last_move=start; last_fall=start; last_spawn=start; last_row_tick=0
        while True:
            t=ticks_ms(); a=inp()
            if a in ('left','right') and ticks_diff(t,last_move)>190:
                if a=='left': x=max(0,x-1)
                elif a=='right': x=min(7,x+1)
                last_move=t
            speed=max(150,430-ticks_diff(t,start)//100)
            if ticks_diff(t,last_fall)>=speed:
                last_fall=t
                for b in beams: b[1]-=1
                beams=[b for b in beams if b[1]>=0]
                last_row_tick+=1
            if last_row_tick>=4:
                hole=random.randrange(8); beams.append([hole,7]); last_row_tick=0
            if any(by==0 and x!=hole for hole,by in beams):
                arcade_result_screen(False); break
            pts=[(x,0,CYAN)]
            for hole,by in beams:
                for bx in range(8):
                    if bx!=hole: pts.append((bx,by,RED))
            draw(pts); sleep_ms(20)
        clear(); show()
    except SystemExit:
        pass
    arcade_clear()
    return
