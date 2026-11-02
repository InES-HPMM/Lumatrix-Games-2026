
# Importierte Bibliotheken
from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms
import random

# Variablen / Objekte initialisieren
led_pin = Pin(19, Pin.OUT)
matrix = NeoPixel(led_pin, 64)

js_re = Pin(2, Pin.IN) #rechts
js_li = Pin(7, Pin.IN) #links
js_ho = Pin(3, Pin.IN) #hoch
js_ru = Pin(6, Pin.IN) #runter
js_click = Pin(8, Pin.IN) #mitte

# [0-255, 0-255, 0-255]
# [Rot, Gruen, Blau]

ROT = [50, 0, 0]
HELLROT = [50, 20, 20]

GRUEN = [0, 50, 0]
VIOLETT = [50, 0, 50]
WEISS = [50,50,50]
GELB = [50, 50, 0]
BLAU = [0, 0, 50]
SCHWARZ = [0, 0, 0]
GRAU = [10,10,8]
PINK = [155, 0, 155]
ORANGE = [127, 50, 0]

F  = [255, 100, 0]     # Katzenfell (Orange)
A  = [0, 255, 60]      # Augen (Grün)
P  = [255, 80, 130]

gegner_positionen = [7, 15, 23, 31, 39, 47, 55]

katzen_leben = 9
level_treffer = 3

def game_over():
    zeichne_schwarz()
    matrix[0] = BLAU
    matrix[7] = BLAU
    matrix[9] = BLAU
    matrix[14] = BLAU
    matrix[18] = BLAU
    matrix[19] = BLAU
    matrix[20] = BLAU
    matrix[21] = BLAU
    matrix[33] = BLAU
    matrix[34] = BLAU
    matrix[37] = BLAU
    matrix[38] = BLAU
    matrix[41] = BLAU
    matrix[42] = BLAU
    matrix[45] = BLAU
    matrix[46] = BLAU

def zeichne_schwarz():
    for x in range(0, 64):
       matrix[x] = SCHWARZ

def zeichne_start():
    matrix[0] = BLAU
    matrix[2] = BLAU   
    matrix[5] = VIOLETT

def raumschiff(pos):
    matrix[pos] = ROT
    matrix[pos + 1] = GRAU
    matrix[pos + 2] = GRAU
    matrix[pos + 9] = GRAU

def raumschiff_getroffen(pos):
    matrix[pos] = VIOLETT
    matrix[pos + 1] = VIOLETT
    matrix[pos + 2] = VIOLETT
    matrix[pos + 9] = VIOLETT

def pompi():
    zeichne_schwarz()
    matrix[10] = F
    matrix[11] = F
    matrix[12] = F
    matrix[13] = F

    matrix[17] = F
    matrix[18] = F
    matrix[19] = F
    matrix[20] = F
    matrix[21] = F
    matrix[22] = F

    matrix[24] = F
    matrix[25] = F
    matrix[26] = F
    matrix[27] = P  # Nase
    matrix[28] = P  # Nase
    matrix[29] = F
    matrix[30] = F
    matrix[31] = F

    matrix[32] = F
    matrix[33] = A  # Linkes Auge
    matrix[34] = F
    matrix[35] = F
    matrix[36] = F
    matrix[37] = F
    matrix[38] = A  # Rechtes Auge
    matrix[39] = F

    matrix[40] = F
    matrix[41] = F
    matrix[42] = F
    matrix[43] = F
    matrix[44] = F
    matrix[45] = F
    matrix[46] = F
    matrix[47] = F

    matrix[48] = F
    matrix[49] = P  # Linkes Ohr innen
    matrix[50] = F
    matrix[53] = F
    matrix[54] = P  # Rechtes Ohr innen
    matrix[55] = F

    matrix[56] = F  # Linke Ohrenspitze
    matrix[63] = F  # Rechte Ohrenspitze

def lvl_text(farbe):
    matrix[56] = farbe
    matrix[58] = farbe
    matrix[60] = farbe
    matrix[62] = farbe
    matrix[48] = farbe
    matrix[50] = farbe
    matrix[52] = farbe
    matrix[54] = farbe
    matrix[40] = farbe
    matrix[41] = farbe
    matrix[43] = farbe
    matrix[46] = farbe
    matrix[47] = farbe

def lvl_1_text():
    zeichne_schwarz()
    lvl_text(VIOLETT)
    
    matrix[28] = VIOLETT
    matrix[20] = VIOLETT
    matrix[19] = VIOLETT
    matrix[10] = VIOLETT
    matrix[12] = VIOLETT
    matrix[4] = VIOLETT

def lvl_2_text():
    zeichne_schwarz()
    lvl_text(GELB)

    matrix[28] = GELB
    matrix[27] = GELB
    matrix[21] = GELB
    matrix[18] = GELB
    matrix[12] = GELB
    matrix[5] = GELB
    matrix[4] = GELB
    matrix[3] = GELB
    matrix[2] = GELB

def lvl_3_text():
    zeichne_schwarz()
    lvl_text(BLAU)

    matrix[27] = BLAU
    matrix[28] = BLAU
    matrix[20] = BLAU
    matrix[21] = BLAU
    matrix[13] = BLAU
    matrix[10] = BLAU
    matrix[4] = BLAU
    matrix[3] = BLAU
    
def lvl_4_text():
    zeichne_schwarz()
    lvl_text(PINK)

    matrix[27] = PINK
    matrix[28] = PINK
    matrix[18] = PINK
    matrix[20] = PINK
    matrix[10] = PINK
    matrix[11] = PINK
    matrix[12] = PINK
    matrix[13] = PINK
    matrix[4] = PINK
    
def lvl_5_text():
    zeichne_schwarz()
    lvl_text(GRAU)

    matrix[26] = GRAU
    matrix[27] = GRAU
    matrix[28] = GRAU
    matrix[18] = GRAU
    matrix[19] = GRAU
    matrix[20] = GRAU
    matrix[21] = GRAU
    matrix[13] = GRAU
    matrix[5] = GRAU
    matrix[4] = GRAU
    matrix[3] = GRAU
    matrix[2] = GRAU

def lvl_6_text():
    zeichne_schwarz()
    lvl_text(ROT)

    matrix[26] = ROT
    matrix[18] = ROT
    matrix[19] = ROT
    matrix[20] = ROT
    matrix[21] = ROT
    matrix[13] = ROT
    matrix[10] = ROT
    matrix[5] = ROT
    matrix[4] = ROT
    matrix[3] = ROT
    matrix[2] = ROT

def raumschiff_loop(position):
    if js_ho.value() == 0:
        position = position + 8
        if position >= 48:
            position = 48
    if js_ru.value() == 0:
        position = position - 8
        if position <= 0:
            position = 0
    raumschiff(position)
    return position

def pinin():
    zeichne_schwarz()
    matrix[1] = GRAU
    matrix[3] = GRAU
    matrix[5] = GRAU
    matrix[8] = GRAU
    matrix[9] = GRAU
    matrix[10] = GRAU
    matrix[11] = GRAU
    matrix[12] = GRAU
    matrix[13] = GRAU
    matrix[14] = GRAU
    matrix[15] = GRAU
    matrix[17] = GRAU
    matrix[18] = VIOLETT
    matrix[19] = GRAU
    matrix[20] = GRAU
    matrix[21] = VIOLETT
    matrix[22] = GRAU
    matrix[24] = GRAU
    matrix[25] = GRAU
    matrix[26] = GRAU
    matrix[27] = GRAU
    matrix[28] = GRAU
    matrix[29] = GRAU
    matrix[30] = GRAU
    matrix[31] = GRAU
    matrix[33] = PINK
    matrix[34] = GRAU
    matrix[37] = GRAU
    matrix[38] = PINK
    matrix[41] = PINK
    matrix[42] = GRAU
    matrix[45] = GRAU
    matrix[46] = PINK
    matrix[50] = GRAU
    matrix[53] = GRAU

def laser(pos):
    matrix[pos] = GELB

def gegner(pos):
    matrix[pos] = VIOLETT

def gegner_laser(pos):
    matrix[pos] = BLAU

def zyklus(millisekunden = 100):
    matrix.write()
    sleep_ms(millisekunden)

def laser_loop(laser_ein, laser_zaehler, laser_position, raumschiff_position):
    if laser_ein:
        laser_zaehler = laser_zaehler + 1
        if laser_zaehler >= 5:
            laser_ein = False
            laser_position = 0
        else:
            laser_position = laser_position + 1
            laser(laser_position)
    else:
        if js_click.value() == 0:
            laser_ein = True
            laser_position = raumschiff_position + 3
            laser_zaehler = 0
            laser(laser_position)
    return laser_ein, laser_zaehler, laser_position

def leben_loop():
    feld = 59
    
    print(f"{katzen_leben}")
    
    if katzen_leben == 0:
        matrix[feld] = SCHWARZ
        matrix[feld + 1] = SCHWARZ
        matrix[feld + 2] = SCHWARZ
    
    if katzen_leben in range(7,10):
        if katzen_leben == 9:
            matrix[feld] = ROT
        elif katzen_leben == 8:
            matrix[feld] = ORANGE
        elif katzen_leben == 7:
            matrix[feld] = GELB
        matrix[feld + 1] = ROT
        matrix[feld + 2] = ROT
    if katzen_leben in range(4,7):
        matrix[feld] = SCHWARZ
        if katzen_leben == 6:
            matrix[feld + 1] = ROT
        elif katzen_leben == 5:
            matrix[feld + 1] = ORANGE
        elif katzen_leben == 4:
            matrix[feld + 1] = GELB
        matrix[feld + 2] = ROT
    if katzen_leben in range(1,4):
        matrix[feld] = SCHWARZ
        matrix[feld + 1] = SCHWARZ
        if katzen_leben == 3:
            matrix[feld + 2] = ROT
        elif katzen_leben == 2:
            matrix[feld + 2] = ORANGE
        elif katzen_leben == 1:
            matrix[feld + 2] = GELB
    

def gegner_laser_loop(laser_ein, laser_zaehler, laser_position, zeit_zaehler, gegner_position, warten = 15):
    if laser_ein:
        laser_zaehler = laser_zaehler + 1
        if laser_zaehler >= 7:
            laser_ein = False
            laser_position = 64
        else:
            laser_position = laser_position - 1
            gegner_laser(laser_position)
    else:   
        if zeit_zaehler > warten:
            zeit_zaehler = 0
            laser_ein = True
            laser_position = gegner_position - 1
            laser_zaehler = 0
            gegner_laser(laser_position)
        else:
            zeit_zaehler = zeit_zaehler + 1
    return laser_ein, laser_zaehler, laser_position, zeit_zaehler

def level1():
    raumschiff_position = 24
    laser_position = 64
    laser_zaehler = 0
    laser_ein = False
    gegner_pos = 47
    zufalls_position = random.choice(gegner_positionen)
    traeffer_zaehler = 0
    
    while(traeffer_zaehler < level_treffer):
        zeichne_schwarz()
        raumschiff_position = raumschiff_loop(raumschiff_position)
        
        leben_loop()
        
        laser_ein, laser_zaehler, laser_position = laser_loop(laser_ein, laser_zaehler, laser_position, raumschiff_position)
        
        if laser_position == gegner_pos:
            traeffer_zaehler = traeffer_zaehler + 1
            laser_position = laser_position + 1
            while gegner_pos == zufalls_position:
                zufalls_position = random.choice(gegner_positionen)
            gegner_pos = zufalls_position
        else:
            gegner(gegner_pos)

        zyklus()
        
def level2():
    raumschiff_position = 24
    laser_position = 0
    laser_zaehler = 0
    laser_ein = False
    gegner_pos = 47
    zufalls_position = random.choice(gegner_positionen)
    traeffer_zaehler = 0
    gegner_warten = 0
    gegner_richtung_hoch = False
    
    while(traeffer_zaehler < level_treffer):
        zeichne_schwarz()
        raumschiff_position = raumschiff_loop(raumschiff_position)
        
        leben_loop()
        
        laser_ein, laser_zaehler, laser_position = laser_loop(laser_ein, laser_zaehler, laser_position, raumschiff_position)
        
        if laser_position == gegner_pos:
            traeffer_zaehler = traeffer_zaehler + 1
            laser_position = laser_position + 1
            while gegner_pos == zufalls_position:
                zufalls_position = random.choice(gegner_positionen)
            gegner_pos = zufalls_position
        else:
            if gegner_warten < 5:
                gegner_warten = gegner_warten + 1
            if gegner_warten >= 5:
                gegner_warten = 0
                if gegner_richtung_hoch:
                    if gegner_pos + 8 > 55:
                      gegner_richtung_hoch = False
                if not gegner_richtung_hoch:
                    if gegner_pos - 8 < 7:
                      gegner_richtung_hoch = True
                if gegner_richtung_hoch:
                    gegner_pos = gegner_pos + 8
                else:
                    gegner_pos = gegner_pos - 8
                
            gegner(gegner_pos)
            
        zyklus()

def level3():
    raumschiff_position = 24
    laser_position = 0
    laser_zaehler = 0
    laser_ein = False
    
    gegner_laser_position = 64
    gegner_laser_zaehler = 0
    gegner_laser_ein = False
    zeit_zaehler = 0

    gegner_pos = 47
    zufalls_position = random.choice(gegner_positionen)
    traeffer_zaehler = 0
    gegner_warten = 0
    gegner_richtung_hoch = False
    
    while(traeffer_zaehler < level_treffer):
        zeichne_schwarz()
        raumschiff_position = raumschiff_loop(raumschiff_position)
        
        leben_loop()
        
        laser_ein, laser_zaehler, laser_position = laser_loop(laser_ein, laser_zaehler, laser_position, raumschiff_position)
        
        gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler = gegner_laser_loop(gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler, gegner_pos)
        
        if laser_position == gegner_pos:
            traeffer_zaehler = traeffer_zaehler + 1
            laser_position = laser_position + 1
            while gegner_pos == zufalls_position:
                zufalls_position = random.choice(gegner_positionen)
            gegner_pos = zufalls_position
        else:
            if gegner_warten < 5:
                gegner_warten = gegner_warten + 1
            if gegner_warten >= 5:
                gegner_warten = 0
                if gegner_richtung_hoch:
                    if gegner_pos + 8 > 55:
                      gegner_richtung_hoch = False
                if not gegner_richtung_hoch:
                    if gegner_pos - 8 < 7:
                      gegner_richtung_hoch = True
                if gegner_richtung_hoch:
                    gegner_pos = gegner_pos + 8
                else:
                    gegner_pos = gegner_pos - 8
                
            gegner(gegner_pos)
        
        if (gegner_laser_position == raumschiff_position or
           gegner_laser_position == raumschiff_position + 1 or
           gegner_laser_position == raumschiff_position + 2 or
           gegner_laser_position == raumschiff_position + 9 ):
            raumschiff_getroffen(raumschiff_position)
            matrix.write()
            sleep_ms(1000)
            return False
        
        zyklus()
    return True

def level4():
    raumschiff_position = 24
    laser_position = 0
    laser_zaehler = 0
    laser_ein = False
    
    gegner_laser_position = 64
    gegner_laser_zaehler = 0
    gegner_laser_ein = False
    zeit_zaehler = 0

    gegner_pos = 47
    zufalls_position = random.choice(gegner_positionen)
    traeffer_zaehler = 0
    gegner_warten = 0
    gegner_richtung_hoch = False
    
    while(traeffer_zaehler < level_treffer):
        zeichne_schwarz()
        raumschiff_position = raumschiff_loop(raumschiff_position)
        
        leben_loop()
        
        laser_ein, laser_zaehler, laser_position = laser_loop(laser_ein, laser_zaehler, laser_position, raumschiff_position)
        
        gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler = gegner_laser_loop(gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler, gegner_pos, 7)
        
        if laser_position == gegner_pos:
            traeffer_zaehler = traeffer_zaehler + 1
            laser_position = laser_position + 1
            while gegner_pos == zufalls_position:
                zufalls_position = random.choice(gegner_positionen)
            gegner_pos = zufalls_position
        else:
            if gegner_warten < 5:
                gegner_warten = gegner_warten + 1
            if gegner_warten >= 5:
                gegner_warten = 0
                if gegner_richtung_hoch:
                    if gegner_pos + 8 > 55:
                      gegner_richtung_hoch = False
                if not gegner_richtung_hoch:
                    if gegner_pos - 8 < 7:
                      gegner_richtung_hoch = True
                if gegner_richtung_hoch:
                    gegner_pos = gegner_pos + 8
                else:
                    gegner_pos = gegner_pos - 8
                
            gegner(gegner_pos)
        
        if (gegner_laser_position == raumschiff_position or
           gegner_laser_position == raumschiff_position + 1 or
           gegner_laser_position == raumschiff_position + 2 or
           gegner_laser_position == raumschiff_position + 9 ):
            raumschiff_getroffen(raumschiff_position)
            matrix.write()
            sleep_ms(1000)
            return False
        
        zyklus(80)
    return True        

def level5():
    raumschiff_position = 24
    laser_position = 0
    laser_zaehler = 0
    laser_ein = False
    
    gegner_laser_position = 64
    gegner_laser_zaehler = 0
    gegner_laser_ein = False
    zeit_zaehler = 0

    gegner_pos = 47
    zufalls_position = random.choice(gegner_positionen)
    traeffer_zaehler = 0
    gegner_warten = 0
    gegner_richtung_hoch = False
    
    while(traeffer_zaehler < level_treffer):
        zeichne_schwarz()
        raumschiff_position = raumschiff_loop(raumschiff_position)
        
        leben_loop()
        
        laser_ein, laser_zaehler, laser_position = laser_loop(laser_ein, laser_zaehler, laser_position, raumschiff_position)
        
        gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler = gegner_laser_loop(gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler, gegner_pos, 2)
        
        if laser_position == gegner_pos:
            traeffer_zaehler = traeffer_zaehler + 1
            laser_position = laser_position + 1
            while gegner_pos == zufalls_position:
                zufalls_position = random.choice(gegner_positionen)
            gegner_pos = zufalls_position
        else:
            if gegner_warten < 5:
                gegner_warten = gegner_warten + 1
            if gegner_warten >= 5:
                gegner_warten = 0
                if gegner_richtung_hoch:
                    if gegner_pos + 8 > 55:
                      gegner_richtung_hoch = False
                if not gegner_richtung_hoch:
                    if gegner_pos - 8 < 7:
                      gegner_richtung_hoch = True
                if gegner_richtung_hoch:
                    gegner_pos = gegner_pos + 8
                else:
                    gegner_pos = gegner_pos - 8
                
            gegner(gegner_pos)
        
        if (gegner_laser_position == raumschiff_position or
           gegner_laser_position == raumschiff_position + 1 or
           gegner_laser_position == raumschiff_position + 2 or
           gegner_laser_position == raumschiff_position + 9 ):
            raumschiff_getroffen(raumschiff_position)
            matrix.write()
            sleep_ms(1000)
            return False
        
        zyklus(80)
    return True

def level6():
    raumschiff_position = 24
    laser_position = 0
    laser_zaehler = 0
    laser_ein = False
    
    gegner_laser_position = 64
    gegner_laser_zaehler = 0
    gegner_laser_ein = False
    zeit_zaehler = 0

    gegner_pos = 47
    zufalls_position = random.choice(gegner_positionen)
    traeffer_zaehler = 0
    gegner_warten = 0
    gegner_richtung_hoch = False
    
    while(traeffer_zaehler < level_treffer):
        zeichne_schwarz()
        raumschiff_position = raumschiff_loop(raumschiff_position)
        
        leben_loop()
        
        laser_ein, laser_zaehler, laser_position = laser_loop(laser_ein, laser_zaehler, laser_position, raumschiff_position)
        
        gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler = gegner_laser_loop(gegner_laser_ein, gegner_laser_zaehler, gegner_laser_position, zeit_zaehler, gegner_pos, 1)
        
        if laser_position == gegner_pos:
            traeffer_zaehler = traeffer_zaehler + 1
            laser_position = laser_position + 1
            while gegner_pos == zufalls_position:
                zufalls_position = random.choice(gegner_positionen)
            gegner_pos = zufalls_position
        else:
            if gegner_warten < 5:
                gegner_warten = gegner_warten + 1
            if gegner_warten >= 5:
                gegner_warten = 0
                if gegner_richtung_hoch:
                    if gegner_pos + 8 > 55:
                      gegner_richtung_hoch = False
                if not gegner_richtung_hoch:
                    if gegner_pos - 8 < 7:
                      gegner_richtung_hoch = True
                if gegner_richtung_hoch:
                    gegner_pos = gegner_pos + 8
                else:
                    gegner_pos = gegner_pos - 8
                
            gegner(gegner_pos)
        
        if (gegner_laser_position == raumschiff_position or
           gegner_laser_position == raumschiff_position + 1 or
           gegner_laser_position == raumschiff_position + 2 or
           gegner_laser_position == raumschiff_position + 9 ):
            raumschiff_getroffen(raumschiff_position)
            matrix.write()
            sleep_ms(1000)
            return False
        
        zyklus(70)
    return True

while True:
    pinin()
    matrix.write() # Informationen zur Matrix / den LEDs schicken

    while js_click.value() != 0:
        sleep_ms(100)
    
    katzen_leben = 9
    
    lvl_1_text()
    matrix.write()
    sleep_ms(2000)

    zeichne_schwarz()
    matrix.write()
    sleep_ms(500)

    level1()

    lvl_2_text()
    matrix.write()
    sleep_ms(2000)

    zeichne_schwarz()
    matrix.write()
    sleep_ms(500)

    level2()

    gewonnen = False
    while katzen_leben > 0:
        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)
    
        lvl_3_text()
        matrix.write()
        sleep_ms(2000)

        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)
        
        gewonnen = level3()
        if gewonnen:
            break
        else:
            katzen_leben = katzen_leben - 1
    
    if not gewonnen and katzen_leben <= 0:
        game_over()
        matrix.write()
        sleep_ms(3000)
        continue

    gewonnen = False
    while katzen_leben > 0:
        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)
        
        lvl_4_text()
        matrix.write()
        sleep_ms(2000)

        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)

        gewonnen = level4()
        
        if gewonnen:
            break
        else:
            katzen_leben = katzen_leben - 1
    
    if not gewonnen and katzen_leben <= 0:
        game_over()
        matrix.write()
        sleep_ms(3000)
        continue

    gewonnen = False
    while katzen_leben > 0:
        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)
        
        lvl_5_text()
        matrix.write()
        sleep_ms(2000)

        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)

        gewonnen = level5()
        
        if gewonnen:
            break
        else:
            katzen_leben = katzen_leben - 1
    
    if not gewonnen and katzen_leben <= 0:
        game_over()
        matrix.write()
        sleep_ms(3000)
        continue
    
    gewonnen = False
    while katzen_leben > 0:
        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)
        
        lvl_6_text()
        matrix.write()
        sleep_ms(2000)

        zeichne_schwarz()
        matrix.write()
        sleep_ms(500)

        gewonnen = level6()
        
        if gewonnen:
            break
        else:
            katzen_leben = katzen_leben - 1
    
    if not gewonnen and katzen_leben <= 0:
        game_over()
        matrix.write()
        sleep_ms(3000)
        continue

    if gewonnen:
        pompi()
        matrix.write() # Informationen zur Matrix / den LEDs schicken
        sleep_ms(5000)
