"""Robuste USB-Verbindung zur originalen Lumatrix."""

import json
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

from catch_core import usb_packet


def find_pico_port(configured_port=""):
    if serial is None or list_ports is None:
        raise RuntimeError("pyserial fehlt; bitte den mitgelieferten Starter verwenden")
    if configured_port:
        return configured_port

    candidates = []
    for port in list_ports.comports():
        description = (port.description or "").lower()
        manufacturer = (port.manufacturer or "").lower()
        if (
            port.vid == 0x2E8A
            or "pico" in description
            or "micropython" in description
            or "raspberry" in manufacturer
        ):
            candidates.append(port.device)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RuntimeError("Keine Lumatrix gefunden; Thonny schliessen und USB pruefen")
    raise RuntimeError("Mehrere Pico-Ports gefunden: {}".format(", ".join(candidates)))


def encoded_packet(packet):
    line = json.dumps(usb_packet(packet), separators=(",", ":"), ensure_ascii=True) + "\n"
    if len(line) >= 900:
        raise ValueError("USB-Paket ist unerwartet gross")
    return line.encode("ascii")


def restart_pico(connection):
    """Bringt die Lumatrix verlaesslich vom REPL-Prompt in main.py zurueck."""
    connection.write(b"\x03\x03")  # laufendes Programm oder REPL sicher anhalten
    connection.flush()
    time.sleep(0.5)
    connection.reset_input_buffer()
    connection.write(b"\x04")  # MicroPython Soft-Reboot; startet main.py
    connection.flush()
    time.sleep(1.8)

    messages = []
    while connection.in_waiting:
        message = connection.readline().decode("utf-8", errors="replace").strip()
        if message:
            messages.append(message)
    for message in messages:
        if "CATCH64_READY" in message:
            return "CATCH64_READY"
    return " | ".join(messages[-3:]) if messages else "Lumatrix neu gestartet"


def run_serial(state, config_store, stop_event):
    """Verbindet automatisch neu; ein USB-Fehler beendet die App nicht."""
    while not stop_event.is_set():
        try:
            config = config_store.load()
            port = find_pico_port(config.get("serial_port", ""))
            state.update_status(serial="Verbunden: {}".format(port), serial_error="")
            with serial.Serial(port, 115200, timeout=0.15, write_timeout=3) as connection:
                state.update_status(pico=restart_pico(connection))
                sent_version = -1
                while not stop_event.is_set():
                    packet, version = state.packet_snapshot()
                    if packet is not None and version != sent_version:
                        connection.write(encoded_packet(packet))
                        connection.flush()
                        sent_version = version
                    while connection.in_waiting:
                        message = connection.readline().decode("utf-8", errors="replace").strip()
                        if message:
                            state.update_status(pico=message)
                    stop_event.wait(0.15)
        except Exception as exc:
            state.update_status(serial="Nicht verbunden", serial_error=str(exc))
            stop_event.wait(2.5)
