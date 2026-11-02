"""Desktop only: python tools/preview.py (requires Pillow)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from pixel_buddy.faces import ORDER, paint

image = Image.new("RGB", (600, 230), (10, 18, 23))
draw = ImageDraw.Draw(image)
for number, emotion in enumerate(ORDER):
    frame = bytearray(192)
    paint(frame, emotion)
    ox, oy = 16 + number % 4 * 200, 16 + number // 4 * 230
    for y in range(8):
        for x in range(8):
            i = (y * 8 + x) * 3
            color = tuple(frame[i:i + 3])
            draw.rounded_rectangle((ox+x*21, oy+y*21, ox+x*21+18, oy+y*21+18), radius=3, fill=color)
    draw.text((ox, oy+182), emotion.upper(), fill=(216, 234, 225))
image.save("pixel_buddy_preview.png")
