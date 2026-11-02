"""Tests for how covers are turned into 8x8 pixels.

    python -m unittest discover -s host

The covers are drawn at 640x640, so each LED's patch is 80x80 pixels:
patch (x, y) spans x*80..x*80+80 and y*80..y*80+80, top row first.
"""

import io
import random
import unittest

from PIL import Image, ImageDraw

from lumatrix_music import cover_pixels

RED = (180, 30, 35)
GREEN = (40, 140, 60)
BLACK = (0, 0, 0)
WHITE = (240, 240, 240)


def png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def cover(background, *shapes, texture=0):
    """A 640x640 cover: a background with rectangles (x0, y0, x1, y1, colour).
    texture > 0 varies the background in 5x5 blocks by up to that much."""
    img = Image.new("RGB", (640, 640), background)
    draw = ImageDraw.Draw(img)
    if texture:
        rng = random.Random(1)
        for y in range(0, 640, 5):
            for x in range(0, 640, 5):
                shade = tuple(max(0, min(255, v + rng.randint(-texture, texture))) for v in background)
                draw.rectangle((x, y, x + 4, y + 4), fill=shade)
    for x0, y0, x1, y1, color in shapes:
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=color)
    return png(img)


def led(pixels, x, y):
    i = 3 * (8 * y + x)
    return tuple(pixels[i : i + 3])


def is_red(color):
    r, g, b = color
    return r > 200 and g < 100 and b < 100


class AutoStyle(unittest.TestCase):
    def test_dark_figure_on_flat_cover_turns_its_leds_dark(self):
        # Black bar over 30 of 80 columns of patches (3, 2)..(3, 4)
        pixels = cover_pixels(cover(RED, (250, 160, 280, 400, BLACK)), "auto")
        for y in (2, 3, 4):
            self.assertLess(max(led(pixels, 3, y)), 50, "patch (3, %d)" % y)
        self.assertTrue(is_red(led(pixels, 0, 0)))
        self.assertTrue(is_red(led(pixels, 4, 3)))

    def test_dark_figure_on_textured_cover_turns_its_leds_dark(self):
        # Like leather or paper: the background is not one exact colour
        pixels = cover_pixels(cover(RED, (250, 160, 280, 400, BLACK), texture=12), "auto")
        self.assertLess(max(led(pixels, 3, 3)), 50)
        self.assertTrue(is_red(led(pixels, 6, 6)))

    def test_light_figure_on_flat_cover_turns_its_leds_light(self):
        # White bar over 20 of 80 columns of patches (3, 2)..(3, 4)
        pixels = cover_pixels(cover(GREEN, (250, 160, 270, 400, WHITE)), "auto")
        self.assertGreater(min(led(pixels, 3, 3)), 180)

    def test_figure_on_dark_cover_is_brightened_like_the_rest(self):
        # smooth brightens dark covers 2.5x; the figure must get that too
        pixels = cover_pixels(cover((20, 30, 60), (250, 160, 270, 400, (120, 120, 130))), "auto")
        self.assertGreater(min(led(pixels, 3, 3)), 200)

    def test_figure_edges_shade_gradually(self):
        # Row 3: the figure covers 5, 10 and 15 of 80 columns in three patches
        pixels = cover_pixels(
            cover(RED, (80, 240, 85, 320, BLACK), (240, 240, 250, 320, BLACK), (400, 240, 415, 320, BLACK)),
            "auto",
        )
        self.assertTrue(is_red(led(pixels, 1, 3)), "barely touched patch stays background")
        self.assertTrue(50 < led(pixels, 3, 3)[0] < 200, "half-covered patch is in between")
        self.assertLess(max(led(pixels, 5, 3)), 50, "well-covered patch is the figure")

    def test_fine_lines_like_lettering_leave_leds_background(self):
        # 1 px lines every 8 px across the top row: 1/8 of those patches is black
        lines = [(x, 0, x + 1, 80, BLACK) for x in range(0, 640, 8)]
        pixels = cover_pixels(cover(RED, *lines), "auto")
        for x in range(8):
            self.assertTrue(is_red(led(pixels, x, 0)), "patch (%d, 0)" % x)

    def test_busy_cover_looks_exactly_like_smooth(self):
        # No colour dominates, like a photo: nothing should be split
        rng = random.Random(7)
        small = Image.new("RGB", (64, 64))
        small.putdata([tuple(rng.randrange(256) for _ in range(3)) for _ in range(64 * 64)])
        data = png(small.resize((640, 640), Image.Resampling.NEAREST))
        self.assertEqual(cover_pixels(data, "auto"), cover_pixels(data, "smooth"))

    def test_photo_on_half_plain_cover_looks_exactly_like_smooth(self):
        # A busy picture over the top 45 % of a plain cover, like a collage
        # on a beige backdrop: splitting it would only add noise
        rng = random.Random(3)
        img = Image.new("RGB", (640, 640), (225, 205, 170))
        draw = ImageDraw.Draw(img)
        for y in range(0, 288, 16):
            for x in range(0, 640, 16):
                draw.rectangle((x, y, x + 15, y + 15), fill=tuple(rng.randrange(256) for _ in range(3)))
        data = png(img)
        self.assertEqual(cover_pixels(data, "auto"), cover_pixels(data, "smooth"))


if __name__ == "__main__":
    unittest.main()
