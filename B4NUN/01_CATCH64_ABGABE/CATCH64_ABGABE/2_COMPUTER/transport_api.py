"""Kleiner, schluesselloser Client fuer Schweizer OeV-Verbindungen."""

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

try:
    import certifi
except ImportError:
    certifi = None


BASE_URL = "https://transport.opendata.ch/v1/connections"
LOCATIONS_URL = "https://transport.opendata.ch/v1/locations"
STATIONBOARD_URL = "https://transport.opendata.ch/v1/stationboard"
_LOCATION_CACHE = {}


def _ssl_context():
    # certifi macht die HTTPS-Pruefung auf Windows, Ubuntu und macOS identisch.
    # Ohne installiertes Paket bleibt der sichere Systemstandard aktiv.
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def connections_url(config):
    params = {
        "from": config["from"],
        "to": config["to"],
        # Die API erlaubt maximal 16. Weniger wuerde spaetere, aber noch
        # erreichbare Verbindungen bereits vor unserer Auswahl abschneiden.
        "limit": 16,
    }
    if config.get("direct_only"):
        params["direct"] = 1
    return BASE_URL + "?" + urllib.parse.urlencode(params)


def _request_json(url, timeout):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CATCH64/1.0 (Lumatrix Games 2026)"},
    )
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        if response.status != 200:
            raise RuntimeError("OeV-Dienst HTTP {}".format(response.status))
        return json.loads(response.read().decode("utf-8"))


def _name(value):
    return " ".join(str(value or "").casefold().split())


def _near(first, second):
    """Bahnhof und gleichnamige Bushaltestelle nur zusammenfassen, wenn sie nah sind."""
    try:
        a = first["coordinate"]
        b = second["coordinate"]
        return abs(float(a["x"]) - float(b["x"])) < 0.02 and abs(float(a["y"]) - float(b["y"])) < 0.02
    except (KeyError, TypeError, ValueError):
        return False


def choose_stations(query, stations):
    """Liefert den exakten Halt plus einen direkt benachbarten Bahnhofsknoten.

    Schweizer Bahnhoefe besitzen oft zwei IDs: z.B. ``Waedenswil`` fuer die
    Bahn und ``Waedenswil, Bahnhof`` fuer die Buskante. CATCH 64 muss beide
    beruecksichtigen, sonst fehlen je nach Eingabe entweder Zuege oder Busse.
    """
    wanted = _name(query)
    exact = next((item for item in stations if _name(item.get("name")) == wanted), None)
    primary = exact or (stations[0] if stations else None)
    if not primary:
        return []

    selected = [primary]
    primary_name = _name(primary.get("name"))
    base = primary_name[:-9] if primary_name.endswith(", bahnhof") else primary_name
    aliases = {base, base + ", bahnhof"}
    for candidate in stations:
        if candidate is primary:
            continue
        if _name(candidate.get("name")) in aliases and _near(primary, candidate):
            selected.append(candidate)
    return selected[:2]


def resolve_stations(query, timeout=10):
    cache_key = _name(query)
    if cache_key in _LOCATION_CACHE:
        return _LOCATION_CACHE[cache_key]
    url = LOCATIONS_URL + "?" + urllib.parse.urlencode(
        {"query": query, "type": "station"}
    )
    response = _request_json(url, timeout)
    stations = choose_stations(query, response.get("stations") or [])
    if not stations:
        raise ValueError("Haltestelle nicht gefunden: {}".format(query))
    _LOCATION_CACHE[cache_key] = stations
    return stations


def stationboard_url(station):
    params = {"id": station["id"], "limit": 96}
    return STATIONBOARD_URL + "?" + urllib.parse.urlencode(params)


def _station_matches(station, targets):
    if not station:
        return False
    station_id = str(station.get("id") or "").lstrip("0")
    station_name = _name(station.get("name"))
    for target in targets:
        target_id = str(target.get("id") or "").lstrip("0")
        if station_id and target_id and station_id == target_id:
            return True
        if station_name and station_name == _name(target.get("name")):
            return True
    return False


def _line(category, number):
    return re.sub(r"[^A-Za-z0-9]", "", "{}{}".format(category or "", number or "")).upper() or "OV"


def stationboard_connections(board, targets):
    """Wandelt alle direkten Abfahrten zum Ziel ins bestehende Datenmodell um."""
    result = []
    for departure in board.get("stationboard") or []:
        pass_list = departure.get("passList") or []
        if not any(_station_matches(item.get("station") or {}, targets) for item in pass_list):
            continue
        stop = dict(departure.get("stop") or {})
        category = departure.get("category") or ""
        number = departure.get("number") or ""
        cancelled = bool(departure.get("cancelled") or departure.get("canceled"))
        journey = {
            "category": category,
            "number": number,
            "cancelled": cancelled,
        }
        result.append({
            "from": stop,
            "products": [_line(category, number)],
            "sections": [{"journey": journey}],
            "cancelled": cancelled,
        })
    return result


def _departure_timestamp(connection):
    origin = connection.get("from") or {}
    value = origin.get("departureTimestamp")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _connection_key(connection):
    products = connection.get("products") or []
    product = products[0] if products else ""
    return re.sub(r"[^A-Za-z0-9]", "", str(product)).upper(), _departure_timestamp(connection)


def merge_connections(*groups):
    """Mischt Fahrplaner und Abfahrtsmonitor chronologisch ohne Doppelungen."""
    result = []
    seen = set()
    for group in groups:
        for connection in group or []:
            key = _connection_key(connection)
            if key in seen:
                continue
            seen.add(key)
            result.append(connection)
    result.sort(key=_departure_timestamp)
    return result


def fetch_connections(config, timeout=15):
    # Der Fahrplaner liefert die schnellsten Routen, laesst aber langsamere
    # Direktzuege (z.B. die S8 Waedenswil–Zuerich HB) bewusst weg.
    planner = _request_json(connections_url(config), timeout)
    direct = []
    try:
        origins = resolve_stations(config["from"], timeout)
        targets = resolve_stations(config["to"], timeout)
        for origin in origins:
            board = _request_json(stationboard_url(origin), timeout)
            direct.extend(stationboard_connections(board, targets))
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        # Der Fahrplaner bleibt ein sicherer Fallback, falls ein Bahnhofsknoten
        # oder der Abfahrtsmonitor voruebergehend nicht erreichbar ist.
        direct = []

    response = dict(planner)
    response["connections"] = merge_connections(
        direct, planner.get("connections") or []
    )
    return response


def fetch_locations(query, timeout=10):
    url = LOCATIONS_URL + "?" + urllib.parse.urlencode({"query": query})
    data = _request_json(url, timeout)
    names = []
    for station in data.get("stations") or []:
        name = station.get("name")
        if name and name not in names:
            names.append(name)
        if len(names) >= 8:
            break
    return names
