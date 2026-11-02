from core import *
import gc
gc.collect()

def launch_cattura_blocchi():
    try:
        from machine import Pin
        from neopixel import NeoPixel
        import random
        from time import sleep_ms, ticks_ms, ticks_diff
        np = NeoPixel(Pin(19, Pin.OUT), 64)
        LEFT, RIGHT, UP, DOWN, S1 = [Pin(p, Pin.IN, Pin.PULL_UP) for p in (7, 2, 3, 6, 8)]
        OFF=(0,0,0); WHITE=(35,35,35); RED=(180,0,0); GREEN=(0,180,0)
        BLUE=(0,0,180); YELLOW=(180,120,0); CYAN=(0,150,150); PURPLE=(100,0,150)
        ORANGE=(180,45,0); BROWN=(90,35,5); COLORS=[RED,GREEN,BLUE,YELLOW,PURPLE,CYAN]
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
        paddle=2; blocks=[]; missed=0; caught=0; last_move=ticks_ms(); last_step=ticks_ms(); last_spawn=ticks_ms()
        while missed<3:
            t=ticks_ms(); a=inp()
            if a and ticks_diff(t,last_move)>120:
                if a=='left': paddle=max(0,paddle-1); last_move=t
                elif a=='right': paddle=min(5,paddle+1); last_move=t
            fall=max(220,520-caught*5)
            if ticks_diff(t,last_step)>=fall:
                last_step=t
                next_blocks=[]
                for bx,by in blocks:
                    by-=1
                    if by<=0:
                        if paddle<=bx<=paddle+2: caught+=1
                        else: missed+=1
                    else: next_blocks.append([bx,by])
                blocks=next_blocks
            if ticks_diff(t,last_spawn)>=max(450,1000-caught*5):
                blocks.append([random.randrange(8),7]); last_spawn=t
            pts=[(paddle+i,0,CYAN) for i in range(3)]
            pts += [(bx,by,random.choice(COLORS[:4])) for bx,by in blocks]
            pts += [(i,7,RED) for i in range(missed)]
            draw(pts); sleep_ms(25)
        arcade_result_screen(False)
    except SystemExit:
        pass
    arcade_clear()
    return
