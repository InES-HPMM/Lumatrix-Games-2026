import json
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPUTER = os.path.join(ROOT, "2_COMPUTER")
sys.path.insert(0, COMPUTER)

import catch_core


class CatchCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "fixtures", "connections.json")
        with open(path, "r", encoding="utf-8") as handle:
            cls.response = json.load(handle)

    def test_normalizes_live_departure_platform_and_delay(self):
        now = 1792681800  # 17:10 local
        items = catch_core.normalize_connections(self.response, now, 6, 2)
        first = items[0]
        self.assertEqual(first["line"], "S2")
        self.assertEqual(first["delay"], 4)
        self.assertEqual(first["platform"], "4")
        self.assertTrue(first["flags"] & catch_core.FLAG_PLATFORM_CHANGED)
        self.assertEqual(first["departure_s"], 900)
        self.assertEqual(first["leave_s"], 420)

    def test_accepts_api_timezone_without_colon(self):
        raw = json.loads(json.dumps(self.response["connections"][1]))
        raw["from"]["prognosis"]["departure"] = "2026-10-22T17:29:00+0200"
        item = catch_core.normalize_connection(raw, 1792681800, 6, 2)
        self.assertEqual(item["departure_s"], 1140)

    def test_recommends_first_reachable_connection(self):
        connections = [
            {"leave_s": -10, "flags": 0},
            {"leave_s": 120, "flags": catch_core.FLAG_CANCELLED},
            {"leave_s": 300, "flags": 0},
        ]
        self.assertEqual(catch_core.recommended_index(connections), 2)

    def test_recommendation_only_stays_for_visible_due_signal(self):
        connections = [
            {"leave_s": -8, "flags": 0},
            {"leave_s": 300, "flags": 0},
        ]
        self.assertEqual(catch_core.recommended_index(connections), 0)
        connections[0]["leave_s"] = -9
        self.assertEqual(catch_core.recommended_index(connections), 1)

    def test_usb_packet_contains_no_private_test_data(self):
        packet = catch_core.make_packet(
            catch_core.demo_packets()[0]["_normalized"],
        )
        public = catch_core.usb_packet(packet)
        self.assertNotIn("_normalized", public)
        self.assertEqual(public["a"], "c")
        self.assertNotIn("q", public)
        self.assertNotIn("d", public)

    def test_demo_covers_delay_platform_and_cancellation(self):
        packets = catch_core.demo_packets()
        self.assertEqual(packets[1]["e"][0], "D")
        self.assertEqual(packets[2]["e"][0], "P")
        self.assertEqual(packets[3]["e"][0], "X")


if __name__ == "__main__":
    unittest.main()
