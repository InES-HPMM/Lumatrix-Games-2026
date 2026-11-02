"""Runs the Pico program (pico/main.py) on the Mac with fake hardware.

    python -m unittest discover -s host

Fakes the machine module, MicroPython's time functions and the serial
link, then drives the Lumatrix with laptop lines and joystick presses and
looks at what would go to the LEDs.
"""

import os
import sys
import time
import types
import unittest

PICO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pico")

CLOCK = [0]
time.ticks_ms = lambda: CLOCK[0]
time.ticks_add = lambda a, b: a + b
time.ticks_diff = lambda a, b: a - b
time.sleep_ms = lambda ms: None

FRAMES = []
PRESSED = set()  # pin numbers held down


class FakePin:
    IN, OUT, PULL_UP = 0, 1, 2

    def __init__(self, number, *args, **kwargs):
        self.number = number

    def value(self, *args):
        return 0 if self.number in PRESSED else 1


machine = types.ModuleType("machine")
machine.Pin = FakePin
machine.bitstream = lambda pin, mode, timing, data: FRAMES.append(bytes(data))
sys.modules["machine"] = machine

sys.path.insert(0, PICO)
os.chdir(PICO)  # main.py opens model.bin, icons.bin, brightness.txt here
import main  # noqa: E402
from main import EmojiZoo, Lumatrix  # noqa: E402


class FakeLink:
    def __init__(self):
        self.queue = []

    def lines(self, budget=800):
        found, self.queue = self.queue, []
        return found


def make_app():
    main.LaptopLink = FakeLink
    app = Lumatrix()
    app.brain.taught_path = os.devnull  # never write taught.bin in tests
    return app


def run(app, ms):
    for _ in range(ms // main.FRAME_MS):
        CLOCK[0] += main.FRAME_MS
        app.step(CLOCK[0])


class Icons(unittest.TestCase):
    def test_every_symbol_of_the_model_has_a_picture(self):
        app = make_app()
        missing = [n for n in app.brain.names if n not in app.zoo.icons]
        self.assertEqual(missing, [])

    def test_animation_modes(self):
        zoo = EmojiZoo("icons.bin")
        zoo.icons["t"] = (100, 0, 0, 3)
        self.assertEqual([zoo.frame_at("t", ms) for ms in range(0, 700, 100)], [0, 1, 2, 0, 1, 2, 0])
        zoo.icons["t"] = (100, 1, 0, 3)
        self.assertEqual([zoo.frame_at("t", ms) for ms in range(0, 700, 100)], [0, 1, 2, 1, 0, 1, 2])
        zoo.icons["t"] = (100, 2, 0, 3)
        self.assertEqual([zoo.frame_at("t", ms) for ms in range(0, 700, 100)], [0, 1, 2, 2, 2, 2, 2])


def in_mode(app, mode):
    """Puts the app in a mode and waits until the mode's number is gone."""
    app.switch_mode(mode, CLOCK[0])
    run(app, main.MODE_DRUMROLL_MS + 100)


def tap(app, name, hold=100, after=500):
    PRESSED.add(main.BUTTON_PINS[name])
    run(app, hold)
    PRESSED.discard(main.BUTTON_PINS[name])
    run(app, after)


def double_press(app):
    tap(app, "center", hold=50, after=100)
    tap(app, "center", hold=50, after=500)


class Modes(unittest.TestCase):
    def test_up_and_down_switch_modes_and_show_the_number_first(self):
        app = make_app()
        self.assertEqual(app.mode, main.LYRICS)
        tap(app, "up", after=100)
        self.assertEqual(app.mode, main.QUIZ)
        self.assertTrue(any(FRAMES[-1]))  # the big 2
        tap(app, "down", after=100)
        self.assertEqual(app.mode, main.LYRICS)

    def test_the_cover_shows_until_the_first_emoji(self):
        app = make_app()
        app.laptop.queue.append("IMG " + "ff0000" * 64)
        run(app, 800)
        self.assertIsNone(app.emoji)
        self.assertEqual(FRAMES[-1][1], max(FRAMES[-1][1::3]))  # red cover (GRB: red is byte 1)
        app.laptop.queue.append("WORD fire")
        run(app, 200)
        self.assertEqual(app.emoji, "fire")

    def test_pressing_in_the_lyrics_mode_scrolls_the_title(self):
        app = make_app()
        app.laptop.queue += ["IMG " + "ff0000" * 64, "TITLE LIKE THE SUN"]
        run(app, 100)
        tap(app, "center", after=600)
        self.assertIsNotNone(app.ticker)
        self.assertTrue(any(FRAMES[-1]))
        run(app, 8000)
        self.assertIsNone(app.ticker)  # scrolled through, back to the cover


class Words(unittest.TestCase):
    def test_a_sung_word_pops_up_its_symbol_and_animates(self):
        app = make_app()
        in_mode(app, main.LYRICS)
        app.laptop.queue.append("WORD fire")
        run(app, 200)
        self.assertEqual(app.emoji, "fire")
        self.assertTrue(any(FRAMES[-1]))
        run(app, 1000)
        if app.zoo.icons["fire"][3] > 1:
            self.assertNotEqual(app.emoji_frame_no, 0)

    def test_a_new_symbol_waits_unless_the_model_is_surer(self):
        app = make_app()
        in_mode(app, main.LYRICS)
        app.laptop.queue.append("WORD fire")
        run(app, 100)
        app.emoji_confidence = 9.0  # pretend the brain was very sure about fire
        app.laptop.queue.append("WORD kiss")
        run(app, 100)
        self.assertEqual(app.emoji, "fire")
        run(app, main.MIN_SPOTLIGHT_MS)
        app.laptop.queue.append("WORD kiss")
        run(app, 100)
        self.assertEqual(app.emoji, "kiss")

    def test_the_emoji_stays_until_the_next_song(self):
        app = make_app()
        in_mode(app, main.LYRICS)
        app.laptop.queue.append("WORD fire")
        run(app, 10000)
        self.assertEqual(app.emoji, "fire")
        app.laptop.queue.append("IMG " + "00ff00" * 64)
        run(app, 100)
        self.assertIsNone(app.emoji)


class Negation(unittest.TestCase):
    def test_dont_cry_shows_a_stop_sign_then_crying(self):
        app = make_app()
        in_mode(app, main.LYRICS)
        app.laptop.queue.append("WORD don't cry")
        run(app, 100)
        self.assertEqual(app.emoji, "stop")
        app.laptop.queue.append("WORD cry")
        run(app, 100)
        self.assertEqual(app.emoji, "stop")  # the stop sign stays a moment
        run(app, main.STOP_SIGN_MS)
        self.assertEqual(app.emoji, "crying")

    def test_dont_before_a_word_without_emoji_shows_nothing(self):
        app = make_app()
        in_mode(app, main.LYRICS)
        app.laptop.queue.append("WORD don't know")
        run(app, 200)
        self.assertIsNone(app.emoji)

    def test_riddles_show_the_stop_sign_too(self):
        app = make_app()
        from riddle import RIDDLES, QuizMaster

        game = QuizMaster(app.brain, app.zoo.icons, 0)
        game.index = RIDDLES.index("boys don't cry")
        game.load(0)
        self.assertEqual([c[1][c[2]] for c in game.clues], ["stop", "crying"])


class EmojiRaetsel(unittest.TestCase):
    def test_without_a_laptop_the_game_starts_and_the_laptop_takes_over(self):
        app = make_app()
        run(app, main.LONELY_AFTER_MS + main.MODE_DRUMROLL_MS + 300)
        self.assertEqual(app.mode, main.QUIZ)
        self.assertIsNotNone(app.quiz)
        app.laptop.queue.append("PLAY 1")
        run(app, 50)
        self.assertEqual(app.mode, main.LYRICS)

    def test_a_chosen_game_stays_when_the_laptop_talks(self):
        app = make_app()
        in_mode(app, main.QUIZ)
        app.laptop.queue.append("IMG " + "ff0000" * 64)
        run(app, 100)
        self.assertEqual(app.mode, main.QUIZ)

    def test_joystick_moves_through_riddles_and_reveals(self):
        app = make_app()
        in_mode(app, main.QUIZ)
        first = app.quiz.index
        tap(app, "right")
        self.assertEqual(app.quiz.index, first + 1)
        tap(app, "center")
        self.assertIsNotNone(app.quiz.reveal_at)
        run(app, 400)
        self.assertTrue(any(FRAMES[-1]))  # the answer scrolls

    def test_teaching_changes_what_the_model_shows(self):
        app = make_app()
        brain = app.brain
        before = brain.guess("highway")[0]
        guess = [brain.names[k] for _, k in brain.ranked(brain.vector("highway"))][0]
        brain.teach("highway", guess)
        self.assertEqual(brain.guess("highway")[0], guess)
        brain.forget()
        self.assertEqual(brain.guess("highway")[0], before)

    def test_every_riddle_shows_at_least_two_symbols(self):
        app = make_app()
        from riddle import RIDDLES, QuizMaster

        game = QuizMaster(app.brain, app.zoo.icons, 0)
        weak = []
        for k, text in enumerate(RIDDLES):
            game.index = k
            game.load(0)
            names = [c[1][c[2]] for c in game.clues]
            if len(names) < 2:
                weak.append("%s -> %s" % (text, names))
        self.assertEqual(weak, [], "riddles with fewer than 2 symbols")


class BareLumatrix(unittest.TestCase):
    """What the jury does with a fresh Lumatrix and no laptop."""

    def test_teaching_a_word_again_changes_it_again(self):
        brain = make_app().brain
        guesses = [brain.names[k] for _, k in brain.ranked(brain.vector("highway"))]
        brain.teach("highway", guesses[1])
        brain.teach("highway", guesses[2])
        self.assertEqual(brain.guess("highway")[0], guesses[2])
        brain.forget()

    def test_asking_for_more_guesses_never_leaves_the_riddle_dark(self):
        app = make_app()
        in_mode(app, main.QUIZ)
        for _ in range(12):
            double_press(app)
        before = len(FRAMES)
        run(app, 4000)
        self.assertTrue(any(any(f) for f in FRAMES[before:]))

    def test_double_press_shows_the_next_guess_and_hold_teaches_it(self):
        app = make_app()
        in_mode(app, main.QUIZ)
        if app.quiz.clue_at(CLOCK[0]) is None:
            run(app, 1700)  # wait for the next clue
        double_press(app)
        self.assertEqual(app.quiz.feedback[0], "next")
        tap(app, "center", hold=900)
        self.assertEqual(app.quiz.feedback[0], "taught")
        app.brain.forget()

    def test_the_cheat_code_works_in_the_riddle_and_teaches_nothing(self):
        app = make_app()
        in_mode(app, main.QUIZ)
        taught = len(app.brain.labels)
        for name in main.KONAMI_CODE:
            tap(app, name, hold=75, after=150)
        run(app, 500)  # the last press counts once the double-press wait is over
        self.assertIsNotNone(app.kaboom)
        self.assertEqual(len(app.brain.labels), taught)

    def test_the_switch_position_at_start_does_not_matter(self):
        PRESSED.add(main.BUTTON_PINS["switch"])
        try:
            app = make_app()
            self.assertFalse(app.brightness_mode)
        finally:
            PRESSED.discard(main.BUTTON_PINS["switch"])

    def test_holding_the_press_3_s_forgets_what_was_taught(self):
        app = make_app()
        in_mode(app, main.QUIZ)
        app.brain.teach("light", "sun")
        tap(app, "center", hold=3200)
        self.assertEqual(len(app.brain.labels), 0)


class TypedRiddles(unittest.TestCase):
    """A sentence typed in Thonny's shell becomes your own riddle."""

    def test_a_typed_sentence_becomes_a_riddle_in_the_quiz_mode(self):
        app = make_app()
        app.laptop.queue.append("I love pizza and the sun")
        run(app, 100)
        self.assertEqual(app.mode, main.QUIZ)
        self.assertEqual(app.quiz.typed, "I love pizza and the sun")
        names = [c[1][c[2]] for c in app.quiz.clues]
        self.assertIn("heart", names)
        self.assertIn("sun", names)
        tap(app, "right")
        self.assertIsNone(app.quiz.typed)  # back to the built-in riddles

    def test_a_sentence_without_emojis_just_scrolls_by(self):
        app = make_app()
        app.laptop.queue.append("the of and")
        run(app, 100)
        self.assertEqual(app.quiz.clues, [])
        self.assertIsNotNone(app.quiz.reveal_at)

    def test_a_garbled_laptop_line_is_not_a_riddle(self):
        app = make_app()
        app.laptop.queue.append("IMG 12ab")
        run(app, 100)
        self.assertEqual(app.mode, main.LYRICS)



if __name__ == "__main__":
    unittest.main()
