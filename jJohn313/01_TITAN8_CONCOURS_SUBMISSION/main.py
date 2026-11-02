"""
TITAN 8 Main Game Loop & Renderer (main.py)
Deterministic Turn-Based Tactical Micro-Roguelike on 8x8 WS2812B / RP2040
"""

import time
import config
from hardware import (
    Display,
    InputHandler,
    CMD_UP,
    CMD_DOWN,
    CMD_LEFT,
    CMD_RIGHT,
    CMD_PASS,
    CMD_UNDO,
    CMD_RESET_LVL,
    CMD_RESET_GAME,
    CMD_RESET,
    CMD_NONE
)
from engine import (
    TitanEngine,
    LEVELS,
    STAGE_PLANNING,
    STAGE_PLAYER_MOVED,
    STAGE_RESOLVING,
    STATE_PLAYING,
    STATE_VICTORY,
    STATE_DEFEAT,
    STATE_GAME_WON,
    TYPE_DASHER,
    TYPE_MORTAR,
    TYPE_STRIKER,
    TYPE_MOUNTAIN
)

def render(display, engine, pulse_phase):
    """Renders current board state and telegraphed threat vectors onto the 8x8 matrix display."""
    display.clear()

    # 1. Render Mountains / Obstacles
    for (mx, my) in engine.mountains:
        display.set_pixel(mx, my, config.COLOR_WALL)

    # 2. Render Telegraphed Attack Vectors (Bleed-reduced, breathing)
    # Gentle 1.5 Hz breathing cycle (26 frames at 25ms/frame) between (6,0,0) and (16,0,0)
    d_phase = (pulse_phase % 26) / 26.0
    d_wave = 2.0 * d_phase if d_phase < 0.5 else 2.0 * (1.0 - d_phase)
    d_r = int(6 + 10 * d_wave)
    faint_dasher = (d_r, 0, 0)

    # Slow pulsing Mortar marker between (30,0,30) and (70,0,70) on ONLY the target tile
    m_phase = (pulse_phase % 40) / 40.0
    m_wave = 2.0 * m_phase if m_phase < 0.5 else 2.0 * (1.0 - m_phase)
    m_val = int(30 + 40 * m_wave)
    faint_mortar = (m_val, 0, m_val)

    # Faint Amber Striker trace
    s_r = int(12 + 14 * d_wave)
    s_g = int(6 + 7 * d_wave)
    faint_striker = (s_r, s_g, 0)

    for enemy in engine.enemies:
        if enemy["hp"] <= 0:
            continue
        e_type = enemy["type"]
        if e_type == TYPE_DASHER:
            trace_col = faint_dasher
        elif e_type == TYPE_MORTAR:
            trace_col = faint_mortar
        else:
            trace_col = faint_striker

        for (tx, ty) in enemy["target_tiles"]:
            display.blend_pixel(tx, ty, trace_col)

    # 3. Render Enemies (Solid, saturated colors)
    for enemy in engine.enemies:
        if enemy["hp"] > 0:
            ex, ey = enemy["pos"]
            e_type = enemy["type"]
            if e_type == TYPE_DASHER:
                color = config.COLOR_ENEMY_DASHER  # Solid saturated Crimson (255, 20, 0)
            elif e_type == TYPE_MORTAR:
                color = config.COLOR_ENEMY_MORTAR  # Vivid Magenta (220, 0, 220)
            else:
                color = config.COLOR_ENEMY_STRIKER # Amber (255, 130, 0)
            display.set_pixel(ex, ey, color)

    # 4. Render Player (ALWAYS on top so player is never masked)
    px, py = engine.player_pos
    if engine.player_hp >= 2:
        # Full health: Steady saturated Cyan (0, 220, 255) with subtle idle breath
        p_breath = 0.90 + 0.10 * d_wave
        p_color = (0, int(220 * p_breath), int(255 * p_breath))
    else:
        # 1 HP: Emergency Strobe Mode (4 Hz alternating between Cyan and Warning Amber)
        is_alert_frame = ((pulse_phase // 5) % 2) == 1
        p_color = config.COLOR_PLAYER_ALERT if is_alert_frame else config.COLOR_PLAYER_CYAN
    display.set_pixel(px, py, p_color)

    display.show()


class VisualAnimator:
    """Handles kinetic animations and physical feedback during turn resolution."""
    def __init__(self, display, engine):
        self.display = display
        self.engine = engine

    def render_frame(self, pulse_phase=0):
        render(self.display, self.engine, pulse_phase)

    def on_shove_slide(self, chain, dx, dy):
        """Intermediate motion frame (40ms) when entity is shoved into empty tile."""
        render(self.display, self.engine, 0)
        for (ox, oy, o_type, o_obj) in chain:
            nx, ny = ox + dx, oy + dy
            if o_type == TYPE_MOUNTAIN:
                c = config.COLOR_WALL
            elif o_type == TYPE_DASHER:
                c = config.COLOR_ENEMY_DASHER
            elif o_type == TYPE_MORTAR:
                c = config.COLOR_ENEMY_MORTAR
            else:
                c = config.COLOR_ENEMY_STRIKER
            half_c = (c[0] // 2, c[1] // 2, c[2] // 2)
            self.display.set_pixel(ox, oy, half_c)
            self.display.set_pixel(nx, ny, half_c)
        self.display.show()
        time.sleep_ms(config.SLIDE_DELAY_MS)

    def on_collision(self, impact_coords):
        """Hit-stop white flash (45ms) followed by faint red micro-shake (25ms)."""
        if not impact_coords:
            return
        # 1. Hit-Stop & Flash
        self.display.flash_cells(impact_coords, config.COLOR_IMPACT, config.HITSTOP_MS)
        # 2. Micro-Shake shockwave
        self.display.screen_shockwave(config.COLOR_SHOCKWAVE, config.SHAKE_MS)
        self.render_frame()

    def on_dasher_step(self, step_impacts):
        """Renders 1 step of Dasher charge (30ms per tile), or collision impact."""
        self.render_frame()
        if step_impacts:
            self.on_collision(step_impacts)
        else:
            time.sleep_ms(config.STEP_DELAY_MS)

    def on_mortar_lob(self, origin, target):
        """4-5 frame ballistic flight arc, detonation flash, and cross expansion."""
        x0, y0 = origin
        x1, y1 = target
        steps = 5
        c_start = config.COLOR_MORTAR_LOB_START
        c_apex  = config.COLOR_MORTAR_LOB_APEX
        c_end   = config.COLOR_MORTAR_LOB_END

        # 1. Flight sequence
        for i in range(1, steps + 1):
            t = i / (steps + 1)
            fx = round(x0 + t * (x1 - x0))
            fy = round(y0 + t * (y1 - y0))
            if t <= 0.5:
                sub_t = t / 0.5
                r = int(c_start[0] + sub_t * (c_apex[0] - c_start[0]))
                g = int(c_start[1] + sub_t * (c_apex[1] - c_start[1]))
                b = int(c_start[2] + sub_t * (c_apex[2] - c_start[2]))
            else:
                sub_t = (t - 0.5) / 0.5
                r = int(c_apex[0] + sub_t * (c_end[0] - c_apex[0]))
                g = int(c_apex[1] + sub_t * (c_end[1] - c_apex[1]))
                b = int(c_apex[2] + sub_t * (c_end[2] - c_apex[2]))

            self.render_frame()
            self.display.set_pixel(fx, fy, (r, g, b))
            self.display.show()
            time.sleep_ms(config.STEP_DELAY_MS)

        # 2. Detonation flash (40ms)
        self.display.flash_cells([(x1, y1)], config.COLOR_IMPACT, config.DETONATION_MS)

        # 3. 1-frame cross expansion in magenta at 30% brightness (40ms)
        cross = []
        for (cx, cy) in [(x1 - 1, y1), (x1 + 1, y1), (x1, y1 - 1), (x1, y1 + 1)]:
            if 0 <= cx < 8 and 0 <= cy < 8:
                cross.append((cx, cy))
        if cross:
            self.display.flash_cells(cross, config.COLOR_MORTAR_CROSS, config.CROSS_EXPAND_MS)

        self.render_frame()

    def on_striker_strike(self, origin, target):
        """Target cell flashes bright amber for 40ms."""
        self.display.flash_cells([target], (255, 180, 0), config.DETONATION_MS)
        self.render_frame()

def render_green_wipe(display):
    """Concentric expanding diamond + green wipe on level victory."""
    rings = [
        [(3, 3), (3, 4), (4, 3), (4, 4)],
        [(2, 3), (2, 4), (3, 2), (3, 5), (4, 2), (4, 5), (5, 3), (5, 4)],
        [(1, 3), (1, 4), (3, 1), (3, 6), (4, 1), (4, 6), (6, 3), (6, 4)],
    ]
    for ring in rings:
        for (x, y) in ring:
            display.set_pixel(x, y, config.COLOR_VICTORY)
        display.show()
        time.sleep_ms(35)

    for col in range(8):
        for row in range(8):
            display.set_pixel(col, row, config.COLOR_VICTORY)
        display.show()
        time.sleep_ms(25)
    time.sleep_ms(120)
    display.clear()
    display.show()

def render_red_wipe(display):
    """Red collapsing wipe animation on defeat."""
    for col in range(4):
        for row in range(8):
            display.set_pixel(col, row, config.COLOR_GAME_OVER)
            display.set_pixel(7 - col, row, config.COLOR_GAME_OVER)
        display.show()
        time.sleep_ms(40)
    time.sleep_ms(140)
    display.clear()
    display.show()

# Trophy pixel pattern for Grand Campaign Victory
TROPHY_PIXELS = [
    (2, 1), (3, 1), (4, 1), (5, 1),
    (1, 2), (6, 2),
    (2, 3), (3, 3), (4, 3), (5, 3),
    (1, 4), (6, 4),
    (2, 5), (3, 5), (4, 5), (5, 5),
    (3, 6), (4, 6),
    (2, 7), (3, 7), (4, 7), (5, 7),
]

def play_campaign_victory_ceremony(display):
    """Grand celebration ceremony when Level 8 is beaten."""
    rainbow_colors = [
        (255, 0, 0),
        (255, 130, 0),
        (255, 220, 0),
        (0, 255, 60),
        (0, 180, 255),
        (130, 0, 255),
        (255, 0, 200),
    ]
    rings = [
        [(3, 3), (3, 4), (4, 3), (4, 4)],
        [(2, 2), (2, 3), (2, 4), (2, 5), (5, 2), (5, 3), (5, 4), (5, 5),
         (3, 2), (4, 2), (3, 5), (4, 5)],
        [(1, 1), (1, 6), (6, 1), (6, 6), (1, 2), (1, 3), (1, 4), (1, 5),
         (6, 2), (6, 3), (6, 4), (6, 5), (2, 1), (3, 1), (4, 1), (5, 1),
         (2, 6), (3, 6), (4, 6), (5, 6)],
        [(0, 0), (0, 7), (7, 0), (7, 7)]
    ]

    # 1. Concentric rainbow shockwaves
    for cycle in range(3):
        for r_idx, ring in enumerate(rings):
            display.clear()
            c = rainbow_colors[(cycle * 2 + r_idx) % len(rainbow_colors)]
            for (rx, ry) in ring:
                display.set_pixel(rx, ry, c)
            display.show()
            time.sleep_ms(50)

    # 2. Firework bursts
    firework_centers = [(2, 2), (5, 3), (2, 5), (5, 2), (3, 4)]
    for (fcx, fcy) in firework_centers:
        display.clear()
        display.set_pixel(fcx, fcy, (255, 255, 255))
        display.show()
        time.sleep_ms(40)
        display.clear()
        sparks = [(fcx - 1, fcy), (fcx + 1, fcy), (fcx, fcy - 1), (fcx, fcy + 1)]
        color = rainbow_colors[(fcx * 3 + fcy * 5) % len(rainbow_colors)]
        for (sx, sy) in sparks:
            if 0 <= sx < 8 and 0 <= sy < 8:
                display.set_pixel(sx, sy, color)
        display.show()
        time.sleep_ms(60)

    display.clear()
    display.show()
    time.sleep_ms(100)

def render_game_won_fanfare(display, phase):
    """Ambient celebration display: Glowing golden trophy with rainbow-shimmering corners."""
    display.clear()
    gold_mod = 0.75 + 0.25 * ((phase % 10) / 10.0)
    trophy_color = (int(255 * gold_mod), int(210 * gold_mod), 0)
    for (tx, ty) in TROPHY_PIXELS:
        display.set_pixel(tx, ty, trophy_color)

    # Shimmering victory corners
    corners = [(0, 0), (7, 0), (0, 7), (7, 7)]
    for idx, (cx, cy) in enumerate(corners):
        sparkle = ((phase + idx * 3) % 12) / 12.0
        if sparkle > 0.65:
            display.set_pixel(cx, cy, (int(80 * sparkle), int(240 * sparkle), int(220 * sparkle)))
    display.show()


def main():
    print("=" * 50)
    print("TITAN 8 — 8x8 Deterministic Tactical Micro-Roguelike")
    print("Hardware: Lumatrix RP2040 (WS2812B + 5-Way Nav + GPIO 9 Undo)")
    print("=" * 50)

    display = Display()
    inputs = InputHandler()
    engine = TitanEngine(current_level=0)
    animator = VisualAnimator(display, engine)

    pulse_counter = 0

    # Intro power-on flash
    display.flash(config.COLOR_PLAYER_FULL, duration_ms=180)

    while True:
        cmd = inputs.poll()

        # Level Reset Trigger (Center hold ~1s)
        if cmd == CMD_RESET_LVL:
            print(f"[Command] Reset Level {engine.current_level + 1}")
            display.flash(config.COLOR_IMPACT, duration_ms=100)
            engine.restart_level()
            animator.engine = engine
            time.sleep_ms(100)
            continue

        # Campaign Reset to Level 1 Trigger (Center hold >2s OR GPIO 9 hold >1.2s)
        if cmd == CMD_RESET_GAME:
            print("[Command] Resetting Campaign back to Level 1!")
            display.flash(config.COLOR_PORTAL, duration_ms=250)
            engine.load_level(0)
            animator.engine = engine
            time.sleep_ms(150)
            continue

        # =========================================================
        # 1. PLAYING STATE
        # =========================================================
        if engine.state == STATE_PLAYING:
            # GPIO 9: Lever flick on the back
            if cmd == CMD_UNDO:
                if engine.has_moved:
                    print("[Action] UNDO Move")
                    engine.restore_snapshot()
                    animator.engine = engine
                    display.flash(config.COLOR_CURSOR, duration_ms=60)
                else:
                    print(f"[Action] Lever flip at turn start -> Reset Level {engine.current_level + 1}")
                    display.flash(config.COLOR_IMPACT, duration_ms=100)
                    engine.restart_level()
                    animator.engine = engine
                continue

            # Tilt Directions (UP / DOWN / LEFT / RIGHT)
            dx, dy = 0, 0
            if cmd == CMD_UP:
                dy = 1
            elif cmd == CMD_DOWN:
                dy = -1
            elif cmd == CMD_LEFT:
                dx = -1
            elif cmd == CMD_RIGHT:
                dx = 1

            if dx != 0 or dy != 0:
                tx = engine.player_pos[0] + dx
                ty = engine.player_pos[1] + dy

                if engine.is_in_bounds(tx, ty):
                    ent_type, _ = engine.get_entity_at(tx, ty)

                    if ent_type is not None:
                        # Adjacent entity (Enemy or Mountain) -> SHOVE ACTION!
                        print(f"[Action] SHOVE at ({tx},{ty}) in dir ({dx},{dy})")
                        engine.take_player_shove(dx, dy, animator=animator)

                    elif not engine.has_moved:
                        # Empty tile & has not moved -> STEP 1 TILE
                        print(f"[Move] Player step to ({tx},{ty})")
                        engine.take_player_move(dx, dy)

            # Center Click: PASS / WAIT ACTION
            elif cmd == CMD_PASS:
                print("[Action] PASS / WAIT")
                engine.take_player_pass(animator=animator)

            # Check if resolution triggered level win/loss
            if engine.state == STATE_VICTORY:
                print(f"[Victory] Cleared Level {engine.current_level + 1}: {LEVELS[engine.current_level]['name']}")
                render_green_wipe(display)
                engine.next_level()
                animator.engine = engine
                if engine.state == STATE_GAME_WON:
                    print("[Campaign Victory] All 8 Levels Cleared!")
                    play_campaign_victory_ceremony(display)
                time.sleep_ms(200)
                continue

            elif engine.state == STATE_DEFEAT:
                print(f"[Defeat] Fallen on Level {engine.current_level + 1}. Reloading...")
                render_red_wipe(display)
                engine.restart_level()
                animator.engine = engine
                time.sleep_ms(200)
                continue

            render(display, engine, pulse_counter)

        # =========================================================
        # 2. CAMPAIGN CLEARED STATE (ALL 8 LEVELS WON)
        # =========================================================
        elif engine.state == STATE_GAME_WON:
            render_game_won_fanfare(display, pulse_counter)
            if cmd in (CMD_PASS, CMD_RESET, CMD_UP, CMD_DOWN, CMD_LEFT, CMD_RIGHT):
                print("[Restart] Restarting campaign from Level 1")
                engine.load_level(0)
                animator.engine = engine
                time.sleep_ms(200)

        pulse_counter = (pulse_counter + 1) % 100
        time.sleep_ms(25)

import sys
try:
    from hardware import ON_HARDWARE
except ImportError:
    ON_HARDWARE = False

if ON_HARDWARE or __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        d = Display()
        d.clear()
        d.show()
        print("\nTITAN 8 stopped.")
    except Exception as e:
        d = Display()
        d.clear()
        d.show()
        print("\nCRITICAL EXCEPTION IN MAIN:")
        if hasattr(sys, "print_exception"):
            sys.print_exception(e)
        else:
            import traceback
            traceback.print_exc()

