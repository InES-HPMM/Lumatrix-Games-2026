# Laedt das Spiel auf den Raspberry Pi Pico und startet es
#
# 1. Sichert alle Dateien, die schon auf dem Pico sind, nach
#    Backups\pico_<Datum>_<Uhrzeit>\
# 2. Kopiert main.py und levels.py auf den Pico und prueft die Kopie
# 3. Startet den Pico neu -> main.py laeuft
#
# Starten:  python upload_pico.py [COM-Port]
# Thonny darf dabei nicht mit dem Pico verbunden sein.

import binascii
import hashlib
import os
import sys
import time

import serial
from serial.tools import list_ports

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)    # das Spiel liegt eine Ebene hoeher
FILES = ["main.py", "levels.py"]
CHUNK = 256


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x2E8A:             # Raspberry Pi
            return p.device
    sys.exit("Kein Pico gefunden. Ist er per USB angeschlossen?")


class Pico:
    def __init__(self, port):
        self.s = serial.Serial(port, 115200, timeout=1)
        if hasattr(self.s, "set_buffer_size"):     # nur unter Windows
            self.s.set_buffer_size(rx_size=1 << 20)
        self.pending = b""                         # schon gelesen, noch offen

    def read_until(self, end, timeout=10):
        # Liest alles, was bereitliegt, auf einmal. Byteweises Lesen ist zu
        # langsam, dann verwirft Windows ganze USB-Pakete (je 64 Bytes).
        data = self.pending
        t = time.time()
        while end not in data:
            chunk = self.s.read(max(1, self.s.in_waiting))
            if chunk:
                data += chunk
            elif time.time() - t > timeout:
                raise TimeoutError("Pico antwortet nicht: %r" % data[-80:])
        i = data.index(end) + len(end)
        self.pending = data[i:]
        return data[:i]

    def enter_raw(self):
        self.s.write(b"\r\x03\x03")     # laufendes Programm stoppen
        time.sleep(0.2)
        self.s.reset_input_buffer()
        self.s.write(b"\r\x01")         # Raw-REPL
        self.read_until(b"raw REPL; CTRL-B to exit\r\n>")

    def exec(self, code):
        # Raw-Paste-Modus: Der Pico gibt mit \x01 frei, wie viel er
        # annehmen kann, damit keine Zeichen verloren gehen
        data = code.encode()
        self.pending = b""
        self.s.write(b"\x05A\x01")
        if self.s.read(2) != b"R\x01":
            raise RuntimeError("Pico unterstuetzt keinen Raw-Paste-Modus")
        window = int.from_bytes(self.s.read(2), "little")
        free = window
        i = 0
        while i < len(data):
            while free == 0 or self.s.in_waiting:
                b = self.s.read(1)
                if b == b"\x01":
                    free += window
                elif b == b"\x04":
                    self.s.write(b"\x04")
                    raise RuntimeError("Pico hat die Uebertragung abgebrochen")
            n = min(free, len(data) - i)
            self.s.write(data[i:i + n])
            i += n
            free -= n
        self.s.write(b"\x04")
        self.read_until(b"\x04")        # Pico bestaetigt das Ende
        out = self.read_until(b"\x04")[:-1]
        err = self.read_until(b"\x04")[:-1]
        self.read_until(b">")
        if err:
            raise RuntimeError(err.decode(errors="replace"))
        return out.decode(errors="replace")

    def list_files(self):
        return eval(self.exec(
            "import os\n"
            "print([f[0] for f in os.ilistdir() if f[1] == 0x8000])"))

    def read_file(self, name):
        # Stueckweise lesen, sonst reicht der Speicher des Pico nicht
        hexdata = self.exec(
            "import binascii\n"
            "with open(%r, 'rb') as f:\n"
            "    while True:\n"
            "        b = f.read(%d)\n"
            "        if not b:\n"
            "            break\n"
            "        print(binascii.hexlify(b).decode())" % (name, CHUNK))
        return binascii.unhexlify("".join(hexdata.split()))

    def file_hash(self, name):
        # Der Pico rechnet die Pruefsumme selbst, nur 64 Zeichen kommen zurueck
        return self.exec(
            "import hashlib, binascii\n"
            "h = hashlib.sha256()\n"
            "with open(%r, 'rb') as f:\n"
            "    while True:\n"
            "        b = f.read(%d)\n"
            "        if not b:\n"
            "            break\n"
            "        h.update(b)\n"
            "print(binascii.hexlify(h.digest()).decode())" % (name, CHUNK)
        ).strip()

    def read_file_checked(self, name, tries=3):
        for _ in range(tries):
            data = self.read_file(name)
            if hashlib.sha256(data).hexdigest() == self.file_hash(name):
                return data
        raise RuntimeError("%s liess sich nicht fehlerfrei lesen" % name)

    def write_file(self, name, data):
        self.exec("f = open(%r, 'wb')" % name)
        for i in range(0, len(data), CHUNK):
            self.exec("f.write(%r)" % data[i:i + CHUNK])
        self.exec("f.close()")

    def soft_reset(self):
        self.s.write(b"\x02")           # Raw-REPL verlassen
        time.sleep(0.1)
        self.s.write(b"\x04")           # Neustart -> main.py laeuft
        time.sleep(0.5)
        self.s.close()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    print("Pico an", port)
    try:
        pico = Pico(port)
    except serial.SerialException as ex:
        sys.exit("Port %s ist belegt (Thonny offen?): %s" % (port, ex))
    pico.enter_raw()

    existing = pico.list_files()
    print("Auf dem Pico:", ", ".join(existing) or "(leer)")
    if existing:
        folder = os.path.join(GAME_DIR, "Backups",
                              time.strftime("pico_%Y-%m-%d_%H%M%S"))
        os.makedirs(folder)         # Fehler, falls es ihn schon gibt
        for name in existing:
            with open(os.path.join(folder, name), "wb") as f:
                f.write(pico.read_file_checked(name))
        print("Gesichert und geprueft nach", folder)

    for name in FILES:
        with open(os.path.join(GAME_DIR, name), "rb") as f:
            data = f.read()
        pico.write_file(name, data)
        if pico.file_hash(name) != hashlib.sha256(data).hexdigest():
            sys.exit("FEHLER: %s auf dem Pico weicht ab!" % name)
        print("Hochgeladen und geprueft:", name, "(%d Bytes)" % len(data))

    pico.soft_reset()
    print("Pico neu gestartet - das Spiel laeuft.")


if __name__ == "__main__":
    main()
