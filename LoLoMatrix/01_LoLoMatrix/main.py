
from time import sleep_ms
from machine import Pin
from zhaw_led_matrix import Lumatrix, ColorTable
import random

# Joystick
pin_js_r = Pin(2, Pin.IN)
pin_js_l = Pin(7, Pin.IN)
pin_js_u = Pin(3, Pin.IN)
pin_js_d = Pin(6, Pin.IN)
pin_js_c = Pin(8, Pin.IN)

# Schalter für den Lernmodus
switch = Pin(9, Pin.IN)

lumatrix = Lumatrix()

# Bilder
b1 = "bitmaps/mc_pig.bmp"
b2 = "bitmaps/mc_creeper.bmp"
b3 = "Paluten3.bmp"
b4 = "yoshi.bmp"
b5 = "zhaw bild.bmp"

lumatrix.drawImage(b5, 20)

dateien = [b1, b2, b3, b4]

bilder = [
    "Minecraft-Schwein",
    "Creeper aus Minecraft",
    "Paluten der Minecraftyoutouber",
    "Yoshi"
]

fragen = [
    "Schwein",
    "Gruenes Monster",
    "YouTube",
    "nicht Minecraft"
]

nummer = 0
punkte = 0


def warte_auf_taste():
    while (
        pin_js_r.value() == 0 or
        pin_js_l.value() == 0 or
        pin_js_u.value() == 0 or
        pin_js_d.value() == 0 or
        pin_js_c.value() == 0
    ):
        sleep_ms(50)


def zeige_punkte():
    print("Punktzahl:", punkte)

    lumatrix.writeText(
        "Punkte: " + str(punkte),
        ColorTable.GREEN,
        10
    )

    sleep_ms(2000)


def quiz():
    global punkte

    # Punkte am Anfang zurücksetzen
    # Noch keine Punkte anzeigen
    punkte = 0

    print("Lernmodus gestartet!")

    # Fragen, die noch nicht gestellt wurden
    noch_offen = []

    while switch.value() == 0:

        # Alle Fragen einmal gestellt?
        # Dann wieder neu mischen
        if len(noch_offen) == 0:
            noch_offen = [0, 1, 2, 3]

        position = random.randint(0, len(noch_offen) - 1)
        richtig = noch_offen.pop(position)

        print("Frage:", fragen[richtig])

        lumatrix.writeText(
            fragen[richtig],
            ColorTable.RED,
            10
        )

        lumatrix.drawImage(b5, 20)
        sleep_ms(1500)

        auswahl = -1
        bestaetigt = False

        # Antwort auswählen
        while switch.value() == 0 and not bestaetigt:
            sleep_ms(100)

            if pin_js_r.value() == 0:
                auswahl = 0
                lumatrix.drawImage(dateien[auswahl], 20)
                print("Auswahl:", bilder[auswahl])
                warte_auf_taste()

            elif pin_js_l.value() == 0:
                auswahl = 1
                lumatrix.drawImage(dateien[auswahl], 20)
                print("Auswahl:", bilder[auswahl])
                warte_auf_taste()

            elif pin_js_u.value() == 0:
                auswahl = 2
                lumatrix.drawImage(dateien[auswahl], 20)
                print("Auswahl:", bilder[auswahl])
                warte_auf_taste()

            elif pin_js_d.value() == 0:
                auswahl = 3
                lumatrix.drawImage(dateien[auswahl], 20)
                print("Auswahl:", bilder[auswahl])
                warte_auf_taste()

            elif pin_js_c.value() == 0:

                if auswahl == -1:
                    print("Bitte zuerst ein Bild auswaehlen!")

                    lumatrix.writeText(
                        "Bild auswaehlen!",
                        ColorTable.RED,
                        10
                    )

                    sleep_ms(1000)

                    # Dieselbe Frage erneut anzeigen
                    lumatrix.writeText(
                        fragen[richtig],
                        ColorTable.RED,
                        10
                    )

                else:
                    bestaetigt = True

                warte_auf_taste()

        # Antwort auswerten, aber keine Punkte anzeigen
        if switch.value() == 0 and bestaetigt:

            if auswahl == richtig:
                punkte += 1

                print("Richtig!")

                lumatrix.writeText(
                    "RICHTIG!",
                    ColorTable.GREEN,
                    10
                )

            else:
                print("Falsch!")

                lumatrix.writeText(
                    "FALSCH!",
                    ColorTable.RED,
                    10
                )

            sleep_ms(1200)

    # Quiz beendet: Punkte einmal anzeigen
    print("Lernmodus beendet!")

    zeige_punkte()

    # Danach Punkte zurücksetzen
    punkte = 0

    # Startbild anzeigen
    lumatrix.drawImage(b5, 20)


# Startbild
lumatrix.drawImage(b5, 20)

while True:
    sleep_ms(100)

    # Schalter eingeschaltet: Lernmodus
    if switch.value() == 0:
        quiz()

    # Normaler Modus: Bilder auswählen
    elif pin_js_r.value() == 0:
        nummer = 1
        lumatrix.drawImage(b1, 20)
        warte_auf_taste()

    elif pin_js_l.value() == 0:
        nummer = 2
        lumatrix.drawImage(b2, 20)
        warte_auf_taste()

    elif pin_js_u.value() == 0:
        nummer = 3
        lumatrix.drawImage(b3, 20)
        warte_auf_taste()

    elif pin_js_d.value() == 0:
        nummer = 4
        lumatrix.drawImage(b4, 20)
        warte_auf_taste()

    elif pin_js_c.value() == 0:

        if nummer > 0:
            print("Ausgewaehlt:", bilder[nummer - 1])

            lumatrix.writeText(
                bilder[nummer - 1],
                ColorTable.RED,
                10
            )

            nummer = 0
            sleep_ms(1000)

            lumatrix.drawImage(b5, 20)

        warte_auf_taste()
#gehe noch weiter runter
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        























































#super aber war umsonst