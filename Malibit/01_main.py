
import time
import math
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import serial
from serial.tools import list_ports


# ---------- Einstellungen ----------

CENTER_LAT = 47.53
CENTER_LON = 8.77

GRID_SIZE = 8

PIXEL_SIZE_KM = 10
MIN_PIXEL_SIZE_KM = 5
MAX_PIXEL_SIZE_KM = 50
PIXEL_STEP_KM = 5

JOYSTICK_UPDATE_DELAY = 1.0  # Sekunden

UPDATE_SECONDS = 15 * 60
TIMEZONE = ZoneInfo("Europe/Zurich")

SERIAL_PORT = "COM34"
BAUD_RATE = 115200

BRIGHTNESS = 0.15

MIN_BRIGHTNESS = 0.1
MAX_BRIGHTNESS = 1.0
BRIGHTNESS_STEP = 0.05

API_URL = "https://api.open-meteo.com/v1/forecast"


# ---------- LED-Zuordnung ----------

def led_index(x, y):
    """x: Westen -> Osten, y: Norden -> Süden.
    Obere Zeile: LEDs 56-63.
    Untere Zeile: LEDs 0-7.
    """
    physical_row = 7 - y
    return physical_row * 8 + x


# ---------- Geografisches Raster ----------

def create_grid(pixel_size_km):
    """Erzeugt 64 Zellmittelpunkte für die aktuelle Pixelgrösse."""
    points = []

    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            east_km = (x - 3.5) * pixel_size_km
            north_km = (3.5 - y) * pixel_size_km

            lat = CENTER_LAT + north_km / 111.32
            lon = CENTER_LON + east_km / (
                111.32 * math.cos(
                    math.radians(CENTER_LAT)
                )
            )

            points.append({
                "x": x,
                "y": y,
                "lat": lat,
                "lon": lon,
            })

    return points


# ---------- Tag-Nacht-Übergang ----------

def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def daylight_factor(now, sunrise, sunset):
    """Sanfter Übergang während je 45 Minuten bei Sonnenauf-
    und -untergang.
    """
    transition = 45 * 60

    rise = sunrise.hour * 3600 + sunrise.minute * 60
    setting = sunset.hour * 3600 + sunset.minute * 60

    seconds = (
        now.hour * 3600
        + now.minute * 60
        + now.second
    )

    morning = smoothstep(
        (seconds - (rise - transition)) / (2 * transition)
    )

    evening = 1.0 - smoothstep(
        (seconds - (setting - transition)) / (2 * transition)
    )

    return min(morning, evening)


# ---------- Farben ----------


def get_pixel_color(cloud_cover, precipitation, snowfall, day_factor):
    """Schnee: weiss. Danach Regen, Wolken und klarer Himmel."""

    # Schnee hat höchste Priorität.
    if snowfall is not None and snowfall > 0:
        return (255, 255, 255)

    # Regen hat Vorrang vor Wolken.
    if precipitation > 5:
        return (180, 0, 255)       # Violett
    elif precipitation >= 2:
        return (255, 0, 0)         # Rot
    elif precipitation >= 1:
        return (255, 100, 0)       # Orange
    elif precipitation > 0:
        return (0, 255, 0)         # Grün

    # Klarer Himmel: Nacht schwarz, Tag blau.
    if cloud_cover < 0.5:
        return (
            0,
            round(80 * day_factor),
            round(255 * day_factor),
        )

    # Wolken als Graustufen.
    grey = round(150 * (cloud_cover / 100) ** 1.5)

    # Bewölkte Pixel nie vollständig schwarz darstellen
    grey = max(50, min(150, grey))

    return (grey, grey, grey)


def apply_brightness(rgb):
    return tuple(
        max(0, min(255, round(channel * BRIGHTNESS)))
        for channel in rgb
    )


# ---------- Wetter-API ----------

def fetch_weather(points):
    """Lädt die Wetterdaten für alle 64 Zellmittelpunkte."""

    params = {
        "latitude": ",".join(
            f"{p['lat']:.5f}" for p in points
        ),
        "longitude": ",".join(
            f"{p['lon']:.5f}" for p in points
        ),
        "hourly": "cloud_cover,precipitation,snowfall",
        "daily": "sunrise,sunset",
        "timezone": "Europe/Zurich",
        "forecast_days": 2,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict):
        data = [data]

    if len(data) != len(points):
        raise ValueError(
            f"Erwartete {len(points)} Wetterzellen, "
            f"API lieferte {len(data)}."
        )

    now = datetime.now(TIMEZONE)
    hour_key = now.strftime("%Y-%m-%dT%H:00")

    pixel_colors = [(0, 0, 0)] * 64

    for point, weather in zip(points, data):
        hourly = weather["hourly"]

        if hour_key not in hourly["time"]:
            raise ValueError(
                f"Stundenwert {hour_key} nicht verfügbar."
            )

        hour_index = hourly["time"].index(hour_key)

        cloud = hourly["cloud_cover"][hour_index]
        rain = hourly["precipitation"][hour_index]
        snow = hourly["snowfall"][hour_index]

        # Fehlende Daten nicht als klares Wetter anzeigen.
        if cloud is None or rain is None or snow is None:
            continue

        daily = weather["daily"]
        today = now.strftime("%Y-%m-%d")

        if today not in daily["time"]:
            raise ValueError(
                "Sonnenaufgang/-untergang fehlt."
            )

        day_index = daily["time"].index(today)

        sunrise = datetime.fromisoformat(
            daily["sunrise"][day_index]
        )
        sunset = datetime.fromisoformat(
            daily["sunset"][day_index]
        )

        factor = daylight_factor(
            now.replace(tzinfo=None),
            sunrise,
            sunset,
        )

        rgb = get_pixel_color(cloud, rain, snow, factor)

        pixel_colors[
            led_index(point["x"], point["y"])
        ] = rgb

    return pixel_colors


# ---------- USB-Kommunikation ----------

def send_pixels(connection, colors):
    """Passt die Helligkeit an und sendet 64 RGB-Pixel."""

    payload = "".join(
        f"{r:02x}{g:02x}{b:02x}"
        for r, g, b in (
            apply_brightness(rgb) for rgb in colors
        )
    )

    connection.write(
        (payload + "\n").encode("ascii")
    )
    connection.flush()

# ---------- Joystick und Aktualisierung ----------


def main():
    global PIXEL_SIZE_KM, BRIGHTNESS

    print("Verfügbare serielle Ports:")
    for port in list_ports.comports():
        print(f"  {port.device}: {port.description}")

    print(f"\nVerbinde mit {SERIAL_PORT} ...")

    with serial.Serial(
        SERIAL_PORT,
        BAUD_RATE,
        timeout=0.1,
        write_timeout=5,
    ) as connection:

        time.sleep(2)
        connection.reset_input_buffer()

        last_update = 0.0
        last_joystick_move = 0.0

        weather_update_requested = True
        cached_colors = None

        print("Lumatrix-Wetterprogramm gestartet.")
        print(f"Pixelgrösse: {PIXEL_SIZE_KM} km")
        print("Joystick: UP = grösser, DOWN = kleiner")

        while True:
            try:
                while connection.in_waiting:
                    message = (
                        connection.readline()
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )

                    if message == "UP":
                        new_size = min(
                            MAX_PIXEL_SIZE_KM,
                            PIXEL_SIZE_KM + PIXEL_STEP_KM,
                        )

                        if new_size != PIXEL_SIZE_KM:
                            PIXEL_SIZE_KM = new_size
                            weather_update_requested = True
                            last_joystick_move = time.monotonic()

                            print(
                                f"Joystick HOCH: "
                                f"{PIXEL_SIZE_KM} km pro Pixel"
                            )

                    elif message == "DOWN":
                        new_size = max(
                            MIN_PIXEL_SIZE_KM,
                            PIXEL_SIZE_KM - PIXEL_STEP_KM,
                        )

                        if new_size != PIXEL_SIZE_KM:
                            PIXEL_SIZE_KM = new_size
                            weather_update_requested = True
                            last_joystick_move = time.monotonic()

                            print(
                                f"Joystick RUNTER: "
                                f"{PIXEL_SIZE_KM} km pro Pixel"
                            )

                    elif message == "RIGHT":
                        new_brightness = min(
                            MAX_BRIGHTNESS,
                            round(BRIGHTNESS + BRIGHTNESS_STEP, 2),
                        )

                        if new_brightness != BRIGHTNESS:
                            BRIGHTNESS = new_brightness
                            if cached_colors is not None:
                                send_pixels(connection, cached_colors)

                            print(
                                f"Helligkeit erhöht: "
                                f"{BRIGHTNESS:.2f}"
                            )

                    elif message == "LEFT":
                        new_brightness = max(
                            MIN_BRIGHTNESS,
                            round(BRIGHTNESS - BRIGHTNESS_STEP, 2),
                        )

                        if new_brightness != BRIGHTNESS:
                            BRIGHTNESS = new_brightness
                            if cached_colors is not None:
                                send_pixels(connection, cached_colors)

                            print(
                                f"Helligkeit reduziert: "
                                f"{BRIGHTNESS:.2f}"
                            )

                    elif message:
                        print(f"Pico: {message}")

                now = time.monotonic()

                # Reguläres Update alle 15 Minuten oder
                # verzögertes Update nach Joystick-Bewegung.
                
                regular_update_due = (
                    now - last_update >= UPDATE_SECONDS
                )

                joystick_delay_elapsed = (
                    now - last_joystick_move
                    >= JOYSTICK_UPDATE_DELAY
                )

                if regular_update_due or (
                    weather_update_requested and joystick_delay_elapsed
                ):
                    print(
                        f"Lade Wetterdaten für "
                        f"{PIXEL_SIZE_KM} km pro Pixel ..."
                    )

                    points = create_grid(PIXEL_SIZE_KM)
                    cached_colors = fetch_weather(points)

                    send_pixels(connection, cached_colors)

                    last_update = time.monotonic()
                    weather_update_requested = False

                    print("64 Pixel aktualisiert.")

            except Exception as error:
                print(f"Fehler: {error}")
                print("Letzte Anzeige bleibt bestehen.")
                time.sleep(2)

            time.sleep(0.02)


if __name__ == "__main__":
    main()
