from core import *
import gc
gc.collect()

def launch_stack_blocks():
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
        tower={(x,0):COLORS[i%len(COLORS)] for i,x in enumerate(range(2,6))}
        moving=[(x,7) for x in range(2,6)]
        direction=1; last=ticks_ms(); last_move=0; stack_count=0
        while True:
            t=ticks_ms(); a=inp()
            if a and ticks_diff(t,last_move)>max(65,115-stack_count*4):
                if a=='left': moving=[(max(0,x-1),y) for x,y in moving]; last_move=t
                elif a=='right': moving=[(min(7,x+1),y) for x,y in moving]; last_move=t
                elif a=='s1':
                    top=max(y for (x,y) in tower)
                    support={x for (x,y) in tower if y==top}
                    moving_x={x for x,y in moving}
                    overlap=sorted(support & moving_x)
                    if not overlap:
                        arcade_result_screen(False); break
                    color=COLORS[stack_count%len(COLORS)]
                    for xx in overlap: tower[(xx,top+1)]=color
                    stack_count+=1
                    moving=[(xx,7) for xx in overlap]
                    if top+1>=7:
                        arcade_result_screen(True); break
                    direction=-direction; last_move=t; wait_release()
            interval=max(45,300-stack_count*28)
            if ticks_diff(t,last)>=interval:
                last=t
                moving=[(x+direction,y) for x,y in moving]
                if min(x for x,y in moving)<=0 or max(x for x,y in moving)>=7:
                    direction*=-1; moving=[(clamp(x,0,7),y) for x,y in moving]
            pts=[(x,y,c) for (x,y),c in tower.items()]
            color=COLORS[stack_count%len(COLORS)]
            pts += [(x,y,color) for x,y in moving]
            draw(pts); sleep_ms(15)
        clear(); show()
    except SystemExit:
        pass
    arcade_clear()
    return
