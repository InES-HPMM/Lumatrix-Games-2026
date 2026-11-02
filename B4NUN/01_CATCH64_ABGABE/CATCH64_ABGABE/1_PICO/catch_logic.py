"""Getestete CATCH-64-Kernlogik ohne Hardwarezugriff.

Die Datei laeuft unveraendert unter MicroPython und normalem Python. Dadurch
kann die Jury die Paket- und Bedienlogik ohne angeschlossene LEDs testen.
"""

PROTOCOL_VERSION = 1

PAGE_LEAVE = 0
PAGE_DEPARTURE = 1
PAGE_PLATFORM = 2

FLAG_CANCELLED = 1
FLAG_PLATFORM_CHANGED = 2
DUE_SIGNAL_SECONDS = 8


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def clean_alnum(value):
    """ASCII-Filter ohne str.isalnum(), das auf MicroPython fehlt."""
    result = []
    for character in str(value).upper():
        if "A" <= character <= "Z" or "0" <= character <= "9":
            result.append(character)
    return "".join(result)


def validate_packet(packet):
    """Validiert jedes Feld, bevor fremde PC-Daten die LEDs steuern."""
    if not isinstance(packet, dict):
        raise ValueError("Paket ist kein Objekt")
    if packet.get("a") != "c" or packet.get("v") != PROTOCOL_VERSION:
        raise ValueError("Unbekanntes CATCH-64-Paket")

    connections = packet.get("c")
    if not isinstance(connections, list) or not 1 <= len(connections) <= 6:
        raise ValueError("Ein bis sechs Verbindungen erwartet")

    recommendation = packet.get("r")
    if not _is_int(recommendation) or not 0 <= recommendation < len(connections):
        raise ValueError("Ungueltiger Empfehlungsindex")

    for connection in connections:
        if not isinstance(connection, list) or len(connection) != 6:
            raise ValueError("Verbindung ist unvollstaendig")
        line, leave_s, departure_s, delay_min, platform, flags = connection
        if not isinstance(line, str) or not 1 <= len(line) <= 8:
            raise ValueError("Ungueltige Linie")
        if not _is_int(leave_s) or not -7200 <= leave_s <= 172800:
            raise ValueError("Ungueltige Aufbruchzeit")
        if not _is_int(departure_s) or not -7200 <= departure_s <= 172800:
            raise ValueError("Ungueltige Abfahrtszeit")
        if not _is_int(delay_min) or not -60 <= delay_min <= 600:
            raise ValueError("Ungueltige Verspaetung")
        if not isinstance(platform, str) or len(platform) > 5:
            raise ValueError("Ungueltiges Gleis")
        if not _is_int(flags) or not 0 <= flags <= 255:
            raise ValueError("Ungueltige Statusflags")

    event = packet.get("e")
    if event is not None:
        if (
            not isinstance(event, list)
            or len(event) != 2
            or event[0] not in ("D", "P", "X")
        ):
            raise ValueError("Ungueltiges Ereignis")
    return packet


def line_chunks(line):
    """Teilt lange Linien ohne nervoesen Laufschrift-Effekt in Zweiergruppen."""
    clean = clean_alnum(line)
    if not clean:
        return ("?",)
    return tuple(clean[index:index + 2] for index in range(0, len(clean), 2))


def minutes_remaining(initial_seconds, elapsed_ms):
    """Sichere, fuer Reisende konservativ aufgerundete Restminuten."""
    remaining = int(initial_seconds) - max(0, int(elapsed_ms // 1000))
    if remaining <= 0:
        return 0
    return min(99, (remaining + 59) // 60)


def seconds_remaining(initial_seconds, elapsed_ms):
    """Exakte Restsekunden fuer die letzte Minute vor dem Aufbruch."""
    remaining = int(initial_seconds) - max(0, int(elapsed_ms // 1000))
    return max(0, min(99, remaining))


def urgency(leave_minutes, cancelled=False):
    if cancelled:
        return "RED"
    if leave_minutes <= 1:
        return "RED"
    if leave_minutes <= 5:
        return "AMBER"
    return "GREEN"


def leave_phase(initial_seconds, elapsed_ms):
    """COUNTDOWN, kurzes Aufbruchssignal oder bereits verpasst."""
    remaining = int(initial_seconds) - max(0, int(elapsed_ms // 1000))
    if remaining > 0:
        return "COUNTDOWN"
    if remaining >= -DUE_SIGNAL_SECONDS:
        return "DUE"
    return "MISSED"


def next_reachable_index(connections, elapsed_ms, start_index=0):
    elapsed_seconds = max(0, int(elapsed_ms // 1000))
    for index in range(max(0, start_index), len(connections)):
        connection = connections[index]
        if not connection[5] & FLAG_CANCELLED and connection[1] - elapsed_seconds >= 0:
            return index
    return None


def demo_packet():
    """Offline-Daten: Die Hardware ist auch ohne Internet voll testbar."""
    return {
        "a": "c",
        "v": PROTOCOL_VERSION,
        "r": 1,
        "c": [
            ["S2", -60, 420, 0, "2", 0],
            ["S2", 300, 780, 0, "2", 0],
            ["IR35", 960, 1440, 3, "4", 0],
            ["S8", 1500, 1980, 0, "3", 0],
        ],
    }
