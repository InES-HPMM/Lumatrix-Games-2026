from core import *
import gc
gc.collect()

def launch_guitar_hero():
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
        lanes=[0,2,5,7]; colors=[RED,GREEN,BLUE,YELLOW]
        notes=[]; start=ticks_ms(); last_step=start; last_spawn=start; last_move=0; lives=3
        while lives>0:
            t=ticks_ms()
            elapsed=ticks_diff(t,start)
            speed=max(120,340-elapsed//9000*20)
            spawn=max(240,speed*3)
            if ticks_diff(t,last_spawn)>=spawn:
                if not notes or max(n[1] for n in notes)<=4:
                    notes.append([random.randrange(4),7])
                    last_spawn=t
            a=inp()
            if a and ticks_diff(t,last_move)>120:
                lane={'left':0,'down':1,'up':2,'right':3}.get(a)
                if lane is not None:
                    hit=next((n for n in notes if n[0]==lane and n[1]<=1),None)
                    if hit: notes.remove(hit)
                last_move=t
            if ticks_diff(t,last_step)>=speed:
                last_step=t
                for n in notes: n[1]-=1
                keep=[]
                for n in notes:
                    if n[1]<0: lives-=1
                    else: keep.append(n)
                notes=keep
            pts=[(lanes[i],0,colors[i]) for i in range(4)]
            pts += [(lanes[l],y,colors[l]) for l,y in notes]
            pts += [(7-i,7,RED) for i in range(lives)]
            draw(pts); sleep_ms(20)
        arcade_result_screen(False)
    except SystemExit:
        pass
    arcade_clear()
    return
