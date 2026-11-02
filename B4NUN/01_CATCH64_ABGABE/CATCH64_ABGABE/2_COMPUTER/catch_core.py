"""Reine CATCH-64-Logik fuer Berechnung, Tests und USB-Protokoll."""

from datetime import datetime
import math
import re


PROTOCOL_VERSION = 1
FLAG_CANCELLED = 1
FLAG_PLATFORM_CHANGED = 2
DUE_SIGNAL_SECONDS = 8


def _timestamp(iso_value):
    if not iso_value:
        return None
    # Die OeV-API liefert je nach Quelle sowohl +02:00 als auch +0200.
    # datetime akzeptiert auf aelteren Jury-Python-Versionen nur die erste Form.
    if re.search(r"[+-]\d{4}$", iso_value):
        iso_value = iso_value[:-2] + ":" + iso_value[-2:]
    return datetime.fromisoformat(iso_value).timestamp()


def _first_journey(raw_connection):
    for section in raw_connection.get("sections") or []:
        journey = section.get("journey")
        if journey:
            return journey
    return {}


def connection_line(raw_connection):
    products = raw_connection.get("products") or []
    if products and products[0]:
        text = str(products[0])
    else:
        journey = _first_journey(raw_connection)
        text = "{}{}".format(journey.get("category") or "", journey.get("number") or "")
    clean = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    return clean[:8] or "OV"


def is_cancelled(raw_connection):
    if raw_connection.get("cancelled") or raw_connection.get("canceled"):
        return True
    journey = _first_journey(raw_connection)
    return bool(journey.get("cancelled") or journey.get("canceled"))


def normalize_connection(raw_connection, now_ts, walk_minutes, reserve_minutes):
    """Reduziert eine grosse API-Antwort auf die sechs wirklich benoetigten Werte."""
    origin = raw_connection.get("from") or {}
    prognosis = origin.get("prognosis") or {}
    planned_ts = origin.get("departureTimestamp")
    if planned_ts is None:
        planned_ts = _timestamp(origin.get("departure"))
    if planned_ts is None:
        raise ValueError("Verbindung ohne Abfahrtszeit")

    predicted_ts = _timestamp(prognosis.get("departure"))
    delay = origin.get("delay")
    delay = int(delay) if isinstance(delay, (int, float)) else 0
    if predicted_ts is None:
        predicted_ts = float(planned_ts) + delay * 60

    planned_platform = str(origin.get("platform") or "")
    predicted_platform = str(prognosis.get("platform") or "")
    platform = predicted_platform or planned_platform
    platform_changed = bool(
        predicted_platform and planned_platform and predicted_platform != planned_platform
    )
    cancelled = is_cancelled(raw_connection)
    departure_s = int(math.floor(predicted_ts - now_ts))
    leave_s = departure_s - int((walk_minutes + reserve_minutes) * 60)

    flags = 0
    if cancelled:
        flags |= FLAG_CANCELLED
    if platform_changed:
        flags |= FLAG_PLATFORM_CHANGED

    return {
        "line": connection_line(raw_connection),
        "leave_s": leave_s,
        "departure_s": departure_s,
        "delay": max(-60, min(600, delay)),
        "platform": platform[:5],
        "flags": flags,
        "planned_ts": int(planned_ts),
        "predicted_ts": int(predicted_ts),
    }


def normalize_connections(api_response, now_ts, walk_minutes, reserve_minutes, limit=6):
    normalized = []
    for raw in api_response.get("connections") or []:
        try:
            connection = normalize_connection(
                raw, now_ts, walk_minutes, reserve_minutes
            )
        except (TypeError, ValueError, OverflowError):
            continue
        if connection["departure_s"] >= -120:
            normalized.append(connection)
        if len(normalized) >= limit:
            break
    if not normalized:
        raise ValueError("Keine brauchbaren Verbindungen erhalten")
    return normalized


def recommended_index(connections):
    """Erste erreichbare Verbindung; 00 ist bereits der Aufbruchsmoment.

    Die kurze Toleranz ist nur die Sichtdauer des roten Pfeils. Sie ist keine
    zusaetzliche Reserve und wird dem Countdown nicht zugerechnet.
    """
    for index, connection in enumerate(connections):
        if (
            not connection["flags"] & FLAG_CANCELLED
            and connection["leave_s"] >= -DUE_SIGNAL_SECONDS
        ):
            return index
    for index, connection in enumerate(connections):
        if not connection["flags"] & FLAG_CANCELLED:
            return index
    return 0


def event_between(previous_packet, connections, recommendation):
    """Erkennt nur Aenderungen, die einen Menschen wirklich interessieren."""
    if not previous_packet:
        return None
    previous_connections = previous_packet.get("_normalized") or []
    if not previous_connections:
        return None
    previous = previous_connections[previous_packet["r"]]
    current = connections[recommendation]

    # Bei einem Ausfall springt die Empfehlung bereits zur naechsten Fahrt.
    # Darum suchen wir die bisher empfohlene Fahrt zuerst in der neuen Liste.
    previous_trip_now = None
    for candidate in connections:
        if (
            candidate["line"] == previous["line"]
            and abs(candidate["planned_ts"] - previous["planned_ts"]) <= 60
        ):
            previous_trip_now = candidate
            break
    if (
        previous_trip_now
        and not previous["flags"] & FLAG_CANCELLED
        and previous_trip_now["flags"] & FLAG_CANCELLED
    ):
        return ["X", 0]

    same_trip = (
        previous["line"] == current["line"]
        and abs(previous["planned_ts"] - current["planned_ts"]) <= 60
    )
    if same_trip and current["flags"] & FLAG_PLATFORM_CHANGED and previous["platform"] != current["platform"]:
        return ["P", current["platform"]]
    if same_trip and current["delay"] > previous["delay"]:
        return ["D", current["delay"]]
    return None


def make_packet(connections, previous_packet=None):
    recommendation = recommended_index(connections)
    packet = {
        "a": "c",
        "v": PROTOCOL_VERSION,
        "r": recommendation,
        "c": [
            [
                item["line"],
                item["leave_s"],
                item["departure_s"],
                item["delay"],
                item["platform"],
                item["flags"],
            ]
            for item in connections
        ],
        # Nur lokal fuer die naechste Aenderungserkennung; wird vor USB entfernt.
        "_normalized": connections,
    }
    event = event_between(previous_packet, connections, recommendation)
    if event:
        packet["e"] = event
    return packet


def usb_packet(packet):
    return {key: value for key, value in packet.items() if not key.startswith("_")}


def demo_packets():
    """Vier reproduzierbare Jury-Szenarien fuer den optionalen Demomodus."""
    base = [
        {"line": "S2", "leave_s": 300, "departure_s": 780, "delay": 0, "platform": "2", "flags": 0, "planned_ts": 1000, "predicted_ts": 1000},
        {"line": "IR35", "leave_s": 960, "departure_s": 1440, "delay": 0, "platform": "4", "flags": 0, "planned_ts": 1660, "predicted_ts": 1660},
        {"line": "S8", "leave_s": 1500, "departure_s": 1980, "delay": 0, "platform": "3", "flags": 0, "planned_ts": 2200, "predicted_ts": 2200},
    ]
    normal = make_packet(base)
    delayed_connections = [dict(item) for item in base]
    delayed_connections[0].update(leave_s=540, departure_s=1020, delay=4, predicted_ts=1240)
    delayed = make_packet(delayed_connections, normal)
    platform_connections = [dict(item) for item in delayed_connections]
    platform_connections[0].update(platform="4", flags=FLAG_PLATFORM_CHANGED)
    platform = make_packet(platform_connections, delayed)
    cancelled_connections = [dict(item) for item in platform_connections]
    cancelled_connections[0].update(flags=FLAG_CANCELLED)
    cancelled = make_packet(cancelled_connections, platform)
    return [normal, delayed, platform, cancelled]
