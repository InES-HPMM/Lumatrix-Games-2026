#Zum optimalen erlebnis ledmatrix.py linie 248 delay auf 100ms ändern
#Die Datei runden.txt sollte umbedigt erstellt werden!
#kein ki code! ki wurde nur verwendet um zu recherchieren
#habe dass meiste erklärt weil unübersichtlich
from time import sleep
from time import sleep_ms
from machine import Pin
from neopixel import NeoPixel
from zhaw_led_matrix import Lumatrix, ColorTable
import os

lumatrix = Lumatrix()

pin = Pin(19, Pin.OUT)
np = NeoPixel(pin, 64)

pin_r = Pin(2, Pin.IN) #rechts
pin_l = Pin(7, Pin.IN) #links
pin_u = Pin(3, Pin.IN) #hoch
pin_d = Pin(6, Pin.IN) #runter
pin_m = Pin(8, Pin.IN) #mitte

#alle bitmaps definieren
bitmap1 = "/Faces/smiley1.bmp"
bitmap3 = "/Faces/smiley-3.bmp"
bitmap2 = "/Faces/smiley-2.bmp"
bitmap4 = "/Faces/smiley-4.bmp"
blinzeln = "/Faces/smileyb.bmp"
bitmapR = "/Faces/smiley-R.bmp"
bitmapB = "/Faces/smiley-B.bmp"
bitmapG = "/Faces/smiley-G.bmp"
R1 = "/Faces/Rainbowcat1.bmp"
R2 = "/Faces/Rainbowcat2.bmp"
R3 = "/Faces/Rainbowcat3.bmp"
R4 = "/Faces/Rainbowcat4.bmp"
G1 = "/Faces/G1.bmp"
G2 = "/Faces/G2.bmp"
G3 = "/Faces/G3.bmp"
G4 = "/Faces/G4.bmp"
Gb = "/Faces/Gb.bmp"

#definieren von speicher dateien
licht = "light.txt"
mode = "mode.txt"
SCORE = "runden.txt"

#definieren von variablen
nightmode = True
runde = 0
#runde ist nicht das insgesamte alle 10 runden wird die insgesamt zeit angezeigt

#light (brightness) abrufen und speichern
def lade_light():
    if licht in os.listdir():
        try:
            with open(licht, "r")as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def storelight(light):
    with open(licht, "w") as f:
        f.write(str(light))

#whitemode abrufen und speichern
def lade_mode():
    if mode in os.listdir():
        try:
            with open(mode, "r")as f:
                return bool(int(f.read().strip()))
        except:
            return 0
    return 0

def storemode(whitemode):
    with open(mode, "w") as f:
        f.write(str(int(whitemode)))
        
#insgesamt abrufen und speichern     
def lade_runden():
    if SCORE in os.listdir():
        try:
            with open(SCORE, "r")as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def speichern(insgesamt):
    with open(SCORE, "w") as f:
        f.write(str(insgesamt))

#alle gespeicherten daten abrufen
insgesamt = lade_runden()
whitemode = lade_mode()
light = lade_light()

#bis linie 212 funktionen die abgespielt werden das W am ende bedeutet whitemode
def Blinzeln():
    lumatrix.drawImage(bitmap3, light)
    sleep(2)
    lumatrix.drawImage(blinzeln, light)
    sleep_ms(50)
    lumatrix.drawImage(bitmap3,light)
    sleep(2)

def BlinzelnW():
    lumatrix.drawImage(G3, light)
    sleep_ms(1950)
    lumatrix.drawImage(Gb, light)
    sleep_ms(100)
    lumatrix.drawImage(G3,light)
    sleep(2)

def herumschauen():
    lumatrix.drawImage(bitmap3, light)
    sleep_ms(50)
    lumatrix.drawImage(bitmap1, light)
    sleep_ms(500)
    lumatrix.drawImage(bitmap3, light)
    sleep_ms(250)
    lumatrix.drawImage(bitmap4, light)
    sleep_ms(500)
    lumatrix.drawImage(bitmap3, light)
    sleep(1)
    #zusätzliches verhaltem
def herumschauenW():
    lumatrix.drawImage(G3, light)
    sleep_ms(50)
    lumatrix.drawImage(G1, light)
    sleep_ms(500)
    lumatrix.drawImage(G3, light)
    sleep_ms(250)
    lumatrix.drawImage(G4, light)
    sleep_ms(500)
    lumatrix.drawImage(G3, light)
    sleep(1)
    
def OOH():
    lumatrix.drawImage(bitmap2, light)
    sleep_ms(50)
    lumatrix.drawImage(bitmap2, light)
    sleep(1)
    lumatrix.drawImage(bitmap2, light)
    sleep(1)
def OOHW():
    lumatrix.drawImage(G2, light)
    sleep_ms(50)
    lumatrix.drawImage(G2, light)
    sleep(1)
    lumatrix.drawImage(G2, light)
    sleep(1)

def Rain():
    lumatrix.drawImage(bitmapR, light)
    sleep_ms(50)
    lumatrix.drawImage(bitmapG, light)
    sleep_ms(50)
    lumatrix.drawImage(bitmap3, light)
    sleep_ms(50)
    lumatrix.drawImage(bitmapB, light)
    sleep_ms(50)
    
def Rainbow():
    Rain()
    Rain()
    Rain()
    Rain()
    Rain()

def Greeting():
    if whitemode == False:
        lumatrix.drawImage(bitmap3, light)
        sleep(1)
        lumatrix.drawImage(bitmap1, light)
        sleep_ms(500)
        lumatrix.drawImage(bitmap3, light)
        sleep_ms(250)
        lumatrix.drawImage(bitmap2, light)
        sleep(1)
        lumatrix.writeText(Greeting_text, ColorTable.GREEN, light)
        sleep_ms(100)
    elif whitemode == True:
        lumatrix.drawImage(G3, light)
        sleep(1)
        lumatrix.drawImage(G1, light)
        sleep_ms(500)
        lumatrix.drawImage(G3, light)
        sleep_ms(250)
        lumatrix.drawImage(G2, light)
        sleep(1)
        lumatrix.writeText(Greeting_text, ColorTable.GREY, light)
        sleep_ms(100)
    #die Begrüssung
    
def cat():
    lumatrix.drawImage(R1, light)
    sleep_ms(50)
    lumatrix.drawImage(R2, light)
    sleep_ms(50)
    lumatrix.drawImage(R3, light)
    sleep_ms(50)
    lumatrix.drawImage(R4, light)
    sleep_ms(50)
    
def Rainbowcat():
    cat()
    cat()
    cat()
    cat()
    cat()
#eine wiederholung für cat der so genannten nyne cat

def Start():
    global runde, insgesamt
    while True:             
        if runde < 10:
            Blinzeln()
            Blinzeln()
            herumschauen()
            if insgesamt == 10000:  
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
            Blinzeln()
            Blinzeln()
            herumschauen()
            OOH()
            if insgesamt == 100000:
                Rainbow()
                Rainbowcat
                Rainbow()
                Rainbowcat()
            Blinzeln()
            Blinzeln()
            herumschauen()
            insgesamt += 1
            speichern(insgesamt)
            print(f"jetzt: {insgesamt}")
            runde += 1
        elif runde >= 10:
            Rainbowcat()
            Rainbowcat()
            Rainbowcat()
            Rainbowcat()
            zeit = 0.5541666667*insgesamt
            if zeit <= 120:
                zeit = round(zeit)
                lumatrix.writeText(f"schon {zeit} minuten", ColorTable.GREEN, light)
            elif zeit >= 120:
                zeit = zeit/60
                zeit = round(zeit)
                lumatrix.writeText(f"schon {zeit} stunden", ColorTable.GREEN, light)
            runde = 0

def StartW():
    global runde, insgesamt
    while True:             
        if runde < 10:
            BlinzelnW()
            BlinzelnW()
            herumschauenW()
            if insgesamt == 10000:  
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
                Rainbow()
            BlinzelnW()
            BlinzelnW()
            herumschauenW()
            OOHW()
            if insgesamt == 100000:
                Rainbow()
                Rainbowcat()
                Rainbow()
                Rainbowcat()
            BlinzelnW()
            BlinzelnW()
            herumschauenW()
            insgesamt += 1
            speichern(insgesamt)
            print(f"jetzt: {insgesamt}")
            runde += 1
        elif runde >= 10:
            Rainbowcat()
            Rainbowcat()
            Rainbowcat()
            Rainbowcat()
            zeit = 0.5541666667*insgesamt
            if zeit <= 120:
                zeit = round(zeit)
                zeit += 1
                lumatrix.writeText(f"schon {zeit} minuten", ColorTable.GREY, light)
            elif zeit >= 120:
                zeit = zeit/60
                zeit = round(zeit)
                lumatrix.writeText(f"schon {zeit} stunden", ColorTable.GREY, light)
            runde = 0
            
            
if light == 3:
    nightmode = True
    print("TRUE")
elif light >= 5:
    nightmode = False
    print("FALSE")
Greeting_text = "Hi, ich heisse Pixel"
if insgesamt == 0:
    Greeting()
else:
    print("hi")
if whitemode == False:
    lumatrix.writeText("Helligkeit", ColorTable.GREEN, light)
elif whitemode == True:
    lumatrix.writeText("Helligkeit", ColorTable.GREY, light)

while True:
    if pin_u.value() == 0:
        if light != 3:
            if light != 100 and light >= 20:
                light += 20
                lumatrix.writeText("U", ColorTable.GREEN, light)
            elif light <= 20 and light == 10:
                light += 10
                lumatrix.writeText("U", ColorTable.GREEN, light)
            elif light <=10 and light == 5:
                light += 5
                lumatrix.writeText("U", ColorTable.GREEN, light)
    if pin_d.value() == 0:
        if light > 20:
            light -= 20
            lumatrix.writeText("D", ColorTable.RED, light)
        elif light == 20:
            light -= 10
            lumatrix.writeText("D", ColorTable.RED, light)
        elif light == 10:
            light -= 5
            lumatrix.writeText("D", ColorTable.RED, light)
    elif pin_r.value() == 0:
        if whitemode == False:
            lumatrix.writeText("Start", ColorTable.GREEN, light)
            storemode(whitemode)
            storelight(light)
            Start()
        elif whitemode == True:
            lumatrix.writeText("Start", ColorTable.GREY, light)
            storemode(whitemode)
            storelight(light)
            StartW()
    elif pin_l.value() == 0:
        if whitemode == False and light !=3:
            light = 40
            whitemode = True
            storemode(whitemode)
            lumatrix.writeText("Weiss", ColorTable.GREY, light)
        elif whitemode == True and nightmode == False:
            nightmode = True
            light = 3
            storelight(light)
            lumatrix.writeText("Night", ColorTable.GREY, light)
        elif light == 3 and whitemode == True:
            nightmode = False
            whitemode = False
            light = 40
            storemode(whitemode)
            lumatrix.writeText("Green", ColorTable.GREEN, light)
