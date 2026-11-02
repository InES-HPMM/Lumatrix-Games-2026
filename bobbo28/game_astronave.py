from core import *
import gc
gc.collect()

def launch_distruggi_astronave():
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
        player=3
        for level in range(1,11):
            show_level_intro(level)
            shipx=1; shipy=7; direction=1; shots=[]; ship={(x,y) for x in range(5) for y in range(3)}
            move_ms=max(220,1200-level*70); last_move=ticks_ms(); last_shot=0; last_input=0; last_bullet=ticks_ms()
            while ship and shipy>=1:
                t=ticks_ms(); a=inp()
                if a and ticks_diff(t,last_input)>130:
                    if a=='left': player=clamp(player-1,0,7); last_input=t
                    elif a=='right': player=clamp(player+1,0,7); last_input=t
                    elif a=='s1' and ticks_diff(t,last_shot)>260: shots.append([player,1]); last_shot=t
                if ticks_diff(t,last_move)>=move_ms:
                    last_move=t; shipx+=direction
                    if shipx<0 or shipx+4>7:
                        direction=-direction; shipx+=2*direction; shipy-=1
                if ticks_diff(t,last_bullet)>=70:
                    last_bullet=t; moved=[]
                    for sx,sy in shots:
                        sy+=1; hit=(sx-shipx,sy-shipy)
                        if hit in ship: ship.remove(hit)
                        elif sy<8: moved.append([sx,sy])
                    shots=moved
                pts=[(player,0,CYAN)]
                pts += [(shipx+sx,shipy+sy,GREEN if (sx+sy)%2==0 else PINK) for sx,sy in ship]
                pts += [(sx,sy,YELLOW) for sx,sy in shots]
                draw(pts); sleep_ms(20)
            if ship: arcade_result_screen(False); break
            flash(GREEN,160)
        if not ship: arcade_result_screen(True)
        clear(); show()
    except SystemExit:
        pass
    arcade_clear()
    return
