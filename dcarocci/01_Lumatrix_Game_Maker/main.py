# Lumatrix: ruhiges Raetselspiel fuer eine 8x8-LED-Matrix.
# Konfiguration und Regeln lassen sich hier anpassen.
COLORS = {
    'floor': (2, 3, 5), 'wall': (38, 38, 42), 'reset': (55, 3, 3),
    'player': (3, 12, 60), 'block': (55, 4, 27),
    'switch': (5, 32, 8), 'pad': (30, 5, 44),
    'door': (55, 30, 2), 'open': (12, 8, 1), 'goal': (2, 55, 16),
    'pulse': (3, 45, 55), 'active': (18, 60, 23)
}
DEBOUNCE_MS = 25
REPEAT_DELAY_MS = 280
REPEAT_INTERVAL_MS = 110
PULSE_STEP_MS = 65
DOOR_ANIMATION_MS = 180
LOOP_MS = 10


def led_index(x, y):
    return y * 8 + x


def screen_row(y):
    return 7 - y


def room_id(coord):
    return 'room_' + '_'.join(('m' + str(-v)) if v < 0 else str(v) for v in coord)


def in_room(x, y):
    return 0 <= x < 8 and 0 <= y < 8


class Game:
    # Definitionen bleiben unveraendert; Zustaende entstehen beim ersten Besuch.
    def __init__(self, world, start):
        self.world = world
        self.room = tuple(start['room'])
        self.x, self.y = start['x'], start['y']
        self.states = {}
        self.time = 0
        self.pulses = []
        self.door_flashes = {}
        self.evaluate(self.room, False)

    def state(self, coord):
        if coord not in self.states:
            blocks, switches, doors = {}, {}, {}
            for obj in self.world[coord]['objects']:
                kind, oid = obj['type'], obj['id']
                if kind == 'block':
                    blocks[oid] = [obj['x'], obj['y']]
                elif kind == 'switch':
                    switches[oid] = obj.get('initial', False)
                elif kind == 'door':
                    doors[oid] = obj.get('initialOpen', False)
            self.states[coord] = {
                'blocks': blocks, 'switches': switches, 'doors': doors,
                'pads': {}, 'latches': {}, 'conditions': {}, 'solved': False
            }
        return self.states[coord]

    def block_at(self, coord, x, y):
        for oid, pos in self.state(coord)['blocks'].items():
            if pos[0] == x and pos[1] == y:
                return oid
        return None

    def occupied(self, coord, x, y):
        return (self.room == coord and self.x == x and self.y == y) or self.block_at(coord, x, y) is not None

    def passable(self, coord, x, y):
        if not in_room(x, y) or self.world[coord]['layout'][y][x] == 'W':
            return False
        state = self.state(coord)
        for obj in self.world[coord]['objects']:
            if obj['type'] == 'door' and obj['x'] == x and obj['y'] == y:
                if not state['doors'][obj['id']]:
                    return False
        return True

    def evaluate(self, coord, animate=True):
        room, state = self.world[coord], self.state(coord)
        for obj in room['objects']:
            if obj['type'] == 'pad':
                state['pads'][obj['id']] = self.occupied(coord, obj['x'], obj['y'])
        desired = {}
        for link in room['connections']:
            values = [state['switches'].get(oid, state['pads'].get(oid, False)) for oid in link['sources']]
            condition = all(values) if link['mode'] == 'ALL' else any(values)
            cid = link['id']
            if condition and not state['conditions'].get(cid, False) and animate and link['path']:
                self.pulses.append((coord, link['path'], self.time))
            state['conditions'][cid] = condition
            if condition and link['latch']:
                state['latches'][cid] = True
            desired[link['target']] = desired.get(link['target'], False) or condition or state['latches'].get(cid, False)
        for obj in room['objects']:
            if obj['type'] != 'door':
                continue
            oid = obj['id']
            opened = desired.get(oid, obj.get('initialOpen', False))
            if not opened and self.occupied(coord, obj['x'], obj['y']):
                opened = True
            if state['doors'][oid] != opened and animate:
                self.door_flashes[(coord, oid)] = self.time
            state['doors'][oid] = opened

    def reset_room(self):
        coord = self.room
        del self.states[coord]
        self.x, self.y = self.world[coord]['spawn']
        self.pulses = [p for p in self.pulses if p[0] != coord]
        self.door_flashes = {k: v for k, v in self.door_flashes.items() if k[0] != coord}
        self.evaluate(coord, False)

    def move(self, dx, dy):
        if abs(dx) + abs(dy) != 1:
            return False
        old = self.room
        coord, x, y = old, self.x + dx, self.y + dy
        if not in_room(x, y):
            coord = (old[0] + dx, old[1] + dy)
            x, y = x % 8, y % 8
            if coord not in self.world:
                return False
            self.evaluate(coord, False)
        if not self.passable(coord, x, y):
            return False
        block = self.block_at(coord, x, y)
        if block is not None:
            bx, by = x + dx, y + dy
            if coord != old or not self.passable(coord, bx, by) or self.block_at(coord, bx, by) is not None:
                return False
            self.state(coord)['blocks'][block] = [bx, by]
        self.room, self.x, self.y = coord, x, y
        state = self.state(coord)
        for obj in self.world[coord]['objects']:
            if obj['type'] == 'switch' and obj['x'] == x and obj['y'] == y:
                state['switches'][obj['id']] = not state['switches'][obj['id']]
        if coord != old:
            self.evaluate(old)
        self.evaluate(coord)
        if self.world[coord]['layout'][y][x] == 'R' and not state['solved']:
            self.reset_room()
        elif coord == old:
            # Ein Ziel am Eingang loest den neuen Raum noch nicht.
            for obj in self.world[coord]['objects']:
                if obj['type'] == 'goal' and obj['x'] == x and obj['y'] == y:
                    state['solved'] = True
        return True

    def update(self, elapsed_ms):
        self.time += elapsed_ms
        self.pulses = [p for p in self.pulses if self.time - p[2] < len(p[1]) * PULSE_STEP_MS]
        self.door_flashes = {k: v for k, v in self.door_flashes.items() if self.time - v < DOOR_ANIMATION_MS}

    def frame(self):
        coord, room, state = self.room, self.world[self.room], self.state(self.room)
        pixels = [COLORS['floor']] * 64
        for y in range(8):
            for x in range(8):
                tile = room['layout'][y][x]
                color = COLORS['wall'] if tile == 'W' else COLORS['floor']
                if tile == 'R' and not state['solved']:
                    color = COLORS['reset']
                pixels[led_index(x, y)] = color
        for obj in room['objects']:
            kind, oid = obj['type'], obj['id']
            if kind == 'block':
                continue
            color = COLORS[kind]
            if kind == 'door':
                color = COLORS['open'] if state['doors'][oid] else COLORS['door']
                stamp = self.door_flashes.get((coord, oid))
                if stamp is not None and (self.time - stamp) // 45 % 2 == 0:
                    color = tuple(v // 2 for v in color)
            if state['switches'].get(oid, False) or state['pads'].get(oid, False):
                color = COLORS['active']
            pixels[led_index(obj['x'], obj['y'])] = color
        for pos in state['blocks'].values():
            pixels[led_index(pos[0], pos[1])] = COLORS['block']
        for pcoord, path, stamp in self.pulses:
            if pcoord == coord:
                step = (self.time - stamp) // PULSE_STEP_MS
                if step < len(path):
                    x, y = path[step]
                    pixels[led_index(x, y)] = COLORS['pulse']
        pixels[led_index(self.x, self.y)] = COLORS['player']
        return pixels


class Buttons:
    # Feste Prioritaet: rechts, hoch, runter, links; Druck bleibt frei.
    def __init__(self):
        self.raw = [False] * 5
        self.stable = [False] * 5
        self.changed = [0] * 5
        self.time = 0
        self.direction = None
        self.next_repeat = 0

    def update(self, pressed, elapsed_ms):
        self.time += elapsed_ms
        press_event = False
        for i in range(5):
            if pressed[i] != self.raw[i]:
                self.raw[i] = pressed[i]
                self.changed[i] = self.time
            if self.raw[i] != self.stable[i] and self.time - self.changed[i] >= DEBOUNCE_MS:
                self.stable[i] = self.raw[i]
                if i == 4 and self.stable[i]:
                    press_event = True
        selected = next((i for i in range(4) if self.stable[i]), None)
        step = None
        if selected != self.direction:
            self.direction = selected
            if selected is not None:
                step = selected
                self.next_repeat = self.time + REPEAT_DELAY_MS
        elif selected is not None and self.time >= self.next_repeat:
            step = selected
            self.next_repeat = self.time + REPEAT_INTERVAL_MS
        return {'direction': step, 'press': press_event}


WORLD = {(0, 0): {'coord': [0, 0], 'id': 'room_0_0', 'spawn': [1, 4], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'R', 'F', 'W', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'F'], ['W', 'F', 'F', 'W', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'door_1', 'type': 'door', 'x': 3, 'y': 4, 'initialOpen': False}, {'id': 'switch_1', 'type': 'switch', 'x': 1, 'y': 6, 'initial': False}, {'id': 'goal_1', 'type': 'goal', 'x': 7, 'y': 4}], 'connections': [{'id': 'link_1', 'sources': ['switch_1'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[2, 6], [2, 5], [2, 4], [3, 4]]}]}, (1, 0): {'coord': [1, 0], 'id': 'room_1_0', 'spawn': [1, 4], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'W', 'F', 'F', 'F', 'W'], ['F', 'F', 'F', 'W', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'F', 'F', 'W'], ['W', 'R', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'F', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 0, 'y': 4}, {'id': 'door_1', 'type': 'door', 'x': 6, 'y': 7, 'initialOpen': False}, {'id': 'door_2', 'type': 'door', 'x': 3, 'y': 6, 'initialOpen': False}, {'id': 'pad_1', 'type': 'pad', 'x': 6, 'y': 1}, {'id': 'block_1', 'type': 'block', 'x': 2, 'y': 4}], 'connections': [{'id': 'link_1', 'sources': ['pad_1'], 'target': 'door_2', 'mode': 'ALL', 'latch': True, 'path': [[5, 1], [4, 1], [3, 1], [2, 1], [2, 2], [2, 3], [2, 4], [2, 5], [2, 6], [3, 6], [4, 6], [5, 6], [6, 6], [6, 7]]}, {'id': 'link_2', 'sources': ['pad_1'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': []}]}, (1, 1): {'coord': [1, 1], 'id': 'room_1_1', 'spawn': [6, 1], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'W'], ['W', 'F', 'W', 'W', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'W', 'F', 'W'], ['W', 'W', 'F', 'W', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'W', 'F', 'W'], ['F', 'F', 'W', 'W', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 6, 'y': 0}, {'id': 'goal_2', 'type': 'goal', 'x': 0, 'y': 6}], 'connections': []}, (0, 1): {'coord': [0, 1], 'id': 'room_0_1', 'spawn': [6, 6], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'W'], ['F', 'F', 'F', 'F', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'F'], ['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'block_1', 'type': 'block', 'x': 6, 'y': 5}, {'id': 'pad_1', 'type': 'pad', 'x': 6, 'y': 1}, {'id': 'switch_1', 'type': 'switch', 'x': 2, 'y': 6, 'initial': False}, {'id': 'switch_2', 'type': 'switch', 'x': 2, 'y': 1, 'initial': False}, {'id': 'door_1', 'type': 'door', 'x': 0, 'y': 4, 'initialOpen': False}, {'id': 'door_2', 'type': 'door', 'x': 5, 'y': 6, 'initialOpen': False}, {'id': 'goal_1', 'type': 'goal', 'x': 7, 'y': 6}], 'connections': [{'id': 'link_1', 'sources': ['pad_1'], 'target': 'door_2', 'mode': 'ALL', 'latch': True, 'path': [[6, 2], [6, 3], [6, 4], [6, 5], [6, 6], [5, 6]]}, {'id': 'link_2', 'sources': ['switch_1', 'switch_2'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[2, 5], [2, 2], [2, 4], [2, 3], [1, 4], [0, 4]]}]}, (-1, 1): {'coord': [-1, 1], 'id': 'room_m1_1', 'spawn': [6, 4], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'F', 'W'], ['W', 'R', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'F'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'R', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 7, 'y': 4}, {'id': 'door_1', 'type': 'door', 'x': 6, 'y': 0, 'initialOpen': False}, {'id': 'pad_1', 'type': 'pad', 'x': 4, 'y': 2}, {'id': 'pad_2', 'type': 'pad', 'x': 2, 'y': 4}, {'id': 'pad_3', 'type': 'pad', 'x': 4, 'y': 6}, {'id': 'block_1', 'type': 'block', 'x': 4, 'y': 4}], 'connections': [{'id': 'link_1', 'sources': ['pad_3'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[4, 6], [5, 6], [5, 5], [5, 4], [5, 3], [6, 3], [6, 2], [6, 1], [6, 0]]}]}, (-1, 0): {'coord': [-1, 0], 'id': 'room_m1_0', 'spawn': [6, 6], 'layout': [['W', 'W', 'W', 'F', 'W', 'W', 'W', 'W'], ['W', 'R', 'F', 'F', 'W', 'F', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'W', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'F', 'W']], 'objects': [{'id': 'block_1', 'type': 'block', 'x': 4, 'y': 3}, {'id': 'pad_1', 'type': 'pad', 'x': 4, 'y': 2}, {'id': 'door_1', 'type': 'door', 'x': 3, 'y': 0, 'initialOpen': False}, {'id': 'goal_1', 'type': 'goal', 'x': 6, 'y': 7}, {'id': 'switch_1', 'type': 'switch', 'x': 1, 'y': 6, 'initial': False}, {'id': 'door_2', 'type': 'door', 'x': 4, 'y': 4, 'initialOpen': False}], 'connections': [{'id': 'link_1', 'sources': ['switch_1'], 'target': 'door_2', 'mode': 'ALL', 'latch': True, 'path': [[2, 6], [3, 6], [4, 6], [4, 5], [4, 4]]}, {'id': 'link_2', 'sources': ['pad_1'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[4, 3], [4, 4], [4, 5], [3, 5], [2, 5], [2, 4], [2, 3], [2, 2], [2, 1], [3, 1], [3, 0]]}]}, (-1, -1): {'coord': [-1, -1], 'id': 'room_m1_m1', 'spawn': [3, 6], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'W', 'W', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'W'], ['W', 'W', 'F', 'W', 'W', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'F'], ['W', 'F', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'F', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 3, 'y': 7}, {'id': 'door_1', 'type': 'door', 'x': 7, 'y': 4, 'initialOpen': False}, {'id': 'door_2', 'type': 'door', 'x': 5, 'y': 1, 'initialOpen': False}, {'id': 'door_3', 'type': 'door', 'x': 2, 'y': 3, 'initialOpen': False}, {'id': 'door_4', 'type': 'door', 'x': 1, 'y': 5, 'initialOpen': False}, {'id': 'switch_1', 'type': 'switch', 'x': 6, 'y': 6, 'initial': False}, {'id': 'switch_2', 'type': 'switch', 'x': 4, 'y': 4, 'initial': False}, {'id': 'switch_3', 'type': 'switch', 'x': 5, 'y': 3, 'initial': False}, {'id': 'switch_4', 'type': 'switch', 'x': 1, 'y': 1, 'initial': False}], 'connections': [{'id': 'link_1', 'sources': ['switch_1'], 'target': 'door_4', 'mode': 'ALL', 'latch': True, 'path': [[5, 6], [4, 6], [3, 6], [2, 6], [1, 6], [1, 5]]}, {'id': 'link_2', 'sources': ['switch_2'], 'target': 'door_3', 'mode': 'ALL', 'latch': True, 'path': [[3, 4], [2, 4], [2, 3]]}, {'id': 'link_3', 'sources': ['switch_4'], 'target': 'door_2', 'mode': 'ALL', 'latch': True, 'path': [[1, 2], [2, 2], [3, 2], [4, 2], [4, 1], [5, 1]]}, {'id': 'link_4', 'sources': ['switch_3'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[6, 3], [6, 4], [7, 4]]}]}, (0, -1): {'coord': [0, -1], 'id': 'room_0_m1', 'spawn': [1, 1], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'F', 'F', 'W', 'F', 'F'], ['W', 'F', 'W', 'W', 'F', 'W', 'F', 'W'], ['W', 'F', 'W', 'W', 'F', 'F', 'F', 'W'], ['F', 'F', 'W', 'W', 'W', 'F', 'W', 'W'], ['W', 'W', 'W', 'W', 'W', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 0, 'y': 4}, {'id': 'switch_1', 'type': 'switch', 'x': 1, 'y': 6, 'initial': False}, {'id': 'door_1', 'type': 'door', 'x': 7, 'y': 1, 'initialOpen': False}], 'connections': [{'id': 'link_1', 'sources': ['switch_1'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[2, 6], [3, 6], [4, 6], [5, 6], [6, 6], [6, 5], [5, 5], [5, 4], [5, 3], [6, 3], [6, 2], [6, 1], [7, 1]]}]}, (1, -1): {'coord': [1, -1], 'id': 'room_1_m1', 'spawn': [1, 1], 'layout': [['W', 'W', 'W', 'F', 'W', 'F', 'W', 'W'], ['F', 'F', 'W', 'F', 'W', 'F', 'F', 'W'], ['W', 'F', 'W', 'F', 'W', 'F', 'F', 'W'], ['W', 'F', 'W', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'W', 'F', 'W', 'F', 'F', 'W'], ['W', 'F', 'W', 'F', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'W', 'W', 'F', 'F'], ['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 0, 'y': 1}, {'id': 'goal_2', 'type': 'goal', 'x': 3, 'y': 0}, {'id': 'goal_3', 'type': 'goal', 'x': 5, 'y': 0}, {'id': 'switch_1', 'type': 'switch', 'x': 4, 'y': 5, 'initial': False}, {'id': 'switch_2', 'type': 'switch', 'x': 5, 'y': 4, 'initial': False}, {'id': 'door_1', 'type': 'door', 'x': 4, 'y': 3, 'initialOpen': False}, {'id': 'door_2', 'type': 'door', 'x': 7, 'y': 6, 'initialOpen': False}], 'connections': [{'id': 'link_1', 'sources': ['switch_2'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[5, 3], [4, 3]]}, {'id': 'link_2', 'sources': ['switch_1'], 'target': 'door_2', 'mode': 'ALL', 'latch': True, 'path': [[3, 5], [3, 4], [3, 3], [4, 3], [5, 3], [6, 3], [6, 4], [6, 5], [6, 6], [7, 6]]}]}, (1, -2): {'coord': [1, -2], 'id': 'room_1_m2', 'spawn': [3, 6], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'F', 'W', 'F', 'F', 'F'], ['W', 'F', 'W', 'F', 'W', 'F', 'W', 'W'], ['W', 'F', 'W', 'F', 'F', 'F', 'W', 'W'], ['W', 'F', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'W', 'W', 'W', 'F', 'F', 'F'], ['W', 'F', 'F', 'F', 'W', 'F', 'W', 'W'], ['W', 'W', 'W', 'F', 'W', 'F', 'W', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 3, 'y': 7}, {'id': 'goal_2', 'type': 'goal', 'x': 5, 'y': 7}, {'id': 'goal_3', 'type': 'goal', 'x': 7, 'y': 5}, {'id': 'goal_4', 'type': 'goal', 'x': 7, 'y': 1}], 'connections': []}, (2, -2): {'coord': [2, -2], 'id': 'room_2_m2', 'spawn': [1, 1], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['F', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'W', 'W', 'F', 'W', 'W', 'W', 'W'], ['F', 'F', 'W', 'F', 'W', 'F', 'R', 'W'], ['W', 'F', 'F', 'F', 'W', 'R', 'F', 'W'], ['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'pad_1', 'type': 'pad', 'x': 5, 'y': 5}, {'id': 'pad_2', 'type': 'pad', 'x': 6, 'y': 6}, {'id': 'door_1', 'type': 'door', 'x': 0, 'y': 5, 'initialOpen': False}, {'id': 'goal_1', 'type': 'goal', 'x': 0, 'y': 1}, {'id': 'switch_1', 'type': 'switch', 'x': 1, 'y': 3, 'initial': False}], 'connections': [{'id': 'link_1', 'sources': ['switch_1'], 'target': 'door_1', 'mode': 'ALL', 'latch': False, 'path': [[2, 3], [3, 3], [3, 4], [3, 5], [3, 6], [2, 6], [1, 6], [1, 5], [0, 5]]}]}, (2, -1): {'coord': [2, -1], 'id': 'room_2_m1', 'spawn': [1, 6], 'layout': [['W', 'W', 'W', 'W', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'R', 'W'], ['F', 'F', 'W', 'F', 'W', 'W', 'W', 'W'], ['W', 'W', 'W', 'F', 'W', 'W', 'W', 'W']], 'objects': [{'id': 'goal_1', 'type': 'goal', 'x': 0, 'y': 6}, {'id': 'door_1', 'type': 'door', 'x': 3, 'y': 7, 'initialOpen': False}, {'id': 'door_2', 'type': 'door', 'x': 3, 'y': 6, 'initialOpen': False}, {'id': 'block_2', 'type': 'block', 'x': 4, 'y': 4}, {'id': 'pad_1', 'type': 'pad', 'x': 6, 'y': 1}, {'id': 'pad_2', 'type': 'pad', 'x': 1, 'y': 1}, {'id': 'block_3', 'type': 'block', 'x': 3, 'y': 4}], 'connections': [{'id': 'link_1', 'sources': ['pad_2'], 'target': 'door_1', 'mode': 'ALL', 'latch': True, 'path': [[2, 1], [3, 1], [3, 2], [3, 3], [3, 4], [3, 5], [3, 6], [3, 7]]}, {'id': 'link_2', 'sources': ['pad_1'], 'target': 'door_2', 'mode': 'ALL', 'latch': True, 'path': [[5, 1], [4, 1], [3, 1], [3, 2], [3, 3], [3, 4], [3, 5], [3, 6]]}]}, (2, 0): {'coord': [2, 0], 'id': 'room_2_0', 'spawn': [3, 1], 'layout': [['W', 'W', 'W', 'F', 'W', 'W', 'W', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'W', 'W', 'F', 'F', 'W'], ['W', 'F', 'W', 'F', 'F', 'W', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['W', 'F', 'F', 'F', 'F', 'F', 'F', 'W'], ['F', 'W', 'W', 'W', 'W', 'W', 'W', 'F']], 'objects': [{'id': 'door_1', 'type': 'door', 'x': 7, 'y': 7, 'initialOpen': False}, {'id': 'door_2', 'type': 'door', 'x': 0, 'y': 7, 'initialOpen': False}, {'id': 'switch_1', 'type': 'switch', 'x': 2, 'y': 5, 'initial': False}, {'id': 'switch_2', 'type': 'switch', 'x': 5, 'y': 5, 'initial': False}, {'id': 'goal_1', 'type': 'goal', 'x': 3, 'y': 0}], 'connections': [{'id': 'link_1', 'sources': ['switch_1'], 'target': 'door_2', 'mode': 'ALL', 'latch': False, 'path': [[2, 4], [3, 4], [3, 5], [3, 6], [2, 6], [1, 6], [1, 5], [1, 4], [2, 4], [3, 4], [3, 5], [3, 6], [2, 6], [1, 6], [0, 6], [0, 7]]}, {'id': 'link_2', 'sources': ['switch_2'], 'target': 'door_1', 'mode': 'ALL', 'latch': False, 'path': [[5, 4], [6, 4], [6, 5], [6, 6], [5, 6], [4, 6], [4, 5], [4, 4], [5, 4], [6, 4], [6, 5], [6, 6], [7, 6], [7, 7]]}]}}
START = {'room': [0, 0], 'x': 1, 'y': 4}

# Hardware erst auf dem Pico starten.
def run():
    from machine import Pin
    from neopixel import NeoPixel
    from utime import ticks_ms, ticks_diff, sleep_ms

    np = NeoPixel(Pin(19, Pin.OUT), 64)
    rechts = Pin(2, Pin.IN, Pin.PULL_UP)
    hoch = Pin(3, Pin.IN, Pin.PULL_UP)
    runter = Pin(6, Pin.IN, Pin.PULL_UP)
    links = Pin(7, Pin.IN, Pin.PULL_UP)
    druck = Pin(8, Pin.IN, Pin.PULL_UP)
    pins = (rechts, hoch, runter, links, druck)
    directions = ((1, 0), (0, 1), (0, -1), (-1, 0))
    buttons = Buttons()
    game = Game(WORLD, START)
    previous = ticks_ms()
    while True:
        now = ticks_ms()
        elapsed = ticks_diff(now, previous)
        previous = now
        game.update(elapsed)
        event = buttons.update([pin.value() == 0 for pin in pins], elapsed)
        if event['direction'] is not None:
            dx, dy = directions[event['direction']]
            game.move(dx, dy)
        # event['press'] ist entprellt und absichtlich unbelegt.
        for i, color in enumerate(game.frame()):
            np[i] = color
        np.write()
        sleep_ms(LOOP_MS)


if __name__ == '__main__':
    run()
