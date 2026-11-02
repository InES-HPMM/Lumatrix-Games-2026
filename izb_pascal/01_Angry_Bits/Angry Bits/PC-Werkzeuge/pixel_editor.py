# Pixel-Editor fuer die Lumatrix (laeuft auf dem PC)
#
# Jeden der 64 Pixel einzeln einfaerben und als Grafik mit Namen speichern.
# Gespeichert wird in grafiken.json im Spielordner.
#
# Linksklick     -> Pixel mit der gewaehlten Farbe malen (halten = malen)
# Rechtsklick    -> Pixel ausschalten
# Mittlere Taste -> Farbe eines Pixels aufnehmen (Pipette)
# Farben sind LED-Werte 0-40, wie im Spiel (main.py)

import json
import os
import time
import tkinter as tk
from tkinter import messagebox

import check_levels as cl          # bringt die Pico-Attrappen und main mit

game = cl.game
HERE = os.path.dirname(os.path.abspath(__file__))
GRAPHICS_FILE = os.path.join(HERE, "grafiken.json")
CELL = 52
PAD = 12
MAX = 40                           # hoechster Farbwert im Spiel
OFF = (0, 0, 0)

PALETTE = [("Rot", game.RED), ("Weiss", game.WHITE),
           ("Grau (Stein)", game.STONE), ("Dunkelgrau", game.STONE_CRACKED),
           ("Holz", game.WOOD), ("Glas", game.GLASS), ("Gruen", game.GREEN),
           ("Gelb", game.STAR), ("Orange", game.ORANGE), ("Blau", (0, 0, 40)),
           ("Pink (TNT)", game.TNT), ("Lila", (10, 0, 35))]


def to_screen(c):
    # Echte LEDs leuchten schon bei kleinen Werten hell -> aufhellen
    if not any(c):
        return "#1a1a1a"
    r, g, b = (int(255 * (v / 255) ** 0.4) if v else 0 for v in c)
    return "#%02x%02x%02x" % (r, g, b)


def icon_to_pixels(icon, colors):
    # Spiel-Bild (Zeichen pro Pixel) -> 8x8 Farben, oberste Zeile zuerst
    return [[tuple(colors.get(ch, OFF)) for ch in line] for line in icon]


def load_graphics():
    try:
        with open(GRAPHICS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {name: [[tuple(p) for p in row] for row in g["pixels"]]
            for name, g in data.get("grafiken", {}).items()}


def save_graphics(graphics):
    # Von Hand formatiert: eine Pixelzeile pro Textzeile, gut lesbar
    info = ("8x8 Grafiken fuer die Lumatrix. pixels = 8 Zeilen, "
            "oberste Zeile zuerst, je 8 Farben [R, G, B] (0-40).")
    items = sorted(graphics.items())
    lines = ["{", ' "_info": %s,' % json.dumps(info), ' "grafiken": {']
    for i, (name, pixels) in enumerate(items):
        rows = ",\n".join("   " + json.dumps([list(p) for p in row])
                          for row in pixels)
        comma = "," if i < len(items) - 1 else ""
        lines.append('  %s: {"pixels": [\n%s]}%s'
                     % (json.dumps(name), rows, comma))
    lines += [" }", "}"]
    with open(GRAPHICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


TEMPLATES = {
    "[Spiel] Muelleimer": icon_to_pixels(game.TRASH_ICON, game.TRASH_COLORS),
    "[Spiel] Vogel": icon_to_pixels(game.BIRD_ICON, game.ICON_COLORS),
}


class PixelEditor:
    def __init__(self, root):
        self.root = root
        self.pixels = [[OFF] * 8 for _ in range(8)]
        self.graphics = load_graphics()
        self.color = game.RED
        self.mirror = tk.BooleanVar(value=False)
        self.name = tk.StringVar()

        root.title("Lumatrix Pixel-Editor")
        root.configure(bg="#111")
        side = dict(bg="#111", fg="#ddd", font=("Segoe UI", 10))

        size = 8 * CELL + 2 * PAD
        self.canvas = tk.Canvas(root, width=size, height=size, bg="#0b0b0b",
                                highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=30, padx=8, pady=8)
        self.cells = {}
        for row in range(8):
            for x in range(8):
                sx, sy = PAD + x * CELL, PAD + row * CELL
                self.cells[(x, row)] = self.canvas.create_oval(
                    sx + 5, sy + 5, sx + CELL - 5, sy + CELL - 5,
                    fill="#1a1a1a", outline="#262626")
        for b in ("<Button-1>", "<B1-Motion>"):
            self.canvas.bind(b, lambda e: self.paint(e, self.color))
        for b in ("<Button-3>", "<B3-Motion>"):
            self.canvas.bind(b, lambda e: self.paint(e, OFF))
        self.canvas.bind("<Button-2>", self.pick)

        # Palette
        r = 0
        tk.Label(root, text="Farbe", **side).grid(row=r, column=1,
                                                  columnspan=2, sticky="w")
        r += 1
        pal = tk.Frame(root, bg="#111")
        pal.grid(row=r, column=1, columnspan=2, sticky="w")
        for i, (label, col) in enumerate(PALETTE):
            tk.Button(pal, bg=to_screen(col), activebackground=to_screen(col),
                      width=3, relief="flat",
                      command=lambda c=col: self.set_color(c)).grid(
                row=i // 6, column=i % 6, padx=2, pady=2)
        r += 1

        # Eigene Farbe als LED-Werte
        self.rgb = [tk.IntVar(value=v) for v in self.color]
        for i, ch in enumerate("RGB"):
            tk.Scale(root, label=ch, from_=0, to=MAX, orient="horizontal",
                     variable=self.rgb[i], length=180, bg="#111", fg="#ddd",
                     highlightthickness=0, command=lambda v: self.from_sliders()
                     ).grid(row=r, column=1, columnspan=2, sticky="w")
            r += 1
        self.swatch = tk.Label(root, text="  aktuelle Farbe  ", **side)
        self.swatch.grid(row=r, column=1, columnspan=2, sticky="w", pady=4)
        r += 1
        tk.Checkbutton(root, text="Symmetrisch malen (links = rechts)",
                       variable=self.mirror, selectcolor="#333",
                       activebackground="#111", **side).grid(
            row=r, column=1, columnspan=2, sticky="w")
        r += 1
        tk.Button(root, text="Alles leeren", width=24,
                  command=self.clear).grid(row=r, column=1, columnspan=2,
                                           sticky="w", pady=(4, 10))
        r += 1

        # Speichern und Laden
        tk.Label(root, text="Name der Grafik", **side).grid(
            row=r, column=1, columnspan=2, sticky="w")
        r += 1
        tk.Entry(root, textvariable=self.name, width=27).grid(
            row=r, column=1, columnspan=2, sticky="w")
        r += 1
        tk.Button(root, text="Speichern", width=24, command=self.save).grid(
            row=r, column=1, columnspan=2, sticky="w", pady=2)
        r += 1
        tk.Label(root, text="Gespeicherte Grafiken und Vorlagen",
                 **side).grid(row=r, column=1, columnspan=2, sticky="w",
                              pady=(10, 0))
        r += 1
        self.listbox = tk.Listbox(root, width=30, height=8, bg="#1a1a1a",
                                  fg="#ddd", selectbackground="#444")
        self.listbox.grid(row=r, column=1, columnspan=2, sticky="w")
        self.listbox.bind("<Double-Button-1>", lambda e: self.load())
        r += 1
        tk.Button(root, text="Laden", width=11, command=self.load).grid(
            row=r, column=1, sticky="w", pady=2)
        tk.Button(root, text="Loeschen", width=11, command=self.delete).grid(
            row=r, column=2, sticky="w", pady=2)
        r += 1
        self.status = tk.Label(root, text="", wraplength=240, justify="left",
                               **side)
        self.status.grid(row=r, column=1, columnspan=2, sticky="nw", pady=6)

        self.set_color(self.color)
        self.refresh_list()
        self.redraw()

    # -----------------------------------------------------------
    def set_color(self, c):
        self.color = tuple(c)
        for i in range(3):
            self.rgb[i].set(self.color[i])
        self.swatch.configure(bg=to_screen(self.color),
                              fg="#000" if any(self.color) else "#ddd")

    def from_sliders(self):
        self.color = tuple(v.get() for v in self.rgb)
        self.swatch.configure(bg=to_screen(self.color),
                              fg="#000" if any(self.color) else "#ddd")

    def cell_at(self, e):
        x, row = (e.x - PAD) // CELL, (e.y - PAD) // CELL
        if 0 <= x < 8 and 0 <= row < 8:
            return x, row
        return None

    def paint(self, e, color):
        c = self.cell_at(e)
        if not c:
            return
        x, row = c
        self.pixels[row][x] = tuple(color)
        if self.mirror.get():
            self.pixels[row][7 - x] = tuple(color)
        self.redraw()

    def pick(self, e):
        c = self.cell_at(e)
        if c and any(self.pixels[c[1]][c[0]]):
            self.set_color(self.pixels[c[1]][c[0]])

    def clear(self):
        self.pixels = [[OFF] * 8 for _ in range(8)]
        self.redraw()

    def redraw(self):
        for (x, row), item in self.cells.items():
            self.canvas.itemconfigure(item, fill=to_screen(self.pixels[row][x]))

    # -----------------------------------------------------------
    def refresh_list(self):
        self.listbox.delete(0, "end")
        for name in sorted(self.graphics):
            self.listbox.insert("end", name)
        for name in TEMPLATES:
            self.listbox.insert("end", name)

    def selected(self):
        sel = self.listbox.curselection()
        return self.listbox.get(sel[0]) if sel else None

    def save(self):
        name = self.name.get().strip()
        if not name or name.startswith("["):
            messagebox.showerror("Name", "Bitte einen Namen eingeben "
                                         "(nicht mit [ beginnen).")
            return
        if name in self.graphics and not messagebox.askyesno(
                "Ueberschreiben", "'%s' gibt es schon. Ueberschreiben?" % name):
            return
        self.graphics[name] = [list(row) for row in self.pixels]
        save_graphics(self.graphics)
        self.refresh_list()
        self.status.configure(text="Gespeichert: '%s' (%s)"
                              % (name, time.strftime("%H:%M")), fg="#8f8")

    def load(self):
        name = self.selected()
        if not name:
            return
        src = TEMPLATES.get(name) or self.graphics[name]
        self.pixels = [list(row) for row in src]
        if not name.startswith("["):
            self.name.set(name)
        self.status.configure(text="Geladen: '%s'" % name, fg="#ddd")
        self.redraw()

    def delete(self):
        name = self.selected()
        if not name or name.startswith("["):
            return
        if messagebox.askyesno("Loeschen", "'%s' loeschen?" % name):
            del self.graphics[name]
            save_graphics(self.graphics)
            self.refresh_list()
            self.status.configure(text="Geloescht: '%s'" % name, fg="#ddd")


if __name__ == "__main__":
    root = tk.Tk()
    PixelEditor(root)
    root.mainloop()
