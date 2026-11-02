"""
TITAN 8 Deterministic Turn Engine & Level Roster (engine.py)
Mechanically identical to Into the Breach:
- 8x8 tactical grid
- Rigid turn lifecycle:
  1. Pre-Turn Telegraph: Enemies lock threat vectors based on turn-start state
  2. Player Turn: Exactly 1 Move (1 tile) + 1 Action (Shove or Wait)
  3. Turn Resolution: Shove resolves -> Enemies attack -> Damage/deaths resolve
- Undo support (turn-start snapshot)
"""

# Turn Stages
STAGE_PLANNING     = "PLANNING"     # Turn start: Player has not moved
STAGE_PLAYER_MOVED = "PLAYER_MOVED" # Player moved 1 tile: Can shove or pass
STAGE_RESOLVING    = "RESOLVING"    # Action executed: Resolving attacks & collisions

# Game States
STATE_PLAYING  = "PLAYING"
STATE_VICTORY  = "VICTORY"     # Level cleared
STATE_DEFEAT   = "DEFEAT"      # Player died
STATE_GAME_WON = "GAME_WON"    # All 8 levels cleared

# Entity Types
TYPE_PLAYER   = "player"
TYPE_MOUNTAIN = "mountain"
TYPE_DASHER   = "dasher"
TYPE_MORTAR   = "mortar"
TYPE_STRIKER  = "striker"

# Handcrafted 8-Level Roster
LEVELS = [
    # Level 1: "The Deflection"
    # Teaches: Dodging a Dasher into an obstacle.
    # Solution: Move Right to (4,5) -> Center Pass. Dasher charges into mountain at (3,6) and dies.
    {
        "name": "The Deflection",
        "player": (3, 5),
        "mountains": [(3, 6)],
        "enemies": [("dasher", 3, 1)]
    },

    # Level 2: "Crossfire"
    # Teaches: Stepping out of intersecting attack vectors so enemies collide.
    # Solution: Move to safe orthogonal tile (e.g. 4,5) -> Center Pass. Dashers ram each other at (4,4).
    {
        "name": "Crossfire",
        "player": (4, 4),
        "mountains": [],
        "enemies": [("dasher", 4, 1), ("dasher", 1, 4)]
    },

    # Level 3: "Wall Slam"
    # Teaches: Move + Shove into an obstacle.
    # Solution: Move to (3,4), then Shove Dasher at (4,4) into the Mountain at (5,4).
    {
        "name": "Wall Slam",
        "player": (2, 4),
        "mountains": [(5, 4)],
        "enemies": [("dasher", 4, 4)]
    },

    # Level 4: "The Mortar Trench"
    # Teaches: Navigating a fortified mountain trench while dual Mortars rain fire,
    # culminating in a domino breach against the bunker wall.
    # Solution: Turn 1: Move Down to (1, 4) -> Center Pass (dodge dual blast at 1, 3).
    #           Turn 2: Move Right to (2, 4) -> Center Pass (dodge dual blast at 1, 4).
    #           Turn 3: Move Right to (3, 4) -> Shove Right (1, 0) into Mortar 1 at (4, 4),
    #                   slamming Mortar 1 and Mortar 2 into the bunker wall at (6, 4).
    {
        "name": "The Mortar Trench",
        "player": (1, 3),
        "mountains": [(1, 2), (2, 2), (3, 2), (2, 3), (0, 4), (1, 5), (2, 5), (6, 4), (7, 4)],
        "enemies": [("mortar", 4, 4), ("mortar", 5, 4)]
    },

    # Level 5: "Dual Deflection"
    # Teaches: 2-Turn tactical setup: Dodge two charge lines on Turn 1, then intercept
    # the returning Dasher with a Striker shove on Turn 2.
    # Solution: Turn 1: Move Down to (3, 4) -> Center Pass.
    #                   Dasher 1 rams mountain at (1, 6) and dies.
    #                   Dasher 2 reaches far left wall at (0, 2).
    #           Turn 2: Move Left to (2, 4) -> Shove Up (0, -1) into Striker at (2, 3).
    #                   Striker is pushed to (2, 2), directly intercepting Dasher 2's return charge!
    {
        "name": "Dual Deflection",
        "player": (3, 3),
        "mountains": [(1, 6), (5, 6)],
        "enemies": [("dasher", 1, 0), ("striker", 2, 3), ("dasher", 5, 2)]
    },

    # Level 6: "The 2-HP Sacrifice"
    # Teaches: 2-Turn sacrifice puzzle: Intentionally absorbing 1 collision damage to body-block
    # Dasher 1 on Turn 1 (triggering 1-HP Emergency Strobe), then executing a clean lethal shove on Turn 2.
    # Solution: Turn 1: Move Right to (2, 4) -> Center Pass.
    #                   Player absorbs Dasher 1 charge (HP drops to 1, Dasher 1 dies).
    #           Turn 2: Move Up to (2, 3) -> Shove Right (1, 0) into Striker at (3, 3).
    #                   Striker is slammed into Dasher 2 at (4, 3); both die!
    {
        "name": "The 2-HP Sacrifice",
        "player": (1, 4),
        "mountains": [(2, 6), (5, 4)],
        "enemies": [("dasher", 2, 1), ("striker", 3, 3), ("dasher", 4, 1)]
    },

    # Level 7: "The Triple Pincer"
    # Teaches: 3-Turn multi-vector evasion: Dodging intersecting charge lines across two turns,
    # then shoving a Striker into the return vector of the surviving Dasher.
    # Solution: Turn 1: Move Left to (2, 3) -> Center Pass (Dasher 1 rams mountain at 1, 6; Dasher 2 flies past).
    #           Turn 2: Move Up to (2, 2) -> Center Pass (evade Dasher 2's northward charge to 4, 0).
    #           Turn 3: Move Up to (2, 1) -> Shove Right (1, 0) into Striker at (3, 1).
    #                   Striker lands at (4, 1) directly intercepting Dasher 2's charge; both die!
    {
        "name": "The Triple Pincer",
        "player": (3, 3),
        "mountains": [(1, 6), (7, 3), (6, 3)],
        "enemies": [("dasher", 1, 0), ("striker", 3, 1), ("dasher", 4, 2)]
    },

    # Level 8: "The Crucible"
    # Grand Campaign Finale: ALL THREE enemy types (2 Dashers, 1 Striker, 1 Mortar).
    # Multi-stage breach requiring simultaneous threat neutralizations and artillery siege.
    # Solution: Turn 1: Move Up to (3, 2) -> Shove Up (0, -1) into Striker at (3, 1) into Mountain at (3, 0).
    #                   Striker dies; Dasher 1 rams (1, 6); Dasher 2 rams (5, 6); Mortar shell misses at (3, 3).
    #           Turn 2: Move Right to (4, 2) -> Center Pass (dodge Mortar shell aimed at 3, 2).
    #           Turn 3: Move Right to (5, 2) -> Shove Right (1, 0) into Mortar at (6, 2) into Mountain at (7, 2).
    #                   Mortar dies. CAMPAIGN VICTORY!
    {
        "name": "The Crucible",
        "player": (3, 3),
        "mountains": [(1, 6), (5, 6), (3, 0), (7, 2)],
        "enemies": [("dasher", 1, 0), ("dasher", 5, 0), ("striker", 3, 1), ("mortar", 6, 2)]
    }
]


class TitanEngine:
    """Headless 8x8 deterministic game state and resolution engine."""
    def __init__(self, current_level=0):
        self.width = 8
        self.height = 8
        self.current_level = current_level
        self.state = STATE_PLAYING
        self.turn_count = 0

        self.player_pos = [0, 0]
        self.player_hp = 2
        self.mountains = set()
        self.enemies = []  # list of dicts: {'type', 'pos': [x, y], 'hp', 'target_tiles': set(), 'charge_dir': (dx, dy)}
        
        # Turn lifecycle state
        self.turn_stage = STAGE_PLANNING
        self.has_moved = False
        self.has_acted = False
        self.turn_snapshot = None
        self.impact_tiles = set()

        self.load_level(self.current_level)

    def is_in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def load_level(self, level_idx):
        """Loads level layout from LEVELS table."""
        if level_idx >= len(LEVELS):
            self.state = STATE_GAME_WON
            return

        self.current_level = level_idx
        lvl = LEVELS[level_idx]
        self.player_pos = list(lvl["player"])
        self.player_hp = 2
        self.mountains = set(lvl["mountains"])
        self.enemies = []
        for e_type, ex, ey in lvl["enemies"]:
            self.enemies.append({
                "type": e_type,
                "pos": [ex, ey],
                "hp": 1,
                "target_tiles": set(),
                "charge_dir": (0, 0),
            })

        self.state = STATE_PLAYING
        self.turn_count = 0
        self.turn_stage = STAGE_PLANNING
        self.has_moved = False
        self.has_acted = False
        self.impact_tiles.clear()

        self.calculate_enemy_telegraphs()
        self.save_snapshot()

    def restart_level(self):
        self.load_level(self.current_level)

    def next_level(self):
        if self.current_level + 1 < len(LEVELS):
            self.load_level(self.current_level + 1)
        else:
            self.state = STATE_GAME_WON

    def get_entity_at(self, x, y):
        """Returns ('player'|'mountain'|enemy_type, obj) or (None, None)."""
        if self.player_pos[0] == x and self.player_pos[1] == y and self.player_hp > 0:
            return (TYPE_PLAYER, None)
        if (x, y) in self.mountains:
            return (TYPE_MOUNTAIN, (x, y))
        for enemy in self.enemies:
            if enemy["hp"] > 0 and enemy["pos"][0] == x and enemy["pos"][1] == y:
                return (enemy["type"], enemy)
        return (None, None)

    # -------------------------------------------------------------
    # Snapshot & Undo (GPIO 9)
    # -------------------------------------------------------------
    def save_snapshot(self):
        """Saves turn-start state for single-turn undo."""
        self.turn_snapshot = {
            "player_pos": list(self.player_pos),
            "player_hp": self.player_hp,
            "mountains": set(self.mountains),
            "enemies": [
                {
                    "type": e["type"],
                    "pos": list(e["pos"]),
                    "hp": e["hp"],
                    "target_tiles": set(e["target_tiles"]),
                    "charge_dir": e["charge_dir"]
                }
                for e in self.enemies
            ]
        }

    def restore_snapshot(self):
        """Restores turn-start state, reverting any movement made this turn."""
        if self.turn_snapshot is None or self.state != STATE_PLAYING:
            return False

        snap = self.turn_snapshot
        self.player_pos = list(snap["player_pos"])
        self.player_hp = snap["player_hp"]
        self.mountains = set(snap["mountains"])
        self.enemies = [
            {
                "type": e["type"],
                "pos": list(e["pos"]),
                "hp": e["hp"],
                "target_tiles": set(e["target_tiles"]),
                "charge_dir": e["charge_dir"]
            }
            for e in snap["enemies"]
        ]
        self.has_moved = False
        self.has_acted = False
        self.turn_stage = STAGE_PLANNING
        self.impact_tiles.clear()
        return True

    # -------------------------------------------------------------
    # 1. Pre-Turn Telegraph
    # -------------------------------------------------------------
    def calculate_enemy_telegraphs(self):
        """Calculates predictable attack vectors targeting the player's initial position."""
        px, py = self.player_pos

        for enemy in self.enemies:
            enemy["target_tiles"] = set()
            enemy["charge_dir"] = (0, 0)
            if enemy["hp"] <= 0:
                continue

            ex, ey = enemy["pos"]
            e_type = enemy["type"]

            if e_type == TYPE_DASHER:
                # Dasher charges along its major axis toward player
                if px == ex:
                    cdx = 0
                    cdy = 1 if py > ey else -1
                elif py == ey:
                    cdx = 1 if px > ex else -1
                    cdy = 0
                else:
                    # Choose major axis with greater distance
                    if abs(py - ey) >= abs(px - ex):
                        cdx = 0
                        cdy = 1 if py > ey else -1
                    else:
                        cdx = 1 if px > ex else -1
                        cdy = 0

                enemy["charge_dir"] = (cdx, cdy)
                # Telegraph the entire line of charge until board edge
                cx, cy = ex + cdx, ey + cdy
                while self.is_in_bounds(cx, cy):
                    enemy["target_tiles"].add((cx, cy))
                    if (cx, cy) in self.mountains:
                        break
                    cx += cdx
                    cy += cdy

            elif e_type == TYPE_MORTAR:
                # Mortar detonates exactly on the player's initial tile
                enemy["target_tiles"].add((px, py))

            elif e_type == TYPE_STRIKER:
                # Striker strikes adjacent tile in direction of player
                sdx = 0 if px == ex else (1 if px > ex else -1)
                sdy = 0 if py == ey else (1 if py > ey else -1)
                if abs(px - ex) >= abs(py - ey):
                    tx, ty = ex + sdx, ey
                else:
                    tx, ty = ex, ey + sdy
                if self.is_in_bounds(tx, ty):
                    enemy["target_tiles"].add((tx, ty))

    # -------------------------------------------------------------
    # 2. Player Turn Actions
    # -------------------------------------------------------------
    def take_player_move(self, dx, dy):
        """Player steps 1 tile into an empty space (exactly 1 move per turn)."""
        if self.state != STATE_PLAYING or self.has_moved or self.has_acted:
            return False

        tx = self.player_pos[0] + dx
        ty = self.player_pos[1] + dy

        if not self.is_in_bounds(tx, ty):
            return False

        ent_type, _ = self.get_entity_at(tx, ty)
        if ent_type is not None:
            # Cannot move into occupied tile (use Shove instead)
            return False

        self.player_pos = [tx, ty]
        self.has_moved = True
        self.turn_stage = STAGE_PLAYER_MOVED
        return True

    def take_player_shove(self, dx, dy, animator=None):
        """
        Player shoves an adjacent entity (Enemy or Mountain) in direction (dx, dy).
        Player remains in place. Triggers resolution phase immediately.
        Supports push propagation (Domino Cascade).
        """
        if self.state != STATE_PLAYING or self.has_acted:
            return False

        self.impact_tiles.clear()

        tx = self.player_pos[0] + dx
        ty = self.player_pos[1] + dy

        if not self.is_in_bounds(tx, ty):
            return False

        ent_type, _ = self.get_entity_at(tx, ty)
        if ent_type is None or ent_type == TYPE_PLAYER:
            # Nothing to shove
            return False

        # If adjacent entity is a Mountain: Mountains are immovable obstacles
        if ent_type == TYPE_MOUNTAIN:
            self.impact_tiles.add((tx, ty))
            if (tx, ty) in self.mountains:
                self.mountains.remove((tx, ty))
            if animator:
                animator.on_collision([(tx, ty)])
            self.has_acted = True
            self.execute_resolution(animator=animator)
            return True

        # Build domino push chain of mobile units along (dx, dy)
        chain = []
        cx, cy = tx, ty
        while self.is_in_bounds(cx, cy):
            e_type, e_obj = self.get_entity_at(cx, cy)
            if e_type is None or e_type == TYPE_PLAYER or e_type == TYPE_MOUNTAIN:
                break
            chain.append((cx, cy, e_type, e_obj))
            cx += dx
            cy += dy

        dest_x, dest_y = cx, cy

        # Determine if destination blocks the push
        is_blocked = False
        blocked_by_mountain = False

        if not self.is_in_bounds(dest_x, dest_y):
            # Blocked by board boundary wall
            is_blocked = True
        else:
            block_type, _ = self.get_entity_at(dest_x, dest_y)
            if block_type == TYPE_MOUNTAIN:
                is_blocked = True
                blocked_by_mountain = True
            elif block_type is not None:
                is_blocked = True

        if is_blocked:
            # Collision damage cascades down the mobile chain
            for (ox, oy, o_type, o_obj) in chain:
                self.impact_tiles.add((ox, oy))
                o_obj["hp"] -= 1

            if blocked_by_mountain and (dest_x, dest_y) in self.mountains:
                self.mountains.remove((dest_x, dest_y))
                self.impact_tiles.add((dest_x, dest_y))

            if animator:
                animator.on_collision(list(self.impact_tiles))
        else:
            # Open shove: animate 1 intermediate motion frame (40ms)
            if animator:
                animator.on_shove_slide(chain, dx, dy)

            # Empty tile at end of chain: Shift mobile units forward by 1
            for (ox, oy, o_type, o_obj) in reversed(chain):
                nx, ny = ox + dx, oy + dy
                o_obj["pos"] = [nx, ny]

            if animator:
                animator.render_frame()

        self.has_acted = True
        self.execute_resolution(animator=animator)
        return True

    def take_player_pass(self, animator=None):
        """Player skips action / waits in place. Triggers resolution phase immediately."""
        if self.state != STATE_PLAYING or self.has_acted:
            return False

        self.impact_tiles.clear()
        self.has_acted = True
        self.execute_resolution(animator=animator)
        return True

    # -------------------------------------------------------------
    # 3. Resolution Pipeline (Phase Execution)
    # -------------------------------------------------------------
    def execute_resolution(self, animator=None):
        """Resolves turn: Player action consequences -> Enemy attacks -> State upkeep."""
        self.turn_stage = STAGE_RESOLVING

        # Step 1: Clean up any units killed during Player Action (Shove)
        self._prune_dead_units()
        if animator:
            animator.render_frame()
        if self._check_win_loss():
            return

        # Step 2: Enemy Attacks Execute
        # Dashers charge simultaneously step-by-step
        charging_dashers = [e for e in self.enemies if e["hp"] > 0 and e["type"] == TYPE_DASHER]

        for _ in range(self.width):
            if not charging_dashers:
                break

            next_positions = {}
            stopped = set()
            step_impacts = []

            for dasher in charging_dashers:
                cdx, cdy = dasher["charge_dir"]
                nx = dasher["pos"][0] + cdx
                ny = dasher["pos"][1] + cdy

                if not self.is_in_bounds(nx, ny):
                    stopped.add(id(dasher))
                else:
                    t_key = (nx, ny)
                    if t_key not in next_positions:
                        next_positions[t_key] = []
                    next_positions[t_key].append(dasher)

            for (tx, ty), dashers in next_positions.items():
                if len(dashers) > 1:
                    # Multiple dashers colliding at the exact same tile!
                    self.impact_tiles.add((tx, ty))
                    step_impacts.append((tx, ty))
                    for d in dashers:
                        d["hp"] -= 1
                        d["pos"] = [tx, ty]
                        stopped.add(id(d))
                else:
                    dasher = dashers[0]
                    target_type, target_obj = self.get_entity_at(tx, ty)
                    if target_type is not None:
                        self.impact_tiles.add((tx, ty))
                        step_impacts.append((tx, ty))
                        dasher["hp"] -= 1
                        stopped.add(id(dasher))
                        if target_type == TYPE_PLAYER:
                            self.player_hp -= 1
                        elif target_type == TYPE_MOUNTAIN:
                            if target_obj in self.mountains:
                                self.mountains.remove(target_obj)
                        else:
                            target_obj["hp"] -= 1
                    else:
                        dasher["pos"] = [tx, ty]

            charging_dashers = [d for d in charging_dashers if id(d) not in stopped and d["hp"] > 0]

            if animator:
                animator.on_dasher_step(step_impacts)

        self._prune_dead_units()
        if animator:
            animator.render_frame()
        if self._check_win_loss():
            return

        # Mortars detonate
        for enemy in list(self.enemies):
            if enemy["hp"] <= 0 or enemy["type"] != TYPE_MORTAR:
                continue
            m_pos = tuple(enemy["pos"])
            for (tx, ty) in enemy["target_tiles"]:
                if animator:
                    animator.on_mortar_lob(m_pos, (tx, ty))
                self.impact_tiles.add((tx, ty))
                target_type, target_obj = self.get_entity_at(tx, ty)
                hit_something = False
                if target_type == TYPE_PLAYER:
                    self.player_hp -= 1
                    hit_something = True
                elif target_type == TYPE_MOUNTAIN:
                    if target_obj in self.mountains:
                        self.mountains.remove(target_obj)
                    hit_something = True
                elif target_obj is not None:
                    target_obj["hp"] -= 1
                    hit_something = True

                if animator and hit_something:
                    animator.on_collision([(tx, ty)])

        self._prune_dead_units()
        if animator:
            animator.render_frame()
        if self._check_win_loss():
            return

        # Strikers strike
        for enemy in list(self.enemies):
            if enemy["hp"] <= 0 or enemy["type"] != TYPE_STRIKER:
                continue
            s_pos = tuple(enemy["pos"])
            for (tx, ty) in enemy["target_tiles"]:
                if animator:
                    animator.on_striker_strike(s_pos, (tx, ty))
                self.impact_tiles.add((tx, ty))
                target_type, target_obj = self.get_entity_at(tx, ty)
                hit_something = False
                if target_type == TYPE_PLAYER:
                    self.player_hp -= 1
                    hit_something = True
                    pdx = tx - enemy["pos"][0]
                    pdy = ty - enemy["pos"][1]
                    px_k = self.player_pos[0] + pdx
                    py_k = self.player_pos[1] + pdy
                    if self.is_in_bounds(px_k, py_k) and self.get_entity_at(px_k, py_k)[0] is None:
                        self.player_pos = [px_k, py_k]
                elif target_type == TYPE_MOUNTAIN:
                    if target_obj in self.mountains:
                        self.mountains.remove(target_obj)
                    hit_something = True
                elif target_obj is not None:
                    target_obj["hp"] -= 1
                    hit_something = True

                if animator and hit_something:
                    animator.on_collision([(tx, ty)])

        self._prune_dead_units()

        # Step 3: State Upkeep
        if self._check_win_loss():
            return

        # Advance to next turn
        self.turn_count += 1
        self.has_moved = False
        self.has_acted = False
        self.turn_stage = STAGE_PLANNING
        self.calculate_enemy_telegraphs()
        self.save_snapshot()

    def _prune_dead_units(self):
        """Removes dead enemies (HP <= 0)."""
        self.enemies = [e for e in self.enemies if e["hp"] > 0]

    def _check_win_loss(self):
        """Evaluates win/defeat conditions."""
        if self.player_hp <= 0:
            self.state = STATE_DEFEAT
            return True

        if len(self.enemies) == 0:
            self.state = STATE_VICTORY
            return True

        return False
