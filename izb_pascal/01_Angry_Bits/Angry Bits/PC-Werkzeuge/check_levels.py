# Prueft alle Levels aus levels.py auf dem PC (nicht auf dem Pico!)
#
# Rechnet mit der echten Spiellogik aus main.py jede Kombination aus
# Winkel und Kraft fuer jeden Vogel durch und meldet:
#   - ob das Level schaffbar ist
#   - wie viele Voegel mindestens noetig sind (= par fuer 3 Sterne)
#   - wie viele erste Schuesse ueberhaupt etwas treffen
#
# Starten:  python check_levels.py        (alle Levels)
#           python check_levels.py 2 5    (nur Level 2 und 5)
# Rueckgabe: Exit-Code 1, wenn ein Level kaputt ist oder par nicht stimmt

import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)    # das Spiel liegt eine Ebene hoeher


# ---------------------------------------------------------------
# Attrappen fuer die Pico-Module, ohne Anzeige und ohne Wartezeiten
# ---------------------------------------------------------------
class _Pin:
    IN = 0
    OUT = 1
    PULL_UP = 1

    def __init__(self, *a, **k):
        pass

    def value(self, v=None):
        return 1


class _NeoPixel:
    def __init__(self, pin, n):
        pass

    def __setitem__(self, i, c):
        pass

    def write(self):
        pass


_machine = types.ModuleType("machine")
_machine.Pin = _Pin
_neopixel = types.ModuleType("neopixel")
_neopixel.NeoPixel = _NeoPixel
sys.modules["machine"] = _machine
sys.modules["neopixel"] = _neopixel
time.sleep_ms = lambda ms: None
time.ticks_ms = lambda: 0
time.ticks_diff = lambda a, b: a - b
time.ticks_add = lambda a, b: a + b

sys.path.insert(0, GAME_DIR)
import main as game                             # noqa: E402

for _name in ("draw", "flash", "shake", "tone", "melody", "sleep_ms"):
    setattr(game, _name, lambda *a, **k: None)


# ---------------------------------------------------------------
# Loeser
# ---------------------------------------------------------------
def pigs(objs):
    return sum(1 for k, hp in objs.values() if k == "P")


def state_key(objs):
    return tuple(sorted((c, k, hp) for c, (k, hp) in objs.items()))


def shoot(objs, kind, ai, pi):
    o = {c: list(v) for c, v in objs.items()}
    game.fly(o, [], kind, game.ANGLES[ai], game.POWERS[pi])
    game.settle(o, [])
    return o


def solve(level):
    """Breitensuche ueber alle Spielzustaende mit allen Voegeln.

    Gibt ein dict zurueck: min_birds (None = unschaffbar), ways (Siegwege
    mit min_birds Voegeln), example (ein Siegweg), first_hits (wie viele
    erste Schuesse etwas veraendern), shots (Schuesse pro Vogel),
    luck (Gewinnchance in %, wenn jeder Schuss zufaellig ist)."""
    birds = level["birds"]
    start = game.make_objs(level)
    shots = len(game.ANGLES) * len(game.POWERS)
    first_hits = 0
    start_key = state_key(start)
    # Zustand -> (Objekte, ein Weg dorthin, Wahrscheinlichkeit)
    layer = {start_key: (start, [], 1.0)}
    min_birds, ways, example, luck = None, 0, None, 0.0
    for b, kind in enumerate(birds):
        nxt = {}
        for objs, path, prob in layer.values():
            for ai in range(len(game.ANGLES)):
                for pi in range(len(game.POWERS)):
                    o = shoot(objs, kind, ai, pi)
                    if b == 0 and state_key(o) != start_key:
                        first_hits += 1
                    if pigs(o) == 0:
                        luck += prob / shots
                        if min_birds is None or min_birds == b + 1:
                            min_birds = b + 1
                            ways += 1
                            example = example or path + [
                                (kind, game.ANGLES[ai], game.POWERS[pi])]
                        continue
                    k = state_key(o)
                    if k in nxt:
                        nxt[k] = (nxt[k][0], nxt[k][1],
                                  nxt[k][2] + prob / shots)
                    else:
                        nxt[k] = (o, path + [
                            (kind, game.ANGLES[ai], game.POWERS[pi])],
                            prob / shots)
        layer = nxt
    return {"min_birds": min_birds, "ways": ways, "example": example,
            "first_hits": first_hits, "shots": shots, "luck": 100 * luck}


def main():
    wanted = [int(a) for a in sys.argv[1:]] or range(1, len(game.LEVELS) + 1)
    ok = True
    for n in wanted:
        lv = game.LEVELS[n - 1]
        t = time.time()
        r = solve(lv)
        par = lv.get("par")
        hit_pct = 100 * r["first_hits"] // r["shots"]
        if r["min_birds"] is None:
            verdict = "UNSCHAFFBAR"
            ok = False
        elif par != r["min_birds"]:
            verdict = "par falsch: steht %s, richtig waere %d" % (
                par, r["min_birds"])
            ok = False
        else:
            verdict = "OK"
        print("Level %d  Voegel %-5s min %s  Siegwege %3d  "
              "1. Schuss trifft %2d%%  Zufallschance %5.1f%%  (%.1fs)  %s"
              % (n, lv["birds"], r["min_birds"], r["ways"], hit_pct,
                 r["luck"], time.time() - t, verdict))
        if r["example"]:
            print("         z.B. " + ", ".join(
                "%s %d Grad Kraft %.2f" % s for s in r["example"]))
    print("\nAlles in Ordnung." if ok else "\nEs gibt Probleme (siehe oben).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
