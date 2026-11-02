from core import *
import gc
gc.collect()

def launch_pallina_rimbalzante():
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
        bricks={(x,y):random.choice(COLORS[:4]) for y in (5,6,7) for x in range(8)}
        paddle=2; x=3; y=2; dx=1; dy=1; lives=3; speed=170; last_move=ticks_ms()
        while bricks and lives>0:
            a=inp(); t=ticks_ms()
            if a=='left' and ticks_diff(t,last_move)>80: paddle=max(0,paddle-1); last_move=t
            elif a=='right' and ticks_diff(t,last_move)>80: paddle=min(5,paddle+1); last_move=t
            nx=x+dx; ny=y+dy
            if nx<0 or nx>7: dx=-dx; nx=x+dx
            if ny>7: dy=-1; ny=y+dy
            if (nx,ny) in bricks:
                del bricks[(nx,ny)]; dy=-dy; ny=y+dy
            if ny==0 and dy<0:
                if paddle<=nx<=paddle+2:
                    dy=1; ny=1
                    dx=-1 if nx<paddle+1 else 1 if nx>paddle+1 else dx
                else:
                    lives-=1; x=3; y=2; dx=random.choice([-1,1]); dy=1; sleep_ms(300); continue
            if ny<0:
                lives-=1; x=3; y=2; dx=random.choice([-1,1]); dy=1; sleep_ms(300); continue
            x,y=nx,ny
            pts=[(bx,by,c) for (bx,by),c in bricks.items()]
            pts += [(paddle+i,0,CYAN) for i in range(3)]
            pts += [(i,0,RED) for i in range(lives)]
            pts.append((x,y,WHITE)); draw(pts); sleep_ms(speed)
        arcade_result_screen(not bricks)
    except SystemExit:
        pass
    arcade_clear()
    return
