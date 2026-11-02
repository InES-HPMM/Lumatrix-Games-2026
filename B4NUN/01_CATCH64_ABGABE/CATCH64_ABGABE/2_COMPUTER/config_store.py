"""Lesbare, validierte Benutzereinstellungen fuer CATCH 64."""

import json
import os


DEFAULT_CONFIG = {
    "from": "Wädenswil",
    "to": "Zürich HB",
    "walk_minutes": 6,
    "reserve_minutes": 3,
    "direct_only": False,
    "update_seconds": 30,
    "serial_port": "",
}


def validate(config):
    result = dict(DEFAULT_CONFIG)
    result.update(config or {})
    # Entfernt den Eintrag automatisch aus Konfigurationen aelterer Versionen.
    result.pop("exit_direction", None)
    for key in ("from", "to"):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 100:
            raise ValueError("{} ist ungueltig".format(key))
        result[key] = value.strip()
    for key, low, high in (
        ("walk_minutes", 0, 60),
        ("reserve_minutes", 0, 30),
        ("update_seconds", 20, 600),
    ):
        value = result.get(key)
        if isinstance(value, bool):
            raise ValueError("{} ist ungueltig".format(key))
        value = int(value)
        if not low <= value <= high:
            raise ValueError("{} ausserhalb des Bereichs".format(key))
        result[key] = value
    result["direct_only"] = bool(result.get("direct_only"))
    port = result.get("serial_port") or ""
    if not isinstance(port, str) or len(port) > 200:
        raise ValueError("serial_port ist ungueltig")
    result["serial_port"] = port.strip()
    return result


class ConfigStore:
    def __init__(self, path):
        self.path = path

    def load(self):
        if not os.path.exists(self.path):
            self.save(DEFAULT_CONFIG)
        with open(self.path, "r", encoding="utf-8") as handle:
            return validate(json.load(handle))

    def save(self, config):
        validated = validate(config)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(validated, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, self.path)
        return validated
