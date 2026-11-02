# TITAN 8: Deterministic Turn-Based Tactical Puzzle Engine
**Concours Project Submission & Technical Dossier**
*Platform: Raspberry Pi Pico (RP2040) / MicroPython + Lumatrix 8×8 WS2812B NeoPixel Matrix*

---

## 1. Executive Summary & Vision

**TITAN 8** is an authentic, deterministic turn-based tactical puzzle game engineered specifically for the 8×8 WS2812B RGB LED matrix on the Raspberry Pi Pico (RP2040). 

Mechanically inspired by *Into the Breach*, TITAN 8 discards real-time randomness and reflex-based gameplay in favor of strict, transparent information theory:
- **Zero Hidden Information:** All enemy attack vectors and destination tiles are clearly telegraphed to the player before any action is taken.
- **Strict Turn Economy:** Every turn, the player is granted **exactly ONE Move (1 tile)** and **ONE Action (Shove or Pass)**.
- **Kinetic Physics & Environment as Weaponry:** Direct damage is rarely dealt with simple attacks; rather, the player uses positional shoves to redirect enemies into colliding with one another, slamming into mountains, or catching their allies in friendly fire.
- **Undo Safety Net:** A snapshot mechanism (GPIO 9) allows instant rollbacks of movement mistakes within the turn.

---

## 2. Hardware Architecture & Pinout

The game is optimized for low-latency physical interaction using tactile mechanical switches and a direct NeoPixel serial pipeline:

| Component | Pin (RP2040) | Configuration | Functionality |
| :--- | :--- | :--- | :--- |
| **WS2812B 8×8 Matrix** | **GPIO 19** | `machine.Pin.OUT` (PIO NeoPixel) | 64-pixel RGB display, progressive row-major mapping (`idx = x + y * 8`) |
| **5-Way Nav: UP** | **GPIO 3** | `Pin.IN, Pin.PULL_UP` | Tilt Up (Move / Shove) |
| **5-Way Nav: DOWN** | **GPIO 6** | `Pin.IN, Pin.PULL_UP` | Tilt Down (Move / Shove) |
| **5-Way Nav: LEFT** | **GPIO 7** | `Pin.IN, Pin.PULL_UP` | Tilt Left (Move / Shove) |
| **5-Way Nav: RIGHT** | **GPIO 2** | `Pin.IN, Pin.PULL_UP` | Tilt Right (Move / Shove) |
| **5-Way Nav: CENTER** | **GPIO 8** | `Pin.IN, Pin.PULL_UP` | Press: Pass / End Turn (Short) \| Level/Game Reset (Hold) |
| **Tactile Button (Undo)** | **GPIO 9** | `Pin.IN, Pin.PULL_UP` | Press: Undo Turn-Start Movement (Short) \| Game Reset (Hold) |

*Power & Thermal Safety:* NeoPixel master brightness is capped at **40%** in `config.py` to prevent voltage drops or excessive USB current draw on RP2040 voltage rails.

---

## 3. Game Architecture & Core Mechanics

The engine is built around a discrete state machine and a deterministic resolution pipeline:

```
[TURN START]
   │  Enemies calculate & display attack telegraphs
   │  Turn-start snapshot saved (for GPIO 9 Undo)
   │  has_moved = False, has_acted = False
   ▼
[PLAYER TURN]
   ├─ Tilt Empty Tile: Steps 1 tile (has_moved = True)
   ├─ Tilt Entity (Enemy/Mountain): Shoves target (has_acted = True) ──┐
   ├─ Press Center: Pass / End turn (has_acted = True) ────────────────┤
   └─ Press Extra (GPIO 9): Reverts move to turn-start position        │
                                                                        ▼
                                                             [RESOLUTION PIPELINE]
                                                                1. Shove Physics & Domino Collision
                                                                2. Dasher Step-by-Step Charges
                                                                3. Mortar Ballistic Detonations
                                                                4. Striker Melee Shoves
                                                                5. State Upkeep (Win / Loss / Next Turn)
```

### The Entity Roster

1. **Player Unit (`player`):**
   * **Color:** Cyan `(0, 220, 255)` at 2 HP.
   * **Emergency 1-HP Alert:** Rapid 4 Hz strobe alternating between Cyan `(0, 220, 255)` and Amber Warning `(255, 60, 0)`.
   * **Capabilities:** 1 step per turn + 1 orthogonal shove.
2. **Dasher (`dasher`):**
   * **Color:** Vibrant Solid Red `(255, 20, 0)`.
   * **Behavior:** Locks onto the player's major axis. On resolution, charges tile-by-tile at high velocity until striking a wall, mountain, unit, or border. Deals 1 collision damage to whatever it hits and takes 1 collision damage (dying).
   * **Telegraph:** Subtle 1.5 Hz breathing trace `(6, 0, 0)` $\leftrightarrow$ `(16, 0, 0)` along its entire projected trajectory.
3. **Mortar (`mortar`):**
   * **Color:** Deep Magenta `(255, 0, 180)`.
   * **Behavior:** Pre-targets the player's exact turn-start coordinate. On resolution, fires a ballistic shell that arcs across the board (interpolated brightness arc) and detonates in an expanding energy cross.
   * **Telegraph:** Pulsing magenta marker `(30, 0, 30)` $\leftrightarrow$ `(70, 0, 70)` strictly on the targeted impact cell.
4. **Striker (`striker`):**
   * **Color:** Sharp Amber `(255, 140, 0)`.
   * **Behavior:** Targets the adjacent tile closest to the player. On resolution, strikes the tile, dealing 1 damage and shoving whatever unit is there 1 tile backward.
5. **Mountain (`mountain`):**
   * **Color:** Earth Bronze `(80, 40, 5)`.
   * **Behavior:** Static destructible obstacle. Absorbs shoves and collisions (crumbling on impact) or acts as an anvil for wall-slam kills.

---

## 4. The Handcrafted 8-Level Puzzle Campaign

The campaign follows a pedagogical curriculum: Levels 1–4 introduce mechanics in concise 1-to-3 turn encounters; Levels 5–8 ramp up into sophisticated, multi-turn tactical challenges.

| Level | Name | Turns | Focus / Concept | Core Tactical Solution |
| :---: | :--- | :---: | :--- | :--- |
| **1** | **The Deflection** | 1 | Dasher evasion & obstacle deflection | Step Right to `(4, 5)` $\rightarrow$ Pass. Dasher rams mountain at `(3, 6)`. |
| **2** | **Crossfire** | 1 | Intersecting threat lines | Step Down to `(4, 5)` $\rightarrow$ Pass. Dual Dashers ram each other at `(4, 4)`. |
| **3** | **Wall Slam** | 1 | Move + Shove mechanics | Move Right to `(3, 4)` $\rightarrow$ Shove Right. Dasher slams into mountain at `(5, 4)`. |
| **4** | **The Mortar Trench** | 3 | Labyrinth trench crawl & Mortar lob | Navigate 2 turns through mountain trench, then domino-slam dual Mortars into bunker wall. |
| **5** | **Dual Deflection** | 2 | Multi-turn tactical setup | Dodge 2 Dashers on T1; on T2 shove Striker to intercept returning Dasher at `(2, 2)`. |
| **6** | **The 2-HP Sacrifice** | 2 | Intentional collision & 1-HP clutch | Absorb Dasher 1 charge on T1 (triggering 1-HP alert strobe); lethal shove on T2. |
| **7** | **The Triple Pincer** | 3 | Dynamic multi-turn evasion | Evade intersecting Dashers over 2 turns, then shove Striker into Dasher 2's return vector. |
| **8** | **The Crucible** | 3 | Grand Campaign Finale (All 3 enemy types) | T1: Wall-slam Striker while baiting Dashers into mountains. T2-T3: Advance under mortar fire & breach bunker. |

---

## 5. Kinetic Visual Presentation & Feedback

Unlike static frame-swapping engines, TITAN 8 implements dedicated kinetic animations:
- **Interpolated Ballistic Arcs:** Mortar shells interpolate between `(x0, y0)` and `(x1, y1)` over 4–5 frames, simulating altitude by climbing from dim magenta `(80, 0, 60)` to peak white apex `(255, 120, 255)`, before impacting in a white flash and cross expansion.
- **Step-by-Step Dasher Charges:** Dashers visibly sprint across the matrix cell-by-cell at 30ms per tile.
- **Hit-Stop & Screen Shockwaves:** Fatal impacts trigger a 45ms pure-white hit-stop flash on the collision tile, followed immediately by a 25ms faint-red whole-matrix shockwave `(12, 0, 0)`.
- **Intermediate Shove Slides:** Pushed units visually slide to their destination over a 40ms intermediate frame.
- **Victory & Defeat Ceremonies:** Complete multi-phase visual sequences celebrate clearing levels and winning the 8-level campaign.

---

## 6. Verification & Automated Testing

The codebase includes a comprehensive headless unit test suite (`test_engine_unit.py`) that executes in **0.000s** without hardware dependencies:
- Tests all 8 handcrafted levels and their deterministic solutions.
- Tests single-turn Undo (GPIO 9 snapshot rollbacks).
- Tests move-once-per-turn rules, push propagation chains, and boundary collisions.

To execute tests:
```bash
python3 test_engine_unit.py
```

---

## 7. Submission Package Manifest

The files included in this submission folder (`~/TITAN8_CONCOURS_SUBMISSION/`):
- `engine.py`: Headless deterministic game state, turn state machine, resolution pipeline, and 8-level campaign roster.
- `hardware.py`: RP2040 hardware drivers, WS2812B PIO display mapping, debounce input handlers, screen shockwaves.
- `config.py`: Pin assignments, color palettes, visual brightness bounds, and animation timing constants.
- `main.py`: Main game loop, real-time kinetic visual animator, state rendering, campaign ceremonies.
- `test_engine_unit.py`: 100% passing automated test suite for headless engine verification.
- `test_hardware.py`: Low-level hardware diagnostic suite for LED matrix and switches.
- `README.md`: This comprehensive project dossier and technical specification.
