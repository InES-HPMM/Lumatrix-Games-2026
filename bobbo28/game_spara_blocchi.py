from core import *
import gc
gc.collect()

def launch_spara_blocchi():
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
        x=3; blocks=[]; shots=[]; start=ticks_ms(); last_move=start; last_shot=start; last_step=start; last_spawn=start
        while True:
            t=ticks_ms(); a=inp()
            if a and ticks_diff(t,last_move)>120:
                if a=='left': x=max(0,x-1); last_move=t
                elif a=='right': x=min(7,x+1); last_move=t
            if ticks_diff(t,last_shot)>=520:
                shots.append([x,1]); last_shot=t
            speed=max(170,360-ticks_diff(t,start)//100)
            if ticks_diff(t,last_step)>=speed:
                last_step=t
                old_blocks=[b[:] for b in blocks]; old_shots=[s[:] for s in shots]
                for b in blocks: b[1]-=1
                for s in shots: s[1]+=1
                removed_blocks=set(); removed_shots=set()
                for si,s in enumerate(shots):
                    for bi,b in enumerate(blocks):
                        crossed=(s[0]==b[0] and (s[1]==b[1] or (si<len(old_shots) and bi<len(old_blocks) and old_shots[si][1]==old_blocks[bi][1])))
                        if crossed:
                            removed_blocks.add(bi); removed_shots.add(si); break
                blocks=[b for i,b in enumerate(blocks) if i not in removed_blocks and b[1]>=0]
                shots=[s for i,s in enumerate(shots) if i not in removed_shots and s[1]<8]
            if ticks_diff(t,last_spawn)>=max(420,850-ticks_diff(t,start)//100):
                blocks.append([random.randrange(8),7]); last_spawn=t
            if any(by==0 for bx,by in blocks): arcade_result_screen(False); break
            draw([(x,0,CYAN)]+[(bx,by,RED) for bx,by in blocks]+[(sx,sy,YELLOW) for sx,sy in shots])
            sleep_ms(25)
        clear(); show()
    except SystemExit:
        pass
    arcade_clear()
    return
