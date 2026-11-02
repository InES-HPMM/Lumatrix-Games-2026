"""Small in-memory needs model and nonblocking star-catching game."""
from random import getrandbits


class Pet:
    def __init__(self):
        self.food = 75
        self.energy = 75
        self.joy = 65
        self.tick = 0
        self.sleeping = False
        self.rest = 0
        self.effect = ""
        self.effect_ms = 0
        self.cooldown = 0
        self.game = False
        self.basket = 3
        self.star = 0
        self.row = 0
        self.fall = 0
        self.round = 0
        self.score = 0

    @property
    def mood(self):
        if min(self.food, self.energy, self.joy) < 30:
            return "sad"
        if min(self.food, self.energy) >= 50 and self.joy >= 65:
            return "happy"
        return "neutral"

    def feedback(self, effect, duration=2000):
        self.effect = effect
        self.effect_ms = duration

    def set_sleep(self, sleeping):
        if sleeping != self.sleeping:
            self.sleeping = sleeping
            self.rest = 0
            self.game = False
            self.effect_ms = 0

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        self.effect_ms = max(0, self.effect_ms - dt)
        self.tick += dt
        while self.tick >= 10000:
            self.tick -= 10000
            self.food = max(0, self.food - 1)
            if self.sleeping or self.rest:
                self.energy = min(100, self.energy + 5)
            else:
                self.energy = max(0, self.energy - 1)
                self.joy = max(0, self.joy - 1)
        self.rest = max(0, self.rest - dt)
        if self.game:
            self.fall += dt
            while self.game and self.fall >= 550:
                self.fall -= 550
                self.row += 1
                if self.row == 7:
                    if self.basket <= self.star <= self.basket + 1:
                        self.score += 1
                    self.round += 1
                    if self.round == 5:
                        self.game = False
                        self.joy = min(100, self.joy + 5 + self.score * 4)
                        self.feedback("win" if self.score >= 3 else "played", 2500)
                    else:
                        self.row = 0
                        self.star = getrandbits(3)

    def action(self, event):
        if self.sleeping:
            return
        if self.game:
            if event == "left":
                self.basket = max(0, self.basket - 1)
            elif event == "right":
                self.basket = min(6, self.basket + 1)
            elif event == "center":
                self.game = False
            return
        if event == "down":
            self.feedback("status", 3500)
            return
        if self.rest:
            if event == "center":
                self.rest = 0
            return
        if self.cooldown:
            return
        if event == "up":
            if self.food >= 95:
                self.feedback("full")
            else:
                self.food = min(100, self.food + 20)
                self.joy = min(100, self.joy + 3)
                self.feedback("food", 2400)
        elif event == "center":
            self.joy = min(100, self.joy + 8)
            self.feedback("heart")
        elif event == "left":
            self.rest = 15000
        elif event == "right":
            if self.energy < 20 or self.food < 15:
                self.feedback("tired")
            else:
                self.energy -= 8
                self.food = max(0, self.food - 3)
                self.game = True
                self.round = self.score = self.row = self.fall = 0
                self.basket = 3
                self.star = getrandbits(3)
                self.effect_ms = 0
        self.cooldown = 2200
