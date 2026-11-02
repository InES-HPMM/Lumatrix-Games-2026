# Level-Editor fuer Angry Birds auf der Lumatrix (laeuft auf dem PC)
#
# Linksklick  -> gewaehltes Objekt setzen (gedrueckt halten = malen)
# Rechtsklick -> Feld leeren
# "Pruefen"   -> rechnet aus, ob das Level schaffbar ist (wie check_levels.py)
# "Speichern" -> schreibt levels.py neu, par wird automatisch berechnet

import os
import threading
import tkinter as tk
from tkinter import messagebox

import check_levels as cl          # bringt die Pico-Attrappen und main mit

game = cl.game
LEVEL_FILE = os.path.join(cl.GAME_DIR, "levels.py")
MAX_LEVELS = 9                     # das Menue zeigt nur eine Ziffer

HEADER = '''# Levels fuer Angry Birds auf der Lumatrix
#
# Diese Datei kann von editor.py neu geschrieben werden.
#
# birds: Reihenfolge der Voegel
#   R = Rot, Y = Gelb (durchschlaegt 2 Bloecke), B = Bombe (3x3)
# objs:  (x, y, Typ), x=0 links, y=0 unten, Spalten 0-2 frei lassen
#   W = Holz, S = Stein (2 Treffer), G = Glas (zerbricht beim Fallen
#   oder wenn etwas darauf landet), T = TNT (explodiert 3x3),
#   F = Plattform (schwebt, unzerstoerbar), P = Schwein
# par:   kleinste Anzahl Voegel fuer den Sieg (= 3 Sterne),
#        wird von check_levels.py berechnet und geprueft

'''

TOOLS = [("W", "Holz"), ("S", "Stein"), ("G", "Glas"), ("T", "TNT"),
         ("F", "Plattform"), ("P", "Schwein")]
RESERVED = {game.START, game.SLING_POS}
CELL = 52
PAD = 12


def to_screen(c):
    r, g, b = (int(255 * (v / 255) ** 0.4) if v else 0 for v in c)
    return "#%02x%02x%02x" % (r, g, b)


def format_levels(levels):
    lines = ["LEVELS = ["]
    for lv in levels:
        lines.append('    {"birds": "%s", "par": %d,' % (lv["birds"], lv["par"]))
        objs = sorted(lv["objs"], key=lambda o: (o[1], o[0]))
        parts = ['(%d, %d, "%s")' % o for o in objs]
        rows = [", ".join(parts[i:i + 4]) for i in range(0, len(parts), 4)]
        body = ",\n              ".join(rows)
        lines.append('     "objs": [%s]},' % body)
    lines.append("]")
    return HEADER + "\n".join(lines) + "\n"


class Editor:
    def __init__(self, root):
        self.root = root
        self.levels = [dict(lv) for lv in game.LEVELS]
        self.objs = {}
        self.tool = tk.StringVar(value="W")
        self.birds = tk.StringVar(value="RRR")
        self.current = tk.IntVar(value=1)
        self.busy = False

        root.title("Lumatrix Level-Editor")
        root.configure(bg="#111")
        size = 8 * CELL + 2 * PAD
        self.canvas = tk.Canvas(root, width=size, height=size, bg="#0b0b0b",
                                highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=20, padx=8, pady=8)
        self.cells = {}
        for x in range(8):
            for y in range(8):
                sx, sy = PAD + x * CELL, PAD + (7 - y) * CELL
                self.cells[(x, y)] = self.canvas.create_rectangle(
                    sx + 3, sy + 3, sx + CELL - 3, sy + CELL - 3,
                    fill="#1a1a1a", outline="#262626")
        for b in ("<Button-1>", "<B1-Motion>"):
            self.canvas.bind(b, lambda e: self.paint(e, self.tool.get()))
        for b in ("<Button-3>", "<B3-Motion>"):
            self.canvas.bind(b, lambda e: self.paint(e, None))

        side = dict(bg="#111", fg="#ddd", font=("Segoe UI", 10))
        r = 0
        tk.Label(root, text="Objekt", **side).grid(row=r, column=1, sticky="w")
        r += 1
        for k, name in TOOLS:
            tk.Radiobutton(root, text=name, value=k, variable=self.tool,
                           selectcolor="#333", activebackground="#111",
                           fg=to_screen(game.color_of(k, game.HP[k])),
                           bg="#111", font=("Segoe UI", 10)).grid(
                row=r, column=1, sticky="w")
            r += 1
        tk.Label(root, text="Voegel (R/Y/B)", **side).grid(
            row=r, column=1, sticky="w", pady=(10, 0))
        r += 1
        tk.Entry(root, textvariable=self.birds, width=10).grid(
            row=r, column=1, sticky="w")
        r += 1
        tk.Label(root, text="Level", **side).grid(
            row=r, column=1, sticky="w", pady=(10, 0))
        r += 1
        self.spin = tk.Spinbox(root, from_=1, to=len(self.levels),
                               textvariable=self.current, width=5,
                               command=self.load)
        self.spin.grid(row=r, column=1, sticky="w")
        r += 1
        for text, cmd in (("Pruefen", self.check),
                          ("Speichern (ueberschreiben)", self.save),
                          ("Als neues Level anhaengen", self.append),
                          ("Feld leeren", self.clear)):
            tk.Button(root, text=text, command=cmd, width=24).grid(
                row=r, column=1, sticky="w", pady=2)
            r += 1
        self.info = tk.Label(root, text="", justify="left", wraplength=260,
                             **side)
        self.info.grid(row=r, column=1, sticky="nw", pady=(10, 0))
        self.load()

    # -----------------------------------------------------------
    def paint(self, e, kind):
        x = (e.x - PAD) // CELL
        y = 7 - (e.y - PAD) // CELL
        if not (0 <= x < 8 and 0 <= y < 8) or (x, y) in RESERVED:
            return
        if kind is None:
            self.objs.pop((x, y), None)
        else:
            self.objs[(x, y)] = kind
        self.redraw()

    def redraw(self):
        for c, item in self.cells.items():
            if c == game.SLING_POS:
                col = to_screen(game.SLING)
            elif c == game.START:
                col = to_screen(game.BIRD_COLORS["R"])
            elif c in self.objs:
                k = self.objs[c]
                col = to_screen(game.color_of(k, game.HP[k]))
            else:
                col = "#1a1a1a"
            self.canvas.itemconfigure(item, fill=col)

    def load(self):
        n = self.current.get()
        if not 1 <= n <= len(self.levels):
            return
        lv = self.levels[n - 1]
        self.objs = {(x, y): k for x, y, k in lv["objs"]}
        self.birds.set(lv["birds"])
        self.info.configure(text="Level %d geladen." % n, fg="#ddd")
        self.redraw()

    def clear(self):
        self.objs = {}
        self.redraw()

    def level(self):
        birds = self.birds.get().strip().upper()
        if not birds or any(b not in "RYB" for b in birds):
            messagebox.showerror("Voegel", "Nur R, Y und B erlaubt.")
            return None
        if "P" not in self.objs.values():
            messagebox.showerror("Schweine", "Mindestens ein Schwein setzen.")
            return None
        objs = [(x, y, k) for (x, y), k in self.objs.items()]
        return {"birds": birds, "par": 1, "objs": objs}

    # -----------------------------------------------------------
    def run_solver(self, lv, done):
        # Loeser im Hintergrund, damit das Fenster nicht einfriert
        if self.busy:
            return
        self.busy = True
        self.info.configure(text="Rechne ...", fg="#ddd")

        def work():
            r = cl.solve(lv)
            self.root.after(0, lambda: self.finish(lv, r, done))

        threading.Thread(target=work, daemon=True).start()

    def finish(self, lv, r, done):
        self.busy = False
        if r["min_birds"] is None:
            self.info.configure(text="UNSCHAFFBAR mit diesen Voegeln.",
                                fg="#f66")
        else:
            ex = ", ".join("%s %d Grad Kraft %.2f" % s for s in r["example"])
            self.info.configure(
                fg="#8f8",
                text="Schaffbar. Mindestens %d Vogel/Voegel (= par)\n"
                     "Zufallschance: %.1f %%\n"
                     "1. Schuss trifft: %d %%\nz.B. %s"
                     % (r["min_birds"], r["luck"],
                        100 * r["first_hits"] // r["shots"], ex))
        if done:
            done(r)

    def check(self):
        lv = self.level()
        if lv:
            self.run_solver(lv, None)

    def save(self):
        self.store(self.current.get() - 1)

    def append(self):
        if len(self.levels) >= MAX_LEVELS:
            messagebox.showerror("Zu viele Levels",
                                 "Maximal %d Levels moeglich." % MAX_LEVELS)
            return
        self.store(len(self.levels))

    def store(self, pos):
        lv = self.level()
        if not lv:
            return

        def done(r):
            if r["min_birds"] is None and not messagebox.askyesno(
                    "Unschaffbar", "Das Level ist unschaffbar. "
                                   "Trotzdem speichern?"):
                return
            lv["par"] = r["min_birds"] or len(lv["birds"])
            if pos < len(self.levels):
                self.levels[pos] = lv
            else:
                self.levels.append(lv)
            with open(LEVEL_FILE, "w", encoding="utf-8") as f:
                f.write(format_levels(self.levels))
            self.spin.configure(to=len(self.levels))
            self.current.set(pos + 1)
            self.info.configure(text=self.info.cget("text")
                                + "\n\nGespeichert als Level %d." % (pos + 1))

        self.run_solver(lv, done)


if __name__ == "__main__":
    root = tk.Tk()
    Editor(root)
    root.mainloop()
