from core import *
import gc
gc.collect()

def launch_schiva_palazzi():
    try:
        from machine import Pin
        from neopixel import NeoPixel
        import random
        from time import sleep_ms, ticks_ms, ticks_diff
        np = NeoPixel(Pin(19, Pin.OUT), 64)
        LEFT, RIGHT, UP, DOWN, S1 = [Pin(p, Pin.IN, Pin.PULL_UP) for p in (7, 2, 3, 6, 8)]
        OFF=(0,0,0); WHITE=(50,50,50); RED=(255,0,0); GREEN=(0,255,0)
        BLUE=(0,0,255); YELLOW=(255,180,0); CYAN=(0,255,255); PURPLE=(180,0,255)
        ORANGE=(255,70,0); COLORS=[RED,GREEN,BLUE,YELLOW,PURPLE,CYAN]
        def put(x,y,c):
            if 0<=x<8 and 0<=y<8: np[x+y*8]=c
        def clear(): np.fill(OFF)
        def show(): np.write()
        def draw(points):
            clear()
            for x,y,c in points: put(x,y,c)
            show()
        def inp():
            if UP.value()==0:return 'up'
            if DOWN.value()==0:return 'down'
            if LEFT.value()==0:return 'left'
            if RIGHT.value()==0:return 'right'
            if S1.value()==0:return 's1'
            return None
        def wait_release():
            while any(p.value()==0 for p in (LEFT,RIGHT,UP,DOWN,S1)): sleep_ms(15)
        def wait_s1():
            wait_release()
            while S1.value()!=0: sleep_ms(10)
            sleep_ms(100); wait_release()
        def clamp(v,a,b): return max(a,min(b,v))
        def rand_free(used):
            free=[(x,y) for y in range(8) for x in range(8) if (x,y) not in used]
            return random.choice(free) if free else None
        player=3; row=[]; start=ticks_ms(); last_spawn=start; last_step=start; score=0; speed=420; spawn=1000
        while True:
            a=inp()
            if a=='left': player=clamp(player-1,0,7)
            elif a=='right': player=clamp(player+1,0,7)
            t=ticks_ms(); speed=max(100,420-score*4); spawn=max(400,1000-score*5)
            if ticks_diff(t,last_spawn)>=spawn:
                available=[x for x in range(8) if all(abs(x-o[0])>=3 for o in row if o[1]>=6)]
                if available: row.append([random.choice(available),7])
                last_spawn=t
            if ticks_diff(t,last_step)>=speed:
                for o in row: o[1]-=1
                row=[o for o in row if o[1]>=0]; score+=1; last_step=t
            if any(oy==0 and ox==player for ox,oy in row): break
            draw([(player,0,CYAN)]+[(ox,oy,random.choice([RED,ORANGE,PURPLE])) for ox,oy in row])
            sleep_ms(speed)
        arcade_result_screen(False)
        clear(); show()
    except SystemExit:
        pass
    arcade_clear()
    return
