import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PICO = os.path.join(ROOT, "1_PICO")
sys.path.insert(0, PICO)

import catch_logic


class PicoLogicTest(unittest.TestCase):
    def test_demo_packet_is_valid(self):
        packet = catch_logic.demo_packet()
        self.assertIs(catch_logic.validate_packet(packet), packet)

    def test_minutes_round_up_for_passenger_safety(self):
        self.assertEqual(catch_logic.minutes_remaining(301, 0), 6)
        self.assertEqual(catch_logic.minutes_remaining(301, 2000), 5)
        self.assertEqual(catch_logic.minutes_remaining(2, 3000), 0)

    def test_last_minute_counts_exact_seconds(self):
        self.assertEqual(catch_logic.seconds_remaining(61, 0), 61)
        self.assertEqual(catch_logic.seconds_remaining(60, 0), 60)
        self.assertEqual(catch_logic.seconds_remaining(60, 1000), 59)
        self.assertEqual(catch_logic.seconds_remaining(60, 59000), 1)
        self.assertEqual(catch_logic.seconds_remaining(60, 61000), 0)

    def test_line_chunks_do_not_scroll(self):
        self.assertEqual(catch_logic.line_chunks("IR35"), ("IR", "35"))
        self.assertEqual(catch_logic.line_chunks("S2"), ("S2",))
        self.assertEqual(catch_logic.clean_alnum(" S 2!"), "S2")

    def test_urgency_is_simple_and_stable(self):
        self.assertEqual(catch_logic.urgency(8), "GREEN")
        self.assertEqual(catch_logic.urgency(5), "AMBER")
        self.assertEqual(catch_logic.urgency(1), "RED")

    def test_due_signal_is_short_and_not_extra_reserve(self):
        self.assertEqual(catch_logic.leave_phase(1, 0), "COUNTDOWN")
        self.assertEqual(catch_logic.leave_phase(0, 0), "DUE")
        self.assertEqual(catch_logic.leave_phase(0, 8000), "DUE")
        self.assertEqual(catch_logic.leave_phase(0, 9000), "MISSED")

    def test_next_reachable_connection_skips_cancelled_and_too_late(self):
        connections = [
            ["S2", -10, 100, 0, "2", 0],
            ["S8", 500, 800, 0, "3", catch_logic.FLAG_CANCELLED],
            ["IR35", 600, 900, 0, "4", 0],
        ]
        self.assertEqual(catch_logic.next_reachable_index(connections, 0, 0), 2)

    def test_rejects_invalid_packet(self):
        packet = catch_logic.demo_packet()
        packet["r"] = 99
        with self.assertRaises(ValueError):
            catch_logic.validate_packet(packet)

if __name__ == "__main__":
    unittest.main()
