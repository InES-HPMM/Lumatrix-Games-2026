# Ablauf des ganzen Spiels
import gc
from . import story, jungle, boss


def run():
    while True:
        story.title()
        story.storm()
        story.beach()
        gc.collect()
        jungle.play()
        story.dizzy()
        gc.collect()
        scene = boss.play()
        story.victory(scene)
        story.ending()
        story.the_end()
        gc.collect()
