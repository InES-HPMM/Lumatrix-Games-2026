from core import *
import gc
gc.collect()

def launch_cross_road():
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

        def draw(points):
            np.fill(OFF)
            for x,y,c in points:
                if 0 <= x < 8 and 0 <= y < 8: np[x+y*8]=c
            np.write()

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
            sleep_ms(duration)

        lives = 3
        dead = False
        for level in range(1,11):
            show_level_intro(level)
            level_done = False
            while lives > 0 and not level_done:
                px,py=3,0
                if level==1: car_specs=[(2,1,500)]
                elif level==2: car_specs=[(1,1,500),(3,-1,510)]
                elif level==3: car_specs=[(2,1,300)]
                elif level==4: car_specs=[(1,1,300),(3,-1,310)]
                elif level==5: car_specs=[(1,1,290)]
                else: car_specs=[(1,1,max(160,290-(level-6)*18)),(2,-1,max(170,300-(level-6)*18))]
                cars=[]
                for row,d,interval in car_specs:
                    for i in range(2 if level>=2 else 1):
                        cars.append([random.randrange(8),row,d,interval,ticks_ms()+random.randrange(interval)])
                logs=[]
                if level>=5:
                    for row in ([5] if level==5 else [4,5]):
                        logs.append([random.randrange(8),row,1 if row%2==0 else -1,3])
                last_log=ticks_ms(); move_lock=0; hit=False
                while py<7 and not hit:
                    t=ticks_ms(); a=inp()
                    if a and ticks_diff(t,move_lock)>160:
                        if a=='left': px=max(0,px-1); move_lock=t
                        elif a=='right': px=min(7,px+1); move_lock=t
                        elif a=='up': py=min(7,py+1); move_lock=t
                        elif a=='down': py=max(0,py-1); move_lock=t
                    for c in cars:
                        if ticks_diff(t,c[4])>=0:
                            c[0]=(c[0]+c[2])%8; c[4]=t+c[3]
                    log_speed=max(190,500-(level-5)*25)
                    if level>=5 and ticks_diff(t,last_log)>=log_speed:
                        last_log=t
                        for log in logs:
                            was_riding=(py==log[1] and px in {(log[0]+i)%8 for i in range(3)})
                            log[0]=(log[0]+log[2])%8
                            if was_riding:
                                px=(px+log[2])%8
                    if any(c[1]==py and c[0]==px for c in cars):
                        hit=True
                    on_log=any(py==log[1] and any((log[0]+i)%8==px for i in range(3)) for log in logs)
                    river_rows=(5,) if level==5 else (4,5) if level>=6 else ()
                    if py in river_rows and not on_log:
                        hit=True
                    pts=[(c[0],c[1],RED) for c in cars]
                    for lx,ly,d,length in logs:
                        pts += [((lx+i)%8,ly,BROWN) for i in range(length)]
                    occupied={(xx,yy) for xx,yy,_ in pts}
                    for ry in river_rows:
                        for xx in range(8):
                            if (xx,ry) not in occupied: pts.append((xx,ry,BLUE))
                    pts.append((px,py,CYAN))
                    # Show remaining lives along the top row: one red pixel per life.
                    for i in range(lives):
                        pts.append((i,7,RED))
                    draw(pts)
                    sleep_ms(25)
                if hit:
                    lives -= 1
                    flash(RED,250)
                    wait_release()
                    if lives <= 0:
                        dead = True
                        break
                    # Briefly show the remaining lives, then retry this level.
                    draw([(i,7,YELLOW) for i in range(lives)])
                    sleep_ms(650)
                    wait_release()
                else:
                    level_done = True
            if dead:
                arcade_result_screen(False)
                break
            if lives <= 0:
                arcade_result_screen(False)
                break
            flash(GREEN,180)
        if not dead and lives > 0:
            arcade_result_screen(True)
        np.fill(OFF); np.write()
    except SystemExit:
        pass
    arcade_clear()
    return

