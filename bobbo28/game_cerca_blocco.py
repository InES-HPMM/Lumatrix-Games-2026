from core import *
import gc
gc.collect()

def launch_cerca_blocco():
    try:
        from machine import Pin
        from neopixel import NeoPixel
        import random
        from time import sleep_ms, ticks_ms, ticks_diff
        np = NeoPixel(Pin(19, Pin.OUT), 64)
        LEFT, RIGHT, UP, DOWN, S1 = [Pin(p, Pin.IN, Pin.PULL_UP) for p in (7, 2, 3, 6, 8)]
        OFF=(0,0,0); WHITE=(45,45,45); RED=(180,0,0); GREEN=(0,180,0)
        BLUE=(0,0,180); YELLOW=(180,120,0); CYAN=(0,150,150); PURPLE=(100,0,150)
        ORANGE=(180,45,0); COLORS=[RED,GREEN,BLUE,YELLOW,PURPLE,CYAN]
        def put(x,y,c):
            if 0 <= x < 8 and 0 <= y < 8: np[x+y*8]=c
        def clear():
            np.fill(OFF)
        def show():
            np.write()
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
        def clamp(v,a,b):
            return max(a,min(b,v))
        def wait_release():
            while any(p.value()==0 for p in (LEFT,RIGHT,UP,DOWN,S1)): sleep_ms(15)
        def flash(c, duration=350):
            draw([(x,y,c) for y in range(8) for x in range(8)])
            sleep_ms(duration)
            clear(); show()
        def make_maze():
            target=(random.randrange(8),random.randrange(8))
            path={(0,0)}; x=y=0
            while (x,y)!=target:
                opts=[]
                if x<target[0]: opts.append((x+1,y))
                if x>target[0]: opts.append((x-1,y))
                if y<target[1]: opts.append((x,y+1))
                if y>target[1]: opts.append((x,y-1))
                x,y=random.choice(opts); path.add((x,y))
            walls=set()
            for yy in range(8):
                for xx in range(8):
                    if (xx,yy) not in path and (xx,yy)!=(0,0) and (xx,yy)!=target and random.random()<0.34:
                        walls.add((xx,yy))
            return target,walls
        for level in range(1,11):
            show_level_intro(level)
            player=(0,0); target,walls=make_maze()
            while player!=target:
                pts=[]
                px,py=player
                for yy in range(8):
                    for xx in range(8):
                        if abs(xx-px)+abs(yy-py)<=2:
                            if (xx,yy) in walls: pts.append((xx,yy,BLUE))
                            elif (xx,yy)==target: pts.append((xx,yy,YELLOW))
                pts.append((px,py,CYAN)); draw(pts)
                a=inp(); nx,ny=px,py
                if a=='left': nx=max(0,px-1)
                elif a=='right': nx=min(7,px+1)
                elif a=='up': ny=min(7,py+1)
                elif a=='down': ny=max(0,py-1)
                if (nx,ny) not in walls: player=(nx,ny)
                sleep_ms(130)
            flash(GREEN,180)
        arcade_result_screen(True)
        clear(); show()
    except SystemExit:
        pass
    arcade_clear()
    return
