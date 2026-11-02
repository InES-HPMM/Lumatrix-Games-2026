from core import *
import gc
gc.collect()

def launch_distruggi_bombe():
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
        x=y=3; bombs=[]; start=ticks_ms(); last_spawn=start; last_move=start
        while True:
            t=ticks_ms(); a=inp()
            if a in ('left','right','up','down') and ticks_diff(t,last_move)>125:
                if a=='left': x=max(0,x-1)
                elif a=='right': x=min(7,x+1)
                elif a=='up': y=min(7,y+1)
                elif a=='down': y=max(0,y-1)
                last_move=t
            spawn=max(650,1800-ticks_diff(t,start)//30)
            if ticks_diff(t,last_spawn)>=spawn:
                occupied={(b[0],b[1]) for b in bombs}|{(x,y)}
                free=[(xx,yy) for yy in range(8) for xx in range(8) if (xx,yy) not in occupied]
                if free:
                    bx,by=random.choice(free); bombs.append([bx,by,t,t+6500])
                last_spawn=t
            bombs=[b for b in bombs if not (b[0]==x and b[1]==y)]
            if any(ticks_diff(t,b[3])>=0 for b in bombs): arcade_result_screen(False); break
            pts=[(x,y,CYAN)]
            for bx,by,born,deadline in bombs:
                age=ticks_diff(t,born)
                col=GREEN if age<2500 else YELLOW if age<4000 else ORANGE if age<5300 else RED
                pts.append((bx,by,col))
            draw(pts); sleep_ms(25)
        clear(); show()
    except SystemExit:
        pass
    arcade_clear()
    return
