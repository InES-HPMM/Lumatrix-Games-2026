import unittest
from pixel_buddy.pet import Pet
from pixel_buddy.controls import Controls, NAMES


class PetTests(unittest.TestCase):
    def test_feed_pet_and_cooldown(self):
        pet = Pet()
        pet.food = 20
        self.assertEqual(pet.mood, "sad")
        pet.action("up")
        self.assertEqual(pet.food, 40)
        pet.action("up")
        self.assertEqual(pet.food, 40)
        pet.update(2400)
        pet.action("up")
        self.assertEqual(pet.food, 60)
        self.assertEqual(pet.mood, "happy")
        pet.update(2400)
        before = pet.joy
        pet.action("center")
        self.assertEqual(pet.joy, min(100, before + 8))

    def test_day_decay_sleep_and_limits(self):
        pet = Pet()
        pet.update(10000)
        self.assertEqual((pet.food, pet.energy, pet.joy), (74, 74, 64))
        pet.set_sleep(True)
        pet.update(10000)
        self.assertEqual((pet.food, pet.energy, pet.joy), (73, 79, 64))
        pet.action("right")
        self.assertFalse(pet.game)
        for _ in range(1000):
            pet.update(10000)
        self.assertEqual(pet.energy, 100)
        self.assertEqual(pet.food, 0)

    def test_rest_and_status(self):
        pet = Pet()
        pet.action("left")
        self.assertEqual(pet.rest, 15000)
        pet.update(10000)
        self.assertEqual(pet.energy, 80)
        pet.action("center")
        self.assertEqual(pet.rest, 0)
        pet.action("down")
        self.assertEqual(pet.effect, "status")

    def test_game_scores_and_returns(self):
        pet = Pet()
        pet.action("right")
        self.assertTrue(pet.game)
        self.assertEqual(pet.energy, 67)
        for _ in range(5):
            pet.basket = min(6, pet.star)
            for _ in range(7):
                pet.update(550)
        self.assertFalse(pet.game)
        self.assertEqual(pet.score, 5)
        self.assertEqual(pet.effect, "win")
        self.assertGreater(pet.joy, 65)

    def test_game_boundaries_cancel_and_sleep(self):
        pet = Pet()
        pet.action("right")
        for _ in range(20):
            pet.action("left")
        self.assertEqual(pet.basket, 0)
        for _ in range(20):
            pet.action("right")
        self.assertEqual(pet.basket, 6)
        pet.action("center")
        self.assertFalse(pet.game)
        pet.update(2300)
        pet.action("right")
        pet.set_sleep(True)
        self.assertFalse(pet.game)


class InputTests(unittest.TestCase):
    def test_bounce_hold_release_and_switch(self):
        class Pin:
            state = 1
            def value(self):
                return self.state
        class Buttons:
            pass
        buttons = Buttons()
        for name in NAMES:
            setattr(buttons, name, Pin())
        controls = Controls(buttons)
        buttons.up.state = 0
        self.assertEqual(controls.update(10), [])
        buttons.up.state = 1
        self.assertEqual(controls.update(10), [])
        buttons.up.state = 0
        self.assertEqual(controls.update(10), [])
        self.assertEqual(controls.update(40), ["up"])
        self.assertEqual(controls.update(200), [])
        buttons.up.state = 1
        controls.update(40)
        controls.update(40)
        buttons.up.state = 0
        controls.update(40)
        self.assertEqual(controls.update(40), ["up"])
        buttons.switch.state = 0
        controls.update(40)
        controls.update(40)
        self.assertTrue(controls.sleeping)


if __name__ == "__main__":
    unittest.main()
