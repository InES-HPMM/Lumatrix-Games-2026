"""Original ZHAW driver owns pin/timing/GRB mapping."""
from zhaw_led_matrix import LedMatrix


class Display:
    def __init__(self, brightness=20):
        self.matrix = LedMatrix(8, 8)
        self.matrix.set_brightness(brightness)

    def show(self, frame):
        for y in range(8):
            for x in range(8):
                i = (y * 8 + x) * 3
                self.matrix[x, 7 - y] = (frame[i], frame[i + 1], frame[i + 2])
        self.matrix.apply()

    def clear(self):
        self.matrix.clear()
        self.matrix.apply()
