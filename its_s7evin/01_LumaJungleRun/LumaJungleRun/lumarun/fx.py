# Gemeinsame Effekte: Leben-Anzeige, Treffer-Blitz, Game Over, Feuerwerk
from . import hw, gfx

GAME_OVER = (
    "R......R",
    ".R....R.",
    "..R..R..",
    "...RR...",
    "...RR...",
    "..R..R..",
    ".R....R.",
    "R......R",
)


def tint(color, amount):
    """Ganzes Bild Richtung color einfaerben (amount 0..100)."""
    fb = hw.fb
    for i in range(64):
        fb[i] = gfx.mix(fb[i], color, amount)


def lives(n):
    """Verbleibende Leben als rote Punkte oben links."""
    for i in range(n):
        hw.set(i, 0, gfx.SHIRT)


def game_over():
    hw.clear(gfx.SHIRT)
    hw.pause(150)
    gfx.draw(GAME_OVER)
    hw.fade(300, 0, 100)
    hw.pause(1500)
    hw.fade(400, 100, 0)


def fireworks(bg, spots=((1, 3), (3, 3), (5, 3)), rounds=2):
    """Kleines Siegesfeuerwerk ueber dem Hintergrundbild bg (64er-Liste)."""
    colors = (gfx.GOLD, gfx.SHIRT, gfx.POISON, gfx.SKY, gfx.LEAF, gfx.WHITE)
    launches = []
    for r in range(rounds):
        for i in range(len(spots)):
            x, y = spots[i]
            launches.append([r * 1500 + i * 380, x, y, colors[(r * len(spots) + i) % len(colors)]])
    end = launches[-1][0] + 1500
    rockets = []    # [x, y, ziel_y, farbe]
    sparks = []     # [x, y, vx, vy, lebensdauer, farbe]
    t = 0
    while t < end:
        dt = hw.tick()
        hw.poll()
        t += dt
        while launches and launches[0][0] <= t:
            _, x, y, c = launches.pop(0)
            rockets.append([x, 7.0, y, c])
        for r in rockets[:]:
            r[1] -= dt / 70
            if r[1] <= r[2]:
                rockets.remove(r)
                for vx in (-1, 0, 1):
                    for vy in (-1, 0, 1):
                        sparks.append([r[0] + 0.5, r[2] + 0.5, vx / 140, vy / 140, 700, r[3]])
        for s in sparks[:]:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += dt / 9000          # Schwerkraft
            s[4] -= dt
            if s[4] <= 0:
                sparks.remove(s)
        hw.blit(bg)
        for r in rockets:
            hw.set(r[0], int(r[1] + 0.5), gfx.GOLD)
        for s in sparks:
            x, y = int(s[0]), int(s[1])
            if 0 <= x < 8 and 0 <= y < 8:
                hw.set(x, y, gfx.mix(bg[y * 8 + x], s[5], s[4] * 100 // 700))
        hw.show()
