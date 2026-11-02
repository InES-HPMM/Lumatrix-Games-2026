from collections import namedtuple

PixelColor = namedtuple ("LED_Color", ["red", "green", "blue"])

class LED_Color(): #Own Colorset
    
    #For normal LED
    WHITE                = PixelColor(50, 50, 50)
    RED                  = PixelColor(50, 0, 0)
    BLUE                 = PixelColor(0, 0, 50)
    GREEN                = PixelColor(0, 50, 0)
    YELLOW               = PixelColor(50, 50, 0)
    BLACK                = PixelColor(0, 0, 0)
    DARK_AMBER           = PixelColor(50, 35, 0)
    PURPLE               = PixelColor(50, 0, 50)
    PURPLE_LOW           = PixelColor(15, 0, 15)
    ORANGE               = PixelColor(100, 40, 0)
    
    #FOR TEXT
    TEXT_YELLOW          = PixelColor(200, 200, 0)
    TEXT_RED             = PixelColor(200, 0, 0)
    TEXT_GREEN           = PixelColor(0, 200, 0)
    
    #For winning screen
    WINN_GREEN_FRAME      = PixelColor(0, 150, 0)
    WINN_GREEN_BG         = PixelColor(0, 25, 0)
    
    #For loose Screen
    LOOSE_RED_LINE       = PixelColor(150, 0, 0)
    LOOSE_RED_BG         = PixelColor(25, 0, 0)
