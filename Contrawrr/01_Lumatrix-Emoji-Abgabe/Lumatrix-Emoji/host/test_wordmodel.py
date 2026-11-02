"""Tests for the Pico's word model (pico/wordmodel.py, run here on the Mac).

    python -m unittest discover -s host

The model file comes from model/build_model.py.
"""

import os
import sys
import unittest

PICO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pico")
sys.path.insert(0, PICO)

from wordmodel import TinyBrain, normal  # noqa: E402

MODEL = os.path.join(PICO, "model.bin")


class Normal(unittest.TestCase):
    def test_lowercase_letters_and_apostrophes_only(self):
        self.assertEqual(normal("Fire,"), "fire")
        self.assertEqual(normal("Don't!"), "don't")


@unittest.skipUnless(os.path.exists(MODEL), "build the model first: python model/build_model.py")
class Symbols(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain = TinyBrain(MODEL)

    def test_keywords_show_their_symbol(self):
        for word, symbol in {"fire": "fire", "heart": "heart", "eyes": "eye", "money": "money", "kiss": "kiss"}.items():
            self.assertEqual(self.brain.guess(word)[0], symbol, word)

    def test_related_words_nobody_listed_find_the_symbol(self):
        cases = {"spacecraft": "rocket", "rattlesnake": "snake", "streetcar": "train", "bawling": "crying", "saxophone": "guitar"}
        for word, symbol in cases.items():
            self.assertEqual(self.brain.guess(word)[0], symbol, word)

    def test_other_forms_of_a_known_word_find_its_symbol(self):
        # Plurals and the dropped g of song lyrics, which the model doesn't store
        for word, symbol in {"kisses": "kiss", "burnin'": "fire", "diamonds": "diamond"}.items():
            self.assertEqual(self.brain.guess(word)[0], symbol, word)

    def test_common_and_unknown_words_show_nothing(self):
        for word in ("the", "you", "baby", "know", "xyzzy"):
            self.assertIsNone(self.brain.guess(word)[0], word)

    def test_percent_is_100_for_keywords_and_50_at_the_bar(self):
        name, confidence = self.brain.guess("sun")
        self.assertEqual(self.brain.percent(name, confidence), 100)
        self.assertEqual(self.brain.percent(name, 1.0), 50)
        self.assertLess(self.brain.percent(name, 0.9), 50)

    def test_capitals_and_punctuation_do_not_matter(self):
        self.assertEqual(self.brain.guess("Fire!")[0], "fire")


if __name__ == "__main__":
    unittest.main()
