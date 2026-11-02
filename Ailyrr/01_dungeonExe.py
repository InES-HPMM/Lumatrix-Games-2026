"""Dungeon.exe has stopped working - a compact, corrupted dungeon crawler.

Each room has either no corruption or exactly one corruption. When entering a
room, the game pauses and shows only the walls plus one fast diagonal scan ray.
Once that ray has passed, the room becomes active and its enemies and items
appear.

MOVE mode: directions move the hero; center uses a potion or enters a cleared
exit.

COMBAT mode: directions use the selected ability; center cycles abilities.
"""

from machine import Timer

from zhaw_led_matrix import Button, ColorTable, LedMatrix


class DungeonExe:
    COLS = 8
    ROWS = 8
    ACTIVE_TICK_MS = 900
    SCAN_TICK_MS = 80
    RAY_START = -8
    RAY_END = 15
    RAY_STEP = 5
    MAX_HP = 3
    MAX_LEVEL = 6

    SWORD = 0
    FIREBALL = 1
    POTION = 2
    BLINK = 3
    ABILITY_COUNT = 4

    NO_CORRUPTION = 0
    REVERSED_MOVEMENT = 1
    TELEPORTING_ENEMIES = 2
    INVISIBLE_WALLS = 3
    COLOR_GLITCH = 4
    CORRUPTION_COUNT = 4

    # x_min, x_max, y_min, y_max for the four visible rooms.
    ROOM_RANGES = (
        (1, 3, 1, 3),
        (4, 6, 1, 3),
        (1, 3, 4, 6),
        (4, 6, 4, 6),
    )
    DOOR_POSITIONS = ((4, 1), (1, 4), (6, 4), (4, 6))
    DIGITS = (
        ("111", "101", "101", "101", "111"),
        ("010", "110", "010", "010", "111"),
        ("111", "001", "111", "100", "111"),
        ("111", "001", "111", "001", "111"),
        ("101", "101", "111", "001", "001"),
        ("111", "100", "111", "001", "111"),
        ("111", "100", "111", "101", "111"),
        ("111", "001", "001", "001", "001"),
        ("111", "101", "111", "101", "111"),
        ("111", "101", "111", "001", "111"),
    )

    def __init__(self):
        self.matrix = LedMatrix(self.ROWS, self.COLS)
        self.matrix.set_brightness(35)

        self.button = Button()
        self.button.set_left_handler(self.joystick_left)
        self.button.set_right_handler(self.joystick_right)
        self.button.set_up_handler(self.joystick_up)
        self.button.set_down_handler(self.joystick_down)
        self.button.set_center_handler(self.joystick_center)
        self.button.set_switch_handler(self.switch_changed)

        self.timer = Timer()
        self.combat_mode = self.button.switch.value() == 0
        self.player_x = 1
        self.player_y = 1
        self.exit_x = 6
        self.exit_y = 6
        self.current_room = 0
        self.room_scanning = True
        self.level = 1
        self.hp = self.MAX_HP
        self.score = 0
        self.enemies_slain = 0
        self.coins_collected = 0
        self.ability = self.SWORD
        self.aim_dx = 0
        self.aim_dy = 1
        self.tick_count = 0
        self.game_over = False

        self.walls = []
        self.enemies = []
        self.potions = []
        self.room_corruption = [self.NO_CORRUPTION for _ in range(4)]
        self.room_initialized = [False for _ in range(4)]
        self.room_cleared = [False for _ in range(4)]
        self.room_enemies = [[] for _ in range(4)]
        self.room_potions = [[] for _ in range(4)]

        # There is deliberately only one ray state. A room cannot leave a
        # second ray behind or recreate one during normal rendering.
        self.ray_type = self.NO_CORRUPTION
        self.ray_phase = None
        self.random_state = 0xD06E0E

        self.reset()


    # Helpers and map generation

    def index(self, x, y):
        return y * self.COLS + x

    def next_random(self):
        self.random_state = (self.random_state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.random_state

    def room_index(self, x, y):
        return (0 if y < 4 else 2) + (0 if x < 4 else 1)

    def has_corruption(self, x, y, corruption):
        return self.room_corruption[self.room_index(x, y)] == corruption

    def is_door(self, x, y):
        return (x, y) in self.DOOR_POSITIONS

    def door_destination(self, x, y):
        """Return the room reached through a door, or -1 for a normal cell."""
        if (x, y) == (4, 1):
            return 1 if self.current_room == 0 else 0
        if (x, y) == (1, 4):
            return 2 if self.current_room == 0 else 0
        if (x, y) == (6, 4):
            return 3 if self.current_room == 1 else 1
        if (x, y) == (4, 6):
            return 3 if self.current_room == 2 else 2
        return -1

    def is_open(self, x, y):
        if x < 0 or x >= self.COLS or y < 0 or y >= self.ROWS:
            return False
        return not self.walls[self.index(x, y)]

    def enemy_at(self, x, y):
        for i in range(len(self.enemies)):
            if self.enemies[i][0] == x and self.enemies[i][1] == y:
                return i
        return -1

    def potion_at(self, x, y):
        for i in range(len(self.potions)):
            if self.potions[i][0] == x and self.potions[i][1] == y:
                return i
        return -1

    def reset(self):
        self.level = 1
        self.hp = self.MAX_HP
        self.score = 0
        self.enemies_slain = 0
        self.coins_collected = 0
        self.ability = self.SWORD
        self.tick_count = 0
        self.game_over = False
        self.player_x = 1
        self.player_y = 1
        self.generate_level()
        self.begin_room_scan(0)

    def generate_level(self):
        self.walls = [False for _ in range(self.COLS * self.ROWS)]

        for x in range(self.COLS):
            self.walls[self.index(x, 0)] = True
            self.walls[self.index(x, self.ROWS - 1)] = True
        for y in range(self.ROWS):
            self.walls[self.index(0, y)] = True
            self.walls[self.index(self.COLS - 1, y)] = True

        # Random walls leave a guaranteed route along y=1 and x=6.
        for y in range(1, self.ROWS - 1):
            for x in range(1, self.COLS - 1):
                if (y != 1 and x != self.COLS - 2
                        and self.next_random() % 5 == 0):
                    self.walls[self.index(x, y)] = True

        # Rooms are separated by walls. Only the four green door cells connect
        # them, so ordinary movement cannot silently trigger a room transition.
        for y in range(1, self.ROWS - 1):
            if not self.is_door(4, y):
                self.walls[self.index(4, y)] = True
        for x in range(1, self.COLS - 1):
            if not self.is_door(x, 4):
                self.walls[self.index(x, 4)] = True

        self.walls[self.index(self.player_x, self.player_y)] = False
        self.walls[self.index(self.exit_x, self.exit_y)] = False

        # A room receives zero or one corruption. Higher levels unlock more
        # types, but the probability stays below 100% so clean rooms remain.
        self.room_corruption = [self.NO_CORRUPTION for _ in range(4)]
        self.room_initialized = [False for _ in range(4)]
        self.room_cleared = [False for _ in range(4)]
        self.room_enemies = [[] for _ in range(4)]
        self.room_potions = [[] for _ in range(4)]
        chance = min(65, 10 + self.level * 10)
        available_types = min(self.CORRUPTION_COUNT, self.level)
        for room in range(4):
            if self.next_random() % 100 < chance:
                self.room_corruption[room] = 1 + self.next_random() % available_types

    def save_current_room(self):
        if self.room_scanning:
            return

        self.room_enemies[self.current_room] = self.enemies
        self.room_potions[self.current_room] = self.potions
        if len(self.enemies) == 0:
            self.room_cleared[self.current_room] = True

    def mark_room_cleared_if_empty(self):
        if not self.room_scanning and len(self.enemies) == 0:
            self.room_cleared[self.current_room] = True
            self.room_enemies[self.current_room] = self.enemies
            self.room_potions[self.current_room] = self.potions

    def begin_room_scan(self, room):
        if room != self.current_room:
            self.save_current_room()

        self.current_room = room

        # Revisited rooms reuse their saved contents. Cleared rooms never
        # produce another scan or regenerate enemies/items.
        if self.room_initialized[room]:
            self.room_scanning = False
            self.ray_type = self.NO_CORRUPTION
            self.ray_phase = None
            self.enemies = self.room_enemies[room]
            self.potions = self.room_potions[room]
            self.render()
            self.schedule(self.ACTIVE_TICK_MS)
            return

        self.room_initialized[room] = True
        self.room_scanning = True
        self.enemies = []
        self.potions = []

        # This is the only place a ray is created.
        self.ray_type = self.room_corruption[room]
        self.ray_phase = None if self.ray_type == self.NO_CORRUPTION else self.RAY_START

        self.render()
        self.schedule(self.SCAN_TICK_MS)

    def finish_room_scan(self):
        self.room_scanning = False
        self.ray_type = self.NO_CORRUPTION
        self.ray_phase = None
        self.spawn_room_content(self.current_room)
        self.mark_room_cleared_if_empty()

    def schedule(self, period):
        self.timer.init(mode=Timer.ONE_SHOT, period=period, callback=self.run)

    def spawn_room_content(self, room):
        enemy_count = min(1 + self.level // 2, 3)
        potion_count = 1 if self.level < 4 else 2

        for _ in range(enemy_count):
            position = self.random_open_position(room, 4)
            if position is not None:
                self.enemies.append([position[0], position[1]])

        for _ in range(potion_count):
            position = self.random_open_position(room, 2)
            if position is not None:
                self.potions.append([position[0], position[1]])

        self.room_enemies[room] = self.enemies
        self.room_potions[room] = self.potions

    def random_open_position(self, room, minimum_distance):
        x_min, x_max, y_min, y_max = self.ROOM_RANGES[room]
        for _ in range(24):
            x = x_min + self.next_random() % (x_max - x_min + 1)
            y = y_min + self.next_random() % (y_max - y_min + 1)
            if not self.is_open(x, y):
                continue
            if abs(x - self.player_x) + abs(y - self.player_y) < minimum_distance:
                continue
            if x == self.exit_x and y == self.exit_y:
                continue
            if self.is_door(x, y):
                continue
            if self.enemy_at(x, y) >= 0 or self.potion_at(x, y) >= 0:
                continue
            return x, y
        return None


    # Input and movement

    def move_player(self, dx, dy):
        if self.game_over or self.room_scanning:
            return

        if self.has_corruption(self.player_x, self.player_y, self.REVERSED_MOVEMENT):
            dx = -dx
            dy = -dy

        target_x = self.player_x + dx
        target_y = self.player_y + dy
        if not self.is_open(target_x, target_y):
            return
        if self.enemy_at(target_x, target_y) >= 0:
            self.hp -= 1
            return

        previous_x = self.player_x
        previous_y = self.player_y
        self.player_x = target_x
        self.player_y = target_y
        self.check_room_transition(previous_x, previous_y)

    def check_room_transition(self, previous_x, previous_y):
        new_room = self.door_destination(self.player_x, self.player_y)
        position_room = self.room_index(self.player_x, self.player_y)
        if new_room < 0 and position_room != self.current_room:
            if self.is_door(previous_x, previous_y):
                new_room = position_room
        if new_room >= 0 and new_room != self.current_room:
            self.begin_room_scan(new_room)

    def joystick_left(self, _):
        if self.combat_mode:
            self.aim_dx, self.aim_dy = -1, 0
            self.use_ability(-1, 0)
        else:
            self.move_player(-1, 0)
        self.render()

    def joystick_right(self, _):
        if self.combat_mode:
            self.aim_dx, self.aim_dy = 1, 0
            self.use_ability(1, 0)
        else:
            self.move_player(1, 0)
        self.render()

    def joystick_up(self, _):
        if self.combat_mode:
            self.aim_dx, self.aim_dy = 0, 1
            self.use_ability(0, 1)
        else:
            self.move_player(0, 1)
        self.render()

    def joystick_down(self, _):
        if self.combat_mode:
            self.aim_dx, self.aim_dy = 0, -1
            self.use_ability(0, -1)
        else:
            self.move_player(0, -1)
        self.render()

    def joystick_center(self, _):
        if self.game_over:
            self.reset()
            return
        if self.room_scanning:
            return

        if self.combat_mode:
            self.ability = (self.ability + 1) % self.ABILITY_COUNT
            self.render()
            return

        potion = self.potion_at(self.player_x, self.player_y)
        if potion >= 0:
            self.hp = min(self.MAX_HP, self.hp + 1)
            self.coins_collected += 1
            self.score += 1
            del self.potions[potion]
        elif (self.player_x == self.exit_x and self.player_y == self.exit_y
              and len(self.enemies) == 0):
            self.level = min(self.MAX_LEVEL, self.level + 1)
            self.score += 10
            self.player_x = 1
            self.player_y = 1
            self.generate_level()
            self.begin_room_scan(0)
            return
        self.render()

    def switch_changed(self, _):
        self.combat_mode = self.button.switch.value() == 0
        self.render()


    # Combat and timer loop

    def use_ability(self, dx, dy):
        if self.game_over or self.room_scanning:
            return

        target_x = self.player_x + dx
        target_y = self.player_y + dy
        if self.ability == self.SWORD:
            enemy = self.enemy_at(target_x, target_y)
            if enemy >= 0:
                del self.enemies[enemy]
                self.enemies_slain += 1
                self.score += 2
                self.mark_room_cleared_if_empty()
            return

        if self.ability == self.FIREBALL:
            for distance in range(1, 4):
                x = self.player_x + dx * distance
                y = self.player_y + dy * distance
                if not self.is_open(x, y):
                    break
                enemy = self.enemy_at(x, y)
                if enemy >= 0:
                    del self.enemies[enemy]
                    self.enemies_slain += 1
                    self.score += 3
                    self.mark_room_cleared_if_empty()
                    break
            return

        if self.ability == self.POTION:
            self.hp = min(self.MAX_HP, self.hp + 1)
            return

        blink_x = self.player_x + dx * 2
        blink_y = self.player_y + dy * 2
        middle_x = self.player_x + dx
        middle_y = self.player_y + dy
        if (self.room_index(blink_x, blink_y) != self.current_room
                and not self.is_door(middle_x, middle_y)):
            return
        if self.is_open(blink_x, blink_y) and self.enemy_at(blink_x, blink_y) < 0:
            previous_x = self.player_x
            previous_y = self.player_y
            self.player_x = blink_x
            self.player_y = blink_y
            if self.room_index(blink_x, blink_y) != self.current_room:
                self.begin_room_scan(self.room_index(blink_x, blink_y))
            else:
                self.check_room_transition(previous_x, previous_y)

    def enemy_turn(self):
        if self.tick_count % 2 != 0:
            return

        for enemy in self.enemies:
            ex, ey = enemy
            dx = self.player_x - ex
            dy = self.player_y - ey

            if abs(dx) + abs(dy) == 1:
                self.hp -= 1
                continue

            if (self.has_corruption(ex, ey, self.TELEPORTING_ENEMIES)
                    and self.tick_count % 4 == 0):
                position = self.random_open_position(self.current_room, 3)
                if position is not None:
                    enemy[0], enemy[1] = position
                continue

            directions = []
            if abs(dx) >= abs(dy) and dx != 0:
                directions.append((1 if dx > 0 else -1, 0))
            if dy != 0:
                directions.append((0, 1 if dy > 0 else -1))

            moved = False
            for step_x, step_y in directions:
                target_x = ex + step_x
                target_y = ey + step_y
                if not self.is_open(target_x, target_y):
                    continue
                if target_x == self.player_x and target_y == self.player_y:
                    self.hp -= 1
                    moved = True
                    break
                if self.enemy_at(target_x, target_y) < 0:
                    enemy[0], enemy[1] = target_x, target_y
                    moved = True
                    break

            if not moved and self.next_random() % 3 == 0:
                direction = self.next_random() % 4
                step_x, step_y = ((1, 0), (0, -1), (-1, 0), (0, 1))[direction]
                target_x = ex + step_x
                target_y = ey + step_y
                if self.is_open(target_x, target_y) and self.enemy_at(target_x, target_y) < 0:
                    enemy[0], enemy[1] = target_x, target_y

    def run(self, _=None):
        if self.game_over:
            self.render()
            return

        if self.room_scanning:
            if self.ray_phase is not None:
                self.ray_phase += self.RAY_STEP
            if self.ray_phase is None or self.ray_phase >= self.RAY_END:
                self.finish_room_scan()
                self.render()
                self.schedule(self.ACTIVE_TICK_MS)
            else:
                self.render()
                self.schedule(self.SCAN_TICK_MS)
            return

        self.tick_count += 1
        self.enemy_turn()
        if self.hp <= 0:
            self.game_over = True
            print("GAME OVER - score: {}, enemies slain: {}, coins: {}".format(
                self.score,
                self.enemies_slain,
                self.coins_collected,
            ))
        self.render()
        if not self.game_over:
            self.schedule(self.ACTIVE_TICK_MS)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def corruption_color(self, corruption):
        if corruption == self.REVERSED_MOVEMENT:
            return ColorTable.RED
        if corruption == self.TELEPORTING_ENEMIES:
            return ColorTable.PURPLE
        if corruption == self.INVISIBLE_WALLS:
            return ColorTable.BLUE
        return ColorTable.GREEN

    def glitch_color(self, normal, alternate, x, y):
        if not self.has_corruption(x, y, self.COLOR_GLITCH):
            return normal
        return alternate if (self.tick_count + x + y) % 2 == 0 else normal

    def draw_walls(self):
        for y in range(self.ROWS):
            for x in range(self.COLS):
                if not self.walls[self.index(x, y)]:
                    continue
                if (not self.room_scanning
                        and self.has_corruption(x, y, self.INVISIBLE_WALLS)
                        and (x + y + self.tick_count) % 4 == 0):
                    continue
                if self.room_scanning:
                    color = ColorTable.BLUE
                else:
                    color = self.glitch_color(ColorTable.BLUE, ColorTable.PURPLE, x, y)
                self.matrix[x, y] = color

    def draw_ray(self):
        if self.ray_phase is None:
            return
        color = self.corruption_color(self.ray_type)
        for x in range(self.COLS):
            y = self.ray_phase - x
            if 0 <= y < self.ROWS:
                self.matrix[x, y] = color

    def ability_color(self):
        if self.ability == self.SWORD:
            return ColorTable.WHITE
        if self.ability == self.FIREBALL:
            return ColorTable.ORANGE
        if self.ability == self.POTION:
            return ColorTable.GREEN
        return ColorTable.PURPLE

    def draw_digit(self, digit, offset_x, color):
        pattern = self.DIGITS[digit]
        for y in range(len(pattern)):
            for x in range(3):
                if pattern[y][x] == "1":
                    # Matrix y=0 is physically the bottom row, so invert the
                    # five-pixel digit vertically to keep it readable.
                    self.matrix[offset_x + x, 5 - y] = color

    def draw_score_screen(self):
        """Show only the final score as two fixed digits."""
        self.matrix.clear()
        display_score = self.score % 100
        tens = display_score // 10
        ones = display_score % 10
        self.draw_digit(tens, 0, ColorTable.YELLOW)
        self.draw_digit(ones, 4, ColorTable.YELLOW)
        self.matrix.apply()

    def draw_ability_preview(self):
        """Show the ability's reachable cells with deliberately dim pixels."""
        if not self.combat_mode or self.room_scanning:
            return

        directions = ((1, 0), (-1, 0), (0, 1), (0, -1))
        if self.ability == self.SWORD:
            dim_color = (45, 45, 45)
            bright_color = (110, 110, 110)
            max_distance = 1
        elif self.ability == self.FIREBALL:
            dim_color = (55, 12, 0)
            bright_color = (140, 35, 0)
            max_distance = 3
        elif self.ability == self.POTION:
            dim_color = (0, 45, 0)
            bright_color = (0, 120, 0)
            max_distance = 1
        else:
            dim_color = (25, 0, 60)
            bright_color = (80, 0, 150)
            max_distance = 2

        for dx, dy in directions:
            for distance in range(1, max_distance + 1):
                x = self.player_x + dx * distance
                y = self.player_y + dy * distance
                if not self.is_open(x, y):
                    break

                if dx == self.aim_dx and dy == self.aim_dy:
                    self.matrix[x, y] = bright_color
                else:
                    self.matrix[x, y] = dim_color

                if self.ability == self.SWORD:
                    break
                if self.ability == self.POTION:
                    break
                if self.ability == self.FIREBALL and self.enemy_at(x, y) >= 0:
                    break

    def draw_doors(self):
        for door_x, door_y in self.DOOR_POSITIONS:
            self.matrix[door_x, door_y] = ColorTable.GREEN

    def render(self):
        self.matrix.clear()
        if self.game_over:
            self.draw_score_screen()
            return

        self.draw_walls()
        if self.room_scanning:
            self.draw_ray()
            self.matrix.apply()
            return

        self.draw_ability_preview()
        self.draw_doors()

        self.matrix[self.exit_x, self.exit_y] = self.glitch_color(
            ColorTable.GREEN, ColorTable.AQUA, self.exit_x, self.exit_y
        )
        for potion in self.potions:
            self.matrix[potion[0], potion[1]] = self.glitch_color(
                ColorTable.YELLOW, ColorTable.ORANGE, potion[0], potion[1]
            )
        for enemy in self.enemies:
            self.matrix[enemy[0], enemy[1]] = self.glitch_color(
                ColorTable.RED, ColorTable.PINK, enemy[0], enemy[1]
            )

        player_color = ColorTable.AQUA if not self.combat_mode else self.ability_color()
        self.matrix[self.player_x, self.player_y] = self.glitch_color(
            player_color, ColorTable.PINK, self.player_x, self.player_y
        )

        # Corner pixels expose mode, health, and selected ability.
        self.matrix[0, 0] = ColorTable.PURPLE if self.combat_mode else ColorTable.WHITE
        self.matrix[1, 0] = ColorTable.RED if self.hp == 1 else ColorTable.GREEN
        self.matrix[2, 0] = self.ability_color()
        self.matrix.apply()


if __name__ == "__main__":
    game = DungeonExe()
