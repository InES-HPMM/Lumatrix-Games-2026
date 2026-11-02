from machine import Pin
from time import sleep_ms, ticks_ms, ticks_diff
import gc
gc.collect()
from core import *
def play_heist():
    from game_heist import make_heist_game
    make_heist_game()()

def play_snake():
    from game_snake import make_snake_game
    make_snake_game()()

def play_pingpong():
    from game_pingpong import make_pingpong_game
    make_pingpong_game()()

def play_hacker():
    from game_hacker import make_hacker_game
    make_hacker_game()()

def play_cerca_blocco():
    from game_cerca_blocco import launch_cerca_blocco
    launch_cerca_blocco()

def play_crea_distruggi():
    from game_crea_distruggi import launch_crea_distruggi
    launch_crea_distruggi()

def play_cross_road():
    from game_cross_road import launch_cross_road
    launch_cross_road()

def play_astronave():
    from game_astronave import launch_distruggi_astronave
    launch_distruggi_astronave()

def play_donkey_kong():
    from game_donkey_kong import launch_donkey_kong
    launch_donkey_kong()

def play_simon_says():
    from game_simon_says import launch_simon_says
    launch_simon_says()

def play_cattura_blocchi():
    from game_cattura_blocchi import launch_cattura_blocchi
    launch_cattura_blocchi()

def play_dino_run():
    from game_dino_run import launch_dino_run
    launch_dino_run()

def play_bombe():
    from game_bombe import launch_distruggi_bombe
    launch_distruggi_bombe()

def play_travi():
    from game_travi import launch_evita_travi
    launch_evita_travi()

def play_guitar_hero():
    from game_guitar_hero import launch_guitar_hero
    launch_guitar_hero()

def play_schiva_palazzi():
    from game_schiva_palazzi import launch_schiva_palazzi
    launch_schiva_palazzi()

def play_spara_blocchi():
    from game_spara_blocchi import launch_spara_blocchi
    launch_spara_blocchi()

def play_pallina():
    from game_pallina import launch_pallina_rimbalzante
    launch_pallina_rimbalzante()

def play_stack_blocks():
    from game_stack_blocks import launch_stack_blocks
    launch_stack_blocks()

_ADDED_GAME_COLORS = [
    (255,80,0),(0,150,255),(255,0,90),(180,255,0),(255,120,0),
    (0,255,130),(255,0,180),(100,80,255),(255,210,0),(0,190,190),
    (255,50,50),(130,255,30),(200,100,255),(255,150,40),(80,220,255)
]
GAME_NAMES = ["HEIST", "SNAKE", "PING PONG", "CYBER VIRUS",
              "CERCA IL BLOCCO", "CREA O DISTRUGGI", "CROSS THE ROAD",
              "DISTRUGGI ASTRONAVE", "DONKEY KONG", "SIMON SAYS",
              "CATTURA BLOCCHI", "DINO RUN", "DISTRUGGI LE BOMBE",
              "EVITA LE TRAVI", "GUITAR HERO", "SCHIVA I PALAZZI",
              "SPARA AI BLOCCHI", "PALLINA RIMBALZANTE", "STACK THE BLOCKS"]
SPRITE_COLORS = [HEIST, SNAKE, SPACE, HACKER] + _ADDED_GAME_COLORS
ADDED_SPRITES = {
    4: (['...A....', '..ABA...', '..BBB...', '..BBB...', '...C....', '...D....', 'D.DDD.D.', '........'], {'A': (255, 165, 0), 'B': (255, 255, 0), 'C': (255, 255, 255), 'D': (0, 255, 255)}),
    5: (['..A..A..', '.ABAABA.', '..A..A..', 'ABBBBBBA', 'ABBBBBBA', '..A..A..', '.ABAABA.', '..A..A..'], {'A': (103, 101, 101), 'B': (255, 165, 0)}),
    6: (['AAAAAAAA', 'AA.BB.AA', 'AAAAAAAA', '..C..C..', '..CCCC..', '..CDDC..', '.C.CC.C.', 'EEEEEEEE'], {'A': (0, 255, 255), 'B': (255, 165, 0), 'C': (0, 255, 0), 'D': (255, 255, 255), 'E': (103, 101, 101)}),
    7: (['..A..A..', '...AA...', '..AAAA..', '.AABBAA.', 'AAAAAAAA', '.A.AA.A.', 'A......A', '...B....'], {'A': (0, 255, 0), 'B': (255, 255, 255)}),
    8: (['A..A...A', 'A.BBBB.A', 'A......A', 'ABABBBAA', 'A....C.A', 'ABBBBBBA', 'A.C....A', 'ADBBBBBA'], {'A': (255, 165, 0), 'B': (0, 255, 255), 'C': (0, 255, 0), 'D': (255, 0, 0)}),
    9: (['.AAAAAA.', 'B.AAAA.C', 'BB.AA.CC', 'BBB..CCC', 'BBB..CCC', 'BB.DD.CC', 'B.DDDD.C', '.DDDDDD.'], {'A': (255, 0, 0), 'B': (0, 255, 255), 'C': (0, 255, 0), 'D': (255, 255, 0)}),
    10: (['.....A..', '..A.....', '.A.A....', '..A.....', '........', '........', '.B....B.', '.BBBBBB.'], {'A': (0, 255, 255), 'B': (255, 255, 0)}),
    11: (['....AAA.', '...A.AAA', '...AAA..', 'A..AAAA.', 'AAAAAA..', '.AAAAA..', '..AAAA..', '..A..A..'], {'A': (255, 255, 255)}),
    12: (['.....A..', '....B...', '....C...', '...CCC..', '..CCCCC.', '..C.C.C.', '..CCCCC.', '...CCC..'], {'A': (255, 0, 0), 'B': (255, 255, 0), 'C': (103, 101, 101)}),
    13: (['AA.AAAAA', '........', 'AAAAA.AA', '........', 'AAA.AAAA', '........', '...B....', '...B....'], {'A': (255, 0, 255), 'B': (255, 255, 255)}),
    14: (['...A....', '...A....', '...A....', '..AA....', '.AAAA...', '.AAAA...', '.AAAA...', '..AABCDE'], {'A': (255, 0, 255), 'B': (255, 0, 0), 'C': (255, 255, 0), 'D': (0, 255, 0), 'E': (0, 255, 255)}),
    15: (['A......A', 'A.B..B.A', 'A......A', 'A.BCCB.A', 'A..DD..A', 'A.DDDD.A', 'A..DD..A', 'A.B..B.A'], {'A': (0, 255, 255), 'B': (103, 101, 101), 'C': (255, 255, 255), 'D': (255, 0, 255)}),
    16: (['...A....', '.A......', '....A...', '..B.....', '.BBB....', '.BBB....', '..B.....', '........'], {'A': (255, 165, 0), 'B': (0, 255, 255)}),
    17: (['AAAAAAAA', 'BBBBBBBB', 'CCCCCCCC', 'DDDDDDDD', '........', '.....E..', '........', '..EEE...'], {'A': (255, 0, 0), 'B': (255, 165, 0), 'C': (255, 255, 0), 'D': (0, 255, 0), 'E': (255, 255, 255)}),
    18: (['..AA....', '........', '........', '....BB..', '...CCC..', '..DDDD..', '..EEEE..', 'FFFFFFFF'], {'A': (0, 255, 255), 'B': (0, 255, 0), 'C': (255, 255, 0), 'D': (255, 165, 0), 'E': (255, 0, 0), 'F': (103, 101, 101)}),
}
def draw_arcade_menu(selected, hint_on=True):
    arcade_clear()
    if selected < 4:
        sprite = SPRITES[selected]
        palette = SPRITE_PALETTE
        for y in range(8):
            for x in range(8):
                pixel = sprite[y][x]
                if pixel != ".": arcade_set(x, 7-y, palette.get(pixel, SPRITE_COLORS[selected]))
    else:
        rows, palette = ADDED_SPRITES[selected]
        for y in range(8):
            for x in range(8):
                pixel = rows[y][x]
                if pixel != ".": arcade_set(x, 7-y, palette[pixel])
    for bit in range(4):
        if selected & (1 << bit): arcade_set(bit+2, 0, WHITE)
    if hint_on:
        arcade_set(0, 0, WHITE); arcade_set(7, 0, WHITE)
    arcade_show()
def arcade_menu():
    selected = 0
    last_input = ticks_ms()
    pulse_time = ticks_ms()
    hint_on = True
    draw_arcade_menu(selected, hint_on)
    while True:
        now = ticks_ms()
        if ticks_diff(now, pulse_time) >= 400:
            hint_on = not hint_on
            pulse_time = now
            draw_arcade_menu(selected, hint_on)
        if ticks_diff(now, last_input) >= 130:
            inp = arcade_read()
            if inp in ("left", "right"):
                selected = (selected + (1 if inp == "right" else -1)) % len(GAME_NAMES)
                last_input = now
                arcade_release()
                draw_arcade_menu(selected, True)
            elif inp == "center":
                arcade_release(); sleep_ms(120)
                return selected
        sleep_ms(10)

GAMES = [play_snake,play_heist, play_pingpong, play_hacker,
         play_cerca_blocco, play_crea_distruggi, play_cross_road,
         play_astronave, play_donkey_kong, play_simon_says,
         play_cattura_blocchi, play_dino_run, play_bombe,
         play_travi, play_guitar_hero, play_schiva_palazzi,
         play_spara_blocchi, play_pallina, play_stack_blocks]

def main():
    arcade_boot()
    while True:
        selected = arcade_menu()
        np.fill(SPRITE_COLORS[selected])
        np.write()
        sleep_ms(70)
        arcade_clear()
        GAMES[selected]()
        gc.collect()
        arcade_clear()
        sleep_ms(200)

main()
 