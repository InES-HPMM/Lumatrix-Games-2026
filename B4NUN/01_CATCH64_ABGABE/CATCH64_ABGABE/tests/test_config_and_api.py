import os
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPUTER = os.path.join(ROOT, "2_COMPUTER")
sys.path.insert(0, COMPUTER)

from config_store import ConfigStore, validate
import transport_api


class ConfigAndApiTest(unittest.TestCase):
    def test_config_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ConfigStore(os.path.join(directory, "config.json"))
            saved = store.save({
                "from": "Wädenswil",
                "to": "Zürich HB",
                "walk_minutes": 5,
                "reserve_minutes": 1,
                "direct_only": True,
            })
            self.assertEqual(store.load(), saved)
            self.assertNotIn("exit_direction", saved)

    def test_invalid_time_is_rejected(self):
        with self.assertRaises(ValueError):
            validate({"walk_minutes": 999})

    def test_url_is_encoded_and_keyless(self):
        url = transport_api.connections_url(validate({}))
        self.assertIn("W%C3%A4denswil", url)
        self.assertIn("Z%C3%BCrich+HB", url)
        self.assertIn("limit=16", url)
        self.assertNotIn("token", url.lower())

    def test_rail_and_bus_station_are_combined(self):
        stations = [
            {"id": "8503798", "name": "Wädenswil, Bahnhof", "coordinate": {"x": 47.2294, "y": 8.6753}},
            {"id": "8503206", "name": "Wädenswil", "coordinate": {"x": 47.2293, "y": 8.6752}},
            {"id": "999", "name": "Wädenswil, Sandhof", "coordinate": {"x": 47.21, "y": 8.65}},
        ]
        selected = transport_api.choose_stations("Wädenswil, Bahnhof", stations)
        self.assertEqual({item["id"] for item in selected}, {"8503798", "8503206"})

    def test_stationboard_adds_s8_to_direct_departures(self):
        board = {"stationboard": [
            {
                "stop": {
                    "departure": "2026-10-25T17:53:00+0100",
                    "departureTimestamp": 1792947180,
                    "delay": 0,
                    "platform": "2",
                    "prognosis": {"departure": "2026-10-25T17:53:00+0100"},
                },
                "category": "S",
                "number": "8",
                "passList": [
                    {"station": {"id": "8503206", "name": "Wädenswil"}},
                    {"station": {"id": "8503000", "name": "Zürich HB"}},
                ],
            },
            {
                "stop": {"departureTimestamp": 1792947500},
                "category": "S",
                "number": "8",
                "passList": [
                    {"station": {"id": "8503206", "name": "Wädenswil"}},
                    {"station": {"id": "8503305", "name": "Pfäffikon SZ"}},
                ],
            },
        ]}
        targets = [{"id": "8503000", "name": "Zürich HB"}]
        connections = transport_api.stationboard_connections(board, targets)
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0]["products"], ["S8"])

    def test_direct_departures_and_fast_routes_are_merged_in_time_order(self):
        s8 = {"from": {"departureTimestamp": 200}, "products": ["S8"]}
        s2 = {"from": {"departureTimestamp": 100}, "products": ["S2"]}
        duplicate = {"from": {"departureTimestamp": 100}, "products": ["S 2"]}
        merged = transport_api.merge_connections([s8], [s2, duplicate])
        self.assertEqual([item["products"][0] for item in merged], ["S2", "S8"])


if __name__ == "__main__":
    unittest.main()
