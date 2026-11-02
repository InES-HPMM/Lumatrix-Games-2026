"""CATCH 64 – Startpunkt fuer Windows, Ubuntu und macOS."""

import argparse
import errno
import os
import threading
import time
import webbrowser

import catch_core
from config_store import ConfigStore
import serial_link
import setup_server
import transport_api


class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self._packet = None
        self._packet_version = 0
        self._status = {
            "data": "Warte auf erste Verbindung",
            "serial": "Suche Lumatrix",
            "pico": "",
            "data_error": "",
            "serial_error": "",
        }
        self._refresh = threading.Event()

    def set_packet(self, packet, data_text):
        with self._lock:
            self._packet = packet
            self._packet_version += 1
            self._status["data"] = data_text
            self._status["data_error"] = ""

    def packet_snapshot(self):
        with self._lock:
            return self._packet, self._packet_version

    def update_status(self, **values):
        with self._lock:
            self._status.update(values)

    def status_snapshot(self):
        with self._lock:
            return dict(self._status)

    def request_refresh(self):
        self._refresh.set()

    def wait_for_refresh(self, timeout):
        changed = self._refresh.wait(timeout)
        self._refresh.clear()
        return changed


def live_loop(state, store, stop_event):
    previous_packet = None
    previous_config = None
    while not stop_event.is_set():
        try:
            config = store.load()
            config_signature = (
                config["from"], config["to"], config["walk_minutes"],
                config["reserve_minutes"], config["direct_only"],
            )
            if config_signature != previous_config:
                previous_packet = None
                previous_config = config_signature
            response = transport_api.fetch_connections(config)
            connections = catch_core.normalize_connections(
                response,
                time.time(),
                config["walk_minutes"],
                config["reserve_minutes"],
            )
            packet = catch_core.make_packet(
                connections,
                previous_packet,
            )
            recommendation = connections[packet["r"]]
            state.set_packet(
                packet,
                "{} → {} · {} · los in {} Min.".format(
                    config["from"],
                    config["to"],
                    recommendation["line"],
                    max(0, (recommendation["leave_s"] + 59) // 60),
                ),
            )
            previous_packet = packet
            wait_seconds = config["update_seconds"]
        except Exception as exc:
            state.update_status(data="Live-Daten voruebergehend nicht erreichbar", data_error=str(exc))
            wait_seconds = 10
        state.wait_for_refresh(wait_seconds)


def demo_loop(state, stop_event):
    packets = catch_core.demo_packets()
    labels = (
        "Demo: S2 · in 5 Minuten losgehen",
        "Demo: +4 Minuten Verspaetung · neue Aufbruchzeit",
        "Demo: Gleiswechsel auf Gleis 4",
        "Demo: Ausfall · naechste Verbindung wird empfohlen",
    )
    index = 0
    while not stop_event.is_set():
        state.set_packet(packets[index], labels[index])
        index = (index + 1) % len(packets)
        stop_event.wait(7)


def parse_args():
    parser = argparse.ArgumentParser(description="CATCH 64 Live-Aufbruchassistent")
    parser.add_argument("--demo", action="store_true", help="reproduzierbare Jury-Demo ohne Internet")
    parser.add_argument("--no-browser", action="store_true", help="Einrichtungsseite nicht automatisch oeffnen")
    parser.add_argument("--port", type=int, default=8765, help="lokaler Port der Einrichtungsseite")
    return parser.parse_args()


def main():
    args = parse_args()
    base = os.path.dirname(os.path.abspath(__file__))
    store = ConfigStore(os.path.join(base, "config.json"))
    store.load()
    state = AppState()
    stop_event = threading.Event()

    url = "http://127.0.0.1:{}".format(args.port)
    try:
        server = setup_server.start_server(store, state, port=args.port)
    except OSError as exc:
        if exc.errno not in (errno.EADDRINUSE, 48, 98):
            raise
        print("CATCH 64 laeuft bereits.")
        print("Die vorhandene Einrichtung wird geoeffnet:", url)
        if not args.no_browser:
            webbrowser.open(url)
        return
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    serial_thread = threading.Thread(
        target=serial_link.run_serial,
        args=(state, store, stop_event),
        daemon=True,
    )
    serial_thread.start()

    data_target = demo_loop if args.demo else live_loop
    data_thread = threading.Thread(
        target=data_target,
        args=(state, stop_event) if args.demo else (state, store, stop_event),
        daemon=True,
    )
    data_thread.start()

    print("CATCH 64 gestartet")
    print("Einrichtung:", url)
    print("Modus:", "DEMO" if args.demo else "LIVE")
    print("Dieses Fenster offen lassen. Beenden mit Ctrl+C.\n")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        while True:
            stop_event.wait(1)
    except KeyboardInterrupt:
        print("\nCATCH 64 beendet.")
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
