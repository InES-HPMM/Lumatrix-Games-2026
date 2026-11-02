"""Poll the original Workshop Button pins; debounce without IRQ callbacks."""

NAMES = ("up", "down", "left", "right", "center", "switch")


class Controls:
    def __init__(self, buttons):
        self.pins = [getattr(buttons, name) for name in NAMES]
        self.stable = [pin.value() for pin in self.pins]
        self.raw = self.stable[:]
        self.ages = [0] * len(NAMES)

    @property
    def sleeping(self):
        return self.stable[-1] == 0

    def update(self, dt):
        events = []
        for i, pin in enumerate(self.pins):
            value = pin.value()
            if value != self.raw[i]:
                self.raw[i] = value
                self.ages[i] = 0
            else:
                self.ages[i] += dt
            if value != self.stable[i] and self.ages[i] >= 40:
                self.stable[i] = value
                if value == 0 and NAMES[i] != "switch":
                    events.append(NAMES[i])
        return events


DOUBLE_MS = 400


class DoublePress:
    """Centre button: single press -> "mic" (after DOUBLE_MS), double press -> "center"."""

    def __init__(self):
        self.wait = 0

    def update(self, events, dt):
        out = []
        for event in events:
            if event != "center":
                out.append(event)
            elif self.wait:
                self.wait = 0
                out.append("center")
            else:
                self.wait = DOUBLE_MS + dt  # The countdown starts with the next frame.
        if self.wait:
            self.wait -= dt
            if self.wait <= 0:
                self.wait = 0
                out.append("mic")
        return out
